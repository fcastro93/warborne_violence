from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
import json

class Command(BaseCommand):
    help = 'Create fixtures for consumables from JSON data'

    def handle(self, *args, **options):
        self.stdout.write('Creating consumable fixtures...')
        
        # Import consumables first
        from guilds.management.commands.import_consumables_from_data import Command as ImportCommand
        import_cmd = ImportCommand()
        import_cmd.handle()
        
        # Create fixtures directory
        fixtures_dir = os.path.join('guilds', 'fixtures')
        os.makedirs(fixtures_dir, exist_ok=True)
        
        # Dump consumables to fixture
        self.stdout.write('Creating consumable fixtures...')
        
        # Get consumable items
        from guilds.models import GearItem
        consumable_items = GearItem.objects.filter(gear_type__category='consumable')
        
        if consumable_items.exists():
            # Create fixture data manually
            fixture_data = []
            for item in consumable_items:
                fixture_data.append({
                    'model': 'guilds.gearitem',
                    'pk': item.pk,
                    'fields': {
                        'base_name': item.base_name,
                        'skill_name': item.skill_name,
                        'gear_type': item.gear_type.pk,
                        'rarity': item.rarity,
                        'required_level': item.required_level,
                        'damage': item.damage,
                        'defense': item.defense,
                        'health_bonus': item.health_bonus,
                        'energy_bonus': item.energy_bonus,
                        'description': item.description,
                        'mana_cost': item.mana_cost,
                        'cooldown': item.cooldown,
                        'casting_range': item.casting_range,
                        'skill_type': item.skill_type,
                        'tier_unlock': item.tier_unlock,
                        'detailed_stats': item.detailed_stats,
                        'is_craftable': item.is_craftable,
                        'is_tradeable': item.is_tradeable,
                        'game_id': item.game_id,
                        'icon_url': item.icon_url
                    }
                })
            
            # Write to file
            with open(os.path.join(fixtures_dir, 'consumables.json'), 'w', encoding='utf-8') as f:
                json.dump(fixture_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(f'✓ Created consumables.json fixture with {len(fixture_data)} items')
        else:
            self.stdout.write('No consumable items found to create fixtures')
        
        self.stdout.write('✓ Created consumables.json fixture')
        self.stdout.write('Consumable fixtures created successfully!')
