#!/usr/bin/env python3
"""
Facebook/Instagram MCP Server
Integrates with Meta Graph API for social media management
Provides posting, monitoring, and analytics capabilities
"""

import os
import json
import logging
import requests
import base64
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta
from pathlib import Path

# Initialize MCP server
mcp = FastMCP("meta-social")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Meta Graph API Configuration
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_INSTAGRAM_ACCOUNT_ID = os.getenv("META_INSTAGRAM_ACCOUNT_ID", "")
META_FACEBOOK_PAGE_ID = os.getenv("META_FACEBOOK_PAGE_ID", "")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v18.0")
GRAPH_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


@mcp.tool()
def meta_connect() -> Dict[str, Any]:
    """Test connection to Meta Graph API"""
    try:
        # Test Instagram connection
        ig_url = f"{GRAPH_API_URL}/{META_INSTAGRAM_ACCOUNT_ID}"
        params = {
            'access_token': META_ACCESS_TOKEN,
            'fields': 'username,biography,followers_count,follows_count,media_count'
        }
        
        response = requests.get(ig_url, params=params, timeout=30)
        response.raise_for_status()
        ig_data = response.json()
        
        # Test Facebook connection
        fb_url = f"{GRAPH_API_URL}/{META_FACEBOOK_PAGE_ID}"
        params = {
            'access_token': META_ACCESS_TOKEN,
            'fields': 'name,followers_count,likes'
        }
        
        response = requests.get(fb_url, params=params, timeout=30)
        response.raise_for_status()
        fb_data = response.json()
        
        return {
            "status": "connected",
            "instagram": {
                "username": ig_data.get('username', ''),
                "followers": ig_data.get('followers_count', 0),
                "following": ig_data.get('follows_count', 0),
                "posts": ig_data.get('media_count', 0)
            },
            "facebook": {
                "page_name": fb_data.get('name', ''),
                "followers": fb_data.get('followers_count', 0),
                "likes": fb_data.get('likes', 0)
            },
            "message": "Successfully connected to Meta Graph API"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def meta_post_to_instagram(
    caption: str,
    image_url: Optional[str] = None,
    image_path: Optional[str] = None,
    is_video: bool = False,
    video_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Post content to Instagram
    
    Args:
        caption: Post caption text
        image_url: URL of image to post (optional)
        image_path: Local path to image (optional)
        is_video: Whether this is a video post
        video_url: URL of video to post (optional)
    
    Returns:
        Post creation result with ID and permalink
    """
    try:
        if is_video:
            # Video post workflow
            if not video_url:
                return {"status": "error", "message": "Video URL required for video posts"}
            
            # Create media container for video
            container_url = f"{GRAPH_API_URL}/{META_INSTAGRAM_ACCOUNT_ID}/media"
            params = {
                'video_url': video_url,
                'caption': caption,
                'media_type': 'REELS',  # or 'IGTV'
                'access_token': META_ACCESS_TOKEN
            }
            
            response = requests.post(container_url, params=params, timeout=60)
            response.raise_for_status()
            container_data = response.json()
            creation_id = container_data.get('id')
            
        else:
            # Image post workflow
            if image_path:
                # Upload image to get URL
                image_url = _upload_image_to_facebook(image_path)
            
            if not image_url:
                return {"status": "error", "message": "Image URL or path required"}
            
            # Create media container for image
            container_url = f"{GRAPH_API_URL}/{META_INSTAGRAM_ACCOUNT_ID}/media"
            params = {
                'image_url': image_url,
                'caption': caption,
                'access_token': META_ACCESS_TOKEN
            }
            
            response = requests.post(container_url, params=params, timeout=30)
            response.raise_for_status()
            container_data = response.json()
            creation_id = container_data.get('id')
        
        # Publish the media
        publish_url = f"{GRAPH_API_URL}/{META_INSTAGRAM_ACCOUNT_ID}/media_publish"
        params = {
            'creation_id': creation_id,
            'access_token': META_ACCESS_TOKEN
        }
        
        response = requests.post(publish_url, params=params, timeout=30)
        response.raise_for_status()
        publish_data = response.json()
        media_id = publish_data.get('id')
        
        # Get the permalink
        permalink_url = f"{GRAPH_API_URL}/{media_id}"
        params = {
            'fields': 'permalink',
            'access_token': META_ACCESS_TOKEN
        }
        
        response = requests.get(permalink_url, params=params, timeout=30)
        response.raise_for_status()
        permalink_data = response.json()
        
        return {
            "status": "success",
            "media_id": media_id,
            "permalink": permalink_data.get('permalink', ''),
            "type": "video" if is_video else "image",
            "caption": caption,
            "message": "Successfully posted to Instagram"
        }
        
    except Exception as e:
        logger.error(f"Error posting to Instagram: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def meta_post_to_facebook(
    message: str,
    link: Optional[str] = None,
    photo_url: Optional[str] = None,
    photo_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Post content to Facebook Page
    
    Args:
        message: Post message text
        link: URL to share (optional)
        photo_url: URL of photo to post (optional)
        photo_path: Local path to photo (optional)
    
    Returns:
        Post creation result with ID and permalink
    """
    try:
        if photo_path:
            # Upload photo from local path
            photo_url = _upload_image_to_facebook(photo_path)
        
        post_url = f"{GRAPH_API_URL}/{META_FACEBOOK_PAGE_ID}/feed"
        params = {
            'message': message,
            'access_token': META_ACCESS_TOKEN
        }
        
        if link:
            params['link'] = link
        if photo_url:
            params['link'] = photo_url  # Facebook uses link for photos too
        
        response = requests.post(post_url, params=params, timeout=30)
        response.raise_for_status()
        post_data = response.json()
        post_id = post_data.get('id')
        
        # Get permalink
        permalink = f"https://www.facebook.com/{META_FACEBOOK_PAGE_ID}/posts/{post_id.split('_')[1]}"
        
        return {
            "status": "success",
            "post_id": post_id,
            "permalink": permalink,
            "message": message,
            "link": link or photo_url,
            "posted_to": "facebook",
            "full_message": f"Successfully posted to Facebook Page"
        }
        
    except Exception as e:
        logger.error(f"Error posting to Facebook: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def meta_post_to_both(
    caption: str,
    image_url: Optional[str] = None,
    image_path: Optional[str] = None,
    link: Optional[str] = None
) -> Dict[str, Any]:
    """
    Post content to both Instagram and Facebook
    
    Args:
        caption: Post caption/message
        image_url: URL of image (optional)
        image_path: Local path to image (optional)
        link: Link to share (optional, for Facebook)
    
    Returns:
        Combined result from both platforms
    """
    results = {
        "instagram": None,
        "facebook": None
    }
    
    # Post to Instagram
    if image_url or image_path:
        results["instagram"] = meta_post_to_instagram(
            caption=caption,
            image_url=image_url,
            image_path=image_path
        )
    
    # Post to Facebook
    fb_message = caption
    if link:
        fb_message += f"\n\n{link}"
    
    results["facebook"] = meta_post_to_facebook(
        message=fb_message,
        link=link,
        photo_url=image_url,
        photo_path=image_path
    )
    
    return {
        "status": "success",
        "results": results,
        "message": "Posted to both platforms"
    }


@mcp.tool()
def meta_get_instagram_insights() -> Dict[str, Any]:
    """
    Get Instagram account insights/analytics
    
    Returns:
        Account insights including reach, impressions, engagement
    """
    try:
        insights_url = f"{GRAPH_API_URL}/{META_INSTAGRAM_ACCOUNT_ID}/insights"
        params = {
            'metric': 'impressions,reach,profile_views,follower_count,engagement',
            'period': 'day',
            'access_token': META_ACCESS_TOKEN
        }
        
        response = requests.get(insights_url, params=params, timeout=30)
        response.raise_for_status()
        insights_data = response.json()
        
        # Parse insights
        metrics = {}
        for item in insights_data.get('data', []):
            metric_name = item.get('name')
            values = item.get('values', [])
            if values:
                metrics[metric_name] = values[-1].get('value', 0)
        
        # Get media insights
        media_url = f"{GRAPH_API_URL}/{META_INSTAGRAM_ACCOUNT_ID}/media"
        params = {
            'fields': 'id,caption,like_count,comments_count,timestamp',
            'limit': 10,
            'access_token': META_ACCESS_TOKEN
        }
        
        response = requests.get(media_url, params=params, timeout=30)
        response.raise_for_status()
        media_data = response.json()
        
        recent_posts = []
        for item in media_data.get('data', []):
            recent_posts.append({
                "id": item.get('id', ''),
                "caption": item.get('caption', '')[:100] + '...' if len(item.get('caption', '')) > 100 else item.get('caption', ''),
                "likes": item.get('like_count', 0),
                "comments": item.get('comments_count', 0),
                "timestamp": item.get('timestamp', '')
            })
        
        return {
            "status": "success",
            "account_metrics": metrics,
            "recent_posts": recent_posts,
            "message": "Instagram insights retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting Instagram insights: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def meta_get_facebook_insights() -> Dict[str, Any]:
    """
    Get Facebook Page insights/analytics
    
    Returns:
        Page insights including reach, engagement, page views
    """
    try:
        insights_url = f"{GRAPH_API_URL}/{META_FACEBOOK_PAGE_ID}/insights"
        params = {
            'metric': 'page_impressions_unique,page_engaged_users,page_post_engagements_unique,page_views_total',
            'period': 'day',
            'access_token': META_ACCESS_TOKEN
        }
        
        response = requests.get(insights_url, params=params, timeout=30)
        response.raise_for_status()
        insights_data = response.json()
        
        # Parse insights
        metrics = {}
        for item in insights_data.get('data', []):
            metric_name = item.get('name')
            values = item.get('values', [])
            if values:
                metrics[metric_name] = values[-1].get('value', 0)
        
        # Get recent posts
        posts_url = f"{GRAPH_API_URL}/{META_FACEBOOK_PAGE_ID}/feed"
        params = {
            'fields': 'message,created_time,likes.summary(true),comments.summary(true),shares',
            'limit': 10,
            'access_token': META_ACCESS_TOKEN
        }
        
        response = requests.get(posts_url, params=params, timeout=30)
        response.raise_for_status()
        posts_data = response.json()
        
        recent_posts = []
        for item in posts_data.get('data', []):
            recent_posts.append({
                "id": item.get('id', ''),
                "message": (item.get('message', '') or '')[:100] + '...' if len(item.get('message', '') or '') > 100 else (item.get('message', '') or ''),
                "created_time": item.get('created_time', ''),
                "likes": item.get('likes', {}).get('summary', {}).get('total_count', 0),
                "comments": item.get('comments', {}).get('summary', {}).get('total_count', 0),
                "shares": item.get('shares', {}).get('count', 0)
            })
        
        return {
            "status": "success",
            "page_metrics": metrics,
            "recent_posts": recent_posts,
            "message": "Facebook Page insights retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting Facebook insights: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def meta_get_comments(media_id: str) -> Dict[str, Any]:
    """
    Get comments for an Instagram media
    
    Args:
        media_id: Instagram media ID
    
    Returns:
        List of comments with details
    """
    try:
        comments_url = f"{GRAPH_API_URL}/{media_id}/comments"
        params = {
            'fields': 'from,message,created_time,like_count',
            'access_token': META_ACCESS_TOKEN
        }
        
        response = requests.get(comments_url, params=params, timeout=30)
        response.raise_for_status()
        comments_data = response.json()
        
        comments = []
        for item in comments_data.get('data', []):
            comments.append({
                "from": item.get('from', {}).get('username', 'Unknown'),
                "message": item.get('message', ''),
                "created_time": item.get('created_time', ''),
                "likes": item.get('like_count', 0)
            })
        
        return {
            "status": "success",
            "media_id": media_id,
            "count": len(comments),
            "comments": comments,
            "message": f"Retrieved {len(comments)} comments"
        }
        
    except Exception as e:
        logger.error(f"Error getting comments: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def meta_reply_to_comment(comment_id: str, message: str) -> Dict[str, Any]:
    """
    Reply to a comment on Instagram
    
    Args:
        comment_id: Comment ID to reply to
        message: Reply message
    
    Returns:
        Reply creation result
    """
    try:
        reply_url = f"{GRAPH_API_URL}/{comment_id}/comments"
        params = {
            'message': message,
            'access_token': META_ACCESS_TOKEN
        }
        
        response = requests.post(reply_url, params=params, timeout=30)
        response.raise_for_status()
        reply_data = response.json()
        
        return {
            "status": "success",
            "comment_id": reply_data.get('id', ''),
            "message": message,
            "full_message": "Successfully replied to comment"
        }
        
    except Exception as e:
        logger.error(f"Error replying to comment: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def _upload_image_to_facebook(image_path: str) -> Optional[str]:
    """
    Upload image to Facebook to get a public URL
    This is a helper function for internal use
    """
    try:
        # Read and encode image
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Upload to Facebook
        upload_url = f"{GRAPH_API_URL}/{META_FACEBOOK_PAGE_ID}/photos"
        params = {
            'access_token': META_ACCESS_TOKEN
        }
        data = {
            'encoded_image': image_data
        }
        
        response = requests.post(upload_url, params=params, data=data, timeout=60)
        response.raise_for_status()
        upload_data = response.json()
        
        return upload_data.get('images', [{}])[0].get('source')
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return None


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
