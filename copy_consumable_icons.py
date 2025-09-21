#!/usr/bin/env python
import os
import shutil
from pathlib import Path

def copy_consumable_icons():
    """Copy appropriate icons for consumable items"""
    print("Copying consumable icons...")
    
    # Source and destination directories
    source_dir = Path('repos/warborne-data-json/icons')
    dest_dir = Path('static/icons')
    
    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Mapping of consumable game_ids to appropriate icon files
    icon_mappings = {
        # Advanced items - use medicine icons
        'advanced-light-blaster-turret': 'equip_medicine_1_1.png',
        'advanced-paratoxin': 'equip_medicine_1_2.png',
        'advanced-psyche-infusion': 'equip_medicine_1_3.png',
        'advanced-rejuvenix-flask': 'equip_medicine_2_1.png',
        
        # Aegis items - use medicine icons
        'aegis-draught-ex': 'equip_medicine_2_2.png',
        'aegis-draught-ultra': 'equip_medicine_2_3.png',
        
        # Other consumables - use food and medicine icons
        'autonomic-harvester-kit': 'equip_food_1.png',
        'battle-standard': 'equip_food_2.png',
        'boost-station-kit': 'equip_food_3.png',
        'cleansing-herb': 'equip_food_4.png',
        'demolisher': 'equip_food_5.png',
        'enhanced-paratoxin': 'equip_medicine_3_1.png',
        'enhanced-psyche-infusion': 'equip_medicine_3_2.png',
        'enhanced-rejuvenix-flask': 'equip_medicine_3_3.png',
        'instant-aid-vial-ex': 'equip_medicine_4_1.png',
        'instant-aid-vial-ultra': 'equip_medicine_4_2.png',
        'light-blaster-turret': 'equip_medicine_4_3.png',
        'mass-healing-elixir': 'equip_medicine_5_1.png',
        'mass-restoration-device': 'equip_medicine_5_2.png',
        'paratoxin': 'equip_medicine_5_3.png',
        'psyche-infusion': 'equip_medicine_6_1.png',
        'rejuvenix-flask': 'equip_medicine_6_2.png',
        'vitalis-potion': 'equip_medicine_6_3.png',
    }
    
    copied_count = 0
    
    for game_id, icon_file in icon_mappings.items():
        source_path = source_dir / icon_file
        dest_path = dest_dir / f"{game_id}.png"
        
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            print(f"✓ Copied {icon_file} -> {game_id}.png")
            copied_count += 1
        else:
            print(f"✗ Source icon not found: {icon_file}")
    
    print(f"\nCopied {copied_count} consumable icons")

if __name__ == '__main__':
    copy_consumable_icons()
