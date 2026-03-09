#!/usr/bin/env python3
"""
Twitter (X) Watcher - Monitors Twitter for mentions, replies, and DMs
Tracks engagement and creates action files for AI processing
"""

import time
import logging
import requests
import os
from pathlib import Path
from datetime import datetime
from base_watcher import BaseWatcher
from audit_logger import get_audit_logger

class TwitterWatcher(BaseWatcher):
    def __init__(self, vault_path: str, check_interval: int = 300):
        """
        Initialize Twitter Watcher
        
        Args:
            vault_path: Path to Obsidian vault
            check_interval: Time between checks in seconds
        """
        super().__init__(vault_path, check_interval)
        
        # Twitter API v2 configuration
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN', '')
        self.user_id = os.getenv('TWITTER_USER_ID', '')
        self.twitter_api_url = 'https://api.twitter.com/2'
        
        # Tracking
        self.processed_tweets = set()
        self.processed_mentions = set()
        self.processed_dms = set()
        
        # Load previously processed IDs
        self._load_processed_ids()
        
        # Audit logger
        self.audit_logger = get_audit_logger(vault_path)
        
        self.logger = logging.getLogger('TwitterWatcher')
        self.logger.info('TwitterWatcher initialized')
    
    def _load_processed_ids(self):
        """Load previously processed IDs from vault"""
        tweets_file = Path(self.vault_path) / 'processed_twitter_tweets.txt'
        mentions_file = Path(self.vault_path) / 'processed_twitter_mentions.txt'
        dms_file = Path(self.vault_path) / 'processed_twitter_dms.txt'
        
        if tweets_file.exists():
            with open(tweets_file, 'r') as f:
                self.processed_tweets = set(f.read().splitlines())
        
        if mentions_file.exists():
            with open(mentions_file, 'r') as f:
                self.processed_mentions = set(f.read().splitlines())
        
        if dms_file.exists():
            with open(dms_file, 'r') as f:
                self.processed_dms = set(f.read().splitlines())
    
    def _save_processed_ids(self):
        """Save processed IDs to vault"""
        tweets_file = Path(self.vault_path) / 'processed_twitter_tweets.txt'
        mentions_file = Path(self.vault_path) / 'processed_twitter_mentions.txt'
        dms_file = Path(self.vault_path) / 'processed_twitter_dms.txt'
        
        with open(tweets_file, 'w') as f:
            f.write('\n'.join(self.processed_tweets))
        
        with open(mentions_file, 'w') as f:
            f.write('\n'.join(self.processed_mentions))
        
        with open(dms_file, 'w') as f:
            f.write('\n'.join(self.processed_dms))
    
    def check_for_updates(self) -> list:
        """Check for new Twitter activities"""
        new_items = []
        
        if not self.bearer_token or not self.user_id:
            self.logger.warning('Twitter credentials not configured')
            return []
        
        try:
            # Check for new mentions
            new_items.extend(self._check_mentions())
            
            # Check for new replies to your tweets
            new_items.extend(self._check_replies())
            
            # Console output
            if new_items:
                print(f"\n{'='*60}")
                print(f"  🐦 TWITTER (X) ACTIVITY DETECTED!")
                print(f"{'='*60}")
                print(f"     📢 New Mentions: {len([i for i in new_items if i['type'] == 'mention'])}")
                print(f"     💬 New Replies: {len([i for i in new_items if i['type'] == 'reply'])}")
                print(f"     📊 Total Items: {len(new_items)}")
                print(f"{'='*60}\n")
            
            return new_items
            
        except Exception as e:
            self.logger.error(f'Error checking Twitter: {e}')
            return []
    
    def _check_mentions(self) -> list:
        """Check for new mentions"""
        new_mentions = []
        
        try:
            url = f'{self.twitter_api_url}/users/{self.user_id}/mentioned_tweets'
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }
            params = {
                'max_results': 10,
                'tweet.fields': 'created_at,public_metrics,author_id,entities,text',
                'expansions': 'author_id',
                'user.fields': 'name,username,verified'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
                
                for tweet in data.get('data', []):
                    tweet_id = tweet.get('id', '')
                    
                    if tweet_id not in self.processed_mentions:
                        author = users.get(tweet.get('author_id'), {})
                        
                        # Check for urgent keywords
                        text_lower = tweet.get('text', '').lower()
                        priority = 'high' if any(kw in text_lower for kw in ['urgent', 'help', 'asap', 'emergency']) else 'normal'
                        
                        new_mentions.append({
                            'type': 'mention',
                            'id': tweet_id,
                            'text': tweet.get('text', '')[:500],
                            'created_at': tweet.get('created_at', ''),
                            'author_username': author.get('username', 'Unknown'),
                            'author_name': author.get('name', 'Unknown'),
                            'author_verified': author.get('verified', False),
                            'retweets': tweet.get('public_metrics', {}).get('retweet_count', 0),
                            'likes': tweet.get('public_metrics', {}).get('like_count', 0),
                            'replies': tweet.get('public_metrics', {}).get('reply_count', 0),
                            'priority': priority
                        })
                        
                        self.processed_mentions.add(tweet_id)
                
                self._save_processed_ids()
            
        except Exception as e:
            self.logger.error(f'Error checking mentions: {e}')
        
        return new_mentions
    
    def _check_replies(self) -> list:
        """Check for new replies to your tweets"""
        new_replies = []
        
        try:
            # First get your recent tweets
            your_tweets_url = f'{self.twitter_api_url}/users/{self.user_id}/tweets'
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }
            params = {
                'max_results': 5,
                'tweet.fields': 'id,created_at',
            }
            
            your_tweets_response = requests.get(your_tweets_url, headers=headers, params=params, timeout=30)
            
            if your_tweets_response.status_code == 200:
                your_tweets = your_tweets_response.json().get('data', [])
                
                # Check for replies to each tweet
                for tweet in your_tweets:
                    tweet_id = tweet.get('id', '')
                    
                    # Search for replies to this tweet
                    query = f'conversation_id:{tweet_id} is:reply'
                    search_url = f'{self.twitter_api_url}/tweets/search/recent'
                    
                    search_params = {
                        'query': query,
                        'max_results': 10,
                        'tweet.fields': 'created_at,public_metrics,author_id,text',
                        'expansions': 'author_id',
                        'user.fields': 'name,username,verified'
                    }
                    
                    search_response = requests.get(search_url, headers=headers, params=search_params, timeout=30)
                    
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        users = {u['id']: u for u in search_data.get('includes', {}).get('users', [])}
                        
                        for reply in search_data.get('data', []):
                            reply_id = reply.get('id', '')
                            
                            if reply_id not in self.processed_tweets:
                                author = users.get(reply.get('author_id'), {})
                                
                                new_replies.append({
                                    'type': 'reply',
                                    'id': reply_id,
                                    'text': reply.get('text', '')[:500],
                                    'created_at': reply.get('created_at', ''),
                                    'author_username': author.get('username', 'Unknown'),
                                    'author_name': author.get('name', 'Unknown'),
                                    'author_verified': author.get('verified', False),
                                    'likes': reply.get('public_metrics', {}).get('like_count', 0),
                                    'parent_tweet_id': tweet_id,
                                    'priority': 'normal'
                                })
                                
                                self.processed_tweets.add(reply_id)
                
                self._save_processed_ids()
            
        except Exception as e:
            self.logger.error(f'Error checking replies: {e}')
        
        return new_replies
    
    def create_action_file(self, item) -> Path:
        """Create action file for Twitter activity"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if item['type'] == 'mention':
                filename = f"TWITTER_MENTION_{timestamp}.md"
                verified_badge = "✓" if item['author_verified'] else ""
                content = f"""---
type: twitter_mention
source: twitter
id: {item['id']}
from: {item['author_name']} @{item['author_username']} {verified_badge}
text: {item['text']}
created_at: {item['created_at']}
retweets: {item['retweets']}
likes: {item['likes']}
replies: {item['replies']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Twitter Mention

**From:** {item['author_name']} (@{item['author_username']}) {verified_badge}  
**Posted:** {item['created_at']}  
**Priority:** {item['priority'].upper()}

## Tweet Content

{item['text']}

## Engagement Metrics

- 🔄 **Retweets:** {item['retweets']}
- ❤️ **Likes:** {item['likes']}
- 💬 **Replies:** {item['replies']}

## Suggested Actions

- [ ] Review mention
- [ ] Check user profile and context
- [ ] Respond with appropriate tweet
- [ ] Like or retweet if relevant
- [ ] Archive after processing

## Quick Actions

- [ ] Like the mention
- [ ] Retweet with comment
- [ ] Reply publicly
- [ ] Send DM if private matter

---
*Generated by Twitter Watcher*
"""
            
            elif item['type'] == 'reply':
                filename = f"TWITTER_REPLY_{timestamp}.md"
                verified_badge = "✓" if item['author_verified'] else ""
                content = f"""---
type: twitter_reply
source: twitter
id: {item['id']}
from: {item['author_name']} @{item['author_username']} {verified_badge}
text: {item['text']}
created_at: {item['created_at']}
likes: {item['likes']}
parent_tweet_id: {item['parent_tweet_id']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Twitter Reply

**From:** {item['author_name']} (@{item['author_username']}) {verified_badge}  
**Posted:** {item['created_at']}  
**Priority:** {item['priority'].upper()}

## Reply Content

{item['text']}

## Details

- ❤️ **Likes:** {item['likes']}
- 📝 **Parent Tweet ID:** {item['parent_tweet_id']}

## Suggested Actions

- [ ] Review reply
- [ ] Check conversation thread
- [ ] Respond if needed
- [ ] Like the reply
- [ ] Archive after processing

---
*Generated by Twitter Watcher*
"""
            
            else:
                filename = f"TWITTER_ACTIVITY_{timestamp}.md"
                content = f"# Twitter Activity\n\n{item}\n"
            
            filepath = self.needs_action / filename
            filepath.write_text(content, encoding='utf-8')
            
            # Log to audit logger
            self.audit_logger.log_watcher_event(
                watcher_name='TwitterWatcher',
                event_type=f'twitter_{item["type"]}',
                event_data={
                    'id': item['id'],
                    'from': item.get('author_username', 'Unknown'),
                    'type': item['type']
                },
                action_file_created=str(filepath)
            )
            
            return filepath
            
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}')
            return Path('')
    
    def run(self):
        """Main watcher loop"""
        self.logger.info(f'Starting TwitterWatcher')
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
            except Exception as e:
                self.logger.error(f'Error in TwitterWatcher: {e}')
            time.sleep(self.check_interval)


if __name__ == "__main__":
    import sys
    
    # Set UTF-8 encoding for Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('twitter_watcher.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Gold-Tier\Personal AI Employee Vault"
    
    print("\n" + "="*60)
    print("  🐦 TWITTER (X) WATCHER")
    print("="*60)
    print("  Monitoring Twitter mentions and replies")
    print("  Checking every 5 minutes")
    print("="*60 + "\n")
    
    try:
        watcher = TwitterWatcher(vault_path, check_interval=300)
        print("✅ Twitter Watcher started!")
        print(f"📁 Files will be created in: {watcher.needs_action}")
        print("⏹ Press Ctrl+C to stop\n")
        watcher.run()
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("  Stopped")
        print("="*60 + "\n")
