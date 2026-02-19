# File System Watcher Skill

## Purpose
Automatically detects when new files are added to the inbox folder and notifies the user.

## How It Works
1. Continuously monitors the `.claude/inbox` folder
2. When a new file is detected, it prints a notification
3. Shows the file name and content
4. Provides options for what to do with the file

## Usage
```bash
# Start the watcher
skill: "file-system-watcher"

# Then add files to .claude/inbox folder
```

## Example Interaction
```
User: skill: "file-system-watcher"
Claude: Watcher started. Monitoring .claude/inbox folder...

[After adding file]
Claude: New file detected: greeting.txt
Claude: Content: Hello Claude!
Claude: What would you like to do with this file?
1. Process with markdown skill
2. Process with text skill
3. View more details
4. Ignore
```