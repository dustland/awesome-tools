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
    logger.info("All components initialized successfully")
    
    try:
        # Search for relevant repositories
        logger.info("Searching for relevant repositories...")
        repos = github_client.discover_repos("awesome+embodied+ai+robotics")
        logger.info(f"Found {len(repos)} relevant repositories")
        
        # Process each repository
        for idx, repo in enumerate(repos, 1):
            owner = repo["owner"]["login"]
            name = repo["name"]
            logger.info(f"Processing repository {idx}/{len(repos)}: {owner}/{name}")
            
            # Fetch and parse README
            logger.info(f"Fetching README from {owner}/{name}...")
            readme_content = github_client.get_readme_content(owner, name)
            if readme_content:
                logger.info(f"Successfully fetched README from {owner}/{name}")
                logger.info("Parsing README content...")
                parsed_sections = gpt_service.parse_and_format_readme(readme_content)
                logger.info(f"Successfully parsed README into {len(parsed_sections)} sections")
                
                # Merge content
                logger.info("Attempting to merge content...")
                if content_merger.merge_content(parsed_sections):
                    logger.info(f"Successfully merged content from {owner}/{name}")
                else:
                    logger.warning(f"No new content merged from {owner}/{name}")
            else:
                logger.warning(f"Failed to fetch README from {owner}/{name}")
        
        # Commit and push changes
        if git_manager.has_changes():
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