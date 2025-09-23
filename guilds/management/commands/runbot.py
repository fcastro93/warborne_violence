"""
Django management command to run the Discord bot
"""

from django.core.management.base import BaseCommand
from guilds.discord_bot import WarborneBot

class Command(BaseCommand):
    help = 'Run the Discord bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Starting Discord Bot...'))
        bot = WarborneBot()
        bot.run()
