# Gmail Watcher Skill

## Purpose
Monitors Gmail for new important emails, scores them by priority, and creates action files for high-priority emails.

## When to Use
- User wants to check Gmail for new emails
- User wants to monitor important emails
- User asks to "run Gmail watcher" or "check Gmail"
- User wants to see email activity in real-time

## Prerequisites

### First Time Setup Required:
1. **Authenticate with Google:**
   ```bash
   python gmail_auth.py
   ```

2. **Scan QR / Login:**
   - Browser will open
   - Login with Google account
   - Grant Gmail permissions
   - If "App not verified" warning appears:
     - Click "Advanced"
     - Click "Go to ... (unsafe)"
     - Complete login

3. **Verify token.json created:**
   ```bash
   dir token.json
   ```

## Commands

### Start Gmail Watcher
```bash
cd /d "C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-silver-tier"
python gmail_watcher.py
```

### Check Recent Logs
```bash
cd /d "C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-silver-tier"
powershell -Command "Get-Content gmail_watcher.log -Tail 30"
```

### Check Action Files Created
```bash
dir "Personal AI Employee Vault\Needs Action\*GMAIL*" /b
```

### View Specific Action File
```bash
type "Personal AI Employee Vault\Needs Action\GMAIL_*.md"
```

## Expected Output

### When Important Email Found:
```
============================================================
  📧 GMAIL IMPORTANT EMAIL DETECTED!
============================================================
  👤 From: client@company.com
  📝 Subject: Urgent: Project Deadline Tomorrow
  🏷️  Priority Score: 8.5/10
  🔑 Keywords: urgent, deadline
  ✅ Action File: GMAIL_EMAIL_1771870945.md
============================================================
```

### When No New Emails:
```
⏳  No new important emails (next check: 2 min)
```

### Authentication Required:
```
============================================================
  GMAIL WATCHER
============================================================
  ERROR: token.json not found!
  
  Solution:
  1. Run: python gmail_auth.py
  2. Login with your Google account
  3. Grant permissions
  4. Then run gmail_watcher.py again
============================================================
```

## Monitoring

The watcher:
- Checks every 2 minutes automatically
- Monitors Gmail for unread, important emails
- Scores emails by priority (0-10 scale)
- Filters emails from last 24 hours
- Creates action files in `Needs_Action` folder
- Logs all activity to `gmail_watcher.log`
- Tracks processed email IDs to avoid duplicates

## Priority Scoring

Emails are scored based on:
- **Keywords** (urgent, asap, important, invoice, payment)
- **Sender importance** (clients, bosses, known contacts)
- **Subject line** (urgent, action required, deadline)
- **Email content** (business-critical keywords)

**Score Thresholds:**
- **8-10:** High priority (immediate action)
- **5-7:** Medium priority (review soon)
- **1-4:** Low priority (when time permits)

## Stop Watcher
Press `Ctrl+C` to stop the watcher

## Related Files
- Script: `gmail_watcher.py`
- Authentication: `gmail_auth.py`
- Credentials: `credentials.json` (Google OAuth)
- Token: `token.json` (generated after auth)
- Logs: `gmail_watcher.log`
- Action Files: `Personal AI Employee Vault/Needs Action/`

## Troubleshooting

### token.json not found:
```bash
python gmail_auth.py
# Login and grant permissions
# Then run gmail_watcher.py again
```

### Access Denied error:
1. Go to Google Cloud Console
2. Add your email as test user
3. Wait 2 minutes
4. Clear browser cache
5. Run `python gmail_auth.py` again

### Check if running:
```bash
tasklist | findstr python
```

### View full logs:
```bash
type gmail_watcher.log | more
```

### Re-authenticate:
```bash
del token.json
python gmail_auth.py
```

## Google Cloud Setup (First Time Only)

1. **Create Google Cloud Project:**
   - Go to: https://console.cloud.google.com/
   - Create new project

2. **Enable Gmail API:**
   - Go to APIs & Services > Library
   - Search "Gmail API"
   - Click Enable

3. **Create OAuth Credentials:**
   - Go to APIs & Services > Credentials
   - Create Credentials > OAuth client ID
   - Application type: Desktop app
   - Download credentials.json

4. **Add Test User:**
   - Go to OAuth consent screen
   - Add your email to Test users
   - Save

5. **Authenticate:**
   ```bash
   python gmail_auth.py
   ```

## Integration
Works with:
- Gmail API (read-only access)
- Approval Workflow (for sensitive email actions)
- Obsidian Vault (stores all action files)
- MCP Email Server (can send replies via approval)

## Action File Structure

```markdown
---
type: gmail_email
source: gmail
id: 18abc123def456
from: client@company.com
subject: Urgent: Project Deadline
priority_score: 8.5
status: pending
---

# Gmail Email

**From:** client@company.com
**Subject:** Urgent: Project Deadline
**Priority Score:** 8.5/10

## Email Content

[Email body content here...]

## Suggested Actions

- [ ] Review email content
- [ ] Draft response
- [ ] Take required action
- [ ] Send reply via approval workflow
- [ ] Mark as done after responding

---
*Generated by Gmail Watcher*
```

## Email Search Query

The watcher uses this Gmail search query:
```
is:unread is:important newer_than:1d
```

This filters:
- Unread emails only
- Marked as important by Gmail
- From the last 24 hours

## Best Practices

1. **Run continuously** in background for real-time monitoring
2. **Check Needs_Action folder** regularly for new emails
3. **Review high-priority emails first** (score > 7)
4. **Use approval workflow** for sending replies
5. **Clean processed emails** from Needs_Action after action
