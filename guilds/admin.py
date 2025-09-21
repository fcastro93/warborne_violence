from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from .models import Guild, Player, Drifter, GearType, GearItem, PlayerGear, GearMod, DiscordBotConfig


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
    list_display = ['in_game_name', 'discord_name', 'guild', 'character_level', 'role', 'game_role', 'faction', 'loadout_link', 'is_active']
    list_filter = ['guild', 'role', 'game_role', 'faction', 'is_active', 'created_at']
    search_fields = ['in_game_name', 'discord_name', 'notes']
    ordering = ['in_game_name']
    readonly_fields = ['created_at', 'updated_at', 'joined_guild_at', 'loadout_link']
    actions = ['view_loadout']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add custom labels
        form.base_fields['role'].label = 'Guild Rank'
        form.base_fields['game_role'].label = 'Game Role'
        return form
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('in_game_name', 'discord_name', 'guild', 'character_level')
        }),
        ('Game Information', {
            'fields': ('faction', 'drifter_1', 'drifter_2', 'drifter_3')
        }),
        ('Roles and Permissions', {
            'fields': ('role', 'game_role'),
            'description': 'role = Guild Rank (Member, Officer, etc.) | game_role = Game Role (Healer, Tank, etc.)'
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
    actions = ['start_bot', 'stop_bot', 'restart_bot']
    
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
    
    def has_add_permission(self, request):
        # Only allow one bot configuration
        return not DiscordBotConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of bot configuration
        return False


# Customize admin title
admin.site.site_header = "Warborne Above Ashes - Guild Tools"
admin.site.site_title = "Warborne Tools"
admin.site.index_title = "Administration Panel"