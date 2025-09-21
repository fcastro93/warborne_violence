#!/usr/bin/env python
"""
Script para verificar la conexión a la base de datos de producción
desde el entorno local.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_local')

# Setup Django
django.setup()

def test_database_connection():
    """Test the database connection and show basic info"""
    try:
        from django.db import connection
        from django.core.management import execute_from_command_line
        
        print("🔍 Testing database connection...")
        print(f"📊 Using settings: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
        print(f"🗄️ Database engine: {connection.settings_dict['ENGINE']}")
        print(f"🏠 Database host: {connection.settings_dict['HOST']}")
        print(f"📝 Database name: {connection.settings_dict['NAME']}")
        
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()
            print(f"✅ PostgreSQL version: {db_version[0]}")
            
            # Get basic stats
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes
                FROM pg_stat_user_tables 
                ORDER BY n_tup_ins DESC 
                LIMIT 5;
            """)
            tables = cursor.fetchall()
            
            print("\n📈 Top 5 tables by activity:")
            for table in tables:
                print(f"  - {table[0]}.{table[1]}: {table[2]} inserts")
            
            # Check if our models exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('guilds_player', 'guilds_guild', 'guilds_event', 'guilds_recommendedbuild')
                ORDER BY table_name;
            """)
            our_tables = cursor.fetchall()
            
            print("\n🏗️ Our Django models in database:")
            for table in our_tables:
                print(f"  ✅ {table[0]}")
                
            if len(our_tables) < 4:
                print("  ⚠️ Some tables might be missing. Run migrations if needed.")
        
        print("\n🎉 Database connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def show_sample_data():
    """Show some sample data from the database"""
    try:
        from guilds.models import Player, Guild, Event, RecommendedBuild
        
        print("\n📊 Sample data from database:")
        
        # Players
        player_count = Player.objects.count()
        print(f"👥 Players: {player_count}")
        if player_count > 0:
            recent_players = Player.objects.order_by('-created_at')[:3]
            for player in recent_players:
                guild_name = player.guild.name if player.guild else "No Guild"
                print(f"  - {player.in_game_name} (Guild: {guild_name})")
        
        # Guilds
        guild_count = Guild.objects.count()
        print(f"🏰 Guilds: {guild_count}")
        if guild_count > 0:
            guilds = Guild.objects.filter(is_active=True)[:3]
            for guild in guilds:
                member_count = guild.players.count()
                print(f"  - {guild.name} ({member_count} members)")
        
        # Events
        event_count = Event.objects.count()
        print(f"📅 Events: {event_count}")
        if event_count > 0:
            recent_events = Event.objects.order_by('-created_at')[:3]
            for event in recent_events:
                print(f"  - {event.title} ({event.event_date.strftime('%Y-%m-%d')})")
        
        # Recommended Builds
        build_count = RecommendedBuild.objects.count()
        print(f"📚 Recommended Builds: {build_count}")
        
    except Exception as e:
        print(f"❌ Error showing sample data: {e}")

if __name__ == "__main__":
    print("🚀 Warborne Tools - Database Connection Test")
    print("=" * 50)
    
    if test_database_connection():
        show_sample_data()
        print("\n✅ Ready to develop with production data!")
        print("\n💡 Next steps:")
        print("  1. Run: python manage.py runserver --settings=warborne_tools.settings_local")
        print("  2. Visit: http://localhost:8000/guilds/dashboard/")
        print("  3. Access Django Admin: http://localhost:8000/admin/")
    else:
        print("\n❌ Please check your database configuration.")
        print("Make sure you have:")
        print("  - psycopg installed: pip install psycopg[binary]")
        print("  - Correct database credentials")
        print("  - Network access to the database host")
