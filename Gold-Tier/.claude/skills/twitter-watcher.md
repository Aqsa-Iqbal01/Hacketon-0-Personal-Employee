---
description: Monitor Twitter/X for mentions, replies, retweets, and engagement
globs: 
---

# Twitter/X Watcher Skill

## Overview
Monitor Twitter/X account for mentions, replies, retweets, likes, and direct messages. Creates action files in Needs_Action folder for AI processing.

## Capabilities
- Track @mentions in tweets
- Monitor replies to your tweets
- Track retweets and quotes
- Monitor tweet engagement
- Priority detection for urgent mentions
- Create action files for all activities

## Usage

### Start Twitter Watcher
```bash
python scripts/twitter_watcher.py
```

### Test Twitter Watcher
```bash
python test_social_watchers.py
```

## Configuration

### Required Environment Variables
```env
TWITTER_BEARER_TOKEN=your_bearer_token
TWITTER_USER_ID=your_twitter_user_id
```

### Get Twitter Bearer Token
1. Go to https://developer.twitter.com/
2. Create a project and app
3. Go to Keys and Tokens
4. Copy "Bearer Token"
5. Add to .env file

### Get Twitter User ID
1. Go to Twitter API Console
2. Run: /2/users/by/username/your_username
3. Copy the "id" field

## Action Files Created

### Twitter Mention
Location: `Needs_Action/TWITTER_MENTION_*.md`

```markdown
---
type: twitter_mention
source: twitter
id: tweet_id
from: User Name @username
text: @yourbusiness Love your product!
created_at: 2026-03-08T00:00:00
retweets: 5
likes: 20
replies: 3
priority: normal
---

# Twitter Mention

**From:** @username
**Posted:** 2026-03-08T00:00:00

## Tweet Content

@yourbusiness Love your product! When will you restock?

## Engagement
- 🔄 Retweets: 5
- ❤️ Likes: 20
- 💬 Replies: 3

## Suggested Actions
- [ ] Thank user for support
- [ ] Answer restock question
- [ ] Like the tweet
- [ ] Retweet if relevant
```

### Twitter Reply
Location: `Needs_Action/TWITTER_REPLY_*.md`

```markdown
---
type: twitter_reply
source: twitter
id: reply_id
from: User Name @username
text: Great thread! Very informative.
parent_tweet_id: tweet_123
priority: normal
---
```

## Priority Detection

### HIGH Priority Keywords
- urgent
- help
- asap
- emergency
- complaint
- issue
- problem
- broken

### NORMAL Priority
- General mentions
- Positive feedback
- Questions
- Conversations

## Integration with MCP Servers

### Post Tweet
```python
from mcp.mcp_twitter_x import twitter_post_tweet

result = twitter_post_tweet(
    text="Your tweet text here",
    media_path="path/to/image.jpg"  # optional
)
```

### Post Thread
```python
from mcp.mcp_twitter_x import twitter_post_thread

tweets = [
    "First tweet in thread 🧵",
    "Second tweet with more details",
    "Final tweet with conclusion"
]
result = twitter_post_thread(tweets=tweets)
```

### Reply to Tweet
```python
from mcp.mcp_twitter_x import twitter_reply_to_tweet

result = twitter_reply_to_tweet(
    tweet_id="tweet_123",
    text="Thanks for the mention! 😊"
)
```

### Get Twitter Analytics
```python
from mcp.mcp_twitter_x import twitter_get_analytics

analytics = twitter_get_analytics(days=7)
```

### Like Tweet
```python
from mcp.mcp_twitter_x import twitter_like_tweet

result = twitter_like_tweet(tweet_id="tweet_123")
```

### Retweet
```python
from mcp.mcp_twitter_x import twitter_retweet

result = twitter_retweet(tweet_id="tweet_123")
```

## Workflow Example

### Mention Response Workflow
1. **User mentions @yourbusiness** → Watcher detects
2. **Action file created** → TWITTER_MENTION_*.md
3. **Claude analyzes** → Determines intent
4. **Draft response** → Appropriate reply
5. **Post via MCP** → Reply tweeted
6. **Log action** → Move to Done

### High Priority Alert
```
🔴 HIGH PRIORITY MENTION DETECTED!

From: @angry_customer
Text: @yourbusiness Your service is broken!
Keywords: broken

Suggested: Immediate response required!
```

## Best Practices

### Response Time
- **High Priority:** 30 minutes
- **Normal Priority:** 2-4 hours
- **General Engagement:** 24 hours

### Engagement Guidelines
- Always respond to questions
- Thank users for positive mentions
- Handle complaints professionally
- Use DMs for sensitive issues
- Never argue publicly

### Content Strategy
- Mix of promotional and educational
- Engage with trending topics
- Use relevant hashtags
- Post consistently (3-5x/day)
- Respond to all mentions

## Monitoring Dashboard

### Daily Metrics to Track
- New mentions count
- Reply response rate
- Engagement rate
- Follower growth
- Top performing tweets

### Weekly Review
- Best performing content
- Response time analysis
- Sentiment analysis
- Competitor comparison

## Troubleshooting

### Error: Invalid Bearer Token
- Token expired or revoked
- Generate new token from Developer Portal
- Update .env file
- Restart watcher

### Error: Rate Limit Exceeded
- Twitter API has rate limits
- Wait 15 minutes for reset
- Reduce check frequency

### No Mentions Detected
- Account may have no mentions
- Check user ID is correct
- Verify token permissions
- Wait for new mentions

## Advanced Features

### Sentiment Analysis
```python
# Analyze mention sentiment
if any(word in text.lower() for word in ['love', 'great', 'awesome']):
    sentiment = 'positive'
elif any(word in text.lower() for word in ['hate', 'terrible', 'awful']):
    sentiment = 'negative'
else:
    sentiment = 'neutral'
```

### Auto-Response Rules
```python
# Auto-respond to common questions
if 'price' in text.lower() or 'cost' in text.lower():
    response = "Thanks for your interest! Please check our website for pricing."
elif 'help' in text.lower() or 'support' in text.lower():
    response = "We'd be happy to help! Please DM us with details."
```

## Related Skills
- facebook-watcher
- instagram-watcher
- linkedin-watcher
- twitter-x-mcp
