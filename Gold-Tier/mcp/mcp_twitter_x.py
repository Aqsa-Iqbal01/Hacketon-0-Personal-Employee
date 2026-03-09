#!/usr/bin/env python3
"""
Twitter (X) MCP Server
Integrates with Twitter API v2 for posting and monitoring
Provides posting, reply, and analytics capabilities
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta
from pathlib import Path
import base64

# Initialize MCP server
mcp = FastMCP("twitter-x")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twitter API Configuration
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")
TWITTER_USER_ID = os.getenv("TWITTER_USER_ID", "")

TWITTER_API_URL = "https://api.twitter.com/2"
TWITTER_UPLOAD_URL = "https://upload.twitter.com/1.1"


@mcp.tool()
def twitter_connect() -> Dict[str, Any]:
    """Test connection to Twitter API"""
    try:
        # Get user info to verify connection
        url = f"{TWITTER_API_URL}/users/me"
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
            'Content-Type': 'application/json'
        }
        params = {
            'user.fields': 'name,username,description,public_metrics,verified'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        user_data = response.json()
        
        user = user_data.get('data', {})
        
        return {
            "status": "connected",
            "user": {
                "id": user.get('id', ''),
                "name": user.get('name', ''),
                "username": user.get('username', ''),
                "description": user.get('description', ''),
                "verified": user.get('verified', False),
                "followers": user.get('public_metrics', {}).get('followers_count', 0),
                "following": user.get('public_metrics', {}).get('following_count', 0),
                "tweets": user.get('public_metrics', {}).get('tweet_count', 0)
            },
            "message": "Successfully connected to Twitter API"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def twitter_post_tweet(
    text: str,
    media_path: Optional[str] = None,
    media_url: Optional[str] = None,
    reply_settings: Optional[str] = None,
    quote_tweet_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Post a tweet to Twitter/X
    
    Args:
        text: Tweet text (max 280 characters for standard)
        media_path: Local path to media file (optional)
        media_url: URL of media to attach (optional)
        reply_settings: Who can reply (everyone, mentionedUsers, following)
        quote_tweet_id: Tweet ID to quote (optional)
    
    Returns:
        Tweet creation result with ID and URL
    """
    try:
        # Prepare tweet payload
        tweet_payload = {
            'text': text
        }
        
        if reply_settings:
            tweet_payload['reply_settings'] = reply_settings
        
        # Handle media attachment
        media_id = None
        if media_path:
            media_id = _upload_media(media_path)
        elif media_url:
            media_id = _upload_media_from_url(media_url)
        
        if media_id:
            tweet_payload['media'] = {
                'media_ids': [media_id]
            }
        
        if quote_tweet_id:
            tweet_payload['quote_tweet_id'] = quote_tweet_id
        
        # Post tweet
        url = f"{TWITTER_API_URL}/tweets"
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=tweet_payload, headers=headers, timeout=30)
        response.raise_for_status()
        tweet_data = response.json()
        
        tweet_id = tweet_data.get('data', {}).get('id')
        
        # Get username for permalink
        user_info = twitter_connect()
        username = user_info.get('user', {}).get('username', 'user')
        
        return {
            "status": "success",
            "tweet_id": tweet_id,
            "text": text,
            "permalink": f"https://twitter.com/{username}/status/{tweet_id}",
            "has_media": media_id is not None,
            "message": "Successfully posted tweet"
        }
        
    except Exception as e:
        logger.error(f"Error posting tweet: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def twitter_post_thread(
    tweets: List[str],
    media_paths: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Post a thread of tweets
    
    Args:
        tweets: List of tweet texts in order
        media_paths: Optional list of media paths for each tweet
    
    Returns:
        Thread creation result with all tweet IDs
    """
    try:
        if not tweets:
            return {"status": "error", "message": "No tweets provided"}
        
        results = []
        previous_tweet_id = None
        
        for i, tweet_text in enumerate(tweets):
            # Prepare media for this tweet
            media_path = None
            if media_paths and i < len(media_paths):
                media_path = media_paths[i]
            
            # For first tweet, just post
            # For subsequent tweets, reply to previous
            if previous_tweet_id:
                # This is a reply
                tweet_payload = {
                    'text': tweet_text,
                    'reply': {
                        'in_reply_to_tweet_id': previous_tweet_id
                    }
                }
            else:
                tweet_payload = {
                    'text': tweet_text
                }
            
            # Handle media
            media_id = None
            if media_path:
                media_id = _upload_media(media_path)
            
            if media_id:
                tweet_payload['media'] = {
                    'media_ids': [media_id]
                }
            
            # Post tweet/reply
            url = f"{TWITTER_API_URL}/tweets"
            headers = {
                'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=tweet_payload, headers=headers, timeout=30)
            response.raise_for_status()
            tweet_data = response.json()
            
            tweet_id = tweet_data.get('data', {}).get('id')
            results.append({
                "tweet_id": tweet_id,
                "text": tweet_text,
                "position": i + 1
            })
            
            previous_tweet_id = tweet_id
        
        user_info = twitter_connect()
        username = user_info.get('user', {}).get('username', 'user')
        
        return {
            "status": "success",
            "tweet_count": len(results),
            "tweets": results,
            "thread_url": f"https://twitter.com/{username}/status/{results[0]['tweet_id']}",
            "message": f"Successfully posted thread with {len(results)} tweets"
        }
        
    except Exception as e:
        logger.error(f"Error posting thread: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def twitter_get_timeline(
    username: Optional[str] = None,
    max_results: int = 10,
    exclude: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get tweets from user timeline
    
    Args:
        username: Twitter username (defaults to authenticated user)
        max_results: Maximum number of tweets to retrieve
        exclude: List of tweet types to exclude (retweets, replies)
    
    Returns:
        List of tweets with details
    """
    try:
        if not username:
            # Use authenticated user's ID
            user_id = TWITTER_USER_ID
        else:
            # Get user ID from username
            url = f"{TWITTER_API_URL}/users/by/username/{username.lstrip('@')}"
            headers = {'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            user_id = response.json().get('data', {}).get('id')
        
        if not user_id:
            return {"status": "error", "message": "User not found"}
        
        # Get timeline
        url = f"{TWITTER_API_URL}/users/{user_id}/tweets"
        headers = {'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'}
        params = {
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,public_metrics,entities,context_annotations',
            'exclude': ','.join(exclude) if exclude else ''
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        timeline_data = response.json()
        
        tweets = []
        for item in timeline_data.get('data', []):
            tweets.append({
                "tweet_id": item.get('id', ''),
                "text": item.get('text', ''),
                "created_at": item.get('created_at', ''),
                "retweets": item.get('public_metrics', {}).get('retweet_count', 0),
                "likes": item.get('public_metrics', {}).get('like_count', 0),
                "replies": item.get('public_metrics', {}).get('reply_count', 0),
                "quotes": item.get('public_metrics', {}).get('quote_count', 0)
            })
        
        return {
            "status": "success",
            "username": username or TWITTER_USER_ID,
            "count": len(tweets),
            "tweets": tweets,
            "message": f"Retrieved {len(tweets)} tweets"
        }
        
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def twitter_get_mentions(
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Get tweets mentioning the authenticated user
    
    Args:
        max_results: Maximum number of mentions to retrieve
    
    Returns:
        List of mention tweets
    """
    try:
        user_id = TWITTER_USER_ID
        
        url = f"{TWITTER_API_URL}/users/{user_id}/mentioned_tweets"
        headers = {'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'}
        params = {
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,public_metrics,author_id,entities',
            'expansions': 'author_id',
            'user.fields': 'name,username'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        mentions_data = response.json()
        
        # Get user info for authors
        users = {u['id']: u for u in mentions_data.get('includes', {}).get('users', [])}
        
        mentions = []
        for item in mentions_data.get('data', []):
            author = users.get(item.get('author_id'), {})
            mentions.append({
                "tweet_id": item.get('id', ''),
                "text": item.get('text', ''),
                "author": author.get('username', 'Unknown'),
                "author_name": author.get('name', ''),
                "created_at": item.get('created_at', ''),
                "retweets": item.get('public_metrics', {}).get('retweet_count', 0),
                "likes": item.get('public_metrics', {}).get('like_count', 0)
            })
        
        return {
            "status": "success",
            "count": len(mentions),
            "mentions": mentions,
            "message": f"Retrieved {len(mentions)} mentions"
        }
        
    except Exception as e:
        logger.error(f"Error getting mentions: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def twitter_reply_to_tweet(
    tweet_id: str,
    text: str,
    media_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reply to a tweet
    
    Args:
        tweet_id: Tweet ID to reply to
        text: Reply text
        media_path: Optional media to attach
    
    Returns:
        Reply creation result
    """
    try:
        payload = {
            'text': text,
            'reply': {
                'in_reply_to_tweet_id': tweet_id
            }
        }
        
        # Handle media
        media_id = None
        if media_path:
            media_id = _upload_media(media_path)
        
        if media_id:
            payload['media'] = {'media_ids': [media_id]}
        
        url = f"{TWITTER_API_URL}/tweets"
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        reply_data = response.json()
        
        reply_id = reply_data.get('data', {}).get('id')
        
        user_info = twitter_connect()
        username = user_info.get('user', {}).get('username', 'user')
        
        return {
            "status": "success",
            "reply_id": reply_id,
            "text": text,
            "in_reply_to": tweet_id,
            "permalink": f"https://twitter.com/{username}/status/{reply_id}",
            "message": "Successfully posted reply"
        }
        
    except Exception as e:
        logger.error(f"Error posting reply: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def twitter_like_tweet(tweet_id: str) -> Dict[str, Any]:
    """
    Like a tweet
    
    Args:
        tweet_id: Tweet ID to like
    
    Returns:
        Like result
    """
    try:
        url = f"{TWITTER_API_URL}/users/{TWITTER_USER_ID}/likes"
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
            'Content-Type': 'application/json'
        }
        payload = {'tweet_id': tweet_id}
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        return {
            "status": "success",
            "tweet_id": tweet_id,
            "message": "Successfully liked tweet"
        }
        
    except Exception as e:
        logger.error(f"Error liking tweet: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def twitter_retweet(tweet_id: str) -> Dict[str, Any]:
    """
    Retweet a tweet
    
    Args:
        tweet_id: Tweet ID to retweet
    
    Returns:
        Retweet result
    """
    try:
        url = f"{TWITTER_API_URL}/users/{TWITTER_USER_ID}/retweets"
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
            'Content-Type': 'application/json'
        }
        payload = {'tweet_id': tweet_id}
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        retweet_data = response.json()
        
        retweet_id = retweet_data.get('data', {}).get('retweet_id')
        
        return {
            "status": "success",
            "tweet_id": tweet_id,
            "retweet_id": retweet_id,
            "message": "Successfully retweeted"
        }
        
    except Exception as e:
        logger.error(f"Error retweeting: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def twitter_get_analytics(
    tweet_ids: Optional[List[str]] = None,
    days: int = 7
) -> Dict[str, Any]:
    """
    Get tweet analytics/impressions
    
    Args:
        tweet_ids: List of tweet IDs to analyze (defaults to recent tweets)
        days: Number of days to analyze
    
    Returns:
        Analytics data for specified tweets
    """
    try:
        if not tweet_ids:
            # Get recent tweets
            timeline = twitter_get_timeline(max_results=10)
            tweet_ids = [t['tweet_id'] for t in timeline.get('tweets', [])]
        
        if not tweet_ids:
            return {"status": "error", "message": "No tweets to analyze"}
        
        # Get metrics for each tweet
        analytics = []
        for tweet_id in tweet_ids:
            url = f"{TWITTER_API_URL}/tweets/{tweet_id}"
            headers = {'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'}
            params = {
                'tweet.fields': 'public_metrics,created_at,text'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            tweet_data = response.json()
            
            tweet = tweet_data.get('data', {})
            metrics = tweet.get('public_metrics', {})
            
            analytics.append({
                "tweet_id": tweet_id,
                "text": tweet.get('text', '')[:100],
                "created_at": tweet.get('created_at', ''),
                "impressions": metrics.get('impression_count', 0),
                "likes": metrics.get('like_count', 0),
                "retweets": metrics.get('retweet_count', 0),
                "replies": metrics.get('reply_count', 0),
                "quotes": metrics.get('quote_count', 0),
                "engagement_rate": _calculate_engagement_rate(metrics)
            })
        
        # Calculate summary
        total_impressions = sum(a['impressions'] for a in analytics)
        total_likes = sum(a['likes'] for a in analytics)
        total_retweets = sum(a['retweets'] for a in analytics)
        
        return {
            "status": "success",
            "tweet_count": len(analytics),
            "period_days": days,
            "summary": {
                "total_impressions": total_impressions,
                "total_likes": total_likes,
                "total_retweets": total_retweets,
                "average_engagement_rate": sum(a['engagement_rate'] for a in analytics) / len(analytics) if analytics else 0
            },
            "tweets": analytics,
            "message": f"Analytics retrieved for {len(analytics)} tweets"
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def _upload_media(media_path: str) -> Optional[str]:
    """Upload media to Twitter and return media ID"""
    try:
        # Initialize upload
        init_url = f"{TWITTER_UPLOAD_URL}/media/upload.json"
        init_params = {
            'command': 'INIT',
            'total_bytes': os.path.getsize(media_path),
            'media_type': _get_media_type(media_path)
        }
        headers = {'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'}
        
        response = requests.post(init_url, params=init_params, headers=headers, timeout=30)
        response.raise_for_status()
        media_id = response.json().get('media_id_string')
        
        # Append media
        with open(media_path, 'rb') as f:
            append_params = {
                'command': 'APPEND',
                'media_id': media_id,
                'segment_index': 0
            }
            files = {'media': f}
            response = requests.post(init_url, params=append_params, headers=headers, files=files, timeout=60)
            response.raise_for_status()
        
        # Finalize upload
        finalize_params = {
            'command': 'FINALIZE',
            'media_id': media_id
        }
        response = requests.post(init_url, params=finalize_params, headers=headers, timeout=30)
        response.raise_for_status()
        
        return media_id
        
    except Exception as e:
        logger.error(f"Error uploading media: {e}")
        return None


def _upload_media_from_url(media_url: str) -> Optional[str]:
    """Download media from URL and upload to Twitter"""
    try:
        # Download media
        response = requests.get(media_url, timeout=30)
        response.raise_for_status()
        
        # Save temporarily
        temp_path = f"/tmp/twitter_media_{datetime.now().timestamp()}"
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        # Upload
        media_id = _upload_media(temp_path)
        
        # Cleanup
        os.remove(temp_path)
        
        return media_id
        
    except Exception as e:
        logger.error(f"Error uploading media from URL: {e}")
        return None


def _get_media_type(file_path: str) -> str:
    """Get MIME type based on file extension"""
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo'
    }
    return mime_types.get(ext, 'application/octet-stream')


def _calculate_engagement_rate(metrics: Dict) -> float:
    """Calculate engagement rate from metrics"""
    impressions = metrics.get('impression_count', 0)
    if impressions == 0:
        return 0.0
    
    engagements = (
        metrics.get('like_count', 0) +
        metrics.get('retweet_count', 0) +
        metrics.get('reply_count', 0) +
        metrics.get('quote_count', 0)
    )
    
    return round((engagements / impressions) * 100, 2)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
