"""
Task Scheduler - Cron-like scheduling system for automated tasks

Provides scheduling capabilities for automated LinkedIn posting, email processing,
and other periodic tasks in the Personal AI Employee system.
"""

import time
import schedule
import json
import logging
from datetime import datetime, timedelta
from threading import Thread, Event
from typing import Callable, Dict, List, Any, Optional
from pathlib import Path

class TaskScheduler:
    def __init__(self, config_path: str = "scheduler_config.json"):
        """
        Initialize the task scheduler.

        Args:
            config_path (str): Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logger()
        self.logger.info("Task Scheduler initialized")

        # Scheduled tasks
        self.tasks = []
        self.running = False
        self.scheduler_thread = None
        self.scheduler_event = Event()

        # Persistence
        self.persistence_file = self.config_path.parent / "scheduled_tasks.json"
        self._load_persisted_tasks()

        # Start scheduler
        self._start_scheduler()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "scheduler": {
                        "enabled": True,
                        "check_interval": 60,
                        "max_concurrent_tasks": 5,
                        "retry_attempts": 3,
                        "retry_delay": 300
                    },
                    "logging": {
                        "level": "INFO",
                        "file": "scheduler.log"
                    }
                }
                self._save_config(default_config)
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            raise

    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def _setup_logger(self):
        """Set up logging."""
        logger = logging.getLogger('TaskScheduler')
        logger.setLevel(logging.INFO)

        # Create handlers
        file_handler = logging.FileHandler(self.config["logging"]["file"])
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create formatter and add to handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        return logger

    def _start_scheduler(self):
        """Start the scheduler."""
        if self.config["scheduler"]["enabled"]:
            self.running = True
            self.scheduler_thread = Thread(target=self._scheduler_loop)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            self.logger.info("Task scheduler started")

    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                self.scheduler_event.wait(self.config["scheduler"]["check_interval"])
                self.scheduler_event.clear()
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")

    def _load_persisted_tasks(self):
        """Load persisted scheduled tasks."""
        if self.persistence_file.exists():
            with open(self.persistence_file, 'r') as f:
                self.tasks = json.load(f)
            self.logger.info(f"Loaded {len(self.tasks)} persisted tasks")

    def _save_persisted_tasks(self):
        """Save scheduled tasks to persistence file."""
        with open(self.persistence_file, 'w') as f:
            json.dump(self.tasks, f, indent=2)

    def _get_next_run_time(self, interval: str, time_unit: str) -> datetime:
        """Calculate next run time for a task."""
        now = datetime.now()
        if interval == "daily":
            next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)  # 9 AM daily
            if next_run < now:
                next_run += timedelta(days=1)
        elif interval == "weekly":
            next_run = now + timedelta(weeks=1)
            next_run = next_run.replace(hour=9, minute=0, second=0, microsecond=0)
        elif interval == "monthly":
            next_run = now + timedelta(days=30)
            next_run = next_run.replace(hour=9, minute=0, second=0, microsecond=0)
        else:  # Custom interval in seconds
            next_run = now + timedelta(seconds=int(interval))
        return next_run

    def add_task(self, name: str, interval: str, time_unit: str,
                 task_func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """
        Add a scheduled task.

        Args:
            name (str): Task name
            interval (str): Time interval (e.g., "daily", "weekly", "monthly", or number for seconds)
            time_unit (str): Time unit for interval
            task_func (Callable): Function to execute
            *args: Arguments for the task function
            **kwargs: Keyword arguments for the task function

        Returns:
            Dict[str, Any]: Task details
        """
        try:
            self.logger.info(f"Adding task: {name}")

            # Create task details
            task = {
                "id": f"task_{len(self.tasks) + 1}",
                "name": name,
                "interval": interval,
                "time_unit": time_unit,
                "func_name": task_func.__name__,
                "args": args,
                "kwargs": kwargs,
                "created_at": datetime.now().isoformat(),
                "next_run": self._get_next_run_time(interval, time_unit).isoformat(),
                "status": "scheduled",
                "retry_count": 0,
                "max_retries": self.config["scheduler"]["retry_attempts"]
            }

            # Schedule the task
            if interval == "daily":
                schedule.every().day.at("09:00").do(task_func, *args, **kwargs)
            elif interval == "weekly":
                schedule.every().monday.at("09:00").do(task_func, *args, **kwargs)
            elif interval == "monthly":
                schedule.every(30).days.do(task_func, *args, **kwargs)
            else:
                schedule.every(int(interval)).seconds.do(task_func, *args, **kwargs)

            # Add to task list
            self.tasks.append(task)
            self._save_persisted_tasks()

            self.logger.info(f"Task {name} scheduled for {task['next_run']}")
            return task

        except Exception as e:
            self.logger.error(f"Error adding task {name}: {e}")
            return {"success": False, "error": str(e)}

    def remove_task(self, task_id: str) -> Dict[str, Any]:
        """Remove a scheduled task."""
        try:
            # Find and remove task
            task = next((t for t in self.tasks if t["id"] == task_id), None)
            if not task:
                return {"success": False, "error": "Task not found"}

            # Remove from schedule (this is a simplified implementation)
            # In a real implementation, you'd need to maintain a mapping of task_id to schedule
            self.tasks = [t for t in self.tasks if t["id"] != task_id]
            self._save_persisted_tasks()

            self.logger.info(f"Task {task_id} removed")
            return {"success": True, "message": "Task removed successfully"}

        except Exception as e:
            self.logger.error(f"Error removing task {task_id}: {e}")
            return {"success": False, "error": str(e)}

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        return self.tasks

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific task."""
        return next((t for t in self.tasks if t["id"] == task_id), None)

    def run_task_immediately(self, task_id: str) -> Dict[str, Any]:
        """Run a task immediately."""
        try:
            task = self.get_task(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}

            # Get the function from globals() (simplified - in real implementation, use a registry)
            func = globals().get(task["func_name"])
            if not func:
                return {"success": False, "error": "Task function not found"}

            # Execute the task
            try:
                result = func(*task["args"], **task["kwargs"])
                self.logger.info(f"Task {task_id} executed successfully")
                return {"success": True, "result": result}
            except Exception as e:
                self.logger.error(f"Error executing task {task_id}: {e}")
                return {"success": False, "error": str(e)}

        except Exception as e:
            self.logger.error(f"Error running task {task_id}: {e}")
            return {"success": False, "error": str(e)}

    def cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_event.set()
            self.scheduler_thread.join(timeout=5)

        self.logger.info("Task Scheduler shutting down")

# Example task functions
def example_daily_task():
    """Example daily task."""
    print("Executing example daily task at", datetime.now())
    return "Daily task completed"

def example_weekly_task():
    """Example weekly task."""
    print("Executing example weekly task at", datetime.now())
    return "Weekly task completed"

def example_monthly_task():
    """Example monthly task."""
    print("Executing example monthly task at", datetime.now())
    return "Monthly task completed"

def example_custom_task():
    """Example custom interval task."""
    print("Executing example custom task at", datetime.now())
    return "Custom task completed"

if __name__ == "__main__":
    # Example usage
    scheduler = TaskScheduler()

    # Add tasks
    scheduler.add_task("Daily Check", "daily", "day", example_daily_task)
    scheduler.add_task("Weekly Report", "weekly", "week", example_weekly_task)
    scheduler.add_task("Monthly Audit", "monthly", "month", example_monthly_task)
    scheduler.add_task("Custom Task", "3600", "seconds", example_custom_task)  # Every hour

    print("🚀 Task Scheduler started!")
    print("⏰ Scheduling automated tasks...")
    print("⏹ Pause: Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.cleanup()