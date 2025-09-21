# Warborne Guild Tools

A Django web application for managing guild members, player loadouts, and gear tracking for the Warborne: Above Ashes game.

## Features

### 🏰 Guild Management
- Create and manage multiple guilds
- Track guild members with in-game and Discord names
- Organize players by factions (Emberwild Magnates, Ashen Ironcreed, Sirius Shroud)

### 🎮 Player Loadouts
- **Public View**: Shareable loadout links for viewing player builds
- **Staff Management**: Full loadout editing capabilities for administrators
- **3 Drifter Slots**: Each player can have up to 3 drifters equipped
- **Gear System**: Complete gear tracking with 9 slots per drifter:
  - 1 Weapon
  - 1 Helmet  
  - 1 Chest
  - 1 Boots
  - 1 Consumable
  - 4 Mods

### ⚔️ Game Data Integration
- **Comprehensive Database**: All weapons, armor, mods, and drifters from the game
- **Visual Interface**: High-quality icons and images for all items
- **Advanced Filtering**: Search and filter by rarity, type, and attributes
- **Real-time Stats**: Dynamic stat calculations and display

### 🔒 Security
- **Public Access**: Anyone can view loadouts via shareable links
- **Staff Protection**: Only authenticated staff can modify data
- **CSRF Protection**: All forms protected against cross-site attacks

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL (for production) or SQLite (for development)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd warborne-guild-tools
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-local.txt
   ```

4. **Set up database**
   ```bash
   python manage.py migrate --settings=warborne_tools.settings_local
   ```

5. **Import game data**
   ```bash
   python manage.py import_complete_data --settings=warborne_tools.settings_local
   ```

6. **Create admin user**
   ```bash
   python manage.py createsuperuser --settings=warborne_tools.settings_local
   ```

7. **Run development server**
   ```bash
   python manage.py runserver --settings=warborne_tools.settings_local
   ```

8. **Access the application**
   - Admin: http://127.0.0.1:8000/admin/
   - Player Loadout: http://127.0.0.1:8000/guilds/player/1/loadout/

## Usage

### For Guild Administrators
1. **Access Admin Panel**: Log in at `/admin/`
2. **Create Guilds**: Add new guilds with faction assignments
3. **Add Players**: Create player profiles with in-game and Discord names
4. **Assign Drifters**: Set up drifters for each player slot
5. **Manage Loadouts**: Equip gear and mods for each drifter

### For Public Users
1. **View Loadouts**: Access any player loadout via direct link
2. **Browse Items**: Explore the complete database of game items
3. **Share Builds**: Copy and share loadout URLs with others

## Data Sources

This project integrates data from multiple Warborne repositories:
- **Game Data**: Complete item database with stats and descriptions
- **Icons**: High-resolution images for all items and drifters
- **Localization**: Multi-language support (English, Spanish, Russian)

## Project Structure

```
warborne-guild-tools/
├── guilds/                    # Main Django app
│   ├── models.py             # Database models
│   ├── views.py              # View logic
│   ├── admin.py              # Admin interface
│   ├── templates/            # HTML templates
│   └── management/commands/  # Custom Django commands
├── warborne_tools/           # Django project settings
├── static/                   # Static files (icons, CSS, JS)
├── repos/                    # Game data repositories
└── requirements.txt          # Python dependencies
```

## Deployment

### Koyeb Deployment
The project includes a `koyeb.yaml` configuration for easy deployment to Koyeb.

### Environment Variables
Create a `.env` file with the following variables:
```env
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=your-postgresql-url
ALLOWED_HOSTS=your-domain.com
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and personal use. Game data belongs to the Warborne: Above Ashes developers.

## Support

For issues or questions, please create an issue in the repository or contact the development team.