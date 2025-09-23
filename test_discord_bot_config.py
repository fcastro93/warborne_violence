#!/usr/bin/env python3
"""
Test script for Discord Bot Configuration API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_discord_bot_config():
    """Test the Discord bot configuration endpoints"""
    
    print("🤖 Testing Discord Bot Configuration API...")
    
    # Test GET endpoint
    print("\n1. Testing GET /api/discord-bot-config/")
    try:
        response = requests.get(f"{BASE_URL}/api/discord-bot-config/")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Configuration retrieved successfully!")
            print(f"Bot Name: {data.get('name', 'N/A')}")
            print(f"Active: {data.get('is_active', False)}")
            print(f"Online: {data.get('is_online', False)}")
            print(f"Command Prefix: {data.get('command_prefix', 'N/A')}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test POST endpoint (update)
    print("\n2. Testing POST /api/discord-bot-config/update/")
    try:
        update_data = {
            "name": "Warborne Bot (Updated)",
            "is_active": True,
            "command_prefix": "!",
            "base_url": "https://violenceguild.duckdns.org",
            "general_channel_id": 123456789,
            "event_announcements_channel_id": 987654321,
            "violence_bot_channel_id": 456789123,
            "can_manage_messages": True,
            "can_embed_links": True,
            "can_attach_files": True,
            "can_read_message_history": True,
            "can_use_external_emojis": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/discord-bot-config/update/",
            json=update_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Configuration updated successfully!")
            print(f"Message: {data.get('message', 'N/A')}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test connection test endpoint
    print("\n3. Testing POST /api/discord-bot-config/test/")
    try:
        response = requests.post(f"{BASE_URL}/api/discord-bot-config/test/")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Connection test completed!")
            print(f"Message: {data.get('message', 'N/A')}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print("\n🎉 Discord Bot Configuration API test completed!")

if __name__ == "__main__":
    test_discord_bot_config()
