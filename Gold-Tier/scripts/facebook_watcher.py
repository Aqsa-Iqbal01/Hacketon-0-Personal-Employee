#!/usr/bin/env python3
"""
Facebook Watcher - Monitors Facebook Page for new activities
Monitors posts, comments, messages, and page insights
"""

import time
import logging
import requests
from pathlib import Path
from datetime import datetime
from base_watcher import BaseWatcher
from audit_logger import get_audit_logger
import os

class FacebookWatcher(BaseWatcher):
    def __init__(self, vault_path: str, check_interval: int = 300):
        """
        Initialize Facebook Watcher
        
        Args:
            vault_path: Path to Obsidian vault
            check_interval: Time between checks in seconds
        """
        super().__init__(vault_path, check_interval)
        
        # Facebook Graph API configuration
        self.access_token = os.getenv('META_ACCESS_TOKEN', '')
        self.page_id = os.getenv('META_FACEBOOK_PAGE_ID', '')
        self.graph_api_version = 'v18.0'
        self.graph_api_url = f'https://graph.facebook.com/{self.graph_api_version}'
        
        # Tracking
        self.processed_posts = set()
        self.processed_comments = set()
        self.processed_messages = set()
        
        # Load previously processed IDs
        self._load_processed_ids()
        
        # Audit logger
        self.audit_logger = get_audit_logger(vault_path)
        
        self.logger = logging.getLogger('FacebookWatcher')
        self.logger.info('FacebookWatcher initialized')
    
    def _load_processed_ids(self):
        """Load previously processed IDs from vault"""
        posts_file = Path(self.vault_path) / 'processed_facebook_posts.txt'
        comments_file = Path(self.vault_path) / 'processed_facebook_comments.txt'
        messages_file = Path(self.vault_path) / 'processed_facebook_messages.txt'
        
        if posts_file.exists():
            with open(posts_file, 'r') as f:
                self.processed_posts = set(f.read().splitlines())
        
        if comments_file.exists():
            with open(comments_file, 'r') as f:
                self.processed_comments = set(f.read().splitlines())
        
        if messages_file.exists():
            with open(messages_file, 'r') as f:
                self.processed_messages = set(f.read().splitlines())
    
    def _save_processed_ids(self):
        """Save processed IDs to vault"""
        posts_file = Path(self.vault_path) / 'processed_facebook_posts.txt'
        comments_file = Path(self.vault_path) / 'processed_facebook_comments.txt'
        messages_file = Path(self.vault_path) / 'processed_facebook_messages.txt'
        
        with open(posts_file, 'w') as f:
            f.write('\n'.join(self.processed_posts))
        
        with open(comments_file, 'w') as f:
            f.write('\n'.join(self.processed_comments))
        
        with open(messages_file, 'w') as f:
            f.write('\n'.join(self.processed_messages))
    
    def check_for_updates(self) -> list:
        """Check for new Facebook activities"""
        new_items = []
        
        if not self.access_token or not self.page_id:
            self.logger.warning('Facebook credentials not configured')
            return []
        
        try:
            # Check for new posts on page
            new_items.extend(self._check_new_posts())
            
            # Check for new comments on posts
            new_items.extend(self._check_new_comments())
            
            # Check for new page messages
            new_items.extend(self._check_page_messages())
            
            # Console output
            if new_items:
                print(f"\n{'='*60}")
                print(f"  📘 FACEBOOK ACTIVITY DETECTED!")
                print(f"{'='*60}")
                print(f"     📝 New Posts: {len([i for i in new_items if i['type'] == 'post'])}")
                print(f"     💬 New Comments: {len([i for i in new_items if i['type'] == 'comment'])}")
                print(f"     📩 New Messages: {len([i for i in new_items if i['type'] == 'message'])}")
                print(f"     📊 Total Items: {len(new_items)}")
                print(f"{'='*60}\n")
            
            return new_items
            
        except Exception as e:
            self.logger.error(f'Error checking Facebook: {e}')
            return []
    
    def _check_new_posts(self) -> list:
        """Check for new posts on the Facebook page"""
        new_posts = []
        
        try:
            url = f'{self.graph_api_url}/{self.page_id}/feed'
            params = {
                'access_token': self.access_token,
                'fields': 'id,message,created_time,from,permalink_url,likes.summary(true),comments.summary(true),shares',
                'limit': 10
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for post in data.get('data', []):
                post_id = post.get('id', '')
                
                if post_id not in self.processed_posts:
                    new_posts.append({
                        'type': 'post',
                        'id': post_id,
                        'message': post.get('message', '')[:500],
                        'created_time': post.get('created_time', ''),
                        'from': post.get('from', {}).get('name', 'Unknown'),
                        'permalink': post.get('permalink_url', ''),
                        'likes': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                        'comments': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                        'shares': post.get('shares', {}).get('count', 0),
                        'priority': 'normal'
                    })
                    
                    self.processed_posts.add(post_id)
            
            self._save_processed_ids()
            
        except Exception as e:
            self.logger.error(f'Error checking posts: {e}')
        
        return new_posts
    
    def _check_new_comments(self) -> list:
        """Check for new comments on page posts"""
        new_comments = []
        
        try:
            # Get recent posts first
            posts_url = f'{self.graph_api_url}/{self.page_id}/feed'
            posts_params = {
                'access_token': self.access_token,
                'fields': 'id,comments.limit(10)',
                'limit': 5
            }
            
            posts_response = requests.get(posts_url, params=posts_params, timeout=30)
            posts_response.raise_for_status()
            posts_data = posts_response.json()
            
            for post in posts_data.get('data', []):
                post_id = post.get('id', '')
                comments_data = post.get('comments', {})
                
                for comment in comments_data.get('data', []):
                    comment_id = comment.get('id', '')
                    
                    if comment_id not in self.processed_comments:
                        new_comments.append({
                            'type': 'comment',
                            'id': comment_id,
                            'post_id': post_id,
                            'message': comment.get('message', '')[:500],
                            'created_time': comment.get('created_time', ''),
                            'from': comment.get('from', {}).get('name', 'Unknown'),
                            'like_count': comment.get('like_count', 0),
                            'priority': 'normal'
                        })
                        
                        self.processed_comments.add(comment_id)
            
            self._save_processed_ids()
            
        except Exception as e:
            self.logger.error(f'Error checking comments: {e}')
        
        return new_comments
    
    def _check_page_messages(self) -> list:
        """Check for new messages to the Facebook page"""
        new_messages = []
        
        try:
            url = f'{self.graph_api_url}/{self.page_id}/conversations'
            params = {
                'access_token': self.access_token,
                'fields': 'messages.limit(10),participants',
                'limit': 5
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for conversation in data.get('data', []):
                messages = conversation.get('messages', {})
                
                for message in messages.get('data', []):
                    message_id = message.get('id', '')
                    
                    if message_id not in self.processed_messages:
                        # Get sender info from participants
                        participants = conversation.get('participants', [])
                        sender_name = participants[0].get('name', 'Unknown') if participants else 'Unknown'
                        
                        new_messages.append({
                            'type': 'message',
                            'id': message_id,
                            'message': message.get('message', '')[:500],
                            'created_time': message.get('created_time', ''),
                            'from': sender_name,
                            'priority': 'high' if any(kw in message.get('message', '').lower() for kw in ['urgent', 'help', 'asap']) else 'normal'
                        })
                        
                        self.processed_messages.add(message_id)
            
            self._save_processed_ids()
            
        except Exception as e:
            self.logger.error(f'Error checking messages: {e}')
        
        return new_messages
    
    def create_action_file(self, item) -> Path:
        """Create action file for Facebook activity"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if item['type'] == 'post':
                filename = f"FACEBOOK_POST_{timestamp}.md"
                content = f"""---
type: facebook_post
source: facebook
id: {item['id']}
from: {item['from']}
message: {item['message']}
created_time: {item['created_time']}
permalink: {item['permalink']}
likes: {item['likes']}
comments: {item['comments']}
shares: {item['shares']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Facebook Post

**From:** {item['from']}  
**Posted:** {item['created_time']}  
**Priority:** {item['priority'].upper()}

## Post Content

{item['message']}

## Engagement Metrics

- 👍 **Likes:** {item['likes']}
- 💬 **Comments:** {item['comments']}
- 🔄 **Shares:** {item['shares']}
- 🔗 **Permalink:** {item['permalink']}

## Suggested Actions

- [ ] Review post content
- [ ] Check engagement metrics
- [ ] Respond to comments if needed
- [ ] Share or boost post if relevant
- [ ] Archive after processing

---
*Generated by Facebook Watcher*
"""
            
            elif item['type'] == 'comment':
                filename = f"FACEBOOK_COMMENT_{timestamp}.md"
                content = f"""---
type: facebook_comment
source: facebook
id: {item['id']}
post_id: {item['post_id']}
from: {item['from']}
message: {item['message']}
created_time: {item['created_time']}
likes: {item['like_count']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Facebook Comment

**From:** {item['from']}  
**Posted:** {item['created_time']}  
**Priority:** {item['priority'].upper()}

## Comment Content

{item['message']}

## Details

- 👍 **Likes:** {item['like_count']}
- 📝 **Post ID:** {item['post_id']}

## Suggested Actions

- [ ] Review comment
- [ ] Respond if needed
- [ ] Check original post context
- [ ] Archive after processing

---
*Generated by Facebook Watcher*
"""
            
            elif item['type'] == 'message':
                filename = f"FACEBOOK_MESSAGE_{timestamp}.md"
                content = f"""---
type: facebook_message
source: facebook
id: {item['id']}
from: {item['from']}
message: {item['message']}
created_time: {item['created_time']}
priority: {item['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# Facebook Page Message

**From:** {item['from']}  
**Received:** {item['created_time']}  
**Priority:** {item['priority'].upper()}

## Message Content

{item['message']}

## Suggested Actions

- [ ] Review message
- [ ] Respond via Facebook Page
- [ ] Take required action
- [ ] Archive after processing

---
*Generated by Facebook Watcher*
"""
            else:
                filename = f"FACEBOOK_ACTIVITY_{timestamp}.md"
                content = f"# Facebook Activity\n\n{item}\n"
            
            filepath = self.needs_action / filename
            filepath.write_text(content, encoding='utf-8')
            
            # Log to audit logger
            self.audit_logger.log_watcher_event(
                watcher_name='FacebookWatcher',
                event_type=f'facebook_{item["type"]}',
                event_data={
                    'id': item['id'],
                    'from': item.get('from', 'Unknown'),
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
        self.logger.info(f'Starting FacebookWatcher')
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
            except Exception as e:
                self.logger.error(f'Error in FacebookWatcher: {e}')
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
            logging.FileHandler('facebook_watcher.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Gold-Tier\Personal AI Employee Vault"
    
    print("\n" + "="*60)
    print("  📘 FACEBOOK PAGE WATCHER")
    print("="*60)
    print("  Monitoring Facebook Page activities")
    print("  Checking every 5 minutes")
    print("="*60 + "\n")
    
    try:
        watcher = FacebookWatcher(vault_path, check_interval=300)
        print("✅ Facebook Watcher started!")
        print(f"📁 Files will be created in: {watcher.needs_action}")
        print("⏹ Press Ctrl+C to stop\n")
        watcher.run()
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("  Stopped")
        print("="*60 + "\n")
