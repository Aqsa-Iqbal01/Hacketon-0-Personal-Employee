"""
LinkedIn Debug Script - Takes screenshot and shows page structure
"""
import time
import sys
from playwright.sync_api import sync_playwright

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def debug_linkedin():
    """Debug LinkedIn page structure"""
    
    session_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\linkedin_session"
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch_persistent_context(
            session_path,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080',
            ],
            timeout=120000,
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        print("\n" + "="*60)
        print("  LINKEDIN DEBUGGER")
        print("="*60)
        
        # Navigate to My Network page
        print("\n[S] Navigating to My Network page...")
        try:
            page.goto('https://www.linkedin.com/mynetwork/', wait_until='domcontentloaded', timeout=60000)
            print("[OK] Page loaded!")
        except Exception as e:
            print(f"[ERR] Error loading page: {e}")
            print("Trying to continue anyway...")
        
        time.sleep(10)  # Wait more time for page to fully load
        
        # Take screenshot
        print("\n[IMG] Taking screenshot...")
        try:
            page.screenshot(path='linkedin_mynetwork_debug.png', full_page=True)
            print("[OK] Screenshot saved: linkedin_mynetwork_debug.png")
        except Exception as e:
            print(f"[ERR] Error taking screenshot: {e}")
        
        # Save page HTML for analysis
        print("\n[HTML] Saving page HTML...")
        try:
            html = page.content()
            with open('linkedin_mynetwork_debug.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("[OK] HTML saved: linkedin_mynetwork_debug.html")
        except Exception as e:
            print(f"[ERR] Error saving HTML: {e}")
        
        # Try to find badges
        print("\n[*] Searching for badges...")
        badge_selectors = [
            'button[aria-label*="invitation"] span[aria-hidden="true"]',
            'button[aria-label*="Invitation"] span[aria-hidden="true"]',
            'div.mynetwork-nav__button span.notification-badge',
            '[data-test="invitations-badge"]',
            'span.mynetwork-nav__badge',
            'nav[aria-label*="My Network"] span[aria-hidden="true"]',
        ]
        
        found_badge = False
        for selector in badge_selectors:
            try:
                elements = page.locator(selector)
                count = elements.count()
                if count > 0:
                    print(f"\n[OK] Found {count} element(s) with: {selector}")
                    for i in range(min(count, 3)):
                        try:
                            text = elements.nth(i).text_content(timeout=2000).strip()
                            print(f"    [{i}] Text: '{text}'")
                            if text.isdigit():
                                found_badge = True
                                print(f"    >>> THIS IS THE BADGE! Count: {text}")
                        except:
                            print(f"    [{i}] (no text)")
            except Exception as e:
                print(f"[ERR] {selector}: {e}")
        
        if not found_badge:
            print("\n[!] No numeric badge found with standard selectors")
        
        # Find all buttons with "Accept" or "Connect" text
        print("\n[*] Searching for Accept/Connect buttons...")
        try:
            accept_buttons = page.locator('button:has-text("Accept")')
            count = accept_buttons.count()
            print(f"Found {count} 'Accept' buttons")
            
            if count > 0:
                print(">>> Connection requests FOUND!")
            
            for i in range(min(count, 5)):
                try:
                    parent = accept_buttons.nth(i).locator('xpath=..')
                    text = parent.text_content(timeout=2000).strip()
                    print(f"\n[Button {i}]")
                    print(f"Text: {text[:200]}")
                except:
                    pass
        except Exception as e:
            print(f"[ERR] Error: {e}")
        
        # Find all list items
        print("\n[*] Searching for list items...")
        try:
            list_items = page.locator('ul[role="list"] > li').all()
            print(f"Found {len(list_items)} list items")
            
            for i, item in enumerate(list_items[:5]):
                try:
                    text = item.text_content(timeout=2000).strip()
                    if len(text) > 20:
                        print(f"\n[Item {i}]")
                        print(f"Text: {text[:150]}...")
                except:
                    pass
        except Exception as e:
            print(f"[ERR] Error: {e}")
        
        # Get page title and URL
        try:
            print(f"\n[TITLE] Page Title: {page.title()}")
        except:
            pass
        
        try:
            print(f"[URL] Current URL: {page.url}")
        except:
            pass
        
        print("\n" + "="*60)
        print("  DEBUG COMPLETE")
        print("="*60)
        print("\nCheck these files:")
        print("  - linkedin_mynetwork_debug.png (screenshot)")
        print("  - linkedin_mynetwork_debug.html (page HTML)")
        print("\nBrowser will stay open for 60 seconds")
        print("You can manually inspect the page")
        print("Press Ctrl+C to close early...\n")
        
        # Keep browser open for 60 seconds
        for i in range(60):
            time.sleep(1)
            if i % 10 == 0:
                print(f"   ... still open ({i}s)")
        
        print("\nClosing browser...")
        browser.close()

if __name__ == '__main__':
    debug_linkedin()
