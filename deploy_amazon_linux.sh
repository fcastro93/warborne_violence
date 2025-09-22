#!/bin/bash

# EC2 Deployment Script for Warborne Guild Tools - Amazon Linux
# This script sets up the Django application on an Amazon Linux EC2 instance

set -e

echo "🚀 Starting EC2 deployment for Warborne Guild Tools on Amazon Linux..."

# Update system packages
echo "📦 Updating system packages..."
sudo yum update -y

# Install required system packages
echo "🔧 Installing system dependencies..."
sudo yum install -y \
    python3.11 \
    python3.11-pip \
    postgresql15 \
    postgresql15-server \
    nginx \
    supervisor \
    git \
    curl \
    gcc \
    python3-devel \
    postgresql15-devel \
    openssl-devel \
    libffi-devel

# Start and enable PostgreSQL
echo "🗄️ Setting up PostgreSQL..."
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create application directory
echo "📁 Setting up application directory..."
sudo mkdir -p /app
sudo chown ec2-user:ec2-user /app
cd /app

# Clone repository (if not already present)
if [ ! -d "/app/.git" ]; then
    echo "📥 Cloning repository..."
    # Replace with your actual repository URL
    # git clone https://github.com/yourusername/warborne-guild-tools.git /app
    echo "⚠️  Please clone your repository to /app directory"
fi

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3.11 -m venv /app/venv
source /app/venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set up PostgreSQL database
echo "🗄️ Setting up PostgreSQL database..."
sudo -u postgres psql << EOF
CREATE DATABASE warborne_tools;
CREATE USER warborne_user WITH PASSWORD 'warborne_password';
GRANT ALL PRIVILEGES ON DATABASE warborne_tools TO warborne_user;
ALTER USER warborne_user CREATEDB;
\q
EOF

# Create environment file
echo "⚙️ Creating environment configuration..."
cat > /app/.env << EOF
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

DB_NAME=warborne_tools
DB_USER=warborne_user
DB_PASSWORD=warborne_password
DB_HOST=localhost
DB_PORT=5432

DISCORD_BOT_TOKEN=
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
BASE_URL=http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
EOF

# Set up Django application
echo "🔧 Setting up Django application..."
export DJANGO_SETTINGS_MODULE=warborne_tools.settings_ec2
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py load_game_data || echo "Game data loading failed or already loaded"

# Create superuser
echo "👤 Creating admin user..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@warborne.com', 'admin123')
    print('Admin user created: admin/admin123')
else:
    print('Admin user already exists')
EOF

# Set up Nginx
echo "🌐 Configuring Nginx..."
sudo cp nginx.conf /etc/nginx/conf.d/warborne-tools.conf
sudo rm -f /etc/nginx/conf.d/default.conf
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# Set up systemd service
echo "🔧 Setting up systemd service..."
sudo cp warborne-tools.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable warborne-tools
sudo systemctl start warborne-tools

# Set up supervisor (alternative to systemd)
echo "🔧 Setting up supervisor..."
sudo cp supervisor.conf /etc/supervisord.d/warborne-tools.ini
sudo systemctl start supervisord
sudo systemctl enable supervisord
sudo supervisorctl reread
sudo supervisorctl update

# Set proper permissions
echo "🔐 Setting up permissions..."
sudo chown -R ec2-user:ec2-user /app
sudo chmod -R 755 /app
sudo chmod +x /app/start_ec2.sh

# Configure firewall (if firewalld is running)
echo "🔥 Configuring firewall..."
if systemctl is-active --quiet firewalld; then
    sudo firewall-cmd --permanent --add-port=22/tcp
    sudo firewall-cmd --permanent --add-port=80/tcp
    sudo firewall-cmd --permanent --add-port=443/tcp
    sudo firewall-cmd --reload
fi

echo "✅ Deployment completed successfully!"
echo "🌐 Your application should be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "👤 Admin login: admin / admin123"
echo ""
echo "📋 Next steps:"
echo "1. Configure your Discord bot tokens in /app/.env"
echo "2. Set up SSL certificate for HTTPS (optional)"
echo "3. Configure domain name (optional)"
echo "4. Set up monitoring and backups"
