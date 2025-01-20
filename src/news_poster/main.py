import os
from dotenv import load_dotenv
from news_poster import NewsPoster
from utils.logger import logger

def main():
    # Load environment variables
    load_dotenv()
    
    # Get API keys from environment
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    twitter_api_key = os.getenv("TWITTER_API_KEY")
    twitter_api_secret = os.getenv("TWITTER_API_SECRET")
    twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    
    # Validate API keys
    required_keys = {
        "TAVILY_API_KEY": tavily_api_key,
        "TWITTER_API_KEY": twitter_api_key,
        "TWITTER_API_SECRET": twitter_api_secret,
        "TWITTER_ACCESS_TOKEN": twitter_access_token,
        "TWITTER_ACCESS_TOKEN_SECRET": twitter_access_token_secret
    }
    
    missing_keys = [key for key, value in required_keys.items() if not value]
    if missing_keys:
        logger.error(f"Missing required API keys: {', '.join(missing_keys)}")
        return
    
    try:
        # Initialize news poster
        news_poster = NewsPoster(
            tavily_api_key=tavily_api_key,
            twitter_api_key=twitter_api_key,
            twitter_api_secret=twitter_api_secret,
            twitter_access_token=twitter_access_token,
            twitter_access_token_secret=twitter_access_token_secret
        )
        
        # Run the news posting process
        logger.info("Starting news posting process...")
        success = news_poster.run()
        
        if success:
            logger.info("Successfully posted news to Twitter")
        else:
            logger.warning("Failed to post some or all news items")
            
    except Exception as e:
        logger.error(f"Error in news posting process: {e}")
        raise

if __name__ == "__main__":
    main() 