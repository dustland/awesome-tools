import os
from dotenv import load_dotenv
from awesome_updater.core.github_client import GitHubClient
from awesome_updater.core.content_merger import ContentMerger
from utils.gpt_service import GPTService
from awesome_updater.core.git_manager import GitManager
from awesome_updater.core.content_fetcher import ContentFetcher
from utils.config import Config
from utils.logger import logger

# Load environment variables from .env file
load_dotenv()


def initialize_components(config: Config):
    """Initialize all necessary components and services."""
    logger.info("Initializing components...")
    
    github_token = os.getenv("GITHUB_TOKEN")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not all([github_token, tavily_api_key, openai_api_key]):
        missing = [var for var, val in [("GITHUB_TOKEN", github_token), ("TAVILY_API_KEY", tavily_api_key), ("OPENAI_API_KEY", openai_api_key)] if not val]
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        raise ValueError("Required environment variables are not set.")

    try:
        logger.info("Initializing GPT service...")
        gpt_service = GPTService(openai_api_key)
        
        logger.info("Initializing Git manager...")
        git_manager = GitManager(target_repo_url="https://github.com/dustland/awesome-embodied-ai")
        
        logger.info("Initializing content merger...")
        content_merger = ContentMerger(git_manager.get_readme_path(), gpt_service)
        
        logger.info("Initializing content fetcher...")
        content_fetcher = ContentFetcher(github_token, tavily_api_key)
        
        logger.info("All components initialized successfully")
        return gpt_service, git_manager, content_merger, content_fetcher
    except Exception as e:
        logger.error(f"Error initializing components: {str(e)}")
        raise

def fetch_and_process_content(content_fetcher: ContentFetcher):
    """Fetch, sort, and format content."""
    logger.info("Fetching content using aggregated search...")
    try:
        all_content = content_fetcher.fetch_all_content()
        logger.info(f"Found {len(all_content)} relevant items")
        
        if not all_content:
            logger.info("No content found.")
            return []
            
        # Sort content by impact score
        all_content.sort(key=lambda x: x.get('impact_score', 0), reverse=True)
        logger.info("Sorted content by impact score")
        
        # Log top 5 items
        logger.info("\nTop 5 items by impact score:")
        for i, item in enumerate(all_content[:5], 1):
            logger.info(f"{i}. {item.get('title', 'No title')} (Score: {item.get('impact_score', 0):.2f})")
            logger.info(f"   Type: {item.get('type', 'unknown')}")
            logger.info(f"   Stars: {item.get('metrics', {}).get('stars', 0)}")
            if 'citations' in item:
                logger.info(f"   Citations: {item['citations']}")
            if 'relevance_score' in item:
                logger.info(f"   Relevance: {item['relevance_score']:.2f}")
            logger.info(f"   Description: {item.get('description', '')[:100]}...")

        logger.info("\nPreparing content for merging...")
        formatted_content = []
        for item in all_content:
            if item.get('type') == 'research':
                paper_link = next((link for link in item.get('links', []) if 'arxiv.org' in link or 'doi.org' in link), '')
                code_link = next((link for link in item.get('links', []) if 'github.com' in link), '')
                formatted_content.append(
                    f"| {item.get('title')} | {item.get('description', '')} | "
                    f"[Paper]({paper_link}) | [Code]({code_link}) |"
                )
            else:
                main_link = item.get('links', [''])[0]
                stars = item.get('metrics', {}).get('stars', 0)
                formatted_content.append(
                    f"- [{item.get('title')}]({main_link}) - {item.get('description', '')} "
                    f"[⭐{stars}]"
                )
        
        logger.info("Content prepared for merging")
        return formatted_content
        
    except Exception as e:
        logger.error(f"Error fetching or processing content: {str(e)}")
        raise

def update_readme(content_merger: ContentMerger, formatted_content: list):
    """Merge new content into the README file."""
    logger.info("\nMerging content with existing README...")
    if not formatted_content:
        logger.info("No formatted content to merge.")
        return False
    
    try:
        if content_merger.merge_content("\n".join(formatted_content)):
            logger.info("Successfully merged formatted content into README")
            return True
        else:
            logger.info("No new content added during merge operation.")
            return False
    except Exception as e:
        logger.error(f"Error merging content: {str(e)}")
        raise

def commit_and_push_changes(git_manager: GitManager, has_updates: bool):
    """Commit and push changes if updates were made."""
    if not has_updates:
        logger.info("\nNo updates were merged, skipping commit.")
        return

    try:
        if git_manager.has_changes():
            logger.info("\nChanges detected in README, committing and pushing...")
            commit_message = "Update awesome list with new high-impact resources"
            git_manager.commit_and_push(commit_message)
            logger.info(f"Successfully committed and pushed changes with message: '{commit_message}'")
        else:
            logger.info("\nREADME merge reported updates, but no changes detected by Git. Skipping commit.")
    except Exception as e:
        logger.error(f"Error committing or pushing changes: {str(e)}")
        raise

def main():
    logger.info("=== Starting Awesome Embodied AI content update process ===")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.load_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize components
        gpt_service, git_manager, content_merger, content_fetcher = initialize_components(config)
        
        # Fetch and process content
        formatted_content = fetch_and_process_content(content_fetcher)
        
        # Merge content into README
        readme_updated = update_readme(content_merger, formatted_content)
        
        # Commit and push changes if necessary
        commit_and_push_changes(git_manager, readme_updated)
        
        logger.info("\n=== Content update process completed successfully ===")

    except ValueError as ve: 
         logger.error(f"Initialization failed: {str(ve)}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during the update process: {str(e)}")

if __name__ == "__main__":
    main()