# Orchestrator Skill

## Purpose
Process inbox files using Claude Code instead of the Python orchestrator script. This skill handles the complete Perception → Reasoning → Action pipeline for the Personal AI Employee system.

## How It Works
1. **Perception**: Reads and analyzes files from Needs_Action folder (not inbox)
2. **Reasoning**: Generates appropriate action plans based on file content
3. **Action**: Processes files, creates plans in Plans folder, and moves completed files to Done folder
4. **Audit**: Maintains complete logs of all activities with timestamps
5. **Dashboard**: Updates Dashboard.md with current metrics

## Usage
```bash
# Start the orchestrator
Claude Code, please process my inbox files using the orchestrator skill
```

## Implementation Details

### File Processing Pipeline
- **Step 1**: Scan Needs_Action folder for new files
- **Step 2**: Read and analyze each file's content
- **Step 3**: Generate appropriate action plan
- **Step 4**: Create plan in Plans folder
- **Step 5**: Move file to Done folder
- **Step 6**: Update Dashboard.md with current status
- **Step 7**: Log all activities with timestamps
- **Step 8**: Remove processed files from Needs_Action folder

### Dashboard Updates
The skill automatically updates Dashboard.md with:
- Number of processed files
- Current status of each folder
- Recent activity log
- Task completion metrics

### Audit Logging
All operations are logged in the Logs folder with timestamps:
- File processing events
- Dashboard updates
- Folder movements (Needs_Action → Done, Plans creation)
- Any errors or issues

## Example Interaction
```bash
User: Claude Code, please process my inbox files using the orchestrator skill
Claude: Starting orchestrator pipeline...
Claude: Found 1 file to process: FILE_hhhh.md
Claude: Analyzing file content...
Claude: Generating action plan...
Claude: Creating plan: PLAN_hhhh.md
Claude: Moving FILE_hhhh.md to Done folder
Claude: Updating Dashboard.md...
Claude: Logging activity...
Claude: Orchestrator pipeline completed successfully
Claude: Summary: Processed 1 file, Created plan, Moved to Done, Updated dashboard
```

## Requirements
- Obsidian vault structure must exist
- Needs_Action folder must be present
- Dashboard.md must be accessible for updates
- Logs folder for audit trail

## File Organization
```
Personal AI Employee Vault/
├── Needs_Action/   # ← Files requiring processing
├── Plans/         # ← Action plans and strategies
├── Done/          # ← Completed tasks
├── Logs/          # ← Audit trail and system logs
└── Dashboard.md   # ← Real-time status dashboard
```

## Integration Points
- Works with existing file system watcher
- Compatible with Claude Code Agent Skills
- Updates Ralph Loop compatible files
- Maintains Bronze Tier workflow consistency
- Automatically updates Dashboard.md after processing

## Error Handling
- Invalid file formats are logged and archived
- Missing folders are created automatically
- Dashboard update failures are retried
- All errors are logged with timestamps for troubleshooting
- Files are moved to Done folder after processing
- Plans are created in Plans folder for each file

## Best Practices
- Always check Needs_Action before starting new tasks
- Process files in chronological order
- Dashboard updates are automatic after processing
- Review audit logs periodically for system health

## Self-Contained Operation
This skill is designed to be self-contained and can be used independently by calling:
```bash
Claude Code, please process my inbox files using the orchestrator skill
```

It will automatically:
1. Scan the Needs_Action folder
2. Process all pending files
3. Create plans in Plans folder
4. Move files to Done folder
5. Update the dashboard
6. Log all activities
7. Provide a summary of what was done

The skill maintains the Bronze Tier philosophy of local-first, human-in-the-loop processing while providing automated organization and tracking capabilities. Dashboard updates can be enabled/disabled based on user preference.

## Perception → Reasoning → Action Pipeline

### Perception
- Reads file metadata (name, type, size, timestamp)
- Analyzes file content for intent and requirements
- Identifies file category (client request, test file, action plan, etc.)

### Reasoning
- Determines appropriate processing strategy
- Generates action plan with specific steps
- Assigns priority and timeline
- Identifies required resources or approvals

### Action
- Executes the processing strategy
- Creates plans in Plans folder
- Moves completed files to Done folder
- Logs all activities with timestamps
- Updates Dashboard.md with current metrics

## Summary Reporting
After processing, the skill provides:
- Total files processed
- Types of files handled
- Actions taken for each file
- Dashboard update status
- Log file locations
- Any errors or issues encountered
- Files moved to Done folder
- Plans created in Plans folder