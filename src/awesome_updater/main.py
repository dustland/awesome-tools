import os
from dotenv import load_dotenv
from awesome_updater.core.github_client import GitHubClient
from awesome_updater.core.content_merger import ContentMerger
from awesome_updater.core.gpt_service import GPTService
from awesome_updater.core.git_manager import GitManager
from awesome_updater.core.content_fetcher import ContentFetcher
from utils.config import Config
from utils.logger import logger

# Load environment variables from .env file
load_dotenv()

def main():
    logger.info("=== Starting Awesome Embodied AI content update process ===")
    
    # Load configuration
    logger.info("Loading configuration...")
    config = Config.load_config()
    logger.info("Configuration loaded successfully")
    
    # Initialize components
    logger.info("Initializing components...")
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        return
        
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        logger.error("TAVILY_API_KEY environment variable not set")
        return
        
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return
    
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
    except Exception as e:
        logger.error(f"Error initializing components: {str(e)}")
        return
    
    # Fetch content
    logger.info("Fetching content using aggregated search...")
    try:
        all_content = content_fetcher.fetch_all_content()
        logger.info(f"Found {len(all_content)} relevant items")
        
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
            
    except Exception as e:
        logger.error(f"Error fetching content: {str(e)}")
        return
    
    # Prepare content for merging
    try:
        logger.info("\nPreparing content for merging...")
        formatted_content = []
        for item in all_content:
            # Format content in the expected table structure
            if item.get('type') == 'research':
                paper_link = next((link for link in item.get('links', []) if 'arxiv.org' in link or 'doi.org' in link), '')
                code_link = next((link for link in item.get('links', []) if 'github.com' in link), '')
                formatted_content.append(
                    f"| {item.get('title')} | {item.get('description', '')} | "
                    f"[Paper]({paper_link}) | [Code]({code_link}) |"
                )
            else:
                # Format as a list item for tools, products, etc.
                main_link = item.get('links', [''])[0]
                stars = item.get('metrics', {}).get('stars', 0)
                formatted_content.append(
                    f"- [{item.get('title')}]({main_link}) - {item.get('description', '')} "
                    f"[⭐{stars}]"
                )
        
        logger.info("Content prepared for merging")
        
    except Exception as e:
        logger.error(f"Error preparing content for merging: {str(e)}")
        return
    
    # Merge content
    try:
        logger.info("\nMerging content with existing README...")
        has_updates = False
        if formatted_content:
            if content_merger.merge_content("\n".join(formatted_content)):
                logger.info("Successfully merged formatted content")
                has_updates = True
            else:
                logger.info("No new content to merge")
        
        # Commit and push changes
        if has_updates and git_manager.has_changes():
            logger.info("\nChanges detected, committing and pushing...")
            git_manager.commit_and_push("Update awesome list with new high-impact resources")
        else:
            logger.info("\nNo changes detected, skipping commit")
            
    except Exception as e:
        logger.error(f"Error updating content: {str(e)}")
        return
        
    logger.info("\n=== Content update process completed successfully ===")

if __name__ == "__main__":
    main()