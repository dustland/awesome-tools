import arxiv
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from utils.logger import logger

class ContentFetcher:
    def __init__(self):
        self.sources = {
            'arxiv': self._fetch_arxiv,
            'conferences': self._fetch_conferences,
            'blogs': self._fetch_tech_blogs,
            'labs': self._fetch_lab_content
        }
    
    def fetch_all_content(self) -> List[str]:
        """Fetch content from all sources."""
        all_content = []
        
        for source_name, fetch_func in self.sources.items():
            try:
                logger.info(f"Fetching content from {source_name}...")
                content = fetch_func()
                all_content.extend(content)
                logger.info(f"Successfully fetched {len(content)} items from {source_name}")
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
        
        return all_content

    def _fetch_arxiv(self) -> List[str]:
        """Fetch relevant papers from arXiv."""
        search = arxiv.Search(
            query="title:embodied AND (title:AI OR title:intelligence OR title:robotics)",
            max_results=50,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        papers = []
        for result in search.results():
            paper_entry = (
                f"- [{result.title}]({result.entry_id}) - "
                f"{result.summary.split('.')[0]}. "
                f"[Paper]({result.pdf_url})"
            )
            papers.append(paper_entry)
        
        return papers

    def _fetch_conferences(self) -> List[str]:
        """Fetch papers from major robotics conferences."""
        conferences = {
            'ICRA': 'https://www.icra2024.org/papers',
            'RSS': 'http://www.roboticsconference.org/',
            'CoRL': 'https://www.corl2024.org/',
            'IROS': 'https://iros2024.org/'
        }
        
        papers = []
        for conf_name, url in conferences.items():
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                # Implementation depends on conference website structure
                # This is a placeholder for actual parsing logic
                papers.append(f"## {conf_name} Papers\n")
            except Exception as e:
                logger.error(f"Error fetching {conf_name} papers: {e}")
        
        return papers

    def _fetch_tech_blogs(self) -> List[str]:
        """Fetch content from major tech blogs."""
        blog_sources = {
            'OpenAI': 'https://openai.com/blog',
            'DeepMind': 'https://deepmind.com/blog',
            'NVIDIA': 'https://blogs.nvidia.com/ai-robotics',
            'Google AI': 'https://ai.googleblog.com/'
        }
        
        blog_posts = []
        for company, url in blog_sources.items():
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                # Implementation depends on blog structure
                # This is a placeholder for actual parsing logic
                blog_posts.append(f"## {company} Blog Posts\n")
            except Exception as e:
                logger.error(f"Error fetching {company} blog posts: {e}")
        
        return blog_posts

    def _fetch_lab_content(self) -> List[str]:
        """Fetch content from research lab websites."""
        labs = {
            'Stanford Robotics': 'https://robotics.stanford.edu/research',
            'Berkeley AI': 'https://bair.berkeley.edu/blog/',
            'MIT CSAIL': 'https://www.csail.mit.edu/research',
            'CMU Robotics': 'https://www.ri.cmu.edu/research/'
        }
        
        lab_content = []
        for lab_name, url in labs.items():
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                # Implementation depends on lab website structure
                # This is a placeholder for actual parsing logic
                lab_content.append(f"## {lab_name} Research\n")
            except Exception as e:
                logger.error(f"Error fetching {lab_name} content: {e}")
        
        return lab_content 