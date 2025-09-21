import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timezone
from django.conf import settings
from .models import DiscordBotConfig, Player, Guild, Event, EventParticipant
from asgiref.sync import sync_to_async


# Global helper functions for database operations
@sync_to_async
def _get_bot_config():
    """Get bot configuration from database"""
    try:
        return DiscordBotConfig.objects.first()
    except DiscordBotConfig.DoesNotExist:
        return None


class CommandMenuView(discord.ui.View):
    """Interactive menu view with command buttons"""
    
    def __init__(self, bot_instance):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.bot_instance = bot_instance
    
    @discord.ui.button(label="🎯 Create Event", style=discord.ButtonStyle.primary, emoji="🎯")
    async def create_event_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to create a new event"""
        await interaction.response.send_modal(CreateEventModal(self.bot_instance))
    
    @discord.ui.button(label="👤 Create Player", style=discord.ButtonStyle.secondary, emoji="👤")
    async def create_player_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to create a new player"""
        # Create a simple modal for player creation
        class CreatePlayerModal(discord.ui.Modal, title="Create Player"):
            def __init__(self, bot_instance):
                super().__init__()
                self.bot_instance = bot_instance
            
            player_name = discord.ui.TextInput(
                label="Player Name",
                placeholder="Enter your in-game name",
                max_length=50,
                required=True
            )
            
            async def on_submit(self, interaction: discord.Interaction):
                # Use the existing createplayer logic
                player_name = self.player_name.value.strip()
                if not player_name:
                    await interaction.response.send_message("❌ Player name cannot be empty.", ephemeral=True)
                    return
                
                # Call the createplayer command logic
                from asgiref.sync import sync_to_async
                
                @sync_to_async
                def _create_player(in_game_name, discord_user_id, discord_name, level=1, faction='none'):
                    from .models import Player
                    
                    # Check if player already exists
                    if Player.objects.filter(in_game_name__iexact=in_game_name).exists():
                        return None, "Ya existe un jugador con ese nombre"
                    
                    # Check if user already has a player
                    if Player.objects.filter(discord_user_id=discord_user_id).exists():
                        return None, "Ya tienes un jugador registrado. Usa !myplayer para ver tu jugador actual."
                    
                    try:
                        player = Player.objects.create(
                            in_game_name=in_game_name,
                            discord_user_id=discord_user_id,
                            discord_name=discord_name,
                            character_level=level,
                            faction=faction
                        )
                        return player, None
                    except Exception as e:
                        return None, f"Error creando jugador: {str(e)}"
                
                player, error = await _create_player(
                    player_name, 
                    interaction.user.id, 
                    str(interaction.user)
                )
                
                if error:
                    await interaction.response.send_message(f"❌ {error}", ephemeral=True)
                else:
                    await interaction.response.send_message(
                        f"✅ ¡Jugador creado exitosamente!\n"
                        f"**Nombre:** {player.in_game_name}\n"
                        f"**Nivel:** {player.character_level}\n"
                        f"**Facción:** {player.get_faction_display()}\n"
                        f"**Link del Loadout:** https://strategic-brena-charfire-afecfd9e.koyeb.app/guilds/player/{player.id}/loadout",
                        ephemeral=True
                    )
        
        await interaction.response.send_modal(CreatePlayerModal(self.bot_instance))
    
    @discord.ui.button(label="👨‍💼 My Player", style=discord.ButtonStyle.secondary, emoji="👨‍💼")
    async def my_player_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to show current player info"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def _get_player_by_discord_user(discord_user_id):
            from .models import Player
            try:
                return Player.objects.get(discord_user_id=discord_user_id)
            except Player.DoesNotExist:
                return None
        
        player = await _get_player_by_discord_user(interaction.user.id)
        
        if player:
            guild_info = ""
            if player.guild:
                guild_info = f"\n**Guild:** {player.guild.name}"
            
            loadout_url = f"https://strategic-brena-charfire-afecfd9e.koyeb.app/guilds/player/{player.id}/loadout"
            
            embed = discord.Embed(
                title=f"👨‍💼 {player.in_game_name}",
                color=0x4a9eff
            )
            embed.add_field(
                name="📊 Player Info",
                value=f"**Nivel:** {player.character_level}\n"
                      f"**Facción:** {player.get_faction_display()}\n"
                      f"{guild_info}\n"
                      f"**Link del Loadout:** {loadout_url}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ No tienes un jugador registrado. Usa el botón 'Create Player' para crear uno.",
                ephemeral=True
            )
    
    @discord.ui.button(label="🔍 Build Player", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def build_player_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to search for a player"""
        # Create a modal for player search
        class SearchPlayerModal(discord.ui.Modal, title="Search Player"):
            def __init__(self, bot_instance):
                super().__init__()
                self.bot_instance = bot_instance
            
            player_name = discord.ui.TextInput(
                label="Player Name",
                placeholder="Enter player name to search",
                max_length=50,
                required=True
            )
            
            async def on_submit(self, interaction: discord.Interaction):
                from asgiref.sync import sync_to_async
                
                @sync_to_async
                def _find_player_by_name(q: str):
                    from .models import Player
                    return Player.objects.filter(in_game_name__icontains=q).first()
                
                player = await _find_player_by_name(self.player_name.value)
                
                if player:
                    guild_info = ""
                    if player.guild:
                        guild_info = f"\n**Guild:** {player.guild.name}"
                    
                    loadout_url = f"https://strategic-brena-charfire-afecfd9e.koyeb.app/guilds/player/{player.id}/loadout"
                    
                    embed = discord.Embed(
                        title=f"🔍 {player.in_game_name}",
                        color=0x4a9eff
                    )
                    embed.add_field(
                        name="📊 Player Info",
                        value=f"**Nivel:** {player.character_level}\n"
                              f"**Facción:** {player.get_faction_display()}\n"
                              f"{guild_info}\n"
                              f"**Link del Loadout:** {loadout_url}",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(
                        f"❌ No se encontró un jugador con el nombre '{self.player_name.value}'",
                        ephemeral=True
                    )
        
        await interaction.response.send_modal(SearchPlayerModal(self.bot_instance))
    
    @discord.ui.button(label="🏰 Guild Info", style=discord.ButtonStyle.secondary, emoji="🏰")
    async def guild_info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to show guild information"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def _get_active_guilds():
            from .models import Guild
            return list(Guild.objects.filter(is_active=True))
        
        guilds = await _get_active_guilds()
        
        if guilds:
            embed = discord.Embed(
                title="🏰 Guilds Activas",
                color=0x4a9eff
            )
            
            for guild in guilds:
                member_count = guild.players.count()
                embed.add_field(
                    name=guild.name,
                    value=f"**Miembros:** {member_count}\n"
                          f"**Descripción:** {guild.description or 'Sin descripción'}",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ No hay guilds activas disponibles.",
                ephemeral=True
            )
    
    @discord.ui.button(label="🏓 Ping", style=discord.ButtonStyle.success, emoji="🏓")
    async def ping_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to test bot ping"""
        latency = round(self.bot_instance.latency * 1000)
        await interaction.response.send_message(
            f"🏓 Pong! Latencia: {latency}ms",
            ephemeral=True
        )


class CreateEventModal(discord.ui.Modal, title="Create Guild Event (Date: YYYY-MM-DD HH:MM)"):
    """Modal for creating guild events"""
    def __init__(self, bot_instance):
        super().__init__()
        self.bot_instance = bot_instance
    
    title_input = discord.ui.TextInput(
        label="Event Title",
        placeholder="e.g., Guild War vs Yellows",
        max_length=100,
        required=True
    )
    
    description_input = discord.ui.TextInput(
        label="Event Description",
        placeholder="Describe what this event is about...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    datetime_input = discord.ui.TextInput(
        label="Event Date & Time",
        placeholder="Format: YYYY-MM-DD HH:MM (24h format)",
        max_length=20,
        required=True
    )
    
    timezone_input = discord.ui.TextInput(
        label="Timezone",
        placeholder="UTC, EST, PST, CST, MST, CET, GMT, JST, AEST",
        default="UTC",
        max_length=10,
        required=True
    )
    
    max_participants_input = discord.ui.TextInput(
        label="Max Participants (optional)",
        placeholder="Leave empty for unlimited",
        max_length=3,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission"""
        try:
            # Parse datetime with timezone
            try:
                # Parse the datetime string
                event_datetime = datetime.strptime(self.datetime_input.value, "%Y-%m-%d %H:%M")
                
                # Get timezone
                timezone_str = self.timezone_input.value.strip().upper()
                
                # For now, just store the timezone string and use UTC for datetime
                # This ensures the bot works even if timezone libraries aren't available
                event_datetime = event_datetime.replace(tzinfo=timezone.utc)
                
                # Validate timezone string (basic validation)
                valid_timezones = ['UTC', 'EST', 'PST', 'CST', 'MST', 'CET', 'GMT', 'JST', 'AEST', 'PDT', 'EDT', 'CDT', 'MDT']
                print(f"DEBUG: Parsed timezone_str: '{timezone_str}'")
                print(f"DEBUG: Valid timezones: {valid_timezones}")
                
                if timezone_str not in valid_timezones:
                    await interaction.response.send_message(
                        f"❌ Invalid timezone '{timezone_str}'. Valid options: UTC, EST, PST, CST, MST, CET, GMT, JST, AEST, PDT, EDT, CDT, MDT",
                        ephemeral=True
                    )
                    return
                
            except ValueError as e:
                await interaction.response.send_message(
                    "❌ Invalid date format. Please use YYYY-MM-DD HH:MM format (e.g., 2025-09-21 09:40).",
                    ephemeral=True
                )
                return
            
            # Validate max participants
            max_participants = None
            if self.max_participants_input.value.strip():
                try:
                    max_participants = int(self.max_participants_input.value)
                    if max_participants <= 0:
                        raise ValueError()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ Max participants must be a positive number.",
                        ephemeral=True
                    )
                    return
            
            # Create event in database
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def create_event():
                event = Event.objects.create(
                    title=self.title_input.value,
                    description=self.description_input.value or "",
                    event_type='other',  # Default type, can be enhanced later
                    created_by_discord_id=interaction.user.id,
                    created_by_discord_name=str(interaction.user),
                    event_datetime=event_datetime,
                    timezone=timezone_str,
                    max_participants=max_participants
                )
                return event
            
            event = await create_event()
            
            # Post event to announcements channel
            await self.post_event_announcement(interaction, event)
            
            # Confirm to user
            await interaction.response.send_message(
                f"✅ **Event created successfully!**\n"
                f"**Title:** {event.title}\n"
                f"**Date:** {event.discord_timestamp}\n"
                f"**Time:** {event.discord_timestamp_relative}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error creating event: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while creating the event. Please try again.",
                ephemeral=True
            )
    
    async def post_event_announcement(self, interaction, event):
        """Post the event announcement to the designated channel"""
        try:
            # Get bot configuration to find channel IDs
            config = await _get_bot_config()
            if not config or not config.event_announcements_channel_id:
                await interaction.followup.send(
                    "❌ Error: Event announcements channel not configured. Please configure it in the admin panel.",
                    ephemeral=True
                )
                return
            
            announcements_channel_id = config.event_announcements_channel_id
            announcements_channel = self.bot_instance.get_channel(announcements_channel_id)
            
            if not announcements_channel:
                print(f"Announcements channel not found: {announcements_channel_id}")
                return
            
            # Create event embed
            embed = discord.Embed(
                title=f"🎯 {event.title}",
                description=event.description or "No description provided.",
                color=0x4a9eff,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="📅 Date & Time",
                value=f"{event.discord_timestamp}\n{event.discord_timestamp_relative}\n**Timezone:** {event.timezone}",
                inline=False
            )
            
            embed.add_field(
                name="👤 Created by",
                value=f"<@{event.created_by_discord_id}>",
                inline=True
            )
            
            if event.max_participants:
                embed.add_field(
                    name="👥 Max Participants",
                    value=str(event.max_participants),
                    inline=True
                )
            
            embed.add_field(
                name="✅ Participants",
                value="0",
                inline=True
            )
            
            embed.set_footer(text="React with ✅ to join this event!")
            
            # Send the announcement
            message = await announcements_channel.send(embed=embed)
            
            # Add reaction
            await message.add_reaction("✅")
            
            # Update event with message info
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def update_event_message():
                event.discord_message_id = message.id
                event.discord_channel_id = announcements_channel_id
                event.save()
            
            await update_event_message()
            
        except Exception as e:
            print(f"Error posting event announcement: {e}")


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
        intents.reactions = True  # Need this for reaction tracking
        
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
        
        @sync_to_async
        def _create_player(in_game_name, discord_user_id, discord_name, level=1, faction='none'):
            """Create a new player with Discord owner"""
            # Check if player already exists
            if Player.objects.filter(in_game_name__iexact=in_game_name).exists():
                return None, "Ya existe un jugador con ese nombre"
            
            # Check if user already has a player
            if Player.objects.filter(discord_user_id=discord_user_id).exists():
                return None, "Ya tienes un jugador registrado. Usa !myplayer para ver tu jugador actual."
            
            try:
                player = Player.objects.create(
                    in_game_name=in_game_name,
                    discord_user_id=discord_user_id,
                    discord_name=discord_name,
                    character_level=level,
                    faction=faction
                )
                return player, None
            except Exception as e:
                return None, f"Error creando jugador: {str(e)}"
        
        @sync_to_async
        def _get_player_by_discord_user(discord_user_id):
            """Get player by Discord user ID"""
            return Player.objects.filter(discord_user_id=discord_user_id).first()

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
        
        @self.command(name="createplayer")
        async def createplayer(ctx, *, player_name=None):
            """Create a new player linked to your Discord account"""
            # Use Discord username as default if no name provided
            if not player_name:
                player_name = ctx.author.name
                
            print(f"🔥 DEBUG: createplayer command called by {ctx.author.name} with {player_name}")
            try:
                # Validate player name
                if len(player_name) < 3 or len(player_name) > 50:
                    await ctx.send("❌ El nombre del jugador debe tener entre 3 y 50 caracteres")
                    return
                
                # Create player
                player, error = await _create_player(
                    in_game_name=player_name,
                    discord_user_id=ctx.author.id,
                    discord_name=str(ctx.author),
                    level=1,
                    faction='none'
                )
                
                if error:
                    await ctx.send(f"❌ {error}")
                else:
                    base_url = self.config.get('base_url', 'http://127.0.0.1:8000')
                    loadout_url = f"{base_url}/guilds/player/{player.id}/loadout/"
                    await ctx.send(f"✅ **¡Jugador creado exitosamente!**\n"
                                 f"**Nombre:** {player.in_game_name}\n"
                                 f"**Nivel:** {player.character_level}\n"
                                 f"**Facción:** {player.get_faction_display()}\n"
                                 f"**Link del Loadout:** {loadout_url}\n"
                                 f"💡 Ahora puedes modificar tu equipamiento desde la página web!")
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
        
        @self.command(name="myplayer")
        async def myplayer(ctx):
            """Show your registered player information"""
            print(f"🔥 DEBUG: myplayer command called by {ctx.author.name}")
            try:
                player = await _get_player_by_discord_user(ctx.author.id)
                if player:
                    base_url = self.config.get('base_url', 'http://127.0.0.1:8000')
                    loadout_url = f"{base_url}/guilds/player/{player.id}/loadout/"
                    
                    guild_info = f"**Guild:** {player.guild.name}" if player.guild else "**Guild:** Sin guild"
                    
                    await ctx.send(f"🎮 **Tu Jugador:**\n"
                                 f"**Nombre:** {player.in_game_name}\n"
                                 f"**Nivel:** {player.character_level}\n"
                                 f"**Facción:** {player.get_faction_display()}\n"
                                 f"{guild_info}\n"
                                 f"**Link del Loadout:** {loadout_url}")
                else:
                    await ctx.send("❌ No tienes un jugador registrado. Usa `!createplayer <nombre>` para crear uno.")
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
        
        @self.command(name="createevent")
        async def createevent(ctx):
            """Create a new guild event using modal"""
            print(f"🔥 DEBUG: createevent command called by {ctx.author.name}")
            
            # Create a simple view with a button that opens the modal
            class EventButton(discord.ui.View):
                def __init__(self, bot_instance):
                    super().__init__(timeout=120)
                    self.bot_instance = bot_instance
                
                @discord.ui.button(label="📅 Create Event", style=discord.ButtonStyle.primary, emoji="🎯")
                async def create_event_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(CreateEventModal(self.bot_instance))
            
            # Send message with button
            embed = discord.Embed(
                title="🎯 Create Guild Event",
                description="Click the button below to create a new guild event!",
                color=0x4a9eff
            )
            embed.add_field(
                name="Event Types",
                value="• Guild War\n• PvP Fight\n• Resource Farming\n• Boss Raid\n• Social Event\n• Training",
                inline=True
            )
            embed.add_field(
                name="Features",
                value="• Automatic timestamps\n• Participant tracking\n• Event announcements\n• Discord integration\n• Timezone support",
                inline=True
            )
            
            view = EventButton(self)
            await ctx.send(embed=embed, view=view)
        
        @self.command(name="menu")
        async def menu(ctx):
            """Show interactive menu with all available commands"""
            embed = discord.Embed(
                title="🎮 Warborne Bot - Command Menu",
                description="Select a command from the menu below:",
                color=0x4a9eff,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="📋 Available Commands",
                value="• 🎯 Create Event\n• 👤 Create Player\n• 👨‍💼 My Player\n• 🔍 Build Player\n• 🏰 Guild Info\n• 🏓 Ping Test",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ How to Use",
                value="Click the buttons below to access each command directly!",
                inline=False
            )
            
            embed.set_footer(text="Warborne Above Ashes - Guild Tools")
            
            view = CommandMenuView(self)
            await ctx.send(embed=embed, view=view)
    
    async def setup_hook(self):
        """Setup hook - no slash commands needed"""
        pass
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print('🤖 ¡Hola! Warborne Bot está listo para la acción!')
        
        # Commands are automatically loaded
        print(f'✅ Bot ready with {len(self.commands)} commands')
        for cmd in self.commands:
            print(f'   - !{cmd.name}: {cmd.description}')
        
        # Start the status monitoring task
        self.status_monitor_task = asyncio.create_task(self.monitor_bot_status())
        
        # Send hello message to all guilds
        config = await _get_bot_config()
        for guild in self.guilds:
            # Use configured general channel if available
            general_channel = None
            if config and config.general_channel_id:
                general_channel = guild.get_channel(config.general_channel_id)
            
            # Fallback to finding a general channel or first available text channel
            if not general_channel:
            for channel in guild.text_channels:
                if channel.name in ['general', 'chat', 'bienvenida', 'welcome']:
                    general_channel = channel
                    break
            
            if not general_channel:
                general_channel = guild.text_channels[0] if guild.text_channels else None
            
            if general_channel:
                try:
                    await general_channel.send("🤖 ¡Hola! Warborne Bot está listo para la acción!\n"
                                              "**Comandos disponibles:**\n"
                                              "`!menu` - 🎮 Menú interactivo con todos los comandos\n"
                                              "`!createevent` - Crear evento de guild\n"
                                              "`!createplayer [nombre]` - Crear tu jugador (usa tu nombre de Discord por defecto)\n"
                                              "`!myplayer` - Ver tu jugador\n"
                                              "`!buildplayer <nombre>` - Ver loadout de jugador\n"
                                              "`!guildinfo` - Información de guilds\n"
                                              "`!ping` - Probar bot")
                except Exception as e:
                    print(f"No se pudo enviar mensaje a {guild.name}: {e}")
            
        await self.update_bot_status(True)
    
    async def monitor_bot_status(self):
        """Monitor bot status and stop if is_online becomes False"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                config = await _get_bot_config()
                if config and not config.is_online:
                    print("🛑 Bot stop requested from admin panel. Shutting down...")
                    await self.close()
                    break
                    
            except asyncio.CancelledError:
                print("📡 Status monitor task cancelled")
                break
            except Exception as e:
                print(f"Error in status monitor: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Comando no encontrado. Comandos disponibles:\n"
                          "`!menu` - 🎮 Menú interactivo con todos los comandos\n"
                          "`!createevent` - Crear evento de guild\n"
                          "`!createplayer [nombre]` - Crear tu jugador\n"
                          "`!myplayer` - Ver tu jugador\n"
                          "`!buildplayer <nombre>` - Ver loadout de jugador\n"
                          "`!guildinfo` - Información de guilds\n"
                          "`!ping` - Probar bot")
        else:
            await ctx.send(f"❌ Error: {str(error)}")
    
    async def on_reaction_add(self, reaction, user):
        """Handle when a user reacts to a message"""
        # Ignore bot reactions
        if user.bot:
            return
        
        # Check if this is an event message
        if reaction.emoji == "✅" and reaction.message.embeds:
            await self.handle_event_reaction(reaction, user, added=True)
    
    async def on_reaction_remove(self, reaction, user):
        """Handle when a user removes a reaction"""
        # Ignore bot reactions
        if user.bot:
            return
        
        # Check if this is an event message
        if reaction.emoji == "✅" and reaction.message.embeds:
            await self.handle_event_reaction(reaction, user, added=False)
    
    async def handle_event_reaction(self, reaction, user, added=True):
        """Handle event reactions (joining/leaving events)"""
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def find_event_by_message():
                return Event.objects.filter(
                    discord_message_id=reaction.message.id,
                    discord_channel_id=reaction.message.channel.id,
                    is_active=True
                ).first()
            
            event = await find_event_by_message()
            
            if not event:
                return  # Not an event message
            
            if added:
                # User is joining the event
                await self.add_event_participant(event, user)
            else:
                # User is leaving the event
                await self.remove_event_participant(event, user)
            
            # Update the embed with new participant count
            await self.update_event_embed(event, reaction.message)
            
        except Exception as e:
            print(f"Error handling event reaction: {e}")
    
    async def add_event_participant(self, event, user):
        """Add a participant to an event"""
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def add_participant():
                # Check if already participating
                existing = EventParticipant.objects.filter(
                    event=event,
                    discord_user_id=user.id
                ).first()
                
                if existing:
                    if existing.is_active:
                        return False  # Already participating
                    else:
                        # Reactivate
                        existing.is_active = True
                        existing.save()
                        return True
                else:
                    # Check if event is full
                    if event.max_participants and event.participant_count >= event.max_participants:
                        return False  # Event is full
                    
                    # Get or create player for this user
                    player = Player.objects.filter(discord_user_id=user.id).first()
                    
                    # Create new participant
                    EventParticipant.objects.create(
                        event=event,
                        discord_user_id=user.id,
                        discord_name=str(user),
                        player=player
                    )
                    return True
            
            success = await add_participant()
            
            if not success:
                # Try to remove the reaction if event is full or already participating
                try:
                    await reaction.remove(user)
                    if event.max_participants and event.participant_count >= event.max_participants:
                        await user.send(f"❌ **{event.title}** is full! ({event.participant_count}/{event.max_participants} participants)")
                    else:
                        await user.send(f"ℹ️ You're already participating in **{event.title}**!")
                except:
                    pass  # Can't send DM, ignore
            
        except Exception as e:
            print(f"Error adding event participant: {e}")
    
    async def remove_event_participant(self, event, user):
        """Remove a participant from an event"""
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def remove_participant():
                participant = EventParticipant.objects.filter(
                    event=event,
                    discord_user_id=user.id,
                    is_active=True
                ).first()
                
                if participant:
                    participant.is_active = False
                    participant.save()
                    return True
                return False
            
            await remove_participant()
            
        except Exception as e:
            print(f"Error removing event participant: {e}")
    
    async def update_event_embed(self, event, message):
        """Update the event embed with current participant count"""
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def get_participants_with_roles():
                participants = EventParticipant.objects.filter(
                    event=event,
                    is_active=True
                ).select_related('player')
                
                participant_data = []
                role_counts = {}
                
                for participant in participants:
                    name = participant.discord_name
                    role = None
                    
                    if participant.player and participant.player.game_role:
                        role = participant.player.get_game_role_display()
                        role_counts[role] = role_counts.get(role, 0) + 1
                    
                    participant_data.append({
                        'name': name,
                        'role': role
                    })
                
                return participant_data, role_counts
            
            participants_data, role_counts = await get_participants_with_roles()
            participants = [p['name'] for p in participants_data]
            
            # Create updated embed
            embed = message.embeds[0]
            
            # Update participant count
            participant_count = len(participants)
            embed.set_field_at(
                len(embed.fields) - 1,  # Last field is participants
                name="✅ Participants",
                value=str(participant_count),
                inline=True
            )
            
            # Add participant list if there are participants
            if participants:
                participant_list = "\n".join([f"• {name}" for name in participants[:10]])  # Show first 10
                if len(participants) > 10:
                    participant_list += f"\n• ... and {len(participants) - 10} more"
                
                # Add or update participant list field
                if len(embed.fields) > 4:  # If participant list field exists
                    embed.set_field_at(
                        len(embed.fields) - 1,
                        name="👥 Participant List",
                        value=participant_list,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="👥 Participant List",
                        value=participant_list,
                        inline=False
                    )
            
            # Add role statistics if there are roles
            if role_counts:
                role_stats = []
                for role, count in role_counts.items():
                    if count > 0:  # Only show roles with participants
                        role_stats.append(f"**{role}**: {count}")
                
                if role_stats:
                    role_stats_text = "\n".join(role_stats)
                    embed.add_field(
                        name="🎯 Role Distribution",
                        value=role_stats_text,
                        inline=True
                    )
            
            # Update the message
            await message.edit(embed=embed)
            
        except Exception as e:
            print(f"Error updating event embed: {e}")
    
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
    
    async def close(self):
        """Override close to clean up monitoring task"""
        if hasattr(self, 'status_monitor_task'):
            self.status_monitor_task.cancel()
            try:
                await self.status_monitor_task
            except asyncio.CancelledError:
                pass
        
        await super().close()
