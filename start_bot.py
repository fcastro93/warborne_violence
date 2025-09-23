#!/usr/bin/env python3
"""
Discord Bot Startup Script
This script starts the Discord bot process
"""

import os
import sys
import django
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_production')
django.setup()

# Import and run the bot
from guilds.discord_bot import WarborneBot

if __name__ == "__main__":
    import asyncio
    print("🤖 Starting Discord Bot...")
    bot = WarborneBot()
    asyncio.run(bot.start(os.getenv('DISCORD_BOT_TOKEN')))
