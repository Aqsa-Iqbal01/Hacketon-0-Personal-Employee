"""
Gmail Authentication Script - Run this once to authenticate with Google
"""
import os.path
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# If modifying scopes, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    creds = None
    
    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("\n" + "="*60)
        print("  ❌ ERROR: credentials.json not found!")
        print("="*60)
        print("\n📧 You need to create a Google Cloud project first:")
        print("   1. Go to: https://console.cloud.google.com/")
        print("   2. Create a new project")
        print("   3. Enable Gmail API")
        print("   4. Create OAuth 2.0 credentials (Desktop app)")
        print("   5. Download credentials.json")
        print("   6. Save it in this folder")
        print("="*60 + "\n")
        return

    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            print("✅ Found existing token.json")
        except Exception as e:
            print(f"⚠️  Invalid token.json: {e}")
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing expired token...")
                creds.refresh(Request())
                print("✅ Token refreshed successfully!")
            except RefreshError as e:
                print(f"⚠️  Token refresh failed: {e}")
                creds = None
        
        if not creds:
            print("\n" + "="*60)
            print("  📧 GMAIL AUTHENTICATION")
            print("="*60)
            print("\n  🔐 A browser window will open for Google login.")
            print("  📌 If browser doesn't open, copy the URL shown below.")
            print("\n  ⚠️  IMPORTANT - If you see 'App not verified' warning:")
            print("     1. Click 'Continue' or 'Advanced'")
            print("     2. Click 'Go to ... (unsafe)'")
            print("     3. Complete login and grant permissions")
            print("\n  ✅ This is normal for personal projects!")
            print("="*60 + "\n")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0, open_browser=True)
            except Exception as e:
                print(f"\n❌ Authentication failed: {e}")
                print("\n💡 Try manual authentication:")
                print("   1. Run the script again")
                print("   2. Copy the URL when shown")
                print("   3. Paste in browser")
                print("   4. Login and grant permissions")
                print("   5. Copy the authorization code")
                print("   6. Paste it in the terminal")
                return

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        
        print("\n" + "="*60)
        print("  ✅ AUTHENTICATION SUCCESSFUL!")
        print("="*60)
        print("\n  📁 token.json created successfully!")
        print("  📧 You can now run: python gmail_watcher.py")
        print("="*60 + "\n")
    else:
        print("\n✅ Already authenticated!")
        print("📧 You can run: python gmail_watcher.py")
        print()

if __name__ == '__main__':
    main()
