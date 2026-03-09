"""Quick Gmail Auth Fix"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

print("\n" + "="*60)
print("  GMAIL AUTHENTICATION")
print("="*60)
print("\nBrowser will open in 3 seconds...")
print("If you see 'App not verified' warning:")
print("  1. Click 'Advanced'")
print("  2. Click 'Go to ... (unsafe)'")
print("  3. Login and Allow permissions")
print("="*60 + "\n")

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Save token
with open('token.json', 'w') as f:
    f.write(creds.to_json())

print("\n" + "="*60)
print("  SUCCESS!")
print("="*60)
print("\ntoken.json created!")
print("Now you can run: python gmail_watcher.py")
print("="*60 + "\n")
