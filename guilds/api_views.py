from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from .models import Guild, Player, Drifter, Event, GearItem, GearType, RecommendedBuild, PlayerGear
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
