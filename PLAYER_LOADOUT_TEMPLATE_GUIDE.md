# Player Loadout Template Guide

## 📋 Overview

This guide explains how the player loadout page template works in the Warborne Guild Tools application, based on the live implementation at [https://strategic-brena-charfire-afecfd9e.koyeb.app/guilds/player/5/loadout](https://strategic-brena-charfire-afecfd9e.koyeb.app/guilds/player/5/loadout).

## 🗂️ File Structure

### Core Template Files
```
guilds/
├── templates/
│   └── guilds/
│       ├── player_loadout.html          # Main loadout template (2,449 lines)
│       ├── recommended_build_view.html  # Recommended builds template (539 lines)
│       └── base.html                    # Base template
├── views.py                            # View logic (759 lines)
├── urls.py                             # URL routing (27 lines)
├── models.py                           # Database models (756 lines)
└── admin.py                            # Admin interface (548 lines)
```

## 🔗 URL Routing

### URL Configuration (`guilds/urls.py`)
```python
# Player loadout URL pattern
path('player/<int:player_id>/loadout/', views.player_loadout_view, name='player_loadout')
```

### URL Structure
- **Pattern**: `/guilds/player/{id}/loadout/`
- **View Function**: `player_loadout_view`
- **Template**: `guilds/player_loadout.html`
- **Example**: `/guilds/player/5/loadout/` → Player ID 5 loadout page

## 🎯 View Logic (`guilds/views.py`)

### Main View Function
```python
def player_loadout_view(request, player_id):
    """
    Display player loadout page with:
    - Player information
    - Drifter loadouts (up to 3)
    - Gear inventory
    - Equipment management
    """
    # Get player data
    player = get_object_or_404(Player, id=player_id)
    
    # Get player's drifters
    drifters = [player.drifter_1, player.drifter_2, player.drifter_3]
    
    # Get player's gear items
    player_gear = PlayerGear.objects.filter(player=player)
    
    # Get gear by category
    gear_by_category = {
        'weapon': GearItem.objects.filter(gear_type__category='weapon'),
        'helmet': GearItem.objects.filter(gear_type__category='armor'),
        'chest': GearItem.objects.filter(gear_type__category='armor'),
        'boots': GearItem.objects.filter(gear_type__category='armor'),
        'consumable': GearItem.objects.filter(gear_type__category='accessory'),
        'mod': GearItem.objects.filter(gear_type__category='mod'),
    }
    
    context = {
        'player': player,
        'drifters': drifters,
        'player_gear': player_gear,
        'gear_by_category': gear_by_category,
    }
    
    return render(request, 'guilds/player_loadout.html', context)
```

## 🎨 Template Structure (`guilds/player_loadout.html`)

### Template Sections (2,449 lines)

#### 1. Player Header Section
```html
<!-- Player Information -->
<div class="player-header">
    <h1>{{ player.in_game_name }} ✏️</h1>
    <div class="player-info">
        <p><strong>Discord:</strong> {{ player.discord_name }}</p>
        <p><strong>Guild:</strong> {{ player.guild.name|default:"No guild" }}</p>
        <p><strong>Level:</strong> {{ player.character_level }}</p>
        <p><strong>Faction:</strong> {{ player.get_faction_display }}</p>
        <p><strong>Guild Rank:</strong> {{ player.get_role_display }}</p>
        <p><strong>Role:</strong> {{ player.get_game_role_display|default:"Not set" }}</p>
    </div>
</div>
```

#### 2. Drifter Loadout Sections
```html
<!-- Drifter Loadouts (up to 3) -->
<div class="drifter-loadouts">
    {% for drifter in drifters %}
        <div class="drifter-section">
            <h3>{{ drifter.name|default:"No drifter assigned" }}</h3>
            
            <!-- Drifter Stats -->
            <div class="drifter-stats">
                <div class="stat">Health: {{ drifter.base_health }}</div>
                <div class="stat">Energy: {{ drifter.base_energy }}</div>
                <div class="stat">Damage: {{ drifter.base_damage }}</div>
                <div class="stat">Defense: {{ drifter.base_defense }}</div>
                <div class="stat">Speed: {{ drifter.base_speed }}</div>
            </div>
            
            <!-- Equipment Slots (9 slots) -->
            <div class="equipment-slots">
                <div class="slot weapon-slot">⚔️ Weapon</div>
                <div class="slot helmet-slot">🪖 Helmet</div>
                <div class="slot chest-slot">🛡️ Chest</div>
                <div class="slot boots-slot">👢 Boots</div>
                <div class="slot consumable-slot">🧪 Consumable</div>
                <div class="slot mod-slot">⚪ Mod 1</div>
                <div class="slot mod-slot">⚪ Mod 2</div>
                <div class="slot mod-slot">⚪ Mod 3</div>
                <div class="slot mod-slot">⚪ Mod 4</div>
            </div>
        </div>
    {% endfor %}
</div>
```

#### 3. Gear Inventory Section
```html
<!-- Gear Inventory -->
<div class="gear-inventory">
    <h3>Game Items</h3>
    
    <!-- Category Filters -->
    <div class="gear-filters">
        <button class="filter-btn" data-category="boots">Boots</button>
        <button class="filter-btn" data-category="chest">Chest</button>
        <button class="filter-btn" data-category="consumable">Consumable</button>
        <button class="filter-btn" data-category="helmet">Helmet</button>
        <button class="filter-btn" data-category="mod">Mod</button>
        <button class="filter-btn" data-category="weapon">Weapon</button>
    </div>
    
    <!-- Rarity Filters -->
    <div class="rarity-filters">
        <button class="rarity-btn" data-rarity="all">All</button>
        <button class="rarity-btn" data-rarity="rare">Rare</button>
        <button class="rarity-btn" data-rarity="epic">Epic</button>
        <button class="rarity-btn" data-rarity="legendary">Legendary</button>
    </div>
    
    <!-- Stat Filters -->
    <div class="stat-filters">
        <button class="stat-btn" data-stat="strength">💪 Strength</button>
        <button class="stat-btn" data-stat="agility">🏃 Agility</button>
        <button class="stat-btn" data-stat="intelligence">🧠 Intelligence</button>
    </div>
</div>
```

#### 4. Gear Item Display
```html
<!-- Gear Items by Category -->
{% for category, items in gear_by_category.items %}
    <div class="gear-category" data-category="{{ category }}">
        {% for item in items %}
            <div class="gear-item" 
                 data-rarity="{{ item.rarity }}"
                 data-stats="{{ item.detailed_stats|default:'' }}">
                
                <!-- Item Name and Skill -->
                <div class="item-name">{{ item.base_name }}</div>
                {% if item.skill_name %}
                    <div class="skill-name">{{ item.skill_name }}</div>
                {% endif %}
                
                <!-- Item Type and Rarity -->
                <div class="item-type">{{ item.gear_type.get_category_display }} • {{ item.get_rarity_display }}</div>
                
                <!-- Item Stats -->
                <div class="item-stats">
                    {% if item.damage > 0 %}
                        <div class="stat">Damage & Heal bonus: {{ item.damage }}%</div>
                    {% endif %}
                    {% if item.health_bonus > 0 %}
                        <div class="stat">HP: +{{ item.health_bonus }}</div>
                    {% endif %}
                    {% if item.armor > 0 %}
                        <div class="stat">Armor: {{ item.armor }}</div>
                    {% endif %}
                    {% if item.magic_resistance > 0 %}
                        <div class="stat">Magic resistance: {{ item.magic_resistance }}</div>
                    {% endif %}
                </div>
                
                <!-- Equipped Status -->
                {% if item in player_gear %}
                    <div class="equipped-status">Equipped</div>
                {% endif %}
            </div>
        {% endfor %}
    </div>
{% endfor %}
```

## 🎨 CSS Styling

### Key CSS Classes
```css
/* Player Header */
.player-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
}

/* Drifter Sections */
.drifter-section {
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 20px;
    background: #f9f9f9;
}

/* Equipment Slots */
.equipment-slots {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-top: 15px;
}

.slot {
    border: 2px dashed #ccc;
    padding: 10px;
    text-align: center;
    border-radius: 5px;
    background: #f0f0f0;
}

/* Gear Items */
.gear-item {
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
    margin: 5px;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Rarity Colors */
.gear-item[data-rarity="rare"] {
    border-left: 4px solid #4CAF50;
}

.gear-item[data-rarity="epic"] {
    border-left: 4px solid #9C27B0;
}

.gear-item[data-rarity="legendary"] {
    border-left: 4px solid #FF9800;
}

/* Equipped Status */
.equipped-status {
    background: #4CAF50;
    color: white;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 12px;
    margin-top: 5px;
}
```

## ⚙️ JavaScript Functionality

### Interactive Features
```javascript
// Category Filtering
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const category = this.dataset.category;
        filterGearByCategory(category);
    });
});

// Rarity Filtering
document.querySelectorAll('.rarity-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const rarity = this.dataset.rarity;
        filterGearByRarity(rarity);
    });
});

// Stat Filtering
document.querySelectorAll('.stat-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const stat = this.dataset.stat;
        filterGearByStat(stat);
    });
});

// Filter Functions
function filterGearByCategory(category) {
    document.querySelectorAll('.gear-category').forEach(section => {
        if (category === 'all' || section.dataset.category === category) {
            section.style.display = 'block';
        } else {
            section.style.display = 'none';
        }
    });
}

function filterGearByRarity(rarity) {
    document.querySelectorAll('.gear-item').forEach(item => {
        if (rarity === 'all' || item.dataset.rarity === rarity) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}
```

## 🗄️ Database Models Integration

### Key Models Used
```python
# Player Model
class Player(models.Model):
    in_game_name = models.CharField(max_length=100, unique=True)
    discord_name = models.CharField(max_length=100, default="")
    character_level = models.IntegerField(default=1)
    faction = models.CharField(max_length=50, choices=FACTION_CHOICES)
    guild = models.ForeignKey(Guild, on_delete=models.SET_NULL, null=True)
    drifter_1 = models.ForeignKey(Drifter, related_name='drifter_1_players')
    drifter_2 = models.ForeignKey(Drifter, related_name='drifter_2_players')
    drifter_3 = models.ForeignKey(Drifter, related_name='drifter_3_players')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    game_role = models.CharField(max_length=20, choices=GAME_ROLE_CHOICES)

# Drifter Model
class Drifter(models.Model):
    name = models.CharField(max_length=100, unique=True)
    base_health = models.IntegerField(default=100)
    base_energy = models.IntegerField(default=100)
    base_damage = models.IntegerField(default=50)
    base_defense = models.IntegerField(default=25)
    base_speed = models.IntegerField(default=10)

# GearItem Model
class GearItem(models.Model):
    base_name = models.CharField(max_length=200)
    skill_name = models.CharField(max_length=200, blank=True)
    gear_type = models.ForeignKey(GearType, on_delete=models.CASCADE)
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES)
    damage = models.FloatField(default=0)
    health_bonus = models.IntegerField(default=0)
    armor = models.IntegerField(default=0)
    magic_resistance = models.IntegerField(default=0)
    detailed_stats = models.JSONField(null=True, blank=True)

# PlayerGear Model
class PlayerGear(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    gear_item = models.ForeignKey(GearItem, on_delete=models.CASCADE)
    equipped_on_drifter = models.IntegerField(choices=DRIFTER_CHOICES)
    is_equipped = models.BooleanField(default=False)
```

## 🔄 Data Flow

### 1. URL Request
```
User visits: /guilds/player/5/loadout/
↓
URL Router: guilds/urls.py
↓
View Function: player_loadout_view(request, player_id=5)
```

### 2. Data Retrieval
```
View queries database:
- Player.objects.get(id=5)
- PlayerGear.objects.filter(player=player)
- GearItem.objects.filter(gear_type__category='weapon')
- GearItem.objects.filter(gear_type__category='armor')
- etc.
```

### 3. Template Rendering
```
View passes context to template:
- player: Player object
- drifters: [drifter_1, drifter_2, drifter_3]
- player_gear: PlayerGear queryset
- gear_by_category: Dictionary of gear by category
```

### 4. HTML Output
```
Template renders:
- Player information header
- Drifter loadout sections
- Gear inventory with filtering
- Interactive JavaScript functionality
```

## 🎯 Key Features

### 1. Player Information Display
- **Name**: Player's in-game name with edit button (✏️)
- **Discord**: Discord username
- **Guild**: Guild affiliation or "No guild"
- **Level**: Character level
- **Faction**: Player's faction (Sirius, Emberwild, etc.)
- **Role**: Guild role and game role

### 2. Drifter Loadout System
- **3 Drifter Slots**: Each player can have up to 3 drifters
- **Drifter Stats**: Health, Energy, Damage, Defense, Speed
- **Equipment Slots**: 9 slots per drifter (Weapon, Helmet, Chest, Boots, Consumable, 4 Mods)
- **Visual Indicators**: Empty slots shown as ⚪

### 3. Gear Management
- **Category Filtering**: Boots, Chest, Consumable, Helmet, Mod, Weapon
- **Rarity Filtering**: All, Rare, Epic, Legendary
- **Stat Filtering**: Strength, Agility, Intelligence
- **Equipped Status**: Visual indicators for equipped items

### 4. Interactive Features
- **Real-time Filtering**: JavaScript-based filtering
- **Responsive Design**: Mobile-friendly interface
- **Visual Feedback**: Hover effects and transitions
- **Edit Functionality**: Player name editing capability

## 📖 How to Use the Player Loadout Page

### For Guild Leaders & Admins

#### 1. Accessing Player Loadouts
```
URL Format: /guilds/player/{player_id}/loadout/
Example: /guilds/player/5/loadout/
```

#### 2. Viewing Player Information
- **Player Name**: Click the ✏️ button to edit player name
- **Discord**: Shows Discord username for communication
- **Guild**: Displays guild affiliation or "No guild"
- **Level**: Character progression level
- **Faction**: Player's faction (Sirius, Emberwild, etc.)
- **Role**: Guild role (Member, Officer, Leader, Recruiter)
- **Game Role**: Primary role (Healer, Tank, DPS, etc.)

#### 3. Managing Drifter Loadouts
- **Drifter 1**: Primary drifter configuration
- **Drifter 2**: Secondary drifter (optional)
- **Drifter 3**: Tertiary drifter (optional)
- **Equipment Slots**: 9 slots per drifter
  - ⚔️ Weapon
  - 🪖 Helmet
  - 🛡️ Chest
  - 👢 Boots
  - 🧪 Consumable
  - ⚪ Mod 1-4

#### 4. Using Gear Filters

##### Category Filters
```
Click on category buttons to filter gear:
- Boots: Show only boot items
- Chest: Show only chest armor
- Consumable: Show only consumables
- Helmet: Show only helmets
- Mod: Show only mods
- Weapon: Show only weapons
```

##### Rarity Filters
```
Filter by item rarity:
- All: Show all items
- Rare: Show only rare items (green border)
- Epic: Show only epic items (purple border)
- Legendary: Show only legendary items (orange border)
```

##### Stat Filters
```
Filter by character attributes:
- 💪 Strength: Items that boost strength
- 🏃 Agility: Items that boost agility
- 🧠 Intelligence: Items that boost intelligence
```

#### 5. Understanding Gear Items

##### Item Information Display
```
Item Name (Skill Name)
Item Type • Rarity
Stats:
- Damage & Heal bonus: X%
- HP: +X
- Armor: X
- Magic resistance: X
- Mana recovery bonus: X%
```

##### Rarity Color Coding
- **Common**: No special border
- **Rare**: Green left border
- **Epic**: Purple left border
- **Legendary**: Orange left border

##### Equipped Status
- **"Equipped"** label shows currently equipped items
- **Visual indicators** for equipped status

#### 6. Equipping Gear Items (Admin/Player)

##### Step-by-Step Equipping Process
```
1. Navigate to the gear category you want (Boots, Chest, Weapon, etc.)
2. Use filters to narrow down your search:
   - Filter by rarity (Rare, Epic, Legendary)
   - Filter by stats (Strength, Agility, Intelligence)
3. Find the specific item you want to equip
4. Click on the item
5. The item automatically goes to the correct slot type
6. Visual confirmation shows the item is now equipped
```

##### Equipment Slot Logic
```
Automatic Slot Assignment Based on Item Type:
- Luminous Ward (Weapon) → ⚔️ Weapon slot
- Healer's Hood (Helmet) → 🪖 Helmet slot
- Cleansing Robe (Chest) → 🛡️ Chest slot
- Arcaneflow Boots (Boots) → 👢 Boots slot
- Mass Healing Elixir (Consumable) → 🧪 Consumable slot
- Any Mod item → ⚪ Mod slot (fills empty mod slots first)
```

##### Equipment Management Features
- **Auto-Slot Detection**: System automatically detects item type
- **Slot Replacement**: Equipping new item replaces old item in same slot
- **Visual Feedback**: Immediate visual confirmation of equipment changes
- **Stat Updates**: Character stats update automatically when equipment changes

### For Players

#### 1. Viewing Your Loadout
- Navigate to your player loadout page
- Review your current drifter configurations
- Check equipped items and stats
- See your gear inventory

#### 2. Understanding Your Stats
```
Drifter Stats:
- Health: Total health points
- Energy: Total energy/mana
- Damage: Base damage output
- Defense: Damage reduction
- Speed: Movement/attack speed
```

#### 3. Gear Management
- **Browse Inventory**: Use filters to find specific gear
- **Compare Items**: View stats of different items
- **Check Rarity**: Understand item quality levels
- **View Skills**: See associated skills for each item

#### 4. Equipping Gear Items
```
How to Equip Items:
1. Find the item you want in the appropriate category
2. Click on the item to equip it
3. The item is automatically added to the correct slot type
4. Visual confirmation shows "Equipped" status
```

##### Equipment Slot Assignment
```
Automatic Slot Assignment:
- Weapon items → ⚔️ Weapon slot
- Helmet items → 🪖 Helmet slot  
- Chest items → 🛡️ Chest slot
- Boots items → 👢 Boots slot
- Consumable items → 🧪 Consumable slot
- Mod items → ⚪ Mod slots (1-4)
```

### For Discord Bot Users

#### 1. Getting Loadout Links
```
Discord Commands:
/buildplayer Charfire
→ Returns: 🔗 Charfire - https://strategic-brena-charfire-afecfd9e.koyeb.app/guilds/player/5/loadout/
```

#### 2. Quick Access
- Use Discord bot to get instant links to player loadouts
- Share loadout links in Discord channels
- Quick reference for guild members

### Navigation & User Experience

#### 1. Page Navigation
- **← Back**: Return to previous page
- **Breadcrumb Navigation**: Shows current location
- **Responsive Design**: Works on mobile and desktop

#### 2. Interactive Elements
- **Filter Buttons**: Click to filter gear
- **Edit Button**: Click ✏️ to edit player name
- **Hover Effects**: Visual feedback on interactions
- **Smooth Transitions**: Animated filtering

#### 3. Data Display
- **Real-time Updates**: Changes reflect immediately
- **Visual Hierarchy**: Clear information organization
- **Color Coding**: Intuitive visual indicators
- **Progress Indicators**: Equipment completion status

### Common Use Cases

#### 1. Guild Recruitment
```
Use Case: Evaluating new members
1. Check player's current loadout
2. Review gear quality and rarity
3. Assess drifter configurations
4. Make recruitment decisions
```

#### 2. Guild Management
```
Use Case: Managing guild members
1. Monitor player progression
2. Check gear upgrades
3. Plan guild activities
4. Assign roles based on loadouts
```

#### 3. Strategy Planning
```
Use Case: Planning guild strategies
1. Review member loadouts
2. Identify gear gaps
3. Plan gear distribution
4. Coordinate team compositions
```

#### 4. Player Development
```
Use Case: Helping players improve
1. Identify underperforming gear
2. Suggest gear upgrades
3. Plan character progression
4. Provide loadout recommendations
```

#### 5. Equipment Management
```
Use Case: Managing player equipment
1. Find desired item in appropriate category
2. Click on item to equip it automatically
3. System assigns item to correct slot type
4. Visual confirmation shows equipment status
5. Character stats update automatically
```

##### Practical Example: Equipping a Weapon
```
Example: Equipping "Luminous Ward (Sanctum Arc)"
1. Navigate to Weapon category
2. Filter by Epic rarity (purple border)
3. Find "Luminous Ward (Sanctum Arc)" in the list
4. Click on the item
5. Item automatically goes to ⚔️ Weapon slot
6. "Equipped" label appears on the item
7. Character damage stats update immediately
```

### Troubleshooting

#### 1. Common Issues
- **"No drifter assigned"**: Player hasn't configured drifters
- **"No guild"**: Player isn't in a guild
- **Empty gear inventory**: Player has no gear items
- **Missing stats**: Incomplete character information

#### 2. Solutions
- **Assign Drifters**: Use admin interface to assign drifters
- **Add to Guild**: Assign player to appropriate guild
- **Add Gear**: Use admin interface to add gear items
- **Update Stats**: Ensure character information is complete

#### 3. Admin Actions
- **Edit Player**: Use Django admin to modify player data
- **Add Gear**: Add gear items to player inventory
- **Assign Guild**: Move player to appropriate guild
- **Update Stats**: Modify character statistics

## 🚀 Performance Considerations

### Database Optimization
- **Select Related**: Use `select_related()` for foreign keys
- **Prefetch Related**: Use `prefetch_related()` for many-to-many relationships
- **Query Optimization**: Minimize database queries

### Template Optimization
- **Template Caching**: Cache frequently accessed data
- **Static Files**: Optimize CSS/JS delivery
- **Image Optimization**: Compress gear item images

### JavaScript Optimization
- **Event Delegation**: Efficient event handling
- **Debouncing**: Limit filter function calls
- **Lazy Loading**: Load gear items on demand

---

**Last Updated**: September 21, 2025
**Template Version**: 1.0
**Lines of Code**: 2,449 (player_loadout.html)
