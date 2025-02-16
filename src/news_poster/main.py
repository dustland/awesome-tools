import os
from pathlib import Path
from dotenv import load_dotenv
from utils.logger import logger
from news_poster.news_poster import NewsPoster

def main():
    """Main function to run the news posting process."""
    try:
        # Try multiple environment sources
        # 1. Check system environment variables first
        # 2. Try local .env file as fallback for development
        env_loaded = False
        
        # Check if variables are already set in system environment
        if any(os.getenv(var) for var in ['OPENAI_API_KEY', 'TAVILY_API_KEY', 'TWITTER_API_KEY']):
            logger.debug("Found environment variables in system environment")
            env_loaded = True
        
        # Try loading from .env file as fallback
        if not env_loaded:
            env_path = Path(__file__).resolve().parents[2] / '.env'
            logger.debug(f"Looking for .env file at: {env_path}")
            if env_path.exists():
                logger.debug(f"Found .env file at: {env_path}")
                load_dotenv(env_path)
                env_loaded = True
            else:
                logger.debug(f"No .env file found at {env_path}")
        
        if not env_loaded:
            logger.error("Could not load environment variables from any source")
            return 1
            
        # Debug: Print first few characters of each env var
        logger.debug("Environment variables loaded:")
        for var_name in ['OPENAI_API_KEY', 'TAVILY_API_KEY', 'TWITTER_API_KEY']:
            value = os.getenv(var_name)
            if value:
                logger.debug(f"{var_name}: {value[:8]}...")
            else:
                logger.debug(f"{var_name}: Not found")
        
        # Verify required environment variables
        required_vars = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'TAVILY_API_KEY': os.getenv('TAVILY_API_KEY'),
            'TWITTER_API_KEY': os.getenv('TWITTER_API_KEY'),
            'TWITTER_API_SECRET': os.getenv('TWITTER_API_SECRET'),
            'TWITTER_ACCESS_TOKEN': os.getenv('TWITTER_ACCESS_TOKEN'),
            'TWITTER_ACCESS_TOKEN_SECRET': os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        }
        
        missing_vars = [key for key, value in required_vars.items() if not value]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return 1
            
        logger.debug("Environment variables loaded successfully")
        for key, value in required_vars.items():
            logger.debug(f"{key} length: {len(value) if value else 0}")
        
        # Initialize news poster
        news_poster = NewsPoster(
            tavily_api_key=required_vars['TAVILY_API_KEY'],
            twitter_api_key=required_vars['TWITTER_API_KEY'],
            twitter_api_secret=required_vars['TWITTER_API_SECRET'],
            twitter_access_token=required_vars['TWITTER_ACCESS_TOKEN'],
            twitter_access_token_secret=required_vars['TWITTER_ACCESS_TOKEN_SECRET'],
            openai_api_key=required_vars['OPENAI_API_KEY']
        )
        
        logger.info("Starting news posting process...")
        
        # Run the news posting process
        if news_poster.run():
            logger.info("Successfully posted news to Twitter")
            return 0
        else:
            logger.warning("Failed to post some or all news items")
            return 1
            
    except Exception as e:
        logger.error(f"Error in news posting process: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 