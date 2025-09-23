"""
Django management command to run the Discord bot
"""

import os
import asyncio
from django.core.management.base import BaseCommand
from guilds.discord_bot import WarborneBot

class Command(BaseCommand):
    help = 'Run the Discord bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Starting Discord Bot...'))
        bot = WarborneBot()
        asyncio.run(bot.start(os.getenv('DISCORD_BOT_TOKEN')))
