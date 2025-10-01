import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import os
import asyncio
from datetime import datetime, timezone
from django.conf import settings
from .models import DiscordBotConfig, Player, Guild, Event, EventParticipant
from asgiref.sync import sync_to_async

# Check Party View for event announcements
class CheckPartyView(View):
    def __init__(self, event_id, bot_instance=None):
        super().__init__(timeout=None)  # No timeout so button stays active
        self.event_id = event_id
        self.bot_instance = bot_instance
    
    @discord.ui.button(label="Check Party", style=discord.ButtonStyle.secondary, emoji="👥")
    async def check_party_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle the Check Party button click"""
        try:
            from .models import Event, EventParticipant, Party, PartyMember
            
            # Get the user's Discord ID
            user_id = interaction.user.id
            
            # Check if user is participating in the event and their party status
            @sync_to_async
            def check_party_status():
                try:
                    # Get the event
                    event = Event.objects.get(id=self.event_id)
                    
                    # Check if user is participating in this event
                    # First try to find by discord_user_id
                    participant = EventParticipant.objects.filter(
                        event=event,
                        discord_user_id=user_id
                    ).first()
                    
                    # If not found by discord_user_id, try to find by discord_name as fallback
                    if not participant:
                        # Get the user's discord name to search by
                        discord_name = f"{interaction.user.name}#{interaction.user.discriminator}"
                        participant = EventParticipant.objects.filter(
                            event=event,
                            discord_name=discord_name
                        ).first()
                    
                    if not participant:
                        return "No Party Assign"
                    
                    # Check if user is assigned to a party
                    party_member = PartyMember.objects.filter(
                        event_participant=participant,
                        is_active=True
                    ).select_related('party', 'event_participant').first()
                    
                    if not party_member:
                        return "No Party Assign"
                    
                    # Get party info
                    party = party_member.party
                    
                    # Find the party leader (member with is_leader=True)
                    party_leader = PartyMember.objects.filter(
                        party=party,
                        is_active=True,
                        is_leader=True
                    ).first()
                    
                    if party_leader:
                        # Get Discord user ID from the Player model, not EventParticipant
                        leader_discord_id = party_leader.player.discord_user_id if party_leader.player else None
                        # Return party info as a dictionary for detailed display
                        return {
                            'party_name': party.party_name or f"Party {party.party_number}",
                            'leader_id': leader_discord_id,
                            'party_id': party.id
                        }
                    else:
                        return "Party Leader: Unknown"
                        
                except Exception as e:
                    print(f"Error checking party status: {e}")
                    # Log the error to database
                    from .models import DiscordBotLog
                    DiscordBotLog.objects.create(
                        action='error',
                        message=f"Check Party Status Error: {str(e)}",
                        user=f"Discord User {user_id}",
                        success=False,
                        details={'error': str(e), 'event_id': self.event_id, 'user_id': user_id}
                    )
                    return "Error checking party status"
            
            # Get the party status
            party_status = await check_party_status()
            
            # Handle different response types
            if isinstance(party_status, dict):
                # User is in a party - show detailed information
                party_name = party_status['party_name']
                leader_id = party_status['leader_id']
                party_id = party_status['party_id']
                
                # Get leader name
                leader_name = await self.get_discord_user_name(leader_id)
                
                # Get all party members
                @sync_to_async
                def get_party_members():
                    try:
                        from .models import Party, PartyMember
                        party = Party.objects.get(id=party_id)
                        members = PartyMember.objects.filter(party=party).select_related('player')
                        
                        member_list = []
                        for member in members:
                            # Get Discord user ID from the Player model, not EventParticipant
                            discord_user_id = member.player.discord_user_id if member.player else None
                            member_list.append(discord_user_id)
                        
                        return member_list
                    except Exception as e:
                        print(f"Error getting party members: {e}")
                        return []
                
                # Get party members
                member_ids = await get_party_members()
                
                # Resolve member names
                member_names = []
                for member_id in member_ids:
                    member_name = await self.get_discord_user_name(member_id)
                    member_names.append(member_name)
                
                # Create detailed response
                response_message = (
                    f"**Party Name:** {party_name}\n"
                    f"**Party Leader:** {leader_name}\n"
                    f"**Party Members:** {', '.join(member_names) if member_names else 'None'}"
                )
                
            elif isinstance(party_status, int):
                # Legacy case - just leader ID
                leader_name = await self.get_discord_user_name(party_status)
                response_message = f"**Party Status:** Party Leader: {leader_name}"
            else:
                # String response (No Party Assign, Error, etc.)
                response_message = f"**Party Status:** {party_status}"
            
            # Send response
            await interaction.response.send_message(
                response_message,
                ephemeral=True  # Only visible to the user who clicked
            )
            
        except Exception as e:
            print(f"Error in check party button: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while checking your party status.",
                ephemeral=True
            )
    
    async def get_discord_user_name(self, discord_user_id):
        """Get Discord user name from user ID"""
        try:
            if self.bot_instance:
                user = self.bot_instance.get_user(discord_user_id)
                if user:
                    return user.display_name or user.name
            # Fallback to mention format
            return f"<@{discord_user_id}>"
        except:
            return f"User_{discord_user_id}"


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
        
        # Add hardcoded guild dropdown
        self._add_hardcoded_guilds()
    
    def _add_hardcoded_guilds(self):
        """Add hardcoded guild dropdown with Violence 1 and Violence 2"""
        print("🔥 DEBUG: Adding hardcoded guild dropdown")
        
        guild_options = [
            discord.SelectOption(
                label="No Guild",
                value="none",
                description="No guild selected",
                default=True
            ),
            discord.SelectOption(
                label="Violence",
                value="Violence",
                description="Guild Violence"
            ),
            discord.SelectOption(
                label="Violence 2",
                value="Violence 2",
                description="Guild Violence 2"
            )
        ]
        
        guild_select = self.GuildSelect(self)
        guild_select.options = guild_options
        self.add_item(guild_select)
        print(f"🔥 DEBUG: Added hardcoded guild dropdown with {len(guild_options)} options")
    
    async def _load_guilds_sync(self):
        """Load guilds from database and create guild select dropdown (async version with sync_to_async)"""
        try:
            from .models import Guild
            from asgiref.sync import sync_to_async
            
            print("DEBUG: Loading guilds from database...")
            
            # Use sync_to_async to handle Django ORM calls from async context
            @sync_to_async
            def get_guilds_data():
                guilds = Guild.objects.filter(is_active=True)
                guild_count = guilds.count()
                print(f"DEBUG: Found {guild_count} active guilds")
                
                # If no active guilds found, try to get all guilds (fallback)
                if guild_count == 0:
                    print("DEBUG: No active guilds found, trying all guilds...")
                    guilds = Guild.objects.all()
                    guild_count = guilds.count()
                    print(f"DEBUG: Found {guild_count} total guilds")
                
                # Convert to list to avoid async iteration issues
                guilds_list = []
                for guild in guilds:
                    member_count = guild.players.count()
                    guilds_list.append({
                        'name': guild.name,
                        'member_count': member_count
                    })
                
                return guilds_list
            
            guilds_data = await get_guilds_data()
            guild_options = []
            
            # Always add "No Guild" option
            guild_options.append(
                discord.SelectOption(
                    label="No Guild",
                    value="none",
                    description="No guild selected",
                    default=True
                )
            )
            print("DEBUG: Added 'No Guild' option")
            
            # Add existing guilds if any
            if guilds_data:
                print(f"DEBUG: Adding {len(guilds_data)} guilds to dropdown")
                for guild_data in guilds_data:
                    print(f"DEBUG: Adding guild '{guild_data['name']}' with {guild_data['member_count']} members")
                    guild_options.append(
                        discord.SelectOption(
                            label=guild_data['name'],
                            value=guild_data['name'],
                            description=f"Members: {guild_data['member_count']}"
                        )
                    )
            else:
                print("DEBUG: No active guilds found in database")
            
            # Always create and add the guild select dropdown
            print(f"DEBUG: Creating guild dropdown with {len(guild_options)} options")
            guild_select = self.GuildSelect(self)
            guild_select.options = guild_options
            self.add_item(guild_select)
            print("DEBUG: Guild dropdown added to view")
            
        except Exception as e:
            print(f"Error loading guilds: {e}")
            import traceback
            traceback.print_exc()
            # Even if there's an error, create a basic guild dropdown
            guild_select = self.GuildSelect(self)
            guild_select.options = [
                discord.SelectOption(
                    label="No Guild",
                    value="none",
                    description="No guild selected",
                    default=True
                )
            ]
            self.add_item(guild_select)
            print("DEBUG: Fallback guild dropdown created")
    
    
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
                discord.SelectOption(label="Healer", value="healer", description="Healer role"),
                discord.SelectOption(label="Defensive Tank", value="defensive_tank", description="Defensive tank"),
                discord.SelectOption(label="Offensive Tank", value="offensive_tank", description="Offensive tank"),
                discord.SelectOption(label="Support", value="support", description="Support role"),
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
            if guild_name and guild_name != "none":
                try:
                    # Debug: List all guilds in database
                    all_guilds = Guild.objects.all()
                    print(f"🔥 DEBUG: All guilds in database:")
                    for g in all_guilds:
                        print(f"  - ID: {g.id}, Name: '{g.name}', Active: {g.is_active}")
                    
                    # Search for guild with exact name match (case insensitive)
                    guild = Guild.objects.filter(name__iexact=guild_name.strip()).first()
                    print(f"🔥 DEBUG: Searching for guild '{guild_name.strip()}' -> Found: {guild}")
                    
                    if not guild:
                        # Try alternative search methods
                        guild = Guild.objects.filter(name__icontains=guild_name.strip()).first()
                        print(f"🔥 DEBUG: Alternative search (icontains) -> Found: {guild}")
                        
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
                value=f"https://weareviolence.com/player/{player.id}/loadout",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def on_timeout(self):
        # Disable all components when view times out
        for item in self.children:
            item.disabled = True


class PlayerInfoView(discord.ui.View):
    """View for displaying player info with edit button"""
    
    def __init__(self, player):
        super().__init__(timeout=300)
        self.player = player
    
    @discord.ui.button(label="✏️ Edit Player", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_player_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to edit player information"""
        # Create and show the edit player modal
        modal = EditPlayerModal(self.player)
        await interaction.response.send_modal(modal)


class EditPlayerView(discord.ui.View):
    """View for editing player information with dropdowns"""
    
    def __init__(self, player):
        super().__init__(timeout=300)
        self.player = player
        self.selected_faction = player.faction
        self.selected_role = player.game_role
        
        # Add dropdowns to the view
        self.add_item(self.FactionSelect(self))
        self.add_item(self.RoleSelect(self))
    
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
            # Set default value to current player's faction
            for option in options:
                if option.value == parent_view.player.faction:
                    option.default = True
                    break
            
            super().__init__(placeholder="Choose your faction...", options=options, min_values=1, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            self.parent_view.selected_faction = self.values[0]
            await interaction.response.send_message(f"✅ Faction selected: {self.values[0]}", ephemeral=True)
    
    # Role Select
    class RoleSelect(discord.ui.Select):
        def __init__(self, parent_view):
            self.parent_view = parent_view
            options = [
                discord.SelectOption(label="Ranged DPS", value="ranged_dps", description="Ranged damage dealer"),
                discord.SelectOption(label="Melee DPS", value="melee_dps", description="Melee damage dealer"),
                discord.SelectOption(label="Healer", value="healer", description="Healer role"),
                discord.SelectOption(label="Defensive Tank", value="defensive_tank", description="Defensive tank"),
                discord.SelectOption(label="Offensive Tank", value="offensive_tank", description="Offensive tank"),
                discord.SelectOption(label="Support", value="support", description="Support role"),
            ]
            # Set default value to current player's role
            for option in options:
                if option.value == parent_view.player.game_role:
                    option.default = True
                    break
            
            super().__init__(placeholder="Choose your role (optional)...", options=options, min_values=0, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            if self.values:
                self.parent_view.selected_role = self.values[0]
                await interaction.response.send_message(f"✅ Role selected: {self.values[0]}", ephemeral=True)
            else:
                self.parent_view.selected_role = None
                await interaction.response.send_message("✅ No role selected", ephemeral=True)
    
    # Edit Player Button
    @discord.ui.button(label="📝 Edit Player Info", style=discord.ButtonStyle.primary, row=0)
    async def edit_player_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = self.PlayerNameModal(self)
        await interaction.response.send_modal(modal)
    
    async def on_timeout(self):
        # Disable all components when view times out
        for item in self.children:
            item.disabled = True


class EditPlayerNameModal(discord.ui.Modal, title="Edit Player Name"):
    """Modal for editing player name and level"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
        # Create text inputs with default values
        self.player_name = discord.ui.TextInput(
            label="Player Name",
            placeholder="Enter your in-game name",
            default=parent_view.player.in_game_name,
            max_length=50,
            required=True
        )
        
        self.level = discord.ui.TextInput(
            label="Level",
            placeholder="Enter your character level",
            default=str(parent_view.player.character_level),
            max_length=3,
            required=True
        )
        
        # Add inputs to modal
        self.add_item(self.player_name)
        self.add_item(self.level)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate level
        try:
            level_value = int(self.level.value)
            if level_value < 1 or level_value > 100:
                raise ValueError("Level must be between 1 and 100")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid level. Please enter a number between 1 and 100.",
                ephemeral=True
            )
            return
        
        # Update player
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def update_player():
            try:
                player = self.parent_view.player
                player.in_game_name = self.player_name.value
                player.character_level = level_value
                player.faction = self.parent_view.selected_faction
                player.game_role = self.parent_view.selected_role
                player.save()
                return player, None
            except Exception as e:
                return None, str(e)
        
        updated_player, error = await update_player()
        
        if error:
            await interaction.response.send_message(
                f"❌ Error updating player: {error}",
                ephemeral=True
            )
        else:
            # Show updated player info
            guild_info = f"**Guild:** {updated_player.guild.name}" if updated_player.guild else "**Guild:** Sin guild"
            role_info = f"**Rol:** {updated_player.get_game_role_display()}" if updated_player.game_role else "**Rol:** No asignado"
            
            loadout_url = f"https://weareviolence.com/player/{updated_player.id}/loadout"
            
            embed = discord.Embed(
                title="✅ Player Updated Successfully",
                color=0x4caf50
            )
            embed.add_field(
                name="📊 Updated Player Information",
                value=f"**Name:** {updated_player.in_game_name}\n"
                      f"**Level:** {updated_player.character_level}\n"
                      f"**Faction:** {updated_player.get_faction_display()}\n"
                      f"{guild_info}\n"
                      f"{role_info}\n"
                      f"**Loadouts:** [View Loadouts]({loadout_url})",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)


class LevelModal(discord.ui.Modal, title="Edit Level"):
    """Modal for editing player level only"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
        # Create text input with default value
        self.level = discord.ui.TextInput(
            label="Level",
            placeholder="Enter your character level",
            default=str(parent_view.player.character_level),
            max_length=3,
            required=True
        )
        
        # Add input to modal
        self.add_item(self.level)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate level
        try:
            level_value = int(self.level.value)
            if level_value < 1 or level_value > 100:
                raise ValueError("Level must be between 1 and 100")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid level. Please enter a number between 1 and 100.",
                ephemeral=True
            )
            return
        
        # Update player level
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def update_level():
            try:
                player = self.parent_view.player
                player.character_level = level_value
                player.faction = self.parent_view.selected_faction
                player.game_role = self.parent_view.selected_role
                player.save()
                return player, None
            except Exception as e:
                return None, str(e)
        
        updated_player, error = await update_level()
        
        if error:
            await interaction.response.send_message(
                f"❌ Error updating player: {error}",
                ephemeral=True
            )
        else:
            # Show updated player info
            guild_info = f"**Guild:** {updated_player.guild.name}" if updated_player.guild else "**Guild:** Sin guild"
            role_info = f"**Rol:** {updated_player.get_game_role_display()}" if updated_player.game_role else "**Rol:** No asignado"
            
            loadout_url = f"https://weareviolence.com/player/{updated_player.id}/loadout"
            
            embed = discord.Embed(
                title="✅ Player Updated Successfully",
                color=0x4caf50
            )
            embed.add_field(
                name="📊 Updated Player Information",
                value=f"**Name:** {updated_player.in_game_name}\n"
                      f"**Level:** {updated_player.character_level}\n"
                      f"**Faction:** {updated_player.get_faction_display()}\n"
                      f"{guild_info}\n"
                      f"{role_info}\n"
                      f"**Loadouts:** [View Loadouts]({loadout_url})",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)


class EditPlayerView(discord.ui.View):
    """View for editing player information with dropdowns"""
    
    def __init__(self, player):
        super().__init__(timeout=300)
        self.player = player
        self.selected_faction = player.faction
        self.selected_role = player.game_role
        
        # Add dropdowns to the view
        self.add_item(self.FactionSelect(self))
        self.add_item(self.RoleSelect(self))
    
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
            # Set default value to current player's faction
            for option in options:
                if option.value == parent_view.player.faction:
                    option.default = True
                    break
            
            super().__init__(placeholder="Choose your faction...", options=options, min_values=1, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            self.parent_view.selected_faction = self.values[0]
            await interaction.response.send_message(f"✅ Faction selected: {self.values[0]}", ephemeral=True)
    
    # Role Select
    class RoleSelect(discord.ui.Select):
        def __init__(self, parent_view):
            self.parent_view = parent_view
            options = [
                discord.SelectOption(label="Ranged DPS", value="ranged_dps", description="Ranged damage dealer"),
                discord.SelectOption(label="Melee DPS", value="melee_dps", description="Melee damage dealer"),
                discord.SelectOption(label="Healer", value="healer", description="Healer role"),
                discord.SelectOption(label="Defensive Tank", value="defensive_tank", description="Defensive tank"),
                discord.SelectOption(label="Offensive Tank", value="offensive_tank", description="Offensive tank"),
                discord.SelectOption(label="Support", value="support", description="Support role"),
            ]
            # Set default value to current player's role
            for option in options:
                if option.value == parent_view.player.game_role:
                    option.default = True
                    break
            
            super().__init__(placeholder="Choose your role (optional)...", options=options, min_values=0, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            if self.values:
                self.parent_view.selected_role = self.values[0]
                
                # Save role to database immediately
                @sync_to_async
                def save_role():
                    try:
                        player = self.parent_view.player
                        player.game_role = self.values[0]
                        player.save()
                        return True
                    except Exception as e:
                        print(f"Error saving role: {e}")
                        return False
                
                success = await save_role()
                if success:
                    await interaction.response.send_message(f"✅ Role updated to: {self.values[0]}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ Error updating role", ephemeral=True)
            else:
                self.parent_view.selected_role = None
                await interaction.response.send_message("✅ No role selected", ephemeral=True)
    

    # Edit Player Button
    @discord.ui.button(label="📝 Edit Player Info", style=discord.ButtonStyle.primary, row=0)
    async def edit_player_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditPlayerNameModal(self)
        await interaction.response.send_modal(modal)
    
    # Edit Level Button
    @discord.ui.button(label="📊 Edit Level", style=discord.ButtonStyle.secondary, row=0)
    async def edit_level_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = LevelModal(self)
        await interaction.response.send_modal(modal)
    
    async def on_timeout(self):
        # Disable all components when view times out
        for item in self.children:
            item.disabled = True


class EditPlayerModal(discord.ui.Modal, title="Edit Player Information"):
    """Modal for editing player information - DEPRECATED, use EditPlayerView instead"""
    
    def __init__(self, player):
        super().__init__()
        self.player = player
        
        # Add text inputs for editable fields
        self.name_input = discord.ui.TextInput(
            label="Player Name",
            placeholder="Enter your in-game name",
            default=player.in_game_name,
            max_length=50,
            required=True
        )
        
        self.level_input = discord.ui.TextInput(
            label="Level",
            placeholder="Enter your character level",
            default=str(player.character_level),
            max_length=3,
            required=True
        )
        
        self.faction_input = discord.ui.TextInput(
            label="Faction",
            placeholder="Sirius, Empire, Federation",
            default=player.get_faction_display(),
            max_length=20,
            required=True
        )
        
        self.role_input = discord.ui.TextInput(
            label="Role",
            placeholder="Healer, Tank, DPS, Support",
            default=player.get_game_role_display() if player.game_role else "",
            max_length=20,
            required=False
        )
        
        # Add inputs to modal
        self.add_item(self.name_input)
        self.add_item(self.level_input)
        self.add_item(self.faction_input)
        self.add_item(self.role_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        from asgiref.sync import sync_to_async
        from .models import Player
        
        # Validate inputs
        try:
            level = int(self.level_input.value)
            if level < 1 or level > 100:
                raise ValueError("Level must be between 1 and 100")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid level. Please enter a number between 1 and 100.",
                ephemeral=True
            )
            return
        
        # Map faction names to choices
        faction_mapping = {
            'sirius': 'sirius',
            'empire': 'empire', 
            'federation': 'federation'
        }
        faction = faction_mapping.get(self.faction_input.value.lower(), 'sirius')
        
        # Map role names to choices
        role_mapping = {
            'healer': 'healer',
            'tank': 'tank',
            'dps': 'dps',
            'support': 'support'
        }
        role = role_mapping.get(self.role_input.value.lower(), None)
        
        @sync_to_async
        def update_player():
            try:
                player = Player.objects.get(id=self.player.id)
                player.in_game_name = self.name_input.value
                player.character_level = level
                player.faction = faction
                player.game_role = role
                player.save()
                return player, None
            except Exception as e:
                return None, str(e)
        
        updated_player, error = await update_player()
        
        if error:
            await interaction.response.send_message(
                f"❌ Error updating player: {error}",
                ephemeral=True
            )
        else:
            # Show updated player info
            guild_info = f"**Guild:** {updated_player.guild.name}" if updated_player.guild else "**Guild:** Sin guild"
            role_info = f"**Rol:** {updated_player.get_game_role_display()}" if updated_player.game_role else "**Rol:** No asignado"
            
            loadout_url = f"https://weareviolence.com/player/{updated_player.id}/loadout"
            
            embed = discord.Embed(
                title="✅ Player Updated Successfully",
                color=0x4caf50
            )
            embed.add_field(
                name="📊 Updated Player Information",
                value=f"**Name:** {updated_player.in_game_name}\n"
                      f"**Level:** {updated_player.character_level}\n"
                      f"**Faction:** {updated_player.get_faction_display()}\n"
                      f"{guild_info}\n"
                      f"{role_info}\n"
                      f"**Loadouts:** [View Loadouts]({loadout_url})",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)


class SimpleMenuView(discord.ui.View):
    """Simple menu view with Player Options button"""
    
    def __init__(self, bot_instance):
        super().__init__(timeout=300)
        self.bot_instance = bot_instance
    
    @discord.ui.button(label="👤 Player Options", style=discord.ButtonStyle.primary, emoji="👤")
    async def player_options_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to show player options based on user status"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def _get_player_by_discord_user(discord_user_id):
            from .models import Player
            try:
                return Player.objects.select_related('guild').get(discord_user_id=discord_user_id)
            except Player.DoesNotExist:
                return None
        
        # Check if user has a player
        player = await _get_player_by_discord_user(interaction.user.id)
        user_has_player = player is not None
        
        embed = discord.Embed(
            title="👤 Player Options",
            description="Select an option from the menu below:",
            color=0x4a9eff,
            timestamp=datetime.now(timezone.utc)
        )
        
        if user_has_player:
            embed.add_field(
                name="📋 Available Options",
                value="• 📊 Player Details\n• ✏️ Edit Player\n• 🌐 My Profile",
                inline=False
            )
            embed.add_field(
                name="ℹ️ How to Use",
                value="Click the buttons below to view or edit your player information!",
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Available Options",
                value="• 👤 Create Player",
                inline=False
            )
            embed.add_field(
                name="ℹ️ How to Use",
                value="Click the button below to create your first player!",
                inline=False
            )
        
        embed.set_footer(text="Warborne Above Ashes - Guild Tools")
        
        view = CommandMenuView(self.bot_instance, user_has_player, player)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CommandMenuView(discord.ui.View):
    """Interactive menu view with command buttons"""
    
    def __init__(self, bot_instance, user_has_player=False, player=None):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.bot_instance = bot_instance
        self.user_has_player = user_has_player
        self.player = player
        
        # Add buttons based on whether user has a player
        if not user_has_player:
            # User doesn't have a player - show Create Player button
            self.add_item(self.CreatePlayerButton())
        else:
            # User has a player - show Player Details, Edit Player, and My Profile buttons
            self.add_item(self.PlayerDetailsButton())
            self.add_item(self.EditPlayerButton())
            self.add_item(self.MyProfileButton())
    
    class CreatePlayerButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="👤 Create Player", style=discord.ButtonStyle.secondary, emoji="👤")
        
        async def callback(self, interaction: discord.Interaction):
            """Button to create a new player"""
            # Get the parent view to access bot_instance
            parent_view = self.view
            view = CreatePlayerView(parent_view.bot_instance)
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
    
    class PlayerDetailsButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="📊 Player Details", style=discord.ButtonStyle.secondary, emoji="📊")
        
        async def callback(self, interaction: discord.Interaction):
            """Button to show current player info"""
            # Get the parent view to access the player data
            parent_view = self.view
            player = parent_view.player
            
            if player:
                guild_info = f"**Guild:** {player.guild.name}" if player.guild else "**Guild:** Sin guild"
                role_info = f"**Rol:** {player.get_game_role_display()}" if player.game_role else "**Rol:** No asignado"
                
                loadout_url = f"https://weareviolence.com/player/{player.id}/loadout"
                
                embed = discord.Embed(
                    title="📊 Player Information",
                    color=0x4a9eff
                )
                embed.add_field(
                    name="👤 Player Details",
                    value=f"**Name:** {player.in_game_name}\n"
                          f"**Level:** {player.character_level}\n"
                          f"**Faction:** {player.get_faction_display()}\n"
                          f"{guild_info}\n"
                          f"{role_info}\n"
                          f"**Loadouts:** [View Loadouts]({loadout_url})",
                    inline=False
                )
                
                # Create view with edit button
                view = PlayerInfoView(player)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "❌ No tienes un jugador registrado. Usa el botón 'Create Player' para crear uno.",
                    ephemeral=True
                )
    
    class EditPlayerButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="✏️ Edit Player", style=discord.ButtonStyle.primary, emoji="✏️")
        
        async def callback(self, interaction: discord.Interaction):
            """Button to edit player information"""
            # Get the parent view to access the player data
            parent_view = self.view
            player = parent_view.player
            
            if player:
                # Create and show the edit player view with dropdowns
                view = EditPlayerView(player)
                embed = discord.Embed(
                    title="✏️ Edit Player Information",
                    description="Use the dropdowns below to select your faction and role, then click the button to edit name and level:",
                    color=0x4a9eff
                )
                embed.add_field(
                    name="📋 Current Information",
                    value=f"**Name:** {player.in_game_name}\n"
                          f"**Level:** {player.character_level}\n"
                          f"**Faction:** {player.get_faction_display()}\n"
                          f"**Role:** {player.get_game_role_display() if player.game_role else 'No role'}",
                    inline=False
                )
                embed.add_field(
                    name="📝 Steps",
                    value="1. Select your faction from the dropdown\n2. Select your role from the dropdown\n3. Click 'Edit Player Info' to change name\n4. Click 'Edit Level' to change level",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "❌ No tienes un jugador registrado. Usa el botón 'Create Player' para crear uno.",
                    ephemeral=True
                )
    
    class MyProfileButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="🌐 My Profile", style=discord.ButtonStyle.success, emoji="🌐")
        
        async def callback(self, interaction: discord.Interaction):
            """Button to generate profile access token and redirect to profile page"""
            from asgiref.sync import sync_to_async
            import jwt
            from datetime import datetime, timedelta
            from django.conf import settings
            
            @sync_to_async
            def generate_profile_token(player, discord_user_id):
                """Generate JWT token for profile access"""
                try:
                    # Token payload
                    payload = {
                        'player_id': player.id,
                        'discord_user_id': discord_user_id,
                        'purpose': 'profile_access',
                        'exp': datetime.utcnow() + timedelta(hours=1),  # 1 hour expiration
                        'iat': datetime.utcnow(),
                        'iss': 'warborne-discord-bot'
                    }
                    
                    # Generate token using Django's SECRET_KEY
                    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
                    return token
                except Exception as e:
                    print(f"Error generating profile token: {e}")
                    return None
            
            # Get the parent view to access the player data
            parent_view = self.view
            player = parent_view.player
            
            if player:
                # Generate profile access token
                token = await generate_profile_token(player, interaction.user.id)
                
                if token:
                    # Create player profile page URL with token (React frontend)
                    base_url = parent_view.bot_instance.config.get('base_url', 'https://weareviolence.com')
                    profile_url = f"{base_url}/player/{player.id}?token={token}"
                    
                    embed = discord.Embed(
                        title="🌐 My Profile",
                        description="Your personal profile page is ready!",
                        color=0x4a9eff
                    )
                    embed.add_field(
                        name="📋 Profile Information",
                        value=f"**Name:** {player.in_game_name}\n"
                              f"**Level:** {player.character_level}\n"
                              f"**Faction:** {player.get_faction_display()}\n"
                              f"**Role:** {player.get_game_role_display() if player.game_role else 'No role'}",
                        inline=False
                    )
                    embed.add_field(
                        name="🔗 Access Your Profile Page",
                        value=f"[Click here to open your profile page]({profile_url})\n\n"
                              f"⏰ **Token expires in 1 hour**\n"
                              f"🔒 **Only you can access this link**",
                        inline=False
                    )
                    embed.add_field(
                        name="ℹ️ What's Available",
                        value="• View your complete player information\n"
                              "• Access your loadout management\n"
                              "• Browse your gear inventory\n"
                              "• Manage your equipment builds",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(
                        "❌ Error generating profile access token. Please try again later.",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "❌ No tienes un jugador registrado. Usa el botón 'Create Player' para crear uno.",
                    ephemeral=True
                )


# CreateEventModal removed - event creation moved to web interface
# Modal removed
    
    
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
        label="Max Party Size (optional)",
        placeholder="Leave empty for default party size",
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
            max_party_size = None
            if self.max_participants_input.value.strip():
                try:
                    max_party_size = int(self.max_participants_input.value)
                    if max_party_size <= 0:
                        raise ValueError()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ Max party size must be a positive number.",
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
                    max_participants=max_party_size
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
                value=f"{event.discord_timestamp}",
                inline=False
            )
            
            if event.party_size_limit:
                embed.add_field(
                    name="👥 Max Party Size",
                    value=str(event.party_size_limit),
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
            return Player.objects.select_related('guild').filter(discord_user_id=discord_user_id).first()

        
        
        
        @self.command(name="createplayer")
        async def createplayer(ctx, *, player_name=None):
            """Create a new player linked to your Discord account using interactive dropdowns"""
            print(f"🔥 DEBUG: createplayer command called by {ctx.author.name}")
            
            # Create a view with dropdowns for player creation
            view = CreatePlayerView(self)
            
            embed = discord.Embed(
                title="👤 Create Player",
                description="Use the dropdowns below to create your player:",
                color=0x4a9eff
            )
            
            if player_name:
                embed.add_field(
                    name="Suggested Name",
                    value=player_name,
                    inline=False
                )
            
            embed.add_field(
                name="Steps",
                value="1. Enter your player name\n2. Select your faction\n3. Choose your guild (optional)\n4. Pick your role (optional)",
                inline=False
            )
            
            print(f"🔥 DEBUG: Sending view with {len(view.children)} dropdowns")
            await ctx.send(embed=embed, view=view, ephemeral=True)
        
        @sync_to_async
        def _get_player_info_for_command(player):
            """Get player info for command display"""
            if not player:
                return None
            
            guild_info = f"**Guild:** {player.guild.name}" if player.guild else "**Guild:** Sin guild"
            role_info = f"**Rol:** {player.get_game_role_display()}" if player.game_role else "**Rol:** No asignado"
            
            return {
                'guild_info': guild_info,
                'role_info': role_info,
                'in_game_name': player.in_game_name,
                'character_level': player.character_level,
                'faction': player.get_faction_display(),
                'player_id': player.id
            }
        
        @self.command(name="myplayer")
        async def myplayer(ctx):
            """Show your registered player information"""
            print(f"🔥 DEBUG: myplayer command called by {ctx.author.name}")
            try:
                player = await _get_player_by_discord_user(ctx.author.id)
                player_info = await _get_player_info_for_command(player)
                
                if player_info:
                    base_url = self.config.get('base_url', 'https://weareviolence.com')
                    loadout_url = f"{base_url}/player/{player_info['player_id']}/loadout"
                    
                    embed = discord.Embed(
                        title="📊 Player Information",
                        color=0x4a9eff
                    )
                    embed.add_field(
                        name="👤 Player Details",
                        value=f"**Name:** {player_info['in_game_name']}\n"
                              f"**Level:** {player_info['character_level']}\n"
                              f"**Faction:** {player_info['faction']}\n"
                              f"{player_info['guild_info']}\n"
                              f"{player_info['role_info']}\n"
                              f"**Loadouts:** [View Loadouts]({loadout_url})",
                        inline=False
                    )
                    
                    # Create view with edit button
                    view = PlayerInfoView(player)
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send("❌ No tienes un jugador registrado. Usa `!createplayer <nombre>` para crear uno.")
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
        
        
        @self.command(name="menu")
        async def menu(ctx):
            """Show interactive menu with all available commands"""
            embed = discord.Embed(
                title="🎮 Warborne Bot - Command Menu",
                description="Select an option from the menu below:",
                color=0x4a9eff,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="📋 Available Options",
                value="• 👤 Player Options",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ How to Use",
                value="Click the button below to access player management options!",
                inline=False
            )
            
            embed.set_footer(text="Warborne Above Ashes - Guild Tools")
            
            view = SimpleMenuView(self)
            await ctx.send(embed=embed, view=view)
    
    async def setup_hook(self):
        """Setup hook - no slash commands needed"""
        pass
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print('🤖 ¡Hola! Warborne Bot está listo para la acción!')
        print("🔍 Bot on_ready method called - starting initialization...")
        
        # Commands are automatically loaded
        print(f'✅ Bot ready with {len(self.commands)} commands')
        for cmd in self.commands:
            print(f'   - !{cmd.name}: {cmd.description}')
        
        print("🔍 Starting task initialization...")
        
        # Start the status monitoring task
        try:
            self.status_monitor_task = asyncio.create_task(self.monitor_bot_status())
            print("✅ Status monitoring task started")
        except Exception as e:
            print(f"❌ Error starting status monitoring: {e}")
        
        # Start the command monitoring task
        try:
            self.command_monitor_task = asyncio.create_task(self.monitor_commands())
            print("✅ Command monitoring task started")
        except Exception as e:
            print(f"❌ Error starting command monitoring: {e}")
            import traceback
            traceback.print_exc()
        
        # Add reaction event handler
        self.add_listener(self.on_reaction_add, 'on_reaction_add')
        self.add_listener(self.on_reaction_remove, 'on_reaction_remove')
        
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
                    # TODO: Optimize startup message later - temporarily commented out
                    # await general_channel.send("🤖 **Warborne Bot is online!**\n\n"
                    #                           "This bot helps players manage their characters and participate in guild events.\n"
                    #                           "Use `!menu` to see all available commands and get started!")
                    pass
                except Exception as e:
                    print(f"Could not send message to {guild.name}: {e}")
            
        await self.update_bot_status(True)
    
    async def publish_event_announcement(self, event_data):
        """Publish an event announcement to Discord"""
        try:
            from .models import DiscordBotConfig
            
            # Get bot config
            config = await _get_bot_config()
            if not config or not config.event_announcements_channel_id:
                return False, "Event announcements channel not configured"
            
            # Get the announcement channel
            announcement_channel = self.get_channel(config.event_announcements_channel_id)
            if not announcement_channel:
                return False, "Could not find event announcements channel"
            
            # Create the announcement embed
            embed = discord.Embed(
                title="📢 NEW EVENT ANNOUNCEMENT",
                description=f"**{event_data['title']}**",
                color=0xff6b35  # Orange color for announcements
            )
            
            # Add event details
            embed.add_field(
                name="📅 Event Date",
                value=event_data['discord_timestamp'],
                inline=True
            )
            
            embed.add_field(
                name="🏷️ Event Type",
                value=event_data['event_type_display'],
                inline=True
            )
            
            if event_data['description']:
                embed.add_field(
                    name="📝 Description",
                    value=event_data['description'][:1000],  # Limit description length
                    inline=False
                )
            
            # Add participant info
            embed.add_field(
                name="👥 Participants",
                value=f"{event_data['participant_count']} participants",
                inline=True
            )
            
            # Add CryptoTommys points if configured
            if event_data.get('points_per_participant', 0) > 0:
                embed.add_field(
                    name="💰 CryptoTommys",
                    value=f"{event_data['points_per_participant']} points per participant",
                    inline=True
                )
            
            # Add footer with instructions
            embed.set_footer(
                text="React with ✅ to join this event! Use !menu to see all available commands."
            )
            
            # Create a view with the Check Party button
            view = CheckPartyView(event_data['event_id'], self)
            
            # Send the announcement with the button
            message = await announcement_channel.send(embed=embed, view=view)
            
            # Add reaction for joining
            await message.add_reaction("✅")
            
            # Update the event record with Discord message info
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def update_event_discord_info():
                from .models import Event
                event = Event.objects.get(id=event_data['event_id'])
                event.discord_message_id = message.id
                event.discord_channel_id = announcement_channel.id
                event.save()
                return event
            
            await update_event_discord_info()
            
            return True, f"Event announcement posted successfully in {announcement_channel.mention}"
            
        except Exception as e:
            return False, f"Error posting event announcement: {str(e)}"
    
    async def monitor_commands(self):
        """Monitor for commands from the API"""
        import time
        from .bot_communication import get_bot_command, mark_command_processed, cleanup_old_commands
        
        print("🔍 Starting command monitoring...")
        
        try:
            while True:
                try:
                    # Check for new commands
                    command = get_bot_command()
                    if command and not command.get('processed', False):
                        print(f"🤖 Received command: {command['command']}")
                        
                        # Process the command
                        if command['command'] == 'publish_event':
                            print(f"📢 Processing publish_event command...")
                            success, message = await self.publish_event_announcement(command['data'])
                            if success:
                                print(f"✅ Event published: {message}")
                            else:
                                print(f"❌ Failed to publish event: {message}")
                        
                        # Mark command as processed
                        mark_command_processed()
                        print(f"✅ Command processed and marked as complete")
                    else:
                        # Only print every 30 seconds to avoid spam
                        if int(time.time()) % 30 == 0:
                            print("🔍 Monitoring for commands...")
                    
                    # Clean up old commands
                    cleanup_old_commands()
                    
                    # Wait before checking again
                    await asyncio.sleep(2)  # Check every 2 seconds
                    
                except Exception as e:
                    print(f"❌ Error in command monitoring loop: {e}")
                    await asyncio.sleep(5)  # Wait longer on error
        except Exception as e:
            print(f"❌ Critical error in command monitoring: {e}")
            import traceback
            traceback.print_exc()
    
    
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
                # Store the reaction so we can remove it if needed
                self._current_reaction = reaction
                success = await self.add_event_participant(event, user)
                # Only update embed if participant was successfully added
                if success:
                    await self.update_event_embed(event, reaction.message)
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
                        return False, "already_participating"  # Already participating
                    else:
                        # Reactivate
                        existing.is_active = True
                        existing.save()
                        return True, "reactivated"
                else:
                    # Check if user has a Player first
                    player = Player.objects.filter(discord_user_id=user.id).first()
                    
                    if not player:
                        return False, "no_player"  # User doesn't have a player
                    
                    # Events have unlimited participants, so no need to check if "full"
                    # The max_participants field represents party size limit, not event limit
                    
                    # Create new participant
                    EventParticipant.objects.create(
                        event=event,
                        discord_user_id=user.id,
                        discord_name=str(user),
                        player=player
                    )
                    return True, "created"
            
            success, reason = await add_participant()
            
            if not success:
                # Try to remove the reaction and send appropriate message
                try:
                    # Find the reaction message to remove the reaction
                    if hasattr(self, '_current_reaction'):
                        await self._current_reaction.remove(user)
                    
                    if reason == "already_participating":
                        await user.send(f"ℹ️ You're already participating in **{event.title}**!")
                    elif reason == "no_player":
                        await user.send(
                            f"❌ **Cannot join event without a player!**\n\n"
                            f"You need to create a player first before joining **{event.title}**.\n\n"
                            f"📋 **Instructions:**\n"
                            f"1. Go to the **#talk-to-violence-bot** channel\n"
                            f"2. Type `!menu`\n"
                            f"3. Click on **Create Player**\n"
                            f"4. Then react with ✅ again to join the event!"
                        )
                except Exception as e:
                    print(f"Error removing reaction or sending DM: {e}")
                
                return False  # Return False to indicate failure
            else:
                return True  # Return True to indicate success
            
        except Exception as e:
            print(f"Error adding event participant: {e}")
            return False
    
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

    async def create_guild_balanced_parties(self, event):
        """Create guild-based balanced parties for an event"""
        from asgiref.sync import sync_to_async
        from .models import Party, PartyMember, EventParticipant, Guild
        
        @sync_to_async
        def create_guild_parties():
            # Get all active participants with their players and guilds
            participants = list(EventParticipant.objects.filter(
                event=event,
                is_active=True,
                player__isnull=False
            ).select_related('player', 'player__guild'))
            
            if len(participants) < 2:
                return False, "At least 2 participants needed to create guild parties"
            
            # Clear existing parties for this event
            Party.objects.filter(event=event).delete()
            
            # Group participants by guild
            participants_by_guild = {}
            for participant in participants:
                guild = participant.player.guild
                guild_name = guild.name if guild else "No Guild"
                if guild_name not in participants_by_guild:
                    participants_by_guild[guild_name] = []
                participants_by_guild[guild_name].append(participant)
            
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
            total_parties_created = 0
            total_members_created = 0
            guild_results = []
            
            # Process each guild separately
            for guild_name, guild_participants in participants_by_guild.items():
                if len(guild_participants) < 2:
                    guild_results.append(f"{guild_name}: {len(guild_participants)} participants (minimum 2 needed)")
                    continue
                
                # Group participants by role within this guild
                participants_by_role = {}
                for participant in guild_participants:
                    role = participant.player.game_role or 'unknown'
                    if role not in participants_by_role:
                        participants_by_role[role] = []
                    participants_by_role[role].append(participant)
                
                # Calculate how many parties we need for this guild
                num_parties = max(1, (len(guild_participants) + MAX_PARTY_SIZE - 1) // MAX_PARTY_SIZE)
                
                # Create party objects for this guild
                parties = []
                for i in range(num_parties):
                    party = Party.objects.create(
                        event=event,
                        party_number=total_parties_created + i + 1,
                        max_members=MAX_PARTY_SIZE
                    )
                    parties.append(party)
                
                # Distribute participants across parties for this guild
                party_assignments = [[] for _ in range(num_parties)]
                party_role_counts = [{} for _ in range(num_parties)]
                
                # Initialize role counts
                for party_idx in range(num_parties):
                    for role in ROLE_REQUIREMENTS.keys():
                        party_role_counts[party_idx][role] = 0
                
                # Distribute participants by role, trying to balance within guild
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
                
                # Create PartyMember objects for this guild
                guild_members_created = 0
                for party_idx, party in enumerate(parties):
                    for participant in party_assignments[party_idx]:
                        PartyMember.objects.create(
                            party=party,
                            event_participant=participant,
                            player=participant.player,
                            assigned_role=participant.player.game_role
                        )
                        guild_members_created += 1
                
                total_parties_created += num_parties
                total_members_created += guild_members_created
                guild_results.append(f"{guild_name}: {num_parties} parties with {guild_members_created} participants")
            
            # Create summary message
            result_message = f"Guild parties created successfully:\n"
            result_message += f"Total: {total_parties_created} parties with {total_members_created} participants\n\n"
            result_message += "Guild breakdown:\n"
            for result in guild_results:
                result_message += f"• {result}\n"
            
            return True, result_message
        
        return await create_guild_parties()


def run_bot():
    """Run the Discord bot"""
    try:
        # Setup Django
        import django
        from django.conf import settings
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_dev')
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
    
