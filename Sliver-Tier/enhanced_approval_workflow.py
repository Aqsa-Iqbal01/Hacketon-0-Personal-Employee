"""
Enhanced Human Approval Workflow - Advanced approval system with notifications and audit logging

Provides comprehensive human-in-the-loop approval with multiple notification methods,
audit logging, and workflow management.
"""

import time
import logging
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from threading import Thread, Event

class EnhancedApprovalWorkflow:
    def __init__(self, config_path: str = "approval_config.json"):
        """Initialize the enhanced approval workflow."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logger()
        self.logger.info("Enhanced Approval Workflow initialized")

        # Approval queue and handlers
        self.approval_queue = []
        self.notification_handlers = {}
        self.approval_event = Event()

        # Persistence
        self.persistence_file = self.config_path.parent / "approval_queue.json"
        self._load_persisted_queue()

        # Start notification service
        self._start_notification_service()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "approval": {
                        "threshold": {
                            "amount": 100.0,
                            "new_recipients": True,
                            "bulk_sends": 10,
                            "sensitive_actions": ["payment", "delete", "reset"]
                        },
                        "notification": {
                            "enabled": True,
                            "methods": ["email", "slack", "webhook"],
                            "email": {
                                "enabled": True,
                                "from": "noreply@ai-employee.com",
                                "template": "approval_request_email_template.txt"
                            },
                            "slack": {
                                "enabled": True,
                                "webhook_url": os.getenv("SLACK_WEBHOOK_URL"),
                                "channel": "#approvals"
                            },
                            "webhook": {
                                "enabled": False,
                                "url": "",
                                "headers": {}
                            }
                        },
                        "audit": {
                            "enabled": True,
                            "retention_days": 90,
                            "log_file": "approval_audit_log.json"
                        },
                        "workflow": {
                            "timeout_hours": 24,
                            "escalation_hours": 12,
                            "auto_reject_after_timeout": True
                        }
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
        logger = logging.getLogger('EnhancedApprovalWorkflow')
        logger.setLevel(logging.INFO)

        # Create handlers
        file_handler = logging.FileHandler('enhanced_approval_workflow.log')
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

    def _load_persisted_queue(self):
        """Load persisted approval queue."""
        if self.persistence_file.exists():
            with open(self.persistence_file, 'r') as f:
                self.approval_queue = json.load(f)
            self.logger.info(f"Loaded {len(self.approval_queue)} persisted approvals")

    def _save_persisted_queue(self):
        """Save approval queue to persistence file."""
        with open(self.persistence_file, 'w') as f:
            json.dump(self.approval_queue, f, indent=2)

    def _start_notification_service(self):
        """Start the notification service."""
        if self.config["approval"]["notification"]["enabled"]:
            # Start notification thread
            self.notification_thread = Thread(target=self._notification_loop)
            self.notification_thread.daemon = True
            self.notification_thread.start()
            self.logger.info("Approval notification service started")

    def _notification_loop(self):
        """Main notification loop."""
        while True:
            try:
                # Check for pending approvals that need notification
                pending_notifications = [
                    req for req in self.approval_queue
                    if req["status"] == "pending" and not req.get("notified", False)
                ]

                for req in pending_notifications:
                    self._send_notification(req)
                    req["notified"] = True

                # Check for timeouts and escalations
                self._check_timeouts()
                self._check_escalations()

                # Save queue state
                self._save_persisted_queue()

                # Wait before next check
                time.sleep(300)  # Check every 5 minutes

            except Exception as e:
                self.logger.error(f"Error in notification loop: {e}")
                time.sleep(60)  # Wait before retrying

    def _send_notification(self, approval_request: Dict[str, Any]):
        """Send notifications for an approval request."""
        # Email notification
        if self.config["approval"]["notification"]["email"]["enabled"]:
            self._send_email_notification(approval_request)

        # Slack notification
        if self.config["approval"]["notification"]["slack"]["enabled"]:
            self._send_slack_notification(approval_request)

        # Webhook notification
        if self.config["approval"]["notification"]["webhook"]["enabled"]:
            self._send_webhook_notification(approval_request)

    def _send_email_notification(self, approval_request: Dict[str, Any]):
        """Send email notification for approval request."""
        try:
            # Load email template
            template_path = Path(self.config["approval"]["notification"]["email"]["template"])
            if not template_path.exists():
                self.logger.warning("Email template not found")
                return

            with open(template_path, 'r') as f:
                template = f.read()

            # Render template with approval data
            notification_content = template.format(
                request_id=approval_request["id"],
                type=approval_request["type"],
                description=approval_request.get("description", "Action required"),
                amount=approval_request.get("amount"),
                recipient=approval_request.get("recipient"),
                created_at=approval_request["created_at"],
                expires_at=approval_request["expires_at"],
                justification=approval_request.get("justification", "No justification provided")
            )

            # In a real implementation, you'd send the email here
            # For now, just log it
            self.logger.info(f"Email notification sent for request {approval_request['id']}")
            self.logger.debug(f"Email content: {notification_content}")

        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")

    def _send_slack_notification(self, approval_request: Dict[str, Any]):
        """Send Slack notification for approval request."""
        try:
            # Load Slack webhook URL
            webhook_url = self.config["approval"]["notification"]["slack"]["webhook_url"]
            if not webhook_url:
                self.logger.warning("Slack webhook URL not configured")
                return

            # Create Slack message
            slack_message = {
                "text": f"*:bell: New Approval Request:*",
                "attachments": [
                    {
                        "color": "warning",
                        "fields": [
                            {
                                "title": "Request ID",
                                "value": approval_request["id"],
                                "short": True
                            },
                            {
                                "title": "Type",
                                "value": approval_request["type"],
                                "short": True
                            },
                            {
                                "title": "Amount",
                                "value": f"${approval_request.get('amount', 0)}",
                                "short": True
                            },
                            {
                                "title": "Created",
                                "value": approval_request["created_at"],
                                "short": True
                            },
                            {
                                "title": "Expires",
                                "value": approval_request["expires_at"],
                                "short": True
                            }
                        ],
                        "actions": [
                            {
                                "name": "approve",
                                "text": "Approve",
                                "type": "button",
                                "value": approval_request["id"],
                                "style": "primary"
                            },
                            {
                                "name": "reject",
                                "text": "Reject",
                                "type": "button",
                                "value": approval_request["id"],
                                "style": "danger"
                            }
                        ]
                    }
                ]
            }

            # In a real implementation, you'd send the request here
            # For now, just log it
            self.logger.info(f"Slack notification sent for request {approval_request['id']}")
            self.logger.debug(f"Slack message: {slack_message}")

        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {e}")

    def _send_webhook_notification(self, approval_request: Dict[str, Any]):
        """Send webhook notification for approval request."""
        try:
            webhook_url = self.config["approval"]["notification"]["webhook"]["url"]
            if not webhook_url:
                return

            # Create webhook payload
            webhook_payload = {
                "event": "approval_request",
                "data": approval_request,
                "timestamp": datetime.now().isoformat()
            }

            # In a real implementation, you'd send the webhook request here
            # For now, just log it
            self.logger.info(f"Webhook notification sent for request {approval_request['id']}")
            self.logger.debug(f"Webhook payload: {webhook_payload}")

        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")

    def _check_timeouts(self):
        """Check for approval requests that have timed out."""
        now = datetime.now()
        for req in self.approval_queue:
            if req["status"] == "pending":
                expires_at = datetime.fromisoformat(req["expires_at"])
                if now > expires_at:
                    self._handle_timeout(req)

    def _check_escalations(self):
        """Check for approval requests that need escalation."""
        now = datetime.now()
        for req in self.approval_queue:
            if req["status"] == "pending" and not req.get("escalated", False):
                created_at = datetime.fromisoformat(req["created_at"])
                escalation_time = created_at + timedelta(hours=self.config["approval"]["workflow"]["escalation_hours"])
                if now > escalation_time:
                    self._handle_escalation(req)

    def _handle_timeout(self, approval_request: Dict[str, Any]):
        """Handle approval request timeout."""
        if self.config["approval"]["workflow"]["auto_reject_after_timeout"]:
            self.reject(approval_request["id"], "system", "Timeout - no response received")
        else:
            approval_request["status"] = "timeout"
            self._log_audit_event("approval_timeout", {
                "request_id": approval_request["id"],
                "request_data": approval_request
            })

    def _handle_escalation(self, approval_request: Dict[str, Any]):
        """Handle approval request escalation."""
        # Mark as escalated
        approval_request["escalated"] = True
        approval_request["escalation_time"] = datetime.now().isoformat()

        # Send escalation notification
        self._send_escalation_notification(approval_request)

        # Log audit event
        self._log_audit_event("approval_escalated", {
            "request_id": approval_request["id"],
            "request_data": approval_request
        })

    def _send_escalation_notification(self, approval_request: Dict[str, Any]):
        """Send escalation notification."""
        # In a real implementation, you'd send a special escalation notification
        # For now, just log it
        self.logger.info(f"Escalation notification sent for request {approval_request['id']}")

    def request_approval(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Request approval for an action."""
        try:
            # Generate request ID
            request_id = f"APPROVAL_{datetime.now().isoformat()}"

            # Create approval request
            approval_request = {
                "id": request_id,
                "type": request_data.get("type", "general"),
                "description": request_data.get("description", "Action requires approval"),
                "amount": request_data.get("amount"),
                "recipient": request_data.get("recipient"),
                "justification": request_data.get("justification", "No justification provided"),
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=self.config["approval"]["workflow"]["timeout_hours"])).isoformat(),
                "status": "pending",
                "metadata": request_data.get("metadata", {})
            }

            # Add to approval queue
            self.approval_queue.append(approval_request)
            self._save_persisted_queue()

            # Log audit event
            self._log_audit_event("approval_requested", {
                "request_id": request_id,
                "request_data": approval_request
            })

            return {
                "success": True,
                "request_id": request_id,
                "message": "Approval request created successfully"
            }

        except Exception as e:
            self.logger.error(f"Error requesting approval: {e}")
            return {"success": False, "error": str(e)}

    def approve(self, request_id: str, approver: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Approve an approval request."""
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
            request["approval_notes"] = notes

            # Execute the approved action
            result = self._execute_approved_action(request)

            # Log audit event
            self._log_audit_event("approval_executed", {
                "request_id": request_id,
                "approver": approver,
                "result": result,
                "request_data": request
            })

            # Save queue state
            self._save_persisted_queue()

            return {"success": True, "result": result}

        except Exception as e:
            self.logger.error(f"Error approving request {request_id}: {e}")
            return {"success": False, "error": str(e)}

    def reject(self, request_id: str, approver: str, reason: str) -> Dict[str, Any]:
        """Reject an approval request."""
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

            # Log audit event
            self._log_audit_event("approval_rejected", {
                "request_id": request_id,
                "approver": approver,
                "reason": reason,
                "request_data": request
            })

            # Save queue state
            self._save_persisted_queue()

            return {"success": True, "message": "Approval request rejected"}

        except Exception as e:
            self.logger.error(f"Error rejecting request {request_id}: {e}")
            return {"success": False, "error": str(e)}

    def _execute_approved_action(self, approval_request: Dict[str, Any]):
        """Execute the action for an approved request."""
        try:
            action_type = approval_request["type"]
            metadata = approval_request["metadata"]

            # In a real implementation, you'd execute the actual action here
            # For now, just return a success message
            result = {
                "status": "success",
                "message": f"Action '{action_type}' executed successfully",
                "metadata": metadata
            }

            return result

        except Exception as e:
            self.logger.error(f"Error executing approved action: {e}")
            return {"status": "error", "message": str(e)}

    def _log_audit_event(self, event_type: str, details: Dict[str, Any]):
        """Log an audit event."""
        if not self.config["approval"]["audit"]["enabled"]:
            return

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
            "source": "approval_workflow",
            "config_version": self.config.get("version", "1.0")
        }

        # Load existing audit log
        audit_log_file = Path(self.config["approval"]["audit"]["log_file"])
        audit_log = []
        if audit_log_file.exists():
            with open(audit_log_file, 'r') as f:
                audit_log = json.load(f)

        audit_log.append(audit_entry)

        # Apply retention policy
        retention_date = datetime.now() - timedelta(days=self.config["approval"]["audit"]["retention_days"])
        audit_log = [entry for entry in audit_log if datetime.fromisoformat(entry["timestamp"]) > retention_date]

        # Save audit log
        with open(audit_log_file, 'w') as f:
            json.dump(audit_log, f, indent=2)

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests."""
        return [req for req in self.approval_queue if req["status"] == "pending"]

    def get_approval_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get approval history."""
        return self.approval_queue[-limit:]

    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Enhanced Approval Workflow shutting down")

if __name__ == "__main__":
    # Example usage
    workflow = EnhancedApprovalWorkflow()

    # Request approval
    request_data = {
        "type": "email_send",
        "description": "Send promotional email to 1000 recipients",
        "amount": 50.0,
        "recipient": "marketing@example.com",
        "justification": "Monthly newsletter campaign",
        "metadata": {
            "email_count": 1000,
            "template": "newsletter_january_2026"
        }
    }

    result = workflow.request_approval(request_data)
    print(f"Approval request result: {result}")

    # Get pending approvals
    pending = workflow.get_pending_approvals()
    print(f"Pending approvals: {pending}")

    # Approve request (in real usage, this would be called by an approver)
    if pending:
        approval_result = workflow.approve(pending[0]["id"], "admin_user", "Approved - campaign is valid")
        print(f"Approval result: {approval_result}")

    # Get approval history
    history = workflow.get_approval_history()
    print(f"Approval history: {history}")

    # Cleanup
    workflow.cleanup()