"""
LinkedIn Poster - Automatically posts business content on LinkedIn to generate sales

Creates and posts professional content on LinkedIn based on business goals and analytics.
"""

import time
import logging
import random
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

class LinkedInPoster:
    def __init__(self, session_path: str, vault_path: str, post_interval: int = 86400):
        """
        Initialize the LinkedIn poster.

        Args:
            session_path (str): Path to Playwright persistent context
            vault_path (str): Path to the Obsidian vault
            post_interval (int): Time between posts in seconds (default: 24 hours)
        """
        self.session_path = session_path
        self.vault_path = Path(vault_path)
        self.post_interval = post_interval
        self.last_post_time = None
        self.post_templates = self._load_post_templates()

        # Set up logging
        self.logger = logging.getLogger('LinkedInPoster')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('linkedin_poster.log'),
                logging.StreamHandler()
            ]
        )

        # Load last post time
        self._load_last_post_time()

        self.logger.info(f'LinkedInPoster initialized')

    def _load_post_templates(self):
        """Load LinkedIn post templates from vault."""
        templates = [
            {
                'title': 'Thought Leadership',
                'template': 'Today I learned: {insight}. This is important because {reason}. What are your thoughts?',
                'categories': ['business_insights', 'industry_trends']
            },
            {
                'title': 'Case Study',
                'template': 'How we helped {client} achieve {result}. The key was {strategy}. Details in comments!',
                'categories': ['success_stories', 'client_results']
            },
            {
                'title': 'Industry Tip',
                'template': 'Pro tip: {tip}. This can save you {benefit}. Have you tried this?',
                'categories': ['productivity', 'best_practices']
            },
            {
                'title': 'Question Post',
                'template': 'What\'s your biggest challenge with {topic}? I\'d love to hear your thoughts!',
                'categories': ['engagement', 'community']
            },
            {
                'title': 'Behind the Scenes',
                'template': 'A day in the life at {company}. Here\'s how we {activity}. #entrepreneurship',
                'categories': ['company_culture', 'transparency']
            }
        ]

        # Add more templates based on business goals
        business_templates = self._load_business_templates()
        templates.extend(business_templates)

        return templates

    def _load_business_templates(self):
        """Load business-specific post templates."""
        # Get business goals from vault
        goals_file = self.vault_path / 'Business_Goals.md'
        if not goals_file.exists():
            return []

        # For now, return generic business templates
        return [
            {
                'title': 'Product Update',
                'template': 'Exciting news! We just launched {feature}. Here\'s what it does: {description}.',
                'categories': ['product_updates', 'announcements']
            },
            {
                'title': 'Customer Success',
                'template': '{customer_name} just achieved {milestone} using our {product}. Real results matter!',
                'categories': ['testimonials', 'social_proof']
            },
            {
                'title': 'Educational Content',
                'template': 'Did you know {fact}? Most people don\'t realize {insight}. Learn more in our guide!',
                'categories': ['education', 'awareness']
            }
        ]

    def _cleanup_session(self):
        """Clean up locked session files"""
        import shutil
        try:
            session_dir = Path(self.session_path)
            if session_dir.exists():
                # Remove lock files
                for lock_file in session_dir.glob('Singleton*'):
                    try:
                        lock_file.unlink()
                    except:
                        pass
                
                # Remove cache directories
                for cache_dir in ['GPUCache', 'Code Cache', 'Shared Cache', 'ShaderCache']:
                    cache_path = session_dir / cache_dir
                    if cache_path.exists():
                        try:
                            shutil.rmtree(cache_path)
                        except:
                            pass
        except:
            pass

    def _init_browser(self):
        """Initialize browser for LinkedIn"""
        import os
        from playwright.sync_api import sync_playwright
        
        # Cleanup session first
        self._cleanup_session()
        time.sleep(2)
        
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]

        chrome_executable = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_executable = path
                break

        if not chrome_executable:
            chrome_executable = "chrome"

        playwright = sync_playwright().start()
        
        # Try persistent context first
        try:
            browser = playwright.chromium.launch_persistent_context(
                self.session_path,
                executable_path=chrome_executable,
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                    '--disable-features=TranslateUI',
                    '--disable-features=ChromeWhatsNewUI',
                    '--disable-infobars',
                ],
                timeout=120000,
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            return playwright, browser, page
        except Exception as e:
            self.logger.debug(f'Persistent context failed: {e}')
            # Fallback to regular browser
            browser = playwright.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                ]
            )
            page = browser.new_page()
            return playwright, browser, page

    def _load_last_post_time(self):
        """Load the last post time from file."""
        post_time_file = self.vault_path / 'last_linkedin_post.txt'
        if post_time_file.exists():
            with open(post_time_file, 'r') as f:
                try:
                    self.last_post_time = datetime.fromisoformat(f.read().strip())
                except:
                    self.last_post_time = None
        else:
            self.last_post_time = None

    def _save_last_post_time(self):
        """Save the last post time to file."""
        post_time_file = self.vault_path / 'last_linkedin_post.txt'
        with open(post_time_file, 'w') as f:
            f.write(datetime.now().isoformat())

    def should_post(self) -> bool:
        """Check if it's time to post."""
        if not self.last_post_time:
            return True

        time_since_last_post = datetime.now() - self.last_post_time
        return time_since_last_post.total_seconds() >= self.post_interval

    def generate_post_content(self) -> dict:
        """Generate LinkedIn post content."""
        # Select a random template
        template = random.choice(self.post_templates)

        # Generate content based on template type
        if template['title'] == 'Thought Leadership':
            content = self._generate_thought_leadership()

        elif template['title'] == 'Case Study':
            content = self._generate_case_study()

        elif template['title'] == 'Industry Tip':
            content = self._generate_industry_tip()

        elif template['title'] == 'Question Post':
            content = self._generate_question_post()

        elif template['title'] == 'Behind the Scenes':
            content = self._generate_behind_scenes()

        else:
            content = self._generate_generic_post(template)

        return {
            'content': content,
            'template': template['title'],
            'category': template['categories'][0] if template['categories'] else 'general'
        }

    def _generate_thought_leadership(self):
        """Generate thought leadership post content."""
        insights = [
            "the future of work is hybrid",
            "AI won't replace humans, but humans with AI will",
            "data-driven decisions outperform gut feelings",
            "customer experience is the new competitive advantage"
        ]

        reasons = [
            "it drives better business outcomes",
            "it creates sustainable competitive advantages",
            "it improves employee satisfaction",
            "it increases customer loyalty"
        ]

        return f"Today I learned: {random.choice(insights)}. This is important because {random.choice(reasons)}. What are your thoughts?"

    def _generate_case_study(self):
        """Generate case study post content."""
        clients = ["TechCorp", "StartupX", "DigitalAgency", "EcommerceCo"]
        results = ["increased revenue by 40%", "reduced costs by 30%", "improved efficiency by 50%"]
        strategies = ["focusing on customer experience", "implementing automation", "optimizing workflows"]

        return f"How we helped {random.choice(clients)} achieve {random.choice(results)}. The key was {random.choice(strategies)}. Details in comments!"

    def _generate_industry_tip(self):
        """Generate industry tip post content."""
        tips = [
            "automating repetitive tasks",
            "using data analytics for decision making",
            "prioritizing customer feedback",
            "investing in employee development"
        ]

        benefits = [
            "save you 10+ hours per week",
            "double your conversion rates",
            "reduce churn by 25%",
            "increase team productivity by 40%"
        ]

        return f"Pro tip: {random.choice(tips)}. This can {random.choice(benefits)}. Have you tried this?"

    def _generate_question_post(self):
        """Generate question post content."""
        topics = [
            "lead generation",
            "customer retention",
            "remote work",
            "AI implementation",
            "marketing automation"
        ]

        return f"What's your biggest challenge with {random.choice(topics)}? I'd love to hear your thoughts!"

    def _generate_behind_scenes(self):
        """Generate behind-the-scenes post content."""
        activities = [
            "we conduct our weekly strategy meetings",
            "we onboard new team members",
            "we develop our products",
            "we serve our customers"
        ]

        company_name = "Your Company Name"  # Replace with actual company name

        return f"A day in the life at {company_name}. Here's how we {random.choice(activities)}. #entrepreneurship"

    def _generate_generic_post(self, template):
        """Generate generic post content based on template."""
        return template['template'].format(
            insight="continuous learning is key",
            reason="it keeps you competitive",
            client="a client",
            result="great results",
            strategy="smart strategies",
            tip="a useful tip",
            benefit="significant benefits",
            topic="a relevant topic",
            company="your company",
            activity="important work",
            feature="an exciting feature",
            description="amazing things",
            customer_name="a customer",
            milestone="an important milestone",
            product="our product",
            fact="an interesting fact"
        )

    def create_post(self, content: str) -> dict:
        """Create a LinkedIn post with content - generates post file only (no auto-posting)."""
        try:
            # Save post to Needs_Action folder for manual review
            post_id = f"POST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            post_file = self.vault_path / 'Needs_Action' / f'LINKEDIN_POST_{post_id}.md'
            
            post_content = f"""---
type: linkedin_post
source: linkedin
id: {post_id}
template: Manual Post
status: pending
created: {datetime.now().isoformat()}
---

# LinkedIn Post

## Content

{content}

## Suggested Actions

- [ ] Review post content
- [ ] Edit if needed
- [ ] Add relevant hashtags
- [ ] Add images/media (optional)
- [ ] Post on LinkedIn manually
- [ ] Monitor engagement after posting

---
*Generated by LinkedIn Poster*
"""
            
            # Ensure Needs_Action folder exists
            post_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the post
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(post_content)
            
            self.logger.info(f'Post saved to: {post_file.name}')
            self._save_last_post_time()
            
            return {'success': True, 'content': content, 'file': str(post_file)}

        except Exception as e:
            self.logger.error(f'Error creating post file: {e}')
            return {'success': False, 'error': str(e)}

    def _add_post_formatting(self, content_box):
        """Add formatting to the post content."""
        # Add emojis and formatting
        emojis = ['💡', '💥', '💡', '🔥', '💪']
        emoji = random.choice(emojis)

        # Add some basic formatting
        content_box.fill(f"{emoji} {content_box.text_content()} {emoji}")

    def run(self):
        """Main posting loop."""
        while True:
            try:
                if self.should_post():
                    # Generate post content
                    post_data = self.generate_post_content()
                    
                    print(f"\n{'='*60}")
                    print(f"  GENERATING NEW POST")
                    print(f"{'='*60}")
                    print(f"  Template: {post_data['template']}")
                    print(f"  Category: {post_data['category']}")
                    print(f"{'='*60}\n")
                    
                    self.logger.info(f'Generating post: {post_data["template"]} ({post_data["category"]})')

                    # Create the post
                    result = self.create_post(post_data['content'])

                    if result['success']:
                        print(f"\n{'='*60}")
                        print(f"  POST CREATED SUCCESSFULLY!")
                        print(f"{'='*60}")
                        print(f"  File: {result['file']}")
                        print(f"  Content: {result['content'][:80]}...")
                        print(f"\n  Next Steps:")
                        print(f"   1. Review the post in Needs_Action folder")
                        print(f"   2. Edit if needed")
                        print(f"   3. Post manually on LinkedIn")
                        print(f"{'='*60}\n")
                        
                        self.logger.info(f'Post created successfully: {result["content"][:50]}...')
                    else:
                        print(f"\n{'='*60}")
                        print(f"  POST FAILED")
                        print(f"{'='*60}")
                        print(f"  Error: {result.get('error', 'Unknown error')}")
                        print(f"{'='*60}\n")
                        
                        self.logger.error(f'Failed to create post: {result["error"]}')
                else:
                    # Calculate time until next post
                    time_since_last = datetime.now() - self.last_post_time
                    hours_since = time_since_last.total_seconds() / 3600
                    hours_until = 24 - hours_since
                    
                    print(f"\n{'='*60}")
                    print(f"  No new post needed yet")
                    print(f"{'='*60}")
                    print(f"  Last post: {hours_since:.1f} hours ago")
                    print(f"  Next post in: {hours_until:.1f} hours")
                    print(f"{'='*60}\n")
                    
                    self.logger.info(f'Not time to post yet. Last post: {hours_since:.1f}h ago')

                # Wait before next check
                print(f"  Checking again in 1 hour...")
                print(f"  (Press Ctrl+C to stop)\n")
                time.sleep(3600)  # Check every hour

            except KeyboardInterrupt:
                print(f"\n{'='*60}")
                print(f"  LINKEDIN POSTER STOPPED")
                print(f"{'='*60}\n")
                self.logger.info('LinkedIn poster stopped')
                break

            except Exception as e:
                self.logger.error(f'Error in posting loop: {e}')
                time.sleep(3600)  # Wait before retrying

if __name__ == "__main__":
    import sys
    
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('linkedin_poster.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Example usage
    vault_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\Personal AI Employee Vault"
    session_path = r"C:\Users\HAROON TRADERS\Desktop\ar portfolio\Hacketon-Employee\Sliver-Tier\linkedin_session"

    poster = LinkedInPoster(session_path, vault_path, post_interval=86400)

    print("\n" + "="*60)
    print("  LINKEDIN POSTER")
    print("="*60)
    print("  Posting business content every 24 hours")
    print("  Posts saved to: Needs_Action folder")
    print("  Press Ctrl+C to stop")
    print("="*60 + "\n")

    # Start the poster
    try:
        poster.run()
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("  Stopped")
        print("="*60 + "\n")