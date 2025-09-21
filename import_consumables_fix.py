#!/usr/bin/env python
import os
import json
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_local')
django.setup()

from guilds.models import GearItem, GearType

def import_consumables_fix():
    """Fix consumables import"""
    print("Importing consumables...")
    
    # Create consumable gear type
    consumable_type, _ = GearType.objects.get_or_create(
        name='Consumable',
        defaults={
            'category': 'consumable',
            'description': 'Consumable items'
        }
    )
    
    repos_path = 'repos/warborne-data-json'
    consumable_files = ['food.json', 'poison.json', 'potions.json', 'utility.json']
    imported_count = 0
    
    for filename in consumable_files:
        file_path = os.path.join(repos_path, 'consumable', filename)
        
        if not os.path.exists(file_path):
            print(f'Warning: {file_path} not found')
            continue
        
        print(f"Processing {filename}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get the consumable list (key varies by file)
        consumable_key = None
        for key in data.keys():
            if key != 'lastUpdate' and isinstance(data[key], list):
                consumable_key = key
                break
        
        if not consumable_key:
            print(f"  No consumable list found in {filename}")
            continue
        
        consumables = data[consumable_key]
        print(f"  Found {len(consumables)} items in {consumable_key}")
        
        for consumable in consumables:
            if not isinstance(consumable, dict):
                continue
            
            # Try different name fields
            item_name = consumable.get('name', consumable.get('consumableName', ''))
            game_id = consumable.get('id', consumable.get('gameId', ''))
            
            if not item_name:
                print(f"  Skipping item without name: {consumable}")
                continue
            
            if not game_id:
                game_id = item_name.lower().replace(' ', '-')
            
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
                base_name=item_name,
                skill_name=item_name,  # For consumables, base_name and skill_name are the same
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
                print(f'  Created consumable: {item_name}')
    
    print(f'Imported {imported_count} consumables')

if __name__ == '__main__':
    import_consumables_fix()
