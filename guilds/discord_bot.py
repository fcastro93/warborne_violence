import discord
from discord.ext import commands
import os
import asyncio
from django.conf import settings
from .models import DiscordBotConfig, Player, Guild


class WarborneBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = False  # Deshabilitar si no es necesario
        intents.presences = False  # Deshabilitar si no es necesario
        
        super().__init__(command_prefix='!violence ', intents=intents)
        self.config = self.get_bot_config()
    
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
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print(f'Bot commands loaded: {[cmd.name for cmd in self.commands]}')
        print(f'Total commands: {len(self.commands)}')
        for cmd in self.commands:
            print(f'Command: {cmd.name} - {cmd.description}')
        await self.update_bot_status(True)
    
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
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Comando no encontrado. Usa `/help` para ver los comandos disponibles.")
        else:
            await ctx.send(f"❌ Error: {str(error)}")
    
    @commands.command(name='buildplayer')
    async def buildplayer(self, ctx, *, player_name):
        """Get a player's loadout link"""
        try:
            player = Player.objects.filter(name__icontains=player_name).first()
            if player:
                loadout_url = f"{self.config.get('base_url')}/guilds/player/{player.id}/loadout/"
                await ctx.send(f"🔗 **{player.name}** - {loadout_url}")
            else:
                await ctx.send(f"❌ No se encontró el jugador '{player_name}'")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name='guildinfo')
    async def guildinfo(self, ctx):
        """Get guild information"""
        try:
            guilds = Guild.objects.filter(is_active=True)
            if guilds.exists():
                guild_info = []
                for guild in guilds:
                    member_count = guild.member_count
                    guild_info.append(f"**{guild.name}** - {member_count} miembros")
                
                await ctx.send(f"🏰 **Guilds Activas:**\n" + "\n".join(guild_info))
            else:
                await ctx.send("❌ No hay guilds activas")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name='playerlist')
    async def playerlist(self, ctx, guild_name=None):
        """List players, optionally filtered by guild"""
        try:
            if guild_name:
                guild = Guild.objects.filter(name__icontains=guild_name).first()
                if guild:
                    players = guild.players.filter(is_active=True)
                    if players.exists():
                        player_list = [f"• {p.name}" for p in players]
                        await ctx.send(f"👥 **Jugadores en {guild.name}:**\n" + "\n".join(player_list))
                    else:
                        await ctx.send(f"❌ No hay jugadores activos en {guild.name}")
                else:
                    await ctx.send(f"❌ No se encontró la guild '{guild_name}'")
            else:
                players = Player.objects.filter(is_active=True)
                if players.exists():
                    player_list = [f"• {p.name}" for p in players[:10]]  # Limit to 10 players
                    await ctx.send(f"👥 **Todos los Jugadores:**\n" + "\n".join(player_list))
                else:
                    await ctx.send("❌ No hay jugadores activos")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name='drifters')
    async def drifters(self, ctx):
        """Get available drifters"""
        try:
            from .models import Drifter
            drifters = Drifter.objects.all()
            if drifters.exists():
                drifter_list = [f"• {d.name}" for d in drifters]
                await ctx.send(f"🎭 **Drifters Disponibles:**\n" + "\n".join(drifter_list))
            else:
                await ctx.send("❌ No hay drifters disponibles")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name='gear')
    async def gear(self, ctx, gear_type=None):
        """Get gear information"""
        try:
            from .models import GearItem
            if gear_type:
                gear_items = GearItem.objects.filter(gear_type__icontains=gear_type)
            else:
                gear_items = GearItem.objects.all()[:10]  # Limit to 10 items
            
            if gear_items.exists():
                gear_list = [f"• {g.name} ({g.get_rarity_display()})" for g in gear_items]
                await ctx.send(f"⚔️ **Gear Items:**\n" + "\n".join(gear_list))
            else:
                await ctx.send("❌ No se encontraron items de gear")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name='help')
    async def help(self, ctx):
        """Show available commands"""
        help_text = """
🤖 **Warborne Bot - Comandos Disponibles:**

**Comandos de Jugadores:**
• `!violence buildplayer <nombre>` - Obtener link del loadout de un jugador
• `!violence playerlist [guild_name]` - Listar jugadores (opcionalmente por guild)

**Comandos de Guild:**
• `!violence guildinfo` - Información de guilds activas

**Comandos de Juego:**
• `!violence drifters` - Listar drifters disponibles
• `!violence gear [tipo]` - Listar items de gear (opcionalmente por tipo)

**Otros:**
• `!violence help` - Mostrar esta ayuda

**Ejemplos:**
• `!violence buildplayer Charfire`
• `!violence playerlist Emberwild`
• `!violence gear weapon`
        """
        await ctx.send(help_text)


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
