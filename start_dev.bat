@echo off
REM Development Server Startup Script (Windows Batch)
REM This script starts the Django development server with the dev settings

echo 🚀 Starting Warborne Tools Development Server...

REM Clear screen
cls

REM Pull latest changes
echo 📥 Pulling latest changes...
git pull

REM Kill any existing Django server processes
echo 🛑 Stopping existing Django servers...
taskkill /f /im python.exe /fi "WINDOWTITLE eq *runserver*" 2>nul

REM Set Django settings module for development
set DJANGO_SETTINGS_MODULE=warborne_tools.settings_dev

REM Start Django development server
echo 🏃 Starting Django development server...
start /b python manage.py runserver 127.0.0.1:8000 > django.log 2>&1

REM Wait a moment for the server to start
timeout /t 3 /nobreak >nul

REM Check if the server is running
echo 🔍 Checking server status...
tasklist /fi "imagename eq python.exe"

echo ✅ Development server started!
echo 📊 Server logs: type django.log
echo 🌐 Development URL: https://violenceguilddev.duckdns.org
echo 📁 Django Admin: https://violenceguilddev.duckdns.org/admin/
pause
