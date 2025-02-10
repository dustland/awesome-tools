import os
from typing import Dict, List, Optional, Any
import arxiv
import requests
from tavily import Client
from utils.logger import logger
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pytz
import re
from utils.logger import logger

class ContentFetcher:
    def __init__(self, github_token: str, tavily_api_key: str = None):
        self.github_token = github_token
        self.tavily_client = Client(tavily_api_key) if tavily_api_key else None
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.important_authors = [
            "Yann LeCun", "Sergey Levine", "Pieter Abbeel", "Chelsea Finn",
            "Lerrel Pinto", "Ashish Kumar", "Jitendra Malik"
        ]
        self.important_venues = [
            "ICML", "NeurIPS", "ICLR", "RSS", "CoRL", "ICRA", "IROS"
        ]
        self.important_labs = [
            "Meta AI", "Google Research", "DeepMind", "BAIR", "Stanford REAL",
            "CMU RED", "MIT CSAIL"
        ]
        
    def fetch_all_content(self) -> List[Dict[Any, Any]]:
        """Fetch content using aggregated search approach with focus on recent updates."""
        all_content = []
        
        # Fetch arXiv papers
        arxiv_papers = self._fetch_arxiv_papers()
        all_content.extend(arxiv_papers)
        
        # Fetch from important labs' websites
        lab_content = self._fetch_lab_content()
        all_content.extend(lab_content)
        
        # Fetch GitHub repositories
        github_repos = self._fetch_github_repos()
        all_content.extend(github_repos)
        
        # Calculate impact scores
        for item in all_content:
            item['impact_score'] = self._calculate_impact_score(item)
        
        return all_content
        
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

    def _calculate_impact_score(self, item: Dict[Any, Any]) -> float:
        """Calculate impact score based on various metrics with emphasis on content value."""
        score = 0.0
        
        # Author impact (0-3 points)
        if any(author in self.important_authors for author in item.get('authors', [])):
            score += 3.0
            
        # Venue impact (0-2 points)
        if any(venue in item.get('description', '') for venue in self.important_venues):
            score += 2.0
            
        # Lab/Institution impact (0-2 points)
        if any(lab in item.get('description', '') for lab in self.important_labs):
            score += 2.0
            
        # Recency impact (0-1 points)
        if 'published_date' in item:
            days_old = (datetime.now() - item['published_date']).days
            recency_score = max(0, 1 - (days_old / 365))  # Linear decay over a year
            score += recency_score
            
        # GitHub stars impact (0-2 points)
        if 'metrics' in item and 'stars' in item['metrics']:
            stars = item['metrics']['stars']
            stars_score = min(2.0, stars / 1000)  # Up to 2 points, scales with stars
            score += stars_score
        
        return score

    def _fetch_arxiv_papers(self) -> List[Dict[Any, Any]]:
        search_queries = [
            'ti:"embodied ai" OR ti:"world model" OR ti:"foundation model" robotics',
            'ti:"physical intelligence" OR ti:"humanoid" OR ti:"manipulation"',
            'cat:cs.RO AND (ti:"learning" OR ti:"neural" OR ti:"deep")'
        ]
        
        papers = []
        for query in search_queries:
            search = arxiv.Search(
                query=query,
                max_results=100,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            for paper in search.results():
                # Check if paper is from important authors or venues
                is_important = any(author in self.important_authors for author in paper.authors)
                
                papers.append({
                    'title': paper.title,
                    'authors': [str(author) for author in paper.authors],
                    'description': paper.summary,
                    'links': [paper.pdf_url],
                    'type': 'research',
                    'published_date': paper.published,
                    'is_important': is_important
                })
        
        return papers

    def _fetch_lab_content(self) -> List[Dict[Any, Any]]:
        # Implementation to fetch from lab websites
        # This would require specific scrapers for each lab's website
        pass

    def _fetch_github_repos(self) -> List[Dict[Any, Any]]:
        # Implementation to fetch relevant GitHub repositories
        pass