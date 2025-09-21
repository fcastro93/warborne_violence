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


class CreatePlayerView(discord.ui.View):
    """View with dropdowns for creating a player"""
    
    def __init__(self, bot_instance):
        super().__init__(timeout=300)
        self.bot_instance = bot_instance
        self.player_name = None
        self.selected_faction = None
        self.selected_guild = None
        self.selected_role = None
        
        # Add dropdowns to the view
        self.add_item(self.FactionSelect(self))
        self.add_item(self.RoleSelect(self))
        
        # Load guilds dynamically
        self._load_guilds()
    
    def _load_guilds(self):
        """Load guilds from database and create guild select dropdown"""
        try:
            from .models import Guild
            guilds = Guild.objects.filter(is_active=True)
            
            if guilds.exists():
                guild_options = []
                for guild in guilds:
                    guild_options.append(
                        discord.SelectOption(
                            label=guild.name,
                            value=guild.name,
                            description=f"Members: {guild.players.count()}"
                        )
                    )
                
                guild_select = self.GuildSelect(self)
                guild_select.options = guild_options
                self.add_item(guild_select)
        except Exception as e:
            print(f"Error loading guilds: {e}")
    
    # Faction Select
    class FactionSelect(discord.ui.Select):
        def __init__(self, parent_view):
            self.parent_view = parent_view
            options = [
                discord.SelectOption(label="No Faction", value="none", description="No faction selected"),
                discord.SelectOption(label="Emberwild", value="emberwild", description="Emberwild faction"),
                discord.SelectOption(label="Magnates", value="magnates", description="Magnates faction"),
                discord.SelectOption(label="Ashen", value="ashen", description="Ashen faction"),
                discord.SelectOption(label="Ironcreed", value="ironcreed", description="Ironcreed faction"),
                discord.SelectOption(label="Sirius", value="sirius", description="Sirius faction"),
                discord.SelectOption(label="Shroud", value="shroud", description="Shroud faction"),
            ]
            super().__init__(placeholder="Choose your faction...", options=options, min_values=1, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            self.parent_view.selected_faction = self.values[0]
            await interaction.response.send_message(f"✅ Faction selected: {self.values[0]}", ephemeral=True)
    
    # Guild Select
    class GuildSelect(discord.ui.Select):
        def __init__(self, parent_view):
            self.parent_view = parent_view
            # We'll populate this dynamically
            super().__init__(placeholder="Choose your guild (optional)...", options=[], min_values=0, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            if self.values:
                self.parent_view.selected_guild = self.values[0]
                await interaction.response.send_message(f"✅ Guild selected: {self.values[0]}", ephemeral=True)
            else:
                self.parent_view.selected_guild = None
                await interaction.response.send_message("✅ No guild selected", ephemeral=True)
    
    # Role Select
    class RoleSelect(discord.ui.Select):
        def __init__(self, parent_view):
            self.parent_view = parent_view
            options = [
                discord.SelectOption(label="Ranged DPS", value="ranged_dps", description="Ranged damage dealer"),
                discord.SelectOption(label="Melee DPS", value="melee_dps", description="Melee damage dealer"),
                discord.SelectOption(label="Tank", value="tank", description="Tank role"),
                discord.SelectOption(label="Healer", value="healer", description="Healer role"),
                discord.SelectOption(label="Defensive Tank", value="defensive_tank", description="Defensive tank"),
                discord.SelectOption(label="Offensive Tank", value="offensive_tank", description="Offensive tank"),
                discord.SelectOption(label="Offensive Support", value="offensive_support", description="Offensive support"),
                discord.SelectOption(label="Defensive Support", value="defensive_support", description="Defensive support"),
            ]
            super().__init__(placeholder="Choose your role (optional)...", options=options, min_values=0, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            if self.values:
                self.parent_view.selected_role = self.values[0]
                await interaction.response.send_message(f"✅ Role selected: {self.values[0]}", ephemeral=True)
            else:
                self.parent_view.selected_role = None
                await interaction.response.send_message("✅ No role selected", ephemeral=True)
    
    # Player Name Input Modal
    class PlayerNameModal(discord.ui.Modal, title="Enter Player Name"):
        def __init__(self, parent_view):
            super().__init__()
            self.parent_view = parent_view
        
        player_name = discord.ui.TextInput(
            label="Player Name",
            placeholder="Enter your in-game name",
            max_length=50,
            required=True
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            self.parent_view.player_name = self.player_name.value.strip()
            await interaction.response.send_message(f"✅ Player name set: {self.parent_view.player_name}", ephemeral=True)
    
    # Create Player Button
    @discord.ui.button(label="📝 Enter Player Name", style=discord.ButtonStyle.primary, row=0)
    async def enter_name_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = self.PlayerNameModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="✅ Create Player", style=discord.ButtonStyle.success, row=0)
    async def create_player_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player_name:
            await interaction.response.send_message("❌ Please enter a player name first.", ephemeral=True)
            return
        
        if not self.selected_faction:
            await interaction.response.send_message("❌ Please select a faction first.", ephemeral=True)
            return
        
        # Create the player
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def _create_player(in_game_name, discord_user_id, discord_name, faction, game_role=None, guild_name=None):
            from .models import Player, Guild
            
            # Check if player already exists
            if Player.objects.filter(in_game_name__iexact=in_game_name).exists():
                return None, "Ya existe un jugador con ese nombre"
            
            # Check if user already has a player
            if Player.objects.filter(discord_user_id=discord_user_id).exists():
                return None, "Ya tienes un jugador registrado. Usa !myplayer para ver tu jugador actual."
            
            # Find guild if specified
            guild = None
            if guild_name:
                try:
                    guild = Guild.objects.filter(name__iexact=guild_name.strip()).first()
                    if not guild:
                        return None, f"No se encontró la guild '{guild_name}'. Verifica el nombre."
                except Exception as e:
                    return None, f"Error buscando guild: {str(e)}"
            
            try:
                player = Player.objects.create(
                    in_game_name=in_game_name,
                    discord_user_id=discord_user_id,
                    discord_name=discord_name,
                    character_level=1,
                    faction=faction,
                    game_role=game_role,
                    guild=guild
                )
                return player, None
            except Exception as e:
                return None, f"Error creando jugador: {str(e)}"
        
        player, error = await _create_player(
            self.player_name,
            interaction.user.id,
            str(interaction.user),
            faction=self.selected_faction,
            game_role=self.selected_role,
            guild_name=self.selected_guild
        )
        
        if error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)
        else:
            guild_info = f"\n**Guild:** {player.guild.name}" if player.guild else ""
            role_info = f"\n**Rol:** {player.get_game_role_display()}" if player.game_role else ""
            
            embed = discord.Embed(
                title="✅ Player created successfully!",
                color=0x4a9eff
            )
            embed.add_field(
                name="📊 Player Information",
                value=f"**Name:** {player.in_game_name}\n"
                      f"**Level:** {player.character_level}\n"
                      f"**Faction:** {player.get_faction_display()}"
                      f"{guild_info}"
                      f"{role_info}",
                inline=False
            )
            embed.add_field(
                name="🔗 Loadout Link",
                value=f"https://strategic-brena-charfire-afecfd9e.koyeb.app/guilds/player/{player.id}/loadout",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def on_timeout(self):
        # Disable all components when view times out
        for item in self.children:
            item.disabled = True


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
        # Create a view with dropdowns instead of modal
        view = CreatePlayerView(self.bot_instance)
        embed = discord.Embed(
            title="👤 Create Player",
            description="Use the dropdowns below to create your player:",
            color=0x4a9eff
        )
        embed.add_field(
            name="📋 Steps",
            value="1. Enter your player name\n2. Select your faction\n3. Choose your guild (optional)\n4. Pick your role (optional)",
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
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
                "❌ No active guilds available.",
                ephemeral=True
            )
    
    @discord.ui.button(label="📅 View Events", style=discord.ButtonStyle.secondary, emoji="📅")
    async def view_events_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to view all events"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def get_events_with_participant_counts():
            from .models import Event, EventParticipant
            events = Event.objects.filter(is_active=True, is_cancelled=False).order_by('event_datetime')[:10]
            
            events_data = []
            for event in events:
                # Count participants using raw SQL to avoid async issues
                participant_count = EventParticipant.objects.filter(
                    event=event, 
                    is_active=True
                ).count()
                
                events_data.append({
                    'title': event.title,
                    'discord_timestamp': event.discord_timestamp,
                    'created_by_discord_name': event.created_by_discord_name,
                    'participant_count': participant_count,
                    'max_participants': event.max_participants,
                    'event_type_display': event.get_event_type_display()
                })
            
            return events_data
        
        events_data = await get_events_with_participant_counts()
        
        if not events_data:
            await interaction.response.send_message(
                "📅 No active events available.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📅 Active Events",
            color=0x4a9eff
        )
        
        for event_data in events_data:
            participants_text = f"{event_data['participant_count']} participants"
            if event_data['max_participants']:
                participants_text += f" / {event_data['max_participants']} max"
            
            embed.add_field(
                name=f"🎯 {event_data['title']}",
                value=f"**Date:** {event_data['discord_timestamp']}\n"
                      f"**Created by:** {event_data['created_by_discord_name']}\n"
                      f"**Participants:** {participants_text}\n"
                      f"**Type:** {event_data['event_type_display']}",
                inline=True
            )
        
        if len(events_data) == 10:
            embed.set_footer(text="Showing 10 most recent events")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📢 Publish Events", style=discord.ButtonStyle.primary, emoji="📢")
    async def publish_events_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to publish events to announcement channel"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def get_events_with_participant_counts():
            from .models import Event, EventParticipant
            events = Event.objects.filter(is_active=True, is_cancelled=False).order_by('event_datetime')[:10]
            
            events_data = []
            for event in events:
                # Count participants using raw SQL to avoid async issues
                participant_count = EventParticipant.objects.filter(
                    event=event, 
                    is_active=True
                ).count()
                
                events_data.append({
                    'title': event.title,
                    'discord_timestamp': event.discord_timestamp,
                    'created_by_discord_name': event.created_by_discord_name,
                    'participant_count': participant_count,
                    'max_participants': event.max_participants,
                    'event_type_display': event.get_event_type_display()
                })
            
            return events_data
        
        # Get bot config to find announcement channel
        config = await _get_bot_config()
        if not config or not config.event_announcements_channel_id:
            await interaction.response.send_message(
                "❌ Event announcements channel not configured. Contact administrator.",
                ephemeral=True
            )
            return
        
        # Get the announcement channel
        announcement_channel = self.bot_instance.get_channel(config.event_announcements_channel_id)
        if not announcement_channel:
            await interaction.response.send_message(
                "❌ Could not find event announcements channel.",
                ephemeral=True
            )
            return
        
        events_data = await get_events_with_participant_counts()
        
        if not events_data:
            await interaction.response.send_message(
                "❌ No active events to publish.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📢 ACTIVE EVENTS - WARBORNE",
            description="Join these epic events!",
            color=0xff6b35  # Orange color for announcements
        )
        
        for event_data in events_data:
            participants_text = f"{event_data['participant_count']} participants"
            if event_data['max_participants']:
                participants_text += f" / {event_data['max_participants']} max"
            
            embed.add_field(
                name=f"🎯 {event_data['title']}",
                value=f"**📅 Date:** {event_data['discord_timestamp']}\n"
                      f"**👤 Created by:** {event_data['created_by_discord_name']}\n"
                      f"**👥 Participants:** {participants_text}\n"
                      f"**🏷️ Type:** {event_data['event_type_display']}",
                inline=True
            )
        
        if len(events_data) == 10:
            embed.set_footer(text="Showing 10 most recent events")
        
        embed.add_field(
            name="🚀 How to participate?",
            value="Use `!menu` and select the event you're interested in to join.",
            inline=False
        )
        
        # Send to announcement channel
        await announcement_channel.send(embed=embed)
        
        # Confirm to user
        await interaction.response.send_message(
            f"✅ Events published successfully in {announcement_channel.mention}",
            ephemeral=True
        )
    
    @discord.ui.button(label="⚔️ Create Parties", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def create_parties_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to create parties for events"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def get_active_events_for_dropdown():
            from .models import Event
            events = Event.objects.filter(is_active=True, is_cancelled=False).order_by('event_datetime')
            
            event_options = []
            for event in events:
                # Create a shorter display name for the dropdown
                display_name = event.title[:90] + "..." if len(event.title) > 90 else event.title
                event_options.append(
                    discord.SelectOption(
                        label=display_name,
                        value=str(event.id),
                        description=f"Date: {event.event_datetime.strftime('%Y-%m-%d %H:%M')} | Type: {event.get_event_type_display()}"
                    )
                )
            
            return event_options
        
        event_options = await get_active_events_for_dropdown()
        
        if not event_options:
            await interaction.response.send_message(
                "❌ No active events available for party creation.",
                ephemeral=True
            )
            return
        
        # Create a view with dropdown for event selection
        class EventSelectionView(discord.ui.View):
            def __init__(self, bot_instance, event_options):
                super().__init__(timeout=300)
                self.bot_instance = bot_instance
                self.add_item(EventSelectDropdown(event_options, bot_instance))
        
        class EventSelectDropdown(discord.ui.Select):
            def __init__(self, event_options, bot_instance):
                super().__init__(
                    placeholder="Choose an event to create parties for...",
                    min_values=1,
                    max_values=1,
                    options=event_options
                )
                self.bot_instance = bot_instance
            
            async def callback(self, interaction: discord.Interaction):
                from asgiref.sync import sync_to_async
                
                @sync_to_async
                def get_event_by_id(event_id):
                    from .models import Event
                    return Event.objects.filter(
                        id=event_id,
                        is_active=True,
                        is_cancelled=False
                    ).first()
                
                event = await get_event_by_id(int(self.values[0]))
                
                if not event:
                    await interaction.response.send_message(
                        "❌ Event not found or no longer active.",
                        ephemeral=True
                    )
                    return
                
                # Create parties using the bot instance method
                success, message = await self.bot_instance.create_balanced_parties(event)
                
                if success:
                    await interaction.response.send_message(f"✅ {message}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ {message}", ephemeral=True)
        
        view = EventSelectionView(self.bot_instance, event_options)
        embed = discord.Embed(
            title="⚔️ Create Parties",
            description="Select an event from the dropdown below to create balanced parties:",
            color=0xff6b35
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🗑️ Delete Event", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_event_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to delete an event"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def get_active_events_for_deletion():
            from .models import Event
            events = Event.objects.filter(is_active=True, is_cancelled=False).order_by('event_datetime')
            
            event_options = []
            for event in events:
                # Create a shorter display name for the dropdown
                display_name = event.title[:90] + "..." if len(event.title) > 90 else event.title
                event_options.append(
                    discord.SelectOption(
                        label=display_name,
                        value=str(event.id),
                        description=f"Date: {event.event_datetime.strftime('%Y-%m-%d %H:%M')} | Type: {event.get_event_type_display()}"
                    )
                )
            
            return event_options
        
        event_options = await get_active_events_for_deletion()
        
        if not event_options:
            await interaction.response.send_message(
                "❌ No active events available for deletion.",
                ephemeral=True
            )
            return
        
        # Create a view with dropdown for event selection
        class DeleteEventView(discord.ui.View):
            def __init__(self, bot_instance, event_options):
                super().__init__(timeout=300)
                self.bot_instance = bot_instance
                self.add_item(DeleteEventDropdown(event_options, bot_instance))
        
        class DeleteEventDropdown(discord.ui.Select):
            def __init__(self, event_options, bot_instance):
                super().__init__(
                    placeholder="Choose an event to delete...",
                    min_values=1,
                    max_values=1,
                    options=event_options
                )
                self.bot_instance = bot_instance
            
            async def callback(self, interaction: discord.Interaction):
                from asgiref.sync import sync_to_async
                
                @sync_to_async
                def find_and_delete_event(event_id):
                    from .models import Event
                    event = Event.objects.filter(
                        id=event_id,
                        is_active=True,
                        is_cancelled=False
                    ).first()
                    
                    if not event:
                        return False, "Event not found or no longer active"
                    
                    # Mark as cancelled instead of deleting to preserve history
                    event.is_cancelled = True
                    event.is_active = False
                    event.save()
                    
                    return True, f"Event '{event.title}' cancelled successfully"
                
                success, message = await find_and_delete_event(int(self.values[0]))
                
                if success:
                    await interaction.response.send_message(f"✅ {message}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ {message}", ephemeral=True)
        
        view = DeleteEventView(self.bot_instance, event_options)
        embed = discord.Embed(
            title="🗑️ Delete Event",
            description="⚠️ **WARNING: This will cancel the selected event!**\n\nSelect an event from the dropdown below to delete:",
            color=0xff0000
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🏓 Ping", style=discord.ButtonStyle.success, emoji="🏓")
    async def ping_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to test bot ping"""
        latency = round(self.bot_instance.latency * 1000)
        await interaction.response.send_message(
            f"🏓 Pong! Latency: {latency}ms",
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
                    await ctx.send(f"✅ **Player created successfully!**\n"
                                 f"**Name:** {player.in_game_name}\n"
                                 f"**Level:** {player.character_level}\n"
                                 f"**Faction:** {player.get_faction_display()}\n"
                                 f"**Loadout Link:** {loadout_url}\n"
                                 f"💡 Now you can modify your equipment from the web page!")
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
                    await general_channel.send("🤖 Hello! Warborne Bot is ready for action!\n"
                                              "**Available commands:**\n"
                                              "`!menu` - 🎮 Interactive menu with all commands\n"
                                              "`!createevent` - Create guild event\n"
                                              "`!createplayer [name]` - Create your player (uses your Discord name by default)\n"
                                              "`!myplayer` - View your player\n"
                                              "`!buildplayer <name>` - View player loadout\n"
                                              "`!guildinfo` - Guild information\n"
                                              "`!ping` - Test bot")
                except Exception as e:
                    print(f"Could not send message to {guild.name}: {e}")
            
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
            await ctx.send("❌ Command not found. Available commands:\n"
                       "`!menu` - 🎮 Interactive menu with all commands\n"
                       "`!createevent` - Create guild event\n"
                       "`!createplayer [name]` - Create your player\n"
                       "`!myplayer` - View your player\n"
                       "`!buildplayer <name>` - View player loadout\n"
                       "`!guildinfo` - Guild information\n"
                       "`!ping` - Test bot")
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
            def get_participants_with_roles_and_parties():
                from .models import Party, PartyMember
                
                participants = EventParticipant.objects.filter(
                    event=event,
                    is_active=True
                ).select_related('player')
                
                participant_data = []
                role_counts = {}
                parties_data = []
                
                # Get participants data
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
                
                # Get parties data
                parties = Party.objects.filter(event=event, is_active=True).order_by('party_number')
                for party in parties:
                    party_members = PartyMember.objects.filter(
                        party=party,
                        is_active=True
                    ).select_related('player', 'event_participant')
                    
                    members_list = []
                    party_role_counts = {}
                    
                    for member in party_members:
                        member_name = member.event_participant.discord_name
                        member_role = member.player.get_game_role_display() if member.player.game_role else 'Unknown'
                        members_list.append(f"• {member_name} ({member_role})")
                        party_role_counts[member_role] = party_role_counts.get(member_role, 0) + 1
                    
                    # Create role summary
                    role_summary = ", ".join([f"{role}: {count}" for role, count in party_role_counts.items()])
                    
                    parties_data.append({
                        'party_number': party.party_number,
                        'members': members_list,
                        'member_count': len(members_list),
                        'role_summary': role_summary
                    })
                
                return participant_data, role_counts, parties_data
            
            participants_data, role_counts, parties_data = await get_participants_with_roles_and_parties()
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
            
            # Add parties information if they exist
            if parties_data:
                for party_data in parties_data:
                    party_title = f"⚔️ Party {party_data['party_number']} ({party_data['member_count']}/15)"
                    
                    # Show first 5 members to avoid embed field limits
                    members_display = "\n".join(party_data['members'][:5])
                    if len(party_data['members']) > 5:
                        members_display += f"\n• ... and {len(party_data['members']) - 5} more"
                    
                    embed.add_field(
                        name=party_title,
                        value=f"**Roles:** {party_data['role_summary']}\n**Members:**\n{members_display}",
                        inline=False
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
    
    async def create_balanced_parties(self, event):
        """Create balanced parties for an event"""
        from asgiref.sync import sync_to_async
        from .models import Party, PartyMember, EventParticipant
        
        @sync_to_async
        def create_parties():
            # Get all active participants with their players
            participants = list(EventParticipant.objects.filter(
                event=event,
                is_active=True,
                player__isnull=False
            ).select_related('player'))
            
            if len(participants) < 2:
                return False, "At least 2 participants needed to create parties"
            
            # Clear existing parties for this event
            Party.objects.filter(event=event).delete()
            
            # Define role requirements per party (minimum)
            ROLE_REQUIREMENTS = {
                'tank': 4,           # 4 tanks per party
                'healer': 2,         # 2 healers per party
                'ranged_dps': 3,     # 3 ranged DPS
                'melee_dps': 3,      # 3 melee DPS
                'defensive_tank': 1, # 1 defensive tank
                'offensive_tank': 1, # 1 offensive tank
                'offensive_support': 1, # 1 offensive support
            }
            
            MAX_PARTY_SIZE = 15
            
            # Group participants by role
            participants_by_role = {}
            for participant in participants:
                role = participant.player.game_role or 'unknown'
                if role not in participants_by_role:
                    participants_by_role[role] = []
                participants_by_role[role].append(participant)
            
            # Calculate how many parties we need
            total_participants = len(participants)
            num_parties = max(1, (total_participants + MAX_PARTY_SIZE - 1) // MAX_PARTY_SIZE)
            
            parties = []
            
            # Create party objects
            for i in range(num_parties):
                party = Party.objects.create(
                    event=event,
                    party_number=i + 1,
                    max_members=MAX_PARTY_SIZE
                )
                parties.append(party)
            
            # Distribute participants across parties
            party_assignments = [[] for _ in range(num_parties)]
            party_role_counts = [{} for _ in range(num_parties)]
            
            # Initialize role counts
            for party_idx in range(num_parties):
                for role in ROLE_REQUIREMENTS.keys():
                    party_role_counts[party_idx][role] = 0
            
            # Distribute participants by role, trying to balance
            for role, role_participants in participants_by_role.items():
                if role == 'unknown':
                    # Distribute unknown roles evenly
                    for i, participant in enumerate(role_participants):
                        party_idx = i % num_parties
                        party_assignments[party_idx].append(participant)
                else:
                    # Distribute known roles to balance requirements
                    for i, participant in enumerate(role_participants):
                        # Find party with least of this role
                        best_party = 0
                        min_count = party_role_counts[0].get(role, 0)
                        
                        for party_idx in range(1, num_parties):
                            current_count = party_role_counts[party_idx].get(role, 0)
                            if current_count < min_count:
                                min_count = current_count
                                best_party = party_idx
                        
                        party_assignments[best_party].append(participant)
                        party_role_counts[best_party][role] = party_role_counts[best_party].get(role, 0) + 1
            
            # Create PartyMember objects
            party_members_created = 0
            for party_idx, party in enumerate(parties):
                for participant in party_assignments[party_idx]:
                    PartyMember.objects.create(
                        party=party,
                        event_participant=participant,
                        player=participant.player,
                        assigned_role=participant.player.game_role
                    )
                    party_members_created += 1
            
            return True, f"Parties created successfully: {num_parties} parties with {party_members_created} participants distributed"
        
        return await create_parties()
