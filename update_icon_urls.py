#!/usr/bin/env python
"""
Script to update icon URLs to use local static files
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_local')
django.setup()

from guilds.models import GearItem

def update_icon_urls():
    print("Updating icon URLs to use local static files...")
    
    # Get all gear items
    gear_items = GearItem.objects.all()
    print(f"Found {gear_items.count()} gear items")
    
    updated_count = 0
    for item in gear_items:
        if item.icon_url and 'SpecImage' in item.icon_url:
            # Extract the icon filename from the URL
            icon_filename = item.icon_url.split('/')[-1]
            # Update to use local static file
            item.icon_url = f"/static/icons/{icon_filename}"
            item.save()
            updated_count += 1
            print(f"Updated: {item.base_name} -> {item.icon_url}")
    
    print(f"✅ Updated {updated_count} icon URLs")

if __name__ == "__main__":
    update_icon_urls()
