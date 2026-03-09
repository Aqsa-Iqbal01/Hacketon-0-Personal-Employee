#!/usr/bin/env python3
"""
Social Media Watchers Test Script
Tests Facebook and Twitter watchers to verify they work correctly
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add scripts to path
scripts_path = Path(__file__).parent
sys.path.insert(0, str(scripts_path / 'scripts'))

def test_environment_variables():
    """Test if all required environment variables are set"""
    print("\n" + "="*60)
    print("  🔧 TESTING ENVIRONMENT VARIABLES")
    print("="*60)
    
    required_vars = {
        'Facebook/Meta': [
            'META_ACCESS_TOKEN',
            'META_FACEBOOK_PAGE_ID'
        ],
        'Twitter': [
            'TWITTER_BEARER_TOKEN',
            'TWITTER_USER_ID'
        ]
    }
    
    all_set = True
    
    for category, vars_list in required_vars.items():
        print(f"\n📌 {category}:")
        for var in vars_list:
            value = os.getenv(var, '')
            if value and value != f'your_{var.lower()}_here':
                print(f"  ✅ {var}: Set ({len(value)} chars)")
            else:
                print(f"  ❌ {var}: NOT SET or placeholder value")
                all_set = False
    
    print("\n" + "="*60)
    
    return all_set


def test_facebook_connection():
    """Test Facebook Graph API connection"""
    print("\n" + "="*60)
    print("  📘 TESTING FACEBOOK CONNECTION")
    print("="*60)
    
    access_token = os.getenv('META_ACCESS_TOKEN', '')
    page_id = os.getenv('META_FACEBOOK_PAGE_ID', '')
    
    if not access_token or not page_id:
        print("  ❌ Facebook credentials not configured")
        return False
    
    try:
        import requests
        
        # Test page info
        graph_api_version = 'v18.0'
        url = f'https://graph.facebook.com/{graph_api_version}/{page_id}'
        params = {
            'access_token': access_token,
            'fields': 'name,followers_count,likes'
        }
        
        print(f"  📡 Connecting to Facebook Graph API...")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Connected successfully!")
            print(f"     Page Name: {data.get('name', 'Unknown')}")
            print(f"     Followers: {data.get('followers_count', 0):,}")
            print(f"     Likes: {data.get('likes', 0):,}")
            return True
        else:
            print(f"  ❌ Connection failed: {response.status_code}")
            print(f"     Error: {response.json().get('error', {}).get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_twitter_connection():
    """Test Twitter API v2 connection"""
    print("\n" + "="*60)
    print("  🐦 TESTING TWITTER CONNECTION")
    print("="*60)
    
    bearer_token = os.getenv('TWITTER_BEARER_TOKEN', '')
    user_id = os.getenv('TWITTER_USER_ID', '')
    
    if not bearer_token or not user_id:
        print("  ❌ Twitter credentials not configured")
        return False
    
    try:
        import requests
        
        # Test user info
        url = f'https://api.twitter.com/2/users/{user_id}'
        headers = {
            'Authorization': f'Bearer {bearer_token}'
        }
        params = {
            'user.fields': 'name,username,description,public_metrics,verified'
        }
        
        print(f"  📡 Connecting to Twitter API v2...")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            user = data.get('data', {})
            print(f"  ✅ Connected successfully!")
            print(f"     Name: {user.get('name', 'Unknown')}")
            print(f"     Username: @{user.get('username', 'Unknown')}")
            print(f"     Followers: {user.get('public_metrics', {}).get('followers_count', 0):,}")
            print(f"     Following: {user.get('public_metrics', {}).get('following_count', 0):,}")
            print(f"     Verified: {'Yes ✓' if user.get('verified') else 'No'}")
            return True
        else:
            print(f"  ❌ Connection failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"     Error: {error_data.get('title', 'Unknown error')}")
                print(f"     Detail: {error_data.get('detail', 'No details')}")
            except:
                print(f"     Error: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_facebook_watcher():
    """Test Facebook Watcher functionality"""
    print("\n" + "="*60)
    print("  📘 TESTING FACEBOOK WATCHER")
    print("="*60)
    
    try:
        from scripts.facebook_watcher import FacebookWatcher
        
        vault_path = Path(__file__).parent / 'Personal AI Employee Vault'
        
        print(f"  📁 Vault Path: {vault_path}")
        print(f"  ⏱️  Check Interval: 60 seconds (test mode)")
        
        watcher = FacebookWatcher(str(vault_path), check_interval=60)
        
        print(f"  ✅ Facebook Watcher initialized")
        
        # Test check_for_updates
        print(f"  🔍 Checking for updates...")
        items = watcher.check_for_updates()
        
        if items:
            print(f"  ✅ Found {len(items)} new items:")
            for item in items[:5]:  # Show first 5
                print(f"     - {item['type']}: {item.get('from', 'Unknown')[:50]}")
        else:
            print(f"  ℹ️  No new activity (this is normal if nothing new)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_twitter_watcher():
    """Test Twitter Watcher functionality"""
    print("\n" + "="*60)
    print("  🐦 TESTING TWITTER WATCHER")
    print("="*60)
    
    try:
        from scripts.twitter_watcher import TwitterWatcher
        
        vault_path = Path(__file__).parent / 'Personal AI Employee Vault'
        
        print(f"  📁 Vault Path: {vault_path}")
        print(f"  ⏱️  Check Interval: 60 seconds (test mode)")
        
        watcher = TwitterWatcher(str(vault_path), check_interval=60)
        
        print(f"  ✅ Twitter Watcher initialized")
        
        # Test check_for_updates
        print(f"  🔍 Checking for updates...")
        items = watcher.check_for_updates()
        
        if items:
            print(f"  ✅ Found {len(items)} new items:")
            for item in items[:5]:  # Show first 5
                print(f"     - {item['type']}: @{item.get('author_username', 'Unknown')[:50]}")
        else:
            print(f"  ℹ️  No new activity (this is normal if nothing new)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_instagram_watcher():
    """Test Instagram Watcher functionality"""
    print("\n" + "="*60)
    print("  📷 TESTING INSTAGRAM WATCHER")
    print("="*60)
    
    try:
        from scripts.instagram_watcher import InstagramWatcher
        
        vault_path = Path(__file__).parent / 'Personal AI Employee Vault'
        
        print(f"  📁 Vault Path: {vault_path}")
        print(f"  ⏱️  Check Interval: 60 seconds (test mode)")
        
        watcher = InstagramWatcher(str(vault_path), check_interval=60)
        
        print(f"  ✅ Instagram Watcher initialized")
        
        # Test check_for_updates
        print(f"  🔍 Checking for updates...")
        items = watcher.check_for_updates()
        
        if items:
            print(f"  ✅ Found {len(items)} new items:")
            for item in items[:5]:  # Show first 5
                print(f"     - {item['type']}: @{item.get('username', 'Unknown')[:50]}")
        else:
            print(f"  ℹ️  No new activity (this is normal if nothing new)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_action_file_creation():
    """Test action file creation in Needs_Action folder"""
    print("\n" + "="*60)
    print("  📝 TESTING ACTION FILE CREATION")
    print("="*60)
    
    try:
        from scripts.facebook_watcher import FacebookWatcher
        from scripts.twitter_watcher import TwitterWatcher
        from scripts.instagram_watcher import InstagramWatcher
        from datetime import datetime

        vault_path = Path(__file__).parent / 'Personal AI Employee Vault'
        needs_action_path = vault_path / 'Needs_Action'

        # Ensure folder exists
        needs_action_path.mkdir(parents=True, exist_ok=True)

        # Test Facebook action file
        print(f"  📘 Creating test Facebook action file...")
        fb_watcher = FacebookWatcher(str(vault_path), check_interval=300)
        test_fb_item = {
            'type': 'post',
            'id': 'test_post_123',
            'message': 'This is a test Facebook post for testing purposes',
            'created_time': datetime.now().isoformat(),
            'from': 'Test User',
            'permalink': 'https://facebook.com/test',
            'likes': 10,
            'comments': 5,
            'shares': 2,
            'priority': 'normal'
        }
        fb_file = fb_watcher.create_action_file(test_fb_item)
        print(f"  ✅ Facebook action file created: {fb_file.name}")

        # Test Twitter action file
        print(f"  🐦 Creating test Twitter action file...")
        twitter_watcher = TwitterWatcher(str(vault_path), check_interval=300)
        test_twitter_item = {
            'type': 'mention',
            'id': 'test_tweet_456',
            'text': 'This is a test Twitter mention for testing purposes',
            'created_at': datetime.now().isoformat(),
            'author_username': 'testuser',
            'author_name': 'Test User',
            'author_verified': False,
            'retweets': 5,
            'likes': 20,
            'replies': 3,
            'priority': 'normal'
        }
        twitter_file = twitter_watcher.create_action_file(test_twitter_item)
        print(f"  ✅ Twitter action file created: {twitter_file.name}")

        # Test Instagram action file
        print(f"  📷 Creating test Instagram action file...")
        instagram_watcher = InstagramWatcher(str(vault_path), check_interval=300)
        test_instagram_item = {
            'type': 'comment',
            'id': 'test_ig_comment_789',
            'media_id': 'test_media_001',
            'text': 'This is a test Instagram comment for testing purposes',
            'timestamp': datetime.now().isoformat(),
            'username': 'test_instagram_user',
            'like_count': 15,
            'media_caption': 'Test post caption',
            'media_permalink': 'https://instagram.com/p/test',
            'priority': 'normal'
        }
        instagram_file = instagram_watcher.create_action_file(test_instagram_item)
        print(f"  ✅ Instagram action file created: {instagram_file.name}")

        # Verify files exist
        print(f"\n  📁 Checking created files...")
        if fb_file.exists():
            print(f"     ✅ Facebook file exists: {fb_file.name}")
        else:
            print(f"     ❌ Facebook file not found")

        if twitter_file.exists():
            print(f"     ✅ Twitter file exists: {twitter_file.name}")
        else:
            print(f"     ❌ Twitter file not found")

        if instagram_file.exists():
            print(f"     ✅ Instagram file exists: {instagram_file.name}")
        else:
            print(f"     ❌ Instagram file not found")

        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("  🧪 SOCIAL MEDIA WATCHERS TEST SUITE")
    print("  Testing Facebook, Twitter & Instagram Watchers")
    print("="*70)

    results = {
        'Environment Variables': False,
        'Facebook Connection': False,
        'Twitter Connection': False,
        'Instagram Connection': False,
        'Facebook Watcher': False,
        'Twitter Watcher': False,
        'Instagram Watcher': False,
        'Action File Creation': False
    }

    # Test 1: Environment Variables
    results['Environment Variables'] = test_environment_variables()

    # Test 2: Facebook Connection
    if os.getenv('META_ACCESS_TOKEN') and os.getenv('META_FACEBOOK_PAGE_ID'):
        results['Facebook Connection'] = test_facebook_connection()
    else:
        print("\n⚠️  Skipping Facebook connection test (credentials not set)")

    # Test 3: Twitter Connection
    if os.getenv('TWITTER_BEARER_TOKEN') and os.getenv('TWITTER_USER_ID'):
        results['Twitter Connection'] = test_twitter_connection()
    else:
        print("\n⚠️  Skipping Twitter connection test (credentials not set)")

    # Test 4: Instagram Connection
    if os.getenv('META_ACCESS_TOKEN') and os.getenv('META_INSTAGRAM_ACCOUNT_ID'):
        results['Instagram Connection'] = test_instagram_watcher()
    else:
        print("\n⚠️  Skipping Instagram connection test (credentials not set)")

    # Test 5: Facebook Watcher
    if os.getenv('META_ACCESS_TOKEN') and os.getenv('META_FACEBOOK_PAGE_ID'):
        results['Facebook Watcher'] = test_facebook_watcher()
    else:
        print("\n⚠️  Skipping Facebook Watcher test (credentials not set)")

    # Test 6: Twitter Watcher
    if os.getenv('TWITTER_BEARER_TOKEN') and os.getenv('TWITTER_USER_ID'):
        results['Twitter Watcher'] = test_twitter_watcher()
    else:
        print("\n⚠️  Skipping Twitter Watcher test (credentials not set)")

    # Test 7: Instagram Watcher
    if os.getenv('META_ACCESS_TOKEN') and os.getenv('META_INSTAGRAM_ACCOUNT_ID'):
        results['Instagram Watcher'] = test_instagram_watcher()
    else:
        print("\n⚠️  Skipping Instagram Watcher test (credentials not set)")

    # Test 8: Action File Creation
    results['Action File Creation'] = test_action_file_creation()

    # Summary
    print("\n" + "="*70)
    print("  📊 TEST SUMMARY")
    print("="*70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print("\n" + "="*70)
    print(f"  Total: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print(f"\n  🎉 ALL TESTS PASSED! Watchers are ready to use!")
    else:
        print(f"\n  ⚠️  Some tests failed. Check the errors above.")
        print(f"  💡 Tip: Make sure API credentials are set in .env file")

    print("="*70 + "\n")


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user\n")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
