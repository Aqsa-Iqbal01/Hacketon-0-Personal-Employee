"""
Enhanced LinkedIn Watcher - Monitors LinkedIn for notifications, connection requests, and posts

Triggers when new LinkedIn activities occur and creates action files for the AI to process.
Integrates with approval workflow and business context analysis.
"""

import time
import logging
import json
import random
import shutil
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from base_watcher import BaseWatcher
from datetime import datetime, timedelta
from enhanced_approval_workflow import EnhancedApprovalWorkflow
from linkedin_poster import LinkedInPoster

class LinkedInWatcher(BaseWatcher):
    def __init__(self, vault_path: str, session_path: str, check_interval: int = 300):
        """
        Initialize the enhanced LinkedIn watcher.

        Args:
            vault_path (str): Path to the Obsidian vault
            session_path (str): Path to Playwright persistent context
            check_interval (int): Time between checks in seconds
        """
        super().__init__(vault_path, check_interval)

        self.session_path = session_path
        self.processed_notifications = set()
        self.processed_requests = set()
        self.processed_posts = set()
        self.post_queue = []

        # Approval workflow integration
        self.approval_workflow = EnhancedApprovalWorkflow()

        # LinkedIn poster
        self.poster = LinkedInPoster(session_path, vault_path, post_interval=86400)

        # Business context integration
        self.business_context = self._load_business_context()

        # Set up logging
        self.logger = logging.getLogger('LinkedInWatcher')
        
        # Browser management
        self.playwright = None
        self.browser = None
        self.page = None

        # Load previously processed IDs
        self._load_processed_ids()

        self.logger.info(f'LinkedInWatcher initialized with business context integration')

    def _cleanup_session(self):
        """Clean up locked session files"""
        try:
            session_dir = Path(self.session_path)
            if session_dir.exists():
                # Remove lock files
                for lock_file in session_dir.glob('Singleton*'):
                    try:
                        lock_file.unlink()
                        self.logger.info(f'Removed lock file: {lock_file}')
                    except Exception as e:
                        self.logger.debug(f'Could not remove lock file: {e}')
                
                # Remove cache directories
                for cache_dir in ['GPUCache', 'Code Cache', 'Shared Cache', 'ShaderCache']:
                    cache_path = session_dir / cache_dir
                    if cache_path.exists():
                        try:
                            shutil.rmtree(cache_path)
                            self.logger.info(f'Removed cache: {cache_path}')
                        except:
                            pass
        except Exception as e:
            self.logger.debug(f'Session cleanup error: {e}')

    def _init_browser(self):
        """Initialize browser using system Chrome"""
        if self.browser and self.page:
            try:
                self.page.title()
                self.logger.info('Browser already running')
                return True
            except:
                self.logger.info('Browser died, reinitializing...')
                try:
                    if self.playwright:
                        self.playwright.stop()
                except:
                    pass
                self.browser = None
                self.page = None
                self.playwright = None

        try:
            self._cleanup_session()
            time.sleep(2)  # Wait longer for cleanup

            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]

            chrome_executable = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_executable = path
                    break

            if not chrome_executable:
                chrome_executable = "chrome"

            self.logger.info(f'Using Chrome: {chrome_executable}')

            self.playwright = sync_playwright().start()

            # Try to launch with persistent context (saves login session)
            try:
                self.browser = self.playwright.chromium.launch_persistent_context(
                    self.session_path,
                    executable_path=chrome_executable if os.path.exists(chrome_executable) else None,
                    headless=False,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--disable-features=TranslateUI',
                        '--disable-features=ChromeWhatsNewUI',
                        '--disable-infobars',
                    ],
                    timeout=120000,
                    slow_mo=200
                )
                self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
                self.page.set_default_timeout(90000)
                self.logger.info('Browser initialized with persistent session')
                return True
            except Exception as e:
                self.logger.warning(f'Persistent context failed: {e}')
                self.logger.info('Trying regular browser launch...')
                
                # Fallback to regular browser
                self.browser = self.playwright.chromium.launch(
                    headless=False,
                    executable_path=chrome_executable if os.path.exists(chrome_executable) else None,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--disable-features=TranslateUI',
                        '--disable-features=ChromeWhatsNewUI',
                        '--disable-infobars',
                    ]
                )
                self.page = self.browser.new_page()
                self.page.set_default_timeout(90000)
                self.logger.info('Browser initialized (session will not be saved)')
                return True
            
        except Exception as e:
            self.logger.error(f'Failed to initialize browser: {e}')
            try:
                if self.playwright:
                    self.playwright.stop()
            except:
                pass
            self.browser = None
            self.page = None
            return False

    def close_browser(self):
        """Close the browser when shutting down"""
        try:
            if self.browser:
                self.browser.close()
                self.logger.info('Browser closed')
            if self.playwright:
                self.playwright.stop()
                self.logger.info('Playwright stopped')
            self._cleanup_session()
        except Exception as e:
            self.logger.error(f'Error closing browser: {e}')

    def _load_business_context(self):
        """Load business context from vault."""
        business_context = {
            'company_name': 'Your Company Name',
            'industry': 'Technology',
            'target_audience': 'Business Professionals',
            'key_products': ['AI Solutions', 'Business Automation'],
            'value_proposition': 'Innovative solutions for business growth'
        }
        return business_context

    def _load_processed_ids(self):
        """Load previously processed notification and request IDs."""
        notifications_file = Path(self.vault_path) / 'processed_linkedin_notifications.txt'
        requests_file = Path(self.vault_path) / 'processed_linkedin_requests.txt'

        if notifications_file.exists():
            with open(notifications_file, 'r') as f:
                self.processed_notifications = set(f.read().splitlines())

        if requests_file.exists():
            with open(requests_file, 'r') as f:
                self.processed_requests = set(f.read().splitlines())

    def _save_processed_ids(self):
        """Save processed notification and request IDs."""
        notifications_file = Path(self.vault_path) / 'processed_linkedin_notifications.txt'
        requests_file = Path(self.vault_path) / 'processed_linkedin_requests.txt'

        with open(notifications_file, 'w') as f:
            f.write('\n'.join(self.processed_notifications))

        with open(requests_file, 'w') as f:
            f.write('\n'.join(self.processed_requests))

    def check_for_updates(self) -> list:
        """
        Check for new LinkedIn activities and generate business-relevant posts.

        Returns:
            list: List of new items to process
        """
        # Initialize browser if needed
        if not self.browser or not self.page:
            if not self._init_browser():
                self.logger.error('Failed to initialize browser')
                return []

        try:
            # Navigate to LinkedIn if not already there
            if 'linkedin.com' not in self.page.url:
                self.logger.info('Loading LinkedIn...')
                try:
                    self.page.goto('https://www.linkedin.com', wait_until='domcontentloaded', timeout=90000)
                    time.sleep(5)
                except Exception as e:
                    self.logger.error(f'Failed to load LinkedIn: {e}')
                    return []
            else:
                self.logger.info('LinkedIn already loaded')

            # Wait for page to stabilize
            time.sleep(3)

            self.logger.info('Checking for new notifications...')
            # Check notifications
            new_notifications = self._check_notifications(self.page)

            self.logger.info('Checking for connection requests...')
            # Check connection requests
            new_requests = self._check_connection_requests(self.page)

            # Combine all new items
            new_items = new_notifications + new_requests

            # Show console status
            if new_items:
                notif_count = len([n for n in new_items if n['type'] in ['notification', 'connection_accepted']])
                req_count = len([n for n in new_items if n['type'] == 'connection_request'])
                
                print(f"\n{'='*60}")
                print(f"  📊 LINKEDIN ACTIVITY DETECTED!")
                print(f"{'='*60}")
                print(f"     🔔 Notifications: {notif_count}")
                print(f"     🤝 Connection Requests: {req_count}")
                print(f"     📝 Total Items: {len(new_items)}")
                print(f"{'='*60}\n")
                
                self.logger.info(f'Found {len(new_items)} new LinkedIn items ({notif_count} notifications, {req_count} requests)')
            else:
                print(f"\n⏳  No new LinkedIn activity (next check: 5 min)")
                self.logger.info('No new LinkedIn activity detected')

            self.logger.debug(f'Found {len(new_items)} new LinkedIn items')

            return new_items

        except Exception as e:
            self.logger.error(f'Error checking LinkedIn updates: {e}')
            self.browser = None
            self.page = None
            return []

    def _check_notifications(self, page):
        """Check for new LinkedIn notifications including accepted connections."""
        new_notifications = []

        try:
            # Navigate to notifications page for accurate detection
            try:
                self.logger.debug('Navigating to notifications page...')
                page.goto('https://www.linkedin.com/notifications/', wait_until='domcontentloaded', timeout=90000)
                time.sleep(5)  # Wait for page to load
            except Exception as e:
                self.logger.error(f'Failed to navigate to notifications page: {e}')
                return new_notifications

            # Method 1: Check notification badge count on bell icon
            try:
                # Try multiple selector patterns for notification badge
                badge_selectors = [
                    'button[aria-label*="notification"] span[aria-hidden="true"]',
                    'div.notifications-nav__button span.notification-badge',
                    'button.lit-navicon__notification-button span',
                    '[data-test="notifications-badge"]',
                    'span.legacy-navicon__notification-count',
                    'nav[aria-label*="Notifications"] span[aria-hidden="true"]',
                ]
                
                count_text = None
                for selector in badge_selectors:
                    try:
                        notif_badge = page.locator(selector).first
                        if notif_badge.is_visible(timeout=3000):
                            count_text = notif_badge.text_content(timeout=3000).strip()
                            if count_text:
                                self.logger.debug(f'Found badge with selector: {selector}, count: {count_text}')
                                break
                    except:
                        continue

                if count_text and count_text.isdigit():
                    notification_count = int(count_text)

                    if notification_count > 0:
                        notification_id = f"NOTIF_{int(time.time())}"

                        new_notifications.append({
                            'type': 'notification',
                            'id': notification_id,
                            'text': f'You have {notification_count} new notifications',
                            'time': 'Just now',
                            'notification_type': 'General',
                            'relevance': 0.5,
                            'requires_action': True
                        })

                        self.logger.info(f'🔔 Found {notification_count} unread notifications')
                else:
                    self.logger.debug('No notification badge count found')
            except Exception as e:
                self.logger.debug(f'No notification badge found: {e}')

            # Method 2: Parse actual notifications from the notifications page
            try:
                self.logger.debug('Looking for notification items...')
                
                # Wait for notification list to appear
                try:
                    page.wait_for_selector('ul.scaffold-layout__list, div.notification-items-list-container, section[aria-label*="notification"], [role="list"]', timeout=15000)
                    time.sleep(3)
                except:
                    self.logger.debug('Notification list container not found, continuing anyway')

                # Try to find notification items with multiple selectors
                notification_selectors = [
                    'ul.scaffold-layout__list > li',
                    'ul.scaffold-layout__list li',
                    '[role="list"] > li',
                    '[role="list"] > div',
                    'div.notification-item',
                    'li.notification-item',
                    '[data-test="notification-item"]',
                    'div.mb2',  # LinkedIn common class
                ]
                
                notif_items = None
                for selector in notification_selectors:
                    try:
                        items = page.locator(selector)
                        count = items.count()
                        if count > 0:
                            self.logger.debug(f'Found {count} items with selector: {selector}')
                            notif_items = items
                            break
                    except:
                        continue

                if notif_items:
                    count = min(notif_items.count(), 15)  # Check up to 15 recent notifications
                    
                    self.logger.info(f'📋 Found {count} notification items on page')
                    
                    for i in range(count):
                        try:
                            item = notif_items.nth(i)
                            if not item.is_visible(timeout=2000):
                                continue
                                
                            # Get full text content from the notification
                            text = item.text_content(timeout=5000).strip()
                            
                            # Clean up the text - remove extra whitespace
                            text = ' '.join(text.split())
                            
                            # Skip empty or very short items
                            if len(text) < 10:
                                continue
                            
                            self.logger.debug(f'Notification {i}: {text[:150]}')

                            # Check for accepted connection notifications
                            if 'accepted your connection invitation' in text.lower() or \
                               'is now connected with you' in text.lower() or \
                               'joined your network' in text.lower() or \
                               'accepted your invitation' in text.lower():

                                notification_id = f"ACCEPT_{int(time.time())}_{i}"

                                new_notifications.append({
                                    'type': 'connection_accepted',
                                    'id': notification_id,
                                    'text': text[:200],
                                    'time': 'Just now',
                                    'notification_type': 'Connection Accepted',
                                    'relevance': 0.8,
                                    'requires_action': True
                                })

                                self.logger.info(f'🤝 Connection accepted! {text[:50]}')
                            
                            # Check for congratulations notifications (work anniversary, new position)
                            elif 'congratulate' in text.lower() or 'work anniversary' in text.lower() or 'new position' in text.lower():
                                notification_id = f"CONGRATS_{int(time.time())}_{i}"
                                new_notifications.append({
                                    'type': 'notification',
                                    'id': notification_id,
                                    'text': text[:200],
                                    'time': 'Just now',
                                    'notification_type': 'Congratulations',
                                    'relevance': 0.5,
                                    'requires_action': True
                                })
                                self.logger.info(f'🎉 Congratulations: {text[:60]}')
                            
                            # Check for reactions/engagement notifications
                            elif any(keyword in text.lower() for keyword in [
                                'reacted to', 'liked your', 'commented on', 'mentioned you',
                                'others reacted', 'reactions', 'comments on your'
                            ]):
                                notification_id = f"ENGAGE_{int(time.time())}_{i}"
                                new_notifications.append({
                                    'type': 'notification',
                                    'id': notification_id,
                                    'text': text[:200],
                                    'time': 'Just now',
                                    'notification_type': 'Engagement',
                                    'relevance': 0.6,
                                    'requires_action': True
                                })
                                self.logger.info(f'💬 Engagement: {text[:60]}')
                            
                            # Check for profile views
                            elif 'viewed your profile' in text.lower():
                                notification_id = f"PROFILE_{int(time.time())}_{i}"
                                new_notifications.append({
                                    'type': 'notification',
                                    'id': notification_id,
                                    'text': text[:200],
                                    'time': 'Just now',
                                    'notification_type': 'Profile View',
                                    'relevance': 0.4,
                                    'requires_action': True
                                })
                                self.logger.info(f'👁️ Profile view: {text[:60]}')
                            
                            # Generic notification fallback
                            elif len(text) > 30:
                                notification_id = f"NOTIF_{int(time.time())}_{i}"
                                new_notifications.append({
                                    'type': 'notification',
                                    'id': notification_id,
                                    'text': text[:200],
                                    'time': 'Just now',
                                    'notification_type': 'General',
                                    'relevance': 0.4,
                                    'requires_action': True
                                })
                                self.logger.info(f'📌 Notification: {text[:60]}')
                                
                        except Exception as e:
                            self.logger.debug(f'Error processing notification {i}: {e}')
                            continue
                else:
                    self.logger.debug('No notification items found on page')
                    
            except Exception as e:
                self.logger.debug(f'Could not check notification items: {e}')

        except Exception as e:
            self.logger.error(f'Error checking notifications: {e}')

        return new_notifications

    def _analyze_business_relevance(self, text: str) -> float:
        """Analyze business relevance of notification text."""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        
        # High-value business keywords
        high_value_keywords = [
            'job opportunity', 'hiring', 'position', 'interview',
            'partnership', 'collaboration', 'investment', 'client',
            'project', 'contract', 'proposal', 'business',
            'revenue', 'sales', 'lead', 'prospect'
        ]
        
        # Medium-value keywords
        medium_value_keywords = [
            'connection', 'network', 'industry', 'professional',
            'skill', 'certification', 'course', 'learning',
            'article', 'post', 'comment', 'mention'
        ]
        
        # Calculate relevance score
        score = 0.0
        for keyword in high_value_keywords:
            if keyword in text_lower:
                score += 0.3
        
        for keyword in medium_value_keywords:
            if keyword in text_lower:
                score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)

    def _analyze_connection_relevance(self, name: str, headline: str, industry: str) -> float:
        """Analyze business relevance of connection request."""
        score = 0.0
        
        # Check headline for relevant keywords
        headline_lower = headline.lower() if headline else ''
        industry_lower = industry.lower() if industry else ''
        
        # High-value connection keywords
        high_value_keywords = [
            'ceo', 'founder', 'director', 'manager', 'executive',
            'investor', 'venture', 'capital', 'partner',
            'head of', 'vp', 'vice president', 'chief'
        ]
        
        # Industry relevance
        relevant_industries = [
            'technology', 'software', 'finance', 'consulting',
            'marketing', 'sales', 'healthcare', 'education'
        ]
        
        for keyword in high_value_keywords:
            if keyword in headline_lower:
                score += 0.2
        
        for ind in relevant_industries:
            if ind in industry_lower or ind in headline_lower:
                score += 0.1
        
        # Check for mutual connections (simplified)
        if 'mutual' in str(name).lower():
            score += 0.1
        
        return min(score, 1.0)

    def _should_create_action(self, text: str, relevance: float) -> bool:
        """Determine if an action file should be created."""
        # Always create action for high relevance items
        if relevance >= 0.7:
            return True
        
        # Check for urgent keywords
        urgent_keywords = ['urgent', 'asap', 'immediate', 'deadline', 'today']
        text_lower = text.lower() if text else ''
        
        for keyword in urgent_keywords:
            if keyword in text_lower:
                return True
        
        # For lower relevance, still create action but mark as normal priority
        return relevance >= 0.3

    def _generate_business_posts(self) -> list:
        """Generate business-relevant posts based on business goals."""
        new_posts = []
        
        try:
            # Load business goals
            business_goals_file = self.vault_path / 'Business_Goals.md'
            if not business_goals_file.exists():
                return new_posts
            
            with open(business_goals_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Generate post based on business goals
            post_id = f"POST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Check if we should post (based on last post time)
            last_post_file = self.vault_path / 'last_linkedin_post.txt'
            if last_post_file.exists():
                with open(last_post_file, 'r') as f:
                    try:
                        last_post = datetime.fromisoformat(f.read().strip())
                        hours_since_post = (datetime.now() - last_post).total_seconds() / 3600
                        if hours_since_post < 24:
                            return new_posts  # Not time to post yet
                    except:
                        pass
            
            # Generate post content
            post_content = self.poster.generate_post_content()
            
            new_posts.append({
                'type': 'business_post',
                'id': post_id,
                'content': post_content['content'],
                'template': post_content['template'],
                'category': post_content['category'],
                'relevance': 0.8,  # High relevance for business posts
                'requires_action': True
            })
            
            self.logger.info(f'Generated business post: {post_content["template"]}')
            
        except Exception as e:
            self.logger.error(f'Error generating business posts: {e}')
        
        return new_posts

    def _check_connection_requests(self, page):
        """Check for new LinkedIn connection requests from the My Network page."""
        new_requests = []

        try:
            # Navigate to My Network page - force main page not grow/manage subpages
            try:
                self.logger.debug('Navigating to My Network page...')
                
                # Go to main mynetwork page first
                page.goto('https://www.linkedin.com/mynetwork/', wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)
                
                # Check current URL
                current_url = page.url
                self.logger.debug(f'Current URL after navigation: {current_url}')
                
                # LinkedIn often redirects to /grow/ or /manage/ - we need to go back
                if '/grow/' in current_url or '/manage/' in current_url:
                    self.logger.debug('LinkedIn redirected to sub-page, using go_back()...')
                    # Try going back
                    page.go_back(timeout=30000)
                    time.sleep(3)
                    
                    # If still on wrong page, navigate directly again
                    current_url = page.url
                    if '/grow/' in current_url or '/manage/' in current_url:
                        self.logger.debug('go_back() did not work, navigating to invitations page directly...')
                        # Navigate to the invitations management page
                        page.goto('https://www.linkedin.com/mynetwork/invitation-manager/', wait_until='domcontentloaded', timeout=60000)
                        time.sleep(5)
                
            except Exception as e:
                self.logger.error(f'Failed to navigate to My Network page: {e}')
                return new_requests

            # Method 1: Count "Accept" buttons (most reliable method)
            try:
                self.logger.debug('Searching for Accept buttons...')
                
                # Wait for page to fully load
                try:
                    page.wait_for_load_state('networkidle', timeout=15000)
                    time.sleep(2)
                except:
                    self.logger.debug('Network idle timeout, continuing anyway')
                
                # Find all "Accept" buttons - each one is a connection request
                accept_buttons = page.locator('button:has-text("Accept")')
                accept_count = accept_buttons.count()
                
                if accept_count > 0:
                    self.logger.info(f'🤝 Found {accept_count} pending connection request(s) via Accept buttons')
                    
                    # Get details from first request
                    try:
                        first_button = accept_buttons.first
                        # Navigate up to find the card containing this button
                        parent = first_button.locator('xpath=ancestor::div[contains(@class, "invitation-card")] | xpath=ancestor::li | xpath=..')
                        text = parent.text_content(timeout=3000).strip()
                        name = text.split('\n')[0].strip() if '\n' in text else text[:50]
                        
                        request_id = f"REQ_{int(time.time())}"
                        new_requests.append({
                            'type': 'connection_request',
                            'id': request_id,
                            'name': name if name else f'{accept_count} pending request(s)',
                            'headline': text[:100] if text else 'Check My Network page',
                            'mutual': '',
                            'industry': '',
                            'relevance': 0.6,
                            'requires_action': True
                        })
                        self.logger.info(f'🤝 Connection request from: {name[:40] if name else "Unknown"}')
                    except Exception as e:
                        self.logger.debug(f'Could not get request details: {e}')
                        request_id = f"REQ_{int(time.time())}"
                        new_requests.append({
                            'type': 'connection_request',
                            'id': request_id,
                            'name': f'{accept_count} pending request(s)',
                            'headline': 'Check My Network page',
                            'mutual': '',
                            'industry': '',
                            'relevance': 0.6,
                            'requires_action': True
                        })
                else:
                    self.logger.debug('No Accept buttons found on current page')
                    
            except Exception as e:
                self.logger.debug(f'Error counting Accept buttons: {e}')

            # Method 2: Also check for invitation badge (backup)
            if not new_requests:
                try:
                    badge_selectors = [
                        'button[aria-label*="invitation"] span[aria-hidden="true"]',
                        'button[aria-label*="Invitation"] span[aria-hidden="true"]',
                        '[data-test="invitations-badge"]',
                        'span.mynetwork-nav__badge',
                        'nav[aria-label*="My Network"] span[aria-hidden="true"]',
                    ]
                    
                    count_text = None
                    for selector in badge_selectors:
                        try:
                            conn_badge = page.locator(selector).first
                            if conn_badge.is_visible(timeout=2000):
                                count_text = conn_badge.text_content(timeout=2000).strip()
                                if count_text:
                                    self.logger.debug(f'Found invitation badge: {count_text}')
                                    break
                        except:
                            continue

                    if count_text and count_text.isdigit() and int(count_text) > 0:
                        request_count = int(count_text)
                        request_id = f"REQ_{int(time.time())}"
                        new_requests.append({
                            'type': 'connection_request',
                            'id': request_id,
                            'name': f'{request_count} pending requests',
                            'headline': 'Check My Network page',
                            'mutual': '',
                            'industry': '',
                            'relevance': 0.6,
                            'requires_action': True
                        })
                        self.logger.info(f'🤝 Found {request_count} pending connection requests')
                except Exception as e:
                    self.logger.debug(f'No badge found: {e}')

        except Exception as e:
            self.logger.error(f'Error checking connection requests: {e}')

        return new_requests

    def create_action_file(self, item) -> Path:
        """
        Create an action file for a LinkedIn item with approval workflow integration.

        Args:
            item: The LinkedIn item to process

        Returns:
            Path: Path to the created action file
        """
        try:
            if item['type'] == 'notification':
                if item.get('requires_action', True):
                    filepath = self._create_notification_file(item)
                    self.processed_notifications.add(item['id'])
                    if item.get('relevance', 0) > 0.8:
                        self._auto_approve_notification(item)

            elif item['type'] == 'connection_accepted':
                if item.get('requires_action', True):
                    filepath = self._create_connection_accepted_file(item)
                    self.processed_notifications.add(item['id'])
                    self.logger.info(f'✅ Created file for accepted connection')

            elif item['type'] == 'connection_request':
                if item.get('requires_action', True):
                    filepath = self._create_connection_request_file(item)
                    self.processed_requests.add(item['id'])
                    if item.get('relevance', 0) > 0.9:
                        self._auto_approve_connection(item)

            elif item['type'] == 'business_post':
                filepath = self._create_business_post_file(item)
                self.processed_posts.add(item['id'])
                if item.get('relevance', 0) > 0.7:
                    self._auto_approve_post(item)

            else:
                return Path('')

            # Save processed IDs
            self._save_processed_ids()

            # Beautiful console output
            type_emoji = {
                'notification': '🔔',
                'connection_accepted': '✅',
                'connection_request': '🤝',
                'business_post': '📝'
            }.get(item['type'], '📌')

            print(f"\n{'='*60}")
            print(f"  {type_emoji} LINKEDIN {item['type'].upper().replace('_', ' ')} DETECTED!")
            print(f"{'='*60}")
            
            if item['type'] == 'connection_accepted':
                print(f"  📝 {item.get('text', 'N/A')[:70]}")
                print(f"  🏷️  Relevance: {item.get('relevance', 0):.0%}")
            elif item['type'] == 'notification':
                print(f"  📝 {item.get('text', 'N/A')[:70]}")
                print(f"  🏷️  Type: {item.get('notification_type', 'General')}")
            elif item['type'] == 'connection_request':
                print(f"  👤 Name: {item.get('name', 'Unknown')}")
                print(f"  💼 Details: {item.get('headline', 'N/A')[:50]}")
                print(f"  🏷️  Relevance: {item.get('relevance', 0):.0%}")
            elif item['type'] == 'business_post':
                print(f"  📝 Template: {item.get('template', 'General')}")
                print(f"  📂 Category: {item.get('category', 'General')}")
            
            print(f"  ✅ Action File: {filepath.name}")
            print(f"{'='*60}\n")

            self.logger.info(f'Created action file for LinkedIn {item["type"]}: {item.get("id", "unknown")}')
            return filepath

        except Exception as e:
            self.logger.error(f'Error creating action file for LinkedIn {item.get("type", "unknown")}: {e}')
            return Path('')

    def _create_notification_file(self, notification) -> Path:
        """Create an action file for a LinkedIn notification."""
        content = f"""---
type: linkedin_notification
source: linkedin
id: {notification['id']}
text: {notification['text']}
time: {notification['time']}
type: {notification['type']}
status: pending
---

# LinkedIn Notification

**Type:** {notification['type']}
**Time:** {notification['time']}

## Notification Details

**Text:** {notification['text']}

## Suggested Actions

- [ ] Review notification content
- [ ] Determine appropriate response
- [ ] Take required action based on notification
- [ ] Move to appropriate folder after processing

## Common Notification Types

- **Job Updates:** Review new job postings or updates
- **Connection Updates:** Check connection status changes
- **Company Updates:** Review company news and updates
- [ ] Reply or engage with content if appropriate
- [ ] Archive notification after processing

---
*Generated by LinkedIn Watcher*
"""

        filepath = self.needs_action / f'LINKEDIN_NOTIFICATION_{notification['id']}.md'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _auto_approve_notification(self, notification):
        """Auto-approve high-relevance notifications."""
        try:
            # Create approval request for notification response
            approval_data = {
                'type': 'linkedin_notification_response',
                'description': f'Auto-respond to high-relevance LinkedIn notification: {notification["text"]}',
                'justification': 'High business relevance (' + str(notification.get('relevance', 0)) + ')',
                'metadata': {
                    'notification_id': notification['id'],
                    'notification_text': notification['text'],
                    'relevance_score': notification.get('relevance', 0)
                }
            }
            self.approval_workflow.request_approval(approval_data)
            self.logger.info(f'Auto-approval requested for notification: {notification["id"]}')
        except Exception as e:
            self.logger.error(f'Error auto-approving notification: {e}')

    def _auto_approve_connection(self, request):
        """Auto-approve high-relevance connection requests."""
        try:
            # Create approval request for connection acceptance
            approval_data = {
                'type': 'linkedin_connection_accept',
                'description': f'Auto-accept high-relevance LinkedIn connection: {request["name"]}',
                'justification': 'High business relevance (' + str(request.get('relevance', 0)) + ')',
                'metadata': {
                    'request_id': request['id'],
                    'name': request['name'],
                    'headline': request['headline'],
                    'mutual_connections': request['mutual'],
                    'industry': request.get('industry', ''),
                    'relevance_score': request.get('relevance', 0)
                }
            }
            self.approval_workflow.request_approval(approval_data)
            self.logger.info(f'Auto-approval requested for connection: {request["name"]}')
        except Exception as e:
            self.logger.error(f'Error auto-approving connection: {e}')

    def _auto_approve_post(self, post):
        """Auto-approve high-relevance business posts."""
        try:
            # Create approval request for post publishing
            approval_data = {
                'type': 'linkedin_post_publish',
                'description': f'Auto-publish high-relevance LinkedIn post: {post["content"][:50]}...',
                'justification': 'High business relevance (' + str(post.get('relevance', 0)) + ')',
                'metadata': {
                    'post_id': post['id'],
                    'content_preview': post['content'][:100],
                    'relevance_score': post.get('relevance', 0),
                    'category': post.get('category', 'general')
                }
            }
            self.approval_workflow.request_approval(approval_data)
            self.logger.info(f'Auto-approval requested for post: {post["id"]}')
        except Exception as e:
            self.logger.error(f'Error auto-approving post: {e}')

    def _create_notification_file(self, notification) -> Path:
        """Create an action file for a LinkedIn notification."""
        content = f"""---
type: linkedin_notification
source: linkedin
id: {notification['id']}
text: {notification['text']}
time: {notification['time']}
notification_type: {notification['notification_type']}
status: pending
relevance: {notification.get('relevance', 0)}
---

# LinkedIn Notification

**Type:** {notification['notification_type']}
**Time:** {notification['time']}

## Notification Details

**Text:** {notification['text']}

## Suggested Actions

- [ ] Review notification content
- [ ] Determine appropriate response
- [ ] Take required action based on notification
- [ ] Move to appropriate folder after processing

## Common Notification Types

- **Job Updates:** Review new job postings or updates
- **Connection Updates:** Check connection status changes
- **Company Updates:** Review company news and updates
- [ ] Reply or engage with content if appropriate
- [ ] Archive notification after processing

---
*Generated by LinkedIn Watcher*
"""

        filepath = self.needs_action / f'LINKEDIN_NOTIFICATION_{notification["id"]}.md'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _create_connection_accepted_file(self, connection) -> Path:
        """Create an action file for an accepted connection."""
        content = f"""---
type: linkedin_connection_accepted
source: linkedin
id: {connection['id']}
text: {connection['text']}
time: {connection['time']}
status: pending
relevance: {connection.get('relevance', 0)}
---

# LinkedIn Connection Accepted ✅

**Notification:** {connection['text']}
**Time:** {connection['time']}
**Relevance Score:** {connection.get('relevance', 0):.1%}

## What Happened

Someone accepted your connection request on LinkedIn.

## Suggested Actions

- [ ] Review the new connection's profile
- [ ] Send a personalized thank you message
- [ ] Note any business opportunities
- [ ] Add to CRM or contact management system
- [ ] Engage with their recent posts
- [ ] Schedule follow-up if relevant

## Networking Best Practices

1. **Personalize:** Send a custom message within 24 hours
2. **Research:** Review their profile for common interests
3. **Engage:** Like or comment on their recent posts
4. **Follow-up:** Schedule a call if there's business potential

---
*Generated by LinkedIn Watcher*
"""

        filepath = self.needs_action / f'LINKEDIN_CONNECTION_ACCEPTED_{connection["id"]}.md'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _create_business_post_file(self, post) -> Path:
        """Create an action file for a business post."""
        content = f"""---
type: linkedin_business_post
source: linkedin
id: {post['id']}
template: {post['template']}
category: {post['category']}
status: pending
relevance: {post.get('relevance', 0)}
---

# LinkedIn Business Post

**Template:** {post['template']}
**Category:** {post['category']}
**Relevance Score:** {post.get('relevance', 0)}

## Post Content

{post['content']}

## Suggested Actions

- [ ] Review post content
- [ ] Check for any errors or improvements
- [ ] Approve for posting
- [ ] Schedule post for optimal time
- [ ] Monitor engagement after posting

## Posting Guidelines

1. **Professional Tone:** Ensure content is professional and engaging
2. **Relevant Hashtags:** Add 3-5 relevant hashtags
3. **Timing:** Post during business hours (9 AM - 5 PM)
4. **Engagement:** Respond to comments within 24 hours

## Approval Required

This post requires human approval before publishing.

---
*Generated by LinkedIn Watcher*
"""

        filepath = self.needs_action / f'LINKEDIN_POST_{post["id"]}.md'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _create_connection_request_file(self, request) -> Path:
        """Create an action file for a LinkedIn connection request."""
        content = f"""---
type: linkedin_connection_request
source: linkedin
id: {request['id']}
name: {request['name']}
headline: {request['headline']}
mutual_connections: {request['mutual']}
status: pending
relevance: {request.get('relevance', 0)}
---

# LinkedIn Connection Request

**From:** {request['name']}
**Headline:** {request['headline']}
**Mutual Connections:** {request['mutual']}
**Relevance Score:** {request.get('relevance', 0)}

## Connection Request Details

A new connection request has been received. Review the profile and decide whether to accept or ignore.

## Suggested Actions

- [ ] Review the person's profile
- [ ] Check mutual connections
- [ ] Evaluate relevance to your network
- [ ] Decide whether to accept or ignore

## Decision Options

### Accept Connection
- [ ] Review their profile and experience
- [ ] Check if they're in your industry
- [ ] Evaluate potential mutual benefits
- [ ] Send personalized acceptance message

### Ignore Request
- [ ] If not relevant to your network
- [ ] If spam or irrelevant connection
- [ ] If you don't know the person

## Profile Information

**Name:** {request['name']}
**Headline:** {request['headline']}
**Mutual Connections:** {request['mutual']}

---
*Generated by LinkedIn Watcher*
"""

        filepath = self.needs_action / f'LINKEDIN_REQUEST_{request["id"]}.md'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

if __name__ == "__main__":
    import sys
    import atexit
    
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    # Beautiful colored logging
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': '\033[36m',     # Cyan
            'INFO': '\033[32m',      # Green
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',     # Red
            'CRITICAL': '\033[35m',  # Magenta
            'RESET': '\033[0m'       # Reset
        }
        
        def format(self, record):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
            return super().format(record)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('linkedin_watcher.log', encoding='utf-8', mode='a'),
        ]
    )

    # Console handler with colors - INFO level for clean output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S'))
    logging.getLogger().addHandler(console_handler)

    # Example usage
    vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\Personal AI Employee Vault"
    session_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\linkedin_session"

    watcher = LinkedInWatcher(vault_path, session_path, check_interval=300)
    
    # Beautiful startup banner
    print("\n" + "=" * 60)
    print("  💼  LINKEDIN PROFESSIONAL WATCHER")
    print("=" * 60)
    print(f"  📂 Vault: {vault_path.split(chr(92))[-1]}")
    print(f"  ⏱️  Check Interval: 5 minutes")
    print(f"  🔔 Monitoring: Notifications & Connections")
    print("=" * 60)
    print("  ✅ Watching for activity...")
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    atexit.register(watcher.close_browser)

    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("  🛑  Stopped by user")
        print("=" * 60 + "\n")
        watcher.close_browser()