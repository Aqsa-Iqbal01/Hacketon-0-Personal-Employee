---
description: Monitor Instagram Business Account for comments, mentions, story replies, and hashtag mentions
globs: 
---

# Instagram Watcher Skill

## Overview
Monitor Instagram Business Account activities including comments, mentions, story replies, and hashtag mentions. Creates action files in Needs_Action folder for AI processing.

## Capabilities
- Monitor comments on Instagram posts
- Track @mentions in comments
- Monitor story replies
- Track branded hashtag usage
- Priority detection for urgent comments (buy, price, order)
- Create action files for all activities

## Usage

### Start Instagram Watcher
```bash
python scripts/instagram_watcher.py
```

### Test Instagram Watcher
```bash
python test_instagram_only.py
```

## Configuration

### Required Environment Variables
```env
META_ACCESS_TOKEN=your_access_token
META_INSTAGRAM_ACCOUNT_ID=your_ig_business_account_id
```

### Get Instagram Account ID
1. Go to Graph API Explorer
2. Run query: /me?fields=instagram_business_account
3. Copy the instagram_business_account.id

### Permissions Required
- instagram_basic
- instagram_content_publish
- pages_read_engagement

## Action Files Created

### Instagram Comment
Location: `Needs_Action/INSTAGRAM_COMMENT_*.md`

```markdown
---
type: instagram_comment
source: instagram
id: comment_id
username: user_username
text: comment_text
timestamp: 2026-03-08T00:00:00
media_id: media_123
likes: 5
priority: high
---

# Instagram Comment

**From:** @username
**Priority:** HIGH

## Comment Content

Great product! How much does it cost?

## Suggested Actions
- [ ] Review comment
- [ ] Respond with price
- [ ] Send DM if needed
```

### Instagram Mention
Location: `Needs_Action/INSTAGRAM_MENTION_*.md`

```markdown
---
type: instagram_mention
source: instagram
id: mention_id
username: user_username
text: @yourbusiness I need help!
priority: high
---
```

### Instagram Story Reply
Location: `Needs_Action/INSTAGRAM_STORY_REPLY_*.md`

```markdown
---
type: instagram_story_reply
source: instagram
id: reply_id
text: Is this available?
expires: 2026-03-09T00:00:00
priority: high
---
```

### Instagram Hashtag
Location: `Needs_Action/INSTAGRAM_HASHTAG_*.md`

```markdown
---
type: instagram_hashtag
source: instagram
hashtag: #yourbusiness
priority: normal
---
```

## Priority Keywords

Comments with these keywords get **HIGH** priority:
- urgent
- help
- asap
- price
- buy
- order
- cost
- how much

## Integration with MCP Servers

### Post to Instagram
```python
from mcp.mcp_meta_social import meta_post_to_instagram

result = meta_post_to_instagram(
    caption="Your caption here",
    image_url="https://example.com/image.jpg"
)
```

### Get Instagram Insights
```python
from mcp.mcp_meta_social import meta_get_instagram_insights

insights = meta_get_instagram_insights()
```

### Reply to Comment
```python
from mcp.mcp_meta_social import meta_reply_to_comment

result = meta_reply_to_comment(
    comment_id="comment_123",
    message="Thank you for your comment!"
)
```

## Workflow Example

1. **Customer comments "How much?"** → Watcher detects
2. **Action file created** → Needs_Action/INSTAGRAM_COMMENT_*.md
3. **Claude reads file** → Sees HIGH priority
4. **Draft response** → "DM sent with pricing!"
5. **Post reply via MCP** → Comment replied
6. **Move to Done** → Task completed

## Best Practices

### Response Time
- **High Priority:** Respond within 1 hour
- **Normal Priority:** Respond within 24 hours
- **Story Replies:** Respond within 2 hours (expires!)

### Engagement Tips
- Always respond to comments
- Like positive comments
- Send DMs for private matters
- Use story replies for urgent matters

## Troubleshooting

### Error: Invalid Access Token
- Token expired, generate new one
- Update .env file
- Restart watcher

### Error: Instagram Account Not Found
- Verify account is Business/Creator
- Check account ID is correct
- Ensure permissions granted

### No Comments Detected
- Posts must have comments
- Wait for next check cycle (5 min)
- Check account is connected

## Related Skills
- facebook-watcher
- twitter-watcher
- linkedin-watcher
- meta-social-mcp
