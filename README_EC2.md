# Warborne Guild Tools - EC2 Deployment Guide

This guide explains how to deploy the Warborne Guild Tools Django application on AWS EC2.

## 🚀 Quick Start

### Prerequisites
- AWS EC2 instance (Ubuntu 20.04+ recommended)
- Security group with ports 22, 80, 443 open
- Domain name (optional, for SSL)

### Automated Deployment

1. **Connect to your EC2 instance:**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/warborne-guild-tools.git /app
   cd /app
   ```

3. **Run the deployment script:**
   ```bash
   chmod +x deploy_ec2.sh
   ./deploy_ec2.sh
   ```

4. **Configure environment variables:**
   ```bash
   nano /app/.env
   # Add your Discord bot tokens and other configuration
   ```

5. **Restart services:**
   ```bash
   sudo systemctl restart warborne-tools
   sudo systemctl restart nginx
   ```

## 🔧 Manual Setup

If you prefer manual setup, follow these steps:

### 1. System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv postgresql nginx supervisor git
```

### 2. Database Setup
```bash
sudo -u postgres psql
CREATE DATABASE warborne_tools;
CREATE USER warborne_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE warborne_tools TO warborne_user;
\q
```

### 3. Application Setup
```bash
cd /app
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Django Configuration
```bash
export DJANGO_SETTINGS_MODULE=warborne_tools.settings_ec2
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 5. Service Configuration
```bash
sudo cp warborne-tools.service /etc/systemd/system/
sudo systemctl enable warborne-tools
sudo systemctl start warborne-tools
```

### 6. Nginx Configuration
```bash
sudo cp nginx.conf /etc/nginx/sites-available/warborne-tools
sudo ln -s /etc/nginx/sites-available/warborne-tools /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## 📁 File Structure

```
/app/
├── warborne_tools/
│   ├── settings_ec2.py      # EC2-specific settings
│   └── ...
├── guilds/                   # Django app
├── static/                   # Static files
├── media/                    # Media files
├── logs/                     # Application logs
├── .env                      # Environment variables
├── Dockerfile               # Docker configuration
├── nginx.conf               # Nginx configuration
├── supervisor.conf          # Supervisor configuration
├── warborne-tools.service   # Systemd service
├── start_ec2.sh            # Startup script
└── deploy_ec2.sh           # Deployment script
```

## ⚙️ Configuration

### Environment Variables
Create `/app/.env` with the following variables:

```bash
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-ip

# Database
DB_NAME=warborne_tools
DB_USER=warborne_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Discord Bot
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_CLIENT_ID=your-client-id
DISCORD_CLIENT_SECRET=your-client-secret
BASE_URL=http://your-domain.com
```

### SSL Configuration (Optional)
To enable HTTPS, install Certbot and configure SSL:

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🔍 Monitoring

### View Logs
```bash
# Application logs
sudo journalctl -u warborne-tools -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Django logs
tail -f /app/logs/django.log
```

### Service Management
```bash
# Start/stop/restart services
sudo systemctl start warborne-tools
sudo systemctl stop warborne-tools
sudo systemctl restart warborne-tools

# Check status
sudo systemctl status warborne-tools
```

## 🚨 Troubleshooting

### Common Issues

1. **Database connection failed:**
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify database credentials in `.env`

2. **Static files not loading:**
   - Run: `python manage.py collectstatic --noinput`
   - Check Nginx configuration

3. **Permission denied:**
   - Fix permissions: `sudo chown -R www-data:www-data /app`

4. **Port already in use:**
   - Check what's using port 8000: `sudo netstat -tlnp | grep :8000`
   - Kill the process or change port

### Health Checks
```bash
# Check if application is running
curl http://localhost:8000/health/

# Check database connection
python manage.py dbshell

# Check static files
ls -la /app/staticfiles/
```

## 🔄 Updates

To update the application:

```bash
cd /app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart warborne-tools
```

## 🛡️ Security

- Change default admin password
- Use strong database passwords
- Enable firewall: `sudo ufw enable`
- Keep system updated: `sudo apt-get update && sudo apt-get upgrade`
- Use SSL certificates for HTTPS
- Regular backups of database and media files

## 📊 Performance

- Monitor memory usage: `htop`
- Check disk space: `df -h`
- Optimize database queries
- Use CDN for static files (optional)
- Enable gzip compression in Nginx

## 🆘 Support

For issues and support:
1. Check logs first
2. Verify configuration
3. Test database connection
4. Check service status
5. Review security groups and firewall rules
