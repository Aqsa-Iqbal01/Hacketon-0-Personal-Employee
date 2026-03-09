---
description: Monitor Facebook Page for new posts, comments, and messages
globs: 
---

# Facebook Watcher Skill

## Overview
Monitor Facebook Page activities including posts, comments, messages, and engagement. Creates action files in Needs_Action folder for AI processing.

## Capabilities
- Monitor Facebook Page posts
- Track new comments on posts
- Monitor page messages
- Track engagement (likes, shares, comments)
- Create action files for new activities
- Priority detection for urgent messages

## Usage

### Start Facebook Watcher
```bash
python scripts/facebook_watcher.py
```

### Check Facebook Activity
```bash
python test_social_watchers.py
```

## Configuration

### Required Environment Variables
```env
META_ACCESS_TOKEN=your_access_token
META_FACEBOOK_PAGE_ID=your_page_id
```

### Get Facebook Access Token
1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app
3. Add permissions: pages_read_engagement, pages_manage_posts
4. Click "Generate Access Token"
5. Copy the token to .env file

### Get Facebook Page ID
1. Open Graph API Explorer
2. Run query: /me/accounts
3. Copy the "id" field from response

## Action Files Created

### Facebook Post
Location: `Needs_Action/FACEBOOK_POST_*.md`

```markdown
---
type: facebook_post
source: facebook
id: post_id
from: user_name
message: post_content
likes: 10
comments: 5
shares: 2
priority: normal
---
```

### Facebook Comment
Location: `Needs_Action/FACEBOOK_COMMENT_*.md`

```markdown
---
type: facebook_comment
source: facebook
id: comment_id
from: user_name
message: comment_text
priority: normal
---
```

### Facebook Message
Location: `Needs_Action/FACEBOOK_MESSAGE_*.md`

```markdown
---
type: facebook_message
source: facebook
id: message_id
from: user_name
message: message_text
priority: high
---
```

## Integration with MCP Servers

### Post to Facebook
```python
from mcp.mcp_meta_social import meta_post_to_facebook

result = meta_post_to_facebook(
    message="Your post message here",
    link="https://your-website.com"
)
```

### Get Facebook Insights
```python
from mcp.mcp_meta_social import meta_get_facebook_insights

insights = meta_get_facebook_insights()
```

## Workflow Example

1. **Watcher detects new comment** → Creates action file
2. **Claude Code reads file** → Analyzes comment
3. **Determine response** → Draft reply
4. **Post via MCP** → Send to Facebook
5. **Log action** → Move to Done folder

## Troubleshooting

### Error: Access Token Expired
- Generate new token from Graph API Explorer
- Update .env file
- Restart watcher

### Error: Page Not Found
- Verify Page ID is correct
- Ensure token has page permissions
- Check page is published

### Error: No Activity Detected
- Wait 5 minutes for next check
- Verify page has activity
- Check watcher logs

## Related Skills
- instagram-watcher
- twitter-watcher
- linkedin-watcher
- meta-social-mcp
