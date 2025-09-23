#!/usr/bin/env python3
"""
Discord Bot Startup Script
This script starts the Discord bot process
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_production')
django.setup()

# Import and run the bot
from guilds.discord_bot import WarborneBot

if __name__ == "__main__":
    print("🤖 Starting Discord Bot...")
    bot = WarborneBot()
    bot.run()
