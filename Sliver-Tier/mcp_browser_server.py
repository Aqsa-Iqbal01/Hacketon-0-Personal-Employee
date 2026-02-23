"""
MCP Browser Server - Model Context Protocol server for browser automation

Provides browser automation capabilities through the MCP interface for Claude Code.
Uses Playwright for web automation tasks.
"""

import os
import json
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright
from typing import Dict, List, Optional, Any, Union

class MCPBrowserServer:
    def __init__(self, config_path: str = "mcp_browser_config.json"):
        """
        Initialize the MCP browser server.

        Args:
            config_path (str): Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logger()
        self.logger.info("MCP Browser Server initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "browser": {
                        "type": "chromium",
                        "headless": True,
                        "args": ["--no-sandbox"]
                    },
                    "session_path": "browser_session",
                    "timeout": 30000  # 30 seconds
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
        logger = logging.getLogger('MCPBrowserServer')
        logger.setLevel(logging.INFO)

        # Create handlers
        file_handler = logging.FileHandler('mcp_browser_server.log')
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

    def navigate(self, url: str, wait_until: str = "networkidle") -> Dict[str, Any]:
        """
        Navigate to a URL.

        Args:
            url (str): URL to navigate to
            wait_until (str): When to consider navigation succeeded

        Returns:
            Dict[str, Any]: Result with success status and page info
        """
        try:
            self.logger.info(f"Navigating to: {url}")

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                page.goto(url, wait_until=wait_until)
                page.wait_for_load_state()

                # Get page information
                page_info = {
                    "url": page.url,
                    "title": page.title(),
                    "content": page.content()[:1000] + "..." if len(page.content()) > 1000 else page.content(),
                    "screenshot": self._take_screenshot(page)
                }

                browser.close()

                self.logger.info(f"Successfully navigated to {url}")
                return {"success": True, "page": page_info}

        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {e}")
            return {"success": False, "error": str(e)}

    def click_element(self, selector: str, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Click on an element.

        Args:
            selector (str): CSS selector for the element
            url (Optional[str]): URL to navigate to first (optional)

        Returns:
            Dict[str, Any]: Result with success status
        """
        try:
            if url:
                navigate_result = self.navigate(url)
                if not navigate_result["success"]:
                    return navigate_result

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                if url:
                    page.goto(url)

                # Wait for element to be visible
                page.wait_for_selector(selector)
                element = page.locator(selector)

                # Click the element
                element.click()

                # Wait a bit for any navigation
                page.wait_for_timeout(1000)

                browser.close()

                self.logger.info(f"Clicked element: {selector}")
                return {"success": True, "action": "clicked", "selector": selector}

        except Exception as e:
            self.logger.error(f"Error clicking element {selector}: {e}")
            return {"success": False, "error": str(e)}

    def fill_form(self, selector: str, text: str, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Fill a form field.

        Args:
            selector (str): CSS selector for the form field
            text (str): Text to fill in
            url (Optional[str]): URL to navigate to first (optional)

        Returns:
            Dict[str, Any]: Result with success status
        """
        try:
            if url:
                navigate_result = self.navigate(url)
                if not navigate_result["success"]:
                    return navigate_result

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                if url:
                    page.goto(url)

                # Wait for element to be visible
                page.wait_for_selector(selector)
                element = page.locator(selector)

                # Fill the form field
                element.fill(text)

                browser.close()

                self.logger.info(f"Filled form: {selector} with text: {text[:50]}...")
                return {"success": True, "action": "filled", "selector": selector, "text": text}

        except Exception as e:
            self.logger.error(f"Error filling form {selector}: {e}")
            return {"success": False, "error": str(e)}

    def take_screenshot(self, selector: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Take a screenshot of the page or specific element.

        Args:
            selector (Optional[str]): CSS selector for specific element (optional)
            url (Optional[str]): URL to navigate to first (optional)

        Returns:
            Dict[str, Any]: Result with success status and screenshot path
        """
        try:
            if url:
                navigate_result = self.navigate(url)
                if not navigate_result["success"]:
                    return navigate_result

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                if url:
                    page.goto(url)

                # Take screenshot
                screenshot_path = f"screenshot_{int(time.time())}.png"

                if selector:
                    element = page.locator(selector)
                    element.screenshot(path=screenshot_path)
                else:
                    page.screenshot(path=screenshot_path)

                browser.close()

                self.logger.info(f"Screenshot taken: {screenshot_path}")
                return {"success": True, "screenshot": screenshot_path}

        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return {"success": False, "error": str(e)}

    def get_page_content(self, selector: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Get page content or content of specific element.

        Args:
            selector (Optional[str]): CSS selector for specific element (optional)
            url (Optional[str]): URL to navigate to first (optional)

        Returns:
            Dict[str, Any]: Result with success status and content
        """
        try:
            if url:
                navigate_result = self.navigate(url)
                if not navigate_result["success"]:
                    return navigate_result

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                if url:
                    page.goto(url)

                # Get content
                if selector:
                    content = page.locator(selector).text_content() or ""
                else:
                    content = page.content()

                browser.close()

                self.logger.info(f"Got page content from {url or 'current page'}")
                return {"success": True, "content": content}

        except Exception as e:
            self.logger.error(f"Error getting page content: {e}")
            return {"success": False, "error": str(e)}

    def login(self, url: str, username_selector: str, password_selector: str,
              submit_selector: str, username: str, password: str) -> Dict[str, Any]:
        """
        Login to a website.

        Args:
            url (str): Login page URL
            username_selector (str): Username field selector
            password_selector (str): Password field selector
            submit_selector (str): Submit button selector
            username (str): Username
            password (str): Password

        Returns:
            Dict[str, Any]: Result with success status
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                # Navigate to login page
                page.goto(url)

                # Fill login form
                page.fill(username_selector, username)
                page.fill(password_selector, password)

                # Click submit
                page.click(submit_selector)

                # Wait for navigation
                page.wait_for_url(url, timeout=10000, state="present")

                browser.close()

                self.logger.info(f"Successfully logged in to {url}")
                return {"success": True, "action": "logged_in", "url": url}

        except Exception as e:
            self.logger.error(f"Error logging in to {url}: {e}")
            return {"success": False, "error": str(e)}

    def get_element_text(self, selector: str, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Get text content of an element.

        Args:
            selector (str): CSS selector for the element
            url (Optional[str]): URL to navigate to first (optional)

        Returns:
            Dict[str, Any]: Result with success status and text
        """
        try:
            if url:
                navigate_result = self.navigate(url)
                if not navigate_result["success"]:
                    return navigate_result

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                if url:
                    page.goto(url)

                # Wait for element to be visible
                page.wait_for_selector(selector)
                element = page.locator(selector)

                # Get text content
                text = element.text_content()

                browser.close()

                self.logger.info(f"Got element text: {selector}")
                return {"success": True, "text": text}

        except Exception as e:
            self.logger.error(f"Error getting element text {selector}: {e}")
            return {"success": False, "error": str(e)}

    def get_element_attribute(self, selector: str, attribute: str,
                            url: Optional[str] = None) -> Dict[str, Any]:
        """
        Get attribute value of an element.

        Args:
            selector (str): CSS selector for the element
            attribute (str): Attribute name
            url (Optional[str]): URL to navigate to first (optional)

        Returns:
            Dict[str, Any]: Result with success status and attribute value
        """
        try:
            if url:
                navigate_result = self.navigate(url)
                if not navigate_result["success"]:
                    return navigate_result

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                if url:
                    page.goto(url)

                # Wait for element to be visible
                page.wait_for_selector(selector)
                element = page.locator(selector)

                # Get attribute value
                attribute_value = element.get_attribute(attribute)

                browser.close()

                self.logger.info(f"Got element attribute: {selector} {attribute}")
                return {"success": True, "attribute": attribute_value}

        except Exception as e:
            self.logger.error(f"Error getting element attribute {selector} {attribute}: {e}")
            return {"success": False, "error": str(e)}

    def wait_for_element(self, selector: str, timeout: int = 30000,
                        url: Optional[str] = None) -> Dict[str, Any]:
        """
        Wait for an element to appear.

        Args:
            selector (str): CSS selector for the element
            timeout (int): Timeout in milliseconds
            url (Optional[str]): URL to navigate to first (optional)

        Returns:
            Dict[str, Any]: Result with success status
        """
        try:
            if url:
                navigate_result = self.navigate(url)
                if not navigate_result["success"]:
                    return navigate_result

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.config["session_path"],
                    headless=self.config["browser"]["headless"],
                    args=self.config["browser"]["args"]
                )
                page = browser.new_page()

                if url:
                    page.goto(url)

                # Wait for element to be visible
                page.wait_for_selector(selector, timeout=timeout)

                browser.close()

                self.logger.info(f"Element appeared: {selector}")
                return {"success": True, "action": "waited_for_element", "selector": selector}

        except Exception as e:
            self.logger.error(f"Error waiting for element {selector}: {e}")
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Example usage
    browser = MCPBrowserServer()

    # Test navigation
    result = browser.navigate("https://example.com")
    print(f"Navigation result: {result}")

    # Test taking screenshot
    screenshot_result = browser.take_screenshot(url="https://example.com")
    print(f"Screenshot result: {screenshot_result}")

    # Test getting element text
    text_result = browser.get_element_text("h1", url="https://example.com")
    print(f"Text result: {text_result}")