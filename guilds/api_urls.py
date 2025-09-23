from django.urls import path
from . import api_views

urlpatterns = [
    path('stats/', api_views.guild_stats, name='guild_stats'),
    path('members/', api_views.guild_members, name='guild_members'),
    path('events/', api_views.recent_events, name='recent_events'),
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
]
