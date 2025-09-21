from django.urls import path
from . import views

urlpatterns = [
    path('player/<int:player_id>/loadout/', views.player_loadout, name='player_loadout'),
    path('player/<int:player_id>/loadout/update/', views.update_loadout, name='update_loadout'),
    path('player/<int:player_id>/assign-drifter/', views.assign_drifter, name='assign_drifter'),
    path('player/<int:player_id>/update-game-role/', views.update_game_role, name='update_game_role'),
    path('drifter/<int:drifter_id>/details/', views.drifter_details, name='drifter_details'),
]
