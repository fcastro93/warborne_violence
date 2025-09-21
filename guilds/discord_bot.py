import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from django.conf import settings
from .models import DiscordBotConfig, Player, Guild

class WarborneBot(commands.Bot):
    def __init__(self):
        # Get config first
        self.config = self.get_bot_config()
        
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = False
        intents.presences = False
        
        # Initialize bot with correct prefix
        super().__init__(command_prefix=self.config.get('command_prefix', '!'), intents=intents)
        
        # Register commands after initialization
        self.load_commands()
    
    def load_commands(self):
        """Load custom commands"""
        from asgiref.sync import sync_to_async
        
        # ---- DB helpers (sync) wrapped for async use ----
        @sync_to_async
        def _find_player_by_name(q: str):
            return Player.objects.filter(in_game_name__icontains=q).first()

        @sync_to_async
        def _get_active_guilds():
            # Force evaluation to detach from ORM before returning to async world
            return list(Guild.objects.filter(is_active=True))

        @self.command(name="ping")
        async def ping_command(ctx):
            """Simple ping command"""
            print(f"🔥 PING COMMAND CALLED by {ctx.author.name}")
            await ctx.send("🏓 Pong!")
        
        @self.command(name="buildplayer")
        async def buildplayer(ctx, *, player_name):
            """Get a player's loadout link"""
            print(f"🔥 DEBUG: buildplayer command called by {ctx.author.name} with {player_name}")
            try:
                player = await _find_player_by_name(player_name)   # <-- await the wrapped call
                if player:
                    base_url = self.config.get('base_url', 'http://127.0.0.1:8000')
                    loadout_url = f"{base_url}/guilds/player/{player.id}/loadout/"
                    await ctx.send(f"🔗 **{player.in_game_name}** - {loadout_url}")
                else:
                    await ctx.send(f"❌ No se encontró el jugador '{player_name}'")
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
        
        @self.command(name="guildinfo")
        async def guildinfo(ctx):
            """Get guild information"""
            print(f"🔥 DEBUG: guildinfo command called by {ctx.author.name}")
            try:
                guilds = await _get_active_guilds()                # <-- await the wrapped call
                if guilds:
                    lines = [f"**{g.name}** - {g.member_count} miembros" for g in guilds]
                    await ctx.send("🏰 **Guilds Activas:**\n" + "\n".join(lines))
                else:
                    await ctx.send("❌ No hay guilds activas")
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print('🤖 ¡Hola! Warborne Bot está listo para la acción!')
        
        # Commands are automatically loaded
        print(f'✅ Bot ready with {len(self.commands)} commands')
        for cmd in self.commands:
            print(f'   - !{cmd.name}: {cmd.description}')
        
        # Send hello message to all guilds
        for guild in self.guilds:
            # Find a general channel or first available text channel
            general_channel = None
            for channel in guild.text_channels:
                if channel.name in ['general', 'chat', 'bienvenida', 'welcome']:
                    general_channel = channel
                    break
            
            if not general_channel:
                general_channel = guild.text_channels[0] if guild.text_channels else None
            
            if general_channel:
                try:
                    await general_channel.send("🤖 ¡Hola! Warborne Bot está listo para la acción! Usa `!help` para ver los comandos disponibles.")
                except Exception as e:
                    print(f"No se pudo enviar mensaje a {guild.name}: {e}")
            
        await self.update_bot_status(True)
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Comando no encontrado. Usa `!help` para ver los comandos disponibles.")
        else:
            await ctx.send(f"❌ Error: {str(error)}")
    
    def get_bot_config(self):
        """Get bot configuration from database or environment variables"""
        try:
            config = DiscordBotConfig.objects.first()
            if config:
                return {
                    'token': config.bot_token or os.getenv('DISCORD_BOT_TOKEN'),
                    'client_id': config.client_id or os.getenv('DISCORD_CLIENT_ID'),
                    'client_secret': config.client_secret or os.getenv('DISCORD_CLIENT_SECRET'),
                    'base_url': config.base_url or os.getenv('BASE_URL', 'http://127.0.0.1:8000'),
                    'is_active': config.is_active,
                    'command_prefix': config.command_prefix,
                }
        except Exception as e:
            print(f"Error getting bot config: {e}")
        
        # Fallback to environment variables
        return {
            'token': os.getenv('DISCORD_BOT_TOKEN'),
            'client_id': os.getenv('DISCORD_CLIENT_ID'),
            'client_secret': os.getenv('DISCORD_CLIENT_SECRET'),
            'base_url': os.getenv('BASE_URL', 'http://127.0.0.1:8000'),
            'is_active': True,
            'command_prefix': '/',
        }
    
    async def update_bot_status(self, is_online):
        """Update bot status in database"""
        try:
            from asgiref.sync import sync_to_async
            from django.utils import timezone
            
            @sync_to_async
            def update_status():
                config = DiscordBotConfig.objects.first()
                if config:
                    config.is_online = is_online
                    if is_online:
                        config.last_heartbeat = timezone.now()
                    config.save()
                return config
            
            await update_status()
        except Exception as e:
            print(f"Error updating bot status: {e}")
    


def run_bot():
    """Run the Discord bot"""
    try:
        # Setup Django
        import django
        from django.conf import settings
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne.settings')
            django.setup()
        
        # Get bot configuration
        config = DiscordBotConfig.objects.first()
        if not config:
            print("❌ No bot configuration found. Please create one in Django Admin.")
            return
        
        if not config.is_active:
            print("❌ Bot is not active. Please activate it in Django Admin.")
            return
        
        # Get token from config or environment
        token = config.bot_token or os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("❌ No bot token found. Please set DISCORD_BOT_TOKEN environment variable.")
            return
        
        # Create and run bot
        bot = WarborneBot()
        bot.run(token)
        
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        # Update error in database
        try:
            config = DiscordBotConfig.objects.first()
            if config:
                config.error_message = str(e)
                config.is_online = False
                config.save()
        except:
            pass
