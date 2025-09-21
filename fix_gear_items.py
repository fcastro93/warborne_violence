#!/usr/bin/env python
"""
Script to fix gear_items.json with correct field names
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_local')
django.setup()

import json
from guilds.models import GearItem

def fix_fixture():
    print("Fixing gear_items.json with correct field names...")
    
    # Get all gear items
    gear_items = GearItem.objects.all()
    print(f"Found {gear_items.count()} gear items")
    
    # Convert to JSON format with correct field names
    fixture_data = []
    for item in gear_items:
        fixture_data.append({
            "model": "guilds.gearitem",
            "pk": item.pk,
            "fields": {
                "base_name": item.base_name,
                "skill_name": item.skill_name or "",
                "gear_type": item.gear_type.pk if item.gear_type else None,
                "game_id": item.game_id,
                "rarity": item.rarity,
                "required_level": item.required_level,
                "damage": float(item.damage) if item.damage else 0,
                "defense": item.defense,
                "health_bonus": item.health_bonus,
                "energy_bonus": item.energy_bonus,
                "mana_recovery": item.mana_recovery,
                "armor": item.armor,
                "magic_resistance": item.magic_resistance,
                "icon_url": item.icon_url,
                "description": item.description or "",
                "mana_cost": float(item.mana_cost) if item.mana_cost else None,
                "cooldown": item.cooldown or "",
                "casting_range": item.casting_range or "",
                "skill_type": item.skill_type or "",
                "tier_unlock": item.tier_unlock or "",
                "detailed_stats": item.detailed_stats or {},
                "is_craftable": item.is_craftable,
            }
        })
    
    # Write to file with proper encoding
    output_path = 'guilds/fixtures/gear_items.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(fixture_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully fixed {output_path} with {len(fixture_data)} items")
    
    # Verify the file
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ File verification successful: {len(data)} items")
    except Exception as e:
        print(f"❌ File verification failed: {e}")

if __name__ == "__main__":
    fix_fixture()
