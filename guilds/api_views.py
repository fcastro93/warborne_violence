from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
import pytz
from .models import Guild, Player, Drifter, Event, EventParticipant, Party, PartyMember, GearItem, GearType, RecommendedBuild, PlayerGear
import json

@api_view(['POST'])
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
            'guild': player.guild.name if player.guild else None,
        })
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
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
                'game_id': gear.gear_item.game_id,
                'icon_url': gear.gear_item.icon_url,
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


# Event Management API endpoints
@api_view(['GET'])
def events_list(request):
    """Get all events with participant counts"""
    try:
        events = Event.objects.filter(is_active=True, is_cancelled=False).order_by('-event_datetime')
        
        events_data = []
        for event in events:
            participant_count = EventParticipant.objects.filter(
                event=event, 
                is_active=True
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
            event=event, 
            is_active=True
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
                is_active=True
            ).select_related('player', 'event_participant')
            
            members_data = []
            for member in party_members:
                members_data.append({
                    'id': member.id,
                    'player_name': member.player.in_game_name,
                    'discord_name': member.event_participant.discord_name,
                    'assigned_role': member.assigned_role,
                    'assigned_at': member.assigned_at.isoformat()
                })
            
            parties_data.append({
                'id': party.id,
                'party_number': party.party_number,
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
    """Delete/cancel an event"""
    try:
        event = Event.objects.get(id=event_id)
        
        # Instead of deleting, mark as cancelled
        event.is_cancelled = True
        event.is_active = False
        event.save()
        
        return Response({
            'message': 'Event cancelled successfully',
            'event_id': event.id
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
        
        if not discord_user_id or not discord_name:
            return Response({'error': 'Discord user ID and name are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        event = Event.objects.get(id=event_id)
        
        # Check if event is still active
        if not event.is_active or event.is_cancelled:
            return Response({'error': 'Event is not active'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if event is full
        if event.max_participants:
            current_participants = EventParticipant.objects.filter(event=event, is_active=True).count()
            if current_participants >= event.max_participants:
                return Response({'error': 'Event is full'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already participating
        existing_participant = EventParticipant.objects.filter(
            event=event,
            discord_user_id=discord_user_id
        ).first()
        
        if existing_participant:
            if existing_participant.is_active:
                return Response({'error': 'Already participating in this event'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Reactivate participation
                existing_participant.is_active = True
                existing_participant.discord_name = discord_name
                existing_participant.save()
                participant = existing_participant
        else:
            # Get player if exists
            player = Player.objects.filter(discord_user_id=discord_user_id).first()
            
            # Create new participant
            participant = EventParticipant.objects.create(
                event=event,
                discord_user_id=discord_user_id,
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
            discord_user_id=discord_user_id,
            is_active=True
        ).first()
        
        if not participant:
            return Response({'error': 'Not participating in this event'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Deactivate participation
        participant.is_active = False
        participant.save()
        
        return Response({
            'message': 'Successfully left event',
            'participant_id': participant.id
        })
        
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
