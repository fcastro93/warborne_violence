from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from functools import wraps
from .models import Player, PlayerGear, GearItem, Drifter, DiscordBotConfig
import threading
import json


def discord_owner_or_staff_required(view_func):
    """
    Decorator that checks if the request is from the Discord owner of the player or staff.
    Expects discord_user_id in request.GET or request.POST
    """
    @wraps(view_func)
    def _wrapped_view(request, player_id, *args, **kwargs):
        # Get Discord user ID from request parameters
        discord_user_id = request.GET.get('discord_user_id') or request.POST.get('discord_user_id')
        
        if not discord_user_id:
            return JsonResponse({'error': 'Discord user ID required'}, status=400)
        
        try:
            discord_user_id = int(discord_user_id)
        except ValueError:
            return JsonResponse({'error': 'Invalid Discord user ID'}, status=400)
        
        # Get the player
        player = get_object_or_404(Player, id=player_id)
        
        # Check permissions
        is_staff = request.user.is_staff if hasattr(request, 'user') and request.user.is_authenticated else False
        can_modify = player.can_modify(discord_user_id, is_staff)
        
        if not can_modify:
            return JsonResponse({'error': 'Permission denied. Only the player owner or staff can modify this loadout.'}, status=403)
        
        # Add player and discord_user_id to request for use in the view
        request.player = player
        request.discord_user_id = discord_user_id
        
        return view_func(request, player_id, *args, **kwargs)
    
    return _wrapped_view


def player_loadout(request, player_id):
    """View to display player's loadout with 3 drifter tabs"""
    player = get_object_or_404(Player, id=player_id)
    
    # Get all player gear for equipped status checking
    player_gear = PlayerGear.objects.filter(
        player=player
    ).select_related('gear_item__gear_type')
    
    # Create a set of owned gear IDs for quick lookup
    owned_gear_ids = set(player_gear.values_list('gear_item_id', flat=True))
    owned_gear_by_id = {pg.gear_item_id: pg for pg in player_gear}
    
    # Base URL for item images from local static files
    image_base_url = "/static/icons/"
    
    # Prepare drifter data for each of the 3 drifters
    drifters_data = []
    for drifter_num in [1, 2, 3]:
        drifter = getattr(player, f'drifter_{drifter_num}', None)
        if drifter:
            # Get equipped gear for this specific drifter
            equipped_gear = PlayerGear.objects.filter(
                player=player, 
                is_equipped=True,
                equipped_on_drifter=drifter_num
            ).select_related('gear_item__gear_type')
            
            # Prepare gear slots for this drifter (9 slots: weapon, helmet, chest, boots, consumable, 4 mods)
            gear_slots = []
            equipped_list = list(equipped_gear)
            
            # Define slot order: weapon, helmet, chest, boots, consumable, 4 mods
            slot_order = ['weapon', 'helmet', 'chest', 'boots', 'consumable'] + ['mod'] * 4
            
            for i in range(9):
                # Find gear for this slot
                slot_gear = None
                for gear in equipped_list:
                    if gear.gear_item.gear_type.category == slot_order[i]:
                        slot_gear = gear
                        break
                
                gear_slots.append(slot_gear)
            
            drifters_data.append({
                'number': drifter_num,
                'drifter': drifter,
                'equipped_gear': equipped_gear,
                'gear_slots': gear_slots,
                'equipped_count': equipped_gear.count(),
            })
        else:
            drifters_data.append({
                'number': drifter_num,
                'drifter': None,
                'equipped_gear': [],
                'gear_slots': [None] * 9,
                'equipped_count': 0,
            })
    
    # Get all available gear items in the game, organized by type and rarity
    from django.db.models import Case, When, IntegerField
    
    all_gear_items = GearItem.objects.all().select_related('gear_type').annotate(
        rarity_order=Case(
            When(rarity='common', then=1),
            When(rarity='uncommon', then=2),
            When(rarity='rare', then=3),
            When(rarity='epic', then=4),
            When(rarity='legendary', then=5),
            default=0,
            output_field=IntegerField(),
        )
    ).order_by('gear_type__category', 'rarity_order', 'base_name')
    
    # Organize gear by type and attribute for better display
    gear_by_type = {}
    for gear_item in all_gear_items:
        gear_type = gear_item.gear_type.category
        if gear_type not in gear_by_type:
            gear_by_type[gear_type] = {
                'Strength': [],
                'Agility': [],
                'Intelligence': [],
                'Other': []
            }
        
        # Check if player owns this item and its equipped status
        is_owned = gear_item.id in owned_gear_ids
        player_gear_instance = owned_gear_by_id.get(gear_item.id)
        
        item_data = {
            'gear_item': gear_item,
            'is_owned': is_owned,
            'player_gear': player_gear_instance,
            'is_equipped': player_gear_instance.is_equipped if player_gear_instance else False,
            'equipped_on_drifter': player_gear_instance.equipped_on_drifter if player_gear_instance else None,
        }
        
        # Determine attribute based on gear type name
        gear_type_name = gear_item.gear_type.name.lower()
        
        # Special handling for mods and consumables - don't categorize by attribute, just add to a single list
        if gear_type == 'mod':
            if 'All' not in gear_by_type[gear_type]:
                gear_by_type[gear_type]['All'] = []
            gear_by_type[gear_type]['All'].append(item_data)
        elif gear_type == 'consumable':
            if 'All' not in gear_by_type[gear_type]:
                gear_by_type[gear_type]['All'] = []
            gear_by_type[gear_type]['All'].append(item_data)
        elif gear_type == 'weapon':
            # For weapons, categorize by weapon type instead of attribute
            weapon_type = gear_item.gear_type.name.split(' (')[0]  # Extract weapon type (e.g., "Sword" from "Sword (Strength)")
            if weapon_type not in gear_by_type[gear_type]:
                gear_by_type[gear_type][weapon_type] = []
            gear_by_type[gear_type][weapon_type].append(item_data)
        else:
            # For other gear types (boots, chest, helmet), categorize by attribute
            if 'strength' in gear_type_name or 'str_' in gear_item.game_id.lower():
                gear_by_type[gear_type]['Strength'].append(item_data)
            elif 'agility' in gear_type_name or 'dex_' in gear_item.game_id.lower():
                gear_by_type[gear_type]['Agility'].append(item_data)
            elif 'intelligence' in gear_type_name or 'int_' in gear_item.game_id.lower():
                gear_by_type[gear_type]['Intelligence'].append(item_data)
            else:
                gear_by_type[gear_type]['Other'].append(item_data)
    
    # Check if current request can modify this player (for display purposes)
    discord_user_id = request.GET.get('discord_user_id')
    can_modify = True  # Everyone can modify loadouts now
    is_owner = False
    
    if discord_user_id:
        try:
            discord_user_id = int(discord_user_id)
            is_owner = player.is_owner(discord_user_id)
        except (ValueError, TypeError):
            pass

    context = {
        'player': player,
        'player_gear': player_gear,
        'gear_by_type': gear_by_type,
        'drifters_data': drifters_data,
        'image_base_url': image_base_url,
        'can_modify': can_modify,
        'is_owner': is_owner,
        'discord_user_id': discord_user_id,
    }
    
    return render(request, 'guilds/player_loadout.html', context)


@require_POST
def assign_drifter(request, player_id):
    """AJAX view to assign a drifter to a player slot"""
    try:
        player = get_object_or_404(Player, id=player_id)
        drifter_slot = request.POST.get('drifter_slot')
        drifter_name = request.POST.get('drifter_name')
        
        if not drifter_slot or not drifter_name:
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        # Find the drifter by name
        try:
            drifter = Drifter.objects.get(name=drifter_name)
        except Drifter.DoesNotExist:
            return JsonResponse({'success': False, 'error': f'Drifter "{drifter_name}" not found'})
        
        # Assign drifter to the appropriate slot
        slot_number = int(drifter_slot)
        if slot_number == 1:
            player.drifter_1 = drifter
        elif slot_number == 2:
            player.drifter_2 = drifter
        elif slot_number == 3:
            player.drifter_3 = drifter
        else:
            return JsonResponse({'success': False, 'error': 'Invalid slot number'})
        
        player.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Drifter {drifter_name} assigned to slot {slot_number}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
@csrf_exempt
def update_loadout(request, player_id):
    """AJAX view to update player's loadout"""
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        player = get_object_or_404(Player, id=player_id)
        
        if action == 'equip':
            # Equip an item to a specific drifter
            gear_item_id = data.get('gear_item_id')  # Changed from gear_id to gear_item_id
            drifter_num = data.get('drifter_num')
            slot_type = data.get('slot_type')
            
            gear_item = get_object_or_404(GearItem, id=gear_item_id)
            
            # Get or create PlayerGear instance
            player_gear, created = PlayerGear.objects.get_or_create(
                player=player,
                gear_item=gear_item,
                defaults={
                    'is_equipped': False,
                    'equipped_on_drifter': None,
                    'is_favorite': False,
                    'mod_slots_used': 0,
                    'mod_slots_max': 0,
                }
            )
            
            # Unequip any other gear of the same type from the same drifter
            PlayerGear.objects.filter(
                player=player,
                equipped_on_drifter=drifter_num,
                gear_item__gear_type__category=slot_type,
                is_equipped=True
            ).update(is_equipped=False, equipped_on_drifter=None)
            
            # Equip the new gear
            player_gear.is_equipped = True
            player_gear.equipped_on_drifter = drifter_num
            player_gear.save()
            
            action_msg = f'Equipped {gear_item.name} to Drifter {drifter_num}'
            if created:
                action_msg += ' (added to inventory)'
            
            return JsonResponse({
                'success': True,
                'message': action_msg
            })
            
        elif action == 'unequip':
            # Unequip an item
            gear_id = data.get('gear_id')
            
            player_gear = get_object_or_404(PlayerGear, id=gear_id, player=player)
            player_gear.is_equipped = False
            player_gear.equipped_on_drifter = None
            player_gear.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Unequipped {player_gear.gear_item.name}'
            })
            
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def drifter_details(request, drifter_id):
    """View to display drifter details similar to warborne.pages.dev"""
    drifter = get_object_or_404(Drifter, id=drifter_id)
    
    context = {
        'drifter': drifter,
    }
    
    return render(request, 'guilds/drifter_details.html', context)


@require_POST
def update_game_role(request, player_id):
    """AJAX view to update player's game role"""
    try:
        player = get_object_or_404(Player, id=player_id)
        data = json.loads(request.body)
        game_role = data.get('game_role')
        
        # Validate game role
        valid_roles = [choice[0] for choice in Player.GAME_ROLE_CHOICES]
        if game_role and game_role not in valid_roles:
            return JsonResponse({'success': False, 'error': 'Invalid game role'})
        
        # Update player's game role
        player.game_role = game_role if game_role else None
        player.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Game role updated to {player.get_game_role_display() if player.game_role else "None"}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def check_player_permissions(request, player_id):
    """Check if a Discord user can modify a specific player"""
    discord_user_id = request.GET.get('discord_user_id')
    
    if not discord_user_id:
        return JsonResponse({'error': 'Discord user ID required'}, status=400)
    
    try:
        discord_user_id = int(discord_user_id)
    except ValueError:
        return JsonResponse({'error': 'Invalid Discord user ID'}, status=400)
    
    try:
        player = get_object_or_404(Player, id=player_id)
        is_owner = player.is_owner(discord_user_id)
        is_staff = request.user.is_staff if hasattr(request, 'user') and request.user.is_authenticated else False
        can_modify = player.can_modify(discord_user_id, is_staff)
        
        return JsonResponse({
            'success': True,
            'player_name': player.in_game_name,
            'is_owner': is_owner,
            'is_staff': is_staff,
            'can_modify': can_modify,
            'discord_user_id': discord_user_id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def update_player_name(request, player_id):
    """AJAX view to update player's name"""
    try:
        player = get_object_or_404(Player, id=player_id)
        data = json.loads(request.body)
        new_name = data.get('name', '').strip()
        
        # Validate new name
        if not new_name:
            return JsonResponse({'success': False, 'error': 'Name cannot be empty'})
        
        if len(new_name) < 3 or len(new_name) > 50:
            return JsonResponse({'success': False, 'error': 'Name must be between 3 and 50 characters'})
        
        # Check if name already exists (excluding current player)
        if Player.objects.filter(in_game_name__iexact=new_name).exclude(id=player_id).exists():
            return JsonResponse({'success': False, 'error': 'A player with this name already exists'})
        
        # Update player name
        old_name = player.in_game_name
        player.in_game_name = new_name
        player.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Player name updated from "{old_name}" to "{new_name}"',
            'new_name': new_name
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Discord Bot Management Views
@staff_member_required
def bot_management(request):
    """View for Discord bot management dashboard"""
    bot_config = DiscordBotConfig.objects.first()
    return render(request, 'guilds/bot_management.html', {'bot_config': bot_config})


@staff_member_required
@require_POST
def start_bot(request):
    """Start the Discord bot"""
    try:
        bot_config = DiscordBotConfig.objects.first()
        if not bot_config:
            return JsonResponse({'success': False, 'message': 'No bot configuration found'})
        
        success, message = bot_config.start_bot_manually()
        return JsonResponse({'success': success, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@staff_member_required
@require_POST
def stop_bot(request):
    """Stop the Discord bot"""
    try:
        bot_config = DiscordBotConfig.objects.first()
        if not bot_config:
            return JsonResponse({'success': False, 'message': 'No bot configuration found'})
        
        success, message = bot_config.stop_bot_manually()
        return JsonResponse({'success': success, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@staff_member_required
@require_POST
def restart_bot(request):
    """Restart the Discord bot"""
    try:
        bot_config = DiscordBotConfig.objects.first()
        if not bot_config:
            return JsonResponse({'success': False, 'message': 'No bot configuration found'})
        
        success, message = bot_config.restart_bot_manually()
        return JsonResponse({'success': success, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@staff_member_required
def bot_status(request):
    """Get Discord bot status"""
    try:
        bot_config = DiscordBotConfig.objects.first()
        if not bot_config:
            return JsonResponse({'success': False, 'message': 'No bot configuration found'})
        
        return JsonResponse({
            'success': True,
            'is_online': bot_config.is_online,
            'is_active': bot_config.is_active,
            'last_heartbeat': bot_config.last_heartbeat.isoformat() if bot_config.last_heartbeat else None,
            'error_message': bot_config.error_message,
            'status': bot_config.get_status_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def recommended_builds(request):
    """View for displaying recommended builds organized by role"""
    from .models import RecommendedBuild, Player
    
    try:
        # Get all active recommended builds with optimized queries
        # Note: template_player field was removed - using new equipment fields
        builds = RecommendedBuild.objects.filter(is_active=True).select_related(
            'drifter', 'weapon', 'helmet', 'chest', 'boots', 'consumable',
            'mod1', 'mod2', 'mod3', 'mod4'
        )
        
        # Group builds by role
        builds_by_role = {}
        for build in builds:
            role = build.role
            if role not in builds_by_role:
                builds_by_role[role] = []
            builds_by_role[role].append(build)
        
        # Get role choices for tab generation
        role_choices = Player.GAME_ROLE_CHOICES
        
        context = {
            'builds_by_role': builds_by_role,
            'role_choices': role_choices,
            'total_builds': len(builds),
        }
        
        return render(request, 'guilds/recommended_builds.html', context)
        
    except Exception as e:
        # Fallback for any database issues
        print(f"Error in recommended_builds view: {e}")
        
        # Return empty context with error handling
        context = {
            'builds_by_role': {},
            'role_choices': Player.GAME_ROLE_CHOICES,
            'total_builds': 0,
            'error_message': 'Error loading recommended builds. Please try again later.'
        }
        
        return render(request, 'guilds/recommended_builds.html', context)


def edit_recommended_build(request, build_id=None):
    """View for editing recommended builds"""
    from .models import RecommendedBuild, Drifter, GearItem, GearMod, Player
    
    build = None
    if build_id and build_id != 'new':
        try:
            build = RecommendedBuild.objects.select_related(
                'drifter', 'weapon', 'helmet', 'chest', 'boots', 'consumable',
                'mod1', 'mod2', 'mod3', 'mod4'
            ).get(id=build_id)
        except RecommendedBuild.DoesNotExist:
            return render(request, 'guilds/error.html', {'error': 'Build not found'})
    
    # Get role choices without database queries
    role_choices = Player.GAME_ROLE_CHOICES
    
    context = {
        'build': build,
        'role_choices': role_choices,
    }
    
    return render(request, 'guilds/recommended_build_edit.html', context)


@require_POST
def save_recommended_build(request, build_id=None):
    """View for saving recommended builds"""
    from .models import RecommendedBuild, Drifter, GearItem, GearMod
    import json
    
    try:
        data = json.loads(request.body)
        
        if build_id and build_id != 'new':
            build = RecommendedBuild.objects.get(id=build_id)
        else:
            build = RecommendedBuild()
        
        # Update build data
        build.title = data.get('title', '')
        build.description = data.get('description', '')
        build.role = data.get('role', '')
        build.is_active = data.get('is_active', False)
        
        # Update equipment
        if data.get('drifter'):
            build.drifter = Drifter.objects.get(id=data['drifter'])
        else:
            build.drifter = None
            
        if data.get('weapon'):
            build.weapon = GearItem.objects.get(id=data['weapon'])
        else:
            build.weapon = None
            
        if data.get('helmet'):
            build.helmet = GearItem.objects.get(id=data['helmet'])
        else:
            build.helmet = None
            
        if data.get('chest'):
            build.chest = GearItem.objects.get(id=data['chest'])
        else:
            build.chest = None
            
        if data.get('boots'):
            build.boots = GearItem.objects.get(id=data['boots'])
        else:
            build.boots = None
            
        if data.get('consumable'):
            build.consumable = GearItem.objects.get(id=data['consumable'])
        else:
            build.consumable = None
            
        if data.get('mod1'):
            build.mod1 = GearMod.objects.get(id=data['mod1'])
        else:
            build.mod1 = None
            
        if data.get('mod2'):
            build.mod2 = GearMod.objects.get(id=data['mod2'])
        else:
            build.mod2 = None
            
        if data.get('mod3'):
            build.mod3 = GearMod.objects.get(id=data['mod3'])
        else:
            build.mod3 = None
            
        if data.get('mod4'):
            build.mod4 = GearMod.objects.get(id=data['mod4'])
        else:
            build.mod4 = None
        
        if not build.id:  # New build
            build.created_by = request.user.username if request.user.is_authenticated else "Admin"
        
        build.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Build saved successfully',
            'redirect_url': f'/guilds/recommended-build/{build.id}/edit/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


def get_items_for_slot(request, slot_type):
    """API endpoint to get items for a specific slot"""
    from .models import Drifter, GearItem, GearMod
    
    try:
        items = []
        
        if slot_type == 'drifter':
            drifters = Drifter.objects.all().order_by('name')
            items = [{'id': d.id, 'name': d.name, 'level': d.level or 1, 'type': 'drifter'} for d in drifters]
        elif slot_type in ['weapon', 'helmet', 'chest', 'boots', 'consumable']:
            gear_items = GearItem.objects.filter(gear_type__name__iexact=slot_type).order_by('name')
            items = [{
                'id': g.id, 
                'name': g.name, 
                'rarity': g.rarity, 
                'type': slot_type,
                'damage': g.damage,
                'armor': g.armor,
                'speed': g.speed
            } for g in gear_items]
        elif slot_type == 'mod':
            gear_mods = GearMod.objects.all().order_by('name')
            items = [{'id': g.id, 'name': g.name, 'rarity': g.rarity, 'type': 'mod'} for g in gear_mods]
        
        return JsonResponse({'success': True, 'items': items})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})