#!/usr/bin/env python
"""
Test script to verify psycopg3 compatibility
"""
import os
import sys

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_production')

try:
    import django
    django.setup()
    
    from django.db import connection
    from django.core.management import execute_from_command_line
    
    print("✅ Django setup successful")
    print(f"✅ Python version: {sys.version}")
    
    # Test database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"✅ Database connection successful: {result}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    
    # Test collectstatic
    try:
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--dry-run'])
        print("✅ collectstatic test successful")
    except Exception as e:
        print(f"❌ collectstatic test failed: {e}")
        
except Exception as e:
    print(f"❌ Setup failed: {e}")
    sys.exit(1)

print("🎉 All tests passed!")
