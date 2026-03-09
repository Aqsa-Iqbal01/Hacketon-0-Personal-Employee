"""
Gmail Watcher - Enhanced version with advanced filtering, priority scoring, and task creation

Monitors Gmail for important emails and creates prioritized action files for the AI to process.
"""

import time
import logging
import httplib2
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from base_watcher import BaseWatcher
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

class EnhancedGmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str, credentials_path: str, check_interval: int = 120):
        """
        Initialize the enhanced Gmail watcher.

        Args:
            vault_path (str): Path to the Obsidian vault
            credentials_path (str): Path to Gmail API credentials file
            check_interval (int): Time between checks in seconds
        """
        super().__init__(vault_path, check_interval)

        self.credentials_path = credentials_path
        self.processed_ids = set()
        self.service = None
        self.important_labels = []
        self.priority_threshold = 7  # Priority score threshold for immediate action

        # Set up logging
        self.logger = logging.getLogger('EnhancedGmailWatcher')

        # Initialize Gmail service
        self._initialize_service()

        # Load important labels
        self._load_important_labels()

        self.logger.info(f'EnhancedGmailWatcher initialized')

    def _initialize_service(self):
        """Initialize the Gmail API service."""
        try:
            # Load credentials
            self.creds = Credentials.from_authorized_user_file(self.credentials_path)

            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=self.creds, cache_discovery=False)

            # Load previously processed email IDs
            processed_file = Path(self.vault_path) / 'processed_emails.txt'
            if processed_file.exists():
                with open(processed_file, 'r') as f:
                    self.processed_ids = set(f.read().splitlines())

            # Load processed important emails
            important_file = Path(self.vault_path) / 'processed_important_emails.txt'
            if important_file.exists():
                with open(important_file, 'r') as f:
                    self.processed_important_ids = set(f.read().splitlines())
            else:
                self.processed_important_ids = set()

            self.logger.info('Gmail API service initialized')

        except Exception as e:
            self.logger.error(f'Error initializing Gmail service: {e}')
            raise

    def _load_important_labels(self):
        """Load important Gmail labels."""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            # Identify important labels (e.g., starred, important, priority)
            self.important_labels = [
                label['id'] for label in labels
                if any(keyword in label['name'].lower() for keyword in ['important', 'priority', 'star'])
            ]

            self.logger.info(f'Found {len(self.important_labels)} important labels')
        except Exception as e:
            self.logger.error(f'Error loading labels: {e}')

    def _get_priority_score(self, message: Dict[str, Any]) -> int:
        """Calculate priority score for an email."""
        score = 0

        # Check if email has important labels
        if message.get('labelIds'):
            important_labels = set(message['labelIds']).intersection(self.important_labels)
            score += len(important_labels) * 3

        # Check sender importance (simplified - in real implementation, use contact database)
        headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
        sender = headers.get('From', '').lower()
        if any(keyword in sender for keyword in ['@company.com', '@boss.com', '@important.com']):
            score += 2

        # Check subject keywords
        subject = headers.get('Subject', '').lower()
        if any(keyword in subject for keyword in ['urgent', 'asap', 'immediate', 'action required']):
            score += 2

        # Check if email is recent
        date_header = headers.get('Date')
        if date_header:
            try:
                email_date = datetime.strptime(date_header, '%a, %d %b %Y %H:%M:%S %z')
                age_hours = (datetime.now() - email_date).total_seconds() / 3600
                if age_hours < 1:
                    score += 1  # Fresh email gets bonus
            except:
                pass

        return score

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check for new important emails."""
        try:
            if not self.service:
                self._initialize_service()

            # Search for unread, important emails
            query = 'is:unread newer_than:24h'
            if self.important_labels:
                query += ' OR label:' + ' OR label:'.join(self.important_labels)

            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=20
            ).execute()

            messages = results.get('messages', [])

            # Filter out already processed emails
            new_messages = []
            for m in messages:
                if m['id'] not in self.processed_ids:
                    new_messages.append(m)

            # Sort by priority score
            new_messages.sort(key=lambda m: self._get_priority_score(m), reverse=True)

            self.logger.info(f'Found {len(new_messages)} new important emails')
            return new_messages

        except Exception as e:
            self.logger.error(f'Error checking for emails: {e}')
            return []

    def create_action_file(self, message) -> Path:
        """Create an action file for an email."""
        try:
            # Get the full email message
            msg = self.service.users().messages().get(
                userId='me',
                id=message['id']
            ).execute()

            # Extract headers
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}

            # Extract email content
            body = self._extract_body(msg)

            # Calculate priority score
            priority_score = self._get_priority_score(message)
            priority = 'high' if priority_score >= self.priority_threshold else 'normal'
            urgent = priority_score >= self.priority_threshold + 2

            # Create action file content
            content = self._generate_action_content(
                headers, body, priority, urgent, priority_score
            )

            # Create file path
            email_type = 'URGENT_EMAIL' if urgent else 'EMAIL'
            filepath = self.needs_action / f'{email_type}_{message['id']}.md'

            # Write the file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            # Mark email as processed
            self.processed_ids.add(message['id'])
            self.processed_important_ids.add(message['id'])

            # Save processed IDs
            processed_file = Path(self.vault_path) / 'processed_emails.txt'
            with open(processed_file, 'w') as f:
                f.write('\n'.join(self.processed_ids))

            important_file = Path(self.vault_path) / 'processed_important_emails.txt'
            with open(important_file, 'w') as f:
                f.write('\n'.join(self.processed_important_ids))

            self.logger.info(f'Created action file for email: {headers.get("Subject", "No Subject")}')
            return filepath

        except Exception as e:
            self.logger.error(f'Error creating action file for email {message.get("id", "unknown")}: {e}')
            return Path('')

    def _extract_body(self, message: Dict[str, Any]) -> str:
        """Extract email body content."""
        body = ''
        if 'parts' in message['payload']:
            # Multi-part message
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = part['body']['data']
                    break
                elif part['mimeType'] == 'text/html':
                    body = part['body']['data']
                    break
        else:
            # Single part message
            if 'body' in message['payload'] and 'data' in message['payload']['body']:
                body = message['payload']['body']['data']

        # Decode base64url encoded body if present
        if body:
            import base64
            try:
                body = base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
            except:
                body = 'Unable to decode email content'

        return body

    def _generate_action_content(self, headers: Dict[str, Any], body: str,
                                priority: str, urgent: bool, score: int) -> str:
        """Generate action file content based on email priority."""
        # Generate suggested actions based on content
        suggested_actions = self._generate_suggested_actions(headers, body, urgent)

        # Generate quick actions
        quick_actions = self._generate_quick_actions(urgent)

        # Generate analysis
        analysis = self._generate_analysis(headers, body, score)

        content = f"""---
type: email
source: gmail
from: {headers.get('From', 'Unknown')}
subject: {headers.get('Subject', 'No Subject')}
received: {datetime.now().isoformat()}
priority: {priority}
priority_score: {score}
status: pending
urgent: {str(urgent).lower()}
---

# Email Content

{body}

# Analysis

{analysis}

# Suggested Actions

{suggested_actions}

# Quick Actions

{quick_actions}

# Email Details

**From:** {headers.get('From', 'Unknown')}
**Subject:** {headers.get('Subject', 'No Subject')}
**Date:** {headers.get('Date', 'Unknown')}
**Priority Score:** {score}
**Message ID:** {headers.get('Message-ID', 'Unknown')}

# Response Templates

## For High Priority Emails

**Template 1: Urgent Response**
```
Hi {sender_name},

Thank you for your urgent message. I'm currently reviewing the details and will provide a comprehensive response within the next [timeframe].

For immediate assistance, please call me at [phone_number].

Best regards,
[Your Name]
```

**Template 2: Request for Clarification**
```
Hi {sender_name},

I received your message regarding [topic]. Could you please clarify [specific_question]?

This will help me provide the most accurate and helpful response.

Best regards,
[Your Name]
```

## For Normal Priority Emails

**Template 1: Standard Response**
```
Hi {sender_name},

Thank you for your email. I'll review your request and respond within [timeframe].

Best regards,
[Your Name]
```

**Template 2: Information Request**
```
Hi {sender_name},

Could you please provide additional information about [topic]? This will help me assist you better.

Best regards,
[Your Name]
```

---
*Generated by Enhanced Gmail Watcher*
"""

        return content

    def _generate_suggested_actions(self, headers: Dict[str, Any], body: str, urgent: bool) -> str:
        """Generate suggested actions based on email content."""
        actions = []
        subject = headers.get('Subject', '').lower()
        sender = headers.get('From', '').lower()

        # Common urgent actions
        if urgent:
            actions.extend([
                "- [ ] Respond immediately if time-sensitive",
                "- [ ] Check if it requires immediate action",
                "- [ ] Consider calling if very urgent",
                "- [ ] Prioritize over other tasks"
            ])

        # Action based on subject keywords
        if any(keyword in subject for keyword in ['invoice', 'payment', 'billing']):
            actions.extend([
                "- [ ] Review invoice/payment details",
                "- [ ] Verify amount and due date",
                "- [ ] Process payment if approved",
                "- [ ] Update accounting records"
            ])

        elif any(keyword in subject for keyword in ['meeting', 'appointment', 'schedule']):
            actions.extend([
                "- [ ] Check calendar availability",
                "- [ ] Propose meeting times",
                "- [ ] Send calendar invitation",
                "- [ ] Prepare for meeting"
            ])

        elif any(keyword in subject for keyword in ['project', 'task', 'work']):
            actions.extend([
                "- [ ] Review project details",
                "- [ ] Assess requirements",
                "- [ ] Provide timeline or estimate",
                "- [ ] Assign resources if needed"
            ])

        # Action based on sender
        if 'boss' in sender or 'manager' in sender:
            actions.extend([
                "- [ ] Prioritize this email",
                "- [ ] Respond within 2 hours",
                "- [ ] Keep them updated on progress",
                "- [ ] Request clarification if needed"
            ])

        # Default actions
        if not actions:
            actions.extend([
                "- [ ] Review email content thoroughly",
                "- [ ] Determine appropriate response time",
                "- [ ] Take required action based on content",
                "- [ ] Move to appropriate folder after processing"
            ])

        return "## Suggested Actions\n\n" + '\n'.join(actions)

    def _generate_quick_actions(self, urgent: bool) -> str:
        """Generate quick action buttons."""
        quick_actions = [
            "- [ ] Mark as read",
            "- [ ] Archive after processing"
        ]

        if urgent:
            quick_actions.extend([
                "- [ ] Reply with 'Received - processing'",
                "- [ ] Set calendar reminder for follow-up"
            ])
        else:
            quick_actions.extend([
                "- [ ] Schedule response time",
                "- [ ] Add to task list if needed"
            ])

        return "## Quick Actions\n\n" + '\n'.join(quick_actions)

    def _generate_analysis(self, headers: Dict[str, Any], body: str, score: int) -> str:
        """Generate analysis of the email."""
        analysis = [
            f"**Priority Score:** {score} (higher is more important)",
            f"**Sender:** {headers.get('From', 'Unknown')}",
            f"**Subject:** {headers.get('Subject', 'No Subject')}"
        ]

        # Content analysis
        if 'urgent' in body.lower():
            analysis.append("**Content:** Contains urgent keywords")
        elif any(keyword in body.lower() for keyword in ['invoice', 'payment', 'billing']):
            analysis.append("**Content:** Financial request detected")
        elif any(keyword in body.lower() for keyword in ['meeting', 'appointment', 'schedule']):
            analysis.append("**Content:** Meeting request detected")
        else:
            analysis.append("**Content:** Standard business communication")

        # Age analysis
        date_header = headers.get('Date')
        if date_header:
            try:
                email_date = datetime.strptime(date_header, '%a, %d %b %Y %H:%M:%S %z')
                age_hours = (datetime.now() - email_date).total_seconds() / 3600
                analysis.append(f"**Age:** {age_hours:.1f} hours old")
            except:
                analysis.append("**Age:** Unknown")

        return "## Analysis\n\n" + '\n'.join(analysis)

if __name__ == "__main__":
    import sys

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('enhanced_gmail_watcher.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Example usage - Update vault path to match your project
    vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\Personal AI Employee Vault"
    credentials_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\gmail_credentials.json"

    watcher = EnhancedGmailWatcher(vault_path, credentials_path, check_interval=120)

    print("🚀 Enhanced Gmail Watcher started!")
    print(f"📧 Watching Gmail for important emails with priority scoring...")
    print(f"📁 Files will be created in: {watcher.needs_action}")
    print("⏸️ Pause: Ctrl+C to stop")

    # Start the watcher
    watcher.run()