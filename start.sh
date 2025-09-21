#!/bin/bash

# Exit on any error
set -e

echo "Starting Warborne Guild Tools..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Import game data (only if not already imported)
echo "Setting up game data..."
python manage.py import_complete_data || echo "Game data already imported or import failed"

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

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 warborne_tools.wsgi:application
