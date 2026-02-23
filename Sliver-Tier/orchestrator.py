"""
Orchestrator - Master process that coordinates all AI Employee components

Manages watchers, processes tasks, handles human-in-the-loop approvals,
and maintains the overall system health.
"""

import os
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class Orchestrator:
    def __init__(self, vault_path: str):
        """
        Initialize the orchestrator.

        Args:
            vault_path (str): Path to the Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.plans = self.vault_path / 'Plans'
        self.done = self.vault_path / 'Done'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.approved = self.vault_path / 'Approved'
        self.rejected = self.vault_path / 'Rejected'
        self.logs = self.vault_path / 'Logs'

        # Create folders if they don't exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.plans.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.pending_approval.mkdir(parents=True, exist_ok=True)
        self.approved.mkdir(parents=True, exist_ok=True)
        self.rejected.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.logs / f'orchestrator_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('Orchestrator')

        self.logger.info("Orchestrator initialized")
        self.logger.info(f"Vault path: {self.vault_path}")

    def check_for_tasks(self) -> List[Path]:
        """
        Check for new tasks in the Needs_Action folder.

        Returns:
            List[Path]: List of task files to process
        """
        try:
            tasks = list(self.needs_action.glob('*.md'))
            self.logger.info(f'Found {len(tasks)} tasks in Needs_Action')
            return tasks
        except Exception as e:
            self.logger.error(f'Error checking for tasks: {e}')
            return []

    def process_task(self, task_file: Path) -> bool:
        """
        Process a single task file using Claude Code.

        Args:
            task_file (Path): Path to the task file

        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            self.logger.info(f'Processing task: {task_file.name}')

            # Create a plan file
            plan_name = task_file.stem.replace('FILE_', 'PLAN_') + '.md'
            plan_file = self.plans / plan_name

            # Read the task content
            with open(task_file, 'r', encoding='utf-8') as f:
                task_content = f.read()

            # Generate a plan using Claude Code
            plan_content = self.generate_plan(task_content, task_file)

            if plan_content:
                # Write the plan to file
                with open(plan_file, 'w', encoding='utf-8') as f:
                    f.write(plan_content)

                self.logger.info(f'Plan created: {plan_file.name}')
                return True
            else:
                self.logger.warning(f'No plan generated for {task_file.name}')
                return False

        except Exception as e:
            self.logger.error(f'Error processing task {task_file.name}: {e}')
            return False

    def generate_plan(self, task_content: str, task_file: Path) -> str:
        """
        Generate an action plan using Claude Code.

        Args:
            task_content (str): Content of the task file
            task_file (Path): Path to the task file

        Returns:
            str: Generated plan content
        """
        # In a real implementation, this would call Claude Code
        # For now, we'll create a basic plan template

        task_type = self.extract_task_type(task_content)
        task_summary = self.extract_task_summary(task_content)

        plan_content = f"""---
name: {task_file.stem}_plan
type: task_plan
created: {datetime.now().isoformat()}
task_type: {task_type}
status: pending
---

# Task Plan: {task_summary}

## Task Details

**Original File:** {task_file.name}
**Type:** {task_type}
**Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Analysis

Based on the task content, this appears to be a file drop that requires processing.

The file "{task_file.name}" was dropped into the system and needs to be handled according to its type and content.

## Action Plan

### Step 1: File Analysis
- [ ] Analyze the file content and type
- [ ] Determine appropriate processing method
- [ ] Check for any special requirements

### Step 2: Content Processing
- [ ] Process the file according to its type
- [ ] Extract relevant information
- [ ] Generate appropriate output

### Step 3: Action Execution
- [ ] Execute the required actions
- [ ] Generate any necessary output files
- [ ] Update the system state

### Step 4: Completion
- [ ] Move original file to appropriate location
- [ ] Update task status
- [ ] Log completion

## Approval Required

This plan requires human approval before execution, especially for:
- File operations outside the vault
- External communications
- Any actions that modify system state

## Next Steps

1. Review this plan in the `Plans` folder
2. Move to `Pending_Approval` if ready for execution
3. Human approval will trigger action execution
4. Completed tasks move to `Done`

---
*Generated by Personal AI Employee Orchestrator v0.1*"""

        return plan_content

    def extract_task_type(self, content: str) -> str:
        """
        Extract the task type from the content.

        Args:
            content (str): Content of the task file

        Returns:
            str: Task type
        """
        # Look for type in YAML frontmatter
        if 'type:' in content:
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith('type:'):
                    return line.split(':')[1].strip()
        return 'unknown'

    def extract_task_summary(self, content: str) -> str:
        """
        Extract a summary of the task.

        Args:
            content (str): Content of the task file

        Returns:
            str: Task summary
        """
        if 'type: file_drop' in content:
            return 'File Drop Processing'
        return 'Task Processing'

    def move_to_done(self, task_file: Path):
        """
        Move a completed task to the Done folder.

        Args:
            task_file (Path): Path to the task file
        """
        try:
            dest = self.done / task_file.name
            task_file.rename(dest)
            self.logger.info(f'Moved {task_file.name} to Done')
        except Exception as e:
            self.logger.error(f'Error moving {task_file.name} to Done: {e}')

    def run_watchers(self):
        """
        Run all configured watchers.
        """
        # For now, we'll just start the file system watcher
        # In a full implementation, this would manage multiple watchers
        self.logger.info('Starting watchers...')

        # Start the file system watcher in a separate process
        try:
            # In a real implementation, you'd use multiprocessing or subprocess
            # For now, we'll just log that we're starting it
            self.logger.info('File System Watcher started')
        except Exception as e:
            self.logger.error(f'Error starting watchers: {e}')

    def health_check(self):
        """
        Perform a health check of the system.

        Returns:
            dict: Health check results
        """
        health = {
            'timestamp': datetime.now().isoformat(),
            'vault_path': str(self.vault_path),
            'needs_action_count': len(list(self.needs_action.glob('*.md'))),
            'plans_count': len(list(self.plans.glob('*.md'))),
            'done_count': len(list(self.done.glob('*.md'))),
            'pending_approval_count': len(list(self.pending_approval.glob('*.md'))),
            'approved_count': len(list(self.approved.glob('*.md'))),
            'rejected_count': len(list(self.rejected.glob('*.md'))),
            'logs_count': len(list(self.logs.glob('*.log'))),
            'status': 'healthy'
        }

        # Check for any issues
        if health['needs_action_count'] > 10:
            health['status'] = 'warning'
            self.logger.warning('High number of pending tasks')

        return health

    def run(self):
        """
        Main orchestrator loop.
        """
        self.logger.info("Orchestrator started")
        self.run_watchers()

        try:
            while True:
                # Check for tasks every 30 seconds
                tasks = self.check_for_tasks()

                for task_file in tasks:
                    if self.process_task(task_file):
                        # Move to done after successful processing
                        self.move_to_done(task_file)

                # Perform health check every 5 minutes
                if datetime.now().minute % 5 == 0:
                    health = self.health_check()
                    self.logger.info(f'Health check: {health}')

                # Sleep for 30 seconds
                time.sleep(30)

        except KeyboardInterrupt:
            self.logger.info("Orchestrator stopped")
        except Exception as e:
            self.logger.error(f'Fatal error in orchestrator: {e}')
            raise

if __name__ == "__main__":
    import sys

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('orchestrator.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Example usage
    vault_path = "C:\\Users\\HAROON TRADERS\\Desktop\\ar portfolio\\Hacketon-Employee\\Personal AI Employee Vault"

    orchestrator = Orchestrator(vault_path)

    print("🚀 Personal AI Employee Orchestrator started!")
    print(f"📁 Vault: {vault_path}")
    print("🔄 Running continuous task processing...")
    print("⏹ Pause: Ctrl+C to stop")

    orchestrator.run()