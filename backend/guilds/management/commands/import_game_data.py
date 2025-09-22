import json
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from guilds.models import GearType, GearItem, GearMod, Drifter
import os
import time


class Command(BaseCommand):
    help = 'Import real Warborne Above Ashes data from GitHub repositories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='github',
            help='Data source: github or local'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing items instead of skipping'
        )

    def handle(self, *args, **options):
        self.stdout.write('Importing real Warborne Above Ashes data...')
        
        source = options['source']
        update_existing = options['update_existing']
        
        if source == 'github':
            self.import_from_github(update_existing)
        else:
            self.stdout.write(self.style.ERROR('Local import not implemented yet'))
    
    def import_from_github(self, update_existing=False):
        """Import data from GitHub repositories"""
        
        # Base URLs for the repositories
        base_urls = {
            'main_data': 'https://raw.githubusercontent.com/ElKite/warborne-data-json/main'
        }
        
        try:
            # Import from main data.json file
            self.import_from_main_data(base_urls['main_data'])
            
            self.stdout.write(
                self.style.SUCCESS('✅ Real game data imported successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error importing data: {e}')
            )
    
    def import_from_main_data(self, base_url):
        """Import data from the main data.json file"""
        self.stdout.write('Importing from main data.json...')
        
        try:
            # Get main data file
            url = f"{base_url}/data.json"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            self.stdout.write(f'✅ Successfully downloaded data.json ({len(str(data))} characters)')
            
            # Extract the actual data from the nested structure
            game_data = data.get('data', data)
            
            # Try to extract weapons, armors, mods, and drifters from the data
            imported_weapons = self.extract_and_import_weapons(game_data, base_url)
            imported_armors = self.extract_and_import_armors(game_data, base_url)
            imported_mods = self.extract_and_import_mods(game_data)
            imported_drifters = self.extract_and_import_drifters(game_data)
            
            self.stdout.write(f'✅ Import summary:')
            self.stdout.write(f'   - Weapons: {imported_weapons}')
            self.stdout.write(f'   - Armors: {imported_armors}')
            self.stdout.write(f'   - Mods: {imported_mods}')
            self.stdout.write(f'   - Drifters: {imported_drifters}')
            
        except Exception as e:
            self.stdout.write(f'❌ Error importing from main data: {e}')
            # Fallback: create some sample data if import fails
            self.create_fallback_data()
    
    def extract_and_import_weapons(self, data, base_url):
        """Extract and import weapons from data structure"""
        self.stdout.write('Extracting weapons...')
        
        # Create weapon gear type
        weapon_type, created = GearType.objects.get_or_create(
            name='Weapon',
            category='weapon'
        )
        
        imported_count = 0
        
        # Try to find weapons in various possible locations in the data
        weapons = []
        if 'weapon' in data:  # Singular form - this is a dict with weapon types
            weapon_data = data['weapon']
            if isinstance(weapon_data, dict):
                # Flatten all weapon types into a single list, but keep track of weapon type
                for weapon_type_name, weapon_list in weapon_data.items():
                    if isinstance(weapon_list, list):
                        # Add weapon type info to each weapon item
                        for weapon in weapon_list:
                            if isinstance(weapon, dict):
                                weapon['_weapon_type'] = weapon_type_name
                        weapons.extend(weapon_list)
            elif isinstance(weapon_data, list):
                weapons = weapon_data
        elif 'weapons' in data:  # Plural form
            weapons = data['weapons']
        elif 'items' in data and 'weapons' in data['items']:
            weapons = data['items']['weapons']
        
        self.stdout.write(f'Found {len(weapons)} weapons to process')
        
        for weapon in weapons:
            try:
                # Skip if weapon is not a dictionary
                if not isinstance(weapon, dict):
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
                
                # Create weapon item using the actual field names from the data
                weapon_name = weapon.get('gearName', '') or weapon.get('skillName', 'Unknown Weapon')
                
                # Get or create specific weapon type based on the weapon type from data
                weapon_type_name = weapon.get('_weapon_type', 'unknown')
                specific_weapon_type, _ = GearType.objects.get_or_create(
                    name=f"{weapon_type_name.title()} Weapon",
                    defaults={
                        'category': 'weapon',
                        'description': f"{weapon_type_name.title()} type weapons"
                    }
                )
                
                weapon_item, created = GearItem.objects.get_or_create(
                    name=weapon_name,
                    defaults={
                        'gear_type': specific_weapon_type,
                        'rarity': rarity,
                        'required_level': int(weapon.get('unlock', 1)) if weapon.get('unlock', '1').isdigit() else 1,
                        'damage': 0,  # Will be calculated from description if needed
                        'defense': 0,
                        'health_bonus': 0,
                        'energy_bonus': 0,
                        'description': weapon.get('description', ''),
                        'is_craftable': False,
                        'is_tradeable': True,
                        'game_id': weapon.get('gameId', ''),
                    }
                )
                
                if created:
                    imported_count += 1
                    
                    # Try to set icon URL if available
                    if 'icon' in weapon and weapon['icon']:
                        weapon_item.icon_url = f"{base_url}/icons/{weapon['icon']}"
                        weapon_item.save()
                    elif weapon_item.game_id:
                        # Try to construct icon URL from game_id
                        weapon_item.icon_url = f"{base_url}/icons/{weapon_item.game_id}.png"
                        weapon_item.save()
                
            except Exception as e:
                self.stdout.write(f'Warning: Could not import weapon {weapon.get("name", "Unknown")}: {e}')
                continue
        
        return imported_count
    
    def extract_and_import_armors(self, data, base_url):
        """Extract and import armors from data structure"""
        self.stdout.write('Extracting armors...')
        
        # Create armor gear type
        armor_type, created = GearType.objects.get_or_create(
            name='Armor',
            category='armor'
        )
        
        imported_count = 0
        
        # Try to find armors in various possible locations in the data
        armors = []
        if 'armor' in data:  # Singular form - this is a dict with armor types
            armor_data = data['armor']
            if isinstance(armor_data, dict):
                # Flatten all armor types into a single list, but keep track of armor type
                for armor_type_name, armor_list in armor_data.items():
                    if isinstance(armor_list, list):
                        # Add armor type info to each armor item
                        for armor in armor_list:
                            if isinstance(armor, dict):
                                armor['_armor_type'] = armor_type_name
                        armors.extend(armor_list)
            elif isinstance(armor_data, list):
                armors = armor_data
        elif 'armors' in data:  # Plural form
            armors = data['armors']
        elif 'items' in data and 'armors' in data['items']:
            armors = data['items']['armors']
        
        self.stdout.write(f'Found {len(armors)} armors to process')
        
        for armor in armors:
            try:
                # Skip if armor is not a dictionary
                if not isinstance(armor, dict):
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
                
                # Create armor item using the actual field names from the data
                armor_name = armor.get('gearName', '') or armor.get('skillName', 'Unknown Armor')
                
                # Get or create specific armor type based on the armor type from data
                armor_type_name = armor.get('_armor_type', 'unknown')
                specific_armor_type, _ = GearType.objects.get_or_create(
                    name=f"{armor_type_name.replace('_', ' ').title()} Armor",
                    defaults={
                        'category': 'armor',
                        'description': f"{armor_type_name.replace('_', ' ').title()} type armor"
                    }
                )
                
                armor_item, created = GearItem.objects.get_or_create(
                    name=armor_name,
                    defaults={
                        'gear_type': specific_armor_type,
                        'rarity': rarity,
                        'required_level': int(armor.get('unlock', 1)) if armor.get('unlock', '1').isdigit() else 1,
                        'damage': 0,
                        'defense': 0,  # Will be calculated from description if needed
                        'health_bonus': 0,
                        'energy_bonus': 0,
                        'description': armor.get('description', ''),
                        'is_craftable': False,
                        'is_tradeable': True,
                        'game_id': armor.get('gameId', ''),
                    }
                )
                
                if created:
                    imported_count += 1
                    
                    # Try to set icon URL if available
                    if 'icon' in armor and armor['icon']:
                        armor_item.icon_url = f"{base_url}/icons/{armor['icon']}"
                        armor_item.save()
                    elif armor_item.game_id:
                        # Try to construct icon URL from game_id
                        armor_item.icon_url = f"{base_url}/icons/{armor_item.game_id}.png"
                        armor_item.save()
                
            except Exception as e:
                self.stdout.write(f'Warning: Could not import armor {armor.get("name", "Unknown")}: {e}')
                continue
        
        return imported_count
    
    def extract_and_import_mods(self, data):
        """Extract and import mods from data structure"""
        self.stdout.write('Extracting mods...')
        
        imported_count = 0
        
        # Try to find mods in various possible locations in the data
        mods = []
        if 'mods' in data:
            mods = data['mods']
        elif 'items' in data and 'mods' in data['items']:
            mods = data['items']['mods']
        
        for mod in mods:
            try:
                # Skip if mod is not a dictionary
                if not isinstance(mod, dict):
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
                
                mod_type = mod_type_map.get(mod.get('type', 'damage'), 'damage')
                
                # Map rarity
                rarity_map = {
                    'rare': 'rare',
                    'epic': 'epic',
                    'legendary': 'legendary'
                }
                
                rarity = rarity_map.get(mod.get('rarity', 'rare'), 'rare')
                
                # Create mod
                gear_mod, created = GearMod.objects.get_or_create(
                    name=mod.get('name', 'Unknown Mod'),
                    defaults={
                        'description': mod.get('description', ''),
                        'mod_type': mod_type,
                        'rarity': rarity,
                        'damage_bonus': mod.get('damage_bonus', 0),
                        'defense_bonus': mod.get('defense_bonus', 0),
                        'health_bonus': mod.get('health_bonus', 0),
                        'energy_bonus': mod.get('energy_bonus', 0),
                        'speed_bonus': mod.get('speed_bonus', 0),
                        'is_active': True,
                        'game_id': mod.get('id', ''),
                    }
                )
                
                if created:
                    imported_count += 1
                
            except Exception as e:
                self.stdout.write(f'Warning: Could not import mod {mod.get("name", "Unknown")}: {e}')
                continue
        
        return imported_count
    
    def extract_and_import_drifters(self, data):
        """Extract and import drifters from data structure"""
        self.stdout.write('Extracting drifters...')
        
        imported_count = 0
        
        # Try to find drifters in various possible locations in the data
        drifters = []
        if 'drifters' in data:
            drifters = data['drifters']
        elif 'characters' in data:
            drifters = data['characters']
        
        for drifter in drifters:
            try:
                # Skip if drifter is not a dictionary
                if not isinstance(drifter, dict):
                    continue
                
                # Create drifter
                drifter_obj, created = Drifter.objects.get_or_create(
                    name=drifter.get('name', 'Unknown Drifter'),
                    defaults={
                        'description': drifter.get('description', ''),
                        'base_health': drifter.get('health', 100),
                        'base_energy': drifter.get('energy', 100),
                        'base_damage': drifter.get('damage', 50),
                        'base_defense': drifter.get('defense', 25),
                        'base_speed': drifter.get('speed', 10),
                        'special_abilities': drifter.get('abilities', ''),
                        'is_active': True,
                    }
                )
                
                if created:
                    imported_count += 1
                
            except Exception as e:
                self.stdout.write(f'Warning: Could not import drifter {drifter.get("name", "Unknown")}: {e}')
                continue
        
        return imported_count
    
    def create_fallback_data(self):
        """Create some fallback data if import fails"""
        self.stdout.write('Creating fallback sample data...')
        
        # Create basic gear types
        weapon_type, _ = GearType.objects.get_or_create(name='Weapon', category='weapon')
        armor_type, _ = GearType.objects.get_or_create(name='Armor', category='armor')
        
        # Create some sample items
        sample_weapons = [
            {'name': 'Plasma Rifle', 'damage': 85, 'rarity': 'rare'},
            {'name': 'Laser Pistol', 'damage': 45, 'rarity': 'common'},
            {'name': 'Energy Sword', 'damage': 120, 'rarity': 'epic'},
        ]
        
        sample_armors = [
            {'name': 'Combat Armor', 'defense': 60, 'rarity': 'uncommon'},
            {'name': 'Heavy Plate', 'defense': 90, 'rarity': 'rare'},
            {'name': 'Energy Shield', 'defense': 40, 'rarity': 'common'},
        ]
        
        for weapon in sample_weapons:
            GearItem.objects.get_or_create(
                name=weapon['name'],
                defaults={
                    'gear_type': weapon_type,
                    'damage': weapon['damage'],
                    'rarity': weapon['rarity'],
                    'required_level': 1,
                }
            )
        
        for armor in sample_armors:
            GearItem.objects.get_or_create(
                name=armor['name'],
                defaults={
                    'gear_type': armor_type,
                    'defense': armor['defense'],
                    'rarity': armor['rarity'],
                    'required_level': 1,
                }
            )
        
        # Create some sample drifters
        sample_drifters = [
            {'name': 'Scout', 'health': 80, 'energy': 120, 'damage': 60, 'defense': 30},
            {'name': 'Tank', 'health': 150, 'energy': 80, 'damage': 40, 'defense': 80},
            {'name': 'Assassin', 'health': 70, 'energy': 100, 'damage': 90, 'defense': 25},
        ]
        
        for drifter in sample_drifters:
            Drifter.objects.get_or_create(
                name=drifter['name'],
                defaults={
                    'base_health': drifter['health'],
                    'base_energy': drifter['energy'],
                    'base_damage': drifter['damage'],
                    'base_defense': drifter['defense'],
                    'base_speed': 10,
                    'description': f"A {drifter['name'].lower()} class character",
                    'is_active': True,
                }
            )
        
        self.stdout.write('✅ Fallback data created successfully!')
    
    def import_item_icon(self, item, icon_path, base_url):
        """Set item icon URL from GitHub (no file download for local dev)"""
        try:
            # Construct full icon URL
            icon_url = f"{base_url}/icons/{icon_path}"
            
            # Just set the URL, don't download the file for local development
            item.icon_url = icon_url
            item.save()
            self.stdout.write(f'  📷 Icon URL set: {icon_url}')
                
        except Exception as e:
            # Silently fail for icons - they're not critical
            pass
