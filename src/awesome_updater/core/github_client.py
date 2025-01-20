from typing import List, Optional, Dict
import requests
from utils.logger import logger

class GitHubClient:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}"}
        self.base_url = "https://api.github.com"
    
    def discover_repos(self, query: str, per_page: int = 10) -> List[Dict]:
        """Discover relevant repositories using GitHub search."""
        url = f"{self.base_url}/search/repositories"
        params = {
            "q": query,
            "per_page": per_page,
            "sort": "stars",
            "order": "desc"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            logger.error(f"Failed to discover repositories: {e}")
            return []
    
    def fetch_readme(self, owner: str, repo: str) -> Optional[str]:
        """Fetch README content from a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/readme"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            content = response.json().get("content", "")
            return self._decode_content(content)
        except Exception as e:
            logger.error(f"Failed to fetch README for {owner}/{repo}: {e}")
            return None
    
    @staticmethod
    def _decode_content(content: str) -> str:
        """Decode base64 encoded content."""
        import base64
        return base64.b64decode(content).decode('utf-8') 