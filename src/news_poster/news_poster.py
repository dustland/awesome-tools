from typing import List, Dict
import tweepy
from tavily import TavilyClient
from utils.logger import logger

class NewsPoster:
    def __init__(self, tavily_api_key: str, twitter_api_key: str, twitter_api_secret: str, 
                 twitter_access_token: str, twitter_access_token_secret: str):
        self.tavily_client = TavilyClient(tavily_api_key)
        logger.debug(f"Initializing Twitter client with credentials:")
        logger.debug(f"API Key length: {len(twitter_api_key)}")
        logger.debug(f"API Secret length: {len(twitter_api_secret)}")
        logger.debug(f"Access Token length: {len(twitter_access_token)}")
        logger.debug(f"Access Token Secret length: {len(twitter_access_token_secret)}")
        
        try:
            # First, try to get a bearer token
            auth = tweepy.OAuthHandler(twitter_api_key, twitter_api_secret)
            auth.set_access_token(twitter_access_token, twitter_access_token_secret)
            
            # Create API v1.1 instance
            self.twitter_api = tweepy.API(auth)
            
            # Create v2 client with bearer token
            self.twitter_client = tweepy.Client(
                consumer_key=twitter_api_key,
                consumer_secret=twitter_api_secret,
                access_token=twitter_access_token,
                access_token_secret=twitter_access_token_secret,
                wait_on_rate_limit=True
            )
            
            # Test the credentials using v1.1 API first
            try:
                me_v1 = self.twitter_api.verify_credentials()
                logger.debug(f"Successfully authenticated with v1.1 API as: {me_v1.screen_name}")
            except Exception as e:
                logger.warning(f"V1.1 API authentication failed: {str(e)}")
            
            # Then test v2 credentials
            try:
                me_v2 = self.twitter_client.get_me()
                logger.debug(f"Successfully authenticated with v2 API as: {me_v2.data.username}")
            except Exception as e:
                logger.warning(f"V2 API authentication failed: {str(e)}")
                # If both authentications fail, raise the error
                if not hasattr(self, 'twitter_api'):
                    raise
            
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            raise
        
    def fetch_top_news(self) -> List[Dict]:
        """Fetch top 3 news about Embodied AI using Tavily."""
        try:
            response = self.tavily_client.search(
                query="embodied AI robotics latest news and developments",
                search_depth="news",  # Use news search
                include_domains=[
                    'techcrunch.com', 'wired.com', 'ieee.org', 'nature.com', 
                    'science.org', 'robotics.org', 'technologyreview.com'
                ],
                max_results=10  # Get more results to filter the best ones
            )
            
            # Filter and sort results
            news_items = []
            for item in response.get('results', []):
                # Calculate a simple relevance score
                relevance = item.get('score', 0)
                if 'embodied' in (item.get('content', '') + item.get('title', '')).lower():
                    relevance *= 1.5
                if 'robot' in (item.get('content', '') + item.get('title', '')).lower():
                    relevance *= 1.2
                    
                news_items.append({
                    'title': item.get('title'),
                    'url': item.get('url'),
                    'published_date': item.get('published_date'),
                    'relevance': relevance
                })
            
            # Sort by relevance and get top 3
            news_items.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            return news_items[:3]
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []
    
    def post_to_twitter(self, news_items: List[Dict]) -> bool:
        """Post news items to Twitter/X."""
        success = True
        try:
            for item in news_items:
                # Create tweet text
                tweet = f"📰 {item['title']}\n\n🔗 {item['url']}\n\n#EmbodiedAI #Robotics #AI"
                
                # Ensure tweet is within character limit
                if len(tweet) > 280:
                    tweet = tweet[:277] + "..."
                
                try:
                    # Try v2 API first
                    response = self.twitter_client.create_tweet(text=tweet)
                    tweet_id = response.data['id']
                    logger.info(f"Posted tweet (v2) about: {item['title']}")
                except Exception as e:
                    error_msg = str(e).lower()
                    if "duplicate" in error_msg:
                        logger.warning(f"Skipping duplicate tweet: {item['title']}")
                        continue
                    elif "403 forbidden" in error_msg:
                        logger.error("Twitter API access level insufficient. Please upgrade to Pro/Enterprise access level.")
                        return False
                    else:
                        logger.warning(f"V2 API failed, trying v1.1: {str(e)}")
                        try:
                            # Fallback to v1.1 API
                            status = self.twitter_api.update_status(tweet)
                            tweet_id = status.id
                            logger.info(f"Posted tweet (v1.1) about: {item['title']}")
                        except Exception as e1:
                            if "duplicate" in str(e1).lower():
                                logger.warning(f"Skipping duplicate tweet: {item['title']}")
                                continue
                            else:
                                logger.error(f"Both APIs failed to post tweet: {str(e1)}")
                                success = False
                
                logger.debug(f"Tweet ID: {tweet_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}")
            return False
    
    def run(self) -> bool:
        """Fetch news and post to Twitter."""
        news_items = self.fetch_top_news()
        if not news_items:
            logger.warning("No news items found")
            return False
            
        logger.info(f"Found {len(news_items)} news items")
        for item in news_items:
            logger.info(f"- {item['title']}")
            
        return self.post_to_twitter(news_items) 