#!/bin/bash

# Exit on any error
set -e

echo "Starting Warborne Guild Tools on EC2..."

# Set production settings
export DJANGO_SETTINGS_MODULE=warborne_tools.settings_ec2

# Wait for database to be available
echo "Waiting for database connection..."
python -c "
import os
import time
import django
from django.conf import settings
from django.db import connections
from django.core.exceptions import ImproperlyConfigured

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_ec2')
django.setup()

# Wait for database connection
max_attempts = 30
attempt = 0
while attempt < max_attempts:
    try:
        db_conn = connections['default']
        db_conn.cursor()
        print('Database connection successful!')
        break
    except Exception as e:
        attempt += 1
        print(f'Database connection attempt {attempt}/{max_attempts} failed: {e}')
        if attempt < max_attempts:
            time.sleep(2)
        else:
            print('Max database connection attempts reached. Exiting.')
            exit(1)
"

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Load game data from fixtures (if not already loaded)
echo "Loading game data from fixtures..."
python manage.py load_game_data || echo "Game data loading failed or already loaded"

# Create superuser if it doesn't exist
echo "Checking for admin user..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@warborne.com', 'admin123')
    print('Admin user created: admin/admin123')
else:
    print('Admin user already exists')
EOF

# Start the application with Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 warborne_tools.wsgi:application
