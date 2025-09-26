from django.core.management.base import BaseCommand
from guilds.models import Player


class Command(BaseCommand):
    help = 'Fix player roles by assigning default roles to players with null or invalid roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--default-role',
            type=str,
            default='defensive_tank',
            help='Default role to assign to players with null or invalid roles (default: defensive_tank)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes'
        )

    def handle(self, *args, **options):
        default_role = options['default_role']
        dry_run = options['dry_run']
        
        # Valid roles from the Player model
        valid_roles = [choice[0] for choice in Player.GAME_ROLE_CHOICES]
        
        # Role mapping for common invalid roles
        role_mapping = {
            'tank': 'defensive_tank',
            'dps': 'ranged_dps',
            'support': 'offensive_support'
        }
        
        self.stdout.write(f"Valid roles: {valid_roles}")
        self.stdout.write(f"Default role: {default_role}")
        
        if default_role not in valid_roles:
            self.stdout.write(
                self.style.ERROR(f"Invalid default role '{default_role}'. Valid roles are: {valid_roles}")
            )
            return
        
        # Find players with null or invalid roles
        null_role_players = Player.objects.filter(game_role__isnull=True)
        invalid_role_players = Player.objects.exclude(game_role__in=valid_roles).exclude(game_role__isnull=True)
        
        self.stdout.write(f"\nPlayers with null roles: {null_role_players.count()}")
        self.stdout.write(f"Players with invalid roles: {invalid_role_players.count()}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN MODE - No changes will be made ==="))
        
        # Fix null roles
        if null_role_players.exists():
            self.stdout.write(f"\n=== Fixing {null_role_players.count()} players with null roles ===")
            for player in null_role_players:
                self.stdout.write(f"  {player.in_game_name} ({player.discord_name}) - Setting role to '{default_role}'")
                if not dry_run:
                    player.game_role = default_role
                    player.save()
        
        # Fix invalid roles
        if invalid_role_players.exists():
            self.stdout.write(f"\n=== Fixing {invalid_role_players.count()} players with invalid roles ===")
            for player in invalid_role_players:
                old_role = player.game_role
                new_role = role_mapping.get(old_role, default_role)
                self.stdout.write(f"  {player.in_game_name} ({player.discord_name}) - Changing role from '{old_role}' to '{new_role}'")
                if not dry_run:
                    player.game_role = new_role
                    player.save()
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN COMPLETE - No changes were made ==="))
        else:
            self.stdout.write(self.style.SUCCESS("\n=== Role fixes completed successfully ==="))
        
        # Show summary
        self.stdout.write(f"\n=== Summary ===")
        self.stdout.write(f"Players with null roles: {null_role_players.count()}")
        self.stdout.write(f"Players with invalid roles: {invalid_role_players.count()}")
        self.stdout.write(f"Total players fixed: {null_role_players.count() + invalid_role_players.count()}")
