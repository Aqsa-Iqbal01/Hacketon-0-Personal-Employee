"""
Simple test to check if Playwright works
"""
from playwright.sync_api import sync_playwright
import os

print("Testing Playwright...")

try:
    with sync_playwright() as p:
        # Try to use system Chrome
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        if not os.path.exists(chrome_path):
            print(f"Chrome not found at {chrome_path}")
            chrome_path = None
        
        print("Launching browser...")
        browser = p.chromium.launch(
            executable_path=chrome_path,
            headless=False,
            args=['--no-sandbox', '--disable-gpu']
        )
        print("Browser launched!")
        
        page = browser.new_page()
        print("Opening WhatsApp Web...")
        page.goto('https://web.whatsapp.com')
        print("Done! Check the browser window.")
        
        input("Press Enter to close browser...")
        browser.close()
        print("Browser closed")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
