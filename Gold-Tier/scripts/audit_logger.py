#!/usr/bin/env python3
"""
Comprehensive Audit Logging Module
Tracks all AI Employee actions for compliance and review
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import wraps
import hashlib
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Comprehensive audit logger for AI Employee actions.
    Logs all actions with timestamps, parameters, and outcomes.
    """
    
    def __init__(self, vault_path: str, retention_days: int = 90):
        """
        Initialize audit logger
        
        Args:
            vault_path: Path to Obsidian vault
            retention_days: Number of days to retain logs
        """
        self.vault_path = Path(vault_path)
        self.logs_path = self.vault_path / "Logs"
        self.retention_days = retention_days
        
        # Ensure logs directory exists
        self.logs_path.mkdir(parents=True, exist_ok=True)
        
        # Today's log file
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.log_file = self.logs_path / f"{self.today}.json"
        
        # Initialize today's log file if needed
        if not self.log_file.exists():
            self._init_log_file()
        
        # In-memory buffer for batch writing
        self.buffer = []
        self.buffer_size = 10  # Write after 10 entries
    
    def _init_log_file(self):
        """Initialize new log file with header"""
        header = {
            "date": self.today,
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "entries": []
        }
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(header, f, indent=2)
    
    def log_action(
        self,
        action_type: str,
        actor: str,
        target: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: str = "success",
        approval_status: str = "auto",
        approved_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> str:
        """
        Log an action
        
        Args:
            action_type: Type of action (email_send, payment, post_create, etc.)
            actor: Who/what performed the action (claude_code, gmail_watcher, etc.)
            target: Target of action (email address, payment recipient, etc.)
            parameters: Action parameters
            result: success, failure, skipped
            approval_status: auto, approved, rejected, pending
            approved_by: Human approver username if applicable
            metadata: Additional metadata
            error: Error message if failed
        
        Returns:
            Log entry ID
        """
        entry = {
            "id": self._generate_entry_id(),
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "parameters": parameters or {},
            "result": result,
            "approval_status": approval_status,
            "approved_by": approved_by,
            "metadata": metadata or {},
            "error": error
        }
        
        # Add to buffer
        self.buffer.append(entry)
        
        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            self.flush()
        
        logger.debug(f"Audit log entry created: {entry['id']}")
        
        return entry['id']
    
    def log_email_action(
        self,
        action: str,
        recipient: str,
        subject: str,
        actor: str = "claude_code",
        approval_status: str = "pending",
        approved_by: Optional[str] = None,
        error: Optional[str] = None
    ) -> str:
        """Log email-related action"""
        return self.log_action(
            action_type=f"email_{action}",
            actor=actor,
            target=recipient,
            parameters={"subject": subject},
            result="failure" if error else "success",
            approval_status=approval_status,
            approved_by=approved_by,
            error=error
        )
    
    def log_payment_action(
        self,
        action: str,
        recipient: str,
        amount: float,
        invoice_number: Optional[str] = None,
        actor: str = "claude_code",
        approval_status: str = "pending",
        approved_by: Optional[str] = None,
        error: Optional[str] = None
    ) -> str:
        """Log payment-related action"""
        return self.log_action(
            action_type=f"payment_{action}",
            actor=actor,
            target=recipient,
            parameters={
                "amount": amount,
                "invoice_number": invoice_number
            },
            result="failure" if error else "success",
            approval_status=approval_status,
            approved_by=approved_by,
            error=error
        )
    
    def log_social_media_action(
        self,
        platform: str,
        action: str,
        content: str,
        actor: str = "claude_code",
        approval_status: str = "pending",
        approved_by: Optional[str] = None,
        error: Optional[str] = None
    ) -> str:
        """Log social media action"""
        return self.log_action(
            action_type=f"social_{platform}_{action}",
            actor=actor,
            target=platform,
            parameters={"content_preview": content[:100] if content else ""},
            result="failure" if error else "success",
            approval_status=approval_status,
            approved_by=approved_by,
            error=error
        )
    
    def log_watcher_event(
        self,
        watcher_name: str,
        event_type: str,
        event_data: Dict[str, Any],
        action_file_created: Optional[str] = None
    ) -> str:
        """Log watcher-detected event"""
        return self.log_action(
            action_type=f"watcher_{event_type}",
            actor=watcher_name,
            target=action_file_created,
            parameters=event_data,
            result="success",
            approval_status="auto"
        )
    
    def log_approval_request(
        self,
        request_id: str,
        action_type: str,
        details: Dict[str, Any],
        requester: str = "claude_code"
    ) -> str:
        """Log approval request"""
        return self.log_action(
            action_type="approval_request",
            actor=requester,
            parameters={
                "request_id": request_id,
                "requested_action": action_type,
                "details": details
            },
            result="success",
            approval_status="pending"
        )
    
    def log_approval_decision(
        self,
        request_id: str,
        decision: str,
        decided_by: str,
        reason: Optional[str] = None
    ) -> str:
        """Log approval decision"""
        return self.log_action(
            action_type="approval_decision",
            actor=decided_by,
            target=request_id,
            parameters={"decision": decision, "reason": reason},
            result="success",
            approval_status=decision
        )
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
        actor: str = "system"
    ) -> str:
        """Log error"""
        return self.log_action(
            action_type=f"error_{error_type}",
            actor=actor,
            parameters=context,
            result="failure",
            error=error_message
        )
    
    def flush(self):
        """Write buffered entries to log file"""
        if not self.buffer:
            return
        
        try:
            # Read existing log
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # Add new entries
            log_data['entries'].extend(self.buffer)
            
            # Write back
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2)
            
            self.buffer = []
            logger.debug(f"Flushed {len(log_data['entries'])} entries to {self.log_file}")
            
        except Exception as e:
            logger.error(f"Error flushing audit log: {e}")
    
    def get_entries(
        self,
        date: Optional[str] = None,
        action_type: Optional[str] = None,
        actor: Optional[str] = None,
        result: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query log entries
        
        Args:
            date: Date filter (YYYY-MM-DD)
            action_type: Action type filter
            actor: Actor filter
            result: Result filter
            limit: Maximum entries to return
        
        Returns:
            List of matching entries
        """
        if date is None:
            date = self.today
        
        log_file = self.logs_path / f"{date}.json"
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            entries = log_data.get('entries', [])
            
            # Apply filters
            filtered = []
            for entry in entries:
                if action_type and entry.get('action_type') != action_type:
                    continue
                if actor and entry.get('actor') != actor:
                    continue
                if result and entry.get('result') != result:
                    continue
                filtered.append(entry)
            
            return filtered[:limit]
            
        except Exception as e:
            logger.error(f"Error reading log entries: {e}")
            return []
    
    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of daily activity"""
        if date is None:
            date = self.today
        
        entries = self.get_entries(date=date, limit=10000)
        
        summary = {
            "date": date,
            "total_actions": len(entries),
            "by_type": {},
            "by_actor": {},
            "by_result": {"success": 0, "failure": 0, "skipped": 0},
            "approval_stats": {"auto": 0, "approved": 0, "pending": 0, "rejected": 0},
            "errors": []
        }
        
        for entry in entries:
            # Count by type
            action_type = entry.get('action_type', 'unknown')
            summary['by_type'][action_type] = summary['by_type'].get(action_type, 0) + 1
            
            # Count by actor
            actor = entry.get('actor', 'unknown')
            summary['by_actor'][actor] = summary['by_actor'].get(actor, 0) + 1
            
            # Count by result
            result = entry.get('result', 'unknown')
            if result in summary['by_result']:
                summary['by_result'][result] += 1
            
            # Count approval status
            approval = entry.get('approval_status', 'unknown')
            if approval in summary['approval_stats']:
                summary['approval_stats'][approval] += 1
            
            # Collect errors
            if entry.get('error'):
                summary['errors'].append({
                    "id": entry.get('id'),
                    "action_type": action_type,
                    "error": entry.get('error'),
                    "timestamp": entry.get('timestamp')
                })
        
        return summary
    
    def cleanup_old_logs(self):
        """Remove logs older than retention period"""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        
        try:
            for log_file in self.logs_path.glob("*.json"):
                # Extract date from filename
                try:
                    file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
                    if file_date < cutoff:
                        log_file.unlink()
                        logger.info(f"Deleted old log: {log_file.name}")
                except:
                    pass  # Skip files with unexpected names
            
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
    
    def _generate_entry_id(self) -> str:
        """Generate unique entry ID"""
        timestamp = datetime.now().isoformat()
        random_bytes = os.urandom(8).hex()
        return hashlib.sha256(f"{timestamp}{random_bytes}".encode()).hexdigest()[:16]
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        if exc_type:
            self.log_error(
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                context={"traceback": traceback.format_exc()}
            )


def audit_log(vault_path: str):
    """
    Decorator for audit logging
    
    Args:
        vault_path: Path to vault
    """
    logger = AuditLogger(vault_path)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            action_type = func.__name__
            
            try:
                # Log start
                logger.log_action(
                    action_type=f"{action_type}_start",
                    actor="system",
                    parameters={"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
                )
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Log success
                logger.log_action(
                    action_type=f"{action_type}_complete",
                    actor="system",
                    result="success"
                )
                
                return result
                
            except Exception as e:
                # Log error
                logger.log_action(
                    action_type=f"{action_type}_error",
                    actor="system",
                    result="failure",
                    error=str(e)
                )
                raise
        
        return wrapper
    return decorator


# Global audit logger instance
_audit_logger = None


def get_audit_logger(vault_path: Optional[str] = None) -> AuditLogger:
    """Get or create global audit logger"""
    global _audit_logger
    
    if _audit_logger is None:
        if vault_path is None:
            vault_path = Path(__file__).parent / "Personal AI Employee Vault"
        _audit_logger = AuditLogger(str(vault_path))
    
    return _audit_logger


def main():
    """Test audit logger"""
    import sys
    
    vault_path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "Personal AI Employee Vault")
    
    logger = AuditLogger(vault_path)
    
    # Test logging
    logger.log_action(
        action_type="test_action",
        actor="audit_logger",
        target="test_target",
        parameters={"test": "value"},
        result="success"
    )
    
    logger.log_email_action(
        action="send",
        recipient="test@example.com",
        subject="Test Email",
        approval_status="approved",
        approved_by="admin"
    )
    
    logger.flush()
    
    # Get summary
    summary = logger.get_daily_summary()
    print(f"Today's summary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
