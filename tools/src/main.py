import os
from dotenv import load_dotenv
from core.github_client import GitHubClient
from core.content_merger import ContentMerger
from core.gpt_service import GPTService
from core.git_manager import GitManager
from utils.config import Config
from utils.logger import logger

# Load environment variables from .env file
load_dotenv()

def main():
    # Load configuration
    config = Config.load_config()
    
    # Initialize components
    github_client = GitHubClient(os.getenv("GITHUB_TOKEN"))
    gpt_service = GPTService(os.getenv("OPENAI_API_KEY"))
    content_merger = ContentMerger("README.md", gpt_service)
    git_manager = GitManager()
    
    try:
        # Search for relevant repositories
        repos = github_client.discover_repos("awesome+embodied+ai+robotics")
        
        # Process each repository
        for repo in repos:
            owner = repo["owner"]["login"]
            name = repo["name"]
            
            # Fetch and parse README
            readme_content = github_client.fetch_readme(owner, name)
            if readme_content:
                parsed_sections = gpt_service.parse_and_format_readme(readme_content)
                
                # Merge content
                if content_merger.merge_content(parsed_sections):
                    logger.info(f"Successfully merged content from {owner}/{name}")
        
        # Commit and push changes
        if git_manager.has_changes():
            git_manager.commit_and_push("Update awesome list with new resources")
            
    except Exception as e:
        logger.error(f"Error in main process: {e}")

if __name__ == "__main__":
    main() 