from django.urls import path
from . import api_views

urlpatterns = [
    path('stats/', api_views.guild_stats, name='guild_stats'),
    path('members/', api_views.guild_members, name='guild_members'),
    path('events/', api_views.recent_events, name='recent_events'),
    path('gear/', api_views.gear_overview, name='gear_overview'),
    path('builds/', api_views.recommended_builds, name='recommended_builds'),
]
