# Process Inbox Skill

## Purpose
Process files from the inbox folder and move them to appropriate folders based on their content and status.

## How It Works
1. Reads all files from the Inbox folder
2. Analyzes each file's content to determine appropriate action
3. Provides summary of inbox contents
4. Does NOT move files to any folders
5. Does NOT update Dashboard.md
6. Does NOT maintain audit logs

## Usage
```bash
skill: "process-inbox"
```

## Implementation Details

### File Processing Logic
- **Client requests**: Analyze and provide summary
- **Completed tasks**: Analyze and provide summary
- **Action plans**: Analyze and provide summary
- **Practice/test files**: Analyze and provide summary
- **Invalid files**: Analyze and provide summary

### Dashboard Updates
Dashboard updates are disabled by default. This skill only processes inbox files and moves them to Needs_Action folder.

### Audit Logging
All operations are logged in the Logs folder with timestamps:
- File processing events
- Folder movements
- Dashboard updates
- Any errors or issues

## Example Interaction
```bash
User: skill: "process-inbox"
Claude: Checking inbox files...
Claude: Found 1 file in inbox:
   - new_client.md: Client request for Python automation
Claude: Summary: 1 client request waiting in inbox
```

## Requirements
- Obsidian vault structure must exist
- Inbox folder must be present
- Dashboard.md must be accessible for updates
- Logs folder for audit trail

## File Organization
```
Personal AI Employee Vault/
├── Inbox/          # ← Source folder (watched)
├── Needs_Action/   # ← Files requiring processing
├── Plans/          # ← Action plans and strategies
├── Done/           # ← Completed tasks
├── Archive/        # ← Invalid or obsolete files
├── Logs/           # ← Audit trail and system logs
└── Dashboard.md    # ← Real-time status dashboard
```

## Integration Points
- Works with existing file system watcher
- Compatible with Claude Code Agent Skills
- Updates Ralph Loop compatible files
- Maintains Bronze Tier workflow consistency
- Does NOT move files to Needs_Action folder

## Error Handling
- Invalid file formats are logged and archived
- Missing folders are created automatically
- All errors are logged with timestamps for troubleshooting
- No file movements are performed

## Best Practices
- Always check inbox before starting new tasks
- Analyze files in chronological order
- No folder movements or dashboard updates
- Review audit logs periodically for system health

## Self-Contained Operation
This skill is designed to be self-contained and can be used independently by calling:
```bash
Claude Code, please check my inbox files
```

It will automatically:
1. Scan the inbox folder
2. Read and analyze all pending files
3. Provide summary of inbox contents
4. Leave files in inbox unchanged
5. No folder movements or dashboard updates

The skill maintains the Bronze Tier philosophy of local-first, human-in-the-loop processing while providing automated analysis and tracking capabilities without moving files.