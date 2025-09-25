# Development Server Startup Script (PowerShell)
# This script starts the Django development server with the dev settings

Write-Host "🚀 Starting Warborne Tools Development Server..." -ForegroundColor Green

# Clear screen
Clear-Host

# Pull latest changes
Write-Host "📥 Pulling latest changes..." -ForegroundColor Blue
git pull

# Kill any existing Django server processes
Write-Host "🛑 Stopping existing Django servers..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -like "*python*" -and $_.CommandLine -like "*runserver*"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Set Django settings module for development
$env:DJANGO_SETTINGS_MODULE = "warborne_tools.settings_dev"

# Copy frontend environment file if it doesn't exist
if (-not (Test-Path "frontend/warborne_frontend/.env")) {
    Write-Host "📝 Creating frontend environment file..." -ForegroundColor Blue
    Copy-Item "frontend-dev.env" "frontend/warborne_frontend/.env"
}

# Start Django development server
Write-Host "🏃 Starting Django development server..." -ForegroundColor Blue
Start-Process python -ArgumentList "manage.py", "runserver", "127.0.0.1:8000" -WindowStyle Hidden -RedirectStandardOutput "django.log" -RedirectStandardError "django_error.log"

# Wait a moment for the server to start
Start-Sleep -Seconds 3

# Check if the server is running
Write-Host "🔍 Checking server status..." -ForegroundColor Blue
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

Write-Host "✅ Development server started!" -ForegroundColor Green
Write-Host "📊 Server logs: Get-Content django.log -Wait" -ForegroundColor Cyan
Write-Host "🌐 Development URL: https://violenceguilddev.duckdns.org" -ForegroundColor Cyan
Write-Host "📁 Django Admin: https://violenceguilddev.duckdns.org/admin/" -ForegroundColor Cyan
