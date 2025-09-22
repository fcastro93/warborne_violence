import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from guilds.models import Drifter

class Command(BaseCommand):
    help = 'Import real drifter data from repositories'

    def handle(self, *args, **options):
        self.stdout.write('Importing real drifter data from repositories...')
        
        # Base path to repositories
        repos_path = os.path.join(settings.BASE_DIR, 'repos', 'warborne-data-json')
        
        if not os.path.exists(repos_path):
            self.stdout.write(self.style.ERROR(f'Repository path not found: {repos_path}'))
            return
        
        # Import drifters from all files
        drifter_files = ['str_drifter.json', 'dex_drifter.json', 'int_drifter.json', 'gather_drifter.json']
        imported_count = 0
        
        for drifter_file in drifter_files:
            file_path = os.path.join(repos_path, 'drifters', drifter_file)
            
            if not os.path.exists(file_path):
                self.stdout.write(f'Warning: {file_path} not found')
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process drifters from this file
            if 'drifters' in data:
                for drifter_id, drifter_data in data['drifters'].items():
                    if not isinstance(drifter_data, dict):
                        continue
                    
                    drifter_name = drifter_data.get('name', '')
                    if not drifter_name:
                        continue
                    
                    # Extract real stats (handle empty strings)
                    base_str = int(drifter_data.get('baseStr', 0)) if drifter_data.get('baseStr', '').strip() else 0
                    base_dex = int(drifter_data.get('baseDex', 0)) if drifter_data.get('baseDex', '').strip() else 0
                    base_int = int(drifter_data.get('baseInt', 0)) if drifter_data.get('baseInt', '').strip() else 0
                    
                    # Calculate derived stats
                    base_health = (base_str * 10) + (base_dex * 5) + (base_int * 3)
                    base_energy = (base_str * 2) + (base_dex * 3) + (base_int * 10)
                    base_damage = (base_str * 2) + (base_dex * 1.5) + (base_int * 1)
                    base_defense = (base_str * 1.5) + (base_dex * 1) + (base_int * 0.5)
                    base_speed = (base_str * 1) + (base_dex * 2) + (base_int * 1)
                    
                    # Extract support station bonus info
                    support_info = drifter_data.get('supportStationBonus', {})
                    support_bonus = support_info.get('supportBonus', '')
                    support_malus = support_info.get('supportMalus', '')
                    
                    # Create description from stats
                    stats = drifter_data.get('stats', {})
                    stat_descriptions = []
                    for stat_name, stat_value in list(stats.items())[:5]:  # First 5 stats
                        stat_descriptions.append(f"{stat_name}: {stat_value}")
                    
                    description = f"Support Bonus: {support_bonus} | Support Malus: {support_malus}\n" + "\n".join(stat_descriptions)
                    
                    # Create drifter
                    drifter, created = Drifter.objects.get_or_create(
                        name=drifter_name,
                        defaults={
                            'description': description,
                            'base_health': int(base_health),
                            'base_energy': int(base_energy),
                            'base_damage': int(base_damage),
                            'base_defense': int(base_defense),
                            'base_speed': int(base_speed),
                            'special_abilities': f"STR: {base_str}, DEX: {base_dex}, INT: {base_int}",
                            'is_active': True
                        }
                    )
                    
                    if created:
                        imported_count += 1
                        self.stdout.write(f'  Created drifter: {drifter_name}')
                    else:
                        self.stdout.write(f'  Already exists: {drifter_name}')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Imported {imported_count} new drifters with real data!'))
        self.stdout.write(f'Total drifters available: {Drifter.objects.count()}')
