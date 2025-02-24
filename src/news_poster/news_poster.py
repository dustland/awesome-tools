from typing import List, Dict
import tweepy
from tavily import TavilyClient
from utils.logger import logger
from utils.gpt_service import GPTService

class NewsPoster:
    def __init__(self, tavily_api_key: str, twitter_api_key: str, twitter_api_secret: str, 
                 twitter_access_token: str, twitter_access_token_secret: str, openai_api_key: str):
        self.tavily_client = TavilyClient(tavily_api_key)
        logger.debug(f"Initializing GPT service with key starting with: {openai_api_key[:8] if openai_api_key else 'None'}")
        self.gpt_service = GPTService(openai_api_key)
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
                search_depth="advanced",  # Use news search
                topic="news",
                include_domains=[
                    'techcrunch.com', 'wired.com', 'ieee.org', 'nature.com', 
                    'science.org', 'robotics.org', 'technologyreview.com',
                    'twitter.com', 'facebook.com', 'linkedin.com'  # Add social media platforms
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
            # Return only the top 1 result to avoid rate limits
            logger.debug(f"Found {len(news_items)} news items, selecting top 1")
            return news_items[:1]
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []
    
    def generate_attractive_text(self, title: str) -> str:
        """Generate a more attractive version of the article title."""
        return self.gpt_service.generate_attractive_title(title)

    def generate_engaging_comment(self, tweet_text: str, tweet_url: str) -> str:
        """Generate an engaging and insightful comment for a tweet."""
        prompt = f"""Generate an engaging and insightful comment for this tweet about Embodied AI:

Tweet: {tweet_text}
URL: {tweet_url}

Requirements:
1. Be insightful and add value to the discussion
2. Highlight a key point or implication
3. Use professional and technical language
4. Keep it concise (max 200 characters)
5. Include relevant technical terms (e.g., Embodied AI, robotics)
6. Make it engaging to encourage discussion
7. Don't be overly promotional
8. Don't use hashtags (they'll be added separately)

The comment should demonstrate expertise and encourage engagement with the original tweet."""

        try:
            comment = self.gpt_service.complete(
                prompt=prompt,
                system_prompt="You are an expert in Embodied AI and robotics, providing insightful technical commentary.",
                max_tokens=100,
                temperature=0.7
            )
            return comment if comment else "Fascinating insights on embodied AI! Looking forward to seeing more developments in this space."
        except Exception as e:
            logger.error(f"Failed to generate comment: {e}")
            return "Fascinating insights on embodied AI! Looking forward to seeing more developments in this space."
        
    def post_to_twitter(self, news_items: List[Dict]) -> bool:
        """Post news items to Twitter/X."""
        success = True
        try:
            for item in news_items:
                # Check if this is a tweet (URL contains twitter.com or x.com)
                is_tweet = 'twitter.com' in item['url'].lower() or 'x.com' in item['url'].lower()
                
                if is_tweet:
                    # Generate an engaging comment
                    comment = self.generate_engaging_comment(item['title'], item['url'])
                    tweet = f"{comment}\n\n🔗 {item['url']}\n\n#EmbodiedAI #Robotics #AI"
                else:
                    # Generate a more attractive tweet text for non-tweet content
                    attractive_title = self.generate_attractive_text(item['title'])
                    tweet = f"📰 {attractive_title}\n\n🔗 {item['url']}\n\n#EmbodiedAI #Robotics #AI"
                
                # Ensure tweet is within character limit
                if len(tweet) > 280:
                    tweet = tweet[:277] + "..."
                
                try:
                    # Try v2 API first
                    response = self.twitter_client.create_tweet(text=tweet)
                    tweet_id = response.data['id']
                    logger.info(f"Posted {'comment' if is_tweet else 'tweet'} about: {item['title']}")
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
                            logger.info(f"Posted {'comment' if is_tweet else 'tweet'} (v1.1) about: {item['title']}")
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
    
    def fetch_top_tweets(self) -> List[Dict]:
        """Fetch top tweets about Embodied AI using Tavily."""
        try:
            response = self.tavily_client.search(
                query="embodied AI robotics",
                search_depth="advanced",
                include_domains=['twitter.com', 'x.com'],
                max_results=5  # Get more results to filter the best ones
            )
            
            # Filter and sort results
            tweet_items = []
            for item in response.get('results', []):
                # Calculate a relevance score
                relevance = item.get('score', 0)
                if 'embodied' in (item.get('content', '') + item.get('title', '')).lower():
                    relevance *= 1.5
                if 'robot' in (item.get('content', '') + item.get('title', '')).lower():
                    relevance *= 1.2
                
                # Extract tweet ID from URL
                url = item.get('url', '')
                tweet_id = url.split('/')[-1].split('?')[0] if url else None
                
                if tweet_id and tweet_id.isdigit():
                    tweet_items.append({
                        'title': item.get('title'),
                        'url': url,
                        'tweet_id': tweet_id,
                        'published_date': item.get('published_date'),
                        'relevance': relevance
                    })
            
            # Sort by relevance and get top 3
            tweet_items.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            # Return only the top 1 result to avoid rate limits
            logger.debug(f"Found {len(tweet_items)} tweet items, selecting top 1")
            return tweet_items[:1]
            
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return []

    def engage_with_tweets(self) -> bool:
        """Find and engage with relevant tweets about Embodied AI."""
        try:
            # Fetch relevant tweets
            tweets = self.fetch_top_tweets()
            if not tweets:
                logger.warning("No relevant tweets found")
                return False

            logger.info(f"Found {len(tweets)} relevant tweets to engage with")
            success = True

            for tweet in tweets:
                try:
                    # Generate engaging comment
                    comment = self.generate_engaging_comment(tweet['title'], tweet['url'])
                    
                    # Create comment tweet
                    tweet_text = f"{comment}\n\n#EmbodiedAI #Robotics #AI"
                    if len(tweet_text) > 280:
                        tweet_text = tweet_text[:277] + "..."

                    try:
                        # Post comment using v2 API
                        response = self.twitter_client.create_tweet(
                            text=tweet_text,
                            in_reply_to_tweet_id=tweet['tweet_id']  # This makes it a reply
                        )
                        tweet_id = response.data['id']
                        
                        # Retweet the original tweet
                        self.twitter_client.retweet(tweet['tweet_id'])
                        
                        # Like the original tweet
                        self.twitter_client.like(tweet['tweet_id'])
                        
                        logger.info(f"Engaged with tweet: {tweet['url']}")
                        logger.debug(f"Comment ID: {tweet_id}")
                        
                    except Exception as e:
                        if "duplicate" in str(e).lower():
                            logger.warning(f"Already engaged with tweet: {tweet['url']}")
                            continue
                        else:
                            logger.error(f"Failed to engage with tweet: {e}")
                            success = False
                            
                except Exception as e:
                    logger.error(f"Error processing tweet {tweet['url']}: {e}")
                    success = False
                    continue

            return success

        except Exception as e:
            logger.error(f"Error in tweet engagement process: {e}")
            return False

    def run(self) -> bool:
        """Run both news posting and tweet engagement."""
        news_success = self.post_to_twitter(self.fetch_top_news())
        tweet_success = self.engage_with_tweets()
        return news_success and tweet_success 