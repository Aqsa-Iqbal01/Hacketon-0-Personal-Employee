"""
Debug WhatsApp to see what messages are being read
"""
import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\Personal AI Employee Vault"
session_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\whatsapp_session"

# Cleanup session
session_dir = Path(session_path)
if session_dir.exists():
    for lock_file in session_dir.glob('Singleton*'):
        try:
            lock_file.unlink()
            print(f'Removed lock: {lock_file}')
        except: pass

print("Starting browser...")
playwright = sync_playwright().start()

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

browser = playwright.chromium.launch_persistent_context(
    session_path,
    executable_path=chrome_path,
    headless=False,
    args=[
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080',
    ],
    timeout=120000,
    slow_mo=500
)

page = browser.pages[0] if browser.pages else browser.new_page()

print("Loading WhatsApp Web...")
page.goto('https://web.whatsapp.com', wait_until='domcontentloaded')
print("\n=== QR CODE SCAN KARO BROWSER MEIN ===\n")

# Wait for chat list
try:
    page.wait_for_selector('#pane-side', timeout=60000)
    print("✓ Chat list found!")
except:
    print("✗ Chat list not found")
    browser.close()
    playwright.stop()
    exit()

time.sleep(3)

# Get all chats
chats = page.locator('#pane-side div[role="row"]')
count = chats.count()
print(f"\n=== Total Chats: {count} ===\n")

keywords = ['urgent', 'asap', 'help', 'invoice', 'payment', 'important', 'need']

for i in range(min(count, 20)):
    try:
        chat = chats.nth(i)
        if not chat.is_visible(timeout=2000):
            continue
        
        text = chat.inner_text(timeout=2000)
        lines = text.split('\n')
        
        if len(lines) >= 2:
            title = lines[0].strip()
            message = lines[-1].strip()
            
            # Check for keywords
            has_keyword = any(kw in text.lower() for kw in keywords)
            marker = ">>> KEYWORD MATCH <<<" if has_keyword else ""
            
            print(f"[{i}] {title}")
            print(f"    Message: {message[:60]}")
            if has_keyword:
                print(f"    {marker}")
            print()
    except Exception as e:
        print(f"[{i}] Error: {e}")

print("\nPress Enter to close...")
input()
browser.close()
playwright.stop()
