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
    
    # Recommended Builds URL
    path('recommended-builds/', views.recommended_builds, name='recommended_builds'),
    
    # Discord Bot Management URLs
    path('bot/management/', views.bot_management, name='bot_management'),
    path('bot/start/', views.start_bot, name='start_bot'),
    path('bot/stop/', views.stop_bot, name='stop_bot'),
    path('bot/restart/', views.restart_bot, name='restart_bot'),
    path('bot/status/', views.bot_status, name='bot_status'),
]
