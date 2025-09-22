import os
import json
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from guilds.models import GearType, GearItem, Drifter, GearMod

class Command(BaseCommand):
    help = 'Import English-only game data from local repositories'

    def handle(self, *args, **options):
        self.stdout.write('Starting English-only data import...')
        
        # Base path to repositories
        repos_path = os.path.join(settings.BASE_DIR, 'repos', 'warborne-data-json')
        
        if not os.path.exists(repos_path):
            self.stdout.write(self.style.ERROR(f'Repository path not found: {repos_path}'))
            return
        
        # Import all data types
        self.import_armors(repos_path)
        self.import_weapons(repos_path)
        self.import_consumables(repos_path)
        self.import_mods(repos_path)
        self.import_drifters(repos_path)
        
        self.stdout.write(self.style.SUCCESS('✅ English-only data import completed successfully!'))

    def import_armors(self, repos_path):
        """Import all armor data (English only)"""
        self.stdout.write('Importing armors...')
        
        armor_types = [
            'str_head', 'str_chest', 'str_boots',
            'dex_head', 'dex_chest', 'dex_boots', 
            'int_head', 'int_chest', 'int_boots'
        ]
        
        imported_count = 0
        
        for armor_type in armor_types:
            file_path = os.path.join(repos_path, 'armors', f'{armor_type}.json')
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract armor data
            armor_key = armor_type.replace('_', '_')
            if armor_key in data:
                armors = data[armor_key]
                
                # Create gear type based on armor type
                if 'head' in armor_type:
                    gear_type_name = 'Helmet'
                elif 'chest' in armor_type:
                    gear_type_name = 'Chest'
                elif 'boots' in armor_type:
                    gear_type_name = 'Boots'
                else:
                    continue
                
                gear_type, _ = GearType.objects.get_or_create(
                    name=gear_type_name,
                    defaults={
                        'category': 'armor',
                        'description': f'{gear_type_name} armor pieces'
                    }
                )
                
                for armor in armors:
                    if not isinstance(armor, dict):
                        continue
                    
                    game_id = armor.get('gameId', '')
                    gear_name = armor.get('gearName', '')
                    
                    if not game_id or not gear_name:
                        continue
                    
                    # Map rarity
                    rarity_map = {
                        'common': 'common',
                        'uncommon': 'uncommon',
                        'rare': 'rare',
                        'epic': 'epic',
                        'legendary': 'legendary'
                    }
                    rarity = rarity_map.get(armor.get('rarity', 'common'), 'common')
                    
                    # Extract stats
                    stats = armor.get('stats', {})
                    health_bonus = int(stats.get('hp', 0)) if stats.get('hp', '').isdigit() else 0
                    
                    # Create armor item
                    armor_item, created = GearItem.objects.get_or_create(
                        name=gear_name,
                        defaults={
                            'gear_type': gear_type,
                            'rarity': rarity,
                            'required_level': 1,
                            'damage': 0,
                            'defense': 0,
                            'health_bonus': health_bonus,
                            'energy_bonus': 0,
                            'description': armor.get('description', ''),
                            'is_craftable': True,
                            'is_tradeable': True,
                            'game_id': game_id,
                            'icon_url': f'/static/icons/{game_id}.png'
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created armor: {gear_name}')
        
        self.stdout.write(f'Imported {imported_count} armors')

    def import_weapons(self, repos_path):
        """Import all weapon data (English only)"""
        self.stdout.write('Importing weapons...')
        
        weapon_types = [
            'str_axe', 'str_gun', 'str_mace', 'str_sword',
            'dex_bow', 'dex_dagger', 'dex_nature', 'dex_spear',
            'int_curse', 'int_fire', 'int_frost', 'int_holy'
        ]
        
        # Create weapon gear type
        weapon_gear_type, _ = GearType.objects.get_or_create(
            name='Weapon',
            defaults={
                'category': 'weapon',
                'description': 'Weapons'
            }
        )
        
        imported_count = 0
        
        for weapon_type in weapon_types:
            file_path = os.path.join(repos_path, 'weapons', f'{weapon_type}.json')
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Import different weapon categories
            weapon_categories = ['basicAttacks', 'spells', 'ultimates', 'passive']
            
            for category in weapon_categories:
                if category in data and isinstance(data[category], list):
                    weapons = data[category]
                    
                    for weapon in weapons:
                        if not isinstance(weapon, dict):
                            continue
                        
                        game_id = weapon.get('gameId', '')
                        skill_name = weapon.get('skillName', '')
                        
                        if not game_id or not skill_name:
                            continue
                        
                        # Map rarity
                        rarity_map = {
                            'common': 'common',
                            'uncommon': 'uncommon',
                            'rare': 'rare',
                            'epic': 'epic',
                            'legendary': 'legendary'
                        }
                        rarity = rarity_map.get(weapon.get('rarity', 'common'), 'common')
                        
                        # Extract detailed weapon data
                        mana_cost = None
                        if weapon.get('manaCost') and weapon.get('manaCost').isdigit():
                            mana_cost = int(weapon.get('manaCost'))
                        
                        cooldown = weapon.get('cooldown', '')
                        casting_range = weapon.get('castingRange', '')
                        skill_type = weapon.get('type', '')
                        tier_unlock = weapon.get('tierUnlock', '')
                        
                        # Extract detailed stats
                        stats = weapon.get('stats', {})
                        detailed_stats = {}
                        if stats:
                            detailed_stats = dict(stats)
                        
                        # Create weapon item
                        weapon_item, created = GearItem.objects.get_or_create(
                            name=skill_name,
                            defaults={
                                'gear_type': weapon_gear_type,
                                'rarity': rarity,
                                'required_level': 1,
                                'damage': 0,
                                'defense': 0,
                                'health_bonus': 0,
                                'energy_bonus': 0,
                                'description': weapon.get('description', ''),
                                'mana_cost': mana_cost,
                                'cooldown': cooldown,
                                'casting_range': casting_range,
                                'skill_type': skill_type,
                                'tier_unlock': tier_unlock,
                                'detailed_stats': detailed_stats,
                                'is_craftable': True,
                                'is_tradeable': True,
                                'game_id': game_id,
                                'icon_url': f'/static/icons/{game_id}.png'
                            }
                        )
                        
                        if created:
                            imported_count += 1
                            self.stdout.write(f'  Created weapon: {skill_name}')
        
        self.stdout.write(f'Imported {imported_count} weapons')

    def import_consumables(self, repos_path):
        """Import consumable items (English only)"""
        self.stdout.write('Importing consumables...')
        
        # Create consumable gear type
        consumable_gear_type, _ = GearType.objects.get_or_create(
            name='Consumable',
            defaults={
                'category': 'consumable',
                'description': 'Consumable items'
            }
        )
        
        consumable_files = ['food.json', 'potions.json', 'utility.json']
        imported_count = 0
        
        for consumable_file in consumable_files:
            file_path = os.path.join(repos_path, 'consumable', consumable_file)
            
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process consumables based on file structure
            for category, items in data.items():
                if not isinstance(items, list):
                    continue
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    item_name = item.get('name', '')
                    item_id = item.get('id', '')
                    
                    if not item_name or not item_id:
                        continue
                    
                    # Map rarity
                    rarity_map = {
                        'common': 'common',
                        'uncommon': 'uncommon',
                        'rare': 'rare',
                        'epic': 'epic',
                        'legendary': 'legendary'
                    }
                    rarity = rarity_map.get(item.get('rarity', 'common'), 'common')
                    
                    # Create consumable item
                    consumable_item, created = GearItem.objects.get_or_create(
                        name=item_name,
                        defaults={
                            'gear_type': consumable_gear_type,
                            'rarity': rarity,
                            'required_level': 1,
                            'damage': 0,
                            'defense': 0,
                            'health_bonus': 0,
                            'energy_bonus': 0,
                            'description': item.get('description', ''),
                            'is_craftable': True,
                            'is_tradeable': True,
                            'game_id': item_id,
                            'icon_url': f'/static/icons/{item_id}.png'
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created consumable: {item_name}')
        
        self.stdout.write(f'Imported {imported_count} consumables')

    def import_mods(self, repos_path):
        """Import all mod data (English only)"""
        self.stdout.write('Importing mods...')
        
        # Create mod gear type
        mod_gear_type, _ = GearType.objects.get_or_create(
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
                    
                    # Determine mod type based on description
                    mod_type = 'special'  # default
                    description = mod.get('description', '').lower()
                    if 'damage' in description:
                        mod_type = 'damage'
                    elif 'defense' in description or 'armor' in description:
                        mod_type = 'defense'
                    elif 'health' in description or 'hp' in description:
                        mod_type = 'health'
                    elif 'energy' in description or 'mana' in description:
                        mod_type = 'energy'
                    elif 'speed' in description or 'movement' in description:
                        mod_type = 'speed'
                    
                    # Map rarity
                    rarity_map = {
                        'common': 'common',
                        'rare': 'rare',
                        'epic': 'epic',
                        'legendary': 'legendary'
                    }
                    rarity = rarity_map.get(mod.get('rarity', 'rare'), 'rare')
                    
                    # Create mod
                    gear_mod, created = GearMod.objects.get_or_create(
                        name=mod_name,
                        defaults={
                            'mod_type': mod_type,
                            'rarity': rarity,
                            'damage_bonus': 0,
                            'defense_bonus': 0,
                            'health_bonus': 0,
                            'energy_bonus': 0,
                            'speed_bonus': 0,
                            'description': mod.get('description', ''),
                            'is_active': True,
                            'game_id': icon_name  # Use iconName as game_id
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created mod: {mod_name} ({slot})')
        
        self.stdout.write(f'Imported {imported_count} mods')

    def import_drifters(self, repos_path):
        """Import all drifter data (English only)"""
        self.stdout.write('Importing drifters...')
        
        drifter_files = ['str_drifter.json', 'dex_drifter.json', 'int_drifter.json', 'gather_drifter.json']
        imported_count = 0
        
        for drifter_file in drifter_files:
            file_path = os.path.join(repos_path, 'drifters', f'{drifter_file}')
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process drifters
            for drifter_key, drifter_data in data.items():
                if not isinstance(drifter_data, dict):
                    continue
                
                drifter_name = drifter_data.get('name', drifter_key.replace('_', ' ').title())
                drifter_id = drifter_data.get('id', drifter_key)
                
                # Create drifter
                drifter, created = Drifter.objects.get_or_create(
                    name=drifter_name,
                    defaults={
                        'description': drifter_data.get('description', ''),
                        'base_health': int(drifter_data.get('baseHp', 100)),
                        'base_energy': int(drifter_data.get('baseMp', 100)),
                        'base_damage': int(drifter_data.get('baseDamage', 50)),
                        'base_defense': int(drifter_data.get('baseDefense', 25)),
                        'base_speed': int(drifter_data.get('baseSpeed', 100)),
                        'special_abilities': drifter_data.get('abilities', ''),
                        'is_active': True
                    }
                )
                
                if created:
                    imported_count += 1
                    self.stdout.write(f'  Created drifter: {drifter_name}')
        
        self.stdout.write(f'Imported {imported_count} drifters')
