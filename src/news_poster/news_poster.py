from typing import List, Dict, Optional
import tweepy
from tavily import TavilyClient
from utils.logger import logger
from utils.gpt_service import GPTService
import random
import time

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
        self.user_id: Optional[str] = None # To store the bot's user ID
        
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
            
            # Then test v2 credentials and store user ID
            try:
                me_v2 = self.twitter_client.get_me()
                self.user_id = me_v2.data.id
                logger.debug(f"Successfully authenticated with v2 API as: {me_v2.data.username} (ID: {self.user_id})")
            except Exception as e:
                logger.warning(f"V2 API authentication failed: {str(e)}")
                # If both authentications fail, raise the error
                if not hasattr(self, 'twitter_api'):
                    raise
            
            if not self.user_id:
                 logger.warning("Could not determine bot's Twitter User ID via V2 API. Duplicate checking will be disabled.")

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
                max_results=15 # Get slightly more to allow for filtering duplicates
            )
            
            # Filter and sort results
            news_items = []
            seen_urls = set()
            for item in response.get('results', []):
                url = item.get('url')
                if not url or url in seen_urls: continue # Skip items without URL or duplicate URLs
                seen_urls.add(url)
                
                # Calculate a simple relevance score
                relevance = item.get('score', 0)
                content_lower = (item.get('content', '') + item.get('title', '')).lower()
                if 'embodied' in content_lower:
                    relevance *= 1.5
                if 'robot' in content_lower:
                    relevance *= 1.2
                    
                news_items.append({
                    'title': item.get('title'),
                    'url': url,
                    'published_date': item.get('published_date'),
                    'content': item.get('content'), # Keep content for similarity check
                    'relevance': relevance
                })
            
            # Sort by relevance
            news_items.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            logger.debug(f"Found {len(news_items)} unique news items initially.")
            # Return more items initially, duplicate check will filter later
            return news_items[:5] # Fetch top 5 potential items
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    def generate_attractive_text(self, title: str) -> str:
        """Generate a more attractive version of the article title using GPTService."""
        # Use the existing method in GPTService
        return self.gpt_service.generate_attractive_title(title)

    def generate_engaging_comment(self, tweet_text: str, tweet_url: str) -> str:
        """Generate an engaging and insightful comment for a tweet with human-like randomness."""
        
        personas = [
            "an AI enthusiast passionate about Embodied AI and Robotics",
            "a curious student exploring the latest in AI and robotics",
            "a thoughtful observer commenting on AI advancements",
            "an industry professional sharing insights on Embodied AI",
        ]
        tones = ["excited", "curious", "analytical", "impressed", "questioning", "thoughtful", "optimistic"]
        angles = [
            "ask a follow-up question", 
            "share a related thought or connection", 
            "briefly mention a potential implication", 
            "highlight a specific point you found interesting",
            "express agreement and add a small nuance"
        ]
        emojis = ["🤖", "✨", "🤔", "👍", "💡", "🚀", "👀"]

        system_persona = f"You are {random.choice(personas)}. You share insightful and engaging thoughts on Twitter about AI developments."
        chosen_tone = random.choice(tones)
        chosen_angle = random.choice(angles)
        use_emoji = random.random() < 0.3 # 30% chance of using an emoji
        chosen_emoji = random.choice(emojis) if use_emoji else ""

        prompt = f"""Here's a tweet I found:
Tweet Text: "{tweet_text}"
Tweet URL: {tweet_url}

Please write a thoughtful and engaging reply in a '{chosen_tone}' tone. Your reply should {chosen_angle}. 

Instructions:
- Sound human and natural.
- Use varied sentence structure.
- Add value or perspective, don't just summarize.
- Keep it concise for Twitter (under 260 characters).
- {f'Consider adding this emoji: {chosen_emoji}' if use_emoji else 'Do not use emojis for this reply.'}
- Ensure the reply is relevant to the tweet content.
"""
        
        try:
            comment = self.gpt_service.complete(
                prompt=prompt,
                system_prompt=system_persona,
                max_tokens=100, # Adjust max tokens for typical tweet length
                temperature=random.uniform(0.6, 0.9) # Add variability
            )
            return comment if comment else "Interesting point!" # Fallback comment
        except Exception as e:
            logger.error(f"Failed to generate engaging comment: {e}")
            return "Interesting perspective! Thanks for sharing." # Generic fallback

    def fetch_recent_posts_texts(self, count: int = 20) -> List[str]:
        """Fetch the text content of the bot's own recent tweets."""
        if not self.user_id:
            logger.warning("Cannot fetch recent posts: User ID not available.")
            return []
        
        try:
            logger.debug(f"Fetching last {count} tweets for user ID {self.user_id}...")
            response = self.twitter_client.get_users_tweets(id=self.user_id, max_results=max(5, min(count, 100)))
            if response.data:
                texts = [tweet.text for tweet in response.data]
                logger.debug(f"Fetched {len(texts)} recent tweet texts.")
                return texts
            else:
                logger.debug("No recent tweets found.")
                return []
        except Exception as e:
            logger.error(f"Error fetching recent tweets: {e}")
            return []

    def is_news_item_duplicate(self, news_item: Dict, recent_texts: List[str]) -> bool:
        """Use GPT to check if a news item is semantically similar to recent posts."""
        if not recent_texts:
            return False # Cannot be duplicate if no recent texts

        item_summary = f"Title: {news_item.get('title', '')}\nContent Snippet: {news_item.get('content', '')[:200]}..." # Use title and snippet
        
        # Limit number of recent texts to check against to keep prompt reasonable
        texts_to_check = "\n---\n".join(recent_texts[:10]) # Check against last 10

        prompt = f"""Analyze the following 'New Item' and the 'Recent Posts'. Determine if the core news story or event described in the 'New Item' is substantively the same as any of the 'Recent Posts', even if the source or wording is different.

New Item:
{item_summary}

Recent Posts:
{texts_to_check}

Is the core news story in the 'New Item' already covered in the 'Recent Posts'? Answer ONLY with 'Yes' or 'No'."""

        system_prompt = "You are an AI assistant helping to avoid posting duplicate news content. Analyze the semantic similarity of the core event described."

        try:
            response = self.gpt_service.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=10, # Yes/No answer
                temperature=0.1 # Low temp for consistent Yes/No
            )
            
            result = response.strip().lower() if response else "no"
            logger.debug(f"Duplicate check for '{news_item.get('title', '')[:50]}...': GPT response '{result}'")
            return result == 'yes'
        except Exception as e:
            logger.error(f"Error during GPT duplicate check: {e}")
            return False # Default to not duplicate on error

    def post_to_twitter(self, news_items: List[Dict]) -> bool:
        """Post news items to Twitter/X, checking for duplicates."""
        if not news_items:
            logger.info("No news items fetched to consider for posting.")
            return True

        # Fetch recent posts for duplicate checking (only if user_id is available)
        recent_posts_texts = self.fetch_recent_posts_texts() if self.user_id else []
        
        logger.info(f"Considering {len(news_items)} potential news items for posting...")
        success = True
        posted_count = 0
        max_posts_per_run = 3 # Limit posts per run to avoid spamming
        base_hashtags = ["#EmbodiedAI", "#Robotics", "#AI", "#ArtificialIntelligence"]
        optional_hashtags = ["#Tech", "#Innovation", "#FutureTech", "#MachineLearning", "#DeepLearning"]

        for item in news_items:
            if posted_count >= max_posts_per_run:
                logger.info(f"Reached max posts limit ({max_posts_per_run}), stopping further posts for this run.")
                break

            try:
                # Check for duplicates before processing further
                if recent_posts_texts and self.is_news_item_duplicate(item, recent_posts_texts):
                    logger.warning(f"Skipping duplicate news item (similar to recent posts): {item['title']}")
                    continue

                # Generate a more attractive title/opening
                attractive_title = self.generate_attractive_text(item['title'])
                
                # Randomly select 2-3 relevant hashtags
                num_hashtags = random.randint(2, 3)
                current_hashtags = random.sample(base_hashtags + optional_hashtags, num_hashtags)
                hashtags_str = " ".join(current_hashtags)

                # Construct tweet text (ensure it fits 280 chars)
                available_chars = 280 - (len(item['url']) + len(hashtags_str) + 5) 
                
                if len(attractive_title) > available_chars:
                    tweet_body = attractive_title[:available_chars-3] + "..."
                else:
                    tweet_body = attractive_title
                    
                tweet_text = f"{tweet_body}\n\n{item['url']}\n{hashtags_str}"
                
                # Add small random delay before posting
                time.sleep(random.uniform(2, 8))
                
                try:
                    # Post using v2 client
                    response = self.twitter_client.create_tweet(text=tweet_text)
                    tweet_id = response.data['id']
                    logger.info(f"Successfully posted tweet ID: {tweet_id} for news: {item['title']}")
                    logger.debug(f"Tweet Text: {tweet_text}")
                    posted_count += 1
                    # Add newly posted text to recent texts to avoid self-duplication within the same run
                    recent_posts_texts.insert(0, tweet_text) 
                except tweepy.errors.TweepyException as e:
                    if "duplicate content" in str(e).lower() or "status is a duplicate" in str(e).lower() or e.api_codes == [187]:
                        logger.warning(f"Skipping duplicate tweet via API error for: {item['title']}")
                        # Even if API catches duplicate, add to recent list to help semantic check
                        recent_posts_texts.insert(0, tweet_text) 
                        continue
                    else:
                        raise e 
                        
            except Exception as e:
                logger.error(f"Failed to process or post news item '{item.get('title', 'N/A')}': {e}")
                success = False
                continue 
        
        logger.info(f"Finished posting phase. Posted {posted_count} items.")
        return success

    def fetch_top_tweets(self) -> List[Dict]:
        """Fetch top tweets about Embodied AI using Tavily."""
        try:
            response = self.tavily_client.search(
                query="embodied AI robotics conversation OR discussion OR opinion",
                search_depth="advanced",
                topic="social", # Focus on social media mentions
                max_results=20 # Get more to find relevant ones
            )
            
            tweet_items = []
            urls_seen = set()
            
            for item in response.get('results', []):
                url = item.get('url', '')
                if not url or 'twitter.com' not in url or '/status/' not in url:
                    continue
                
                content_lower = (item.get('content', '') + item.get('title', '')).lower()
                if 'embodied' not in content_lower and 'robot' not in content_lower:
                     continue

                try:
                    tweet_id = url.split('/status/')[1].split('?')[0]
                    if not tweet_id.isdigit(): continue
                except IndexError:
                    continue

                if url in urls_seen:
                    continue
                urls_seen.add(url)
                
                relevance = item.get('score', 0) 
                relevance += 1 if 'embodied' in content_lower else 0
                relevance += 0.5 if 'robot' in content_lower else 0
                relevance += 1 if 'discussion' in content_lower else 0
                relevance += 1 if 'opinion' in content_lower else 0
                
                tweet_items.append({
                    'title': item.get('content'), 
                    'url': url,
                    'tweet_id': tweet_id,
                    'published_date': item.get('published_date'),
                    'relevance': relevance
                })
            
            tweet_items.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            num_to_engage = random.randint(1, 2)
            logger.debug(f"Found {len(tweet_items)} relevant tweet items, selecting top {num_to_engage} for engagement.")
            return tweet_items[:num_to_engage]
            
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return []

    def engage_with_tweets(self) -> bool:
        """Find and engage with relevant tweets about Embodied AI with randomness."""
        try:
            tweets_to_engage = self.fetch_top_tweets()
            if not tweets_to_engage:
                logger.info("No relevant tweets found to engage with.")
                return True

            logger.info(f"Found {len(tweets_to_engage)} relevant tweets to engage with")
            success = True
            possible_actions = ['reply', 'like', 'retweet']

            for tweet in tweets_to_engage:
                try:
                    tweet_id_int = int(tweet['tweet_id'])
                    tweet_url = tweet['url']
                    logger.info(f"Processing engagement for tweet: {tweet_url}")

                    num_actions = random.randint(1, len(possible_actions))
                    actions_to_take = random.sample(possible_actions, k=num_actions)
                    logger.debug(f"Actions for tweet {tweet_id_int}: {actions_to_take}")

                    engagement_performed = False
                    if 'reply' in actions_to_take:
                        comment = self.generate_engaging_comment(tweet['title'], tweet_url)
                        if comment and comment not in ["Interesting point!", "Interesting perspective! Thanks for sharing."]:
                            time.sleep(random.uniform(1, 4))
                            try:
                                response = self.twitter_client.create_tweet(
                                    text=comment, 
                                    in_reply_to_tweet_id=tweet_id_int
                                )
                                logger.info(f"Replied to tweet {tweet_id_int}. Reply ID: {response.data['id']}")
                                engagement_performed = True
                            except tweepy.errors.TweepyException as e:
                                if e.api_codes == [187]:
                                    logger.warning(f"Reply to {tweet_id_int} is a duplicate, skipping reply.")
                                elif e.api_codes == [433]:
                                     logger.warning(f"Cannot reply to tweet {tweet_id_int}, it might be deleted/hidden.")
                                else:
                                    logger.error(f"Failed to reply to tweet {tweet_id_int}: {e}")
                        else:
                             logger.warning(f"Generated comment for {tweet_id_int} was empty or fallback, skipping reply.")
                    
                    if 'retweet' in actions_to_take:
                        time.sleep(random.uniform(0.5, 3))
                        try:
                            self.twitter_client.retweet(tweet_id_int)
                            logger.info(f"Retweeted tweet {tweet_id_int}")
                            engagement_performed = True
                        except tweepy.errors.TweepyException as e:
                            if e.api_codes == [327]:
                                logger.warning(f"Already retweeted {tweet_id_int}, skipping retweet.")
                            elif e.api_codes == [144]:
                                logger.warning(f"Cannot retweet tweet {tweet_id_int}, not found.")
                            else:
                                logger.error(f"Failed to retweet tweet {tweet_id_int}: {e}")

                    if 'like' in actions_to_take:
                        time.sleep(random.uniform(0.5, 3))
                        try:
                            self.twitter_client.like(tweet_id_int)
                            logger.info(f"Liked tweet {tweet_id_int}")
                            engagement_performed = True
                        except tweepy.errors.TweepyException as e:
                            if e.api_codes == [139]:
                                logger.warning(f"Already liked {tweet_id_int}, skipping like.")
                            elif e.api_codes == [144]:
                                 logger.warning(f"Cannot like tweet {tweet_id_int}, not found.")
                            else:
                                logger.error(f"Failed to like tweet {tweet_id_int}: {e}")
                                
                    if engagement_performed:
                         logger.info(f"Completed engagement actions for tweet: {tweet_url}")
                         time.sleep(random.uniform(5, 15))
                    else:
                        logger.warning(f"No engagement actions successfully performed for tweet: {tweet_url}")

                except Exception as e:
                    logger.error(f"Error processing engagement for tweet {tweet.get('url', 'N/A')}: {e}")
                    success = False 
                    continue

            return success

        except Exception as e:
            logger.error(f"Error in tweet engagement process: {e}")
            return False

    def run(self) -> bool:
        """Run both news posting and tweet engagement."""
        news_success = self.post_to_twitter(self.fetch_top_news())
        logger.info(f"News posting phase completed with success: {news_success}. Waiting before engagement...")
        time.sleep(random.uniform(10, 25)) 
        tweet_success = self.engage_with_tweets()
        logger.info(f"Tweet engagement phase completed with success: {tweet_success}")
        return news_success and tweet_success 