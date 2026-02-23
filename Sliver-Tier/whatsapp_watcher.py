"""
WhatsApp Watcher - Monitors WhatsApp Web for new messages and creates action files
"""

import time
import logging
import os
import shutil
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from base_watcher import BaseWatcher
from datetime import datetime

class WhatsAppWatcher(BaseWatcher):
    def __init__(self, vault_path: str, session_path: str, check_interval: int = 30):
        super().__init__(vault_path, check_interval)
        self.session_path = session_path
        self.processed_messages = set()
        self.keywords = ['urgent', 'asap', 'help', 'invoice', 'payment', 'important', 'need']
        self.logger = logging.getLogger('WhatsAppWatcher')
        self._load_processed_ids()
        self.logger.info('WhatsAppWatcher initialized')
        self.playwright = None
        self.browser = None
        self.page = None

    def _cleanup_session(self):
        """Clean up locked session files"""
        try:
            session_dir = Path(self.session_path)
            if session_dir.exists():
                # Remove all lock files
                for lock_file in session_dir.glob('Singleton*'):
                    try:
                        lock_file.unlink()
                        self.logger.info(f'Removed lock file: {lock_file}')
                    except Exception as e:
                        self.logger.debug(f'Could not remove lock file: {e}')
                # Remove Chrome lock files
                for lock_file in session_dir.glob('*.lock'):
                    try:
                        lock_file.unlink()
                        self.logger.info(f'Removed .lock file: {lock_file}')
                    except Exception as e:
                        self.logger.debug(f'Could not remove .lock file: {e}')
                # Remove Code Cache
                for cache_dir in ['GPUCache', 'Code Cache', 'Shared Cache']:
                    cache_path = session_dir / cache_dir
                    if cache_path.exists():
                        try:
                            shutil.rmtree(cache_path)
                            self.logger.info(f'Removed cache: {cache_path}')
                        except Exception as e:
                            self.logger.debug(f'Could not remove cache: {e}')
                # Remove Default folder lock
                default_folder = session_dir / 'Default'
                if default_folder.exists():
                    for lock_file in default_folder.glob('Singleton*'):
                        try:
                            lock_file.unlink()
                            self.logger.info(f'Removed Default lock: {lock_file}')
                        except Exception as e:
                            self.logger.debug(f'Could not remove Default lock: {e}')
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
            # Clean up session before starting
            self._cleanup_session()
            time.sleep(1)  # Give time for locks to be released

            # Find Chrome executable
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
            
            # Launch with better stability options
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
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ],
                timeout=120000,
                slow_mo=500,
                ignore_default_args=['--enable-automation'],
            )
            self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
            self.page.set_default_timeout(90000)
            
            # Hide automation flags
            try:
                self.page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
            except:
                pass
            
            self.logger.info('Browser initialized')
            return True
        except Exception as e:
            self.logger.error(f'Failed to initialize browser: {e}')
            # Clean up on failure
            try:
                if self.playwright:
                    self.playwright.stop()
            except:
                pass
            self.browser = None
            self.page = None
            return False

    def _load_processed_ids(self):
        messages_file = Path(self.vault_path) / 'processed_whatsapp_messages.txt'
        if messages_file.exists():
            with open(messages_file, 'r') as f:
                self.processed_messages = set(f.read().splitlines())

    def _save_processed_ids(self):
        """Save processed message IDs to file"""
        try:
            messages_file = Path(self.vault_path) / 'processed_whatsapp_messages.txt'
            with open(messages_file, 'w') as f:
                f.write('\n'.join(self.processed_messages))
        except Exception as e:
            self.logger.error(f'Error saving processed IDs: {e}')

    def close_browser(self):
        """Close the browser when shutting down"""
        try:
            if self.browser:
                self.browser.close()
                self.logger.info('Browser closed')
            if self.playwright:
                self.playwright.stop()
                self.logger.info('Playwright stopped')
            # Clean up session after closing
            self._cleanup_session()
        except Exception as e:
            self.logger.error(f'Error closing browser: {e}')

    def check_for_updates(self) -> list:
        new_messages = []

        if not self.browser or not self.page:
            if not self._init_browser():
                self.logger.error('Failed to initialize browser')
                return []

        try:
            # Navigate to WhatsApp Web if needed
            if 'web.whatsapp.com' not in self.page.url:
                self.logger.info('Loading WhatsApp Web...')
                try:
                    self.page.goto('https://web.whatsapp.com', wait_until='domcontentloaded', timeout=90000)
                    time.sleep(5)
                except Exception as e:
                    self.logger.error(f'Failed to load WhatsApp Web: {e}')
                    try:
                        self.page.reload(wait_until='domcontentloaded', timeout=60000)
                        time.sleep(3)
                    except:
                        return []

            # Wait for chat list with multiple fallback selectors
            chat_list_found = False
            selectors = [
                '[data-testid="chat-list"]',
                '#pane-side',
                'div[aria-label="Chats"]',
                '[data-tab="3"]'
            ]

            for selector in selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=10000, state='visible')
                    chat_list_found = True
                    self.logger.debug(f'Found chat list: {selector}')
                    break
                except:
                    continue

            if not chat_list_found:
                self.logger.info("Please scan QR code in browser...")
                for selector in selectors:
                    try:
                        self.page.wait_for_selector(selector, timeout=60000, state='visible')
                        chat_list_found = True
                        self.logger.debug(f'Chat list found after QR scan: {selector}')
                        break
                    except:
                        continue

                if not chat_list_found:
                    self.logger.error('Chat list not found after QR scan')
                    return []

            time.sleep(2)

            # Find all chats
            chat_selectors = [
                '[data-testid="chat-list"] [role="row"]',
                '[data-testid="chat-list"] > div > div',
                '#pane-side div[role="row"]',
                'div[data-tab="3"] > div[role="row"]'
            ]

            chats = None
            for selector in chat_selectors:
                try:
                    chats = self.page.locator(selector)
                    count = chats.count()
                    if count > 0:
                        self.logger.debug(f'Found {count} chats using: {selector}')
                        break
                except:
                    continue

            if not chats:
                chats = self.page.locator('#pane-side div[role="row"]')

            count = chats.count()
            self.logger.debug(f"Total chats: {count}")

            # Process recent chats
            for i in range(min(count, 10)):
                try:
                    chat = chats.nth(i)
                    if not chat.is_visible(timeout=2000):
                        continue

                    # Get chat preview text
                    preview_text = chat.inner_text(timeout=2000)
                    preview_lines = preview_text.split('\n')

                    if len(preview_lines) < 2:
                        continue

                    title = preview_lines[0].strip()
                    
                    # Get message from preview (skip title and timestamps)
                    preview_message = ''
                    for line in preview_lines[1:]:
                        line = line.strip()
                        if line and not any(x in line for x in ['AM', 'PM', 'Yesterday', 'Today']):
                            preview_message = line
                            break
                    
                    if not preview_message and len(preview_lines) > 1:
                        preview_message = preview_lines[-1].strip()

                    if not title or not preview_message:
                        continue

                    # Check for keywords in preview
                    text_lower = preview_message.lower()
                    if any(kw in text_lower for kw in self.keywords):
                        # Click on chat to get full message
                        try:
                            chat.click()
                            time.sleep(1)
                            
                            # Get full message from chat header
                            try:
                                messagebubble = self.page.locator('div[data-testid="message-container"] span[title]').first
                                full_message = messagebubble.inner_text(timeout=3000)
                                if full_message:
                                    preview_message = full_message
                            except:
                                pass
                            
                            # Go back to chat list
                            self.page.keyboard.press('Escape')
                            time.sleep(0.5)
                        except Exception as e:
                            self.logger.debug(f'Could not click chat: {e}')
                        
                        # Create unique ID
                        msg_id = f"{title}_{preview_message[:50]}".replace(' ', '_').replace('/', '_').replace('\\', '_')
                        
                        if msg_id not in self.processed_messages:
                            priority = 'high' if any(kw in text_lower for kw in ['urgent', 'asap', 'help']) else 'normal'
                            new_messages.append({
                                'id': msg_id,
                                'from': title,
                                'message': preview_message,
                                'priority': priority
                            })
                            # Beautiful console output for new messages
                            priority_emoji = "🔴" if priority == 'high' else "🟢"
                            print(f"\n{'='*60}")
                            print(f"  {priority_emoji} NEW MESSAGE DETECTED!")
                            print(f"{'='*60}")
                            print(f"  👤 From: {title}")
                            print(f"  📝 Message: {preview_message[:60]}")
                            print(f"  🏷️  Priority: {priority.upper()}")
                            print(f"{'='*60}\n")
                except Exception as e:
                    self.logger.debug(f"Chat {i} error: {e}")
                    continue

            self.logger.debug(f"Found {len(new_messages)} new messages")
            return new_messages

        except Exception as e:
            self.logger.error(f'Error checking WhatsApp updates: {e}')
            self.browser = None
            self.page = None
            return []

    def create_action_file(self, message) -> Path:
        try:
            # Get next file number
            existing_files = list(self.needs_action.glob('WHATSAPP_*.md'))
            next_num = len(existing_files) + 1
            
            filepath = self.needs_action / f"WHATSAPP_{next_num}.md"
            
            content = f"""---
type: whatsapp_message
source: whatsapp
id: {message['id']}
from: {message['from']}
message: {message['message']}
priority: {message['priority']}
received: {datetime.now().isoformat()}
status: pending
---

# WhatsApp Message

**From:** {message['from']}
**Priority:** {message['priority'].upper()}
**Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Message Content

{message['message']}

## Actions

- [ ] Review and respond
- [ ] Take required action

---
*Generated by WhatsApp Watcher*
"""
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.processed_messages.add(message['id'])
            self._save_processed_ids()
            # Beautiful console output for file creation
            print(f"  ✅ Action File Created!")
            print(f"  📄 File: {filepath.name}")
            print(f"  📍 Location: Needs_Action/")
            print(f"{'='*60}\n")
            return filepath
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}')
            return Path('')

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
            logging.FileHandler('whatsapp.md', encoding='utf-8', mode='a'),
        ]
    )
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S'))
    logging.getLogger().addHandler(console_handler)
    
    vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\Personal AI Employee Vault"
    session_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\whatsapp_session"

    watcher = WhatsAppWatcher(vault_path, session_path, check_interval=30)
    
    # Beautiful startup banner
    print("\n" + "=" * 60)
    print("  📱  WHATSAPP MESSAGE WATCHER  📱")
    print("=" * 60)
    print(f"  📂 Vault: {vault_path.split('/')[-1]}")
    print(f"  ⏱️  Check Interval: 30 seconds")
    print(f"  🔍 Keywords: urgent, asap, help, invoice, payment")
    print("=" * 60)
    print("  ✅ Watching for new messages...")
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    atexit.register(watcher.close_browser)

    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("  🛑 WhatsApp Watcher stopped by user")
        print("=" * 60 + "\n")
        watcher.close_browser()
