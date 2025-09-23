"""
Communication module between Django API and Discord bot
"""
import json
import os
import time
from typing import Dict, Any, Optional

# File path for bot communication
BOT_COMMUNICATION_FILE = "bot_commands.json"

def send_bot_command(command_type: str, data: Dict[str, Any]) -> bool:
    """
    Send a command to the Discord bot via file-based communication
    
    Args:
        command_type: Type of command (e.g., 'publish_event')
        data: Command data
    
    Returns:
        bool: True if command was sent successfully
    """
    try:
        command = {
            'command': command_type,
            'data': data,
            'timestamp': time.time(),
            'processed': False
        }
        
        # Write command to file
        with open(BOT_COMMUNICATION_FILE, 'w') as f:
            json.dump(command, f, indent=2)
        
        print(f"✅ Bot command sent: {command_type} to {BOT_COMMUNICATION_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error sending bot command: {e}")
        return False

def get_bot_command() -> Optional[Dict[str, Any]]:
    """
    Get the latest bot command from the communication file
    
    Returns:
        Dict with command data or None if no command
    """
    try:
        if not os.path.exists(BOT_COMMUNICATION_FILE):
            return None
        
        with open(BOT_COMMUNICATION_FILE, 'r') as f:
            command = json.load(f)
        
        return command
    except Exception as e:
        print(f"Error reading bot command: {e}")
        return None

def mark_command_processed() -> bool:
    """
    Mark the current command as processed
    
    Returns:
        bool: True if marked successfully
    """
    try:
        if not os.path.exists(BOT_COMMUNICATION_FILE):
            return False
        
        with open(BOT_COMMUNICATION_FILE, 'r') as f:
            command = json.load(f)
        
        command['processed'] = True
        
        with open(BOT_COMMUNICATION_FILE, 'w') as f:
            json.dump(command, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error marking command as processed: {e}")
        return False

def cleanup_old_commands(max_age_seconds: int = 300) -> None:
    """
    Clean up old processed commands
    
    Args:
        max_age_seconds: Maximum age of commands to keep (default 5 minutes)
    """
    try:
        if not os.path.exists(BOT_COMMUNICATION_FILE):
            return
        
        with open(BOT_COMMUNICATION_FILE, 'r') as f:
            command = json.load(f)
        
        # Check if command is old and processed
        if (command.get('processed', False) and 
            time.time() - command.get('timestamp', 0) > max_age_seconds):
            os.remove(BOT_COMMUNICATION_FILE)
    except Exception as e:
        print(f"Error cleaning up old commands: {e}")
