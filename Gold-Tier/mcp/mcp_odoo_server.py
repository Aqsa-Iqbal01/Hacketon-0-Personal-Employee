#!/usr/bin/env python3
"""
Odoo Accounting MCP Server
Integrates with Odoo Community Edition (v19+) via JSON-RPC API
Provides accounting capabilities for the AI Employee system
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from datetime import datetime
from pathlib import Path

# Initialize MCP server
mcp = FastMCP("odoo-accounting")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Odoo Configuration (from environment variables)
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")
ODOO_COMPANY_ID = int(os.getenv("ODOO_COMPANY_ID", "1"))


class OdooClient:
    """Client for Odoo JSON-RPC API"""
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.session = requests.Session()
        
    def authenticate(self) -> bool:
        """Authenticate with Odoo and get session UID"""
        try:
            # First, get session cookie
            auth_url = f"{self.url}/web/session/authenticate"
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": self.db,
                    "login": self.username,
                    "password": self.password,
                    "context": {}
                },
                "id": 1
            }
            
            response = self.session.post(auth_url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('result'):
                self.uid = result['result'].get('uid')
                logger.info(f"Authenticated with Odoo. UID: {self.uid}")
                return self.uid is not None
            else:
                logger.error(f"Authentication failed: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def execute_kw(self, model: str, method: str, args: List = None, kwargs: Dict = None) -> Any:
        """Execute Odoo model method"""
        if self.uid is None:
            if not self.authenticate():
                raise Exception("Not authenticated with Odoo")
        
        url = f"{self.url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args or [],
                "kwargs": kwargs or {}
            },
            "id": 1
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                raise Exception(f"Odoo error: {result['error']}")
            
            return result.get('result', {})
            
        except Exception as e:
            logger.error(f"Execute error: {e}")
            raise


# Global Odoo client
odoo_client = OdooClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)


@mcp.tool()
def odoo_connect() -> Dict[str, Any]:
    """Test connection to Odoo ERP"""
    try:
        if odoo_client.authenticate():
            return {
                "status": "connected",
                "url": ODOO_URL,
                "database": ODOO_DB,
                "company_id": ODOO_COMPANY_ID,
                "message": "Successfully connected to Odoo ERP"
            }
        else:
            return {
                "status": "failed",
                "message": "Failed to authenticate with Odoo"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def odoo_create_invoice(
    partner_name: str,
    partner_email: str,
    amount: float,
    description: str,
    invoice_type: str = "out_invoice",
    due_days: int = 30
) -> Dict[str, Any]:
    """
    Create a new invoice in Odoo
    
    Args:
        partner_name: Customer/Client name
        partner_email: Customer email
        amount: Invoice amount (without tax)
        description: Invoice description/line item
        invoice_type: Type (out_invoice for customer, in_invoice for vendor)
        due_days: Payment due days
    
    Returns:
        Invoice creation result with ID and URL
    """
    try:
        # Find or create partner
        partner_id = odoo_client.execute_kw(
            'res.partner',
            'search',
            [[['email', '=', partner_email]]]
        )
        
        if not partner_id:
            # Create new partner
            partner_id = odoo_client.execute_kw(
                'res.partner',
                'create',
                [[{
                    'name': partner_name,
                    'email': partner_email,
                    'customer_rank': 1
                }]]
            )
            logger.info(f"Created new partner: {partner_name} (ID: {partner_id})")
        else:
            partner_id = partner_id[0]
        
        # Create invoice
        invoice_data = {
            'partner_id': partner_id,
            'invoice_origin': f"AI Employee - {datetime.now().strftime('%Y-%m-%d')}",
            'move_type': invoice_type,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'quantity': 1,
                'price_unit': amount,
            })]
        }
        
        invoice_id = odoo_client.execute_kw(
            'account.move',
            'create',
            [invoice_data]
        )
        
        # Get invoice number
        invoice = odoo_client.execute_kw(
            'account.move',
            'read',
            [invoice_id],
            {'fields': ['name', 'state', 'invoice_date', 'invoice_date_due']}
        )[0]
        
        # Update due date
        from datetime import timedelta
        due_date = datetime.now() + timedelta(days=due_days)
        odoo_client.execute_kw(
            'account.move',
            'write',
            [invoice_id, {'invoice_date_due': due_date.strftime('%Y-%m-%d')}]
        )
        
        return {
            "status": "success",
            "invoice_id": invoice_id,
            "invoice_number": invoice.get('name', 'Draft'),
            "partner": partner_name,
            "amount": amount,
            "state": invoice.get('state', 'draft'),
            "due_date": due_date.strftime('%Y-%m-%d'),
            "url": f"{ODOO_URL}/web#id={invoice_id}&model=account.move&view_type=form",
            "message": f"Invoice {invoice.get('name', 'Draft')} created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def odoo_get_invoices(
    partner_email: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieve invoices from Odoo
    
    Args:
        partner_email: Filter by partner email (optional)
        state: Filter by state (draft, posted, cancel) (optional)
        limit: Maximum number of invoices to return
    
    Returns:
        List of invoices with details
    """
    try:
        domain = []
        
        if partner_email:
            partner_ids = odoo_client.execute_kw(
                'res.partner',
                'search',
                [[['email', '=', partner_email]]]
            )
            if partner_ids:
                domain.append(['partner_id', 'in', partner_ids])
        
        if state:
            domain.append(['state', '=', state])
        
        invoice_ids = odoo_client.execute_kw(
            'account.move',
            'search',
            [domain],
            {'limit': limit, 'order': 'invoice_date desc'}
        )
        
        if not invoice_ids:
            return {
                "status": "success",
                "count": 0,
                "invoices": [],
                "message": "No invoices found"
            }
        
        # Read invoice details
        invoices = odoo_client.execute_kw(
            'account.move',
            'read',
            [invoice_ids],
            {
                'fields': [
                    'name', 'partner_id', 'amount_total', 'amount_untaxed',
                    'state', 'invoice_date', 'invoice_date_due', 'payment_state'
                ]
            }
        )
        
        # Get partner names
        partner_ids = list(set([inv['partner_id'][0] for inv in invoices if inv.get('partner_id')]))
        partners = odoo_client.execute_kw(
            'res.partner',
            'read',
            [partner_ids],
            {'fields': ['name', 'email']}
        )
        partner_map = {p['id']: p for p in partners}
        
        formatted_invoices = []
        for inv in invoices:
            partner_info = partner_map.get(inv['partner_id'][0], {})
            formatted_invoices.append({
                "invoice_id": inv['id'],
                "invoice_number": inv.get('name', 'Draft'),
                "partner": partner_info.get('name', 'Unknown'),
                "partner_email": partner_info.get('email', ''),
                "amount_total": inv.get('amount_total', 0),
                "amount_untaxed": inv.get('amount_untaxed', 0),
                "state": inv.get('state', 'draft'),
                "payment_state": inv.get('payment_state', 'not_paid'),
                "invoice_date": inv.get('invoice_date', ''),
                "due_date": inv.get('invoice_date_due', '')
            })
        
        return {
            "status": "success",
            "count": len(formatted_invoices),
            "invoices": formatted_invoices
        }
        
    except Exception as e:
        logger.error(f"Error getting invoices: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def odoo_record_payment(
    invoice_id: int,
    amount: float,
    payment_date: Optional[str] = None,
    payment_reference: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record a payment for an invoice
    
    Args:
        invoice_id: Odoo invoice ID
        amount: Payment amount
        payment_date: Payment date (YYYY-MM-DD format)
        payment_reference: Payment reference/note
    
    Returns:
        Payment registration result
    """
    try:
        if not payment_date:
            payment_date = datetime.now().strftime('%Y-%m-%d')
        
        if not payment_reference:
            payment_reference = f"Payment recorded by AI Employee"
        
        # Register payment
        payment_wizard = odoo_client.execute_kw(
            'account.move.reversal',
            'create',
            [[{
                'invoice_ids': [invoice_id],
                'amount': amount,
                'date': payment_date,
                'reason': payment_reference,
                'refund_method': 'cancel',
            }]]
        )
        
        # Alternative: Direct payment registration
        # Get invoice journal
        invoice = odoo_client.execute_kw(
            'account.move',
            'read',
            [invoice_id],
            {'fields': ['journal_id', 'partner_id']}
        )[0]
        
        # Create payment record
        payment_data = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': invoice['partner_id'][0],
            'amount': amount,
            'date': payment_date,
            'payment_reference': payment_reference,
            'journal_id': invoice['journal_id'][0],
        }
        
        payment_id = odoo_client.execute_kw(
            'account.payment',
            'create',
            [payment_data]
        )
        
        # Confirm payment
        odoo_client.execute_kw(
            'account.payment',
            'action_post',
            [payment_id]
        )
        
        # Link payment to invoice
        odoo_client.execute_kw(
            'account.move',
            'action_register_payment',
            [[invoice_id]],
            {
                'amount': amount,
                'payment_date': payment_date,
                'payment_reference': payment_reference
            }
        )
        
        return {
            "status": "success",
            "payment_id": payment_id,
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_date": payment_date,
            "message": f"Payment of {amount} recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error recording payment: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def odoo_get_account_summary() -> Dict[str, Any]:
    """
    Get overall accounting summary from Odoo
    
    Returns:
        Summary of receivables, payables, and key metrics
    """
    try:
        # Get total receivables (money owed to you)
        receivables = odoo_client.execute_kw(
            'account.move',
            'search_count',
            [[['move_type', '=', 'out_invoice'], ['state', '=', 'posted'], ['payment_state', '!=', 'paid']]]
        )
        
        # Get total payables (money you owe)
        payables = odoo_client.execute_kw(
            'account.move',
            'search_count',
            [[['move_type', '=', 'in_invoice'], ['state', '=', 'posted'], ['payment_state', '!=', 'paid']]]
        )
        
        # Get invoices to collect
        to_collect = odoo_client.execute_kw(
            'account.move',
            'search',
            [[['move_type', '=', 'out_invoice'], ['state', '=', 'posted'], ['payment_state', '!=', 'paid']]]
        )
        
        # Calculate total amount to collect
        if to_collect:
            invoices_data = odoo_client.execute_kw(
                'account.move',
                'read',
                [to_collect],
                {'fields': ['amount_total']}
            )
            total_receivable = sum(inv.get('amount_total', 0) for inv in invoices_data)
        else:
            total_receivable = 0
        
        # Get recent revenue (this month)
        from datetime import timedelta
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        recent_invoices = odoo_client.execute_kw(
            'account.move',
            'search',
            [[['move_type', '=', 'out_invoice'], ['state', '=', 'posted'], ['invoice_date', '>=', month_ago]]]
        )
        
        if recent_invoices:
            revenue_data = odoo_client.execute_kw(
                'account.move',
                'read',
                [recent_invoices],
                {'fields': ['amount_total']}
            )
            monthly_revenue = sum(inv.get('amount_total', 0) for inv in revenue_data)
        else:
            monthly_revenue = 0
        
        return {
            "status": "success",
            "summary": {
                "total_receivables": total_receivable,
                "unpaid_customer_invoices": receivables,
                "unpaid_vendor_bills": payables,
                "monthly_revenue": monthly_revenue,
                "currency": "PKR"  # Default, can be configured
            },
            "message": f"Accounting summary retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting account summary: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def odoo_create_journal_entry(
    name: str,
    lines: List[Dict[str, Any]],
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a manual journal entry
    
    Args:
        name: Entry reference/name
        lines: List of journal items with account, debit, credit, partner_id (optional)
        date: Entry date (YYYY-MM-DD format)
    
    Returns:
        Journal entry creation result
    
    Example lines:
    [
        {"account_code": "110100", "debit": 1000, "credit": 0, "partner_id": 1},
        {"account_code": "410100", "debit": 0, "credit": 1000}
    ]
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Find account IDs from codes
        journal_lines = []
        for line in lines:
            account_id = odoo_client.execute_kw(
                'account.account',
                'search',
                [[['code', '=', line['account_code']]]]
            )
            
            if not account_id:
                return {
                    "status": "error",
                    "message": f"Account {line['account_code']} not found"
                }
            
            journal_line = {
                'account_id': account_id[0],
                'debit': line.get('debit', 0),
                'credit': line.get('credit', 0),
                'name': name
            }
            
            if line.get('partner_id'):
                journal_line['partner_id'] = line['partner_id']
            
            journal_lines.append((0, 0, journal_line))
        
        # Create journal entry
        entry_data = {
            'name': name,
            'date': date,
            'journal_id': 1,  # Default journal, can be configured
            'line_ids': journal_lines,
            'ref': f"AI Employee Entry - {datetime.now().strftime('%Y-%m-%d')}"
        }
        
        entry_id = odoo_client.execute_kw(
            'account.move',
            'create',
            [entry_data]
        )
        
        # Post the entry
        odoo_client.execute_kw(
            'account.move',
            'action_post',
            [entry_id]
        )
        
        return {
            "status": "success",
            "entry_id": entry_id,
            "name": name,
            "date": date,
            "message": f"Journal entry '{name}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating journal entry: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def odoo_get_partner_ledger(partner_email: str) -> Dict[str, Any]:
    """
    Get complete ledger for a specific partner
    
    Args:
        partner_email: Partner's email address
    
    Returns:
        Complete transaction history with the partner
    """
    try:
        # Find partner
        partner_ids = odoo_client.execute_kw(
            'res.partner',
            'search',
            [[['email', '=', partner_email]]]
        )
        
        if not partner_ids:
            return {
                "status": "error",
                "message": f"Partner with email {partner_email} not found"
            }
        
        partner_id = partner_ids[0]
        
        # Get all invoices for this partner
        invoice_ids = odoo_client.execute_kw(
            'account.move',
            'search',
            [[['partner_id', '=', partner_id]]],
            {'order': 'invoice_date desc'}
        )
        
        if not invoice_ids:
            return {
                "status": "success",
                "partner_email": partner_email,
                "count": 0,
                "transactions": [],
                "message": "No transactions found"
            }
        
        # Read invoice details
        invoices = odoo_client.execute_kw(
            'account.move',
            'read',
            [invoice_ids],
            {
                'fields': [
                    'name', 'move_type', 'amount_total', 'amount_residual',
                    'state', 'invoice_date', 'payment_state'
                ]
            }
        )
        
        transactions = []
        total_debit = 0
        total_credit = 0
        
        for inv in invoices:
            if inv['move_type'] in ['out_invoice', 'out_refund']:
                total_debit += inv.get('amount_total', 0)
            else:
                total_credit += inv.get('amount_total', 0)
            
            transactions.append({
                "date": inv.get('invoice_date', ''),
                "reference": inv.get('name', ''),
                "type": inv.get('move_type', ''),
                "amount": inv.get('amount_total', 0),
                "paid": inv.get('amount_residual', 0) == 0,
                "state": inv.get('state', 'draft')
            })
        
        return {
            "status": "success",
            "partner_email": partner_email,
            "count": len(transactions),
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance": total_debit - total_credit,
            "transactions": transactions
        }
        
    except Exception as e:
        logger.error(f"Error getting partner ledger: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
