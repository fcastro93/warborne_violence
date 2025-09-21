from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from .models import Guild, Player, Drifter, GearType, GearItem, PlayerGear, GearMod, DiscordBotConfig, Event, EventParticipant, Party, PartyMember, RecommendedBuild


@admin.register(Guild)
class GuildAdmin(admin.ModelAdmin):
    list_display = ['name', 'faction', 'member_count', 'is_active', 'created_at']
    list_filter = ['faction', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Game Information', {
            'fields': ('faction',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def member_count(self, obj):
        return obj.member_count
    member_count.short_description = 'Active Members'


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0
    fields = ['in_game_name', 'discord_name', 'character_level', 'role', 'faction', 'is_active']
    readonly_fields = ['in_game_name']


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['in_game_name', 'discord_name', 'discord_owner', 'guild', 'character_level', 'role', 'game_role', 'faction', 'loadout_link', 'is_active']
    list_filter = ['guild', 'role', 'game_role', 'faction', 'is_active', 'created_at', 'discord_user_id']
    search_fields = ['in_game_name', 'discord_name', 'notes', 'discord_user_id']
    ordering = ['in_game_name']
    readonly_fields = ['created_at', 'updated_at', 'joined_guild_at', 'loadout_link', 'discord_owner']
    actions = ['view_loadout']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add custom labels
        form.base_fields['role'].label = 'Guild Rank'
        form.base_fields['game_role'].label = 'Game Role'
        return form
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('in_game_name', 'discord_name', 'discord_owner', 'guild', 'character_level')
        }),
        ('Game Information', {
            'fields': ('faction', 'drifter_1', 'drifter_2', 'drifter_3')
        }),
        ('Roles and Permissions', {
            'fields': ('role', 'game_role'),
            'description': 'role = Guild Rank (Member, Officer, etc.) | game_role = Game Role (Healer, Tank, etc.)'
        }),
        ('Discord Integration', {
            'fields': ('discord_user_id',),
            'description': 'Discord User ID of the player owner (set automatically when player is created via Discord bot)',
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'joined_guild_at')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Quick Actions', {
            'fields': ('loadout_link',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('guild', 'drifter_1', 'drifter_2', 'drifter_3')
    
    def loadout_link(self, obj):
        """Display a link to view the player's loadout"""
        if obj.pk:
            url = reverse('player_loadout', args=[obj.pk])
            return mark_safe(f'<a href="{url}" target="_blank" style="background: #4a90e2; color: white; padding: 5px 10px; border-radius: 5px; text-decoration: none; font-size: 12px;">🎮 View Loadout</a>')
        return '-'
    loadout_link.short_description = 'Loadout'
    loadout_link.allow_tags = True
    
    def discord_owner(self, obj):
        """Display Discord owner information"""
        if obj.discord_user_id:
            return format_html('<span style="color: #5865F2; font-weight: bold;">🔗 {}</span>', obj.discord_user_id)
        return format_html('<span style="color: #888;">Sin propietario</span>')
    discord_owner.short_description = 'Discord Owner'
    
    def view_loadout(self, request, queryset):
        """Admin action to view loadout for selected players"""
        if queryset.count() == 1:
            player = queryset.first()
            url = reverse('player_loadout', args=[player.pk])
            return redirect(url)
        else:
            self.message_user(request, "Please select only one player to view their loadout.")
    view_loadout.short_description = "View selected player's loadout"


@admin.register(Drifter)
class DrifterAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_health', 'base_energy', 'base_damage', 'base_defense', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'special_abilities']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'special_abilities')
        }),
        ('Base Stats', {
            'fields': ('base_health', 'base_energy', 'base_damage', 'base_defense', 'base_speed')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(GearType)
class GearTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'item_count']
    list_filter = ['category']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'


@admin.register(GearItem)
class GearItemAdmin(admin.ModelAdmin):
    list_display = ['base_name', 'skill_name', 'gear_type', 'rarity', 'required_level', 'damage', 'defense', 'is_craftable']
    list_filter = ['gear_type__category', 'rarity', 'required_level', 'is_craftable', 'is_tradeable']
    search_fields = ['base_name', 'skill_name', 'description']
    ordering = ['gear_type__category', 'rarity', 'required_level', 'base_name']
    readonly_fields = ['created_at'] if hasattr(GearItem, 'created_at') else []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('base_name', 'skill_name', 'gear_type', 'rarity', 'required_level', 'game_id')
        }),
        ('Statistics', {
            'fields': ('damage', 'defense', 'health_bonus', 'energy_bonus')
        }),
        ('Properties', {
            'fields': ('is_craftable', 'is_tradeable')
        }),
        ('Images', {
            'fields': ('icon_url',),
            'classes': ('collapse',)
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('gear_type')


@admin.register(PlayerGear)
class PlayerGearAdmin(admin.ModelAdmin):
    list_display = ['player', 'gear_item', 'is_equipped', 'is_favorite', 'mod_slots_used', 'acquired_at']
    list_filter = ['is_equipped', 'is_favorite', 'gear_item__gear_type__category', 'gear_item__rarity', 'acquired_at']
    search_fields = ['player__in_game_name', 'gear_item__base_name', 'gear_item__skill_name']
    ordering = ['-is_equipped', 'gear_item__base_name']
    readonly_fields = ['acquired_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('player', 'gear_item')
        }),
        ('Status', {
            'fields': ('is_equipped', 'is_favorite')
        }),
        ('Modifications', {
            'fields': ('mod_slots_used', 'mod_slots_max')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('acquired_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('player', 'gear_item__gear_type')


@admin.register(GearMod)
class GearModAdmin(admin.ModelAdmin):
    list_display = ['name', 'mod_type', 'rarity', 'damage_bonus', 'defense_bonus', 'is_active']
    list_filter = ['mod_type', 'rarity', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['rarity', 'mod_type', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'mod_type', 'rarity', 'description', 'game_id')
        }),
        ('Effects', {
            'fields': ('damage_bonus', 'defense_bonus', 'health_bonus', 'energy_bonus', 'speed_bonus')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


# Customize User admin to show player information
# Players are no longer linked to Users, so no custom UserAdmin needed

# Discord Bot Configuration Admin
@admin.register(DiscordBotConfig)
class DiscordBotConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'get_status_display', 'is_online', 'last_heartbeat', 'created_at']
    list_filter = ['is_active', 'is_online', 'created_at']
    search_fields = ['name', 'error_message']
    readonly_fields = ['is_online', 'last_heartbeat', 'error_message', 'created_at', 'updated_at']
    actions = ['start_bot', 'stop_bot', 'restart_bot', 'check_bot_status']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active', 'command_prefix', 'base_url')
        }),
        ('Bot Credentials', {
            'fields': ('bot_token', 'client_id', 'client_secret'),
            'description': 'These should be set from environment variables'
        }),
        ('Bot Status', {
            'fields': ('is_online', 'last_heartbeat', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Channel Configuration', {
            'fields': ('general_channel_id', 'event_announcements_channel_id', 'violence_bot_channel_id'),
            'description': 'Configure Discord channel IDs for bot functionality'
        }),
        ('Bot Permissions', {
            'fields': ('can_manage_messages', 'can_embed_links', 'can_attach_files', 
                      'can_read_message_history', 'can_use_external_emojis'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Status'
    
    def start_bot(self, request, queryset):
        for config in queryset:
            success, message = config.start_bot_manually()
            if success:
                self.message_user(request, f"Bot started: {message}")
            else:
                self.message_user(request, f"Failed to start bot: {message}", level='ERROR')
    start_bot.short_description = "Start Bot"
    
    def stop_bot(self, request, queryset):
        for config in queryset:
            success, message = config.stop_bot_manually()
            if success:
                self.message_user(request, f"Bot stopped: {message}")
            else:
                self.message_user(request, f"Failed to stop bot: {message}", level='ERROR')
    stop_bot.short_description = "Stop Bot"
    
    def restart_bot(self, request, queryset):
        for config in queryset:
            success, message = config.restart_bot_manually()
            if success:
                self.message_user(request, f"Bot restarted: {message}")
            else:
                self.message_user(request, f"Failed to restart bot: {message}", level='ERROR')
    restart_bot.short_description = "Restart Bot"
    
    def check_bot_status(self, request, queryset):
        for config in queryset:
            status = config.check_bot_status()
            if status:
                self.message_user(request, f"Bot status checked: Online")
            else:
                self.message_user(request, f"Bot status checked: Offline", level='WARNING')
    check_bot_status.short_description = "Check Bot Status"
    
    def has_add_permission(self, request):
        # Only allow one bot configuration
        return not DiscordBotConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of bot configuration
        return False


class EventParticipantInline(admin.TabularInline):
    model = EventParticipant
    extra = 0
    fields = ['discord_name', 'player', 'is_active', 'joined_at']
    readonly_fields = ['discord_name', 'joined_at']
    fk_name = 'event'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'event_datetime', 'participant_count_display', 'created_by_discord_name', 'is_active', 'is_cancelled']
    list_filter = ['event_type', 'is_active', 'is_cancelled', 'created_at', 'event_datetime']
    search_fields = ['title', 'description', 'created_by_discord_name']
    ordering = ['event_datetime']
    readonly_fields = ['created_at', 'updated_at', 'discord_message_id', 'discord_channel_id', 'discord_timestamp_display']
    inlines = [EventParticipantInline]
    
    fieldsets = (
        ('Event Information', {
            'fields': ('title', 'description', 'event_type', 'event_datetime', 'timezone')
        }),
        ('Discord Integration', {
            'fields': ('created_by_discord_name', 'discord_message_id', 'discord_channel_id', 'discord_timestamp_display'),
            'classes': ('collapse',)
        }),
        ('Event Management', {
            'fields': ('max_participants', 'is_active', 'is_cancelled')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def participant_count_display(self, obj):
        """Display participant count with color coding"""
        count = obj.participant_count
        if obj.max_participants:
            if count >= obj.max_participants:
                color = "#ff4444"  # Red if full
            elif count >= obj.max_participants * 0.8:
                color = "#ffaa00"  # Orange if almost full
            else:
                color = "#44ff44"  # Green if space available
            return format_html(
                '<span style="color: {};">{}/{} participants</span>',
                color, count, obj.max_participants
            )
        else:
            return format_html('<span style="color: #44ff44;">{} participants</span>', count)
    participant_count_display.short_description = 'Participants'
    
    def discord_timestamp_display(self, obj):
        """Display Discord timestamp"""
        if obj.event_datetime:
            return format_html(
                '<span style="font-family: monospace; background: #2f3136; padding: 2px 6px; border-radius: 3px;">{}</span>',
                obj.discord_timestamp
            )
        return "-"
    discord_timestamp_display.short_description = 'Discord Timestamp'


@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):
    list_display = ['discord_name', 'event_title', 'player', 'is_active', 'joined_at']
    list_filter = ['is_active', 'event__event_type', 'joined_at']
    search_fields = ['discord_name', 'event__title']
    ordering = ['-joined_at']
    readonly_fields = ['joined_at']
    
    def event_title(self, obj):
        """Display event title"""
        return obj.event.title
    event_title.short_description = 'Event'
    event_title.admin_order_field = 'event__title'


class PartyMemberInline(admin.TabularInline):
    model = PartyMember
    extra = 0
    fields = ['player', 'assigned_role', 'is_active', 'assigned_at']
    readonly_fields = ['assigned_at']
    fk_name = 'party'


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ['event_title', 'party_number', 'member_count_display', 'max_members', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'event__event_type']
    search_fields = ['event__title', 'party_number']
    ordering = ['event', 'party_number']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PartyMemberInline]
    
    fieldsets = (
        ('Party Information', {
            'fields': ('event', 'party_number', 'max_members', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def event_title(self, obj):
        return obj.event.title
    event_title.short_description = "Event"
    
    def member_count_display(self, obj):
        return f"{obj.member_count}/{obj.max_members}"
    member_count_display.short_description = "Members"


@admin.register(PartyMember)
class PartyMemberAdmin(admin.ModelAdmin):
    list_display = ['player_name', 'party_display', 'assigned_role', 'is_active', 'assigned_at']
    list_filter = ['is_active', 'assigned_role', 'assigned_at']
    search_fields = ['player__in_game_name', 'party__event__title']
    ordering = ['-assigned_at']
    readonly_fields = ['assigned_at']
    
    def player_name(self, obj):
        return obj.player.in_game_name
    player_name.short_description = "Player"
    
    def party_display(self, obj):
        return f"Party {obj.party.party_number} - {obj.party.event.title}"
    party_display.short_description = "Party"


@admin.register(RecommendedBuild)
class RecommendedBuildAdmin(admin.ModelAdmin):
    list_display = ['title', 'role_display', 'template_player_name', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'role', 'created_at', 'created_by']
    search_fields = ['title', 'description', 'template_player__in_game_name', 'created_by']
    ordering = ['role', 'title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Build Information', {
            'fields': ('title', 'description', 'role', 'is_active', 'created_by')
        }),
        ('Template Player', {
            'fields': ('template_player',),
            'description': 'Select the player whose loadout will serve as the template for this build.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = "Role"
    role_display.admin_order_field = 'role'
    
    def template_player_name(self, obj):
        return obj.template_player.in_game_name
    template_player_name.short_description = "Template Player"
    template_player_name.admin_order_field = 'template_player__in_game_name'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user.username if request.user.is_authenticated else "Admin"
        super().save_model(request, obj, form, change)


# Customize admin title
admin.site.site_header = "Warborne Above Ashes - Guild Tools"
admin.site.site_title = "Warborne Tools"
admin.site.index_title = "Administration Panel"