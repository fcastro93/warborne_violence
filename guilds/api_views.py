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

# Player Loadout API endpoints
@api_view(['GET'])
def player_detail(request, player_id):
    """Get player details"""
    try:
        player = Player.objects.get(id=player_id)
        return Response({
            'id': player.id,
            'name': player.in_game_name,
            'discord_name': player.discord_name,
            'role': player.role,
            'game_role': player.game_role,
            'faction': player.faction,
            'level': player.character_level,
            'is_active': player.is_active,
            'created_at': player.created_at,
        })
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def player_drifters(request, player_id):
    """Get player's drifters"""
    try:
        player = Player.objects.get(id=player_id)
        drifters = []
        
        for i in range(1, 4):  # 3 drifters
            drifter = getattr(player, f'drifter_{i}', None)
            if drifter:
                drifters.append({
                    'number': i,
                    'name': drifter.name,
                    'base_health': getattr(drifter, 'base_health', 100),
                    'base_energy': getattr(drifter, 'base_energy', 100),
                    'base_damage': getattr(drifter, 'base_damage', 50),
                    'base_defense': getattr(drifter, 'base_defense', 25),
                })
            else:
                drifters.append({
                    'number': i,
                    'name': None,
                    'base_health': 100,
                    'base_energy': 100,
                    'base_damage': 50,
                    'base_defense': 25,
                })
        
        return Response({'drifters': drifters})
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def player_equipped_gear(request, player_id):
    """Get player's equipped gear"""
    try:
        player = Player.objects.get(id=player_id)
        
        # Get all equipped gear for this player
        equipped_gear = PlayerGear.objects.filter(
            player=player,
            is_equipped=True
        ).select_related('gear_item__gear_type')
        
        gear_data = {}
        for gear in equipped_gear:
            drifter_num = gear.equipped_on_drifter or 1
            if drifter_num not in gear_data:
                gear_data[drifter_num] = []
            
            gear_data[drifter_num].append({
                'id': gear.id,
                'gear_item_id': gear.gear_item.id,
                'name': gear.gear_item.base_name,
                'type': gear.gear_item.gear_type.category,
                'rarity': gear.gear_item.rarity,
                'skill_name': gear.gear_item.skill_name,
                'damage': gear.gear_item.damage,
                'defense': gear.gear_item.defense,
                'health_bonus': gear.gear_item.health_bonus,
                'slot_type': gear.gear_item.gear_type.category,
            })
        
        return Response({'equipped_gear': gear_data})
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def equip_gear(request, player_id):
    """Equip gear to a player's drifter"""
    try:
        player = Player.objects.get(id=player_id)
        data = request.data
        
        gear_id = data.get('gear_id')
        drifter_num = data.get('drifter_num', 1)
        slot_type = data.get('slot_type')
        
        if not gear_id:
            return Response({'error': 'gear_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the gear item
        gear_item = GearItem.objects.get(id=gear_id)
        
        # Check if player owns this gear
        player_gear, created = PlayerGear.objects.get_or_create(
            player=player,
            gear_item=gear_item,
            defaults={'is_equipped': False}
        )
        
        if not created and player_gear.is_equipped:
            return Response({'error': 'Gear is already equipped'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Unequip any gear in the same slot for this drifter
        PlayerGear.objects.filter(
            player=player,
            is_equipped=True,
            equipped_on_drifter=drifter_num,
            gear_item__gear_type__category=slot_type
        ).update(is_equipped=False, equipped_on_drifter=None)
        
        # Equip the new gear
        player_gear.is_equipped = True
        player_gear.equipped_on_drifter = drifter_num
        player_gear.save()
        
        return Response({'success': True, 'message': 'Gear equipped successfully'})
        
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except GearItem.DoesNotExist:
        return Response({'error': 'Gear item not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def unequip_gear(request, player_id):
    """Unequip gear from a player"""
    try:
        player = Player.objects.get(id=player_id)
        data = request.data
        
        gear_id = data.get('gear_id')
        
        if not gear_id:
            return Response({'error': 'gear_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find and unequip the gear
        player_gear = PlayerGear.objects.get(
            player=player,
            gear_item_id=gear_id,
            is_equipped=True
        )
        
        player_gear.is_equipped = False
        player_gear.equipped_on_drifter = None
        player_gear.save()
        
        return Response({'success': True, 'message': 'Gear unequipped successfully'})
        
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except PlayerGear.DoesNotExist:
        return Response({'error': 'Equipped gear not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
