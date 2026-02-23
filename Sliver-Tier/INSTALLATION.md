# Bronze Tier Installation & Setup Guide

## 🎯 Quick Start

### Prerequisites
- Python 3.13+ installed
- Claude Code subscription (or use Gemini API with Claude Code Router)
- Obsidian v1.10.6+ installed

### Installation Steps

#### 1. Clone/Download Project
```bash
# Navigate to your project directory
git clone https://github.com/your-repo/Hacketon-Employee.git
cd Hacketon-Employee
```

#### 2. Set Up Python Environment
```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install watchdog python-dotenv
```

#### 3. Configure Obsidian Vault
1. Open Obsidian
2. Create new vault at: `Personal AI Employee Vault`
3. Verify the folder structure:
   ```
   Personal AI Employee Vault/
   ├── Dashboard.md
   ├── Company_Handbook.md
   ├── Needs_Action/
   ├── Plans/
   ├── Done/
   ├── Pending_Approval/
   ├── Approved/
   ├── Rejected/
   └── Logs/
   ```

#### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
# Development Mode (set to true for testing)
DRY_RUN=true

# Logging Configuration
LOG_LEVEL=INFO
```

#### 5. Test the System
```bash
# Start the orchestrator
python orchestrator.py

# In another terminal, start the file watcher
python file_system_watcher.py

# Create a test file
echo "Test file" > File_Drop_Folder/test.txt
```

## 🚀 Running the System

### Method 1: Manual Start
```bash
# Start orchestrator (main process)
python orchestrator.py

# Start file watcher (in separate terminal)
python file_system_watcher.py
```

### Method 2: Using PM2 (Recommended)
```bash
# Install PM2 globally
npm install -g pm2

# Start both processes
pm2 start orchestrator.py --interpreter python
pm2 start file_system_watcher.py --interpreter python

# Save processes to start on boot
pm2 save
pm2 startup
```

## 📋 Folder Structure Usage

### Needs_Action/
- Drop files here to trigger processing
- Files are automatically copied and converted to markdown

### Plans/
- Generated action plans for each task
- Contains step-by-step instructions

### Pending_Approval/
- Files requiring human review before execution
- Move to Approved/ to proceed

### Done/
- Completed tasks and their plans
- Archive for future reference

### Logs/
- System logs and audit trails
- Error reports and debugging information

## 🔧 Configuration

### Watcher Settings
Edit `file_system_watcher.py`:
```python
# Adjust check interval (in seconds)
check_interval = 60  # Default: 60 seconds

# Set watch path
watch_path = "File_Drop_Folder"
```

### Orchestrator Settings
Edit `orchestrator.py`:
```python
# Adjust processing interval
processing_interval = 30  # Default: 30 seconds

# Set vault path
vault_path = "Personal AI Employee Vault"
```

## 🐛 Troubleshooting

### Common Issues

#### 1. File Watcher Not Working
```bash
# Check if watchdog is installed
pip list | grep watchdog

# Check log file
cat file_watcher.log

# Verify watch folder exists
ls -la File_Drop_Folder/
```

#### 2. Orchestrator Errors
```bash
# Check orchestrator logs
cat orchestrator.log

# Verify vault structure
ls -la Personal\ AI\ Employee\ Vault/
```

#### 3. Permission Issues
```bash
# Check file permissions
ls -la

# Run with elevated permissions if needed
sudo python orchestrator.py
```

### Debug Mode
Enable detailed logging by setting:
```bash
export LOG_LEVEL=DEBUG
# or in .env file
LOG_LEVEL=DEBUG
```

## 🔄 Testing the System

### Test File Drop
1. Create a test file:
   ```bash
echo "This is a test file" > File_Drop_Folder/test.txt
```

2. Wait for processing (30-60 seconds)

3. Check results:
   ```bash
   # Check Needs_Action folder
   ls -la Personal\ AI\ Employee\ Vault/Needs_Action/

   # Check Plans folder
   ls -la Personal\ AI\ Employee\ Vault/Plans/
   ```

### Test Approval Workflow
1. Move a file to `Pending_Approval/`
2. Review and move to `Approved/`
3. Verify processing occurs

## 📦 Dependencies

### Required Packages
```bash
watchdog              # File system monitoring
python-dotenv         # Environment variable management
```

### Optional Packages
```bash
pm2                   # Process management (recommended)
rich                  # Enhanced console output (for debugging)
```

## 🚀 Deployment Tips

### For Production
1. Set `DRY_RUN=false` in `.env`
2. Configure proper logging
3. Set up automated backups
4. Implement monitoring

### Security Considerations
- Never commit `.env` file
- Use strong environment variables
- Regular security audits
- Backup encryption

## 📚 Next Steps

After Bronze Tier is working:
1. Test all folder workflows
2. Verify audit logging
3. Check dashboard updates
4. Test error handling
5. Review security settings

---

**Bronze Tier Status:** ✅ COMPLETED
**Next Upgrade:** Silver Tier (20-30 hours)