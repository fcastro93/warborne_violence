from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from guilds.models import Guild, Player, GearType, GearItem, GearMod
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create sample users
        users_data = [
            {'username': 'admin', 'email': 'admin@warborne.com', 'first_name': 'Admin', 'last_name': 'User'},
            {'username': 'player1', 'email': 'player1@warborne.com', 'first_name': 'Player', 'last_name': 'One'},
            {'username': 'player2', 'email': 'player2@warborne.com', 'first_name': 'Player', 'last_name': 'Two'},
            {'username': 'player3', 'email': 'player3@warborne.com', 'first_name': 'Player', 'last_name': 'Three'},
        ]
        
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'User created: {user.username}')
        
        # Create sample guilds
        guilds_data = [
            {'name': 'Warborne Warriors', 'tag': '[WAR]', 'faction': 'emberwild'},
            {'name': 'Ashes Alliance', 'tag': '[ASH]', 'faction': 'ashen'},
            {'name': 'Iron Legion', 'tag': '[IRON]', 'faction': 'ironcreed'},
            {'name': 'Shadow Operatives', 'tag': '[SHADOW]', 'faction': 'shroud'},
        ]
        
        for guild_data in guilds_data:
            guild, created = Guild.objects.get_or_create(
                name=guild_data['name'],
                defaults=guild_data
            )
            if created:
                self.stdout.write(f'Guild created: {guild.name}')
        
        # Create gear types
        gear_types_data = [
            {'name': 'Assault Rifle', 'category': 'weapon'},
            {'name': 'Pistol', 'category': 'weapon'},
            {'name': 'Light Armor', 'category': 'armor'},
            {'name': 'Heavy Armor', 'category': 'armor'},
            {'name': 'Helmet', 'category': 'armor'},
            {'name': 'Boots', 'category': 'armor'},
            {'name': 'Ring', 'category': 'accessory'},
            {'name': 'Amulet', 'category': 'accessory'},
            {'name': 'Combat Vehicle', 'category': 'vehicle'},
            {'name': 'Grenade', 'category': 'tactical'},
            {'name': 'Damage Mod', 'category': 'mod'},
            {'name': 'Defense Mod', 'category': 'mod'},
        ]
        
        for gear_type_data in gear_types_data:
            gear_type, created = GearType.objects.get_or_create(
                name=gear_type_data['name'],
                defaults=gear_type_data
            )
            if created:
                self.stdout.write(f'Gear type created: {gear_type.name}')
        
        # Create gear items
        gear_items_data = [
            # Weapons
            {'name': 'Assault Rifle MK-1', 'gear_type': 'Assault Rifle', 'rarity': 'common', 'required_level': 1, 'damage': 50},
            {'name': 'Assault Rifle MK-2', 'gear_type': 'Assault Rifle', 'rarity': 'uncommon', 'required_level': 5, 'damage': 75},
            {'name': 'Assault Rifle MK-3', 'gear_type': 'Assault Rifle', 'rarity': 'rare', 'required_level': 10, 'damage': 100},
            {'name': 'Laser Pistol', 'gear_type': 'Pistol', 'rarity': 'common', 'required_level': 1, 'damage': 30},
            {'name': 'Plasma Pistol', 'gear_type': 'Pistol', 'rarity': 'epic', 'required_level': 15, 'damage': 80},
            
            # Armor
            {'name': 'Basic Light Armor', 'gear_type': 'Light Armor', 'rarity': 'common', 'required_level': 1, 'defense': 25},
            {'name': 'Advanced Light Armor', 'gear_type': 'Light Armor', 'rarity': 'uncommon', 'required_level': 5, 'defense': 40},
            {'name': 'Military Heavy Armor', 'gear_type': 'Heavy Armor', 'rarity': 'rare', 'required_level': 10, 'defense': 80},
            {'name': 'Combat Helmet', 'gear_type': 'Helmet', 'rarity': 'common', 'required_level': 1, 'defense': 15},
            {'name': 'Combat Boots', 'gear_type': 'Boots', 'rarity': 'common', 'required_level': 1, 'defense': 10},
            
            # Accessories
            {'name': 'Power Ring', 'gear_type': 'Ring', 'rarity': 'rare', 'required_level': 8, 'health_bonus': 50},
            {'name': 'Protection Amulet', 'gear_type': 'Amulet', 'rarity': 'epic', 'required_level': 12, 'defense': 30},
            
            # Vehicles
            {'name': 'Alpha Combat Vehicle', 'gear_type': 'Combat Vehicle', 'rarity': 'rare', 'required_level': 15, 'health_bonus': 200},
            
            # Tactical
            {'name': 'Fragmentation Grenade', 'gear_type': 'Grenade', 'rarity': 'common', 'required_level': 3, 'damage': 150},
        ]
        
        for item_data in gear_items_data:
            gear_type = GearType.objects.get(name=item_data['gear_type'])
            gear_item, created = GearItem.objects.get_or_create(
                name=item_data['name'],
                defaults={
                    'gear_type': gear_type,
                    'rarity': item_data['rarity'],
                    'required_level': item_data['required_level'],
                    'damage': item_data.get('damage', 0),
                    'defense': item_data.get('defense', 0),
                    'health_bonus': item_data.get('health_bonus', 0),
                    'energy_bonus': item_data.get('energy_bonus', 0),
                }
            )
            if created:
                self.stdout.write(f'Gear item created: {gear_item.name}')
        
        # Create mods
        mods_data = [
            {'name': 'Basic Damage Mod', 'mod_type': 'damage', 'rarity': 'rare', 'damage_bonus': 10},
            {'name': 'Advanced Damage Mod', 'mod_type': 'damage', 'rarity': 'epic', 'damage_bonus': 25},
            {'name': 'Legendary Damage Mod', 'mod_type': 'damage', 'rarity': 'legendary', 'damage_bonus': 50},
            {'name': 'Basic Defense Mod', 'mod_type': 'defense', 'rarity': 'rare', 'defense_bonus': 15},
            {'name': 'Advanced Defense Mod', 'mod_type': 'defense', 'rarity': 'epic', 'defense_bonus': 35},
            {'name': 'Health Mod', 'mod_type': 'health', 'rarity': 'rare', 'health_bonus': 100},
            {'name': 'Energy Mod', 'mod_type': 'energy', 'rarity': 'rare', 'energy_bonus': 50},
            {'name': 'Speed Mod', 'mod_type': 'speed', 'rarity': 'epic', 'speed_bonus': 20},
        ]
        
        for mod_data in mods_data:
            mod, created = GearMod.objects.get_or_create(
                name=mod_data['name'],
                defaults=mod_data
            )
            if created:
                self.stdout.write(f'Mod created: {mod.name}')
        
        # Create sample players
        players_data = [
            {'user': 'player1', 'in_game_name': 'Warrior1', 'guild': 'Warborne Warriors', 'role': 'leader', 'character_level': 15},
            {'user': 'player2', 'in_game_name': 'Ashes2', 'guild': 'Ashes Alliance', 'role': 'leader', 'character_level': 12},
            {'user': 'player3', 'in_game_name': 'Fighter3', 'guild': 'Warborne Warriors', 'role': 'officer', 'character_level': 10},
        ]
        
        for player_data in players_data:
            user = User.objects.get(username=player_data['user'])
            guild = Guild.objects.get(name=player_data['guild'])
            player, created = Player.objects.get_or_create(
                user=user,
                defaults={
                    'in_game_name': player_data['in_game_name'],
                    'guild': guild,
                    'role': player_data['role'],
                    'character_level': player_data['character_level'],
                    'faction': guild.faction,
                    'joined_guild_at': timezone.now(),
                }
            )
            if created:
                self.stdout.write(f'Player created: {player.in_game_name}')
        
        self.stdout.write(
            self.style.SUCCESS('Sample data created successfully!')
        )
        self.stdout.write('Users created: admin, player1, player2, player3 (password: password123)')
        self.stdout.write('Guilds created: Warborne Warriors, Ashes Alliance')
        self.stdout.write('Visit /admin/ to see all data')
