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
        active_events = Event.objects.filter(is_active=True, is_cancelled=False).count()
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
            # Get drifters from the three drifter fields
            drifters = []
            if player.drifter_1:
                drifters.append(player.drifter_1.name)
            if player.drifter_2:
                drifters.append(player.drifter_2.name)
            if player.drifter_3:
                drifters.append(player.drifter_3.name)
            
            members.append({
                'id': player.id,
                'name': player.in_game_name,
                'role': player.role,
                'game_role': player.game_role,
                'faction': player.faction,
                'level': player.character_level,
                'status': 'Online' if player.is_active else 'Offline',
                'avatar': player.in_game_name[:2].upper() if player.in_game_name else 'XX',
                'drifters': drifters
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
            # Determine status based on is_active and is_cancelled
            if event.is_cancelled:
                status = 'Cancelled'
            elif event.is_active:
                status = 'Active'
            else:
                status = 'Inactive'
            
            events.append({
                'id': event.id,
                'title': event.title,
                'type': event.event_type,
                'participants': event.participant_count,
                'status': status,
                'time': event.event_datetime.strftime('%Y-%m-%d %H:%M') if event.event_datetime else 'TBD',
                'organizer': event.created_by_discord_name if event.created_by_discord_name else 'Unknown'
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
                'name': item.base_name,
                'skill': item.skill_name or 'Unknown Skill',
                'type': item.gear_type.name if item.gear_type else 'Unknown',
                'rarity': item.rarity or 'common',
                'stats': {
                    'damage': item.damage,
                    'defense': item.defense,
                    'health': item.health_bonus
                },
                'equipped': False,  # GearItem doesn't have an equipped field
                'owner': 'Guild'  # Gear items are guild-owned
            })
        
        return Response({'gear_items': gear_items})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def recommended_builds(request):
    """Get recommended builds"""
    try:
        builds = []
        for build in RecommendedBuild.objects.filter(is_active=True)[:4]:  # Limit to 4
            # Get gear items
            gear_items = []
            if build.weapon:
                gear_items.append(build.weapon.base_name)
            if build.helmet:
                gear_items.append(build.helmet.base_name)
            if build.chest:
                gear_items.append(build.chest.base_name)
            if build.boots:
                gear_items.append(build.boots.base_name)
            if build.consumable:
                gear_items.append(build.consumable.base_name)
            
            # Get mods
            mod_items = []
            if build.mod1:
                mod_items.append(build.mod1.name)
            if build.mod2:
                mod_items.append(build.mod2.name)
            if build.mod3:
                mod_items.append(build.mod3.name)
            if build.mod4:
                mod_items.append(build.mod4.name)
            
            builds.append({
                'id': build.id,
                'title': build.title,
                'role': build.role,
                'description': build.description,
                'gear': gear_items[:2],  # Limit to 2 items
                'mods': mod_items[:2],   # Limit to 2 mods
                'rating': 4.5  # Default rating since it's not in the model
            })
        
        return Response({'builds': builds})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
