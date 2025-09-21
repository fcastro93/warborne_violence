import os
import json
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from guilds.models import GearType, GearItem, Drifter, GearMod

class Command(BaseCommand):
    help = 'Import all game data from local repositories'

    def handle(self, *args, **options):
        self.stdout.write('Starting local data import...')
        
        # Base path to repositories
        repos_path = os.path.join(settings.BASE_DIR, 'repos', 'warborne-data-json')
        
        if not os.path.exists(repos_path):
            self.stdout.write(self.style.ERROR(f'Repository path not found: {repos_path}'))
            return
        
        # Copy all icons first
        self.copy_icons(repos_path)
        
        # Import all data types
        self.import_armors(repos_path)
        self.import_weapons(repos_path)
        self.import_items(repos_path)
        self.import_mods(repos_path)
        self.import_drifters(repos_path)
        
        self.stdout.write(self.style.SUCCESS('✅ Local data import completed successfully!'))

    def copy_icons(self, repos_path):
        """Copy all icons to local static folder"""
        self.stdout.write('Copying icons...')
        
        icons_source = os.path.join(repos_path, 'icons')
        icons_dest = os.path.join(settings.BASE_DIR, 'static', 'icons')
        
        if not os.path.exists(icons_source):
            self.stdout.write(self.style.WARNING(f'Icons source not found: {icons_source}'))
            return
        
        # Create destination directory if it doesn't exist
        os.makedirs(icons_dest, exist_ok=True)
        
        copied_count = 0
        
        # Copy all PNG files from icons source
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
        """Import all armor data"""
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
                
                # Create gear type
                gear_type_name = armor_type.replace('_', ' ').title()
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
                            'icon_url': f'/static/icons/{game_id}.png'  # Local path
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created armor: {gear_name}')
        
        self.stdout.write(f'Imported {imported_count} armors')

    def import_weapons(self, repos_path):
        """Import all weapon data"""
        self.stdout.write('Importing weapons...')
        
        weapon_types = [
            'str_axe', 'str_gun', 'str_mace', 'str_sword',
            'dex_bow', 'dex_dagger', 'dex_nature', 'dex_spear',
            'int_curse', 'int_fire', 'int_frost', 'int_holy'
        ]
        
        imported_count = 0
        
        for weapon_type in weapon_types:
            file_path = os.path.join(repos_path, 'weapons', f'{weapon_type}.json')
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create gear type
            gear_type_name = weapon_type.replace('_', ' ').title() + ' Weapon'
            gear_type, _ = GearType.objects.get_or_create(
                name=gear_type_name,
                defaults={
                    'category': 'weapon',
                    'description': f'{gear_type_name} weapons'
                }
            )
            
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
                        
                        # Create weapon item
                        weapon_item, created = GearItem.objects.get_or_create(
                            name=skill_name,
                            defaults={
                                'gear_type': gear_type,
                                'rarity': rarity,
                                'required_level': 1,
                                'damage': 0,
                                'defense': 0,
                                'health_bonus': 0,
                                'energy_bonus': 0,
                                'description': weapon.get('description', ''),
                                'is_craftable': True,
                                'is_tradeable': True,
                                'game_id': game_id,
                                'icon_url': f'/static/icons/{game_id}.png'  # Local path
                            }
                        )
                        
                        if created:
                            imported_count += 1
                            self.stdout.write(f'  Created weapon: {skill_name}')
        
        self.stdout.write(f'Imported {imported_count} weapons')

    def import_items(self, repos_path):
        """Import all general items"""
        self.stdout.write('Importing general items...')
        
        file_path = os.path.join(repos_path, 'items', 'items.json')
        
        if not os.path.exists(file_path):
            self.stdout.write(f'Warning: {file_path} not found')
            return
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported_count = 0
        
        for item in data.get('items', []):
            if not isinstance(item, dict):
                continue
            
            item_id = item.get('id', '')
            item_name = item.get('name', '')
            category = item.get('category', 'accessory')
            
            if not item_id or not item_name:
                continue
            
            # Create gear type based on category
            gear_type, _ = GearType.objects.get_or_create(
                name=category.title(),
                defaults={
                    'category': 'accessory',
                    'description': f'{category.title()} items'
                }
            )
            
            # Map rarity
            rarity_map = {
                'common': 'common',
                'uncommon': 'uncommon',
                'rare': 'rare',
                'epic': 'epic',
                'legendary': 'legendary',
                'abandoned': 'common',
                'advanced': 'rare',
                'enhanced': 'epic'
            }
            rarity = rarity_map.get(item.get('rarity', 'common'), 'common')
            
            # Create item
            gear_item, created = GearItem.objects.get_or_create(
                name=item_name,
                defaults={
                    'gear_type': gear_type,
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
                    'icon_url': f'/static/icons/{item_id}.png'  # Local path
                }
            )
            
            if created:
                imported_count += 1
                self.stdout.write(f'  Created item: {item_name}')
        
        self.stdout.write(f'Imported {imported_count} general items')

    def import_mods(self, repos_path):
        """Import all mod data"""
        self.stdout.write('Importing mods...')
        
        mod_files = ['mod_armor.json', 'mod_weapon.json']
        imported_count = 0
        
        for mod_file in mod_files:
            file_path = os.path.join(repos_path, 'mods', mod_file)
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process mods based on file structure
            for mod_category, mods in data.items():
                if not isinstance(mods, list):
                    continue
                
                for mod in mods:
                    if not isinstance(mod, dict):
                        continue
                    
                    mod_name = mod.get('modName', '')
                    mod_id = mod.get('modId', '')
                    
                    if not mod_name or not mod_id:
                        continue
                    
                    # Map mod type
                    mod_type_map = {
                        'damage': 'damage',
                        'defense': 'defense',
                        'health': 'health',
                        'energy': 'energy',
                        'speed': 'speed',
                        'special': 'special'
                    }
                    mod_type = mod_type_map.get(mod_category, 'special')
                    
                    # Map rarity
                    rarity_map = {
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
                            'game_id': mod_id
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created mod: {mod_name}')
        
        self.stdout.write(f'Imported {imported_count} mods')

    def import_drifters(self, repos_path):
        """Import all drifter data"""
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
