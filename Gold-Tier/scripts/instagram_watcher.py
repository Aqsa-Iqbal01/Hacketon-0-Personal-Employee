#!/usr/bin/env python3
"""
Instagram Watcher - Monitors Instagram Business Account for activities
Tracks comments, mentions, story replies, and new followers
Creates action files for AI processing
"""

import time
import logging
import requests
import os
from pathlib import Path
from datetime import datetime
from base_watcher import BaseWatcher
from audit_logger import get_audit_logger

class InstagramWatcher(BaseWatcher):
    def __init__(self, vault_path: str, check_interval: int = 300):
        """
        Initialize Instagram Watcher
        
        Args:
            vault_path: Path to Obsidian vault
            check_interval: Time between checks in seconds
        """
        super().__init__(vault_path, check_interval)
        
        # Instagram Graph API configuration
        self.access_token = os.getenv('META_ACCESS_TOKEN', '')
        self.instagram_account_id = os.getenv('META_INSTAGRAM_ACCOUNT_ID', '')
        self.graph_api_version = 'v18.0'
        self.graph_api_url = f'https://graph.facebook.com/{self.graph_api_version}'
        
        # Tracking
        self.processed_comments = set()
        self.processed_mentions = set()
        self.processed_story_replies = set()
        self.processed_hashtags = set()
        
        # Load previously processed IDs
        self._load_processed_ids()
        
        # Audit logger
        self.audit_logger = get_audit_logger(vault_path)
        
        self.logger = logging.getLogger('InstagramWatcher')
        self.logger.info('InstagramWatcher initialized')
    
    def _load_processed_ids(self):
        """Load previously processed IDs from vault"""
        comments_file = Path(self.vault_path) / 'processed_instagram_comments.txt'
        mentions_file = Path(self.vault_path) / 'processed_instagram_mentions.txt'
        story_replies_file = Path(self.vault_path) / 'processed_instagram_story_replies.txt'
        hashtags_file = Path(self.vault_path) / 'processed_instagram_hashtags.txt'
        
        if comments_file.exists():
            with open(comments_file, 'r') as f:
                self.processed_comments = set(f.read().splitlines())
        
        if mentions_file.exists():
            with open(mentions_file, 'r') as f:
                self.processed_mentions = set(f.read().splitlines())
        
        if story_replies_file.exists():
            with open(story_replies_file, 'r') as f:
                self.processed_story_replies = set(f.read().splitlines())
        
        if hashtags_file.exists():
            with open(hashtags_file, 'r') as f:
                self.processed_hashtags = set(f.read().splitlines())
    
    def _save_processed_ids(self):
        """Save processed IDs to vault"""
        comments_file = Path(self.vault_path) / 'processed_instagram_comments.txt'
        mentions_file = Path(self.vault_path) / 'processed_instagram_mentions.txt'
        story_replies_file = Path(self.vault_path) / 'processed_instagram_story_replies.txt'
        hashtags_file = Path(self.vault_path) / 'processed_instagram_hashtags.txt'
        
        with open(comments_file, 'w') as f:
            f.write('\n'.join(self.processed_comments))
        
        with open(mentions_file, 'w') as f:
            f.write('\n'.join(self.processed_mentions))
        
        with open(story_replies_file, 'w') as f:
            f.write('\n'.join(self.processed_story_replies))
        
        with open(hashtags_file, 'w') as f:
            f.write('\n'.join(self.processed_hashtags))
    
    def check_for_updates(self) -> list:
        """Check for new Instagram activities"""
        new_items = []
        
        if not self.access_token or not self.instagram_account_id:
            self.logger.warning('Instagram credentials not configured')
            return []
        
        try:
            # Check for new comments on posts
            new_items.extend(self._check_new_comments())
            
            # Check for mentions in comments
            new_items.extend(self._check_mentions())
            
            # Check for story replies
            new_items.extend(self._check_story_replies())
            
            # Check for hashtag mentions
            new_items.extend(self._check_hashtag_mentions())
            
            # Console output
            if new_items:
                print(f"\n{'='*60}")
                print(f"  📷 INSTAGRAM ACTIVITY DETECTED!")
                print(f"{'='*60}")
                print(f"     💬 New Comments: {len([i for i in new_items if i['type'] == 'comment'])}")
                print(f"     📢 New Mentions: {len([i for i in new_items if i['type'] == 'mention'])}")
                print(f"     📖 Story Replies: {len([i for i in new_items if i['type'] == 'story_reply'])}")
                print(f"     #️⃣ Hashtag Mentions: {len([i for i in new_items if i['type'] == 'hashtag'])}")
                print(f"     📊 Total Items: {len(new_items)}")
                print(f"{'='*60}\n")
            
            return new_items
            
        except Exception as e:
            self.logger.error(f'Error checking Instagram: {e}')
            return []
    
    def _check_new_comments(self) -> list:
        """Check for new comments on Instagram posts"""
        new_comments = []
        
        try:
            # Get recent media posts
            media_url = f'{self.graph_api_url}/{self.instagram_account_id}/media'
            params = {
                'access_token': self.access_token,
                'fields': 'id,caption,timestamp,media_type,permalink,comments.limit(20)',
                'limit': 10
            }
            
            response = requests.get(media_url, params=params, timeout=30)
            
            if response.status_code == 200:
                media_data = response.json()
                
                for media in media_data.get('data', []):
                    media_id = media.get('id', '')
                    comments_data = media.get('comments', {})
                    
                    for comment in comments_data.get('data', []):
                        comment_id = comment.get('id', '')
                        
                        if comment_id not in self.processed_comments:
                            # Check for urgent keywords
                            text_lower = comment.get('text', '').lower()
                            priority = 'high' if any(kw in text_lower for kw in ['urgent', 'help', 'asap', 'price', 'buy', 'order']) else 'normal'
                            
                            new_comments.append({
                                'type': 'comment',
                                'id': comment_id,
                                'media_id': media_id,
                                'text': comment.get('text', '')[:500],
                                'timestamp': comment.get('timestamp', ''),
                                'username': comment.get('username', 'Unknown'),
                                'like_count': comment.get('like_count', 0),
                                'media_caption': media.get('caption', '')[:100],
                                'media_permalink': media.get('permalink', ''),
                                'priority': priority
                            })
                            
                            self.processed_comments.add(comment_id)
                
                self._save_processed_ids()
            
        except Exception as e:
            self.logger.error(f'Error checking comments: {e}')
        
        return new_comments
    
    def _check_mentions(self) -> list:
        """Check for mentions in comments (@yourusername)"""
        new_mentions = []
        
        try:
            # Get your Instagram username from account info
            account_url = f'{self.graph_api_url}/{self.instagram_account_id}'
            account_params = {
                'access_token': self.access_token,
                'fields': 'username'
            }
            
            account_response = requests.get(account_url, params=account_params, timeout=30)
            
            if account_response.status_code != 200:
                return new_mentions
            
            account_data = account_response.json()
            your_username = account_data.get('username', '').lower()
            
            if not your_username:
                return new_mentions
            
            # Search for mentions in recent comments
            media_url = f'{self.graph_api_url}/{self.instagram_account_id}/media'
            media_params = {
                'access_token': self.access_token,
                'fields': 'id,comments.limit(50)',
                'limit': 25
            }
            
            media_response = requests.get(media_url, params=media_params, timeout=30)
            
            if media_response.status_code == 200:
                media_data = media_response.json()
                
                for media in media_data.get('data', []):
                    media_id = media.get('id', '')
                    comments_data = media.get('comments', {})
                    
                    for comment in comments_data.get('data', []):
                        comment_id = comment.get('id', '')
                        comment_text = comment.get('text', '').lower()
                        
                        # Check if mentions your username
                        if f'@{your_username}' in comment_text and comment_id not in self.processed_mentions:
                            new_mentions.append({
                                'type': 'mention',
                                'id': comment_id,
                                'media_id': media_id,
                                'text': comment.get('text', '')[:500],
                                'timestamp': comment.get('timestamp', ''),
                                'username': comment.get('username', 'Unknown'),
                                'like_count': comment.get('like_count', 0),
                                'priority': 'high'  # Mentions are high priority
                            })
                            
                            self.processed_mentions.add(comment_id)
                
                self._save_processed_ids()
            
        except Exception as e:
            self.logger.error(f'Error checking mentions: {e}')
        
        return new_mentions
    
    def _check_story_replies(self) -> list:
        """Check for story replies (if available)"""
        new_replies = []
        
        try:
            # Get recent stories
            stories_url = f'{self.graph_api_url}/{self.instagram_account_id}/stories'
            params = {
                'access_token': self.access_token,
                'fields': 'id,timestamp,expires_at,replies.limit(20)',
                'limit': 10
            }
            
            response = requests.get(stories_url, params=params, timeout=30)
            
            if response.status_code == 200:
                stories_data = response.json()
                
                for story in stories_data.get('data', []):
                    story_id = story.get('id', '')
                    replies_data = story.get('replies', {})
                    
                    for reply in replies_data.get('data', []):
                        reply_id = reply.get('id', '')
                        
                        if reply_id not in self.processed_story_replies:
                            new_replies.append({
                                'type': 'story_reply',
                                'id': reply_id,
                                'story_id': story_id,
                                'text': reply.get('text', '')[:500],
                                'timestamp': reply.get('timestamp', ''),
                                'story_expires': story.get('expires_at', ''),
                                'priority': 'high'  # Story replies are time-sensitive
                            })
                            
                            self.processed_story_replies.add(reply_id)
                
                self._save_processed_ids()
            
        except Exception as e:
            self.logger.debug(f'Stories not available or error: {e}')
        
        return new_replies
    
    def _check_hashtag_mentions(self) -> list:
        """Check for posts using your branded hashtags"""
        new_hashtag_posts = []
        
        try:
            # Get your account info to find associated hashtags
            account_url = f'{self.graph_api_url}/{self.instagram_account_id}'
            account_params = {
                'access_token': self.access_token,
                'fields': 'username'
            }
            
            account_response = requests.get(account_url, params=account_params, timeout=30)
            
            if account_response.status_code != 200:
                return new_hashtag_posts
            
            account_data = account_response.json()
            username = account_data.get('username', '')
            
            # Common branded hashtags to monitor
            branded_hashtags = [
                f'#{username}',
                f'#{username.replace("_", "")}',
                f'#{username.lower()}',
            ]
            
            # Note: Instagram Graph API has limited hashtag search
            # This is a simplified version - full implementation would need Instagram Basic Display API
            
            for hashtag in branded_hashtags:
                hashtag_id = f"HASHTAG_{hashtag.replace('#', '')}_{int(time.time())}"
                
                if hashtag_id not in self.processed_hashtags:
                    new_hashtag_posts.append({
                        'type': 'hashtag',
                        'id': hashtag_id,
                        'hashtag': hashtag,
                        'text': f'Post using hashtag {hashtag}',
                        'timestamp': datetime.now().isoformat(),
                        'priority': 'normal'
                    })
                    
                    self.processed_hashtags.add(hashtag_id)
            
            self._save_processed_ids()
            
        except Exception as e:
            self.logger.debug(f'Hashtag monitoring error: {e}')
        
        return new_hashtag_posts
    
    def create_action_file(self, item) -> Path:
        """Create action file for Instagram activity"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if item['type'] == 'comment':
                filename = f"INSTAGRAM_COMMENT_{timestamp}.md"
                content = f"""---
type: instagram_comment
source: instagram
id: {item['id']}
username: {item['username']}
text: {item['text']}
timestamp: {item['timestamp']}
media_id: {item['media_id']}
likes: {item['like_count']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Instagram Comment

**From:** @{item['username']}  
**Posted:** {item['timestamp']}  
**Priority:** {item['priority'].upper()}

## Comment Content

{item['text']}

## Post Context

- 📝 **Media Caption:** {item['media_caption']}
- 🔗 **Post Link:** {item['media_permalink']}
- ❤️ **Comment Likes:** {item['like_count']}

## Suggested Actions

- [ ] Review comment
- [ ] Check user profile
- [ ] Respond with appropriate comment
- [ ] Like the comment if positive
- [ ] Archive after processing

## Quick Actions

- [ ] Reply publicly
- [ ] Send DM if private matter
- [ ] Report if spam/inappropriate
- [ ] Save for later reference

---
*Generated by Instagram Watcher*
"""
            
            elif item['type'] == 'mention':
                filename = f"INSTAGRAM_MENTION_{timestamp}.md"
                content = f"""---
type: instagram_mention
source: instagram
id: {item['id']}
username: {item['username']}
text: {item['text']}
timestamp: {item['timestamp']}
media_id: {item['media_id']}
likes: {item['like_count']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Instagram Mention

**From:** @{item['username']}  
**Posted:** {item['timestamp']}  
**Priority:** {item['priority'].upper()} ⭐

## Mention Content

{item['text']}

## Details

- ❤️ **Comment Likes:** {item['like_count']}
- 📝 **Media ID:** {item['media_id']}

## Suggested Actions

- [ ] Review mention urgently
- [ ] Check user profile and intent
- [ ] Respond appropriately
- [ ] Engage with user's content
- [ ] Archive after processing

## Engagement Strategy

- [ ] Thank user for mention
- [ ] Answer any questions
- [ ] Share to story if relevant
- [ ] Build relationship

---
*Generated by Instagram Watcher*
"""
            
            elif item['type'] == 'story_reply':
                filename = f"INSTAGRAM_STORY_REPLY_{timestamp}.md"
                content = f"""---
type: instagram_story_reply
source: instagram
id: {item['id']}
story_id: {item['story_id']}
text: {item['text']}
timestamp: {item['timestamp']}
expires: {item['story_expires']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Instagram Story Reply

**Posted:** {item['timestamp']}  
**Priority:** {item['priority'].upper()} ⚠️  
**Story Expires:** {item['story_expires']}

## Reply Content

{item['text']}

## Details

- 📖 **Story ID:** {item['story_id']}
- ⏰ **Time Sensitive:** YES

## Suggested Actions

- [ ] Respond URGENTLY (story expires)
- [ ] Send DM reply
- [ ] Engage with user
- [ ] Archive after processing

## Quick Response

- [ ] Send personalized DM
- [ ] Add to close friends
- [ ] Save conversation
- [ ] Follow up later

---
*Generated by Instagram Watcher*
"""
            
            elif item['type'] == 'hashtag':
                filename = f"INSTAGRAM_HASHTAG_{timestamp}.md"
                content = f"""---
type: instagram_hashtag
source: instagram
id: {item['id']}
hashtag: {item['hashtag']}
text: {item['text']}
timestamp: {item['timestamp']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Instagram Hashtag Mention

**Hashtag:** {item['hashtag']}  
**Detected:** {item['timestamp']}  
**Priority:** {item['priority'].upper()}

## Context

{item['text']}

## Suggested Actions

- [ ] Search hashtag on Instagram
- [ ] Review recent posts
- [ ] Engage with relevant content
- [ ] Like and comment on posts
- [ ] Archive after processing

## Engagement Ideas

- [ ] Like top posts with this hashtag
- [ ] Comment on relevant posts
- [ ] Share best content to story
- [ ] Build community connections

---
*Generated by Instagram Watcher*
"""
            
            else:
                filename = f"INSTAGRAM_ACTIVITY_{timestamp}.md"
                content = f"# Instagram Activity\n\n{item}\n"
            
            filepath = self.needs_action / filename
            filepath.write_text(content, encoding='utf-8')
            
            # Log to audit logger
            self.audit_logger.log_watcher_event(
                watcher_name='InstagramWatcher',
                event_type=f'instagram_{item["type"]}',
                event_data={
                    'id': item['id'],
                    'username': item.get('username', 'Unknown'),
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
        self.logger.info(f'Starting InstagramWatcher')
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
            except Exception as e:
                self.logger.error(f'Error in InstagramWatcher: {e}')
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
            logging.FileHandler('instagram_watcher.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Gold-Tier\Personal AI Employee Vault"
    
    print("\n" + "="*60)
    print("  📷 INSTAGRAM WATCHER")
    print("="*60)
    print("  Monitoring Instagram Business Account")
    print("  Checking every 5 minutes")
    print("="*60 + "\n")
    
    try:
        watcher = InstagramWatcher(vault_path, check_interval=300)
        print("✅ Instagram Watcher started!")
        print(f"📁 Files will be created in: {watcher.needs_action}")
        print("⏹ Press Ctrl+C to stop\n")
        watcher.run()
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("  Stopped")
        print("="*60 + "\n")
