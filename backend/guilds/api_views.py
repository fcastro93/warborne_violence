from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from .models import Guild, Player, Drifter, Event, GearItem, GearType, RecommendedBuild
import json

@api_view(['GET'])
def guild_stats(request):
    """Get guild statistics"""
    try:
        guild = Guild.objects.first()
        if not guild:
            return Response({'error': 'No guild found'}, status=status.HTTP_404_NOT_FOUND)
        
        total_members = Player.objects.count()
        active_events = Event.objects.filter(status='active').count()
        total_gear = GearItem.objects.count()
        
        # Faction distribution
        faction_counts = {}
        for player in Player.objects.all():
            faction = player.faction or 'Unknown'
            faction_counts[faction] = faction_counts.get(faction, 0) + 1
        
        return Response({
            'total_members': total_members,
            'active_events': active_events,
            'total_gear': total_gear,
            'faction_distribution': faction_counts,
            'guild_name': guild.name if guild else 'Unknown Guild'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def guild_members(request):
    """Get guild members list"""
    try:
        members = []
        for player in Player.objects.all()[:10]:  # Limit to 10 for now
            members.append({
                'id': player.id,
                'name': player.name,
                'role': player.role,
                'game_role': player.game_role,
                'faction': player.faction,
                'level': player.level,
                'status': 'Online' if player.is_active else 'Offline',
                'avatar': player.name[:2].upper() if player.name else 'XX',
                'drifters': [d.name for d in player.drifters.all()[:3]]
            })
        
        return Response({'members': members})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def recent_events(request):
    """Get recent events"""
    try:
        events = []
        for event in Event.objects.all()[:5]:  # Limit to 5
            events.append({
                'id': event.id,
                'title': event.name,
                'type': event.event_type,
                'participants': event.participants.count(),
                'status': event.status,
                'time': event.start_time.strftime('%Y-%m-%d %H:%M') if event.start_time else 'TBD',
                'organizer': event.organizer.name if event.organizer else 'Unknown'
            })
        
        return Response({'events': events})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def gear_overview(request):
    """Get gear overview"""
    try:
        gear_items = []
        for item in GearItem.objects.all()[:5]:  # Limit to 5
            gear_items.append({
                'id': item.id,
                'name': item.name,
                'skill': item.skill_name or 'Unknown Skill',
                'type': item.gear_type.name if item.gear_type else 'Unknown',
                'rarity': item.rarity or 'common',
                'stats': {
                    'damage': getattr(item, 'damage', 0),
                    'defense': getattr(item, 'defense', 0),
                    'health': getattr(item, 'health', 0)
                },
                'equipped': getattr(item, 'is_equipped', False),
                'owner': item.owner.name if item.owner else 'Unknown'
            })
        
        return Response({'gear_items': gear_items})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def recommended_builds(request):
    """Get recommended builds"""
    try:
        builds = []
        for build in RecommendedBuild.objects.all()[:4]:  # Limit to 4
            builds.append({
                'id': build.id,
                'title': build.name,
                'role': build.role,
                'description': build.description,
                'gear': [item.name for item in build.recommended_gear.all()[:2]],
                'mods': [mod.name for mod in build.recommended_mods.all()[:2]],
                'rating': getattr(build, 'rating', 4.5)
            })
        
        return Response({'builds': builds})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
