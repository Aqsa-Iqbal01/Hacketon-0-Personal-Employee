"""
MCP Email Server - Enhanced version with scheduling, approval workflows, and audit logging

Provides comprehensive email capabilities with human-in-the-loop approval for sensitive actions.
"""

import os
import json
import logging
import smtplib
import schedule
import time
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from threading import Thread, Event

class EnhancedMCPEmailServer:
    def __init__(self, config_path: str = "mcp_email_config.json"):
        """
        Initialize the enhanced MCP email server.

        Args:
            config_path (str): Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logger()
        self.logger.info("Enhanced MCP Email Server initialized")

        # Approval workflow
        self.approval_queue = []
        self.approval_handlers = {}
        self.approval_event = Event()

        # Scheduling
        self.scheduled_tasks = []
        self.scheduler_thread = None
        self.scheduler_running = False

        # Audit logging
        self.audit_log_file = self.config_path.parent / "email_audit_log.json"

        # Initialize approval workflow
        self._initialize_approval_workflow()

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
                    "email": {
                        "host": "smtp.gmail.com",
                        "port": 587,
                        "use_tls": True,
                        "use_ssl": False,
                        "credentials": {
                            "username": os.getenv("EMAIL_USERNAME"),
                            "password": os.getenv("EMAIL_PASSWORD")
                        }
                    },
                    "defaults": {
                        "from": os.getenv("DEFAULT_FROM_EMAIL"),
                        "reply_to": os.getenv("DEFAULT_REPLY_TO_EMAIL")
                    },
                    "approval": {
                        "threshold": {
                            "amount": 100.0,
                            "new_recipients": True,
                            "bulk_sends": 10
                        },
                        "notification": {
                            "enabled": True,
                            "method": "email",
                            "interval": 300
                        }
                    },
                    "scheduling": {
                        "enabled": True,
                        "check_interval": 60
                    },
                    "audit": {
                        "enabled": True,
                        "retention_days": 90
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
        logger = logging.getLogger('EnhancedMCPEmailServer')
        logger.setLevel(logging.INFO)

        # Create handlers
        file_handler = logging.FileHandler('enhanced_mcp_email_server.log')
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

    def _initialize_approval_workflow(self):
        """Initialize the approval workflow system."""
        # Load existing approval queue
        approval_file = self.config_path.parent / "approval_queue.json"
        if approval_file.exists():
            with open(approval_file, 'r') as f:
                self.approval_queue = json.load(f)

    def _save_approval_queue(self):
        """Save the approval queue to file."""
        approval_file = self.config_path.parent / "approval_queue.json"
        with open(approval_file, 'w') as f:
            json.dump(self.approval_queue, f, indent=2)

    def _start_scheduler(self):
        """Start the task scheduler."""
        if self.config["scheduling"]["enabled"]:
            self.scheduler_running = True
            self.scheduler_thread = Thread(target=self._scheduler_loop)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            self.logger.info("Email scheduler started")

    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.scheduler_running:
            try:
                schedule.run_pending()
                time.sleep(self.config["scheduling"]["check_interval"])
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")

    def _check_approval_required(self, email_data: Dict[str, Any]) -> bool:
        """Check if email requires approval based on configured thresholds."""
        # Check amount threshold
        if email_data.get("amount") and email_data["amount"] > self.config["approval"]["threshold"]["amount"]:
            return True

        # Check new recipients
        if self.config["approval"]["threshold"]["new_recipients"]:
            # In a real implementation, check if recipient is in known contacts
            # For now, assume any external recipient requires approval
            if "@" in email_data.get("to", ""):
                return True

        # Check bulk sends
        if len(email_data.get("to", "").split(",")) > self.config["approval"]["threshold"]["bulk_sends"]:
            return True

        return False

    def _create_approval_request(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an approval request for an email."""
        request_id = f"EMAIL_APPROVAL_{datetime.now().isoformat()}"

        approval_request = {
            "id": request_id,
            "type": "email_approval",
            "email_data": email_data,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "status": "pending",
            "requester": email_data.get("from", "system"),
            "justification": email_data.get("justification", "Automated email processing"),
            "metadata": {
                "amount": email_data.get("amount"),
                "recipients": email_data.get("to"),
                "attachments": len(email_data.get("attachments", [])),
                "priority": email_data.get("priority", "normal")
            }
        }

        # Add to approval queue
        self.approval_queue.append(approval_request)
        self._save_approval_queue()

        # Log audit event
        self._log_audit_event("approval_requested", {
            "request_id": request_id,
            "email_data": email_data,
            "reason": "threshold_exceeded"
        })

        return approval_request

    def _log_audit_event(self, event_type: str, details: Dict[str, Any]):
        """Log an audit event."""
        if not self.config["audit"]["enabled"]:
            return

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
            "source": "email_server",
            "config_version": self.config.get("version", "1.0")
        }

        # Load existing audit log
        audit_log = []
        if self.audit_log_file.exists():
            with open(self.audit_log_file, 'r') as f:
                audit_log = json.load(f)

        audit_log.append(audit_entry)

        # Apply retention policy
        retention_date = datetime.now() - timedelta(days=self.config["audit"]["retention_days"])
        audit_log = [entry for entry in audit_log if datetime.fromisoformat(entry["timestamp"]) > retention_date]

        # Save audit log
        with open(self.audit_log_file, 'w') as f:
            json.dump(audit_log, f, indent=2)

    def send_email(self, to: str, subject: str, body: str,
                   from_email: Optional[str] = None,
                   reply_to: Optional[str] = None,
                   cc: Optional[List[str]] = None,
                   bcc: Optional[List[str]] = None,
                   attachments: Optional[List[str]] = None,
                   is_html: bool = False,
                   amount: Optional[float] = None,
                   justification: Optional[str] = None,
                   priority: str = "normal") -> Dict[str, Any]:
        """
        Send an email through the MCP server with approval workflow.

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
            amount (Optional[float]): Amount associated with email (for approval)
            justification (Optional[str]): Justification for approval
            priority (str): Email priority (normal, high, urgent)

        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            self.logger.info(f"Sending email to: {to}, subject: {subject}")

            # Prepare email data
            email_data = {
                "to": to,
                "subject": subject,
                "body": body,
                "from": from_email,
                "reply_to": reply_to,
                "cc": cc,
                "bcc": bcc,
                "attachments": attachments,
                "is_html": is_html,
                "amount": amount,
                "justification": justification,
                "priority": priority,
                "created_at": datetime.now().isoformat()
            }

            # Check if approval is required
            if self._check_approval_required(email_data):
                self.logger.info("Email requires approval")
                approval_request = self._create_approval_request(email_data)

                # Return approval required response
                return {
                    "success": False,
                    "status": "approval_required",
                    "request_id": approval_request["id"],
                    "message": "Email requires approval before sending",
                    "approval_request": approval_request
                }

            # Send email directly
            result = self._send_email_directly(email_data)

            if result["success"]:
                # Log audit event
                self._log_audit_event("email_sent", {
                    "email_data": email_data,
                    "approval": "auto_approved"
                })

            return result

        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return {"success": False, "error": str(e)}

    def _send_email_directly(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email directly without approval."""
        try:
            # Get email configuration
            email_config = self.config["email"]
            defaults = self.config["defaults"]

            # Set from and reply-to addresses
            from_addr = email_data.get("from") or defaults.get("from")
            reply_addr = email_data.get("reply_to") or defaults.get("reply_to") or from_addr

            if not from_addr:
                raise ValueError("No from email address configured")

            # Create message
            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = email_data["to"]
            msg["Subject"] = email_data["subject"]
            if reply_addr:
                msg.add_header("reply-to", reply_addr)
            if email_data.get("cc"):
                msg["Cc"] = ", ".join(email_data["cc"])

            # Attach body
            if email_data["is_html"]:
                msg.attach(MIMEText(email_data["body"], "html"))
            else:
                msg.attach(MIMEText(email_data["body"], "plain"))

            # Attach files
            if email_data.get("attachments"):
                for attachment_path in email_data["attachments"]:
                    self._attach_file(msg, attachment_path)

            # Connect to SMTP server
            server = self._get_smtp_server(email_config)

            # Send email
            to_addrs = [email_data["to"]]
            if email_data.get("cc"):
                to_addrs.extend(email_data["cc"])
            if email_data.get("bcc"):
                to_addrs.extend(email_data["bcc"])

            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()

            self.logger.info(f"Email sent successfully to {email_data['to']}")
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

    def approve_email(self, request_id: str, approver: str) -> Dict[str, Any]:
        """Approve a pending email approval request."""
        try:
            # Find the approval request
            request = next((r for r in self.approval_queue if r["id"] == request_id), None)
            if not request:
                return {"success": False, "error": "Approval request not found"}

            if request["status"] != "pending":
                return {"success": False, "error": "Approval request already processed"}

            # Update request status
            request["status"] = "approved"
            request["approved_by"] = approver
            request["approved_at"] = datetime.now().isoformat()
            self._save_approval_queue()

            # Send the email
            email_data = request["email_data"]
            result = self._send_email_directly(email_data)

            if result["success"]:
                # Log audit event
                self._log_audit_event("email_approved_and_sent", {
                    "request_id": request_id,
                    "approver": approver,
                    "email_data": email_data
                })

            return result

        except Exception as e:
            self.logger.error(f"Error approving email: {e}")
            return {"success": False, "error": str(e)}

    def reject_email(self, request_id: str, approver: str, reason: str) -> Dict[str, Any]:
        """Reject a pending email approval request."""
        try:
            # Find the approval request
            request = next((r for r in self.approval_queue if r["id"] == request_id), None)
            if not request:
                return {"success": False, "error": "Approval request not found"}

            if request["status"] != "pending":
                return {"success": False, "error": "Approval request already processed"}

            # Update request status
            request["status"] = "rejected"
            request["rejected_by"] = approver
            request["rejected_at"] = datetime.now().isoformat()
            request["rejection_reason"] = reason
            self._save_approval_queue()

            # Log audit event
            self._log_audit_event("email_rejected", {
                "request_id": request_id,
                "approver": approver,
                "reason": reason,
                "email_data": request["email_data"]
            })

            return {"success": True, "message": "Email approval rejected"}

        except Exception as e:
            self.logger.error(f"Error rejecting email: {e}")
            return {"success": False, "error": str(e)}

    def schedule_email(self, to: str, subject: str, body: str,
                       send_at: datetime,
                       from_email: Optional[str] = None,
                       reply_to: Optional[str] = None,
                       cc: Optional[List[str]] = None,
                       bcc: Optional[List[str]] = None,
                       attachments: Optional[List[str]] = None,
                       is_html: bool = False,
                       amount: Optional[float] = None,
                       justification: Optional[str] = None,
                       priority: str = "normal") -> Dict[str, Any]:
        """
        Schedule an email to be sent at a specific time.

        Args:
            to (str): Recipient email address
            subject (str): Email subject
            body (str): Email body content
            send_at (datetime): When to send the email
            from_email (Optional[str]): Sender email address
            reply_to (Optional[str]): Reply-to email address
            cc (Optional[List[str]]): CC recipients
            bcc (Optional[List[str]]): BCC recipients
            attachments (Optional[List[str]]): List of file paths to attach
            is_html (bool): Whether body is HTML
            amount (Optional[float]): Amount associated with email
            justification (Optional[str]): Justification for approval
            priority (str): Email priority

        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            self.logger.info(f"Scheduling email to: {to}, subject: {subject}, send_at: {send_at}")

            # Prepare email data
            email_data = {
                "to": to,
                "subject": subject,
                "body": body,
                "from": from_email,
                "reply_to": reply_to,
                "cc": cc,
                "bcc": bcc,
                "attachments": attachments,
                "is_html": is_html,
                "amount": amount,
                "justification": justification,
                "priority": priority,
                "scheduled_at": send_at.isoformat(),
                "created_at": datetime.now().isoformat()
            }

            # Check if approval is required
            if self._check_approval_required(email_data):
                approval_request = self._create_approval_request(email_data)
                return {
                    "success": False,
                    "status": "approval_required",
                    "request_id": approval_request["id"],
                    "message": "Scheduled email requires approval before scheduling",
                    "approval_request": approval_request
                }

            # Schedule the email
            schedule_time = send_at - datetime.now()
            if schedule_time.total_seconds() > 0:
                schedule.every(schedule_time.total_seconds()).seconds.do(
                    self._send_scheduled_email,
                    email_data=email_data
                )
                self.logger.info(f"Email scheduled for {send_at}")

                # Log audit event
                self._log_audit_event("email_scheduled", {
                    "email_data": email_data,
                    "send_at": send_at.isoformat()
                })

                return {"success": True, "message": "Email scheduled successfully"}
            else:
                return {"success": False, "error": "Send time is in the past"}

        except Exception as e:
            self.logger.error(f"Error scheduling email: {e}")
            return {"success": False, "error": str(e)}

    def _send_scheduled_email(self, email_data: Dict[str, Any]):
        """Send a scheduled email."""
        try:
            self.logger.info(f"Sending scheduled email to: {email_data['to']}")
            result = self._send_email_directly(email_data)

            # Log audit event
            self._log_audit_event("scheduled_email_sent", {
                "email_data": email_data,
                "sent_at": datetime.now().isoformat()
            })

            return result

        except Exception as e:
            self.logger.error(f"Error sending scheduled email: {e}")
            return {"success": False, "error": str(e)}

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests."""
        return [req for req in self.approval_queue if req["status"] == "pending"]

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        if not self.audit_log_file.exists():
            return []

        with open(self.audit_log_file, 'r') as f:
            audit_log = json.load(f)

        return audit_log[-limit:]

    def cleanup(self):
        """Clean up resources."""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        self.logger.info("Enhanced MCP Email Server shutting down")

if __name__ == "__main__":
    # Example usage
    server = EnhancedMCPEmailServer()

    # Test sending an email
    result = server.send_email(
        to="test@example.com",
        subject="Test Email from Enhanced MCP Server",
        body="This is a test email sent through the enhanced MCP email server.",
        from_email="noreply@example.com",
        amount=150.0,
        justification="Test approval workflow"
    )

    print(f"Email result: {result}")

    # Schedule an email
    send_time = datetime.now() + timedelta(minutes=5)
    schedule_result = server.schedule_email(
        to="test@example.com",
        subject="Scheduled Test Email",
        body="This is a scheduled test email.",
        send_at=send_time,
        from_email="noreply@example.com"
    )

    print(f"Schedule result: {schedule_result}")

    # Get pending approvals
    approvals = server.get_pending_approvals()
    print(f"Pending approvals: {approvals}")