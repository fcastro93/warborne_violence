#!/usr/bin/env python3
"""
Test script for event publishing integration
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_event_publishing():
    """Test the event publishing functionality"""
    
    print("📢 Testing Event Publishing Integration...")
    
    # Test publishing event ID 7 (from the curl command)
    print("\n1. Testing POST /api/events/7/publish/")
    try:
        response = requests.post(
            f"{BASE_URL}/api/events/7/publish/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': 'niglF01feQh3oX7EagUo9j7aRH30XMhq'
            }
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Event publish request successful!")
            print(f"Message: {data.get('message', 'N/A')}")
            
            # Check if command file was created
            import os
            if os.path.exists("bot_commands.json"):
                print("✅ Bot command file created!")
                with open("bot_commands.json", 'r') as f:
                    command = json.load(f)
                print(f"Command: {command.get('command', 'N/A')}")
                print(f"Event Title: {command.get('data', {}).get('title', 'N/A')}")
            else:
                print("❌ Bot command file not created")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print("\n🎉 Event publishing test completed!")
    print("\nNote: The Discord bot needs to be running to actually post the announcement.")
    print("The bot will check for commands every 2 seconds and process them.")

if __name__ == "__main__":
    test_event_publishing()
