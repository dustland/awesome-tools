import os
from typing import Dict, List, Optional
import arxiv
import requests
from tavily import Client
from utils.logger import logger
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pytz
import re

class ContentFetcher:
    def __init__(self, github_token: str, tavily_api_key: str = None):
        self.github_token = github_token
        self.tavily_client = Client(tavily_api_key) if tavily_api_key else None
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
    def fetch_all_content(self) -> List[Dict]:
        """Fetch content using aggregated search approach with focus on recent updates."""
        all_content = []
        
        searches = [
            {
                'query': 'latest embodied AI robotics research papers 2025 2024 github implementation',
                'type': 'research',
                'search_type': 'tech'
            },
            {
                'query': 'new embodied AI robotics simulator tools github released:>2024',
                'type': 'tools',
                'search_type': 'tech'
            },
            {
                'query': 'latest embodied AI humanoid robotics products news 2025 2024',
                'type': 'product',
                'search_type': 'news'
            }
        ]
        
        total_searches = len(searches) * (2 if self.tavily_client else 1)  # Each search does Tavily + GitHub
        completed_searches = 0
        
        for search in searches:
            try:
                # 1. Search using Tavily API with time filtering
                if self.tavily_client:
                    logger.info(f"[{completed_searches + 1}/{total_searches}] Searching Tavily for {search['type']}: {search['query']}")
                    tavily_results = self._tavily_search(
                        search['query'], 
                        search['search_type'],
                        search['type']
                    )
                    if tavily_results:
                        all_content.extend(tavily_results)
                        logger.info(f"Added {len(tavily_results)} results from Tavily {search['type']} search")
                    completed_searches += 1
                
                # 2. Search GitHub with time filtering
                logger.info(f"[{completed_searches + 1}/{total_searches}] Searching GitHub for {search['type']}: {search['query']}")
                github_results = self._github_search(search['query'])
                processed_github = self._process_github_results(github_results, search['type'])
                # Filter for recent updates
                recent_github = [
                    item for item in processed_github 
                    if self._is_recent_content(item.get('metrics', {}).get('updated_at'))
                ]
                if recent_github:
                    all_content.extend(recent_github)
                    logger.info(f"Added {len(recent_github)} results from GitHub {search['type']} search")
                completed_searches += 1
                
                # 3. Search arXiv for research papers if needed
                if search['type'] == 'research':
                    logger.info(f"Searching arXiv for research papers...")
                    arxiv_results = self._arxiv_search(search['query'])
                    # Filter for recent papers
                    recent_arxiv = [
                        item for item in arxiv_results 
                        if self._is_recent_content(item.get('metrics', {}).get('published_date'))
                    ]
                    if recent_arxiv:
                        all_content.extend(recent_arxiv)
                        logger.info(f"Added {len(recent_arxiv)} results from arXiv search")
                
            except Exception as e:
                logger.error(f"Error during {search['type']} search: {str(e)}")
                continue
        
        # Remove duplicates based on URLs
        seen_urls = set()
        unique_content = []
        for item in all_content:
            urls = set(item.get('links', []))
            if not urls.intersection(seen_urls):
                unique_content.append(item)
                seen_urls.update(urls)
        
        # Sort by impact score
        scored_content = []
        for content in unique_content:
            try:
                content['impact_score'] = self._calculate_impact_score(content)
                scored_content.append(content)
            except Exception as e:
                logger.error(f"Error calculating impact score: {str(e)}")
                continue
        
        scored_content.sort(key=lambda x: x.get('impact_score', 0), reverse=True)
        logger.info(f"Final content count: {len(scored_content)} items")
        return scored_content
        
    def _is_recent_content(self, date_str: Optional[str], months: int = 6) -> bool:
        """Check if content is recent (within specified months)."""
        if not date_str:
            return False
            
        try:
            if isinstance(date_str, str):
                content_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                content_date = date_str
                
            cutoff_date = datetime.now(pytz.UTC) - timedelta(days=30 * months)
            return content_date > cutoff_date
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return False

    def _tavily_search(self, query: str, search_type: str, content_type: str) -> List[Dict]:
        """Search using Tavily API."""
        if not self.tavily_client:
            return []
        
        try:
            # Adjust query based on content type
            if content_type == "product":
                query = f"news {query}"  # Prefix with 'news' for product searches
            
            logger.info(f"Starting Tavily search for query: {query}")
            response = self.tavily_client.search(
                query=query,
                search_depth="advanced",  # Use advanced search for better results
                include_domains=[
                    'github.com',
                    'arxiv.org', 
                    'paperswithcode.com',
                    'x.com',
                    'twitter.com',
                    'huggingface.co',
                    'arxiv-sanity.com'
                ],
                max_results=20
            )
            
            if not response:
                logger.warning(f"Empty response from Tavily for query: {query}")
                return []
                
            logger.info(f"Received {len(response.get('results', []))} results from Tavily")
            
            results = []
            for item in response.get('results', []):
                try:
                    # Extract GitHub URLs if present (but not required)
                    github_links = re.findall(
                        r'https?://github\.com/[^/\s]+/[^/\s]+',
                        item.get('content', '') + item.get('url', '')
                    )
                    
                    # For research content, look for citation information
                    citations = 0
                    if content_type == 'research':
                        citation_patterns = [
                            r'cited by (\d+)',
                            r'(\d+) citations',
                            r'citations: (\d+)'
                        ]
                        content_lower = item.get('content', '').lower()
                        for pattern in citation_patterns:
                            match = re.search(pattern, content_lower)
                            if match:
                                citations = int(match.group(1))
                                break
                    
                    # Check if it's a social media post
                    is_social = any(domain in item.get('url', '').lower() 
                                  for domain in ['x.com', 'twitter.com'])
                    
                    # Check for research indicators
                    is_research = any(domain in item.get('url', '').lower()
                                    for domain in ['arxiv.org', 'arxiv-sanity.com', 'paperswithcode.com'])
                    
                    # Extract date information if available
                    pub_date = None
                    date_patterns = [
                        r'published(?:\s+on)?\s+(\d{4}-\d{2}-\d{2})',
                        r'posted(?:\s+on)?\s+(\d{4}-\d{2}-\d{2})',
                        r'date:\s+(\d{4}-\d{2}-\d{2})'
                    ]
                    for pattern in date_patterns:
                        match = re.search(pattern, item.get('content', '').lower())
                        if match:
                            pub_date = match.group(1)
                            break
                    
                    results.append({
                        'title': item.get('title'),
                        'description': item.get('content'),
                        'links': [item.get('url')] + github_links,
                        'type': content_type,
                        'citations': citations,
                        'relevance_score': item.get('score', 0),
                        'is_social': is_social,
                        'is_research': is_research,
                        'has_code': bool(github_links),
                        'published_date': pub_date
                    })
                except Exception as e:
                    logger.error(f"Error processing Tavily result: {str(e)}")
                    continue
            
            logger.info(f"Successfully processed {len(results)} results from Tavily")
            return results
            
        except Exception as e:
            logger.error(f"Tavily search error for query '{query}': {str(e)}")
            return []

    def _github_search(self, query: str) -> List[Dict]:
        """Search GitHub repositories."""
        url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 20
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('items', [])
        except requests.exceptions.Timeout:
            logger.error(f"GitHub search timed out for query: {query}")
            return []
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return []

    def _arxiv_search(self, query: str) -> List[Dict]:
        """Search arXiv papers with GitHub links."""
        search = arxiv.Search(
            query=query,
            max_results=20,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        papers = []
        for result in search.results():
            # Look for GitHub links in the abstract
            github_links = re.findall(r'https?://github\.com/[^/\s]+/[^/\s]+', result.summary)
            if github_links:
                paper = {
                    'title': result.title,
                    'description': result.summary.split('.')[0],
                    'links': [
                        result.entry_id,  # arXiv link
                        result.pdf_url,   # PDF link
                        *github_links     # GitHub links
                    ],
                    'published_date': result.published.isoformat(),
                    'authors': [author.name for author in result.authors],
                    'citations': 0,
                    'type': 'paper'
                }
                papers.append(paper)
        
        return papers

    def _process_github_results(self, results: List[Dict], content_type: str) -> List[Dict]:
        """Process GitHub search results."""
        processed = []
        for item in results:
            processed.append({
                'title': item.get('full_name', ''),
                'description': item.get('description', ''),
                'links': [item.get('html_url')],
                'type': content_type,
                'metrics': {
                    'stars': item.get('stargazers_count', 0),
                    'forks': item.get('forks_count', 0),
                    'updated_at': item.get('updated_at'),
                    'created_at': item.get('created_at')
                }
            })
        return processed

    def _enrich_with_metrics(self, content: Dict) -> Dict:
        """Enrich content with popularity metrics."""
        # Extract GitHub URLs from the content
        github_urls = self._extract_github_urls(content.get('links', []))
        
        if github_urls and 'metrics' not in content:
            metrics = self._get_github_metrics(github_urls[0])
            content['metrics'] = metrics
        elif 'metrics' not in content:
            content['metrics'] = {
                'stars': 0,
                'forks': 0,
                'updated_at': None,
                'created_at': None
            }
        
        # Calculate impact score
        content['impact_score'] = self._calculate_impact_score(content)
        return content

    def _extract_github_urls(self, links: List[str]) -> List[str]:
        """Extract GitHub repository URLs from a list of links."""
        github_pattern = r'https?://github\.com/([^/]+/[^/]+)'
        return [
            link for link in links 
            if re.match(github_pattern, link)
        ]

    def _get_github_metrics(self, github_url: str) -> Dict:
        """Get GitHub repository metrics."""
        try:
            # Skip URLs that are clearly not repository URLs
            if any(invalid_path in github_url for invalid_path in [
                '/features/', '/apps/', '/settings/', '/marketplace/',
                'github.blog', 'help.github.com', 'docs.github.com'
            ]):
                return {}
            
            # Extract owner and repo using a more specific regex
            match = re.match(r'https?://github\.com/([^/\s]+)/([^/\s#?]+)', github_url)
            if not match:
                return {}
            
            owner, repo = match.groups()
            # Skip if owner or repo looks invalid
            if not owner or not repo or len(owner) < 1 or len(repo) < 1:
                return {}
            
            # Clean up repo name (remove any trailing parts)
            repo = repo.split('#')[0].split('?')[0]
            
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            
            response = requests.get(api_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Only return metrics if we got valid data
            if not isinstance(data, dict) or 'message' in data:
                return {}
                
            return {
                'stars': data.get('stargazers_count', 0),
                'forks': data.get('forks_count', 0),
                'updated_at': data.get('updated_at'),
                'created_at': data.get('created_at')
            }
        except requests.exceptions.Timeout:
            logger.error(f"GitHub metrics timed out for {github_url}")
            return {}
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'status_code') and e.response.status_code == 404:
                # Silently ignore 404 errors as they're expected for invalid repos
                return {}
            logger.error(f"Error fetching GitHub metrics for {github_url}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error fetching GitHub metrics for {github_url}: {e}")
            return {}

    def _calculate_impact_score(self, content: Dict) -> float:
        """Calculate impact score based on various metrics with emphasis on content value."""
        metrics = content.get('metrics', {})
        
        # Base score calculation
        base_score = 0.0
        
        # GitHub metrics if available
        if content.get('has_code', False):
            stars = metrics.get('stars', 0)
            forks = metrics.get('forks', 0)
            base_score += (stars * 1.0 + forks * 0.5) / 100  # Normalize large numbers
        else:
            # Base score for non-code content
            base_score += 0.5  # Give a reasonable base score
        
        # Recency factors
        now = datetime.now(pytz.UTC)
        
        # Get the most relevant date
        reference_date = None
        if content.get('published_date'):
            try:
                reference_date = datetime.fromisoformat(content['published_date'].replace('Z', '+00:00'))
            except:
                pass
                
        if not reference_date and metrics.get('updated_at'):
            try:
                reference_date = datetime.fromisoformat(metrics['updated_at'].replace('Z', '+00:00'))
            except:
                pass
                
        if not reference_date and metrics.get('created_at'):
            try:
                reference_date = datetime.fromisoformat(metrics['created_at'].replace('Z', '+00:00'))
            except:
                pass
        
        # Calculate age factor
        days_old = (now - reference_date).days if reference_date else 1000
        
        # Adjust decay rate based on content type
        if content.get('is_social', False):
            age_factor = max(0.1, 2.0 - (days_old / 30))  # Faster decay for social
        elif content.get('is_research', False):
            age_factor = max(0.1, 2.0 - (days_old / 180))  # Slower decay for research
        else:
            age_factor = max(0.1, 2.0 - (days_old / 90))  # Medium decay for other content
        
        # Citations impact (especially important for research without code)
        citations = content.get('citations', 0)
        if content.get('is_research', False):
            citations_factor = 1.0 + (citations / 50)  # More weight to citations for research
        else:
            citations_factor = 1.0 + (citations / 100)
        
        # Content type specific boosts
        type_boosts = {
            'research': 1.3 if not content.get('has_code', False) else 1.2,  # Higher boost for pure research
            'tools': 1.2 if content.get('has_code', False) else 1.1,        # Higher boost for tools with code
            'product': 1.1                                                   # Standard boost for products
        }
        type_boost = type_boosts.get(content.get('type', ''), 1.0)
        
        # Social media adjustments
        if content.get('is_social', False):
            if days_old <= 7:  # Very recent social content
                type_boost *= 1.5
            elif days_old <= 30:  # Recent social content
                type_boost *= 1.2
            else:  # Older social content
                type_boost *= 0.7
        
        # Relevance boost from search results
        relevance_score = content.get('relevance_score', 0.5)
        relevance_boost = 0.5 + relevance_score  # Scale from 0.5 to 1.5
        
        # Calculate final score with adjusted weights
        impact_score = (
            base_score * 0.3 +         # Base/GitHub score
            age_factor * 0.3 +         # Recency
            citations_factor * 0.2 +    # Citations (increased weight)
            relevance_boost * 0.2      # Search relevance (increased weight)
        ) * type_boost                 # Type-specific boost
        
        # Log scoring details
        logger.debug(f"Impact score calculation for {content.get('title', 'Unknown')}:")
        logger.debug(f"  - Base Score: {base_score:.2f}")
        logger.debug(f"  - Age Factor: {age_factor:.2f}")
        logger.debug(f"  - Citations Factor: {citations_factor:.2f}")
        logger.debug(f"  - Type Boost: {type_boost:.2f}")
        logger.debug(f"  - Relevance Boost: {relevance_boost:.2f}")
        logger.debug(f"  - Is Research: {content.get('is_research', False)}")
        logger.debug(f"  - Has Code: {content.get('has_code', False)}")
        logger.debug(f"  - Is Social: {content.get('is_social', False)}")
        logger.debug(f"  - Days Old: {days_old}")
        logger.debug(f"  - Final Score: {impact_score:.2f}")
        
        return impact_score