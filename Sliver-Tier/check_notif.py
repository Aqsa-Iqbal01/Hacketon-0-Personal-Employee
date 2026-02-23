"""
Quick LinkedIn Notification Check
"""
import time
from playwright.sync_api import sync_playwright

session_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\linkedin_session"

print("\n=== LinkedIn Notification Checker ===\n")

with sync_playwright() as p:
    # Launch browser
    browser = p.chromium.launch_persistent_context(
        session_path,
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=False,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--window-size=1920,1080'],
        timeout=120000,
    )
    
    page = browser.pages[0] if browser.pages else browser.new_page()
    
    # Go to notifications
    print("Navigating to notifications...")
    page.goto('https://www.linkedin.com/notifications/', wait_until='domcontentloaded', timeout=90000)
    time.sleep(8)
    
    # Save screenshot
    page.screenshot(path='notif_check.png')
    print("Screenshot saved: notif_check.png")
    
    # Save HTML
    with open('notif_check.html', 'w', encoding='utf-8') as f:
        f.write(page.content())
    print("HTML saved: notif_check.html")
    
    # Check badge
    print("\n--- Checking for badge ---")
    selectors = [
        'button[aria-label*="notification"] span[aria-hidden="true"]',
        '[data-test="notifications-badge"]',
        'span.notification-badge',
    ]
    
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                text = el.text_content(timeout=2000).strip()
                print(f"FOUND with '{sel}': '{text}'")
        except:
            pass
    
    # Check notification list
    print("\n--- Checking notification list ---")
    list_selectors = [
        'ul.scaffold-layout__list li',
        '[role="list"] > li',
        '[role="list"] > div',
        'div.notification-item',
    ]
    
    for sel in list_selectors:
        try:
            items = page.locator(sel)
            count = items.count()
            if count > 0:
                print(f"FOUND {count} items with '{sel}'")
                for i in range(min(count, 3)):
                    try:
                        text = items.nth(i).text_content(timeout=3000).strip()
                        if len(text) > 20:
                            print(f"  [{i}] {text[:100]}...")
                    except:
                        pass
        except Exception as e:
            print(f"Error with '{sel}': {e}")
    
    # Get all text content from page
    print("\n--- All visible text on page ---")
    try:
        all_text = page.locator('body').text_content(timeout=5000)
        lines = all_text.split('\n')
        for line in lines[:50]:  # First 50 lines
            line = line.strip()
            if len(line) > 10:
                print(f"  {line[:100]}")
    except:
        pass
    
    print("\n=== Complete ===")
    print("\nBrowser will stay open for 30 seconds...")
    print("Check the screenshot: notif_check.png")
    time.sleep(30)
    browser.close()
