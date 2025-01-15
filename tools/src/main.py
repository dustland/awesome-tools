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
    github_token = os.getenv("GITHUB_TOKEN")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    gpt_service = GPTService(os.getenv("OPENAI_API_KEY"))
    content_merger = ContentMerger("../README.md", gpt_service)
    git_manager = GitManager()
    content_fetcher = ContentFetcher(github_token, tavily_api_key)
    logger.info("All components initialized successfully")
    
    try:
        # Fetch content using aggregated search
        logger.info("Fetching content using aggregated search...")
        all_content = content_fetcher.fetch_all_content()
        logger.info(f"Found {len(all_content)} relevant items")
        
        # Sort content by impact score
        all_content.sort(key=lambda x: x.get('impact_score', 0), reverse=True)
        logger.info("Sorted content by impact score")
        
        # Log top items for visibility
        logger.info("\nTop 5 items by impact score:")
        for idx, item in enumerate(all_content[:5], 1):
            desc = item.get('description', '')[:100] + '...' if item.get('description') else 'No description'
            logger.info(f"{idx}. {item.get('title')} (Score: {item.get('impact_score', 0):.2f})")
            logger.info(f"   Type: {item.get('type')}")
            logger.info(f"   Stars: {item.get('metrics', {}).get('stars', 0)}")
            if item.get('citations'):
                logger.info(f"   Citations: {item.get('citations')}")
            if item.get('relevance_score'):
                logger.info(f"   Relevance: {item.get('relevance_score'):.2f}")
            logger.info(f"   Description: {desc}")
        
        # Prepare content for merging
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
        
        # Merge content, starting with highest impact
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
        logger.error(f"Error in main process: {e}")
        raise
    
    logger.info("Content update process completed")

if __name__ == "__main__":
    main() 