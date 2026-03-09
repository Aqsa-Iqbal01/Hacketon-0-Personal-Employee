"""
Base Watcher Class - Template for all watchers

Provides the core architecture for monitoring systems and triggering AI processing.
"""

import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod

class BaseWatcher(ABC):
    def __init__(self, vault_path: str, check_interval: int = 60):
        """
        Initialize the base watcher.

        Args:
            vault_path (str): Path to the Obsidian vault
            check_interval (int): Time between checks in seconds
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)

        # Create folders if they don't exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.logger.info(f'Initialized {self.__class__.__name__} watching {self.vault_path}')

    @abstractmethod
    def check_for_updates(self) -> list:
        """
        Check for new updates or events.

        Returns:
            list: List of new items to process
        """
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """
        Create an action file in the Needs_Action folder.

        Args:
            item: The item to create an action file for

        Returns:
            Path: Path to the created action file
        """
        pass

    def run(self):
        """
        Main watcher loop. Continuously checks for updates.
        """
        self.logger.info(f'Starting {self.__class__.__name__}')
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
            except Exception as e:
                self.logger.error(f'Error in {self.__class__.__name__}: {e}')
            time.sleep(self.check_interval)

if __name__ == "__main__":
    # Basic test to verify the base class works
    watcher = BaseWatcher(vault_path="test", check_interval=10)
    print("BaseWatcher initialized successfully")