"""
Gmail Watcher - Monitors Gmail for new emails and creates action files

Triggers when new important emails arrive and creates action files for the AI to process.
"""

import time
import logging
import httplib2
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from base_watcher import BaseWatcher
from datetime import datetime

class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str, check_interval: int = 120):
        """
        Initialize the Gmail watcher.

        Args:
            vault_path (str): Path to the Obsidian vault
            check_interval (int): Time between checks in seconds
        """
        super().__init__(vault_path, check_interval)

        self.token_path = Path('token.json')
        self.credentials_path = Path('credentials.json')
        self.processed_ids = set()
        self.service = None

        # Set up logging
        self.logger = logging.getLogger('GmailWatcher')

        # Initialize Gmail service
        self._initialize_service()

        self.logger.info(f'GmailWatcher initialized')

    def _initialize_service(self):
        """Initialize the Gmail API service."""
        try:
            # Check if token.json exists
            if not self.token_path.exists():
                self.logger.error('ERROR: token.json not found!')
                self.logger.error('Please run: python gmail_auth.py')
                self.logger.error('Then login with your Google account')
                raise FileNotFoundError('token.json not found. Run gmail_auth.py first.')

            # Load credentials from token.json
            self.creds = Credentials.from_authorized_user_file(self.token_path, ['https://www.googleapis.com/auth/gmail.readonly'])

            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=self.creds, cache_discovery=False)

            # Load previously processed email IDs
            processed_file = Path(self.vault_path) / 'processed_emails.txt'
            if processed_file.exists():
                with open(processed_file, 'r') as f:
                    self.processed_ids = set(f.read().splitlines())

            self.logger.info('Gmail API service initialized')

        except Exception as e:
            self.logger.error(f'Error initializing Gmail service: {e}')
            raise

    def check_for_updates(self) -> list:
        """
        Check for new important emails.

        Returns:
            list: List of new email messages to process
        """
        try:
            if not self.service:
                self._initialize_service()

            # Search for unread, important emails
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread is:important newer_than:1d'
            ).execute()

            messages = results.get('messages', [])

            # Filter out already processed emails
            new_messages = [m for m in messages if m['id'] not in self.processed_ids]

            self.logger.info(f'Found {len(new_messages)} new important emails')
            return new_messages

        except Exception as e:
            self.logger.error(f'Error checking for emails: {e}')
            return []

    def create_action_file(self, message) -> Path:
        """
        Create an action file for an email.

        Args:
            message: The email message to process

        Returns:
            Path: Path to the created action file
        """
        try:
            # Get the full email message
            msg = self.service.users().messages().get(
                userId='me',
                id=message['id']
            ).execute()

            # Extract headers
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}

            # Extract email content (handle different payload types)
            body = ''
            if 'parts' in msg['payload']:
                # Multi-part message
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = part['body']['data']
                        break
            else:
                # Single part message
                if 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                    body = msg['payload']['body']['data']

            # Decode base64url encoded body if present
            if body:
                import base64
                body = base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')

            # Create action file content
            content = f"""---
type: email
from: {headers.get('From', 'Unknown')}
subject: {headers.get('Subject', 'No Subject')}
received: {datetime.now().isoformat()}
priority: high
status: pending
---

# Email Content

{body}

# Suggested Actions

- [ ] Review email content
- [ ] Determine appropriate response
- [ ] Draft reply if needed
- [ ] Take required action based on email content
- [ ] Move to appropriate folder after processing

# Email Details

**From:** {headers.get('From', 'Unknown')}
**Subject:** {headers.get('Subject', 'No Subject')}
**Date:** {headers.get('Date', 'Unknown')}
**Message ID:** {message['id']}

# Quick Actions

- [ ] Mark as read
- [ ] Archive after processing
- [ ] Forward to relevant party if needed
- [ ] Create calendar event if it's a meeting request

---
*Generated by Gmail Watcher*
"""

            # Create file path
            filepath = self.needs_action / f'EMAIL_{message['id']}.md'

            # Write the file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            # Mark email as processed
            self.processed_ids.add(message['id'])

            # Save processed IDs
            processed_file = Path(self.vault_path) / 'processed_emails.txt'
            with open(processed_file, 'w') as f:
                f.write('\n'.join(self.processed_ids))

            self.logger.info(f'Created action file for email: {headers.get("Subject", "No Subject")}')
            return filepath

        except Exception as e:
            self.logger.error(f'Error creating action file for email {message.get("id", "unknown")}: {e}')
            return Path('')

if __name__ == "__main__":
    import sys
    
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('gmail_watcher.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Example usage
    vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\Personal AI Employee Vault"

    print("\n" + "="*60)
    print("  GMAIL WATCHER")
    print("="*60)
    print("  Watching Gmail for important emails")
    print("  Checking every 2 minutes")
    print("="*60 + "\n")
    
    try:
        watcher = GmailWatcher(vault_path, check_interval=120)
        
        print("✅ Gmail Watcher started!")
        print(f"📁 Files will be created in: {watcher.needs_action}")
        print("⏹ Press Ctrl+C to stop\n")

        # Start the watcher
        watcher.run()
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Solution:")
        print("   1. Run: python gmail_auth.py")
        print("   2. Login with your Google account")
        print("   3. Grant permissions")
        print("   4. Then run gmail_watcher.py again\n")
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("  Stopped")
        print("="*60 + "\n")