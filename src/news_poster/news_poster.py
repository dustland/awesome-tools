from typing import List, Dict
import tweepy
from tavily import TavilyClient
from utils.logger import logger

class NewsPoster:
    def __init__(self, tavily_api_key: str, twitter_api_key: str, twitter_api_secret: str, 
                 twitter_access_token: str, twitter_access_token_secret: str):
        self.tavily_client = TavilyClient(tavily_api_key)
        self.twitter_client = tweepy.Client(
            consumer_key=twitter_api_key,
            consumer_secret=twitter_api_secret,
            access_token=twitter_access_token,
            access_token_secret=twitter_access_token_secret
        )
        
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
                max_results=10,  # Get more results to filter the best ones
                sort_by="relevance"
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
        try:
            for item in news_items:
                # Create tweet text
                tweet = f"📰 {item['title']}\n\n🔗 {item['url']}\n\n#EmbodiedAI #Robotics #AI"
                
                # Ensure tweet is within character limit
                if len(tweet) > 280:
                    tweet = tweet[:277] + "..."
                
                # Post tweet
                self.twitter_client.create_tweet(text=tweet)
                logger.info(f"Posted tweet about: {item['title']}")
            
            return True
            
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