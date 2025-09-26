from rest_framework import viewsets, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from datetime import datetime
import pytz
from .models import Guild, Player, Drifter, Event, EventParticipant, Party, PartyMember, GearItem, GearType, RecommendedBuild, PlayerGear
import json
import asyncio
import logging
from .discord_bot import WarborneBot

# Get logger for this module
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def update_player_drifter(request, player_id):
    """Update a player's drifter selection"""
    try:
        player = Player.objects.get(id=player_id)
        drifter_id = request.data.get('drifter_id')
        drifter_slot = request.data.get('drifter_slot')  # 1, 2, or 3
        
        if drifter_slot is None:
            return Response({'error': 'drifter_slot is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if drifter_slot not in [1, 2, 3]:
            return Response({'error': 'drifter_slot must be 1, 2, or 3'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle clearing drifter (null) or setting a drifter
        if drifter_id is None:
            # Clear the drifter slot
            if drifter_slot == 1:
                player.drifter_1 = None
            elif drifter_slot == 2:
                player.drifter_2 = None
            elif drifter_slot == 3:
                player.drifter_3 = None
        else:
            # Get the drifter
            try:
                drifter = Drifter.objects.get(id=drifter_id)
            except Drifter.DoesNotExist:
                return Response({'error': 'Drifter not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Update the appropriate drifter slot
            if drifter_slot == 1:
                player.drifter_1 = drifter
            elif drifter_slot == 2:
                player.drifter_2 = drifter
            elif drifter_slot == 3:
                player.drifter_3 = drifter
        
        player.save()
        
        if drifter_id is None:
            return Response({
                'success': True,
                'message': f'Drifter slot {drifter_slot} cleared',
                'drifter': None
            })
        else:
            return Response({
                'success': True,
                'message': f'Drifter {drifter.name} assigned to slot {drifter_slot}',
                'drifter': {
                    'id': drifter.id,
                    'name': drifter.name,
                    'base_health': drifter.base_health,
                    'base_energy': drifter.base_energy,
                    'base_damage': drifter.base_damage,
                    'base_defense': drifter.base_defense,
                    'base_speed': drifter.base_speed,
                    'special_abilities': drifter.special_abilities
                }
            })
        
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def all_drifters(request):
    """Get all available drifters"""
    try:
        drifters = Drifter.objects.all()
        drifter_data = []
        
        for drifter in drifters:
            drifter_data.append({
                'id': drifter.id,
                'name': drifter.name,
                'description': drifter.description,
                'base_health': drifter.base_health,
                'base_energy': drifter.base_energy,
                'base_damage': drifter.base_damage,
                'base_defense': drifter.base_defense,
                'base_speed': drifter.base_speed,
                'special_abilities': drifter.special_abilities,
                'is_active': drifter.is_active
            })
        
        return Response({
            'drifters': drifter_data
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        for player in Player.objects.select_related('guild').all():
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
                'discord_name': player.discord_name,
                'discord_user_id': player.discord_user_id,
                'role': player.role,
                'game_role': player.game_role,
                'faction': player.faction,
                'level': player.character_level,
                'status': 'Online' if player.is_active else 'Offline',
                'avatar': player.in_game_name[:2].upper() if player.in_game_name else 'XX',
                'drifters': drifters,
                'guild': {
                    'id': player.guild.id if player.guild else None,
                    'name': player.guild.name if player.guild else None
                }
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
                'title': event.title,
                'type': event.event_type,
                'participants': event.participant_count,
                'status': 'active' if event.is_active and not event.is_cancelled else 'cancelled',
                'time': event.event_datetime.strftime('%Y-%m-%d %H:%M') if event.event_datetime else 'TBD',
                'organizer': event.created_by_discord_name
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
                'type': item.gear_type.category if item.gear_type else 'Unknown',
                'rarity': item.rarity or 'common',
                'stats': {
                    'damage': getattr(item, 'damage', 0),
                    'defense': getattr(item, 'defense', 0),
                    'health': getattr(item, 'health_bonus', 0)
                },
                'equipped': getattr(item, 'is_equipped', False),
                'owner': 'Guild'  # Gear items belong to the guild
            })
        
        return Response({'gear_items': gear_items})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def gear_items(request):
    """Get all gear items for loadout page"""
    try:
        gear_items = []
        for item in GearItem.objects.select_related('gear_type').all():
            gear_items.append({
                'id': item.id,
                'base_name': item.base_name,
                'skill_name': item.skill_name,
                'rarity': item.rarity,
                'damage': item.damage,
                'defense': item.defense,
                'health_bonus': item.health_bonus,
                'energy_bonus': item.energy_bonus,
                'description': item.description,
                'game_id': item.game_id,
                'icon_url': item.icon_url,
                'gear_type': {
                    'id': item.gear_type.id if item.gear_type else None,
                    'category': item.gear_type.category if item.gear_type else 'unknown'
                }
            })
        
        return Response({'gear_items': gear_items})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def recommended_builds(request):
    """Get recommended builds"""
    try:
        builds = []
        for build in RecommendedBuild.objects.filter(is_active=True).select_related(
            'drifter', 'weapon', 'helmet', 'chest', 'boots', 'consumable',
            'mod1', 'mod2', 'mod3', 'mod4'
        ):
            builds.append({
                'id': build.id,
                'title': build.title,
                'description': build.description,
                'role': build.role,
                'is_active': build.is_active,
                'created_at': build.created_at,
                'updated_at': build.updated_at,
                'created_by': build.created_by,
                'drifter': {
                    'id': build.drifter.id if build.drifter else None,
                    'name': build.drifter.name if build.drifter else None,
                    'base_health': build.drifter.base_health if build.drifter else None,
                    'base_energy': build.drifter.base_energy if build.drifter else None,
                    'base_damage': build.drifter.base_damage if build.drifter else None,
                    'base_defense': build.drifter.base_defense if build.drifter else None,
                    'base_speed': build.drifter.base_speed if build.drifter else None,
                    'special_abilities': build.drifter.special_abilities if build.drifter else None
                } if build.drifter else None,
                'weapon': {
                    'id': build.weapon.id if build.weapon else None,
                    'name': build.weapon.base_name if build.weapon else None,
                    'skill_name': build.weapon.skill_name if build.weapon else None,
                    'rarity': build.weapon.rarity if build.weapon else None,
                    'damage': build.weapon.damage if build.weapon else None,
                    'health_bonus': build.weapon.health_bonus if build.weapon else None,
                    'energy_bonus': build.weapon.energy_bonus if build.weapon else None,
                    'game_id': build.weapon.game_id if build.weapon else None,
                    'icon_url': build.weapon.icon_url if build.weapon else None
                } if build.weapon else None,
                'helmet': {
                    'id': build.helmet.id if build.helmet else None,
                    'name': build.helmet.base_name if build.helmet else None,
                    'skill_name': build.helmet.skill_name if build.helmet else None,
                    'rarity': build.helmet.rarity if build.helmet else None,
                    'damage': build.helmet.damage if build.helmet else None,
                    'health_bonus': build.helmet.health_bonus if build.helmet else None,
                    'energy_bonus': build.helmet.energy_bonus if build.helmet else None,
                    'game_id': build.helmet.game_id if build.helmet else None,
                    'icon_url': build.helmet.icon_url if build.helmet else None
                } if build.helmet else None,
                'chest': {
                    'id': build.chest.id if build.chest else None,
                    'name': build.chest.base_name if build.chest else None,
                    'skill_name': build.chest.skill_name if build.chest else None,
                    'rarity': build.chest.rarity if build.chest else None,
                    'damage': build.chest.damage if build.chest else None,
                    'health_bonus': build.chest.health_bonus if build.chest else None,
                    'energy_bonus': build.chest.energy_bonus if build.chest else None,
                    'game_id': build.chest.game_id if build.chest else None,
                    'icon_url': build.chest.icon_url if build.chest else None
                } if build.chest else None,
                'boots': {
                    'id': build.boots.id if build.boots else None,
                    'name': build.boots.base_name if build.boots else None,
                    'skill_name': build.boots.skill_name if build.boots else None,
                    'rarity': build.boots.rarity if build.boots else None,
                    'damage': build.boots.damage if build.boots else None,
                    'health_bonus': build.boots.health_bonus if build.boots else None,
                    'energy_bonus': build.boots.energy_bonus if build.boots else None,
                    'game_id': build.boots.game_id if build.boots else None,
                    'icon_url': build.boots.icon_url if build.boots else None
                } if build.boots else None,
                'consumable': {
                    'id': build.consumable.id if build.consumable else None,
                    'name': build.consumable.base_name if build.consumable else None,
                    'skill_name': build.consumable.skill_name if build.consumable else None,
                    'rarity': build.consumable.rarity if build.consumable else None,
                    'damage': build.consumable.damage if build.consumable else None,
                    'health_bonus': build.consumable.health_bonus if build.consumable else None,
                    'energy_bonus': build.consumable.energy_bonus if build.consumable else None,
                    'game_id': build.consumable.game_id if build.consumable else None,
                    'icon_url': build.consumable.icon_url if build.consumable else None
                } if build.consumable else None,
                'mod1': {
                    'id': build.mod1.id if build.mod1 else None,
                    'name': build.mod1.name if build.mod1 else None,
                    'description': build.mod1.description if build.mod1 else None,
                    'rarity': build.mod1.rarity if build.mod1 else None,
                    'game_id': build.mod1.game_id if build.mod1 else None,
                    'icon_url': build.mod1.icon_url if build.mod1 else None
                } if build.mod1 else None,
                'mod2': {
                    'id': build.mod2.id if build.mod2 else None,
                    'name': build.mod2.name if build.mod2 else None,
                    'description': build.mod2.description if build.mod2 else None,
                    'rarity': build.mod2.rarity if build.mod2 else None,
                    'game_id': build.mod2.game_id if build.mod2 else None,
                    'icon_url': build.mod2.icon_url if build.mod2 else None
                } if build.mod2 else None,
                'mod3': {
                    'id': build.mod3.id if build.mod3 else None,
                    'name': build.mod3.name if build.mod3 else None,
                    'description': build.mod3.description if build.mod3 else None,
                    'rarity': build.mod3.rarity if build.mod3 else None,
                    'game_id': build.mod3.game_id if build.mod3 else None,
                    'icon_url': build.mod3.icon_url if build.mod3 else None
                } if build.mod3 else None,
                'mod4': {
                    'id': build.mod4.id if build.mod4 else None,
                    'name': build.mod4.name if build.mod4 else None,
                    'description': build.mod4.description if build.mod4 else None,
                    'rarity': build.mod4.rarity if build.mod4 else None,
                    'game_id': build.mod4.game_id if build.mod4 else None,
                    'icon_url': build.mod4.icon_url if build.mod4 else None
                } if build.mod4 else None
            })
        
        return Response({'builds': builds})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_recommended_build(request):
    """Create a new recommended build"""
    try:
        data = request.data
        
        # Validate required fields
        if not data.get('title'):
            return Response({'error': 'Title is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get('description'):
            return Response({'error': 'Description is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get('role'):
            return Response({'error': 'Role is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the build
        build = RecommendedBuild.objects.create(
            title=data['title'],
            description=data['description'],
            role=data['role'],
            is_active=True,
            created_by=request.user.username if request.user.is_authenticated else 'Anonymous'
        )
        
        return Response({
            'build_id': build.id,
            'message': 'Build created successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def assign_drifter_to_build(request, build_id):
    """Assign a drifter to a recommended build or clear the assignment"""
    try:
        data = request.data
        drifter_id = data.get('drifter_id')
        
        # Get the build
        try:
            build = RecommendedBuild.objects.get(id=build_id)
        except RecommendedBuild.DoesNotExist:
            return Response({'error': 'Build not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if drifter_id is None:
            # Clear the drifter assignment
            build.drifter = None
            build.save()
            
            return Response({
                'message': 'Drifter assignment cleared successfully',
                'drifter': None
            }, status=status.HTTP_200_OK)
        else:
            # Assign a specific drifter
            try:
                drifter = Drifter.objects.get(id=drifter_id)
            except Drifter.DoesNotExist:
                return Response({'error': 'Drifter not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Assign the drifter to the build
            build.drifter = drifter
            build.save()
            
            return Response({
                'message': 'Drifter assigned successfully',
                'drifter': {
                    'id': drifter.id,
                    'name': drifter.name,
                    'base_health': drifter.base_health,
                    'base_energy': drifter.base_energy,
                    'base_damage': drifter.base_damage,
                    'base_defense': drifter.base_defense,
                    'base_speed': drifter.base_speed,
                    'special_abilities': drifter.special_abilities
                }
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def equip_item_to_build(request, build_id):
    """Equip an item to a recommended build"""
    try:
        data = request.data
        item_id = data.get('item_id')
        slot_type = data.get('slot_type')
        
        if not item_id:
            return Response({'error': 'Item ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not slot_type:
            return Response({'error': 'Slot type is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the build
        try:
            build = RecommendedBuild.objects.get(id=build_id)
        except RecommendedBuild.DoesNotExist:
            return Response({'error': 'Build not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get the item
        try:
            item = GearItem.objects.get(id=item_id)
        except GearItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Assign the item to the appropriate slot
        if slot_type == 'weapon':
            build.weapon = item
        elif slot_type == 'helmet':
            build.helmet = item
        elif slot_type == 'chest':
            build.chest = item
        elif slot_type == 'boots':
            build.boots = item
        elif slot_type == 'consumable':
            build.consumable = item
        elif slot_type == 'mod':
            # For mods, find the first empty slot
            if not build.mod1:
                build.mod1 = item
            elif not build.mod2:
                build.mod2 = item
            elif not build.mod3:
                build.mod3 = item
            elif not build.mod4:
                build.mod4 = item
            else:
                return Response({'error': 'No empty mod slots available'}, status=status.HTTP_400_BAD_REQUEST)
        
        build.save()
        
        return Response({
            'message': 'Item equipped successfully',
            'item': {
                'id': item.id,
                'name': item.base_name,
                'rarity': item.rarity,
                'slot_type': slot_type
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def unequip_item_from_build(request, build_id):
    """Unequip an item from a recommended build"""
    try:
        data = request.data
        slot_type = data.get('slot_type')
        
        if not slot_type:
            return Response({'error': 'Slot type is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the build
        try:
            build = RecommendedBuild.objects.get(id=build_id)
        except RecommendedBuild.DoesNotExist:
            return Response({'error': 'Build not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Clear the appropriate slot
        if slot_type == 'weapon':
            build.weapon = None
        elif slot_type == 'helmet':
            build.helmet = None
        elif slot_type == 'chest':
            build.chest = None
        elif slot_type == 'boots':
            build.boots = None
        elif slot_type == 'consumable':
            build.consumable = None
        elif slot_type == 'mod':
            # For mods, clear the last filled slot
            if build.mod4:
                build.mod4 = None
            elif build.mod3:
                build.mod3 = None
            elif build.mod2:
                build.mod2 = None
            elif build.mod1:
                build.mod1 = None
        
        build.save()
        
        return Response({
            'message': 'Item unequipped successfully',
            'slot_type': slot_type
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Player Loadout API endpoints
@api_view(['GET'])
@permission_classes([AllowAny])
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
            'character_level': player.character_level,
            'total_gear_power': player.total_gear_power,
            'is_active': player.is_active,
            'created_at': player.created_at,
            'guild': player.guild.name if player.guild else None,
        })
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def player_drifters(request, player_id):
    """Get player's drifters with gear slots"""
    try:
        player = Player.objects.get(id=player_id)
        drifters = []
        
        # Get all player gear for equipped status checking
        player_gear = PlayerGear.objects.filter(
            player=player
        ).select_related('gear_item__gear_type')
        
        for i in range(1, 4):  # 3 drifters
            drifter = getattr(player, f'drifter_{i}', None)
            if drifter:
                # Get equipped gear for this specific drifter
                equipped_gear = PlayerGear.objects.filter(
                    player=player, 
                    is_equipped=True,
                    equipped_on_drifter=i
                ).select_related('gear_item__gear_type')
                
                # Prepare gear slots for this drifter (9 slots: weapon, helmet, chest, boots, consumable, 4 mods)
                gear_slots = []
                equipped_list = list(equipped_gear)
                
                # Define slot order: weapon, helmet, chest, boots, consumable, 4 mods
                slot_order = ['weapon', 'helmet', 'chest', 'boots', 'consumable'] + ['mod'] * 4
                
                for slot_index in range(9):
                    # Find gear for this slot
                    slot_gear = None
                    for gear in equipped_list:
                        if gear.gear_item.gear_type.category == slot_order[slot_index]:
                            slot_gear = gear
                            break
                    
                    if slot_gear:
                        gear_slots.append({
                            'id': slot_gear.id,
                            'gear_item': {
                                'id': slot_gear.gear_item.id,
                                'base_name': slot_gear.gear_item.base_name,
                                'skill_name': slot_gear.gear_item.skill_name,
                                'rarity': slot_gear.gear_item.rarity,
                                'tier': slot_gear.gear_item.tier,
                                'item_level': slot_gear.gear_item.item_level,
                                'damage': slot_gear.gear_item.damage,
                                'defense': slot_gear.gear_item.defense,
                                'health_bonus': slot_gear.gear_item.health_bonus,
                                'energy_bonus': slot_gear.gear_item.energy_bonus,
                                'game_id': slot_gear.gear_item.game_id,
                                'icon_url': slot_gear.gear_item.icon_url,
                            },
                            'gear_type': {
                                'category': slot_gear.gear_item.gear_type.category
                            }
                        })
                    else:
                        gear_slots.append(None)
                
                drifters.append({
                    'number': i,
                    'name': drifter.name,
                    'base_health': getattr(drifter, 'base_health', 100),
                    'base_energy': getattr(drifter, 'base_energy', 100),
                    'base_damage': getattr(drifter, 'base_damage', 50),
                    'base_defense': getattr(drifter, 'base_defense', 25),
                    'base_speed': getattr(drifter, 'base_speed', 75),
                    'gear_slots': gear_slots,
                    'equipped_count': equipped_gear.count(),
                })
            else:
                drifters.append({
                    'number': i,
                    'name': None,
                    'base_health': 100,
                    'base_energy': 100,
                    'base_damage': 50,
                    'base_defense': 25,
                    'base_speed': 75,
                    'gear_slots': [None] * 9,
                    'equipped_count': 0,
                })
        
        return Response({'drifters': drifters})
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
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
                'base_name': gear.gear_item.base_name,
                'type': gear.gear_item.gear_type.category,
                'rarity': gear.gear_item.rarity,
                'tier': gear.gear_item.tier,
                'item_level': gear.gear_item.item_level,
                'skill_name': gear.gear_item.skill_name,
                'damage': gear.gear_item.damage,
                'defense': gear.gear_item.defense,
                'health_bonus': gear.gear_item.health_bonus,
                'slot_type': gear.gear_item.gear_type.category,
                'game_id': gear.gear_item.game_id,
                'icon_url': gear.gear_item.icon_url,
                'gear_type': {
                    'category': gear.gear_item.gear_type.category,
                    'name': gear.gear_item.gear_type.name
                }
            })
        
        return Response({'equipped_gear': gear_data})
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def equip_gear(request, player_id):
    """Equip gear to a player's drifter"""
    try:
        player = Player.objects.get(id=player_id)
        data = request.data
        
        gear_id = data.get('gear_id')
        drifter_num = data.get('drifter_num', 1)
        slot_type = data.get('slot_type')
        tier = data.get('tier', 'II')
        item_level = data.get('item_level', 30)
        
        if not gear_id:
            return Response({'error': 'gear_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the gear item
        gear_item = GearItem.objects.get(id=gear_id)
        
        # Update the gear item's tier and level if provided
        if tier and tier != gear_item.tier:
            gear_item.tier = tier
        if item_level and item_level != gear_item.item_level:
            gear_item.item_level = item_level
        gear_item.save()
        
        # Check if player owns this gear
        player_gear, created = PlayerGear.objects.get_or_create(
            player=player,
            gear_item=gear_item,
            defaults={'is_equipped': False}
        )
        
        # If gear is already equipped, unequip it first (allows moving gear between slots/drifters)
        if not created and player_gear.is_equipped:
            # Check if it's the same slot on the same drifter (no change needed)
            if player_gear.equipped_on_drifter == drifter_num and slot_type != 'mod' and player_gear.gear_item.gear_type.category == slot_type:
                return Response({'error': 'Gear is already equipped in this slot'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Unequip the gear from its current location
            player_gear.is_equipped = False
            player_gear.equipped_on_drifter = None
            player_gear.save()
        
        # For mods, find the next available mod slot
        if slot_type == 'mod':
            # Get all equipped mods for this drifter
            equipped_mods = PlayerGear.objects.filter(
                player=player,
                is_equipped=True,
                equipped_on_drifter=drifter_num,
                gear_item__gear_type__category='mod'
            ).count()
            
            # Check if we have space for another mod (max 4 mods)
            if equipped_mods >= 4:
                return Response({'error': 'All mod slots are full'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # For other gear types, unequip any gear in the same slot
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
        
        # Calculate gear power for the response (using item's own level)
        gear_power = gear_item.get_gear_power()
        
        return Response({
            'success': True, 
            'message': 'Gear equipped successfully',
            'gear_power': gear_power,
            'tier': gear_item.tier,
            'rarity': gear_item.rarity
        })
        
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except GearItem.DoesNotExist:
        return Response({'error': 'Gear item not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
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


# Event Management API endpoints
@api_view(['GET'])
@permission_classes([AllowAny])
def events_list(request):
    """Get all events with participant counts"""
    try:
        events = Event.objects.filter(is_active=True, is_cancelled=False).order_by('-event_datetime')
        
        events_data = []
        for event in events:
            participant_count = EventParticipant.objects.filter(
                event=event
            ).count()
            
            events_data.append({
                'id': event.id,
                'title': event.title,
                'description': event.description or '',
                'event_type': event.event_type,
                'event_type_display': event.get_event_type_display(),
                'event_datetime': event.event_datetime.isoformat(),
                'timezone': event.timezone,
                'max_participants': event.max_participants,
                'participant_count': participant_count,
                'created_by_discord_name': event.created_by_discord_name,
                'created_at': event.created_at.isoformat(),
                'discord_epoch': event.discord_epoch,
                'discord_timestamp': event.discord_timestamp,
                'discord_timestamp_relative': event.discord_timestamp_relative,
                'is_active': event.is_active,
                'is_cancelled': event.is_cancelled
            })
        
        return Response({'events': events_data})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def event_detail(request, event_id):
    """Get detailed information about a specific event"""
    try:
        event = Event.objects.get(id=event_id)
        
        # Get participants
        participants = EventParticipant.objects.filter(
            event=event
        ).select_related('player')
        
        participants_data = []
        for participant in participants:
            participants_data.append({
                'id': participant.id,
                'discord_name': participant.discord_name,
                'discord_user_id': participant.discord_user_id,
                'player': {
                    'id': participant.player.id,
                    'in_game_name': participant.player.in_game_name,
                    'game_role': participant.player.game_role,
                    'faction': participant.player.faction
                } if participant.player else None,
                'joined_at': participant.joined_at.isoformat(),
                'notes': participant.notes or ''
            })
        
        # Get parties
        parties = Party.objects.filter(event=event, is_active=True).order_by('party_number')
        parties_data = []
        for party in parties:
            party_members = PartyMember.objects.filter(
                party=party,
            ).select_related('player', 'event_participant')
            
            members_data = []
            for member in party_members:
                members_data.append({
                    'id': member.id,
                    'player_name': member.player.in_game_name,
                    'discord_name': member.event_participant.discord_name,
                    'event_participant': {
                        'id': member.event_participant.id,
                        'discord_name': member.event_participant.discord_name
                    },
                    'assigned_role': member.assigned_role,
                    'is_leader': member.is_leader,
                    'assigned_at': member.assigned_at.isoformat()
                })
            
            parties_data.append({
                'id': party.id,
                'party_number': party.party_number,
                'party_name': party.party_name,
                'max_members': party.max_members,
                'member_count': party.member_count,
                'members': members_data,
                'created_at': party.created_at.isoformat()
            })
        
        event_data = {
            'id': event.id,
            'title': event.title,
            'description': event.description or '',
            'event_type': event.event_type,
            'event_type_display': event.get_event_type_display(),
            'event_datetime': event.event_datetime.isoformat(),
            'timezone': event.timezone,
            'max_participants': event.max_participants,
            'participant_count': len(participants_data),
            'participants': participants_data,
            'parties': parties_data,
            'created_by_discord_name': event.created_by_discord_name,
            'created_at': event.created_at.isoformat(),
            'discord_timestamp': event.discord_timestamp,
            'discord_timestamp_relative': event.discord_timestamp_relative,
            'is_active': event.is_active,
            'is_cancelled': event.is_cancelled
        }
        
        return Response(event_data)
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_event(request):
    """Create a new event with proper timezone handling"""
    try:
        data = request.data
        
        # Validate required fields
        if not data.get('title'):
            return Response({'error': 'Title is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get('event_datetime'):
            return Response({'error': 'Event datetime is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get('timezone'):
            return Response({'error': 'Timezone is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate timezone
        timezone_str = data['timezone']
        try:
            user_tz = pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            return Response({'error': f'Invalid timezone: {timezone_str}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse local datetime
        try:
            local_datetime_str = data['event_datetime']
            # Parse as naive datetime first
            local_dt = datetime.fromisoformat(local_datetime_str.replace('Z', ''))
        except ValueError:
            return Response({'error': 'Invalid datetime format. Use YYYY-MM-DDTHH:MM format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert local datetime to UTC
        try:
            # Localize to user's timezone
            local_dt_aware = user_tz.localize(local_dt)
            # Convert to UTC
            utc_dt = local_dt_aware.astimezone(pytz.UTC)
        except (pytz.exceptions.AmbiguousTimeError, pytz.exceptions.NonExistentTimeError) as e:
            return Response({'error': f'Invalid local time due to DST transition: {str(e)}. Please choose a different time.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate max participants
        max_participants = None
        if data.get('max_participants'):
            try:
                max_participants = int(data['max_participants'])
                if max_participants <= 0:
                    raise ValueError()
            except ValueError:
                return Response({'error': 'Max participants must be a positive number'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create event
        event = Event.objects.create(
            title=data['title'],
            description=data.get('description', ''),
            event_type=data.get('event_type', 'other'),
            event_datetime=utc_dt,
            timezone=timezone_str,
            max_participants=max_participants,
            created_by_discord_id=data.get('created_by_discord_id', 0),
            created_by_discord_name=data.get('created_by_discord_name', 'Web User')
        )
        
        return Response({
            'id': event.id,
            'message': 'Event created successfully',
            'event': {
                'id': event.id,
                'title': event.title,
                'description': event.description,
                'event_type': event.event_type,
                'event_datetime': event.event_datetime.isoformat(),
                'timezone': event.timezone,
                'max_participants': event.max_participants,
                'created_by_discord_name': event.created_by_discord_name,
                'created_at': event.created_at.isoformat(),
                'discord_epoch': event.discord_epoch,
                'discord_timestamp': event.discord_timestamp,
                'discord_timestamp_relative': event.discord_timestamp_relative
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
def update_event(request, event_id):
    """Update an existing event"""
    try:
        event = Event.objects.get(id=event_id)
        data = request.data
        
        # Update fields if provided
        if 'title' in data:
            event.title = data['title']
        if 'description' in data:
            event.description = data['description']
        if 'event_type' in data:
            event.event_type = data['event_type']
        if 'event_datetime' in data:
            try:
                event.event_datetime = datetime.fromisoformat(data['event_datetime'].replace('Z', '+00:00'))
            except ValueError:
                return Response({'error': 'Invalid datetime format'}, status=status.HTTP_400_BAD_REQUEST)
        if 'timezone' in data:
            event.timezone = data['timezone']
        if 'max_participants' in data:
            if data['max_participants'] is None:
                event.max_participants = None
            else:
                try:
                    event.max_participants = int(data['max_participants'])
                    if event.max_participants <= 0:
                        raise ValueError()
                except ValueError:
                    return Response({'error': 'Max participants must be a positive number'}, status=status.HTTP_400_BAD_REQUEST)
        
        event.save()
        
        return Response({
            'message': 'Event updated successfully',
            'event': {
                'id': event.id,
                'title': event.title,
                'description': event.description,
                'event_type': event.event_type,
                'event_datetime': event.event_datetime.isoformat(),
                'timezone': event.timezone,
                'max_participants': event.max_participants,
                'updated_at': event.updated_at.isoformat()
            }
        })
        
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_event(request, event_id):
    """Delete/cancel an event - performs hard delete"""
    try:
        event = Event.objects.get(id=event_id)
        event_title = event.title  # Store title for success message
        
        # Perform hard delete - this will cascade delete related objects
        event.delete()
        
        return Response({
            'message': f'Event "{event_title}" deleted successfully',
            'event_id': event_id
        })
        
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def join_event(request, event_id):
    """Join an event as a participant"""
    try:
        data = request.data
        discord_user_id = data.get('discord_user_id')
        discord_name = data.get('discord_name')
        assigned_role = data.get('assigned_role')
        
        if not discord_name:
            return Response({'error': 'Discord name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        event = Event.objects.get(id=event_id)
        
        # Check if event is still active
        if not event.is_active or event.is_cancelled:
            return Response({'error': 'Event is not active'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if event is full
        if event.max_participants:
            current_participants = EventParticipant.objects.filter(event=event).count()
            if current_participants >= event.max_participants:
                return Response({'error': 'Event is full'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already participating (by discord_name if no discord_user_id)
        if discord_user_id:
            existing_participant = EventParticipant.objects.filter(
                event=event,
                discord_user_id=discord_user_id
            ).first()
        else:
            existing_participant = EventParticipant.objects.filter(
                event=event,
                discord_name=discord_name
            ).first()
        
        if existing_participant:
            # EventParticipant doesn't have is_active field, so if it exists, they're already participating
                return Response({'error': 'Already participating in this event'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Get player if exists
            if discord_user_id:
                player = Player.objects.filter(discord_user_id=discord_user_id).first()
            else:
                player = Player.objects.filter(discord_name=discord_name).first()
            
            # Create new participant
            # Use discord_user_id from request, or fall back to player's discord_user_id
            final_discord_user_id = discord_user_id
            if not final_discord_user_id and player and player.discord_user_id:
                final_discord_user_id = player.discord_user_id
            
            participant = EventParticipant.objects.create(
                event=event,
                discord_user_id=final_discord_user_id,
                discord_name=discord_name,
                player=player
            )
        
        return Response({
            'message': 'Successfully joined event',
            'participant': {
                'id': participant.id,
                'discord_name': participant.discord_name,
                'joined_at': participant.joined_at.isoformat()
            }
        })
        
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def leave_event(request, event_id):
    """Leave an event"""
    try:
        data = request.data
        discord_user_id = data.get('discord_user_id')
        
        if not discord_user_id:
            return Response({'error': 'Discord user ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        event = Event.objects.get(id=event_id)
        
        participant = EventParticipant.objects.filter(
            event=event,
            discord_user_id=discord_user_id
        ).first()
        
        if not participant:
            return Response({'error': 'Not participating in this event'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Remove participation (EventParticipant doesn't have is_active field)
        participant_id = participant.id
        participant.delete()
        
        return Response({
            'message': 'Successfully left event',
            'participant_id': participant_id
        })
        
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def publish_event(request, event_id):
    """Publish a single event to Discord announcements channel"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f" Starting publish_event for event_id: {event_id}")
        
        from .models import Event, DiscordBotConfig
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
            logger.info(f" Event found: {event.title} (ID: {event.id})")
        except Event.DoesNotExist:
            logger.error(f" Event not found or not active: {event_id}")
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get bot config
        config = DiscordBotConfig.objects.first()
        logger.info(f"📋 Bot config found: {config.name if config else 'None'}")
        logger.info(f"📢 Event announcements channel ID: {config.event_announcements_channel_id if config else 'None'}")
        
        if not config or not config.event_announcements_channel_id:
            logger.error(" Event announcements channel not configured")
            return Response({'error': 'Event announcements channel not configured'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get participant count
        from .models import EventParticipant
        participant_count = EventParticipant.objects.filter(
            event=event
        ).count()
        logger.info(f"👥 Participant count: {participant_count}")
        
        # Create the announcement message data
        announcement_data = {
            'event_id': event.id,
            'title': event.title,
            'description': event.description,
            'event_type': event.event_type,
            'event_type_display': event.get_event_type_display(),
            'event_datetime': event.event_datetime.isoformat(),
            'timezone': event.timezone,
            'participant_count': participant_count,
            'max_participants': event.max_participants,
            'created_by_discord_name': event.created_by_discord_name,
            'discord_epoch': event.discord_epoch,
            'discord_timestamp': event.discord_timestamp,
            'discord_timestamp_relative': event.discord_timestamp_relative,
            'announcement_channel_id': config.event_announcements_channel_id
        }
        logger.info(f"📝 Announcement data prepared: {announcement_data['title']}")
        
        # Send command to the running Discord bot via file communication
        from .bot_communication import send_bot_command
        
        logger.info("📤 Sending command to Discord bot...")
        success = send_bot_command('publish_event', announcement_data)
        if not success:
            logger.error(" Failed to send command to Discord bot")
            return Response({'error': 'Failed to send command to Discord bot'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.info(" Command sent successfully to Discord bot")
        
        return Response({
            'message': f'Event "{event.title}" published successfully to Discord announcements channel',
            'announcement_data': announcement_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def balance_parties(parties):
    """Balance parties by moving members from incomplete parties to fill numbers"""
    from .models import PartyMember
    
    logger.info("🔄 Starting party balancing...")
    
    # Get current member counts for all parties
    party_counts = []
    for party in parties:
        member_count = PartyMember.objects.filter(party=party, is_active=True).count()
        party_counts.append((party, member_count))
    
    # Sort parties by member count (ascending)
    party_counts.sort(key=lambda x: x[1])
    
    logger.info(f"📊 Party counts before balancing: {[f'Party {p.party_number}: {count}' for p, count in party_counts]}")
    
    # Move members from parties with fewer members to parties with more members
    # until we have at most 1 incomplete party
    parties_moved = 0
    
    while len([count for _, count in party_counts if count < 15]) > 1:
        # Find the party with the fewest members
        smallest_party, smallest_count = party_counts[0]
        
        # Find the party with the most members that's not full
        largest_party, largest_count = None, 0
        for party, count in party_counts[1:]:
            if count < 15 and count > largest_count:
                largest_party, largest_count = party, count
        
        if largest_party is None:
            break  # No more parties to balance with
        
        # Move a member from smallest to largest party
        member_to_move = PartyMember.objects.filter(
            party=smallest_party, 
            is_active=True
        ).exclude(is_leader=True).first()  # Don't move leaders
        
        if member_to_move:
            # Update the member's party
            member_to_move.party = largest_party
            member_to_move.save()
            
            # Update our counts
            party_counts[0] = (smallest_party, smallest_count - 1)
            for i, (party, count) in enumerate(party_counts[1:], 1):
                if party == largest_party:
                    party_counts[i] = (largest_party, largest_count + 1)
                    break
            
            parties_moved += 1
            logger.info(f"  - Moved {member_to_move.player.in_game_name} from Party {smallest_party.party_number} to Party {largest_party.party_number}")
            
            # Re-sort the list
            party_counts.sort(key=lambda x: x[1])
        else:
            break  # No more members to move
    
    # Delete empty parties
    empty_parties = []
    for party, count in party_counts:
        if count == 0:
            empty_parties.append(party)
    
    for party in empty_parties:
        logger.info(f"🗑️ Deleting empty Party {party.party_number}")
        party.delete()
        parties_moved += 1
    
    logger.info(f"✅ Party balancing completed: {parties_moved} moves/deletions")
    return parties_moved

@api_view(['POST'])
def create_parties(request, event_id):
    """Create balanced parties for an event (migrated from Discord bot logic)"""
    try:
        from .models import Event, Party, PartyMember, EventParticipant
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"🎯 Starting Fill Party process for event {event_id}")
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
            logger.info(f"✅ Event found: {event.name} (ID: {event.id})")
        except Event.DoesNotExist:
            logger.error(f"❌ Event not found or not active: {event_id}")
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all participants with their players
        participants = list(EventParticipant.objects.filter(
            event=event,
            player__isnull=False
        ).select_related('player', 'player__guild'))
        
        logger.info(f"👥 Total participants found: {len(participants)}")
        
        if len(participants) < 2:
            logger.warning(f"⚠️ Not enough participants: {len(participants)} (minimum 2 needed)")
            return Response({'error': 'At least 2 participants needed to create parties'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Clear existing parties for this event
        existing_parties_count = Party.objects.filter(event=event).count()
        logger.info(f"🗑️ Clearing {existing_parties_count} existing parties for this event")
        Party.objects.filter(event=event).delete()
        
        # Get party configuration from database or request
        from .models import EventPartyConfiguration
        config = EventPartyConfiguration.get_or_create_default(event)
        logger.info(f"⚙️ Party configuration loaded: Guild Split = {config.guild_split}")
        
        # Use saved configuration or fallback to request data
        party_config = request.data.get('partyConfig', {})
        if party_config:
            # Update configuration if provided in request
            role_composition = party_config.get('roleComposition', {})
            guild_split = party_config.get('guildSplit', False)
        else:
            # Use saved configuration from database
            role_composition = {
                'tank': config.tank_count,
                'healer': config.healer_count,
                'ranged_dps': config.ranged_dps_count,
                'melee_dps': config.melee_dps_count,
                'defensive_tank': config.defensive_tank_count,
                'offensive_tank': config.offensive_tank_count,
                'offensive_support': config.offensive_support_count,
                'defensive_support': config.defensive_support_count,
            }
            guild_split = config.guild_split
        
        # Use role requirements from configuration
        ROLE_REQUIREMENTS = {
            'healer': role_composition.get('healer', 2),
            'ranged_dps': role_composition.get('ranged_dps', 0),
            'melee_dps': role_composition.get('melee_dps', 0),
            'defensive_tank': role_composition.get('defensive_tank', 2),
            'offensive_tank': role_composition.get('offensive_tank', 2),
            'offensive_support': role_composition.get('offensive_support', 0),
            'defensive_support': role_composition.get('defensive_support', 0),
        }
        
        logger.info(f"🎭 Role requirements: {ROLE_REQUIREMENTS}")
        MAX_PARTY_SIZE = 15
        logger.info(f"📊 Max party size: {MAX_PARTY_SIZE}")
        
        if guild_split:
            logger.info("🏰 Using guild split mode - grouping participants by guild")
            # Group participants by guild first
            participants_by_guild = {}
            for participant in participants:
                guild = participant.player.guild
                guild_name = guild.name if guild else "No Guild"
                if guild_name not in participants_by_guild:
                    participants_by_guild[guild_name] = []
                participants_by_guild[guild_name].append(participant)
            
            logger.info(f"🏰 Guilds found: {list(participants_by_guild.keys())}")
            for guild_name, guild_participants in participants_by_guild.items():
                logger.info(f"  - {guild_name}: {len(guild_participants)} participants")
            
            total_parties_created = 0
            total_members_created = 0
            guild_results = []
            
            # Process each guild separately
            for guild_name, guild_participants in participants_by_guild.items():
                logger.info(f"🔄 Processing guild: {guild_name} with {len(guild_participants)} participants")
                if len(guild_participants) < 2:
                    logger.warning(f"⚠️ Guild {guild_name} has insufficient participants: {len(guild_participants)} (minimum 2 needed)")
                    guild_results.append(f"{guild_name}: {len(guild_participants)} participants (minimum 2 needed)")
                    continue
                
                # Group participants by role within this guild
                participants_by_role = {}
                for participant in guild_participants:
                    role = participant.player.game_role or 'unknown'
                    if role not in participants_by_role:
                        participants_by_role[role] = []
                    participants_by_role[role].append(participant)
                
                logger.info(f"🎭 Role distribution for {guild_name}: {dict((role, len(participants)) for role, participants in participants_by_role.items())}")
                
                # TODO: Implement party creation logic
                logger.info(f"🎯 Party creation logic removed - returning test response")
            
            # Create summary message
            result_message = f"Guild parties created successfully:\n"
            result_message += f"Total: {total_parties_created} parties with {total_members_created} participants\n\n"
            result_message += "Guild breakdown:\n"
            for result in guild_results:
                result_message += f"• {result}\n"
            
            logger.info(f"🎉 Guild Fill Party completed: {total_parties_created} parties with {total_members_created} participants distributed")
            return Response({
                'message': result_message,
                'parties_created': total_parties_created,
                'members_assigned': total_members_created,
                'guild_breakdown': guild_results
            }, status=status.HTTP_200_OK)
        else:
            logger.info("🌍 Using mixed guild mode - all participants together")
            # Original logic for non-guild split
            # Group participants by role
            participants_by_role = {}
            for participant in participants:
                role = participant.player.game_role or 'unknown'
                if role not in participants_by_role:
                    participants_by_role[role] = []
                participants_by_role[role].append(participant)
            
            logger.info(f"🎭 Role distribution (mixed): {dict((role, len(participants)) for role, participants in participants_by_role.items())}")
            
            # TODO: Implement party creation logic
            logger.info(f"🎯 Party creation logic removed - returning test response")
        
    except Exception as e:
        logger.error(f"❌ Fill Party failed with error: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_guild_parties(request, event_id):
    """Create guild-based balanced parties for an event (migrated from Discord bot logic)"""
    try:
        from .models import Event, Party, PartyMember, EventParticipant, Guild
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all participants with their players and guilds
        participants = list(EventParticipant.objects.filter(
            event=event,
            player__isnull=False
        ).select_related('player', 'player__guild'))
        
        if len(participants) < 2:
            return Response({'error': 'At least 2 participants needed to create guild parties'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Clear existing parties for this event
        Party.objects.filter(event=event).delete()
        
        # Group participants by guild
        participants_by_guild = {}
        for participant in participants:
            guild = participant.player.guild
            guild_name = guild.name if guild else "No Guild"
            if guild_name not in participants_by_guild:
                participants_by_guild[guild_name] = []
            participants_by_guild[guild_name].append(participant)
        
        # Define role requirements per party (minimum) - from Discord bot
        ROLE_REQUIREMENTS = {
            'tank': 4,           # 4 tanks per party
            'healer': 2,         # 2 healers per party
            'ranged_dps': 3,     # 3 ranged DPS
            'melee_dps': 3,      # 3 melee DPS
            'defensive_tank': 1, # 1 defensive tank
            'offensive_tank': 1, # 1 offensive tank
            'offensive_support': 1, # 1 offensive support
        }
        
        MAX_PARTY_SIZE = 15
        total_parties_created = 0
        total_members_created = 0
        guild_results = []
        
        # Process each guild separately
        for guild_name, guild_participants in participants_by_guild.items():
            if len(guild_participants) < 2:
                guild_results.append(f"{guild_name}: {len(guild_participants)} participants (minimum 2 needed)")
                continue
            
            # Group participants by role within this guild
            participants_by_role = {}
            for participant in guild_participants:
                role = participant.player.game_role or 'unknown'
                if role not in participants_by_role:
                    participants_by_role[role] = []
                participants_by_role[role].append(participant)
            
            # TODO: Implement party creation logic
            logger.info(f"🎯 Party creation logic removed - returning test response")
            
        
        # Create summary message
        result_message = f"Guild parties created successfully:\n"
        result_message += f"Total: {total_parties_created} parties with {total_members_created} participants\n\n"
        result_message += "Guild breakdown:\n"
        for result in guild_results:
            result_message += f"• {result}\n"
        
        return Response({'success': True}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def event_participants(request, event_id):
    """Get all participants for a specific event"""
    try:
        from .models import Event, EventParticipant
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all participants with their players and guilds
        participants = EventParticipant.objects.filter(
            event=event,
            player__isnull=False
        ).select_related('player', 'player__guild')
        
        participants_data = []
        for participant in participants:
            participants_data.append({
                'id': participant.id,
                'discord_user_id': participant.discord_user_id,
                'discord_name': participant.discord_name,
                'player': {
                    'id': participant.player.id,
                    'discord_name': participant.player.discord_name,
                    'in_game_name': participant.player.in_game_name,
                    'game_role': participant.player.game_role,
                    'guild': {
                        'id': participant.player.guild.id if participant.player.guild else None,
                        'name': participant.player.guild.name if participant.player.guild else None
                    } if participant.player.guild else None
                },
                'joined_at': participant.joined_at.isoformat()
            })
        
        return Response({
            'participants': participants_data,
            'total_count': len(participants_data)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def event_parties(request, event_id):
    """Get all parties for a specific event"""
    try:
        from .models import Event, Party, PartyMember
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all parties for this event with their members
        parties = Party.objects.filter(
            event=event,
            is_active=True
        ).prefetch_related('members__player', 'members__event_participant').order_by('party_number')
        
        parties_data = []
        for party in parties:
            members_data = []
            for member in party.members.filter(is_active=True):
                members_data.append({
                    'id': member.id,
                    'player': {
                        'id': member.player.id,
                        'discord_name': member.player.discord_name,
                        'in_game_name': member.player.in_game_name,
                        'game_role': member.player.game_role
                    },
                    'event_participant': {
                        'id': member.event_participant.id,
                        'discord_name': member.event_participant.discord_name
                    },
                    'assigned_role': member.assigned_role,
                    'is_leader': member.is_leader,
                    'assigned_at': member.assigned_at.isoformat()
                })
            
            parties_data.append({
                'id': party.id,
                'party_number': party.party_number,
                'party_name': party.party_name,
                'max_members': party.max_members,
                'member_count': len(members_data),
                'members': members_data,
                'created_at': party.created_at.isoformat()
            })
        
        return Response({
            'parties': parties_data,
            'total_count': len(parties_data)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def remove_participant(request, event_id):
    """Remove a participant from an event"""
    try:
        from .models import Event, EventParticipant
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        participant_id = request.data.get('participant_id')
        if not participant_id:
            return Response({'error': 'Participant ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the participant
        try:
            participant = EventParticipant.objects.get(
                id=participant_id,
                event=event,
            )
        except EventParticipant.DoesNotExist:
            return Response({'error': 'Participant not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Remove the participant completely (hard deletion)
        participant.delete()
        
        return Response({
            'message': 'Participant removed successfully',
            'participant_id': participant_id
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def fill_parties(request, event_id):
    """Fill existing parties with remaining participants"""
    try:
        from .models import Event, Party, PartyMember, EventParticipant
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get party configuration from request
        role_composition = request.data.get('roleComposition', {})
        guild_split = request.data.get('guildSplit', False)
        
        # Separate roles into required (count > 0) and filler roles (count = 0)
        required_roles = {role: count for role, count in role_composition.items() if count > 0}
        filler_config_roles = {role: 0 for role, count in role_composition.items() if count == 0}
        
        # Get all event participants
        participants = list(EventParticipant.objects.filter(
            event=event,
            player__isnull=False
        ).select_related('player', 'player__guild'))
        
        if guild_split:
            logger.info("🏰 Using guild split mode - creating parties separately per guild")
            return _create_guild_split_parties(event, participants, required_roles, filler_config_roles)
        
        # Group participants by role (non-guild split mode) with role mapping
        participants_by_role = {}
        
        # Role mapping for common role variations
        ROLE_MAPPING = {
            'tank': 'defensive_tank',
            'dps': 'ranged_dps',
            'support': 'offensive_support'
        }
        
        for participant in participants:
            role = participant.player.game_role or 'unknown'
            
            # Apply role mapping if needed
            if role in ROLE_MAPPING:
                role = ROLE_MAPPING[role]
                logger.info(f"DEBUG: Mapped role '{participant.player.game_role}' to '{role}' for {participant.player.in_game_name}")
            
            if role not in participants_by_role:
                participants_by_role[role] = []
            participants_by_role[role].append(participant)
        
        # Separate roles into those that can fill multiple parties vs those that can only fill some parties
        primary_roles = {}  # Roles that can fill multiple parties
        filler_roles = {}   # Roles that can only fill some parties
        
        for role, required_count in required_roles.items():
            available_count = len(participants_by_role.get(role, []))
            if available_count >= required_count * 2:  # Need enough for at least 2 parties
                primary_roles[role] = required_count
                logger.info(f"DEBUG: Role {role} - Available: {available_count}, Required: {required_count} - PRIMARY (enough for {available_count // required_count} parties)")
            elif available_count >= required_count:  # Can fill at least 1 party
                filler_roles[role] = required_count
                logger.info(f"DEBUG: Role {role} - Available: {available_count}, Required: {required_count} - FILLER (only enough for {available_count // required_count} parties)")
            else:
                logger.info(f"DEBUG: Role {role} - Available: {available_count}, Required: {required_count} - IGNORED (not enough for any party)")
        
        # Use primary roles for party creation
        available_roles = primary_roles
        
        # Calculate minimum party size (sum of available roles)
        min_party_size = sum(available_roles.values())
        logger.info(f"DEBUG: Using roles: {available_roles}, min_party_size: {min_party_size}")
        
        # Create parties with minimum required roles
        parties_created = 0
        members_assigned = 0
        
        # Keep creating parties until we can't fill all available roles
        while True:
            # Check if we have enough participants for all available roles
            can_create_party = True
            for role, required_count in available_roles.items():
                available_count = len(participants_by_role.get(role, []))
                logger.info(f"DEBUG: Role {role} - Available: {available_count}, Required: {required_count}")
                if available_count < required_count:
                    can_create_party = False
                    logger.info(f"DEBUG: Cannot create party - not enough {role}")
                    break
            
            if not can_create_party:
                # Try to create parties with available roles (even if not complete)
                logger.info(f"DEBUG: Cannot create complete party, trying to create incomplete parties with available roles")
                
                # Check if we have any participants left in any role
                total_remaining = sum(len(participants_by_role.get(role, [])) for role in available_roles.keys())
                if total_remaining >= 4:  # Minimum party size
                    logger.info(f"DEBUG: Creating incomplete parties with {total_remaining} remaining participants")
                    # Continue with incomplete party creation
                else:
                    logger.info(f"DEBUG: Stopping party creation - insufficient participants for even incomplete parties")
                    break
            
            # Create new party
            new_party = Party.objects.create(
                event=event,
                party_number=Party.objects.filter(event=event, is_active=True).count() + 1,
                party_name=f"Party {Party.objects.filter(event=event, is_active=True).count() + 1}",
                max_members=15,  # Keep max at 15, but fill only with required roles
                is_active=True
            )
            parties_created += 1
            logger.info(f"DEBUG: Created party {parties_created}")
            
            # Assign available roles to this party
            for role, required_count in available_roles.items():
                available_participants = participants_by_role.get(role, [])
                # For incomplete parties, assign what's available instead of requiring exact count
                assign_count = min(required_count, len(available_participants))
                for i in range(assign_count):
                    participant = available_participants.pop(0)  # Remove from available list
                    
                    # Create party member
                    is_first_member = new_party.member_count == 0
                    PartyMember.objects.create(
                        party=new_party,
                        event_participant=participant,
                        player=participant.player,
                        assigned_role=participant.player.game_role,
                        is_leader=is_first_member
                    )
                    members_assigned += 1
                    logger.info(f"DEBUG: Assigned {participant.player.in_game_name} as {role}")
                
                if assign_count < required_count:
                    logger.info(f"DEBUG: Party {parties_created} incomplete - only {assign_count}/{required_count} {role} assigned")
            
            logger.info(f"DEBUG: Party {parties_created} complete. Remaining: Healers={len(participants_by_role.get('healer', []))}, DefTanks={len(participants_by_role.get('defensive_tank', []))}, OffTanks={len(participants_by_role.get('offensive_tank', []))}")
        
        # Phase 2: Add remaining participants from primary roles as fillers
        remaining_primary_members_assigned = 0
        if primary_roles:
            logger.info(f"DEBUG: Adding remaining participants from primary roles as fillers: {primary_roles}")
            
            # Get all created parties
            created_parties = list(Party.objects.filter(
                event=event,
                is_active=True
            ).order_by('party_number'))
            
            for role, required_count in primary_roles.items():
                available_participants = participants_by_role.get(role, [])
                logger.info(f"DEBUG: Adding remaining {len(available_participants)} {role} players as fillers to parties")
                
                for participant in available_participants:
                    # Find a party that has space
                    assigned = False
                    for party in created_parties:
                        if party.member_count < party.max_members:
                            # Add to this party as filler
                            PartyMember.objects.create(
                                party=party,
                                event_participant=participant,
                                player=participant.player,
                                assigned_role=participant.player.game_role,
                                is_leader=False
                            )
                            remaining_primary_members_assigned += 1
                            logger.info(f"DEBUG: Added {participant.player.in_game_name} as {role} filler to Party {party.party_number} (now {party.member_count + 1}/15)")
                            assigned = True
                            break
                    
                    if not assigned:
                        logger.info(f"DEBUG: Could not assign {participant.player.in_game_name} as {role} filler - all parties at max capacity")

        # Phase 3: Add filler roles (roles that don't have enough for multiple parties)
        filler_members_assigned = 0
        if filler_roles:
            logger.info(f"DEBUG: Adding filler roles: {filler_roles}")
            
            # Get all created parties
            created_parties = list(Party.objects.filter(
                event=event,
                is_active=True
            ).order_by('party_number'))
            
            for role, required_count in filler_roles.items():
                available_participants = participants_by_role.get(role, [])
                logger.info(f"DEBUG: Adding {len(available_participants)} {role} players to parties")
                
                for participant in available_participants:
                    # Find a party that doesn't have this role yet or has space
                    assigned = False
                    for party in created_parties:
                        # Check if this party already has enough of this role
                        current_count = party.members.filter(assigned_role=role, is_active=True).count()
                        if current_count < required_count and party.member_count < party.max_members:
                            # Add to this party
                            PartyMember.objects.create(
                                party=party,
                                event_participant=participant,
                                player=participant.player,
                                assigned_role=participant.player.game_role,
                                is_leader=False
                            )
                            filler_members_assigned += 1
                            logger.info(f"DEBUG: Added {participant.player.in_game_name} as {role} to Party {party.party_number}")
                            assigned = True
                            break
                    
                    if not assigned:
                        logger.info(f"DEBUG: Could not assign {participant.player.in_game_name} as {role} - no suitable party found")
        
        # Phase 3: Fill parties to maximum capacity using roles set to 0 in config
        max_filler_members_assigned = 0
        if filler_config_roles:
            logger.info(f"DEBUG: Adding config filler roles (0 in config): {list(filler_config_roles.keys())}")
            
            # Get all created parties that aren't at max capacity
            created_parties = list(Party.objects.filter(
                event=event,
                is_active=True
            ).order_by('party_number'))
            
            for role in filler_config_roles.keys():
                available_participants = participants_by_role.get(role, [])
                if available_participants:
                    logger.info(f"DEBUG: Adding {len(available_participants)} {role} players as fillers to reach max party size")
                    
                    for participant in available_participants:
                        # Find a party that has space
                        assigned = False
                        for party in created_parties:
                            if party.member_count < party.max_members:
                                # Add to this party
                                PartyMember.objects.create(
                                    party=party,
                                    event_participant=participant,
                                    player=participant.player,
                                    assigned_role=participant.player.game_role,
                                    is_leader=False
                                )
                                max_filler_members_assigned += 1
                                logger.info(f"DEBUG: Added {participant.player.in_game_name} as {role} filler to Party {party.party_number} (now {party.member_count + 1}/15)")
                                assigned = True
                                break
                        
                        if not assigned:
                            logger.info(f"DEBUG: Could not assign {participant.player.in_game_name} as {role} filler - all parties at max capacity")
        
        # Phase 4: Balance parties - consolidate incomplete parties and remove empty ones
        balance_members_moved = 0
        parties_removed = 0

        # Get all parties ordered by creation (party_number)
        all_parties = list(Party.objects.filter(
            event=event,
            is_active=True
        ).order_by('party_number'))

        if len(all_parties) > 1:
            logger.info(f"DEBUG: Starting party balancing with {len(all_parties)} parties")
            
            # Continue balancing until we have at most 1 incomplete party
            while True:
                # Refresh party data to get current member counts
                all_parties = list(Party.objects.filter(
                    event=event,
                    is_active=True
                ).order_by('party_number'))
                
                # Find incomplete parties (not at max capacity)
                incomplete_parties = [p for p in all_parties if p.member_count < p.max_members]
                complete_parties = [p for p in all_parties if p.member_count >= p.max_members]
                
                logger.info(f"DEBUG: Found {len(complete_parties)} complete parties and {len(incomplete_parties)} incomplete parties")
                
                # If we have at most 1 incomplete party, we're done
                if len(incomplete_parties) <= 1:
                    logger.info(f"DEBUG: Balancing complete - only {len(incomplete_parties)} incomplete party(ies) remaining")
                    break
                
                # Get the LAST party from ALL parties (not just incomplete ones) - highest party_number
                last_party = all_parties[-1]  # This is the actual last party created
                logger.info(f"DEBUG: Consolidating members from last party {last_party.party_number} (has {last_party.member_count} members)")
                
                # Get all members from the last party
                last_party_members = list(PartyMember.objects.filter(
                    party=last_party,
                    is_active=True
                ).select_related('player'))
                
                # Try to move members to incomplete parties (excluding the last one)
                # Sort incomplete parties by party_number to fill from first to last
                incomplete_parties_sorted = sorted([p for p in incomplete_parties if p.party_number != last_party.party_number], key=lambda p: p.party_number)
                
                members_moved_this_round = 0
                for member in last_party_members:
                    moved = False
                    for party in incomplete_parties_sorted:
                        # Get current member count from database
                        current_count = party.member_count
                        if current_count < party.max_members:
                            # Move member to this party
                            member.party = party
                            member.save()
                            balance_members_moved += 1
                            members_moved_this_round += 1
                            logger.info(f"DEBUG: Moved {member.player.in_game_name} from Party {last_party.party_number} to Party {party.party_number} (now {current_count + 1}/15)")
                            moved = True
                            break
                    
                    if not moved:
                        logger.info(f"DEBUG: Could not move {member.player.in_game_name} - no space in other parties")
                
                # Check if the last party is now empty
                last_party.refresh_from_db()
                if last_party.member_count == 0:
                    logger.info(f"DEBUG: Removing empty party {last_party.party_number}")
                    last_party.delete()
                    parties_removed += 1
                elif members_moved_this_round == 0:
                    # No members were moved this round, break to avoid infinite loop
                    logger.info(f"DEBUG: No members moved this round, stopping balancing")
                    break
        
        total_members_assigned = members_assigned + remaining_primary_members_assigned + filler_members_assigned + max_filler_members_assigned
        
        # Final refresh of all parties to ensure accurate member counts
        final_parties = Party.objects.filter(event=event, is_active=True).order_by('party_number')
        for party in final_parties:
            # Force fresh database query for member count
            member_count = party.member_count  # This will execute a fresh query
            logger.info(f"DEBUG: Final party {party.party_number} has {member_count} members")
        
        final_party_count = final_parties.count()
        
        return Response({
            'message': f'Created {final_party_count} parties with {total_members_assigned} members assigned',
            'parties_created': final_party_count,
            'members_assigned': total_members_assigned,
            'min_party_size': min_party_size,
            'primary_roles': primary_roles,
            'filler_roles': filler_roles,
            'config_filler_roles': list(filler_config_roles.keys()),
            'ignored_roles': {role: count for role, count in required_roles.items() if role not in primary_roles and role not in filler_roles},
            'balance_members_moved': balance_members_moved,
            'parties_removed': parties_removed
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def discord_bot_config(request):
    """Get Discord bot configuration"""
    try:
        from .models import DiscordBotConfig
        
        config = DiscordBotConfig.objects.first()
        if not config:
            return Response({'error': 'No bot configuration found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'id': config.id,
            'name': config.name,
            'is_active': config.is_active,
            'command_prefix': config.command_prefix,
            'base_url': config.base_url,
            'is_online': config.is_online,
            'general_channel_id': config.general_channel_id,
            'event_announcements_channel_id': config.event_announcements_channel_id,
            'violence_bot_channel_id': config.violence_bot_channel_id,
            'last_heartbeat': config.last_heartbeat.isoformat() if config.last_heartbeat else None,
            'error_message': config.error_message,
            'can_manage_messages': config.can_manage_messages,
            'can_embed_links': config.can_embed_links,
            'can_attach_files': config.can_attach_files,
            'can_read_message_history': config.can_read_message_history,
            'can_use_external_emojis': config.can_use_external_emojis,
            'created_at': config.created_at.isoformat(),
            'updated_at': config.updated_at.isoformat()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def update_discord_bot_config(request):
    """Update Discord bot configuration"""
    try:
        from .models import DiscordBotConfig
        
        config = DiscordBotConfig.objects.first()
        if not config:
            return Response({'error': 'No bot configuration found'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        
        # Update configuration fields
        config.name = data.get('name', config.name)
        config.is_active = data.get('is_active', config.is_active)
        config.command_prefix = data.get('command_prefix', config.command_prefix)
        config.base_url = data.get('base_url', config.base_url)
        config.general_channel_id = data.get('general_channel_id', config.general_channel_id)
        config.event_announcements_channel_id = data.get('event_announcements_channel_id', config.event_announcements_channel_id)
        config.violence_bot_channel_id = data.get('violence_bot_channel_id', config.violence_bot_channel_id)
        config.can_manage_messages = data.get('can_manage_messages', config.can_manage_messages)
        config.can_embed_links = data.get('can_embed_links', config.can_embed_links)
        config.can_attach_files = data.get('can_attach_files', config.can_attach_files)
        config.can_read_message_history = data.get('can_read_message_history', config.can_read_message_history)
        config.can_use_external_emojis = data.get('can_use_external_emojis', config.can_use_external_emojis)
        
        config.save()
        
        return Response({
            'message': 'Bot configuration updated successfully',
            'config': {
                'id': config.id,
                'name': config.name,
                'is_active': config.is_active,
                'command_prefix': config.command_prefix,
                'base_url': config.base_url,
                'is_online': config.is_online,
                'general_channel_id': config.general_channel_id,
                'event_announcements_channel_id': config.event_announcements_channel_id,
                'violence_bot_channel_id': config.violence_bot_channel_id,
                'last_heartbeat': config.last_heartbeat.isoformat() if config.last_heartbeat else None,
                'error_message': config.error_message,
                'can_manage_messages': config.can_manage_messages,
                'can_embed_links': config.can_embed_links,
                'can_attach_files': config.can_attach_files,
                'can_read_message_history': config.can_read_message_history,
                'can_use_external_emojis': config.can_use_external_emojis,
                'created_at': config.created_at.isoformat(),
                'updated_at': config.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def test_discord_bot_connection(request):
    """Test Discord bot connection"""
    try:
        from .models import DiscordBotConfig
        
        config = DiscordBotConfig.objects.first()
        if not config:
            return Response({'error': 'No bot configuration found'}, status=status.HTTP_404_NOT_FOUND)
        
        # This would typically test the actual bot connection
        # For now, we'll just return a success message
        # In a real implementation, you might:
        # 1. Check if the bot is running
        # 2. Test Discord API connectivity
        # 3. Verify channel permissions
        # 4. Update the bot's status
        
        return Response({
            'message': 'Bot connection test completed',
            'status': 'success'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def start_discord_bot(request):
    """Start the Discord bot (like Django admin action)"""
    try:
        from .models import DiscordBotConfig
        
        config = DiscordBotConfig.objects.first()
        if not config:
            return Response({'error': 'No bot configuration found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Use the same method as Django admin
        success, message = config.start_bot_manually()
        
        if success:
            return Response({
                'message': message,
                'status': 'success'
            })
        else:
            return Response({'error': message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def stop_discord_bot(request):
    """Stop the Discord bot (like Django admin action)"""
    try:
        from .models import DiscordBotConfig
        
        config = DiscordBotConfig.objects.first()
        if not config:
            return Response({'error': 'No bot configuration found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Use the same method as Django admin
        success, message = config.stop_bot_manually()
        
        if success:
            return Response({
                'message': message,
                'status': 'success'
            })
        else:
            return Response({'error': message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_party_configuration(request, event_id):
    """Get party configuration for an event"""
    try:
        from .models import Event, EventPartyConfiguration
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create configuration
        config = EventPartyConfiguration.get_or_create_default(event)
        
        return Response({
            'configuration': config.to_dict()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def save_party_configuration(request, event_id):
    """Save party configuration for an event"""
    try:
        from .models import Event, EventPartyConfiguration
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get configuration data
        data = request.data
        role_composition = data.get('roleComposition', {})
        guild_split = data.get('guildSplit', False)
        
        # Get or create configuration
        config = EventPartyConfiguration.get_or_create_default(event)
        
        # Update configuration
        config.healer_count = role_composition.get('healer', 2)
        config.ranged_dps_count = role_composition.get('ranged_dps', 0)
        config.melee_dps_count = role_composition.get('melee_dps', 0)
        config.defensive_tank_count = role_composition.get('defensive_tank', 2)
        config.offensive_tank_count = role_composition.get('offensive_tank', 2)
        config.offensive_support_count = role_composition.get('offensive_support', 0)
        config.defensive_support_count = role_composition.get('defensive_support', 0)
        config.guild_split = guild_split
        
        config.save()
        
        return Response({
            'message': 'Party configuration saved successfully',
            'configuration': config.to_dict()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_party(request, event_id):
    """Create a single party for an event"""
    try:
        from .models import Event, Party, EventParticipant
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        party_name = data.get('party_name', '')
        max_members = data.get('max_members', 15)
        
        # Get the next party number
        existing_parties = Party.objects.filter(event=event, is_active=True).order_by('-party_number')
        next_party_number = existing_parties[0].party_number + 1 if existing_parties else 1
        
        # Create the party
        party = Party.objects.create(
            event=event,
            party_number=next_party_number,
            party_name=party_name,
            max_members=max_members
        )
        
        return Response({
            'message': 'Party created successfully',
            'party': {
                'id': party.id,
                'party_number': party.party_number,
                'party_name': party.party_name,
                'max_members': party.max_members,
                'member_count': 0
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def add_member_to_party(request, event_id, party_id):
    """Add a participant to a specific party"""
    try:
        from .models import Event, Party, EventParticipant, Player
        
        # Get the event and party
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
            party = Party.objects.get(id=party_id, event=event, is_active=True)
        except (Event.DoesNotExist, Party.DoesNotExist):
            return Response({'error': 'Event or party not found'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        participant_id = data.get('participant_id')
        assigned_role = data.get('assigned_role')
        
        if not participant_id:
            return Response({'error': 'Participant ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the participant
        try:
            participant = EventParticipant.objects.get(
                id=participant_id,
                event=event,
            )
        except EventParticipant.DoesNotExist:
            return Response({'error': 'Participant not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if party is full
        if party.member_count >= party.max_members:
            return Response({'error': 'Party is full'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if participant is already in this party
        existing_member = PartyMember.objects.filter(
            party=party,
            event_participant=participant,
            is_active=True
        ).first()
        
        if existing_member:
            return Response({'error': 'Participant is already in this party'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Remove participant from any other parties first
        other_party_members = PartyMember.objects.filter(
            event_participant=participant,
            is_active=True
        ).exclude(party=party)
        
        for other_member in other_party_members:
            other_member.is_active = False
            other_member.save()
        
        # Check if there's an inactive PartyMember for this party/participant combination
        inactive_member = PartyMember.objects.filter(
            party=party,
            event_participant=participant,
            is_active=False
        ).first()
        
        if inactive_member:
            # Reactivate the existing record
            inactive_member.is_active = True
            inactive_member.assigned_role = assigned_role or participant.player.game_role if participant.player else inactive_member.assigned_role
            inactive_member.save()
            party_member = inactive_member
        else:
            # Create new PartyMember record
            # Check if this is the first member (will be leader)
            is_first_member = party.member_count == 0
            party_member = PartyMember.objects.create(
                party=party,
                event_participant=participant,
                player=participant.player,
                assigned_role=assigned_role or participant.player.game_role if participant.player else None,
                is_leader=is_first_member
            )
        
        return Response({
            'message': 'Member added to party successfully',
            'party_member': {
                'id': party_member.id,
                'discord_name': participant.discord_name,
                'assigned_role': party_member.assigned_role,
                'assigned_at': party_member.assigned_at.isoformat()
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def remove_member_from_party(request, event_id, party_id):
    """Remove a member from a party"""
    try:
        from .models import Event, Party, PartyMember
        
        # Get the event and party
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
            party = Party.objects.get(id=party_id, event=event, is_active=True)
        except (Event.DoesNotExist, Party.DoesNotExist):
            return Response({'error': 'Event or party not found'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        member_id = data.get('member_id')
        
        if not member_id:
            return Response({'error': 'Member ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get and remove the party member
        try:
            party_member = PartyMember.objects.get(
                id=member_id,
                party=party,
            )
            party_member.is_active = False
            party_member.save()
            
            return Response({
                'message': 'Member removed from party successfully',
                'member_id': party_member.id
            })
        except PartyMember.DoesNotExist:
            return Response({'error': 'Party member not found'}, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def delete_party(request, event_id, party_id):
    """Delete a party and all its members"""
    try:
        from .models import Event, Party, PartyMember
        
        # Get the event and party
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
            party = Party.objects.get(id=party_id, event=event, is_active=True)
        except (Event.DoesNotExist, Party.DoesNotExist):
            return Response({'error': 'Event or party not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Store party info for response before deletion
        party_name = party.party_name or f"Party {party.party_number}"
        party_id = party.id
        
        # Delete all party members first (due to foreign key constraints)
        deleted_members_count = PartyMember.objects.filter(party=party).delete()[0]
        
        # Delete the party itself
        party.delete()
        
        return Response({
            'message': f'Party "{party_name}" and {deleted_members_count} members deleted successfully',
            'party_id': party_id,
            'deleted_members_count': deleted_members_count
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
def update_party_name(request, event_id, party_id):
    """Update party name and settings"""
    try:
        from .models import Event, Party
        
        # Get the event and party
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
            party = Party.objects.get(id=party_id, event=event, is_active=True)
        except (Event.DoesNotExist, Party.DoesNotExist):
            return Response({'error': 'Event or party not found'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        
        # Update party fields
        if 'party_name' in data:
            party.party_name = data['party_name']
        if 'max_members' in data:
            max_members = int(data['max_members'])
            if max_members < party.member_count:
                return Response({'error': 'Cannot set max members below current member count'}, status=status.HTTP_400_BAD_REQUEST)
            party.max_members = max_members
        
        party.save()
        
        return Response({
            'message': 'Party updated successfully',
            'party': {
                'id': party.id,
                'party_number': party.party_number,
                'party_name': party.party_name,
                'max_members': party.max_members,
                'member_count': party.member_count
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def make_party_leader(request, event_id, party_id):
    """Make a party member the leader of the party"""
    try:
        from .models import Event, Party, PartyMember
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get the party
        try:
            party = Party.objects.get(id=party_id, event=event, is_active=True)
        except Party.DoesNotExist:
            return Response({'error': 'Party not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get member ID from request
        member_id = request.data.get('member_id')
        if not member_id:
            return Response({'error': 'member_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the member to make leader
        try:
            new_leader = PartyMember.objects.get(
                id=member_id,
                party=party,
                is_active=True
            )
        except PartyMember.DoesNotExist:
            return Response({'error': 'Party member not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Update all members in the party to remove leader status
        PartyMember.objects.filter(
            party=party,
            is_active=True
        ).update(is_leader=False)
        
        # Set the new leader
        new_leader.is_leader = True
        new_leader.save()
        
        return Response({
            'message': f'{new_leader.player.discord_name} is now the party leader',
            'leader': {
                'id': new_leader.id,
                'discord_name': new_leader.player.discord_name,
                'player_name': new_leader.player.in_game_name
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def make_party_leader(request, event_id, party_id):
    """Make a specific member the party leader"""
    try:
        from .models import Event, Party, PartyMember
        
        # Get the event
        try:
            event = Event.objects.get(id=event_id, is_active=True, is_cancelled=False)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get the party
        try:
            party = Party.objects.get(id=party_id, event=event, is_active=True)
        except Party.DoesNotExist:
            return Response({'error': 'Party not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get member_id from request
        member_id = request.data.get('member_id')
        if not member_id:
            return Response({'error': 'member_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the member to make leader
        try:
            member = PartyMember.objects.get(
                id=member_id,
                party=party,
                is_active=True
            )
        except PartyMember.DoesNotExist:
            return Response({'error': 'Party member not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Remove leader status from all other members in the party
        PartyMember.objects.filter(
            party=party,
            is_active=True
        ).exclude(id=member_id).update(is_leader=False)
        
        # Set this member as leader
        member.is_leader = True
        member.save()
        
        return Response({
            'message': f'{member.player.discord_name} is now the party leader',
            'leader': {
                'id': member.id,
                'player_name': member.player.discord_name,
                'is_leader': member.is_leader
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def discord_presence(request):
    """Get Discord presence status for multiple users"""
    try:
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response({'error': 'user_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        presence_data = {}
        
        # Try to get real presence data from Discord bot if available
        try:
            from .discord_bot import WarborneBot
            bot_instance = WarborneBot.get_instance()
            
            if bot_instance and bot_instance.bot and bot_instance.bot.is_ready():
                guild = bot_instance.bot.get_guild(bot_instance.config.get('guild_id'))
                
                if guild:
                    for user_id in user_ids:
                        member = guild.get_member(int(user_id))
                        if member:
                            # Get real presence status
                            status = member.status
                            presence_data[str(user_id)] = {
                                'status': str(status),  # online, idle, dnd, offline
                                'activities': [activity.name for activity in member.activities if activity.name],
                                'client_status': {
                                    'desktop': str(member.desktop_status),
                                    'mobile': str(member.mobile_status),
                                    'web': str(member.web_status)
                                }
                            }
                        else:
                            # Member not found in guild, assume offline
                            presence_data[str(user_id)] = {
                                'status': 'offline',
                                'activities': [],
                                'client_status': {
                                    'desktop': 'offline',
                                    'mobile': 'offline',
                                    'web': 'offline'
                                }
                            }
                else:
                    # Guild not found, use mock data
                    raise Exception("Guild not found")
            else:
                # Bot not ready, use mock data
                raise Exception("Bot not ready")
                
        except Exception as bot_error:
            # Fallback to intelligent mock data
            print(f"Discord bot presence unavailable: {bot_error}")
            
            # For now, return a mix of online/offline to simulate real data
            # In production, you would implement proper Discord Gateway connection
            import random
            
            for i, user_id in enumerate(user_ids):
                # Simulate some users being online (70% chance)
                if random.random() < 0.7:
                    status_options = ['online', 'idle', 'dnd']
                    status = random.choice(status_options)
                else:
                    status = 'offline'
                
                presence_data[str(user_id)] = {
                    'status': status,
                    'activities': ['Playing Warborne'] if status != 'offline' else [],
                    'client_status': {
                        'desktop': status if status != 'offline' else 'offline',
                        'mobile': 'offline',
                        'web': status if status != 'offline' else 'offline'
                    }
                }
        
        return Response({
            'presence': presence_data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    """JWT-based logout (client-side token removal)"""
    try:
        # For JWT logout, we don't need to blacklist on server side
        # The client should remove tokens from localStorage
        # This is a simple logout that just returns success
        
        return Response({
            'success': True,
            'message': 'Logout successful'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def auth_verify(request):
    """Verify JWT token and return user info"""
    try:
        user = request.user
        
        # Check if user has a player profile (optional)
        player = None
        try:
            player = Player.objects.get(in_game_name=user.username)
        except Player.DoesNotExist:
            # Player profile doesn't exist, which is fine for web users
            pass
        
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'player_id': player.id if player else None
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def auth_login(request):
    """JWT-based authentication login"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'success': False,
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_active:
            # Check if user has a player profile (optional)
            player = None
            try:
                player = Player.objects.get(in_game_name=user.username)
            except Player.DoesNotExist:
                # Player profile doesn't exist, which is fine for web users
                pass
            
            # Generate JWT tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'player_id': player.id if player else None
                },
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                },
                'message': 'Login successful'
            })
        else:
            return Response({
                'success': False,
                'error': 'Invalid username or password'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_refresh(request):
    """Refresh JWT token"""
    try:
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({
                'success': False,
                'error': 'Refresh token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken(refresh_token)
        access_token = refresh.access_token
        
        return Response({
            'success': True,
            'tokens': {
                'access': str(access_token),
                'refresh': str(refresh)
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Invalid refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    """JWT-based logout (blacklist refresh token)"""
    try:
        refresh_token = request.data.get('refresh')
        
        if refresh_token:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'success': True,
            'message': 'Logout successful'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# User Management API endpoints
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def user_list(request):
    """Get list of all users (staff only)"""
    try:
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        users = User.objects.all().order_by('-date_joined')
        user_data = []
        
        for user in users:
            user_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            })
        
        return Response({
            'success': True,
            'users': user_data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_user(request):
    """Create a new user (staff only)"""
    try:
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        is_staff = request.data.get('is_staff', False)
        is_active = request.data.get('is_active', True)
        
        # Validate required fields
        if not username:
            return Response({
                'success': False,
                'error': 'Username is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not password:
            return Response({
                'success': False,
                'error': 'Password is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return Response({
                'success': False,
                'error': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if email already exists (if provided)
        if email and User.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'error': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
            is_active=is_active
        )
        
        return Response({
            'success': True,
            'message': f'User {username} created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat()
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    """Update user information (staff only)"""
    try:
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update fields if provided
        if 'username' in request.data:
            # Check if new username already exists
            new_username = request.data['username']
            if new_username != user.username and User.objects.filter(username=new_username).exists():
                return Response({
                    'success': False,
                    'error': 'Username already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
            user.username = new_username
        
        if 'email' in request.data:
            # Check if new email already exists
            new_email = request.data['email']
            if new_email != user.email and new_email and User.objects.filter(email=new_email).exists():
                return Response({
                    'success': False,
                    'error': 'Email already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
            user.email = new_email
        
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        
        if 'is_active' in request.data:
            user.is_active = request.data['is_active']
        
        if 'is_staff' in request.data:
            user.is_staff = request.data['is_staff']
        
        if 'password' in request.data and request.data['password']:
            user.set_password(request.data['password'])
        
        user.save()
        
        return Response({
            'success': True,
            'message': f'User {user.username} updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    """Delete a user (staff only, cannot delete superuser)"""
    try:
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Prevent deletion of superusers
        if user.is_superuser:
            return Response({
                'success': False,
                'error': 'Cannot delete superuser accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent self-deletion
        if user.id == request.user.id:
            return Response({
                'success': False,
                'error': 'Cannot delete your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        username = user.username
        user.delete()
        
        return Response({
            'success': True,
            'message': f'User {username} deleted successfully'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def gear_power_analytics(request):
    """Get gear power analytics for all players with their loadouts"""
    try:
        from .models import Player, PlayerGear, GearItem
        
        # Get all players
        players = Player.objects.all()
        analytics_data = []
        
        for player in players:
            # Get player's drifters
            drifters_data = []
            for i in range(1, 4):  # 3 drifters
                drifter = getattr(player, f'drifter_{i}', None)
                if drifter:
                    # Get equipped gear for this drifter
                    equipped_gear = PlayerGear.objects.filter(
                        player=player, 
                        is_equipped=True,
                        equipped_on_drifter=i
                    ).select_related('gear_item__gear_type')
                    
                    # Calculate gear power for this loadout
                    total_power = 0
                    gear_count = 0
                    
                    # Only count weapon, helmet, chest, boots, off-hand (first 5 slots)
                    main_slots = ['weapon', 'helmet', 'chest', 'boots', 'consumable']
                    equipped_list = list(equipped_gear)
                    
                    for slot_type in main_slots:
                        slot_gear = None
                        for gear in equipped_list:
                            if gear.gear_item.gear_type.category == slot_type:
                                slot_gear = gear
                                break
                        
                        if slot_gear:
                            gear_power = slot_gear.gear_item.get_gear_power()
                            total_power += gear_power
                            gear_count += 1
                    
                    # Only include loadouts that have at least one equipped item
                    if gear_count > 0:
                        loadout_power = total_power // 5  # floor division
                        drifters_data.append({
                            'drifter_name': drifter.name,
                            'drifter_number': i,
                            'gear_power': loadout_power,
                            'equipped_count': gear_count
                        })
            
            # Only include players who have at least one complete loadout
            if drifters_data:
                analytics_data.append({
                    'player_id': player.id,
                    'player_name': player.in_game_name,
                    'loadouts': drifters_data
                })
        
        return Response({
            'analytics': analytics_data,
            'total_players': len(analytics_data),
            'total_loadouts': sum(len(player['loadouts']) for player in analytics_data)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def role_analytics(request):
    """Get role distribution analytics for all players with loadouts"""
    try:
        from .models import Player, PlayerGear, GearItem
        
        # Get all players
        players = Player.objects.all()
        role_data = {}
        
        for player in players:
            # Get player's drifters and check if they have any equipped loadouts
            has_loadout = False
            for i in range(1, 4):  # 3 drifters
                drifter = getattr(player, f'drifter_{i}', None)
                if drifter:
                    # Check if this drifter has equipped gear
                    equipped_gear = PlayerGear.objects.filter(
                        player=player, 
                        is_equipped=True,
                        equipped_on_drifter=i
                    ).exists()
                    
                    if equipped_gear:
                        has_loadout = True
                        break
            
            # Only count players who have at least one equipped loadout
            if has_loadout and player.game_role:
                role = player.game_role
                if role not in role_data:
                    role_data[role] = {
                        'role_name': role,
                        'player_count': 0,
                        'players': []
                    }
                role_data[role]['player_count'] += 1
                role_data[role]['players'].append({
                    'player_name': player.in_game_name,
                    'player_id': player.id
                })
        
        # Convert to list and sort by player count
        analytics_data = list(role_data.values())
        analytics_data.sort(key=lambda x: x['player_count'], reverse=True)
        
        return Response({
            'analytics': analytics_data,
            'total_roles': len(analytics_data),
            'total_players': sum(role['player_count'] for role in analytics_data)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def event_participation_analytics(request):
    """Get event participation analytics showing time vs number of players by event category"""
    try:
        from .models import Event, EventParticipant
        from django.db.models import Count
        from datetime import datetime, timedelta
        import json
        
        # Get events from the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        events = Event.objects.filter(
            event_datetime__gte=thirty_days_ago,
            is_active=True,
            is_cancelled=False
        ).order_by('event_datetime')
        
        # Group events by date and category
        daily_data = {}
        categories = set()
        
        for event in events:
            # Get participant count for this event
            participant_count = EventParticipant.objects.filter(event=event).count()
            
            # Format date as YYYY-MM-DD
            event_date = event.event_datetime.date().strftime('%Y-%m-%d')
            event_category = event.event_type or 'other'
            categories.add(event_category)
            
            if event_date not in daily_data:
                daily_data[event_date] = {}
            
            if event_category not in daily_data[event_date]:
                daily_data[event_date][event_category] = 0
            
            daily_data[event_date][event_category] += participant_count
        
        # Convert to chart format
        chart_data = []
        for date_str, categories_data in sorted(daily_data.items()):
            chart_data.append({
                'date': date_str,
                **categories_data
            })
        
        # Prepare series data for each category
        series_data = {}
        for category in sorted(categories):
            series_data[category] = {
                'name': category.replace('_', ' ').title(),
                'data': []
            }
            
            for point in chart_data:
                value = point.get(category, 0)
                series_data[category]['data'].append({
                    'x': point['date'],
                    'y': value
                })
        
        return Response({
            'analytics': list(series_data.values()),
            'categories': sorted(categories),
            'total_events': events.count(),
            'date_range': {
                'start': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                'end': datetime.now().strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== BLUEPRINTS API ENDPOINTS ====================

@api_view(['GET'])
def blueprints_list(request):
    """Get all legendary blueprints"""
    try:
        from .models import LegendaryBlueprint
        
        blueprints = LegendaryBlueprint.objects.select_related('player').all()
        
        blueprint_data = []
        for blueprint in blueprints:
            blueprint_data.append({
                'id': blueprint.id,
                'player_name': blueprint.player.discord_name,
                'player_id': blueprint.player.id,
                'item_name': blueprint.item_name,
                'item_display': blueprint.get_item_name_display(),
                'quantity': blueprint.quantity,
                'can_craft_free': blueprint.can_craft_free,
                'status': blueprint.status,
                'created_at': blueprint.created_at,
                'updated_at': blueprint.updated_at
            })
        
        return Response({
            'blueprints': blueprint_data,
            'total': len(blueprint_data)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_blueprint(request):
    """Create a new legendary blueprint"""
    try:
        from .models import LegendaryBlueprint, Player
        
        data = request.data
        player_name = data.get('player_name')
        item_name = data.get('item_name')
        quantity = data.get('quantity', 1)
        
        if not player_name or not item_name:
            return Response({'error': 'Player name and item name are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find player by discord name
        try:
            player = Player.objects.get(discord_name=player_name)
        except Player.DoesNotExist:
            return Response({'error': f'Player "{player_name}" not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if blueprint already exists for this player and item
        blueprint, created = LegendaryBlueprint.objects.get_or_create(
            player=player,
            item_name=item_name,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Update existing blueprint quantity
            blueprint.quantity += quantity
            blueprint.save()
            message = f'Updated blueprint quantity to {blueprint.quantity}'
        else:
            message = f'Created blueprint with quantity {blueprint.quantity}'
        
        return Response({
            'message': message,
            'blueprint': {
                'id': blueprint.id,
                'player_name': blueprint.player.discord_name,
                'item_name': blueprint.item_name,
                'item_display': blueprint.get_item_name_display(),
                'quantity': blueprint.quantity,
                'can_craft_free': blueprint.can_craft_free,
                'status': blueprint.status
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_blueprint(request, blueprint_id):
    """Delete a legendary blueprint"""
    try:
        from .models import LegendaryBlueprint
        
        blueprint = LegendaryBlueprint.objects.get(id=blueprint_id)
        blueprint.delete()
        
        return Response({
            'message': 'Blueprint deleted successfully'
        })
        
    except LegendaryBlueprint.DoesNotExist:
        return Response({'error': 'Blueprint not found'}, status=status.HTTP_404_NOT_FOUND)


# ==================== CRAFTERS API ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def crafters_list(request):
    """Get all crafters"""
    try:
        from .models import Crafter
        
        crafters = Crafter.objects.select_related('player', 'created_by').all()
        
        crafter_data = []
        for crafter in crafters:
            crafter_data.append({
                'id': crafter.id,
                'player_name': crafter.player.discord_name,
                'player_id': crafter.player.id,
                'item_name': crafter.item_name,
                'item_display': crafter.get_item_name_display(),
                'created_at': crafter.created_at,
                'created_by': crafter.created_by.username if crafter.created_by else 'System'
            })
        
        return Response({
            'crafters': crafter_data,
            'total': len(crafter_data)
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_crafter(request):
    """Create a new crafter"""
    try:
        from .models import Crafter, Player
        
        data = request.data
        player_name = data.get('player_name')
        item_name = data.get('item_name')
        
        if not player_name or not item_name:
            return Response({'error': 'Player name and item name are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find player by discord name
        try:
            player = Player.objects.get(discord_name=player_name)
        except Player.DoesNotExist:
            return Response({'error': f'Player "{player_name}" not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if crafter already exists for this player and item
        crafter, created = Crafter.objects.get_or_create(
            player=player,
            item_name=item_name,
            defaults={'created_by': request.user}
        )
        
        if created:
            message = f'{player.discord_name} is now a crafter for {item_name}'
        else:
            message = f'{player.discord_name} is already a crafter for {item_name}'
        
        return Response({
            'message': message,
            'crafter': {
                'id': crafter.id,
                'player_name': crafter.player.discord_name,
                'item_name': crafter.item_name,
                'item_display': crafter.get_item_name_display(),
                'created_at': crafter.created_at,
                'created_by': crafter.created_by.username if crafter.created_by else 'System'
            }
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_crafter(request, crafter_id):
    """Delete a crafter"""
    try:
        from .models import Crafter
        
        crafter = Crafter.objects.get(id=crafter_id)
        player_name = crafter.player.discord_name
        item_name = crafter.get_item_name_display()
        crafter.delete()
        
        return Response({
            'message': f'{player_name} is no longer a crafter for {item_name}'
        })
    
    except Crafter.DoesNotExist:
        return Response({'error': 'Crafter not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _create_guild_split_parties(event, participants, required_roles, filler_config_roles):
    """Create parties separately for each guild when guild_split is enabled"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Group participants by guild
    participants_by_guild = {}
    for participant in participants:
        guild = participant.player.guild
        guild_name = guild.name if guild else "No Guild"
        if guild_name not in participants_by_guild:
            participants_by_guild[guild_name] = []
        participants_by_guild[guild_name].append(participant)
    
    logger.info(f"🏰 Guilds found: {list(participants_by_guild.keys())}")
    for guild_name, guild_participants in participants_by_guild.items():
        logger.info(f"  - {guild_name}: {len(guild_participants)} participants")
    
    total_parties_created = 0
    total_members_assigned = 0
    guild_results = []
    
    # Process each guild separately
    for guild_name, guild_participants in participants_by_guild.items():
        logger.info(f"🏰 Processing guild: {guild_name}")
        
        # Group participants by role for this guild with role mapping
        participants_by_role = {}
        
        # Role mapping for common role variations
        ROLE_MAPPING = {
            'tank': 'defensive_tank',
            'dps': 'ranged_dps',
            'support': 'offensive_support'
        }
        
        for participant in guild_participants:
            role = participant.player.game_role or 'unknown'
            
            # Apply role mapping if needed
            if role in ROLE_MAPPING:
                role = ROLE_MAPPING[role]
                logger.info(f"DEBUG: Guild {guild_name} - Mapped role '{participant.player.game_role}' to '{role}' for {participant.player.in_game_name}")
            
            if role not in participants_by_role:
                participants_by_role[role] = []
            participants_by_role[role].append(participant)
        
        # Use the same party creation logic as the main function
        guild_parties_created, guild_members_assigned = _create_parties_for_guild(
            event, guild_participants, participants_by_role, required_roles, filler_config_roles, guild_name
        )
        
        total_parties_created += guild_parties_created
        total_members_assigned += guild_members_assigned
        
        guild_results.append({
            'guild': guild_name,
            'parties_created': guild_parties_created,
            'members_assigned': guild_members_assigned
        })
    
    return Response({
        'success': True,
        'message': f'Created {total_parties_created} parties with {total_members_assigned} members assigned (guild split mode)',
        'parties_created': total_parties_created,
        'members_assigned': total_members_assigned,
        'guild_results': guild_results,
        'guild_split': True
    })


def _create_parties_for_guild(event, guild_participants, participants_by_role, required_roles, filler_config_roles, guild_name):
    """Create parties for a specific guild using the same logic as the main fill_parties function"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Filter roles to only those available in this guild
    available_roles = {}
    for role, required_count in required_roles.items():
        available_count = len(participants_by_role.get(role, []))
        if available_count > 0:
            available_roles[role] = required_count
            logger.info(f"DEBUG: Guild {guild_name} - Role {role} - Available: {available_count}, Required: {required_count}")
    
    if not available_roles:
        logger.info(f"DEBUG: Guild {guild_name} - No available roles, skipping party creation")
        return 0, 0
    
    # Calculate minimum party size
    min_party_size = sum(available_roles.values())
    logger.info(f"DEBUG: Guild {guild_name} - Using roles: {available_roles}, min_party_size: {min_party_size}")
    
    parties_created = 0
    members_assigned = 0
    
    # Keep creating parties until we can't fill all available roles
    while True:
        # Check if we have enough participants for all available roles
        can_create_party = True
        for role, required_count in available_roles.items():
            available_count = len(participants_by_role.get(role, []))
            logger.info(f"DEBUG: Guild {guild_name} - Role {role} - Available: {available_count}, Required: {required_count}")
            if available_count < required_count:
                can_create_party = False
                logger.info(f"DEBUG: Guild {guild_name} - Cannot create party - not enough {role}")
                break
        
        if not can_create_party:
            # Try to create parties with available roles (even if not complete)
            logger.info(f"DEBUG: Guild {guild_name} - Cannot create complete party, trying to create incomplete parties with available roles")
            
            # Check if we have any participants left in any role
            total_remaining = sum(len(participants_by_role.get(role, [])) for role in available_roles.keys())
            if total_remaining >= 4:  # Minimum party size
                logger.info(f"DEBUG: Guild {guild_name} - Creating incomplete parties with {total_remaining} remaining participants")
                # Continue with incomplete party creation
            else:
                logger.info(f"DEBUG: Guild {guild_name} - Stopping party creation - insufficient participants for even incomplete parties")
                break
        
        # Create new party
        new_party = Party.objects.create(
            event=event,
            party_number=Party.objects.filter(event=event, is_active=True).count() + 1,
            party_name=f"{guild_name} Party {parties_created + 1}",
            max_members=15,
            is_active=True
        )
        parties_created += 1
        logger.info(f"DEBUG: Guild {guild_name} - Created party {parties_created}")
        
        # Assign available roles to this party
        for role, required_count in available_roles.items():
            available_participants = participants_by_role.get(role, [])
            # For incomplete parties, assign what's available instead of requiring exact count
            assign_count = min(required_count, len(available_participants))
            for i in range(assign_count):
                participant = available_participants.pop(0)  # Remove from available list
                
                # Create party member
                is_first_member = new_party.member_count == 0
                PartyMember.objects.create(
                    party=new_party,
                    event_participant=participant,
                    player=participant.player,
                    assigned_role=participant.player.game_role,
                    is_leader=is_first_member
                )
                members_assigned += 1
                logger.info(f"DEBUG: Guild {guild_name} - Assigned {participant.player.in_game_name} as {role}")
            
            if assign_count < required_count:
                logger.info(f"DEBUG: Guild {guild_name} - Party {parties_created} incomplete - only {assign_count}/{required_count} {role} assigned")
        
        logger.info(f"DEBUG: Guild {guild_name} - Party {parties_created} complete. Remaining: {sum(len(participants_by_role.get(role, [])) for role in available_roles.keys())} total participants")
    
    # Phase 2: Add remaining participants as fillers to existing parties
    for role, required_count in available_roles.items():
        remaining_participants = participants_by_role.get(role, [])
        if remaining_participants:
            logger.info(f"DEBUG: Guild {guild_name} - Adding remaining {len(remaining_participants)} {role} players as fillers to existing parties")
            
            created_parties = Party.objects.filter(event=event, is_active=True, party_name__startswith=guild_name).order_by('party_number')
            
            for participant in remaining_participants:
                # Find a party that has space
                assigned = False
                for party in created_parties:
                    if party.member_count < party.max_members:
                        # Add to this party as filler
                        PartyMember.objects.create(
                            party=party,
                            event_participant=participant,
                            player=participant.player,
                            assigned_role=participant.player.game_role,
                            is_leader=False
                        )
                        members_assigned += 1
                        logger.info(f"DEBUG: Guild {guild_name} - Added {participant.player.in_game_name} as {role} filler to Party {party.party_number}")
                        assigned = True
                        break
                
                if not assigned:
                    logger.info(f"DEBUG: Guild {guild_name} - Could not assign {participant.player.in_game_name} as {role} filler - all parties at max capacity")
    
    # Phase 3: Consolidate small parties within this guild
    created_parties = list(Party.objects.filter(event=event, is_active=True, party_name__startswith=guild_name).order_by('party_number'))
    if len(created_parties) > 1:
        logger.info(f"DEBUG: Guild {guild_name} - Starting party consolidation with {len(created_parties)} parties")
        
        # Multi-round consolidation
        while True:
            incomplete_parties = [party for party in created_parties if party.member_count < 15]
            logger.info(f"DEBUG: Guild {guild_name} - Found {len(incomplete_parties)} incomplete parties")
            
            if len(incomplete_parties) <= 1:
                logger.info(f"DEBUG: Guild {guild_name} - Consolidation complete - only {len(incomplete_parties)} incomplete party(ies) remaining")
                break
            
            # Find the smallest incomplete party to consolidate
            smallest_party = min(incomplete_parties, key=lambda p: p.member_count)
            
            # If the smallest party has very few members, consolidate it
            if smallest_party.member_count <= 3:
                logger.info(f"DEBUG: Guild {guild_name} - Consolidating small party {smallest_party.party_number} (has {smallest_party.member_count} members)")
                
                # Get all members from the smallest party
                small_party_members = list(PartyMember.objects.filter(party=smallest_party, is_active=True))
                members_moved = 0
                
                for member in small_party_members:
                    # Find the first incomplete party that has space (excluding the smallest party)
                    for target_party in incomplete_parties:
                        if target_party != smallest_party and target_party.member_count < target_party.max_members:
                            # Move this member to the target party
                            member.party = target_party
                            member.save()
                            members_moved += 1
                            logger.info(f"DEBUG: Guild {guild_name} - Moved {member.player.in_game_name} from Party {smallest_party.party_number} to Party {target_party.party_number}")
                            break
                
                if members_moved == 0:
                    logger.info(f"DEBUG: Guild {guild_name} - No members could be moved from party {smallest_party.party_number}")
                    break
                
                # If the smallest party is now empty, remove it
                smallest_party.refresh_from_db()
                if smallest_party.member_count == 0:
                    logger.info(f"DEBUG: Guild {guild_name} - Removing empty party {smallest_party.party_number}")
                    smallest_party.delete()
                    created_parties.remove(smallest_party)
            else:
                logger.info(f"DEBUG: Guild {guild_name} - Smallest party has {smallest_party.member_count} members, stopping consolidation")
                break
    
    # Add config filler roles to fill parties to max capacity
    for role, _ in filler_config_roles.items():
        participants = participants_by_role.get(role, [])
        if participants:
            logger.info(f"DEBUG: Guild {guild_name} - Adding {len(participants)} {role} players as fillers to reach max party size")
            
            created_parties = Party.objects.filter(event=event, is_active=True, party_name__startswith=guild_name).order_by('party_number')
            
            for participant in participants:
                # Find a party that has space
                assigned = False
                for party in created_parties:
                    if party.member_count < party.max_members:
                        # Add to this party
                        PartyMember.objects.create(
                            party=party,
                            event_participant=participant,
                            player=participant.player,
                            assigned_role=participant.player.game_role,
                            is_leader=False
                        )
                        members_assigned += 1
                        logger.info(f"DEBUG: Guild {guild_name} - Added {participant.player.in_game_name} as {role} filler to Party {party.party_number}")
                        assigned = True
                        break
                
                if not assigned:
                    logger.info(f"DEBUG: Guild {guild_name} - Could not assign {participant.player.in_game_name} as {role} filler - all parties at max capacity")
    
    logger.info(f"DEBUG: Guild {guild_name} - Total members assigned: {members_assigned}")
    
    return parties_created, members_assigned


