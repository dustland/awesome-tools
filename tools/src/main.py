import os
from dotenv import load_dotenv
from core.github_client import GitHubClient
from core.content_merger import ContentMerger
from core.gpt_service import GPTService
from core.git_manager import GitManager
from core.content_fetcher import ContentFetcher
from utils.config import Config
from utils.logger import logger

# Load environment variables from .env file
load_dotenv()

def main():
    logger.info("Starting Awesome Embodied AI content update process...")
    
    # Load configuration
    config = Config.load_config()
    logger.info("Configuration loaded successfully")
    
    # Initialize components
    logger.info("Initializing components...")
    github_client = GitHubClient(os.getenv("GITHUB_TOKEN"))
    gpt_service = GPTService(os.getenv("OPENAI_API_KEY"))
    content_merger = ContentMerger("README.md", gpt_service)
    git_manager = GitManager()
    content_fetcher = ContentFetcher()
    logger.info("All components initialized successfully")
    
    try:
        # Fetch content from multiple sources
        logger.info("Fetching content from multiple sources...")
        
        # 1. Fetch from GitHub repositories
        logger.info("Searching for relevant repositories...")
        repos = github_client.discover_repos("awesome+embodied+ai")
        logger.info(f"Found {len(repos)} relevant repositories")
        
        all_content = []
        
        # Process GitHub repositories
        for idx, repo in enumerate(repos, 1):
            owner = repo["owner"]["login"]
            name = repo["name"]
            logger.info(f"Processing repository {idx}/{len(repos)}: {owner}/{name}")
            
            readme_content = github_client.get_readme_content(owner, name)
            if readme_content:
                logger.info(f"Successfully fetched README from {owner}/{name}")
                all_content.append(readme_content)
            else:
                logger.warning(f"Failed to fetch README from {owner}/{name}")
        
        # 2. Fetch from other sources (arXiv, conferences, blogs, labs)
        logger.info("Fetching content from additional sources...")
        additional_content = content_fetcher.fetch_all_content()
        all_content.extend(additional_content)
        logger.info(f"Successfully fetched {len(additional_content)} items from additional sources")
        
        # Merge all content
        has_updates = False
        for content in all_content:
            logger.info("Attempting to merge content...")
            if content_merger.merge_content(content):
                logger.info("Successfully merged new content")
                has_updates = True
            else:
                logger.info("No new content to merge from this source")
        
        # Commit and push changes
        if has_updates and git_manager.has_changes():
            logger.info("Changes detected, committing and pushing...")
            git_manager.commit_and_push("Update awesome list with new resources")
        else:
            logger.info("No changes detected, skipping commit")
            
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise
    
    logger.info("Content update process completed")

if __name__ == "__main__":
    main() 