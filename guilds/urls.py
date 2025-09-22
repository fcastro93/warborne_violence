from django.urls import path
from . import views

urlpatterns = [
    path('player/<int:player_id>/loadout/', views.player_loadout, name='player_loadout'),
    path('player/<int:player_id>/loadout/update/', views.update_loadout, name='update_loadout'),
    path('player/<int:player_id>/assign-drifter/', views.assign_drifter, name='assign_drifter'),
    path('player/<int:player_id>/update-game-role/', views.update_game_role, name='update_game_role'),
    path('player/<int:player_id>/update-name/', views.update_player_name, name='update_player_name'),
    path('player/<int:player_id>/check-permissions/', views.check_player_permissions, name='check_player_permissions'),
    path('drifter/<int:drifter_id>/details/', views.drifter_details, name='drifter_details'),
    
    # Recommended Builds URLs
    path('recommended-builds/', views.recommended_builds, name='recommended_builds'),
    path('recommended-build/<str:build_id>/edit/', views.edit_recommended_build, name='edit_recommended_build'),
    path('recommended-build/<str:build_id>/view/', views.view_recommended_build, name='view_recommended_build'),
    path('recommended-build/<str:build_id>/save/', views.save_recommended_build, name='save_recommended_build'),
    path('recommended-build/<str:build_id>/equipment/update/', views.update_recommended_build_equipment, name='update_recommended_build_equipment'),
    path('api/items/<str:slot_type>/', views.get_items_for_slot, name='get_items_for_slot'),
    
    # Staff Dashboard URLs
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('players/', views.players_management, name='players_management'),
    path('guilds/', views.guilds_management, name='guilds_management'),
    path('events/', views.events_management, name='events_management'),
    path('guild-analytics/', views.guild_analytics, name='guild_analytics'),
    path('event-analytics/', views.event_analytics, name='event_analytics'),
    path('bot-analytics/', views.bot_analytics, name='bot_analytics'),
    
    # Discord Bot Management URLs
    path('bot/management/', views.bot_management, name='bot_management'),
    path('bot/start/', views.start_bot, name='start_bot'),
    path('bot/stop/', views.stop_bot, name='stop_bot'),
    path('bot/restart/', views.restart_bot, name='restart_bot'),
    path('bot/status/', views.bot_status, name='bot_status'),
]
