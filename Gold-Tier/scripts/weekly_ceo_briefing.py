#!/usr/bin/env python3
"""
Weekly Business Audit and CEO Briefing Generator
Generates comprehensive weekly business reports with accounting audit
Integrates with Odoo, social media platforms, and task management
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CEOBriefingGenerator:
    """Generates weekly CEO briefings with business audit"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.logs_path = self.vault_path / "Logs"
        self.done_path = self.vault_path / "Done"
        self.plans_path = self.vault_path / "Plans"
        self.dashboard_path = self.vault_path / "Dashboard.md"
        self.briefings_path = self.vault_path / "Briefings"
        
        # Ensure briefings folder exists
        self.briefings_path.mkdir(exist_ok=True)
        
        # Odoo configuration
        self.odo_url = os.getenv("ODOO_URL", "http://localhost:8069")
        self.odo_db = os.getenv("ODOO_DB", "odoo")
        self.odo_username = os.getenv("ODOO_USERNAME", "admin")
        self.odo_password = os.getenv("ODOO_PASSWORD", "admin")
        
        # Social media configuration
        self.meta_access_token = os.getenv("META_ACCESS_TOKEN", "")
        self.meta_instagram_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID", "")
        self.meta_facebook_id = os.getenv("META_FACEBOOK_PAGE_ID", "")
        self.twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
    
    def generate_weekly_briefing(self, week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate comprehensive weekly CEO briefing
        
        Args:
            week_start: Start of week (defaults to last Monday)
        
        Returns:
            Briefing data and file path
        """
        if not week_start:
            # Get last Monday
            today = datetime.now()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday, weeks=1)
        
        week_end = week_start + timedelta(days=6)  # Sunday
        
        logger.info(f"Generating weekly briefing for {week_start.date()} to {week_end.date()}")
        
        # Collect all data
        accounting_data = self._get_accounting_summary(week_start, week_end)
        tasks_data = self._get_tasks_summary(week_start, week_end)
        social_media_data = self._get_social_media_summary(week_start, week_end)
        goals_data = self._get_goals_progress()
        
        # Generate briefing content
        briefing_content = self._create_briefing_content(
            week_start=week_start,
            week_end=week_end,
            accounting=accounting_data,
            tasks=tasks_data,
            social=social_media_data,
            goals=goals_data
        )
        
        # Save briefing
        briefing_date = week_end.strftime("%Y-%m-%d")
        briefing_filename = f"{briefing_date}_Weekly_CEO_Briefing.md"
        briefing_path = self.briefings_path / briefing_filename
        
        with open(briefing_path, 'w', encoding='utf-8') as f:
            f.write(briefing_content)
        
        # Update dashboard
        self._update_dashboard_with_briefing(briefing_path, accounting_data)
        
        return {
            "status": "success",
            "briefing_path": str(briefing_path),
            "period": f"{week_start.date()} to {week_end.date()}",
            "accounting_summary": accounting_data,
            "tasks_summary": tasks_data,
            "social_summary": social_media_data
        }
    
    def _get_accounting_summary(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Get accounting data from Odoo"""
        try:
            # Call Odoo MCP for accounting summary
            from mcp.mcp_odoo_server import odoo_get_account_summary, odoo_get_invoices
            
            # Get overall summary
            summary_result = odoo_get_account_summary()
            
            if summary_result.get('status') != 'success':
                return {
                    "status": "error",
                    "message": "Could not retrieve accounting data",
                    "revenue_this_week": 0,
                    "pending_invoices": 0
                }
            
            summary = summary_result.get('summary', {})
            
            # Get invoices from this week
            invoices_result = odoo_get_invoices(limit=50)
            weekly_revenue = 0
            invoices_this_week = []
            
            if invoices_result.get('status') == 'success':
                for invoice in invoices_result.get('invoices', []):
                    invoice_date = invoice.get('invoice_date', '')
                    if invoice_date:
                        try:
                            inv_date = datetime.strptime(invoice_date, '%Y-%m-%d')
                            if week_start <= inv_date <= week_end:
                                weekly_revenue += invoice.get('amount_total', 0)
                                invoices_this_week.append({
                                    "number": invoice.get('invoice_number', ''),
                                    "partner": invoice.get('partner', ''),
                                    "amount": invoice.get('amount_total', 0),
                                    "state": invoice.get('state', '')
                                })
                        except:
                            pass
            
            return {
                "status": "success",
                "revenue_this_week": weekly_revenue,
                "total_receivables": summary.get('total_receivables', 0),
                "monthly_revenue": summary.get('monthly_revenue', 0),
                "unpaid_invoices": summary.get('unpaid_customer_invoices', 0),
                "invoices_this_week": invoices_this_week,
                "currency": summary.get('currency', 'PKR')
            }
            
        except Exception as e:
            logger.error(f"Error getting accounting data: {e}")
            return {
                "status": "error",
                "message": str(e),
                "revenue_this_week": 0,
                "pending_invoices": 0
            }
    
    def _get_tasks_summary(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Analyze completed tasks from the week"""
        try:
            completed_tasks = []
            pending_tasks = []
            bottlenecks = []
            
            # Scan Done folder for completed tasks
            if self.done_path.exists():
                for file in self.done_path.glob("*.md"):
                    try:
                        content = file.read_text(encoding='utf-8')
                        
                        # Extract task date from content or filename
                        task_date = self._extract_date_from_file(file)
                        if task_date and week_start <= task_date <= week_end:
                            completed_tasks.append({
                                "name": file.stem,
                                "date": task_date.strftime('%Y-%m-%d'),
                                "type": self._extract_task_type(content)
                            })
                    except:
                        pass
            
            # Scan Needs_Action for pending tasks
            needs_action_path = self.vault_path / "Needs_Action"
            if needs_action_path.exists():
                pending_count = len(list(needs_action_path.glob("*.md")))
                pending_tasks.append({
                    "location": "Needs_Action",
                    "count": pending_count
                })
            
            # Scan Pending_Approval for bottlenecks
            pending_approval_path = self.vault_path / "Pending_Approval"
            if pending_approval_path.exists():
                approval_count = len(list(pending_approval_path.glob("*.md")))
                if approval_count > 0:
                    bottlenecks.append({
                        "type": "Pending Approvals",
                        "count": approval_count,
                        "severity": "high" if approval_count > 5 else "medium"
                    })
            
            # Calculate completion rate
            total_completed = len(completed_tasks)
            total_pending = sum(t['count'] for t in pending_tasks)
            completion_rate = 0
            if total_completed + total_pending > 0:
                completion_rate = round((total_completed / (total_completed + total_pending)) * 100, 1)
            
            return {
                "status": "success",
                "completed_tasks": completed_tasks,
                "completed_count": total_completed,
                "pending_count": total_pending,
                "completion_rate": completion_rate,
                "bottlenecks": bottlenecks
            }
            
        except Exception as e:
            logger.error(f"Error getting tasks summary: {e}")
            return {
                "status": "error",
                "message": str(e),
                "completed_count": 0,
                "pending_count": 0
            }
    
    def _get_social_media_summary(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Get social media performance summary"""
        try:
            social_data = {
                "instagram": {},
                "facebook": {},
                "twitter": {},
                "linkedin": {}
            }
            
            # Instagram insights
            try:
                from mcp.mcp_meta_social import meta_get_instagram_insights
                ig_result = meta_get_instagram_insights()
                if ig_result.get('status') == 'success':
                    social_data["instagram"] = {
                        "followers": ig_result.get('account_metrics', {}).get('follower_count', 0),
                        "reach": ig_result.get('account_metrics', {}).get('reach', 0),
                        "impressions": ig_result.get('account_metrics', {}).get('impressions', 0),
                        "engagement": ig_result.get('account_metrics', {}).get('engagement', 0),
                        "posts_this_week": len(ig_result.get('recent_posts', []))
                    }
            except Exception as e:
                logger.error(f"Error getting Instagram data: {e}")
            
            # Facebook insights
            try:
                from mcp.mcp_meta_social import meta_get_facebook_insights
                fb_result = meta_get_facebook_insights()
                if fb_result.get('status') == 'success':
                    social_data["facebook"] = {
                        "followers": fb_result.get('page_metrics', {}).get('page_followers_total', 0),
                        "reach": fb_result.get('page_metrics', {}).get('page_impressions_unique', 0),
                        "engagement": fb_result.get('page_metrics', {}).get('page_engaged_users', 0),
                        "posts_this_week": len(fb_result.get('recent_posts', []))
                    }
            except Exception as e:
                logger.error(f"Error getting Facebook data: {e}")
            
            # Twitter analytics
            try:
                from mcp.mcp_twitter_x import twitter_get_analytics
                twitter_result = twitter_get_analytics(days=7)
                if twitter_result.get('status') == 'success':
                    summary = twitter_result.get('summary', {})
                    social_data["twitter"] = {
                        "impressions": summary.get('total_impressions', 0),
                        "likes": summary.get('total_likes', 0),
                        "retweets": summary.get('total_retweets', 0),
                        "engagement_rate": summary.get('average_engagement_rate', 0),
                        "tweets_this_week": twitter_result.get('tweet_count', 0)
                    }
            except Exception as e:
                logger.error(f"Error getting Twitter data: {e}")
            
            # LinkedIn (from local files)
            linkedin_file = self.vault_path / "processed_linkedin_requests.txt"
            if linkedin_file.exists():
                try:
                    content = linkedin_file.read_text()
                    lines = [l for l in content.split('\n') if l.strip()]
                    social_data["linkedin"] = {
                        "interactions_this_week": len(lines),
                        "status": "active"
                    }
                except:
                    pass
            
            return {
                "status": "success",
                "platforms": social_data,
                "total_reach": sum([
                    social_data.get('instagram', {}).get('reach', 0),
                    social_data.get('facebook', {}).get('reach', 0),
                    social_data.get('twitter', {}).get('impressions', 0)
                ]),
                "total_posts": sum([
                    social_data.get('instagram', {}).get('posts_this_week', 0),
                    social_data.get('facebook', {}).get('posts_this_week', 0),
                    social_data.get('twitter', {}).get('tweets_this_week', 0),
                    social_data.get('linkedin', {}).get('interactions_this_week', 0)
                ])
            }
            
        except Exception as e:
            logger.error(f"Error getting social media summary: {e}")
            return {
                "status": "error",
                "message": str(e),
                "platforms": {},
                "total_reach": 0
            }
    
    def _get_goals_progress(self) -> Dict[str, Any]:
        """Get progress on business goals"""
        try:
            goals_file = self.vault_path / "Business_Goals.md"
            if not goals_file.exists():
                return {
                    "status": "no_goals",
                    "message": "No business goals file found"
                }
            
            content = goals_file.read_text(encoding='utf-8')
            
            # Parse goals (simple parsing)
            goals = []
            current_goal = None
            
            for line in content.split('\n'):
                if line.startswith('###') or line.startswith('##'):
                    if current_goal:
                        goals.append(current_goal)
                    current_goal = {
                        "name": line.replace('#', '').strip(),
                        "target": None,
                        "current": None,
                        "status": "unknown"
                    }
                elif current_goal and 'Monthly goal:' in line.lower():
                    try:
                        target = float(line.split('$')[1].replace(',', ''))
                        current_goal['target'] = target
                    except:
                        pass
                elif current_goal and 'Current MTD:' in line:
                    try:
                        current = float(line.split('$')[1].replace(',', ''))
                        current_goal['current'] = current
                        if current_goal['target']:
                            progress = (current / current_goal['target']) * 100
                            current_goal['status'] = f"{progress:.1f}% on track" if progress >= 45 else f"{progress:.1f}% behind"
                    except:
                        pass
            
            if current_goal:
                goals.append(current_goal)
            
            return {
                "status": "success",
                "goals": goals,
                "count": len(goals)
            }
            
        except Exception as e:
            logger.error(f"Error getting goals progress: {e}")
            return {
                "status": "error",
                "message": str(e),
                "goals": []
            }
    
    def _create_briefing_content(
        self,
        week_start: datetime,
        week_end: datetime,
        accounting: Dict[str, Any],
        tasks: Dict[str, Any],
        social: Dict[str, Any],
        goals: Dict[str, Any]
    ) -> str:
        """Create Markdown briefing content"""
        
        period_str = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
        
        # Determine overall tone
        revenue = accounting.get('revenue_this_week', 0)
        completion_rate = tasks.get('completion_rate', 0)
        
        if revenue > 100000 and completion_rate > 70:
            executive_summary = "Excellent week with strong revenue and high task completion. Business is thriving."
        elif revenue > 50000 and completion_rate > 50:
            executive_summary = "Solid week with good revenue generation and steady progress on tasks."
        elif revenue > 0 or completion_rate > 30:
            executive_summary = "Moderate week with room for improvement in both revenue and task completion."
        else:
            executive_summary = "Challenging week. Review bottlenecks and consider strategic adjustments."
        
        content = f"""---
generated: {datetime.now().isoformat()}
period: {period_str}
type: weekly_ceo_briefing
---

# Weekly CEO Briefing

**Period:** {period_str}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Status:** {executive_summary.split('.')[0]}

---

## Executive Summary

{executive_summary}

---

## 📊 Revenue & Accounting

### Key Metrics
| Metric | Value | Status |
|--------|-------|--------|
| Revenue This Week | **PKR {revenue:,.0f}** | {'✅ On Track' if revenue > 50000 else '⚠️ Needs Attention'} |
| Total Receivables | PKR {accounting.get('total_receivables', 0):,.0f} | {accounting.get('unpaid_invoices', 0)} unpaid invoices |
| Monthly Revenue (MTD) | PKR {accounting.get('monthly_revenue', 0):,.0f} | - |

### Invoices This Week
"""
        
        invoices = accounting.get('invoices_this_week', [])
        if invoices:
            content += "\n| Invoice | Client | Amount | Status |\n|---------|--------|--------|--------|\n"
            for inv in invoices[:10]:  # Show top 10
                content += f"| {inv.get('number', 'N/A')} | {inv.get('partner', 'Unknown')} | PKR {inv.get('amount', 0):,.0f} | {inv.get('state', 'draft')} |\n"
        else:
            content += "\n*No invoices generated this week*\n"
        
        content += f"""
---

## ✅ Tasks & Productivity

### Completion Metrics
| Metric | Value |
|--------|-------|
| Tasks Completed | {tasks.get('completed_count', 0)} |
| Tasks Pending | {tasks.get('pending_count', 0)} |
| Completion Rate | **{tasks.get('completion_rate', 0)}%** |

### Completed Tasks This Week
"""
        
        completed = tasks.get('completed_tasks', [])
        if completed:
            for task in completed[:15]:  # Show top 15
                content += f"- [{task.get('date', '')}] **{task.get('name', 'Unknown')}** ({task.get('type', 'general')})\n"
        else:
            content += "*No tasks completed this week*\n"
        
        bottlenecks = tasks.get('bottlenecks', [])
        if bottlenecks:
            content += "\n### ⚠️ Bottlenecks Identified\n"
            for bottleneck in bottlenecks:
                severity_icon = "🔴" if bottleneck.get('severity') == 'high' else "🟡"
                content += f"- {severity_icon} **{bottleneck.get('type', 'Unknown')}**: {bottleneck.get('count', 0)} items pending\n"
        
        content += f"""
---

## 📱 Social Media Performance

### Overall Reach
- **Total Reach:** {social.get('total_reach', 0):,} impressions
- **Total Posts:** {social.get('total_posts', 0)} across all platforms

### Platform Breakdown
"""
        
        platforms = social.get('platforms', {})
        
        if platforms.get('instagram'):
            ig = platforms['instagram']
            content += f"""
#### Instagram
- Followers: {ig.get('followers', 0):,}
- Reach: {ig.get('reach', 0):,}
- Engagement: {ig.get('engagement', 0):,}
- Posts This Week: {ig.get('posts_this_week', 0)}
"""
        
        if platforms.get('facebook'):
            fb = platforms['facebook']
            content += f"""
#### Facebook
- Followers: {fb.get('followers', 0):,}
- Reach: {fb.get('reach', 0):,}
- Engagement: {fb.get('engagement', 0):,}
- Posts This Week: {fb.get('posts_this_week', 0)}
"""
        
        if platforms.get('twitter'):
            tw = platforms['twitter']
            content += f"""
#### Twitter (X)
- Impressions: {tw.get('impressions', 0):,}
- Likes: {tw.get('likes', 0):,}
- Retweets: {tw.get('retweets', 0):,}
- Engagement Rate: {tw.get('engagement_rate', 0):.2f}%
- Tweets This Week: {tw.get('tweets_this_week', 0)}
"""
        
        content += f"""
---

## 🎯 Business Goals Progress

"""
        
        goals_list = goals.get('goals', [])
        if goals_list:
            for goal in goals_list:
                target = goal.get('target', 0)
                current = goal.get('current', 0)
                status = goal.get('status', 'unknown')
                content += f"### {goal.get('name', 'Goal')}\n"
                content += f"- Target: PKR {target:,.0f}\n"
                content += f"- Current: PKR {current:,.0f}\n"
                content += f"- Status: **{status}**\n\n"
        else:
            content += "*No business goals configured. Consider setting up Business_Goals.md*\n"
        
        content += f"""
---

## 🤖 Proactive Suggestions

"""
        
        # Generate proactive suggestions based on data
        suggestions = []
        
        if accounting.get('unpaid_invoices', 0) > 5:
            suggestions.append(f"🔴 **Follow up on {accounting.get('unpaid_invoices', 0)} unpaid invoices** - Consider sending payment reminders")
        
        if tasks.get('pending_count', 0) > 10:
            suggestions.append(f"🟡 **{tasks.get('pending_count', 0)} tasks pending** - Review and prioritize or delegate")
        
        if bottlenecks and any(b.get('severity') == 'high' for b in bottlenecks):
            suggestions.append("🔴 **High-severity bottlenecks detected** - Immediate attention required on pending approvals")
        
        if social.get('total_posts', 0) < 3:
            suggestions.append("🟡 **Low social media activity** - Consider scheduling more posts for next week")
        
        if revenue < 50000:
            suggestions.append("🟡 **Revenue below target** - Review sales pipeline and consider outreach campaigns")
        
        if not suggestions:
            suggestions.append("✅ All systems running smoothly. Continue current strategies.")
        
        for suggestion in suggestions:
            content += f"- {suggestion}\n"
        
        content += f"""
---

## 📅 Upcoming Deadlines & Events

*Check Plans folder for detailed project timelines*

---

## 📝 Notes

This briefing was automatically generated by your AI Employee.
For questions or clarifications, review the Logs folder or ask in the next interactive session.

---
*Generated by AI Employee v1.0 - Gold Tier*
"""
        
        return content
    
    def _update_dashboard_with_briefing(self, briefing_path: Path, accounting_data: Dict[str, Any]):
        """Update Dashboard.md with latest briefing summary"""
        try:
            if not self.dashboard_path.exists():
                return
            
            content = self.dashboard_path.read_text(encoding='utf-8')
            
            # Update revenue section
            revenue = accounting_data.get('revenue_this_week', 0)
            receivables = accounting_data.get('total_receivables', 0)
            
            # Find and replace revenue section
            if "## Financial Summary" in content:
                # Update existing section
                lines = content.split('\n')
                new_lines = []
                in_financial_section = False
                skip_until_next_header = False
                
                for line in lines:
                    if line.strip() == "## Financial Summary":
                        in_financial_section = True
                        new_lines.append(line)
                        new_lines.append(f"- **Revenue This Week:** PKR {revenue:,.0f}")
                        new_lines.append(f"- **Total Receivables:** PKR {receivables:,.0f}")
                        new_lines.append(f"- **Last Briefing:** [{briefing_path.name}]({briefing_path})")
                        skip_until_next_header = True
                        continue
                    
                    if in_financial_section and skip_until_next_header:
                        if line.startswith('##'):
                            in_financial_section = False
                            skip_until_next_header = False
                            new_lines.append(line)
                        continue
                    
                    if not skip_until_next_header:
                        new_lines.append(line)
                
                content = '\n'.join(new_lines)
            else:
                # Add new section
                financial_section = f"""
## Financial Summary
- **Revenue This Week:** PKR {revenue:,.0f}
- **Total Receivables:** PKR {receivables:,.0f}
- **Last Briefing:** [{briefing_path.name}]({briefing_path})
"""
                content += financial_section
            
            self.dashboard_path.write_text(content, encoding='utf-8')
            logger.info("Dashboard updated with briefing summary")
            
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
    
    def _extract_date_from_file(self, file: Path) -> Optional[datetime]:
        """Extract date from file content or name"""
        try:
            content = file.read_text(encoding='utf-8')
            
            # Try to find date in frontmatter
            if 'received:' in content:
                for line in content.split('\n'):
                    if 'received:' in line:
                        date_str = line.split('received:')[1].strip()
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00').split('+')[0])
            
            if 'created:' in content:
                for line in content.split('\n'):
                    if 'created:' in line:
                        date_str = line.split('created:')[1].strip()
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00').split('+')[0])
            
            # Try to extract from filename
            import re
            date_pattern = r'\d{4}-\d{2}-\d{2}'
            match = re.search(date_pattern, file.name)
            if match:
                return datetime.strptime(match.group(), '%Y-%m-%d')
            
            # Default to file modification time
            return datetime.fromtimestamp(file.stat().st_mtime)
            
        except:
            return None
    
    def _extract_task_type(self, content: str) -> str:
        """Extract task type from content"""
        if 'type: email' in content.lower():
            return "email"
        elif 'type: whatsapp' in content.lower():
            return "whatsapp"
        elif 'type: linkedin' in content.lower():
            return "linkedin"
        elif 'type: invoice' in content.lower() or 'payment' in content.lower():
            return "finance"
        elif 'type: social' in content.lower():
            return "social_media"
        else:
            return "general"


def main():
    """Main function to generate weekly briefing"""
    import sys
    
    # Get vault path
    if len(sys.argv) > 1:
        vault_path = sys.argv[1]
    else:
        vault_path = str(Path(__file__).parent / "Personal AI Employee Vault")
    
    generator = CEOBriefingGenerator(vault_path)
    result = generator.generate_weekly_briefing()
    
    if result.get('status') == 'success':
        print(f"✅ Weekly briefing generated successfully!")
        print(f"📄 Briefing saved to: {result.get('briefing_path')}")
        print(f"📊 Period: {result.get('period')}")
        print(f"💰 Revenue this week: PKR {result.get('accounting_summary', {}).get('revenue_this_week', 0):,.0f}")
        print(f"✅ Tasks completed: {result.get('tasks_summary', {}).get('completed_count', 0)}")
    else:
        print(f"❌ Error generating briefing: {result.get('message', 'Unknown error')}")


if __name__ == "__main__":
    main()
