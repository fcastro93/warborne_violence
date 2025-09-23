from django.urls import path
from . import api_views

urlpatterns = [
    path('stats/', api_views.guild_stats, name='guild_stats'),
    path('members/', api_views.guild_members, name='guild_members'),
    path('recent-events/', api_views.recent_events, name='recent_events'),
    path('gear/', api_views.gear_overview, name='gear_overview'),
    path('gear-items/', api_views.gear_items, name='gear_items'),
    path('builds/', api_views.recommended_builds, name='recommended_builds'),
    path('builds/create/', api_views.create_recommended_build, name='create_recommended_build'),
    path('builds/<int:build_id>/assign-drifter/', api_views.assign_drifter_to_build, name='assign_drifter_to_build'),
    path('builds/<int:build_id>/equip-item/', api_views.equip_item_to_build, name='equip_item_to_build'),
    path('builds/<int:build_id>/unequip-item/', api_views.unequip_item_from_build, name='unequip_item_from_build'),
    path('drifters/', api_views.all_drifters, name='all_drifters'),
    
    # Player Loadout API endpoints
    path('player/<int:player_id>/', api_views.player_detail, name='player_detail'),
    path('player/<int:player_id>/drifters/', api_views.player_drifters, name='player_drifters'),
    path('player/<int:player_id>/update-drifter/', api_views.update_player_drifter, name='update_player_drifter'),
    path('player/<int:player_id>/equipped-gear/', api_views.player_equipped_gear, name='player_equipped_gear'),
    path('player/<int:player_id>/equip-gear/', api_views.equip_gear, name='equip_gear'),
    path('player/<int:player_id>/unequip-gear/', api_views.unequip_gear, name='unequip_gear'),
    
    # Event Management API endpoints
    path('events/', api_views.events_list, name='events_list'),
    path('events/<int:event_id>/', api_views.event_detail, name='event_detail'),
    path('events/create/', api_views.create_event, name='create_event'),
    path('events/<int:event_id>/update/', api_views.update_event, name='update_event'),
    path('events/<int:event_id>/delete/', api_views.delete_event, name='delete_event'),
    path('events/<int:event_id>/join/', api_views.join_event, name='join_event'),
    path('events/<int:event_id>/leave/', api_views.leave_event, name='leave_event'),
    path('events/<int:event_id>/publish/', api_views.publish_event, name='publish_event'),
    path('events/<int:event_id>/create-parties/', api_views.create_parties, name='create_parties'),
    path('events/<int:event_id>/create-guild-parties/', api_views.create_guild_parties, name='create_guild_parties'),
    path('events/<int:event_id>/participants/', api_views.event_participants, name='event_participants'),
    path('events/<int:event_id>/parties/', api_views.event_parties, name='event_parties'),
    path('events/<int:event_id>/remove-participant/', api_views.remove_participant, name='remove_participant'),
    path('events/<int:event_id>/fill-parties/', api_views.fill_parties, name='fill_parties'),
    path('events/<int:event_id>/party-configuration/', api_views.get_party_configuration, name='get_party_configuration'),
    path('events/<int:event_id>/save-party-configuration/', api_views.save_party_configuration, name='save_party_configuration'),
    path('discord-bot-config/', api_views.discord_bot_config, name='discord_bot_config'),
    path('discord-bot-config/update/', api_views.update_discord_bot_config, name='update_discord_bot_config'),
    path('discord-bot-config/test/', api_views.test_discord_bot_connection, name='test_discord_bot_connection'),
]
