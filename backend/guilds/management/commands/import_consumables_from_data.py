from django.core.management.base import BaseCommand
from guilds.models import GearItem, GearType
import json
import os

class Command(BaseCommand):
    help = 'Import consumables from existing data'

    def handle(self, *args, **options):
        self.stdout.write('Importing consumables from JSON files...')
        
        # Create consumable gear type
        consumable_type, _ = GearType.objects.get_or_create(
            name='Consumable',
            defaults={
                'category': 'consumable',
                'description': 'Consumable items'
            }
        )
        
        # Import from JSON files
        repos_path = 'repos/warborne-data-json'
        consumable_files = ['food.json', 'poison.json', 'potions.json', 'utility.json']
        imported_count = 0
        
        for filename in consumable_files:
            file_path = os.path.join(repos_path, 'consumable', filename)
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
            
            self.stdout.write(f"Processing {filename}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get the consumable list (key varies by file)
            consumable_key = None
            for key in data.keys():
                if key != 'lastUpdate' and isinstance(data[key], list):
                    consumable_key = key
                    break
            
            if not consumable_key:
                self.stdout.write(f"  No consumable list found in {filename}")
                continue
            
            consumables = data[consumable_key]
            self.stdout.write(f"  Found {len(consumables)} items in {consumable_key}")
            
            for consumable in consumables:
                if not isinstance(consumable, dict):
                    continue
                
                # Get item data
                item_name = consumable.get('name', '')
                game_id = consumable.get('id', '')
                
                if not item_name or not game_id:
                    continue
                
                # Map rarity
                rarity_map = {
                    'common': 'common',
                    'uncommon': 'uncommon', 
                    'rare': 'rare',
                    'epic': 'epic',
                    'legendary': 'legendary'
                }
                rarity = rarity_map.get(consumable.get('rarity', 'common'), 'common')
                
                # Create consumable item
                consumable_item, created = GearItem.objects.get_or_create(
                    base_name=item_name,
                    skill_name=item_name,
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
                        'cooldown': '',
                        'casting_range': '',
                        'skill_type': '',
                        'tier_unlock': '',
                        'detailed_stats': {},
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
