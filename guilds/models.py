from django.db import models
from django.utils import timezone


class Guild(models.Model):
    """Model to represent a guild in Warborne Above Ashes"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Game information
    faction = models.CharField(
        max_length=50,
        choices=[
            ('none', 'No Faction'),
            ('emberwild', 'Emberwild'),
            ('magnates', 'Magnates'),
            ('ashen', 'Ashen'),
            ('ironcreed', 'Ironcreed'),
            ('sirius', 'Sirius'),
            ('shroud', 'Shroud'),
        ],
        default='none'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = "Guild"
        verbose_name_plural = "Guilds"
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self):
        return self.players.filter(is_active=True).count()


class Drifter(models.Model):
    """Model to represent a Drifter (character class) in Warborne Above Ashes"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Drifter stats
    base_health = models.IntegerField(default=100)
    base_energy = models.IntegerField(default=100)
    base_damage = models.IntegerField(default=50)
    base_defense = models.IntegerField(default=25)
    base_speed = models.IntegerField(default=10)
    
    # Special abilities or traits
    special_abilities = models.TextField(blank=True, null=True, help_text="Special abilities or traits")
    
    # Game data
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Drifter"
        verbose_name_plural = "Drifters"
    
    def __str__(self):
        return self.name


class Player(models.Model):
    """Model to represent a player in Warborne Above Ashes"""
    guild = models.ForeignKey(Guild, on_delete=models.SET_NULL, null=True, blank=True, related_name='players')
    
    # Player information
    in_game_name = models.CharField(max_length=100, unique=True)
    discord_name = models.CharField(max_length=100, default="", help_text="Discord username (e.g., PlayerName#1234)")
    discord_user_id = models.BigIntegerField(null=True, blank=True, help_text="Discord User ID of the player owner")
    character_level = models.IntegerField(default=1)
    faction = models.CharField(
        max_length=50,
        choices=[
            ('none', 'No Faction'),
            ('emberwild', 'Emberwild'),
            ('magnates', 'Magnates'),
            ('ashen', 'Ashen'),
            ('ironcreed', 'Ironcreed'),
            ('sirius', 'Sirius'),
            ('shroud', 'Shroud'),
        ],
        default='none'
    )
    
    # Drifter selection (3 drifters per player)
    drifter_1 = models.ForeignKey(Drifter, on_delete=models.SET_NULL, null=True, blank=True, related_name='drifter_1_players', verbose_name="Drifter 1")
    drifter_2 = models.ForeignKey(Drifter, on_delete=models.SET_NULL, null=True, blank=True, related_name='drifter_2_players', verbose_name="Drifter 2")
    drifter_3 = models.ForeignKey(Drifter, on_delete=models.SET_NULL, null=True, blank=True, related_name='drifter_3_players', verbose_name="Drifter 3")
    
    # Roles and permissions
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('officer', 'Officer'),
        ('leader', 'Leader'),
        ('recruiter', 'Recruiter'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    
    # Game role/playstyle
    GAME_ROLE_CHOICES = [
        ('ranged_dps', 'Ranged DPS'),
        ('melee_dps', 'Melee DPS'),
        ('tank', 'Tank'),
        ('healer', 'Healer'),
        ('defensive_tank', 'Defensive Tank'),
        ('offensive_tank', 'Offensive Tank'),
        ('offensive_support', 'Offensive Support'),
        ('defensive_support', 'Defensive Support'),
    ]
    game_role = models.CharField(
        max_length=20, 
        choices=GAME_ROLE_CHOICES, 
        null=True, 
        blank=True,
        help_text="Primary role/playstyle in the game"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    joined_guild_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional information
    notes = models.TextField(blank=True, null=True, help_text="Notes about the player")
    
    class Meta:
        ordering = ['in_game_name']
        verbose_name = "Player"
        verbose_name_plural = "Players"
    
    def __str__(self):
        return f"{self.in_game_name} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        if self.guild and not self.joined_guild_at:
            from django.utils import timezone
            self.joined_guild_at = timezone.now()
        super().save(*args, **kwargs)
    
    def is_owner(self, discord_user_id):
        """Check if a Discord user is the owner of this player"""
        return self.discord_user_id == discord_user_id
    
    def can_modify(self, discord_user_id, is_staff=False):
        """Check if a Discord user can modify this player (owner or staff)"""
        return is_staff or self.is_owner(discord_user_id)


class GearType(models.Model):
    """Available gear types in the game"""
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ('weapon', 'Weapon'),
            ('armor', 'Armor'),
            ('accessory', 'Accessory'),
            ('vehicle', 'Vehicle'),
            ('tactical', 'Tactical'),
            ('mod', 'Mod'),
        ]
    )
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Gear Type"
        verbose_name_plural = "Gear Types"
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class GearItem(models.Model):
    """Specific gear items"""
    base_name = models.CharField(max_length=200, help_text="Base item name (e.g., 'Energizer Boots')")
    skill_name = models.CharField(max_length=200, blank=True, help_text="Associated skill name (e.g., 'Vitality')")
    gear_type = models.ForeignKey(GearType, on_delete=models.CASCADE, related_name='items')
    
    # Item statistics
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    
    # Required level
    required_level = models.IntegerField(default=1)
    
    # Base statistics
    damage = models.FloatField(default=0, help_text="Damage bonus percentage")
    defense = models.IntegerField(default=0, help_text="Base defense of the item")
    health_bonus = models.IntegerField(default=0, help_text="Health bonus")
    energy_bonus = models.IntegerField(default=0, help_text="Energy bonus")
    mana_recovery = models.IntegerField(default=0, help_text="Mana recovery value")
    armor = models.IntegerField(default=0, help_text="Armor value")
    magic_resistance = models.IntegerField(default=0, help_text="Magic resistance value")
    
    # Additional information
    description = models.TextField(blank=True, null=True)
    is_craftable = models.BooleanField(default=False)
    is_tradeable = models.BooleanField(default=True)
    
    # Detailed weapon/skill data
    mana_cost = models.IntegerField(null=True, blank=True, help_text="Mana cost for skills")
    cooldown = models.CharField(max_length=20, blank=True, null=True, help_text="Cooldown time (e.g., '19s', '11s')")
    casting_range = models.CharField(max_length=20, blank=True, null=True, help_text="Casting range (e.g., '12m', '7m')")
    skill_type = models.CharField(max_length=50, blank=True, null=True, help_text="Type of skill (basic, skill, ultimate, passive)")
    tier_unlock = models.CharField(max_length=10, blank=True, null=True, help_text="Tier unlock requirement")
    
    # Detailed stats (JSON field for flexible stats)
    detailed_stats = models.JSONField(null=True, blank=True, help_text="Detailed stats like attackPower, tenacity, etc.")
    
    # Image support
    icon_url = models.URLField(blank=True, null=True, help_text="URL to item icon")
    # icon_file = models.ImageField(upload_to='item_icons/', blank=True, null=True)  # Disabled for local dev
    
    # Game data source
    game_id = models.CharField(max_length=100, blank=True, null=True, help_text="Original game ID for reference")
    
    class Meta:
        ordering = ['gear_type__category', 'rarity', 'required_level', 'base_name']
        verbose_name = "Gear Item"
        verbose_name_plural = "Gear Items"
    
    @property
    def name(self):
        """Return the full name with skill if skill_name exists"""
        if self.skill_name:
            return f"{self.base_name} ({self.skill_name})"
        return self.base_name
    
    
    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"


class PlayerGear(models.Model):
    """Gear owned by a player"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='gear_items')
    gear_item = models.ForeignKey(GearItem, on_delete=models.CASCADE)
    
    # Which drifter is using this gear (1, 2, or 3)
    DRIFTER_CHOICES = [
        (1, 'Drifter 1'),
        (2, 'Drifter 2'),
        (3, 'Drifter 3'),
    ]
    equipped_on_drifter = models.IntegerField(choices=DRIFTER_CHOICES, null=True, blank=True, help_text="Which drifter is using this gear")
    
    # Gear status
    is_equipped = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    
    # Modifications
    mod_slots_used = models.IntegerField(default=0)
    mod_slots_max = models.IntegerField(default=0)
    
    # Additional information
    acquired_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['player', 'gear_item']
        ordering = ['-is_equipped', 'gear_item__base_name']
        verbose_name = "Player Gear"
        verbose_name_plural = "Player Gear"
    
    def __str__(self):
        return f"{self.player.in_game_name} - {self.gear_item.name}"


class GearMod(models.Model):
    """Mods that can be applied to gear"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Mod type
    MOD_TYPE_CHOICES = [
        ('damage', 'Damage'),
        ('defense', 'Defense'),
        ('health', 'Health'),
        ('energy', 'Energy'),
        ('speed', 'Speed'),
        ('special', 'Special'),
    ]
    mod_type = models.CharField(max_length=20, choices=MOD_TYPE_CHOICES)
    
    # Mod rarity
    RARITY_CHOICES = [
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES)
    
    # Mod effects
    damage_bonus = models.IntegerField(default=0)
    defense_bonus = models.IntegerField(default=0)
    health_bonus = models.IntegerField(default=0)
    energy_bonus = models.IntegerField(default=0)
    speed_bonus = models.IntegerField(default=0)
    
    # Additional information
    is_active = models.BooleanField(default=True)
    
    # Game data source
    game_id = models.CharField(max_length=100, blank=True, null=True, help_text="Original game ID for reference")
    
    class Meta:
        ordering = ['rarity', 'mod_type', 'name']
        verbose_name = "Gear Mod"
        verbose_name_plural = "Gear Mods"
    
    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"


class DiscordBotConfig(models.Model):
    """Model to store Discord bot configuration"""
    name = models.CharField(max_length=100, default="Warborne Bot")
    is_active = models.BooleanField(default=False, help_text="Whether the bot is currently active")
    
    # Bot credentials (stored in environment variables)
    bot_token = models.CharField(max_length=200, blank=True, help_text="Discord bot token (from environment)")
    client_id = models.CharField(max_length=100, blank=True, help_text="Discord client ID (from environment)")
    client_secret = models.CharField(max_length=200, blank=True, help_text="Discord client secret (from environment)")
    
    # Bot settings
    command_prefix = models.CharField(max_length=10, default="/", help_text="Command prefix for the bot")
    base_url = models.URLField(default="http://127.0.0.1:8000", help_text="Base URL for the application")
    
    # Bot status
    is_online = models.BooleanField(default=False, help_text="Whether the bot is currently online")
    
    # Channel configuration
    general_channel_id = models.BigIntegerField(null=True, blank=True, help_text="ID of the general channel for bot announcements")
    event_announcements_channel_id = models.BigIntegerField(null=True, blank=True, help_text="ID of the channel where event announcements are posted")
    violence_bot_channel_id = models.BigIntegerField(null=True, blank=True, help_text="ID of the violence-bot channel where events are created")
    last_heartbeat = models.DateTimeField(null=True, blank=True, help_text="Last heartbeat from the bot")
    error_message = models.TextField(blank=True, help_text="Last error message from the bot")
    
    # Bot permissions
    can_manage_messages = models.BooleanField(default=True)
    can_embed_links = models.BooleanField(default=True)
    can_attach_files = models.BooleanField(default=True)
    can_read_message_history = models.BooleanField(default=True)
    can_use_external_emojis = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Discord Bot Configuration"
        verbose_name_plural = "Discord Bot Configurations"
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    
    def get_status_display(self):
        """Get a human-readable status"""
        if self.is_online:
            return "🟢 Online"
        elif self.is_active:
            return "🟡 Active (Offline)"
        else:
            return "🔴 Inactive"
    
    def start_bot_manually(self):
        """Start the bot manually"""
        try:
            import threading
            import os
            import django
            from django.conf import settings
            from .discord_bot import WarborneBot
            
            if not self.is_online:
                def run_bot_in_thread():
                    """Run bot in thread with proper Django setup"""
                    try:
                        # Ensure Django is configured
                        if not settings.configured:
                            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_production')
                            django.setup()
                        
                        # Create and run bot
                        bot = WarborneBot()
                        bot.run(self.bot_token or os.getenv('DISCORD_BOT_TOKEN'))
                    except Exception as e:
                        print(f"Bot thread error: {e}")
                        # Update status in database
                        config = DiscordBotConfig.objects.first()
                        if config:
                            config.is_online = False
                            config.error_message = str(e)
                            config.save()
                
                # Start bot in background thread
                bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
                bot_thread.start()
                
                self.is_online = True
                self.error_message = ""
                self.save()
                
                return True, "Bot started successfully"
            else:
                return False, "Bot is already running"
                
        except Exception as e:
            self.error_message = str(e)
            self.save()
            return False, f"Error starting bot: {str(e)}"
    
    def stop_bot_manually(self):
        """Stop the bot manually"""
        try:
            self.is_online = False
            self.error_message = ""
            self.save()
            return True, "Bot stopped successfully"
        except Exception as e:
            self.error_message = str(e)
            self.save()
            return False, f"Error stopping bot: {str(e)}"
    
    def check_bot_status(self):
        """Check if bot is actually running"""
        try:
            # This is a simple check - in production you might want to ping the bot
            # or check if the Discord connection is active
            return self.is_online
        except Exception as e:
            self.is_online = False
            self.error_message = str(e)
            self.save()
            return False
    
    def restart_bot_manually(self):
        """Restart the bot manually"""
        try:
            # Stop the bot first
            self.stop_bot_manually()
            
            # Wait a bit for cleanup
            import time
            time.sleep(3)
            
            # Start the bot again
            return self.start_bot_manually()
        except Exception as e:
            self.error_message = str(e)
            self.save()
            return False, f"Error restarting bot: {str(e)}"


class Event(models.Model):
    """Model to represent guild events created via Discord"""
    # Event basic information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('guild_war', 'Guild War'),
            ('pvp_fight', 'PvP Fight'),
            ('resource_farming', 'Resource Farming'),
            ('boss_raid', 'Boss Raid'),
            ('social_event', 'Social Event'),
            ('training', 'Training'),
            ('other', 'Other'),
        ],
        default='other'
    )
    
    # Discord integration
    discord_message_id = models.BigIntegerField(null=True, blank=True, help_text="Discord message ID of the event post")
    discord_channel_id = models.BigIntegerField(null=True, blank=True, help_text="Discord channel ID where event was posted")
    created_by_discord_id = models.BigIntegerField(help_text="Discord User ID of event creator")
    created_by_discord_name = models.CharField(max_length=100, help_text="Discord username of event creator")
    
    # Event scheduling
    event_datetime = models.DateTimeField(help_text="When the event will take place (UTC)")
    timezone = models.CharField(max_length=50, default='UTC', help_text="IANA timezone name (e.g., 'America/New_York')")
    
    # Event management
    max_participants = models.IntegerField(null=True, blank=True, help_text="Maximum number of participants (null = unlimited)")
    is_active = models.BooleanField(default=True, help_text="Whether the event is still active")
    is_cancelled = models.BooleanField(default=False, help_text="Whether the event was cancelled")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['event_datetime']
        verbose_name = "Event"
        verbose_name_plural = "Events"
    
    def __str__(self):
        return f"{self.title} - {self.event_datetime.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def participant_count(self):
        """Get the number of participants"""
        return self.participants.filter(is_active=True).count()
    
    def get_participant_count_sync(self):
        """Sync version of participant count for use with sync_to_async"""
        return self.participants.filter(is_active=True).count()
    
    @property
    def discord_epoch(self):
        """Get Unix epoch timestamp for Discord timestamps"""
        import calendar
        # Ensure we have a timezone-aware datetime
        if self.event_datetime.tzinfo is None:
            # If naive, assume UTC
            from django.utils import timezone
            dt = timezone.make_aware(self.event_datetime, timezone.utc)
        else:
            dt = self.event_datetime
        return int(dt.timestamp())
    
    @property
    def discord_timestamp(self):
        """Generate Discord timestamp for the event datetime"""
        return f"<t:{self.discord_epoch}:F>"  # Full date and time format
    
    @property
    def discord_timestamp_relative(self):
        """Generate Discord relative timestamp for the event datetime"""
        return f"<t:{self.discord_epoch}:R>"  # Relative time format


class EventParticipant(models.Model):
    """Model to track event participants"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participants')
    discord_user_id = models.BigIntegerField(help_text="Discord User ID of participant")
    discord_name = models.CharField(max_length=100, help_text="Discord username of participant")
    
    # Player information (if they have a player created)
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='event_participations')
    
    # Participation status
    is_active = models.BooleanField(default=True, help_text="Whether the participant is still active")
    joined_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True, help_text="Notes about the participant")
    
    class Meta:
        unique_together = ['event', 'discord_user_id']
        ordering = ['joined_at']
        verbose_name = "Event Participant"
        verbose_name_plural = "Event Participants"
    
    def __str__(self):
        return f"{self.discord_name} - {self.event.title}"


class Party(models.Model):
    """Model for event parties/groups"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='parties')
    party_number = models.IntegerField(help_text="Party number within the event (1, 2, 3, etc.)")
    max_members = models.IntegerField(default=15, help_text="Maximum members per party")
    is_active = models.BooleanField(default=True, help_text="Whether the party is still active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['event', 'party_number']
        ordering = ['party_number']
        verbose_name = "Party"
        verbose_name_plural = "Parties"
    
    @property
    def member_count(self):
        return self.members.filter(is_active=True).count()
    
    @property
    def role_distribution(self):
        """Get role distribution for this party"""
        from collections import Counter
        roles = self.members.filter(is_active=True).values_list('player__game_role', flat=True)
        return Counter(roles)
    
    def __str__(self):
        return f"Party {self.party_number} - {self.event.title}"


class PartyMember(models.Model):
    """Model for party members"""
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='members')
    event_participant = models.ForeignKey(EventParticipant, on_delete=models.CASCADE, related_name='party_assignments')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='party_assignments')
    assigned_role = models.CharField(
        max_length=20,
        choices=Player.GAME_ROLE_CHOICES,
        null=True,
        blank=True,
        help_text="Role assigned in this party (may differ from player's default role)"
    )
    is_active = models.BooleanField(default=True, help_text="Whether the member is still active in the party")
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['party', 'event_participant']
        ordering = ['assigned_at']
        verbose_name = "Party Member"
        verbose_name_plural = "Party Members"
    
    def __str__(self):
        return f"{self.player.in_game_name} - {self.party}"


class RecommendedBuild(models.Model):
    """Model for recommended build templates"""
    title = models.CharField(max_length=100, help_text="Build title/name")
    description = models.TextField(blank=True, help_text="Build description and strategy")
    role = models.CharField(
        max_length=20,
        choices=Player.GAME_ROLE_CHOICES,
        help_text="Role this build is designed for"
    )
    
    # Equipment fields - store gear directly instead of referencing a player
    drifter = models.ForeignKey(
        Drifter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Primary drifter for this build"
    )
    weapon = models.ForeignKey(
        GearItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_weapon',
        help_text="Weapon for this build"
    )
    helmet = models.ForeignKey(
        GearItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_helmet',
        help_text="Helmet for this build"
    )
    chest = models.ForeignKey(
        GearItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_chest',
        help_text="Chest piece for this build"
    )
    boots = models.ForeignKey(
        GearItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_boots',
        help_text="Boots for this build"
    )
    consumable = models.ForeignKey(
        GearItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_consumable',
        help_text="Consumable for this build"
    )
    mod1 = models.ForeignKey(
        GearMod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_mod1',
        help_text="Mod 1 for this build"
    )
    mod2 = models.ForeignKey(
        GearMod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_mod2',
        help_text="Mod 2 for this build"
    )
    mod3 = models.ForeignKey(
        GearMod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_mod3',
        help_text="Mod 3 for this build"
    )
    mod4 = models.ForeignKey(
        GearMod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommended_builds_mod4',
        help_text="Mod 4 for this build"
    )
    
    is_active = models.BooleanField(default=True, help_text="Whether this build is currently recommended")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, default="Admin", help_text="Who created this build recommendation")
    
    class Meta:
        ordering = ['role', 'title']
        verbose_name = "Recommended Build"
        verbose_name_plural = "Recommended Builds"
    
    def __str__(self):
        return f"{self.title} ({self.get_role_display()})"
    
    @property
    def build_url(self):
        """Get the URL to edit this build"""
        return f"/guilds/recommended-build/{self.id}/edit/"
    
    @property
    def equipped_items(self):
        """Get list of equipped items"""
        items = []
        if self.weapon:
            items.append(('weapon', self.weapon))
        if self.helmet:
            items.append(('helmet', self.helmet))
        if self.chest:
            items.append(('chest', self.chest))
        if self.boots:
            items.append(('boots', self.boots))
        if self.consumable:
            items.append(('consumable', self.consumable))
        return items
    
    @property
    def equipped_mods(self):
        """Get list of equipped mods"""
        mods = []
        if self.mod1:
            mods.append(('mod1', self.mod1))
        if self.mod2:
            mods.append(('mod2', self.mod2))
        if self.mod3:
            mods.append(('mod3', self.mod3))
        if self.mod4:
            mods.append(('mod4', self.mod4))
        return mods