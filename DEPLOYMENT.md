# 🚀 Warborne Above Ashes - Deployment Guide

## 📋 Overview

This guide covers deploying the Warborne Above Ashes Django application with Discord bot integration to Koyeb.

## 🔧 Prerequisites

- Koyeb account
- GitHub repository with the code
- Discord bot token and credentials

## 🌐 Koyeb Deployment

### **Step 1: Set Environment Variables in Koyeb Dashboard**

Go to your Koyeb dashboard and set these environment variables:

```bash
# Django Settings
DJANGO_SETTINGS_MODULE=warborne.settings
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.koyeb.app,localhost,127.0.0.1
BASE_URL=https://your-domain.koyeb.app

# Discord Bot Credentials
DISCORD_BOT_TOKEN=your-bot-token-here
DISCORD_CLIENT_ID=your-client-id-here
DISCORD_CLIENT_SECRET=your-client-secret-here
```

### **Step 2: Deploy with koyeb.yaml**

The `koyeb.yaml` file is configured for multi-service deployment:

```yaml
services:
  web:
    run: python manage.py migrate && python manage.py create_bot_config && python manage.py runserver 0.0.0.0:$PORT
    env:
      - name: DJANGO_SETTINGS_MODULE
        value: warborne.settings
      - name: DATABASE_URL
        value: ${{KOYEB_POSTGRES_URL}}
      - name: SECRET_KEY
        value: ${{KOYEB_SECRET_KEY}}
      - name: ALLOWED_HOSTS
        value: ${{KOYEB_APP_DOMAIN}},localhost,127.0.0.1
      - name: BASE_URL
        value: https://${{KOYEB_APP_DOMAIN}}
      - name: DISCORD_BOT_TOKEN
        value: ${{DISCORD_BOT_TOKEN}}
      - name: DISCORD_CLIENT_ID
        value: ${{DISCORD_CLIENT_ID}}
      - name: DISCORD_CLIENT_SECRET
        value: ${{DISCORD_CLIENT_SECRET}}
    ports:
      - port: 8000
        targetPort: 8000
        protocol: http
```

### **Step 3: Deploy to Koyeb**

1. Connect your GitHub repository to Koyeb
2. Koyeb will automatically detect the `koyeb.yaml` file
3. The deployment will:
   - Run database migrations
   - Create Discord bot configuration
   - Start the Django server with Discord bot integration

## 🏠 Local Development

### **Step 1: Environment Setup**

Create a `.env` file:

```bash
# Discord Bot Credentials
DISCORD_BOT_TOKEN=your-bot-token-here
DISCORD_CLIENT_ID=your-client-id-here
DISCORD_CLIENT_SECRET=your-client-secret-here

# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/warborne_db
BASE_URL=http://127.0.0.1:8000
```

### **Step 2: Install Dependencies**

```bash
pip install -r requirements.txt
```

### **Step 3: Database Setup**

```bash
python manage.py migrate
python manage.py create_bot_config
```

### **Step 4: Run Development Server**

```bash
python manage.py runserver
```

## 🤖 Discord Bot Management

### **Django Admin Panel**

1. Go to `/admin/`
2. Navigate to "Discord Bot Configurations"
3. Create or edit the bot configuration
4. Use the admin actions to start/stop/restart the bot

### **Bot Management Dashboard**

1. Go to `/guilds/bot/management/`
2. View bot status and configuration
3. Use the control buttons to manage the bot

### **Available Commands**

- `/buildplayer <name>` - Get player loadout link
- `/guildinfo` - Get guild information
- `/playerlist [guild_name]` - List players
- `/drifters` - List available drifters
- `/gear [type]` - List gear items
- `/help` - Show help

## 🔒 Security Notes

- **Never commit sensitive credentials to Git**
- All tokens and secrets are stored in environment variables
- The bot starts in an "off" state by default
- Bot management is restricted to staff members only

## 📝 Troubleshooting

### **Bot Not Starting**

1. Check environment variables are set correctly
2. Verify Discord bot token is valid
3. Check bot permissions in Discord
4. Review error messages in Django Admin

### **Database Issues**

1. Ensure DATABASE_URL is correctly formatted
2. Run migrations: `python manage.py migrate`
3. Check database connectivity

### **Deployment Issues**

1. Verify all environment variables are set in Koyeb
2. Check Koyeb logs for errors
3. Ensure the `koyeb.yaml` file is correct

## 🎯 Next Steps

1. Set up your Discord bot in the Discord Developer Portal
2. Configure environment variables in Koyeb
3. Deploy the application
4. Test the Discord bot functionality
5. Configure bot permissions and invite to your server
