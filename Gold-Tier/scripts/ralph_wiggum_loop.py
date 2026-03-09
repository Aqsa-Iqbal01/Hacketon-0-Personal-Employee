#!/usr/bin/env python3
"""
Ralph Wiggum Loop Implementation
Autonomous multi-step task completion with persistence
Keeps Claude Code working until tasks are complete
"""

import os
import sys
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RalphWiggumLoop:
    """
    Ralph Wiggum pattern implementation for autonomous task completion.
    
    This pattern intercepts Claude Code's exit and re-injects prompts
    until tasks are marked as complete.
    """
    
    def __init__(
        self,
        vault_path: str,
        max_iterations: int = 10,
        completion_promise: str = "TASK_COMPLETE",
        state_file_path: Optional[str] = None
    ):
        """
        Initialize Ralph Wiggum loop
        
        Args:
            vault_path: Path to Obsidian vault
            max_iterations: Maximum loop iterations before forcing exit
            completion_promise: String pattern to detect completion
            state_file_path: Optional custom state file path
        """
        self.vault_path = Path(vault_path)
        self.max_iterations = max_iterations
        self.completion_promise = completion_promise
        self.state_file_path = state_file_path or (self.vault_path / ".ralph_state.json")
        
        # Paths
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.plans_path = self.vault_path / "Plans"
        self.done_path = self.vault_path / "Done"
        self.pending_approval_path = self.vault_path / "Pending_Approval"
        self.approved_path = self.vault_path / "Approved"
        self.logs_path = self.vault_path / "Logs"
        
        # Ensure paths exist
        for path in [self.needs_action_path, self.plans_path, self.done_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # State
        self.current_iteration = 0
        self.current_prompt = None
        self.start_time = None
        self.task_history = []
    
    def start_task(self, prompt: str) -> Dict[str, Any]:
        """
        Start a new task with Ralph loop
        
        Args:
            prompt: Initial task prompt
        
        Returns:
            Task state dictionary
        """
        self.current_iteration = 0
        self.current_prompt = prompt
        self.start_time = datetime.now()
        
        # Create state file
        state = {
            "task_id": f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "prompt": prompt,
            "started_at": self.start_time.isoformat(),
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "status": "in_progress",
            "completion_promise": self.completion_promise,
            "history": []
        }
        
        self._save_state(state)
        
        # Create plan file
        plan_file = self.plans_path / f"PLAN_{state['task_id']}.md"
        plan_content = f"""---
task_id: {state['task_id']}
created: {self.start_time.isoformat()}
status: in_progress
prompt: {prompt}
iteration: 0
max_iterations: {self.max_iterations}
---

# Task Plan

**Objective:** {prompt}

**Started:** {self.start_time.strftime('%Y-%m-%d %H:%M')}

## Steps

- [ ] Analyze requirements
- [ ] Execute tasks
- [ ] Verify completion

## Iteration Log

"""
        plan_file.write_text(plan_content, encoding='utf-8')
        
        logger.info(f"Started Ralph loop task: {state['task_id']}")
        
        return state
    
    def check_completion(self, output: str, state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if task is complete based on output and file system state
        
        Args:
            output: Claude Code output
            state: Current task state
        
        Returns:
            Tuple of (is_complete, reason)
        """
        # Check for completion promise in output
        if self.completion_promise.lower() in output.lower():
            return True, f"Completion promise '{self.completion_promise}' found in output"
        
        # Check for explicit completion markers
        completion_markers = [
            "task completed",
            "all tasks complete",
            "finished all steps",
            "no more actions needed"
        ]
        
        for marker in completion_markers:
            if marker.lower() in output.lower():
                return True, f"Completion marker '{marker}' found"
        
        # Check if all files moved to Done
        needs_action_count = len(list(self.needs_action_path.glob("*.md")))
        pending_approval_count = len(list(self.pending_approval_path.glob("*.md")))
        
        # If we started with files in Needs_Action and they're all gone
        initial_needs_action = state.get('initial_needs_action_count', 0)
        if initial_needs_action > 0 and needs_action_count == 0:
            if pending_approval_count == 0:
                return True, "All files processed and moved to Done"
        
        # Check for explicit task complete file
        complete_file = self.vault_path / f".task_complete_{state['task_id']}"
        if complete_file.exists():
            return True, "Task complete file found"
        
        return False, "Task still in progress"
    
    def should_continue(self, state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if Ralph loop should continue
        
        Args:
            state: Current task state
        
        Returns:
            Tuple of (should_continue, reason)
        """
        iteration = state.get('iteration', 0)
        
        # Check max iterations
        if iteration >= self.max_iterations:
            return False, f"Max iterations ({self.max_iterations}) reached"
        
        # Check for error states
        error_file = self.vault_path / f".ralph_error_{state['task_id']}"
        if error_file.exists():
            return False, "Error file found - task failed"
        
        # Check for manual stop
        stop_file = self.vault_path / f".ralph_stop_{state['task_id']}"
        if stop_file.exists():
            return False, "Manual stop requested"
        
        return True, "Continue processing"
    
    def reinject_prompt(self, state: Dict[str, Any], last_output: str) -> str:
        """
        Generate prompt for next iteration
        
        Args:
            state: Current task state
            last_output: Previous Claude output
        
        Returns:
            New prompt string
        """
        iteration = state.get('iteration', 0)
        original_prompt = state.get('prompt', '')
        
        # Build context-aware prompt
        needs_action_files = list(self.needs_action_path.glob("*.md"))
        pending_approval_files = list(self.pending_approval_path.glob("*.md"))
        approved_files = list(self.approved_path.glob("*.md"))
        
        context = []
        
        if needs_action_files:
            context.append(f"There are {len(needs_action_files)} files still in Needs_Action folder")
            for f in needs_action_files[:5]:
                context.append(f"  - {f.name}")
        
        if pending_approval_files:
            context.append(f"There are {len(pending_approval_files)} files awaiting approval in Pending_Approval")
            for f in pending_approval_files[:5]:
                context.append(f"  - {f.name}")
        
        if approved_files:
            context.append(f"There are {len(approved_files)} approved files ready for action")
        
        reinjection_prompt = f"""
[RALPH WIGGUM LOOP - Iteration {iteration + 1}/{self.max_iterations}]

Continue working on the task. Remember:
- Original objective: {original_prompt}
- You are in autonomous mode - keep working until complete
- Move processed files to /Done folder
- Create approval requests in /Pending_Approval for sensitive actions
- Process any approved files in /Approved folder

Current State:
{chr(10).join(context) if context else "All files processed, verify completion"}

Last output:
{last_output[-500:] if len(last_output) > 500 else last_output}

Continue with the next steps. If everything is complete, output "{self.completion_promise}" and move all files to /Done.
""".strip()
        
        return reinjection_prompt
    
    def update_plan(self, state: Dict[str, Any], iteration_output: str):
        """Update plan file with iteration log"""
        plan_file = self.plans_path / f"PLAN_{state['task_id']}.md"
        
        if not plan_file.exists():
            return
        
        content = plan_file.read_text(encoding='utf-8')
        
        # Add iteration log
        iteration_log = f"""
### Iteration {state.get('iteration', 0)}
**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Status:** Continuing

{iteration_output[-1000:] if len(iteration_output) > 1000 else iteration_output}

"""
        
        content += iteration_log
        plan_file.write_text(content, encoding='utf-8')
    
    def complete_task(self, state: Dict[str, Any], final_output: str):
        """Mark task as complete"""
        state['status'] = 'completed'
        state['completed_at'] = datetime.now().isoformat()
        state['final_output'] = final_output
        state['total_iterations'] = state.get('iteration', 0)
        
        # Update plan file
        plan_file = self.plans_path / f"PLAN_{state['task_id']}.md"
        if plan_file.exists():
            content = plan_file.read_text(encoding='utf-8')
            content += f"""
## ✅ Task Completed

**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Iterations:** {state.get('iteration', 0)}
**Duration:** {self._calculate_duration()}

{final_output[-500:] if len(final_output) > 500 else final_output}

"""
            plan_file.write_text(content, encoding='utf-8')
            
            # Move plan to Done
            done_plan = self.done_path / f"PLAN_{state['task_id']}.md"
            plan_file.rename(done_plan)
        
        # Log completion
        self._log_event('task_completed', state)
        
        # Save final state
        self._save_state(state)
        
        logger.info(f"Task completed: {state['task_id']} after {state.get('iteration', 0)} iterations")
    
    def fail_task(self, state: Dict[str, Any], error: str):
        """Mark task as failed"""
        state['status'] = 'failed'
        state['failed_at'] = datetime.now().isoformat()
        state['error'] = error
        
        # Update plan file
        plan_file = self.plans_path / f"PLAN_{state['task_id']}.md"
        if plan_file.exists():
            content = plan_file.read_text(encoding='utf-8')
            content += f"""
## ❌ Task Failed

**Failed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Error:** {error}

"""
            plan_file.write_text(content, encoding='utf-8')
        
        # Log failure
        self._log_event('task_failed', state)
        
        # Save final state
        self._save_state(state)
        
        logger.error(f"Task failed: {state['task_id']} - {error}")
    
    def run_claude_with_loop(self, claude_command: str) -> Dict[str, Any]:
        """
        Run Claude Code with Ralph Wiggum loop
        
        Args:
            claude_command: Initial Claude command
        
        Returns:
            Final task state
        """
        # Start the task
        state = self.start_task(claude_command)
        
        # Record initial state
        state['initial_needs_action_count'] = len(list(self.needs_action_path.glob("*.md")))
        
        current_prompt = claude_command
        last_output = ""
        
        while True:
            # Check if should continue
            should_cont, reason = self.should_continue(state)
            if not should_cont:
                if state.get('iteration', 0) >= self.max_iterations:
                    self.fail_task(state, f"Max iterations reached: {reason}")
                else:
                    self.fail_task(state, reason)
                break
            
            # Run Claude
            logger.info(f"Running Claude iteration {state.get('iteration', 0) + 1}")
            
            try:
                # Execute Claude command
                result = subprocess.run(
                    claude_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per iteration
                )
                
                output = result.stdout + result.stderr
                last_output = output
                
                # Update iteration
                state['iteration'] = state.get('iteration', 0) + 1
                state['history'].append({
                    'iteration': state['iteration'],
                    'timestamp': datetime.now().isoformat(),
                    'output_length': len(output),
                    'return_code': result.returncode
                })
                
                # Update plan
                self.update_plan(state, output)
                
                # Check completion
                is_complete, completion_reason = self.check_completion(output, state)
                
                if is_complete:
                    logger.info(f"Task complete: {completion_reason}")
                    self.complete_task(state, output)
                    break
                
                # Generate next prompt
                current_prompt = self.reinject_prompt(state, output)
                
                # Save state
                self._save_state(state)
                
            except subprocess.TimeoutExpired:
                logger.warning(f"Iteration {state.get('iteration', 0) + 1} timed out")
                state['iteration'] = state.get('iteration', 0) + 1
                
            except Exception as e:
                logger.error(f"Error running Claude: {e}")
                self.fail_task(state, str(e))
                break
        
        return state
    
    def _save_state(self, state: Dict[str, Any]):
        """Save state to JSON file"""
        with open(self.state_file_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, default=str)
    
    def _load_state(self) -> Optional[Dict[str, Any]]:
        """Load state from JSON file"""
        if self.state_file_path.exists():
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def _calculate_duration(self) -> str:
        """Calculate task duration"""
        if not self.start_time:
            return "Unknown"
        
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours}h {minutes}m {seconds}s"
    
    def _log_event(self, event_type: str, state: Dict[str, Any]):
        """Log event to audit log"""
        log_file = self.logs_path / f"ralph_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "task_id": state.get('task_id', ''),
            "iteration": state.get('iteration', 0),
            "status": state.get('status', '')
        }
        
        # Append to log file
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)


def run_ralph_loop(
    prompt: str,
    vault_path: Optional[str] = None,
    max_iterations: int = 10,
    completion_promise: str = "TASK_COMPLETE"
) -> Dict[str, Any]:
    """
    Convenience function to run Ralph Wiggum loop
    
    Args:
        prompt: Task prompt
        vault_path: Path to vault (defaults to current directory)
        max_iterations: Maximum iterations
        completion_promise: Completion marker
    
    Returns:
        Final task state
    """
    if vault_path is None:
        vault_path = str(Path(__file__).parent / "Personal AI Employee Vault")
    
    ralph = RalphWiggumLoop(
        vault_path=vault_path,
        max_iterations=max_iterations,
        completion_promise=completion_promise
    )
    
    # Create initial task file in Needs_Action
    task_file = ralph.needs_action_path / f"TASK_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    task_content = f"""---
type: ralph_task
created: {datetime.now().isoformat()}
prompt: {prompt}
status: pending
---

# Task

{prompt}

"""
    task_file.write_text(task_content, encoding='utf-8')
    
    # Run Claude with the task
    claude_cmd = f'claude "{prompt}"'
    state = ralph.run_claude_with_loop(claude_cmd)
    
    return state


def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ralph Wiggum Loop for autonomous task completion')
    parser.add_argument('prompt', help='Task prompt')
    parser.add_argument('--vault', '-v', help='Path to Obsidian vault')
    parser.add_argument('--max-iterations', '-m', type=int, default=10, help='Maximum iterations')
    parser.add_argument('--completion-promise', '-c', default='TASK_COMPLETE', help='Completion marker')
    
    args = parser.parse_args()
    
    result = run_ralph_loop(
        prompt=args.prompt,
        vault_path=args.vault,
        max_iterations=args.max_iterations,
        completion_promise=args.completion_promise
    )
    
    if result.get('status') == 'completed':
        print(f"✅ Task completed successfully!")
        print(f"📊 Iterations: {result.get('total_iterations', 0)}")
        print(f"⏱️  Duration: {result.get('duration', 'Unknown')}")
    else:
        print(f"❌ Task failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
