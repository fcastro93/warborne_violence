from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Create Discord bot configuration from environment variables'

    def handle(self, *args, **options):
        from guilds.models import DiscordBotConfig
        
        # Check if config already exists
        if DiscordBotConfig.objects.exists():
            self.stdout.write(
                self.style.WARNING('Discord bot configuration already exists.')
            )
            return
        
        # Create new configuration
        config = DiscordBotConfig.objects.create(
            name="Warborne Bot",
            is_active=False,  # Start as inactive
            bot_token=os.getenv('DISCORD_BOT_TOKEN', ''),
            client_id=os.getenv('DISCORD_CLIENT_ID', ''),
            client_secret=os.getenv('DISCORD_CLIENT_SECRET', ''),
            base_url=os.getenv('BASE_URL', 'http://127.0.0.1:8000'),
            command_prefix='/',
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created Discord bot configuration: {config.name}')
        )
        
        # Display configuration details
        self.stdout.write(f'Bot Name: {config.name}')
        self.stdout.write(f'Active: {config.is_active}')
        self.stdout.write(f'Client ID: {config.client_id}')
        self.stdout.write(f'Token: {"***" + config.bot_token[-4:] if config.bot_token else "Not set"}')
        self.stdout.write(f'Base URL: {config.base_url}')
        
        self.stdout.write(
            self.style.WARNING('Remember to activate the bot in Django Admin after setting up environment variables.')
        )
