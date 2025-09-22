#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting Warborne Guild Tools (Django + React + Nginx)..."

# Set production settings
export DJANGO_SETTINGS_MODULE=warborne_tools.settings_production

# Function to wait for database
wait_for_database() {
    echo "⏳ Waiting for database connection..."
    python -c "
import os
import time
import django
from django.conf import settings
from django.db import connections
from django.core.exceptions import ImproperlyConfigured

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_production')
django.setup()

# Wait for database connection
max_attempts = 30
attempt = 0
while attempt < max_attempts:
    try:
        db_conn = connections['default']
        db_conn.cursor()
        print('✅ Database connection successful!')
        break
    except Exception as e:
        attempt += 1
        print(f'❌ Database connection attempt {attempt}/{max_attempts} failed: {e}')
        if attempt < max_attempts:
            time.sleep(2)
        else:
            print('💥 Max database connection attempts reached. Exiting.')
            exit(1)
"
}

# Function to setup Django
setup_django() {
    echo "🔧 Setting up Django..."
    
    # Run migrations
    echo "📊 Running database migrations..."
    python manage.py migrate --noinput
    
    # Collect static files
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput
    
    # Load game data from fixtures (if needed)
    echo "🎮 Loading game data from fixtures..."
    python manage.py load_game_data || echo "⚠️ Game data loading failed or already loaded"
    
    # Create superuser if it doesn't exist
    echo "👤 Checking for admin user..."
    python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@warborne.com', 'admin123')
    print('✅ Admin user created: admin/admin123')
else:
    print('✅ Admin user already exists')
EOF
    
    # Create bot config if needed
    echo "🤖 Creating bot configuration..."
    python manage.py create_bot_config || echo "⚠️ Bot config already exists"
}

# Function to start Django server
start_django() {
    echo "🐍 Starting Django server..."
    gunicorn warborne_tools.wsgi:application \
        --bind 127.0.0.1:8000 \
        --workers 2 \
        --worker-class sync \
        --worker-connections 1000 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --timeout 30 \
        --keep-alive 2 \
        --daemon \
        --access-logfile logs/django_access.log \
        --error-logfile logs/django_error.log \
        --log-level info
}

# Function to start Nginx
start_nginx() {
    echo "🌐 Starting Nginx..."
    # Test nginx configuration
    nginx -t
    
    # Start nginx in foreground
    echo "✅ Starting Nginx in foreground..."
    exec nginx -g "daemon off;"
}

# Main execution
main() {
    echo "🎯 Initializing Warborne Guild Tools..."
    
    # Wait for database
    wait_for_database
    
    # Setup Django
    setup_django
    
    # Start Django server
    start_django
    
    # Start Nginx (this will run in foreground)
    start_nginx
}

# Handle shutdown gracefully
cleanup() {
    echo "🛑 Shutting down gracefully..."
    # Kill Django process
    pkill -f gunicorn || true
    # Kill Nginx process
    pkill -f nginx || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Run main function
main
