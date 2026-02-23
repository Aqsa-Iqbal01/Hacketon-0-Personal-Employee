"""
MCP Email Server - Model Context Protocol server for email actions

Provides email sending capabilities through the MCP interface for Claude Code.
"""

import os
import json
import logging
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any

class MCPEmailServer:
    def __init__(self, config_path: str = "mcp_email_config.json"):
        """
        Initialize the MCP email server.

        Args:
            config_path (str): Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logger()
        self.logger.info("MCP Email Server initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "email": {
                        "host": "smtp.gmail.com",
                        "port": 587,
                        "use_tls": true,
                        "use_ssl": false,
                        "credentials": {
                            "username": os.getenv("EMAIL_USERNAME"),
                            "password": os.getenv("EMAIL_PASSWORD")
                        }
                    },
                    "defaults": {
                        "from": os.getenv("DEFAULT_FROM_EMAIL"),
                        "reply_to": os.getenv("DEFAULT_REPLY_TO_EMAIL")
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
        logger = logging.getLogger('MCPEmailServer')
        logger.setLevel(logging.INFO)

        # Create handlers
        file_handler = logging.FileHandler('mcp_email_server.log')
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

    def send_email(self, to: str, subject: str, body: str,
                   from_email: Optional[str] = None,
                   reply_to: Optional[str] = None,
                   cc: Optional[List[str]] = None,
                   bcc: Optional[List[str]] = None,
                   attachments: Optional[List[str]] = None,
                   is_html: bool = False,
                   approval_required: bool = False,
                   approval_action: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an email through the MCP server.

        Args:
            to (str): Recipient email address
            subject (str): Email subject
            body (str): Email body content
            from_email (Optional[str]): Sender email address
            reply_to (Optional[str]): Reply-to email address
            cc (Optional[List[str]]): CC recipients
            bcc (Optional[List[str]]): BCC recipients
            attachments (Optional[List[str]]): List of file paths to attach
            is_html (bool): Whether body is HTML
            approval_required (bool): Whether approval is required before sending
            approval_action (Optional[str]): Action to perform after approval (e.g., "send_email")

        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            self.logger.info(f"Sending email to: {to}, subject: {subject}")

            # Get email configuration
            email_config = self.config["email"]
            defaults = self.config["defaults"]

            # Set from and reply-to addresses
            from_addr = from_email or defaults.get("from")
            reply_addr = reply_to or defaults.get("reply_to") or from_addr

            if not from_addr:
                raise ValueError("No from email address configured")

            if approval_required:
                # Create approval request instead of sending
                approval_result = self._create_approval_request(
                    to, subject, body, from_addr, reply_addr, cc, bcc, attachments, is_html, approval_action
                )
                return approval_result

            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = to
            msg['Subject'] = subject
            if reply_addr:
                msg.add_header('reply-to', reply_addr)
            if cc:
                msg['Cc'] = ", ".join(cc)

            # Attach body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Attach files
            if attachments:
                for attachment_path in attachments:
                    self._attach_file(msg, attachment_path)

            # Connect to SMTP server
            server = self._get_smtp_server(email_config)

            # Send email
            to_addrs = [to]
            if cc:
                to_addrs.extend(cc)
            if bcc:
                to_addrs.extend(bcc)

            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()

            self.logger.info(f"Email sent successfully to {to}")
            return {"success": True, "message": "Email sent successfully"}

        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return {"success": False, "error": str(e)}

    def _get_smtp_server(self, config: Dict[str, Any]):
        """Get configured SMTP server."""
        if config["use_ssl"]:
            server = smtplib.SMTP_SSL(config["host"], config["port"])
        else:
            server = smtplib.SMTP(config["host"], config["port"])
            if config["use_tls"]:
                server.starttls()

        # Login
        if config["credentials"]["username"] and config["credentials"]["password"]:
            server.login(config["credentials"]["username"], config["credentials"]["password"])

        return server

    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Attach a file to the email."""
        try:
            attachment = MIMEBase('application', 'octet-stream')
            with open(file_path, 'rb') as f:
                attachment.set_payload(f.read())

            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename={Path(file_path).name}')
            msg.attach(attachment)

            self.logger.info(f"Attached file: {file_path}")

        except Exception as e:
            self.logger.error(f"Error attaching file {file_path}: {e}")

    def get_email_templates(self) -> List[Dict[str, Any]]:
        """Get available email templates."""
        return [
            {
                "name": "welcome",
                "subject": "Welcome to Our Service!",
                "body": "Hello {name},\n\nThank you for joining our service. We're excited to have you on board!\n\nBest regards,\nYour Team"
            },
            {
                "name": "invoice",
                "subject": "Invoice {invoice_number}",
                "body": "Hello {name},\n\nPlease find attached Invoice #{invoice_number} for {amount}.\n\nPayment is due by {due_date}.\n\nBest regards,\nYour Team"
            },
            {
                "name": "follow_up",
                "subject": "Following up on our conversation",
                "body": "Hello {name},\n\nI wanted to follow up on our recent conversation about {topic}. Do you have any questions or need further information?\n\nBest regards,\nYour Team"
            }
        ]

    def render_template(self, template_name: str, variables: Dict[str, str]) -> Dict[str, str]:
        """Render an email template with variables."""
        templates = self.get_email_templates()
        template = next((t for t in templates if t["name"] == template_name), None)

        if not template:
            return {"success": False, "error": "Template not found"}

        try:
            subject = template["subject"].format(**variables)
            body = template["body"].format(**variables)
            return {"success": True, "subject": subject, "body": body}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_email(self, email: str) -> bool:
        """Validate an email address."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

if __name__ == "__main__":
    # Example usage
    server = MCPEmailServer()

    # Test sending an email
    result = server.send_email(
        to="test@example.com",
        subject="Test Email from MCP Server",
        body="This is a test email sent through the MCP email server.",
        from_email="noreply@example.com"
    )

    print(f"Email result: {result}")

    # Test template rendering
    template_result = server.render_template(
        "welcome",
        variables={"name": "John Doe"}
    )

    print(f"Template result: {template_result}")

    # Test email validation
    valid = server.validate_email("test@example.com")
    print(f"Email validation: {valid}")