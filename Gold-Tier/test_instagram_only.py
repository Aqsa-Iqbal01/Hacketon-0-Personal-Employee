#!/usr/bin/env python3
"""
Instagram Watcher - Quick Test
Tests Instagram watcher action file creation
"""

import sys
from pathlib import Path

# Add scripts folder to path
scripts_path = Path(__file__).parent / 'scripts'
sys.path.insert(0, str(scripts_path))

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from instagram_watcher import InstagramWatcher
from datetime import datetime

print('='*60)
print('  📷 INSTAGRAM WATCHER - QUICK TEST')
print('='*60)

vault_path = Path(__file__).parent / 'Personal AI Employee Vault'

# Test 1: Initialize
print('\n✅ Test 1: Initializing Instagram Watcher...')
try:
    watcher = InstagramWatcher(str(vault_path), check_interval=300)
    print('   ✅ Instagram Watcher initialized successfully!')
except Exception as e:
    print(f'   ❌ Error: {e}')

# Test 2: Create test action files
print('\n✅ Test 2: Creating test action files...')

# Test Comment
comment_item = {
    'type': 'comment',
    'id': 'test_comment_001',
    'media_id': 'media_123',
    'text': 'Great product! How much does it cost?',
    'timestamp': datetime.now().isoformat(),
    'username': 'customer_user',
    'like_count': 5,
    'media_caption': 'New product launch',
    'media_permalink': 'https://instagram.com/p/test123',
    'priority': 'high'
}

print('   📝 Creating comment action file...')
comment_file = watcher.create_action_file(comment_item)
print(f'   ✅ Created: {comment_file.name}')

# Test Mention
mention_item = {
    'type': 'mention',
    'id': 'test_mention_002',
    'media_id': 'media_456',
    'text': '@yourbusiness I need help with my order!',
    'timestamp': datetime.now().isoformat(),
    'username': 'urgent_customer',
    'like_count': 0,
    'priority': 'high'
}

print('   📢 Creating mention action file...')
mention_file = watcher.create_action_file(mention_item)
print(f'   ✅ Created: {mention_file.name}')

# Test Story Reply
story_item = {
    'type': 'story_reply',
    'id': 'test_story_003',
    'story_id': 'story_789',
    'text': 'Is this available?',
    'timestamp': datetime.now().isoformat(),
    'story_expires': '2026-03-08T23:59:59Z',
    'priority': 'high'
}

print('   📖 Creating story reply action file...')
story_file = watcher.create_action_file(story_item)
print(f'   ✅ Created: {story_file.name}')

# Test Hashtag
hashtag_item = {
    'type': 'hashtag',
    'id': 'test_hashtag_004',
    'hashtag': '#yourbusiness',
    'text': 'Post using branded hashtag',
    'timestamp': datetime.now().isoformat(),
    'priority': 'normal'
}

print('   #️⃣ Creating hashtag action file...')
hashtag_file = watcher.create_action_file(hashtag_item)
print(f'   ✅ Created: {hashtag_file.name}')

# Verify all files
print('\n' + '='*60)
print('  📁 VERIFYING CREATED FILES')
print('='*60)

files_created = [comment_file, mention_file, story_file, hashtag_file]
for file in files_created:
    if file.exists():
        print(f'   ✅ {file.name}')
    else:
        print(f'   ❌ {file.name} - NOT FOUND')

print('\n' + '='*60)
print('  ✅ INSTAGRAM WATCHER TEST COMPLETE!')
print('='*60)
