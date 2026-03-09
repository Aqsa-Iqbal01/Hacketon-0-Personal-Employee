# LinkedIn Watcher Skill

## Purpose
Automatically runs and monitors the LinkedIn Watcher script, showing real-time logs and activity detection.

## When to Use
- User wants to check LinkedIn for new notifications
- User wants to monitor connection requests
- User wants to see LinkedIn activity in real-time
- User asks to "run LinkedIn watcher" or "check LinkedIn"

## Commands

### Start LinkedIn Watcher
```bash
cd /d "C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-silver-tier"
python linkedin_watcher.py
```

### Check Recent Logs
```bash
cd /d "C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-silver-tier"
powershell -Command "Get-Content linkedin_watcher.log -Tail 30"
```

### Check Action Files Created
```bash
dir "Personal AI Employee Vault\Needs Action\*LINKEDIN*" /b
```

### View Specific Action File
```bash
type "Personal AI Employee Vault\Needs Action\LINKEDIN_*.md"
```

## Expected Output

### When Activity Found:
```
============================================================
  📊 LINKEDIN ACTIVITY DETECTED!
============================================================
     🔔 Notifications: 2
     🤝 Connection Requests: 1
     📝 Total Items: 3
============================================================

============================================================
  🤝 LINKEDIN CONNECTION REQUEST DETECTED!
============================================================
  👤 Name: John Doe
  💼 Details: CEO at TechCorp
  🏷️  Relevance: 60%
  ✅ Action File: LINKEDIN_REQUEST_REQ_1771870945.md
============================================================
```

### When No Activity:
```
⏳  No new LinkedIn activity (next check: 5 min)
```

## Monitoring

The watcher:
- Checks every 5 minutes automatically
- Monitors LinkedIn notifications
- Monitors connection requests
- Creates action files in `Needs_Action` folder
- Logs all activity to `linkedin_watcher.log`

## Stop Watcher
Press `Ctrl+C` to stop the watcher

## Related Files
- Script: `linkedin_watcher.py`
- Logs: `linkedin_watcher.log`
- Action Files: `Personal AI Employee Vault/Needs Action/`
- Session: `linkedin_session/`

## Troubleshooting

### Browser won't open:
```bash
taskkill /F /IM chrome.exe
rmdir /s /q "linkedin_session"
python linkedin_watcher.py
```

### Check if running:
```bash
tasklist | findstr python
```

### View full logs:
```bash
type linkedin_watcher.log | more
```

## Integration
Works with:
- LinkedIn Poster (auto-generates posts every 24 hours)
- Approval Workflow (auto-approves high-relevance items)
- Obsidian Vault (stores all action files)
