#!/bin/bash

# Development Server Startup Script
# This script starts the Django development server with the dev settings

echo "🚀 Starting Warborne Tools Development Server..."

# Clear screen
clear

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull

# Kill any existing Django server processes
echo "🛑 Stopping existing Django servers..."
pkill -f runserver

# Set Django settings module for development
export DJANGO_SETTINGS_MODULE=warborne_tools.settings_dev

# Copy frontend environment file if it doesn't exist
if [ ! -f "frontend/warborne_frontend/.env" ]; then
    echo "📝 Creating frontend environment file..."
    cp frontend-dev.env frontend/warborne_frontend/.env
fi

# Start Django development server
echo "🏃 Starting Django development server..."
nohup python manage.py runserver 127.0.0.1:8000 > django.log 2>&1 &

# Wait a moment for the server to start
sleep 2

# Check if the server is running
echo "🔍 Checking server status..."
ps aux | grep runserver

echo "✅ Development server started!"
echo "📊 Server logs: tail -f django.log"
echo "🌐 Development URL: https://violenceguilddev.duckdns.org"
echo "📁 Django Admin: https://violenceguilddev.duckdns.org/admin/"
