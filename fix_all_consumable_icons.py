#!/usr/bin/env python
import os
import shutil
from pathlib import Path

def fix_all_consumable_icons():
    """Assign icons to all consumable items"""
    print("Fixing all consumable icons...")
    
    # Source and destination directories
    source_dir = Path('repos/warborne-data-json/icons')
    dest_dir = Path('static/icons')
    
    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Available icon files
    available_icons = [
        'equip_food_1.png', 'equip_food_2.png', 'equip_food_3.png', 'equip_food_4.png', 'equip_food_5.png',
        'equip_medicine_1_1.png', 'equip_medicine_1_2.png', 'equip_medicine_1_3.png',
        'equip_medicine_2_1.png', 'equip_medicine_2_2.png', 'equip_medicine_2_3.png',
        'equip_medicine_3_1.png', 'equip_medicine_3_2.png', 'equip_medicine_3_3.png',
        'equip_medicine_4_1.png', 'equip_medicine_4_2.png', 'equip_medicine_4_3.png',
        'equip_medicine_5_1.png', 'equip_medicine_5_2.png', 'equip_medicine_5_3.png',
        'equip_medicine_6_1.png', 'equip_medicine_6_2.png', 'equip_medicine_6_3.png',
        'equip_medicine_blackhand_2.png', 'equip_medicine_blackhand_3.png',
        'equip_medicine_iceblock_2.png', 'equip_medicine_iceblock_3.png',
        'equip_medicine_mass_defen_2.png', 'equip_medicine_mass_defen_3.png',
        'equip_medicine_reflect_shell_2.png', 'equip_medicine_reflect_shell_3.png',
        'equip_medicine_voidzone_2.png', 'equip_medicine_voidzone_3.png',
        'Invincible_Potion.png'
    ]
    
    # Get all consumable game_ids that need icons
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_local')
    django.setup()
    
    from guilds.models import GearItem
    
    consumables = GearItem.objects.filter(gear_type__category='consumable')
    missing_icons = []
    
    for item in consumables:
        icon_path = dest_dir / f"{item.game_id}.png"
        if not icon_path.exists():
            missing_icons.append(item)
    
    print(f"Found {len(missing_icons)} consumables without icons")
    
    # Assign icons to missing consumables
    icon_index = 0
    copied_count = 0
    
    for item in missing_icons:
        if icon_index >= len(available_icons):
            icon_index = 0  # Cycle through icons
        
        source_icon = available_icons[icon_index]
        source_path = source_dir / source_icon
        dest_path = dest_dir / f"{item.game_id}.png"
        
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            print(f"✓ Assigned {source_icon} -> {item.base_name} ({item.game_id})")
            copied_count += 1
        else:
            print(f"✗ Source icon not found: {source_icon}")
        
        icon_index += 1
    
    print(f"\nAssigned {copied_count} icons to consumables")

if __name__ == '__main__':
    fix_all_consumable_icons()
