from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
import shutil
from guilds.models import GearType, GearItem, GearMod


class Command(BaseCommand):
    help = 'Import complete game data including armors, weapons, consumables, and mods'

    def handle(self, *args, **options):
        repos_path = os.path.join(settings.BASE_DIR, 'repos', 'warborne-data-json')
        
        if not os.path.exists(repos_path):
            self.stdout.write(self.style.ERROR(f'Repository path not found: {repos_path}'))
            return
        
        # Copy icons first
        self.copy_icons(repos_path)
        
        # Import all data
        self.import_armors(repos_path)
        self.import_weapons(repos_path)
        self.import_consumables(repos_path)
        self.import_mods_as_gear_items(repos_path)
        
        self.stdout.write(self.style.SUCCESS('Complete data import finished!'))
    
    def get_weapon_name_from_game_id(self, game_id):
        """Extract weapon name from game_id"""
        # Examples:
        # "HolyStaff_Passive" -> "Holy Staff"
        # "SwordAttack_1" -> "Sword"
        # "Bow_Common_Skill_1" -> "Bow"
        
        if '_Passive' in game_id:
            # "HolyStaff_Passive" -> "Holy Staff"
            weapon_part = game_id.replace('_Passive', '')
        elif 'Attack_' in game_id:
            # "SwordAttack_1" -> "Sword"
            weapon_part = game_id.split('Attack_')[0]
        elif 'Common_Skill_' in game_id:
            # "Bow_Common_Skill_1" -> "Bow"
            weapon_part = game_id.split('_Common_Skill_')[0]
        else:
            # For other cases, try to extract the weapon type
            weapon_part = game_id.split('_')[0]
        
        # Convert camelCase to readable format
        # "HolyStaff" -> "Holy Staff"
        # "Sword" -> "Sword"
        import re
        # Insert space before capital letters that follow lowercase letters
        readable_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', weapon_part)
        
        return readable_name

    def get_weapon_specific_icon(self, game_id, weapon_category):
        """Get specific weapon icon based on game_id pattern"""
        weapon_category = weapon_category.upper()
        
        # Map weapon categories to their image prefixes
        weapon_prefixes = {
            'SWORD': 'SWORD',
            'AXE': 'AXE', 
            'MACE': 'MACE',
            'GUN': 'GUN',
            'BOW': 'BOW',
            'DAGGER': 'DAGGER',
            'NATURE': 'NATURE',
            'SPEAR': 'SPEAR',
            'CURSE': 'CURSE',
            'FIRE': 'FIRE',
            'FROST': 'FROST',
            'HOLY': 'STAFF'  # Holy weapons use STAFF images
        }
        
        prefix = weapon_prefixes.get(weapon_category, weapon_category)
        
        # Extract number from game_id for specific weapon image
        if 'Attack_' in game_id:
            # For basic attacks: SwordAttack_1 -> SpecImage_SWORD1
            number = game_id.split('_')[-1]
            return f'SpecImage_{prefix}{number}.png'
        elif 'Common_Skill_' in game_id:
            # For common skills: Sword_Common_Skill_1 -> SpecImage_SWORD1
            number = game_id.split('_')[-1]
            return f'SpecImage_{prefix}{number}.png'
        elif 'Passive' in game_id:
            # For passive skills, use first image
            return f'SpecImage_{prefix}1.png'
        else:
            # For specific skills, try to extract number or use first image
            # This is a fallback - we might need to refine this
            return f'SpecImage_{prefix}1.png'

    def copy_icons(self, repos_path):
        """Copy all icons to local static folder"""
        self.stdout.write('Copying icons...')
        
        icons_source = os.path.join(repos_path, 'icons')
        icons_dest = os.path.join(settings.BASE_DIR, 'static', 'icons')
        
        if not os.path.exists(icons_source):
            self.stdout.write(self.style.WARNING(f'Icons source not found: {icons_source}'))
            return
        
        os.makedirs(icons_dest, exist_ok=True)
        
        copied_count = 0
        for filename in os.listdir(icons_source):
            if filename.lower().endswith('.png'):
                source_path = os.path.join(icons_source, filename)
                dest_path = os.path.join(icons_dest, filename)
                try:
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
                except Exception as e:
                    self.stdout.write(f'Warning: Could not copy {filename}: {e}')
        self.stdout.write(f'Copied {copied_count} icon files to static/icons/')

    def import_armors(self, repos_path):
        """Import all armor data (helmets, chests, boots) by attribute type"""
        self.stdout.write('Importing armors...')
        
        # Define armor types and their corresponding files
        armor_types = [
            ('helmet', 'Head', [
                ('str_head.json', 'Strength'),
                ('dex_head.json', 'Agility'), 
                ('int_head.json', 'Intelligence')
            ]),
            ('chest', 'Chest', [
                ('str_chest.json', 'Strength'),
                ('dex_chest.json', 'Agility'),
                ('int_chest.json', 'Intelligence')
            ]),
            ('boots', 'Boots', [
                ('str_boots.json', 'Strength'),
                ('dex_boots.json', 'Agility'),
                ('int_boots.json', 'Intelligence')
            ])
        ]
        
        imported_count = 0
        
        for armor_category, gear_type_name, files in armor_types:
            # Create gear type for this armor category
            gear_type, _ = GearType.objects.get_or_create(
                name=gear_type_name,
                defaults={
                    'category': armor_category,
                    'description': f'{gear_type_name} armor pieces'
                }
            )
            
            for filename, attribute in files:
                file_path = os.path.join(repos_path, 'armors', filename)
                
                if not os.path.exists(file_path):
                    self.stdout.write(f'Warning: {file_path} not found')
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Get the armor list (key varies by file)
                armor_key = list(data.keys())[1] if len(data.keys()) > 1 else None
                if not armor_key:
                    continue
                
                armors = data[armor_key]
                if not isinstance(armors, list):
                    continue
                
                for armor in armors:
                    if not isinstance(armor, dict):
                        continue
                    
                    armor_name = armor.get('gearName', '')
                    skill_name = armor.get('skillName', '')
                    game_id = armor.get('gameId', '')
                    gear_icon = armor.get('gearIcon', '')
                    
                    if not armor_name or not game_id:
                        continue
                    
                    # Separate base name and skill name
                    base_name = armor_name
                    skill_name = skill_name
                    
                    # Map rarity
                    rarity_map = {
                        'common': 'common',
                        'rare': 'rare', 
                        'epic': 'epic',
                        'legendary': 'legendary'
                    }
                    rarity = rarity_map.get(armor.get('rarity', 'common'), 'common')
                    
                    # Extract stats
                    stats = armor.get('stats', {})
                    health_bonus = 0
                    damage = 0
                    mana_recovery = 0
                    armor_value = 0
                    magic_resistance = 0
                    
                    if stats.get('hp'):
                        try:
                            health_bonus = int(stats['hp'])
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract damage bonus (convert percentage to float for storage)
                    if stats.get('dmgBonus'):
                        try:
                            dmg_bonus_str = stats['dmgBonus'].replace('%', '')
                            damage = float(dmg_bonus_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract mana recovery
                    if stats.get('mpRecovery'):
                        try:
                            mana_recovery = int(stats['mpRecovery'])
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract armor value
                    if stats.get('armor'):
                        try:
                            armor_value = int(stats['armor'])
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract magic resistance
                    if stats.get('magicResi'):
                        try:
                            magic_resistance = int(stats['magicResi'])
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract detailed stats
                    detailed_stats = {}
                    if stats:
                        detailed_stats = dict(stats)
                    
                    # Create armor item
                    armor_item, created = GearItem.objects.get_or_create(
                        base_name=base_name,
                        skill_name=skill_name,
                        gear_type=gear_type,
                        defaults={
                            'rarity': rarity,
                            'required_level': 1,
                            'damage': damage,
                            'defense': 0,
                            'health_bonus': health_bonus,
                            'energy_bonus': 0,
                            'mana_recovery': mana_recovery,
                            'armor': armor_value,
                            'magic_resistance': magic_resistance,
                            'description': armor.get('description', ''),
                            'mana_cost': None,
                            'cooldown': armor.get('cooldown', ''),
                            'casting_range': armor.get('castingRange', ''),
                            'skill_type': armor.get('type', ''),
                            'tier_unlock': armor.get('tierUnlock', ''),
                            'detailed_stats': detailed_stats,
                            'is_craftable': True,
                            'is_tradeable': True,
                            'game_id': game_id,
                            'icon_url': f'/static/icons/{gear_icon}.png' if gear_icon else f'/static/icons/{game_id}.png'
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created {armor_category} ({attribute}): {base_name} ({skill_name})')
        
        self.stdout.write(f'Imported {imported_count} armor items')

    def import_weapons(self, repos_path):
        """Import all weapon data by attribute type"""
        self.stdout.write('Importing weapons...')
        
        # Define weapon types and their corresponding files
        weapon_types = [
            ('sword', 'Sword', 'str_sword.json', 'Strength'),
            ('axe', 'Axe', 'str_axe.json', 'Strength'),
            ('mace', 'Mace', 'str_mace.json', 'Strength'),
            ('gun', 'Gun', 'str_gun.json', 'Strength'),
            ('bow', 'Bow', 'dex_bow.json', 'Agility'),
            ('dagger', 'Dagger', 'dex_dagger.json', 'Agility'),
            ('nature', 'Nature', 'dex_nature.json', 'Agility'),
            ('spear', 'Spear', 'dex_spear.json', 'Agility'),
            ('curse', 'Curse', 'int_curse.json', 'Intelligence'),
            ('fire', 'Fire', 'int_fire.json', 'Intelligence'),
            ('frost', 'Frost', 'int_frost.json', 'Intelligence'),
            ('holy', 'Holy', 'int_holy.json', 'Intelligence'),
        ]
        
        imported_count = 0
        
        for weapon_category, weapon_name, filename, attribute in weapon_types:
            # Create gear type for this weapon
            gear_type, _ = GearType.objects.get_or_create(
                name=f'{weapon_name} ({attribute})',
                defaults={
                    'category': 'weapon',
                    'description': f'{weapon_name} weapons for {attribute} builds'
                }
            )
            
            file_path = os.path.join(repos_path, 'weapons', filename)
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Import weapons from different sections
            weapon_sections = ['passive', 'basicAttacks', 'commonSkills', 'skills']
            
            for section in weapon_sections:
                if section not in data:
                    continue
                    
                weapons_data = data[section]
                
                # Handle different data structures
                if section == 'passive':
                    # Passive is a single object, not an array
                    if isinstance(weapons_data, dict):
                        weapons_data = [weapons_data]
                elif not isinstance(weapons_data, list):
                    continue
                
                for weapon in weapons_data:
                    if not isinstance(weapon, dict):
                        continue
                    
                    skill_name = weapon.get('skillName', weapon.get('weaponName', ''))
                    weapon_name = weapon.get('gearName', '')
                    game_id = weapon.get('gameId', '')
                    
                    if not skill_name or not weapon_name or not game_id:
                        continue
                    
                    # Use rarity directly from JSON, fallback to tierUnlock mapping
                    rarity = weapon.get('rarity', '')
                    if not rarity:
                        # Fallback: Map rarity based on tierUnlock
                        tier_unlock = weapon.get('tierUnlock', '1')
                        try:
                            tier = int(tier_unlock)
                            if tier <= 2:
                                rarity = 'common'
                            elif tier <= 4:
                                rarity = 'rare'
                            elif tier <= 6:
                                rarity = 'epic'
                            else:
                                rarity = 'legendary'
                        except (ValueError, TypeError):
                            rarity = 'common'
                    
                    # Extract mana cost
                    mana_cost = None
                    mana_cost_str = weapon.get('manaCost', '')
                    if mana_cost_str and mana_cost_str.isdigit():
                        mana_cost = int(mana_cost_str)
                    
                    # Extract detailed stats
                    stats = weapon.get('stats', {})
                    detailed_stats = {}
                    if stats:
                        detailed_stats = dict(stats)
                    
                    # Use gearIcon from JSON if available, otherwise determine from game_id pattern
                    gear_icon = weapon.get('gearIcon', '')
                    if gear_icon:
                        weapon_icon = f'{gear_icon}.png'
                    else:
                        weapon_icon = self.get_weapon_specific_icon(game_id, weapon_category)
                    
                    # Create weapon item
                    weapon_item, created = GearItem.objects.get_or_create(
                        base_name=weapon_name,
                        skill_name=skill_name,
                        defaults={
                            'gear_type': gear_type,
                            'rarity': rarity,
                            'required_level': 1,
                            'damage': 0,
                            'defense': 0,
                            'health_bonus': 0,
                            'energy_bonus': 0,
                            'description': weapon.get('description', ''),
                            'mana_cost': mana_cost,
                            'cooldown': weapon.get('cooldown', ''),
                            'casting_range': weapon.get('castingRange', ''),
                            'skill_type': weapon.get('type', ''),
                            'tier_unlock': weapon.get('tierUnlock', ''),
                            'detailed_stats': detailed_stats,
                            'is_craftable': True,
                            'is_tradeable': True,
                            'game_id': game_id,
                            'icon_url': f'/static/icons/{weapon_icon}'
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created weapon ({attribute}): {weapon_name} ({skill_name})')
        
        self.stdout.write(f'Imported {imported_count} weapon items')

    def import_consumables(self, repos_path):
        """Import all consumable data"""
        self.stdout.write('Importing consumables...')
        
        # Create consumable gear type
        consumable_type, _ = GearType.objects.get_or_create(
            name='Consumable',
            defaults={
                'category': 'consumable',
                'description': 'Consumable items'
            }
        )
        
        consumable_files = ['food.json', 'poison.json', 'potions.json', 'utility.json']
        imported_count = 0
        
        for filename in consumable_files:
            file_path = os.path.join(repos_path, 'consumable', filename)
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get the consumable list (key varies by file)
            consumable_key = list(data.keys())[1] if len(data.keys()) > 1 else None
            if not consumable_key:
                continue
            
            consumables = data[consumable_key]
            if not isinstance(consumables, list):
                continue
            
            for consumable in consumables:
                if not isinstance(consumable, dict):
                    continue
                
                item_name = consumable.get('consumableName', consumable.get('name', ''))
                game_id = consumable.get('gameId', '')
                
                if not item_name or not game_id:
                    continue
                
                # Map rarity
                rarity_map = {
                    'common': 'common',
                    'rare': 'rare',
                    'epic': 'epic',
                    'legendary': 'legendary'
                }
                rarity = rarity_map.get(consumable.get('rarity', 'common'), 'common')
                
                # Create consumable item
                consumable_item, created = GearItem.objects.get_or_create(
                    name=item_name,
                    defaults={
                        'gear_type': consumable_type,
                        'rarity': rarity,
                        'required_level': 1,
                        'damage': 0,
                        'defense': 0,
                        'health_bonus': 0,
                        'energy_bonus': 0,
                        'description': consumable.get('description', ''),
                        'mana_cost': None,
                        'cooldown': consumable.get('cooldown', ''),
                        'casting_range': consumable.get('castingRange', ''),
                        'skill_type': consumable.get('type', ''),
                        'tier_unlock': consumable.get('tierUnlock', ''),
                        'detailed_stats': consumable.get('stats', {}),
                        'is_craftable': True,
                        'is_tradeable': True,
                        'game_id': game_id,
                        'icon_url': f'/static/icons/{game_id}.png'
                    }
                )
                
                if created:
                    imported_count += 1
                    self.stdout.write(f'  Created consumable: {item_name}')
        
        self.stdout.write(f'Imported {imported_count} consumables')

    def import_mods_as_gear_items(self, repos_path):
        """Import mods as GearItems so they appear in tabs"""
        self.stdout.write('Importing mods as gear items...')
        
        # Create mod gear type
        mod_type, _ = GearType.objects.get_or_create(
            name='Mod',
            defaults={
                'category': 'mod',
                'description': 'Equipment modifications'
            }
        )
        
        mod_files = ['mod_armor.json', 'mod_weapon.json']
        imported_count = 0
        
        for mod_file in mod_files:
            file_path = os.path.join(repos_path, 'mods', mod_file)
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process mods from the correct structure
            if 'mods' in data and isinstance(data['mods'], list):
                for mod in data['mods']:
                    if not isinstance(mod, dict):
                        continue
                    
                    mod_name = mod.get('name', '')
                    icon_name = mod.get('iconName', '')
                    slot = mod.get('slot', '')
                    
                    if not mod_name:
                        continue
                    
                    # Map rarity
                    rarity_map = {
                        'common': 'common',
                        'rare': 'rare',
                        'epic': 'epic',
                        'legendary': 'legendary'
                    }
                    rarity = rarity_map.get(mod.get('rarity', 'rare'), 'rare')
                    
                    # Create mod as GearItem
                    mod_item, created = GearItem.objects.get_or_create(
                        base_name=mod_name,
                        skill_name='',  # Mods don't have separate skills
                        gear_type=mod_type,
                        defaults={
                            'rarity': rarity,
                            'required_level': 1,
                            'damage': 0,
                            'defense': 0,
                            'health_bonus': 0,
                            'energy_bonus': 0,
                            'description': mod.get('description', ''),
                            'mana_cost': None,
                            'cooldown': '',
                            'casting_range': '',
                            'skill_type': 'mod',
                            'tier_unlock': '',
                            'detailed_stats': {},
                            'is_craftable': True,
                            'is_tradeable': True,
                            'game_id': icon_name,
                            'icon_url': f'/static/icons/{icon_name}.png'
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created mod: {mod_name} ({slot})')
        
        self.stdout.write(f'Imported {imported_count} mod items')
