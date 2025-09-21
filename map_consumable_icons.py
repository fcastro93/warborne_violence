#!/usr/bin/env python
import os
import shutil
from guilds.models import GearItem

def map_consumable_icons():
    """Map consumable items to their correct icon files"""
    print("Mapping consumable icons...")
    
    # Get all consumables
    consumables = GearItem.objects.filter(gear_type__category='consumable')
    
    # Common icon mappings based on item names
    icon_mappings = {
        'advanced-light-blaster-turret': 'equip_turret_1',
        'advanced-paratoxin': 'equip_medicine_2_1', 
        'advanced-psyche-infusion': 'equip_medicine_1_1',
        'advanced-rejuvenix-flask': 'equip_medicine_3_1',
        'aegis-draught-ex': 'equip_medicine_3_1',
        'aegis-draught-ultra': 'equip_medicine_3_2',
        'autonomic-harvester-kit': 'equip_utility_1',
        'battle-standard': 'equip_utility_2',
        'boost-station-kit': 'equip_utility_3',
        'cleansing-herb': 'equip_food_1',
        'demolisher': 'equip_utility_4',
        'enhanced-paratoxin': 'equip_medicine_2_2',
    }
    
    repos_icons_dir = 'repos/warborne-data-json/icons'
    static_icons_dir = 'static/icons'
    
    if not os.path.exists(repos_icons_dir):
        print(f"Repos icons directory not found: {repos_icons_dir}")
        return
    
    if not os.path.exists(static_icons_dir):
        os.makedirs(static_icons_dir)
    
    mapped_count = 0
    
    for consumable in consumables:
        game_id = consumable.game_id.lower().replace('_', '-')
        
        # Try to find matching icon
        icon_found = False
        
        # Check direct mapping
        if game_id in icon_mappings:
            source_icon = f"{icon_mappings[game_id]}.png"
            source_path = os.path.join(repos_icons_dir, source_icon)
            if os.path.exists(source_path):
                dest_path = os.path.join(static_icons_dir, f"{game_id}.png")
                shutil.copy2(source_path, dest_path)
                print(f"✓ Mapped {consumable.base_name} -> {source_icon}")
                mapped_count += 1
                icon_found = True
        
        # If not found, try to find by name patterns
        if not icon_found:
            name_lower = consumable.base_name.lower()
            if 'turret' in name_lower:
                source_icon = 'equip_turret_1.png'
            elif 'potion' in name_lower or 'draught' in name_lower:
                source_icon = 'equip_medicine_3_1.png'
            elif 'herb' in name_lower or 'food' in name_lower:
                source_icon = 'equip_food_1.png'
            elif 'harvester' in name_lower or 'kit' in name_lower:
                source_icon = 'equip_utility_1.png'
            elif 'standard' in name_lower or 'banner' in name_lower:
                source_icon = 'equip_utility_2.png'
            else:
                source_icon = 'equip_medicine_1_1.png'  # Default
            
            source_path = os.path.join(repos_icons_dir, source_icon)
            if os.path.exists(source_path):
                dest_path = os.path.join(static_icons_dir, f"{game_id}.png")
                shutil.copy2(source_path, dest_path)
                print(f"✓ Mapped {consumable.base_name} -> {source_icon}")
                mapped_count += 1
            else:
                print(f"✗ No icon found for {consumable.base_name}")
    
    print(f"\nMapped {mapped_count} consumable icons")

if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_local')
    django.setup()
    map_consumable_icons()
