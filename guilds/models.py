from django.db import models


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