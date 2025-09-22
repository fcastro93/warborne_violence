from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from guilds.models import Player, PlayerGear, GearItem, GearType


class Command(BaseCommand):
    help = 'Create test loadouts for players'

    def handle(self, *args, **options):
        self.stdout.write('Creating test loadouts for players...')
        
        # Get some players
        players = Player.objects.all()[:3]
        
        if not players:
            self.stdout.write(self.style.ERROR('No players found. Run create_sample_data first.'))
            return
        
        # Get some gear items
        gear_items = GearItem.objects.all()[:10]  # Get first 10 items
        
        if not gear_items:
            self.stdout.write(self.style.ERROR('No gear items found. Run import_game_data first.'))
            return
        
        # Create loadouts for each player
        for i, player in enumerate(players):
            # Clear existing gear
            PlayerGear.objects.filter(player=player).delete()
            
            # Assign some gear items to each player
            start_idx = i * 3
            end_idx = start_idx + 5
            
            for j, gear_item in enumerate(gear_items[start_idx:end_idx]):
                player_gear = PlayerGear.objects.create(
                    player=player,
                    gear_item=gear_item,
                    is_equipped=j < 3,  # First 3 items are equipped
                    is_favorite=j == 0,  # First item is favorite
                    mod_slots_used=0,
                    mod_slots_max=2,
                    notes=f"Test gear item {j+1}"
                )
                self.stdout.write(f'Created gear: {gear_item.name} for {player.in_game_name}')
        
        self.stdout.write(
            self.style.SUCCESS('✅ Test loadouts created successfully!')
        )
