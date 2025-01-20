import os
from typing import Dict, List, Optional
import arxiv
import requests
from tavily import Client
from utils.logger import logger
from datetime import datetime
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
        """Fetch content using aggregated search approach."""
        all_content = []
        
        # Define search queries for different content types
        searches = [
            {
                'query': 'embodied AI humanoid robotics research papers with github implementation',
                'type': 'research',
                'search_type': 'research'  # Tavily research search
            },
            {
                'query': 'embodied AI robotics simulator open source tools github',
                'type': 'tools',
                'search_type': 'tech'  # Tavily tech search
            },
            {
                'query': 'embodied AI humanoid robotics companies and products',
                'type': 'product',
                'search_type': 'news'  # Tavily news search for recent products
            }
        ]
        
        for search in searches:
            try:
                # 1. Search using Tavily API
                if self.tavily_client:
                    logger.info(f"Searching using Tavily API for {search['query']}...")
                    tavily_results = self._tavily_search(
                        search['query'], 
                        search['search_type'],
                        search['type']
                    )
                    all_content.extend(tavily_results)
                
                # 2. Search GitHub directly
                github_results = self._github_search(search['query'])
                all_content.extend(self._process_github_results(github_results, search['type']))
                
                # 3. Search arXiv for research papers
                if search['type'] == 'research':
                    arxiv_results = self._arxiv_search(search['query'])
                    all_content.extend(arxiv_results)
                
            except Exception as e:
                logger.error(f"Error in search {search['type']}: {e}")
        
        # Enrich all content with metrics and remove duplicates
        enriched_content = []
        seen_urls = set()
        
        for item in all_content:
            if not any(url in seen_urls for url in item.get('links', [])):
                enriched_item = self._enrich_with_metrics(item)
                enriched_content.append(enriched_item)
                seen_urls.update(item.get('links', []))
        
        return enriched_content

    def _tavily_search(self, query: str, search_type: str, content_type: str) -> List[Dict]:
        """Search using Tavily API."""
        if not self.tavily_client:
            return []
        
        try:
            # Use Tavily's search with specific search types
            response = self.tavily_client.search(
                query=query,
                search_depth=search_type,
                include_domains=['github.com', 'arxiv.org', 'paperswithcode.com'],
                max_results=20
            )
            
            results = []
            for item in response.get('results', []):
                # Extract GitHub URLs if present
                github_links = re.findall(
                    r'https?://github\.com/[^/\s]+/[^/\s]+',
                    item.get('content', '') + item.get('url', '')
                )
                
                # For research content, look for citation information
                citations = 0
                if content_type == 'research' and 'cited by' in item.get('content', '').lower():
                    citation_match = re.search(r'cited by (\d+)', item.get('content', '').lower())
                    if citation_match:
                        citations = int(citation_match.group(1))
                
                if github_links or content_type == 'product':
                    results.append({
                        'title': item.get('title'),
                        'description': item.get('content'),
                        'links': [item.get('url')] + github_links,
                        'type': content_type,
                        'citations': citations if content_type == 'research' else 0,
                        'relevance_score': item.get('score', 0)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
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
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get('items', [])
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
            
            response = requests.get(api_url, headers=self.headers)
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
        """Calculate impact score based on various metrics."""
        metrics = content.get('metrics', {})
        
        # Base score from GitHub metrics
        github_score = (
            metrics.get('stars', 0) * 0.5 +  # Weight stars more heavily
            metrics.get('forks', 0) * 0.3
        )
        
        # Get current time in UTC
        now = datetime.now(pytz.UTC)
        
        # Age factor (newer content gets a boost)
        if metrics.get('created_at'):
            created_at = datetime.fromisoformat(metrics['created_at'].replace('Z', '+00:00'))
            age_days = (now - created_at).days
            age_factor = max(0.5, 1 - (age_days / 365))  # Decay over a year, but maintain at least 0.5
        else:
            age_factor = 0.5
        
        # Activity factor (recently updated content gets a boost)
        if metrics.get('updated_at'):
            updated_at = datetime.fromisoformat(metrics['updated_at'].replace('Z', '+00:00'))
            last_update_days = (now - updated_at).days
            activity_factor = max(0.5, 1 - (last_update_days / 90))  # Decay over 90 days, but maintain at least 0.5
        else:
            activity_factor = 0.5
        
        # Citations/references factor (if available)
        citations = content.get('citations', 0)
        citations_factor = min(1 + (citations / 100), 2)  # Cap at 2x boost
        
        # Tavily relevance score (if available)
        relevance_boost = content.get('relevance_score', 1.0)
        
        # Type-specific boosts
        type_boost = {
            'research': 1.2,  # Boost research papers with code
            'tools': 1.5,     # Boost tools and frameworks
            'product': 1.0    # Standard weight for products
        }.get(content.get('type', ''), 1.0)
        
        # Combine factors
        impact_score = github_score * age_factor * activity_factor * citations_factor * type_boost * relevance_boost
        return impact_score 