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
        logger.info(f"Initializing content fetcher with {len(config.content_sources)} sources...")
        content_fetcher = ContentFetcher(config.content_sources, config.github_token, gpt_service)
        logger.info("Content fetcher initialized.")
        
        logger.info("All components initialized successfully")
        return gpt_service, git_manager, content_merger, content_fetcher
    except Exception as e:
        logger.error(f"Error initializing components: {str(e)}")
        raise

def fetch_and_process_content(content_fetcher: ContentFetcher) -> list:
    """Fetches, processes (sorts, formats), and returns content."""
    logger.info("Fetching content using aggregated search...")
    try:
        all_content = content_fetcher.fetch_all_content()
        
        # Check for None or empty list right after fetching
        if not all_content:
            logger.info("No content found or returned from fetcher.")
            return []
            
        logger.info(f"Found {len(all_content)} relevant items initially.")

        # Sort content by relevance (assuming relevance score exists)
        all_content.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        logger.debug("Content sorted by relevance.")

        # Basic deduplication based on URL
        seen_urls = set()
        deduplicated_content = []
        for item in all_content:
            url = item.get('url')
            if url:
                if url not in seen_urls:
                    deduplicated_content.append(item)
                    seen_urls.add(url)
                else:
                    logger.debug(f"Skipping duplicate URL: {url}")
            else:
                deduplicated_content.append(item) 
                
        logger.info(f"Content deduplicated, {len(deduplicated_content)} items remaining.")

        # Format content for README
        formatted_content = []
        for item in deduplicated_content:
            title = item.get('title', 'No Title')
            url = item.get('url')
            line = f"- [{title}]({url})" if url else f"- {title}"
            formatted_content.append(line)
            
        logger.info("Content formatted for README.")
        return formatted_content
        
    except Exception as e:
        # Log the specific error encountered during fetching/processing
        logger.error(f"Error during content fetching or processing: {e}", exc_info=True) 
        # Return an empty list to gracefully handle the error downstream
        return []

def update_readme(content_merger: ContentMerger, formatted_content: list) -> bool:
    """Updates the README file with new content."""
    if not formatted_content:
        logger.info("No new formatted content to merge into README.")
        return False
        
    logger.info(f"Merging {len(formatted_content)} new items into README...")
    try:
        readme_path = content_merger.get_readme_path()
        if not readme_path or not os.path.exists(readme_path):
             logger.error("README file path not found or doesn't exist.")
             return False
        updated = content_merger.merge_content_into_readme(formatted_content)
        if updated:
            logger.info("README updated successfully.")
        else:
            logger.info("No changes made to README (content might already exist).")
        return updated
    except Exception as e:
        logger.error(f"Error merging content into README: {e}")
        return False

def commit_and_push_changes(git_manager: GitManager, has_updates: bool):
    """Commits and pushes changes if the README was updated."""
    if not has_updates:
        logger.info("No updates detected, skipping commit and push.")
        return

    logger.info("Updates detected, proceeding with commit and push...")
    try:
        commit_message = "Update awesome list with new high-impact resources"
        git_manager.commit(commit_message)
        git_manager.push()
        logger.info("Changes committed and pushed successfully.")
    except Exception as e:
        logger.error(f"Error during commit and push: {e}")


def main():
    logger.info("=== Starting Awesome Embodied AI content update process ===")
    # Load configuration
    logger.info("Loading configuration...")
    config = Config.load_config()
    logger.info("Configuration loaded successfully")
    
    gpt_service, git_manager, content_merger, content_fetcher = (None, None, None, None)
    try:
        # Initialize components
        gpt_service, git_manager, content_merger, content_fetcher = initialize_components(config)
        
        # Fetch and process content
        # The function now handles internal errors and returns []
        formatted_content = fetch_and_process_content(content_fetcher)
        
        # Merge content into README
        readme_updated = update_readme(content_merger, formatted_content) 
        
        # Commit and push changes if necessary
        commit_and_push_changes(git_manager, readme_updated)
        
        logger.info("\n=== Content update process completed successfully ===")

    except ValueError as ve: 
         logger.error(f"Initialization failed: {str(ve)}")
    except Exception as e:
        # Catch any other unexpected errors in the main flow
        logger.error(f"An unexpected error occurred in the main update process: {str(e)}", exc_info=True)
    finally:
        # Ensure git_manager temporary directory is cleaned up 
        if git_manager:
            logger.debug("Ensuring cleanup of GitManager's temporary directory.")
            # Assuming GitManager has a __del__ method for cleanup
            pass 

if __name__ == "__main__":
    main()