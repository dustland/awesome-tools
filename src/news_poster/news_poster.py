from typing import List, Dict, Optional
import tweepy
from tavily import TavilyClient
from utils.logger import logger
from utils.gpt_service import GPTService
import random
import time

# Constants
MAX_NEWS_POSTS_PER_RUN = 2
MAX_TWEET_ENGAGEMENTS_PER_RUN = 3 # Includes retweets, replies, likes
RECENT_POST_FETCH_COUNT = 30 # How many recent posts to fetch for duplicate checks
GPT_DUPLICATE_CHECK_COUNT = 15 # How many recent posts to send to GPT for semantic check

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
                if not hasattr(self, 'twitter_api'): raise
            
            if not self.user_id:
                 logger.warning("Could not determine bot's Twitter User ID. Duplicate checking might be less effective.")

        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            raise
        
    def fetch_supplementary_news(self) -> List[Dict]:
        """Fetch top news from various sources (excluding Twitter) as supplementary content."""
        logger.debug("Fetching supplementary news links...")
        try:
            # Expanded list of reputable domains (excluding twitter.com)
            include_domains = [
                'techcrunch.com', 'wired.com', 'theverge.com', 'venturebeat.com',
                'arxiv.org', 'ieee.org', 'nature.com', 'science.org', 
                'mit.edu', 'stanford.edu', 'berkeley.edu', # University AI labs
                'openai.com', 'deepmind.google', 'ai.meta.com', # AI Research blogs
                'robotics.org', 'technologyreview.com', 'wsj.com', 'bloomberg.com'
            ]
            response = self.tavily_client.search(
                query="embodied AI OR robotics LATEST developments OR research OR breakthroughs",
                search_depth="advanced",
                topic="news", # Focus on news/research articles
                include_domains=include_domains,
                max_results=10 # Fetch a few candidates
            )
            
            # Filter and sort results
            news_items = []
            seen_urls = set()
            for item in response.get('results', []):
                url = item.get('url')
                if not url or url in seen_urls: continue
                seen_urls.add(url)
                relevance = item.get('score', 0)
                content_lower = (item.get('content', '') + item.get('title', '')).lower()
                if 'embodied' in content_lower: relevance *= 1.5
                if 'robot' in content_lower: relevance *= 1.2
                if 'research' in content_lower or 'arxiv' in url: relevance *= 1.1
                news_items.append({
                    'title': item.get('title'), 'url': url, 'content': item.get('content'),
                    'published_date': item.get('published_date'), 'relevance': relevance
                })
            news_items.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            logger.debug(f"Found {len(news_items)} supplementary news items.")
            return news_items[:5] # Return top candidates
            
        except Exception as e:
            logger.error(f"Error fetching supplementary news: {e}")
            return []

    def generate_attractive_text(self, title: str) -> str:
        """Generate a more attractive version of the article title using GPTService."""
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


    def fetch_recent_posts_texts(self, count: int = RECENT_POST_FETCH_COUNT) -> List[str]:
        """Fetch the text content of the bot's own recent tweets/retweets."""
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

    def is_duplicate(self, item_url: str, item_title: str, item_content: str, recent_texts: List[str]) -> bool:
        """Check if an item (URL or content) is a duplicate of recent posts."""
        if not recent_texts:
            return False

        # 1. Check for exact URL match in recent posts
        if item_url:
            for text in recent_texts:
                if item_url in text:
                    logger.warning(f"Skipping duplicate: URL {item_url} found in recent post.")
                    return True

        # 2. Perform semantic check using GPT if URL check passed
        item_summary = f"Title: {item_title}\nContent Snippet: {item_content[:200]}..."
        texts_to_check = "\n---\n".join(recent_texts[:GPT_DUPLICATE_CHECK_COUNT])

        prompt = f"""Analyze the following 'New Item' and the 'Recent Posts'. Determine if the core news story, event, or link described in the 'New Item' is substantively the same as any of the 'Recent Posts', even if the source or wording is different.

New Item:
{item_summary}

Recent Posts:
{texts_to_check}

Is the core news story or link in the 'New Item' already covered in the 'Recent Posts'? Answer ONLY with 'Yes' or 'No'."""
        system_prompt = "You are an AI assistant helping to avoid posting duplicate news content. Analyze the semantic similarity of the core event or link described."

        try:
            response = self.gpt_service.complete(prompt=prompt, system_prompt=system_prompt, max_tokens=10, temperature=0.1)
            result = response.strip().lower() if response else "no"
            is_semantic_duplicate = result == 'yes'
            if is_semantic_duplicate:
                 logger.warning(f"Skipping duplicate (semantic match): '{item_title[:50]}...' ")
            return is_semantic_duplicate
        except Exception as e:
            logger.error(f"Error during GPT duplicate check: {e}")
            return False # Default to not duplicate on error

    def post_supplementary_news(self, news_items: List[Dict], recent_texts: List[str], posts_needed: int) -> int:
        """Post supplementary news links if needed, checking for duplicates."""
        if not news_items or posts_needed <= 0:
            logger.info("No supplementary news items to post or no posts needed.")
            return 0

        logger.info(f"Considering {len(news_items)} supplementary news items to fill {posts_needed} slot(s)...")
        posted_count = 0
        base_hashtags = ["#EmbodiedAI", "#Robotics", "#AI", "#ArtificialIntelligence"]
        optional_hashtags = ["#Tech", "#Innovation", "#FutureTech", "#MachineLearning", "#DeepLearning", "#Research"]

        for item in news_items:
            if posted_count >= posts_needed:
                break # Stop if we've filled the needed slots
            
            try:
                # Check for duplicates (URL and semantic)
                if self.is_duplicate(item.get('url'), item.get('title'), item.get('content'), recent_texts):
                    continue

                attractive_title = self.generate_attractive_text(item['title'])
                num_hashtags = random.randint(2, 3)
                current_hashtags = random.sample(base_hashtags + optional_hashtags, num_hashtags)
                hashtags_str = " ".join(current_hashtags)
                available_chars = 280 - (len(item['url']) + len(hashtags_str) + 5)
                tweet_body = attractive_title[:available_chars-3] + "..." if len(attractive_title) > available_chars else attractive_title
                tweet_text = f"{tweet_body}\n\n{item['url']}\n{hashtags_str}"
                
                time.sleep(random.uniform(2, 8))
                try:
                    response = self.twitter_client.create_tweet(text=tweet_text)
                    tweet_id = response.data['id']
                    logger.info(f"Successfully posted supplementary news tweet ID: {tweet_id} for: {item['title']}")
                    posted_count += 1
                    recent_texts.insert(0, tweet_text) # Update recent texts
                except tweepy.errors.TweepyException as e:
                    if e.api_codes == [187]: # Duplicate tweet error from API
                        logger.warning(f"Skipping duplicate supplementary news post via API error for: {item['title']}")
                        recent_texts.insert(0, tweet_text) # Still add to check list
                        continue
                    else: raise e 
            except Exception as e:
                logger.error(f"Failed to process supplementary news item '{item.get('title', 'N/A')}': {e}")
                continue 
        
        logger.info(f"Finished posting supplementary news. Posted {posted_count} items.")
        return posted_count

    def fetch_top_tweets_for_engagement(self) -> List[Dict]:
        """Fetch top tweets specifically for engagement (retweeting, replying, liking)."""
        logger.debug("Fetching tweets for potential engagement...")
        try:
            response = self.tavily_client.search(
                query='("embodied AI" OR "robotics") (discussion OR conversation OR interesting thread OR new research OR breakthrough OR opinion)',
                search_depth="advanced",
                # Removed topic="social"
                max_results=25 # Get a good pool of candidates
            )
            
            tweet_items = []
            urls_seen = set()
            for item in response.get('results', []):
                url = item.get('url', '')
                if not url or 'twitter.com' not in url or '/status/' not in url:
                    continue
                content_lower = (item.get('content', '') + item.get('title', '')).lower()
                # Slightly broader keyword check for engagement candidates
                if 'embodied' not in content_lower and 'robot' not in content_lower and ' ai ' not in content_lower:
                     continue
                try:
                    tweet_id = url.split('/status/')[1].split('?')[0]
                    if not tweet_id.isdigit(): continue
                except IndexError: continue
                if url in urls_seen: continue
                urls_seen.add(url)
                # Simple relevance: prioritize keywords, slightly deprioritize replies?
                relevance = item.get('score', 0) 
                relevance += 2 if 'embodied' in content_lower else 0
                relevance += 1 if 'robot' in content_lower else 0
                relevance += 1 if 'research' in content_lower or 'breakthrough' in content_lower else 0
                relevance += 0.5 if 'discussion' in content_lower or 'opinion' in content_lower else 0
                # if 'in_reply_to' in item: relevance *= 0.8 # Might require inspecting item structure
                tweet_items.append({
                    'title': item.get('content'), 'url': url, 'tweet_id': tweet_id,
                    'published_date': item.get('published_date'), 'relevance': relevance
                })
            tweet_items.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            logger.debug(f"Found {len(tweet_items)} potential tweets for engagement.")
            return tweet_items[:MAX_TWEET_ENGAGEMENTS_PER_RUN + 2] # Fetch a few extra 
            
        except Exception as e:
            logger.error(f"Error fetching tweets for engagement: {e}", exc_info=True)
            return []

    def process_and_engage_tweets(self, tweets_to_process: List[Dict], recent_texts: List[str]) -> int:
        """Process potential tweets: Prioritize retweeting, optionally like/reply."""
        if not tweets_to_process:
            logger.info("No relevant tweets found to process.")
            return 0

        logger.info(f"Processing {len(tweets_to_process)} potential tweets for engagement (max {MAX_TWEET_ENGAGEMENTS_PER_RUN})...")
        engagement_count = 0 # Total actions: retweets, likes, replies
        retweet_count = 0
        possible_secondary_actions = ['like', 'reply']

        for tweet in tweets_to_process:
            if engagement_count >= MAX_TWEET_ENGAGEMENTS_PER_RUN:
                logger.info("Reached max engagement actions for this run.")
                break
            
            try:
                tweet_id_int = int(tweet['tweet_id'])
                tweet_url = tweet['url']
                tweet_text_snippet = tweet.get('title', '')[:80] + "..."
                logger.info(f"Considering tweet {tweet_id_int}: '{tweet_text_snippet}'")

                # *** Primary Action: Retweet ***
                # Check if URL already exists in recent posts before attempting retweet
                should_retweet = True
                for recent_post in recent_texts:
                    if tweet_url in recent_post:
                        logger.warning(f"Tweet URL {tweet_url} found in recent posts. Skipping retweet attempt.")
                        should_retweet = False
                        break
                
                retweet_successful = False
                if should_retweet:
                    time.sleep(random.uniform(1, 5))
                    try:
                        self.twitter_client.retweet(tweet_id_int)
                        logger.info(f"Retweeted tweet {tweet_id_int}")
                        engagement_count += 1
                        retweet_count += 1
                        retweet_successful = True
                        # Add marker to recent texts to help internal duplicate check
                        recent_texts.insert(0, f"Retweeted: {tweet_url}") 
                    except tweepy.errors.TweepyException as e:
                        if e.api_codes == [327]: logger.warning(f"Already retweeted {tweet_id_int}.")
                        elif e.api_codes == [144]: logger.warning(f"Cannot retweet {tweet_id_int}, not found.")
                        else: logger.error(f"Failed to retweet {tweet_id_int}: {e}")
                
                # *** Secondary Actions (Like/Reply) - Less frequent ***
                if engagement_count < MAX_TWEET_ENGAGEMENTS_PER_RUN and random.random() < 0.4: # 40% chance for secondary actions
                    num_secondary = random.randint(0, len(possible_secondary_actions))
                    actions_to_take = random.sample(possible_secondary_actions, k=num_secondary)
                    logger.debug(f"Secondary actions for tweet {tweet_id_int}: {actions_to_take}")

                    if 'reply' in actions_to_take:
                         # Check semantic duplication before replying
                        if not self.is_duplicate(tweet_url, tweet.get('title'), tweet.get('title'), recent_texts):
                            comment = self.generate_engaging_comment(tweet['title'], tweet_url)
                            if comment and comment not in ["Interesting point!", "Interesting perspective! Thanks for sharing."]:
                                time.sleep(random.uniform(1, 4))
                                try:
                                    response = self.twitter_client.create_tweet(text=comment, in_reply_to_tweet_id=tweet_id_int)
                                    logger.info(f"Replied to tweet {tweet_id_int}. Reply ID: {response.data['id']}")
                                    engagement_count += 1
                                    recent_texts.insert(0, comment) # Add reply to recent texts
                                except tweepy.errors.TweepyException as e:
                                    if e.api_codes == [187]: logger.warning(f"Reply to {tweet_id_int} is duplicate.")
                                    elif e.api_codes == [433]: logger.warning(f"Cannot reply to {tweet_id_int} (deleted/hidden).")
                                    else: logger.error(f"Failed to reply to {tweet_id_int}: {e}")
                            else: logger.warning(f"Generated comment for {tweet_id_int} was empty/fallback, skipping reply.")
                        else: logger.warning(f"Skipping reply to {tweet_id_int} due to semantic duplication.")
                    
                    if 'like' in actions_to_take:
                        time.sleep(random.uniform(0.5, 3))
                        try:
                            self.twitter_client.like(tweet_id_int)
                            logger.info(f"Liked tweet {tweet_id_int}")
                            engagement_count += 1 # Liking also counts as an engagement action
                        except tweepy.errors.TweepyException as e:
                            if e.api_codes == [139]: logger.warning(f"Already liked {tweet_id_int}.")
                            elif e.api_codes == [144]: logger.warning(f"Cannot like {tweet_id_int}, not found.")
                            else: logger.error(f"Failed to like {tweet_id_int}: {e}")
                
                if retweet_successful: # Add longer pause after a successful primary action (retweet)
                    time.sleep(random.uniform(10, 25)) 
                elif engagement_count > 0: # Shorter pause after secondary actions
                     time.sleep(random.uniform(3, 8))

            except Exception as e:
                logger.error(f"Error processing engagement for tweet {tweet.get('url', 'N/A')}: {e}")
                continue

        logger.info(f"Finished tweet engagement phase. Total actions: {engagement_count} ({retweet_count} retweets)." )
        return engagement_count # Return total actions performed

    def run(self) -> bool:
        """Run the main workflow: Prioritize Twitter engagement, supplement with news links."""
        logger.info("=== Starting News Poster Run ===")
        recent_posts = self.fetch_recent_posts_texts()
        
        # 1. Fetch and process Twitter content (Primary Goal)
        tweets_for_engagement = self.fetch_top_tweets_for_engagement()
        engagements_done = self.process_and_engage_tweets(tweets_for_engagement, recent_posts)
        
        # 2. Fetch and post supplementary news links if fewer than max posts were done via engagement
        posts_needed = MAX_NEWS_POSTS_PER_RUN - engagements_done
        news_posted_count = 0
        if posts_needed > 0:
            logger.info(f"Engagement actions ({engagements_done}) less than target ({MAX_NEWS_POSTS_PER_RUN}). Looking for supplementary news links...")
            supplementary_news = self.fetch_supplementary_news()
            news_posted_count = self.post_supplementary_news(supplementary_news, recent_posts, posts_needed)
        else:
            logger.info("Target engagement actions met or exceeded, skipping supplementary news posting.")
            
        total_posts_actions = engagements_done + news_posted_count
        logger.info(f"=== News Poster Run Finished. Total actions/posts: {total_posts_actions} ===")
        return total_posts_actions > 0 # Consider run successful if at least one action was taken