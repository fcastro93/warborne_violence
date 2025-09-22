from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from functools import wraps
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Player, PlayerGear, GearItem, GearMod, Drifter, DiscordBotConfig, Guild, Event, RecommendedBuild, Party, PartyMember
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
    """View for editing recommended builds - Staff only"""
    from django.contrib.admin.views.decorators import staff_member_required
    from .models import RecommendedBuild, Drifter, GearItem, GearMod, Player
    from django.db.models import Case, When, IntegerField
    
    # Check if user is staff
    if not request.user.is_authenticated or not request.user.is_staff:
        # Redirect non-staff users to view-only page
        if build_id and build_id != 'new':
            return redirect(f'/guilds/recommended-build/{build_id}/view/')
        else:
            return redirect('/guilds/recommended-builds/')
    
    build = None
    if build_id and build_id != 'new':
        try:
            build = RecommendedBuild.objects.select_related(
                'drifter', 'weapon', 'helmet', 'chest', 'boots', 'consumable',
                'mod1', 'mod2', 'mod3', 'mod4'
            ).get(id=build_id)
        except RecommendedBuild.DoesNotExist:
            return render(request, 'guilds/error.html', {'error': 'Build not found'})
    
    # Base URL for item images from local static files
    image_base_url = "/static/icons/"
    
    # Get all available gear items in the game, organized by type and rarity (same as player loadout)
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
    
    # Organize gear by type and attribute for better display (same as player loadout)
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
        
        # For build editor, all items are available (no ownership concept)
        item_data = {
            'gear_item': gear_item,
            'is_owned': True,  # All items available for builds
            'player_gear': None,  # No player gear concept for builds
            'is_equipped': False,  # Will be determined by build equipment
            'equipped_on_drifter': None,
        }
        
        # Determine attribute based on gear type name (same logic as player loadout)
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
    
    # Add drifters to gear_by_type (same as player loadout)
    drifters = Drifter.objects.all().order_by('name')
    gear_by_type['drifter'] = {'All': [{'gear_item': drifter, 'is_owned': True, 'player_gear': None, 'is_equipped': False, 'equipped_on_drifter': None} for drifter in drifters]}
    
    # Get role choices without database queries
    role_choices = Player.GAME_ROLE_CHOICES
    
    context = {
        'build': build,
        'role_choices': role_choices,
        'gear_by_type': gear_by_type,
        'image_base_url': image_base_url,
        'user': request.user,  # Pass user for staff checks
    }
    
    return render(request, 'guilds/recommended_build_edit.html', context)


def view_recommended_build(request, build_id):
    """View for viewing recommended builds - Read only for all users"""
    from .models import RecommendedBuild, Drifter, GearItem, GearMod, Player
    
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
        'read_only': True,  # Flag to indicate this is read-only mode
    }
    
    return render(request, 'guilds/recommended_build_view.html', context)


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


def update_recommended_build_equipment(request, build_id):
    """AJAX endpoint to update recommended build equipment (similar to player loadout update)"""
    from .models import RecommendedBuild
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        # Check if user is staff
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Staff privileges required'})
        
        build = RecommendedBuild.objects.get(id=build_id)
        
        # Parse JSON data
        import json
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'equip':
            gear_item_id = data.get('gear_item_id')
            slot_type = data.get('slot_type')
            
            if not gear_item_id or not slot_type:
                return JsonResponse({'success': False, 'error': 'Missing required parameters'})
            
            # Update the appropriate slot
            if slot_type == 'weapon':
                build.weapon_id = gear_item_id
            elif slot_type == 'helmet':
                build.helmet_id = gear_item_id
            elif slot_type == 'chest':
                build.chest_id = gear_item_id
            elif slot_type == 'boots':
                build.boots_id = gear_item_id
            elif slot_type == 'consumable':
                build.consumable_id = gear_item_id
            elif slot_type == 'mod1':
                build.mod1_id = gear_item_id
            elif slot_type == 'mod2':
                build.mod2_id = gear_item_id
            elif slot_type == 'mod3':
                build.mod3_id = gear_item_id
            elif slot_type == 'mod4':
                build.mod4_id = gear_item_id
            elif slot_type == 'drifter':
                build.drifter_id = gear_item_id
            
            build.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Item equipped to {slot_type}',
                'equipped_item': {
                    'id': gear_item_id,
                    'slot': slot_type
                }
            })
            
        elif action == 'unequip':
            slot_type = data.get('slot_type')
            
            if not slot_type:
                return JsonResponse({'success': False, 'error': 'Missing slot type'})
            
            # Unequip the appropriate slot
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
            elif slot_type == 'mod1':
                build.mod1 = None
            elif slot_type == 'mod2':
                build.mod2 = None
            elif slot_type == 'mod3':
                build.mod3 = None
            elif slot_type == 'mod4':
                build.mod4 = None
            elif slot_type == 'drifter':
                build.drifter = None
            
            build.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Item unequipped from {slot_type}',
                'unequipped_slot': slot_type
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
            
    except RecommendedBuild.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Build not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
def staff_dashboard(request):
    """Staff dashboard with overview statistics and management tools"""
    try:
        # Get basic statistics
        total_players = Player.objects.count()
        active_guilds = Guild.objects.filter(is_active=True).count()
        total_events = Event.objects.count()
        active_events = Event.objects.filter(
            event_datetime__gte=timezone.now()
        ).count()
        total_builds = RecommendedBuild.objects.filter(is_active=True).count()
        
        # Get recent activity
        recent_players = Player.objects.order_by('-created_at')[:5]
        recent_events = Event.objects.order_by('-created_at')[:5]
        
        # Get guild statistics
        guilds_with_members = Guild.objects.all()[:5]
        
        # Get role distribution
        role_distribution = Player.objects.values('game_role').annotate(
            count=Count('game_role')
        ).order_by('-count')
        
        # Get faction distribution
        faction_distribution = Player.objects.values('faction').annotate(
            count=Count('faction')
        ).order_by('-count')
        
        # Get bot status
        try:
            bot_config = DiscordBotConfig.objects.first()
            bot_status = "Active" if bot_config and bot_config.is_active else "Inactive"
        except:
            bot_status = "Unknown"
        
        # Get system health metrics
        players_with_loadouts = Player.objects.filter(
            gear_items__isnull=False
        ).distinct().count()
        
        completion_rate = (players_with_loadouts / total_players * 100) if total_players > 0 else 0
        
        # Get more detailed statistics
        players_with_discord = Player.objects.filter(
            discord_user_id__isnull=False
        ).exclude(discord_user_id=0).count()
        
        discord_integration_rate = (players_with_discord / total_players * 100) if total_players > 0 else 0
        
        # Get gear statistics
        total_gear_items = GearItem.objects.count()
        total_drifters = Drifter.objects.count()
        total_gear_mods = GearMod.objects.count()
        
        # Get party statistics
        total_parties = Party.objects.count()
        total_party_members = PartyMember.objects.count()
        
        # Get recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_players_week = Player.objects.filter(created_at__gte=week_ago).count()
        recent_events_week = Event.objects.filter(created_at__gte=week_ago).count()
        
        context = {
            # Basic statistics
            'total_players': total_players,
            'active_guilds': active_guilds,
            'total_events': total_events,
            'active_events': active_events,
            'total_builds': total_builds,
            
            # Recent activity
            'recent_players': recent_players,
            'recent_events': recent_events,
            'recent_players_week': recent_players_week,
            'recent_events_week': recent_events_week,
            
            # Guild and role statistics
            'guilds_with_members': guilds_with_members,
            'role_distribution': role_distribution,
            'faction_distribution': faction_distribution,
            
            # System health
            'bot_status': bot_status,
            'completion_rate': round(completion_rate, 1),
            'players_with_loadouts': players_with_loadouts,
            'discord_integration_rate': round(discord_integration_rate, 1),
            'players_with_discord': players_with_discord,
            
            # Gear and equipment statistics
            'total_gear_items': total_gear_items,
            'total_drifters': total_drifters,
            'total_gear_mods': total_gear_mods,
            
            # Party statistics
            'total_parties': total_parties,
            'total_party_members': total_party_members,
            
            # For sidebar
            'player_count': total_players,
            'guild_count': active_guilds,
            'event_count': active_events,
        }
        
        return render(request, 'guilds/staff_dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return render(request, 'guilds/staff_dashboard.html', {
            'total_players': 0,
            'active_guilds': 0,
            'total_events': 0,
            'active_events': 0,
            'total_builds': 0,
            'bot_status': 'Unknown',
            'error': str(e)
        })


@staff_member_required
def guild_analytics(request):
    """Guild analytics and statistics page"""
    try:
        # Get guild statistics
        guilds = Guild.objects.all()
        
        # Get role distribution by guild
        guild_role_stats = {}
        for guild in guilds:
            role_stats = Player.objects.filter(guild=guild).values('game_role').annotate(
                count=Count('game_role')
            )
            guild_role_stats[guild.id] = list(role_stats)
        
        # Get total members across all guilds
        total_members = Player.objects.filter(is_active=True).count()
        
        context = {
            'guilds': guilds,
            'guild_role_stats': guild_role_stats,
            'total_guilds': guilds.count(),
            'total_members': total_members,
        }
        
        return render(request, 'guilds/guild_analytics.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading guild analytics: {str(e)}')
        return render(request, 'guilds/guild_analytics.html', {
            'guilds': [],
            'total_guilds': 0,
            'total_members': 0,
            'error': str(e)
        })


@staff_member_required
def event_analytics(request):
    """Event analytics and statistics page"""
    try:
        # Get event statistics
        events = Event.objects.annotate(
            participant_count=Count('participants', filter=Q(
                participants__is_active=True
            ))
        ).order_by('-event_datetime')
        
        # Get upcoming events
        upcoming_events = events.filter(
            event_datetime__gte=timezone.now()
        )[:10]
        
        # Get past events
        past_events = events.filter(
            event_datetime__lt=timezone.now()
        )[:10]
        
        # Get participation trends
        participation_trends = Event.objects.filter(
            event_datetime__gte=timezone.now() - timedelta(days=30)
        ).annotate(
            participant_count=Count('participants', filter=Q(
                participants__is_active=True
            ))
        ).order_by('event_datetime')
        
        context = {
            'events': events,
            'upcoming_events': upcoming_events,
            'past_events': past_events,
            'participation_trends': participation_trends,
            'total_events': events.count(),
            'total_participants': sum(e.participant_count for e in events),
        }
        
        return render(request, 'guilds/event_analytics.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading event analytics: {str(e)}')
        return render(request, 'guilds/event_analytics.html', {
            'events': [],
            'total_events': 0,
            'total_participants': 0,
            'error': str(e)
        })


@staff_member_required
def bot_analytics(request):
    """Bot analytics and management page"""
    try:
        # Get bot configuration
        bot_config = DiscordBotConfig.objects.first()
        
        # Get bot-related statistics
        players_with_discord = Player.objects.filter(
            discord_user_id__isnull=False
        ).exclude(discord_user_id='').count()
        
        # Get recent bot activity (this would need to be implemented with logging)
        # For now, we'll use player creation as a proxy
        recent_discord_players = Player.objects.filter(
            discord_user_id__isnull=False
        ).exclude(discord_user_id='').order_by('-created_at')[:10]
        
        context = {
            'bot_config': bot_config,
            'players_with_discord': players_with_discord,
            'recent_discord_players': recent_discord_players,
            'total_players': Player.objects.count(),
            'discord_integration_rate': round(
                (players_with_discord / Player.objects.count() * 100) 
                if Player.objects.count() > 0 else 0, 1
            ),
        }
        
        return render(request, 'guilds/bot_analytics.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading bot analytics: {str(e)}')
        return render(request, 'guilds/bot_analytics.html', {
            'bot_config': None,
            'players_with_discord': 0,
            'total_players': 0,
            'discord_integration_rate': 0,
            'error': str(e)
        })