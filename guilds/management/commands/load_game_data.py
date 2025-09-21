"""
Management command to load game data from fixtures
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Load game data from fixtures'

    def handle(self, *args, **options):
        self.stdout.write('Loading game data from fixtures...')
        
        # Get the fixtures directory
        fixtures_dir = os.path.join(settings.BASE_DIR, 'guilds', 'fixtures')
        
        if not os.path.exists(fixtures_dir):
            self.stdout.write(
                self.style.ERROR('Fixtures directory not found. Please create fixtures first.')
            )
            return
        
        # Load fixtures in order
        fixtures = [
            'gear_types.json',
            'drifters.json', 
            'gear_items.json',
            'gear_mods.json'
        ]
        
        for fixture in fixtures:
            fixture_path = os.path.join(fixtures_dir, fixture)
            if os.path.exists(fixture_path):
                try:
                    call_command('loaddata', fixture_path, verbosity=0)
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Loaded {fixture}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'⚠ Error loading {fixture}: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Fixture {fixture} not found')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Game data loading completed!')
        )
