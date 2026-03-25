import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import random
import hashlib
import json
from pathlib import Path
from discord.ui import View, Button
import time
import asyncio

TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Background task for automatic aging
@tasks.loop(hours=1)
async def automatic_aging_task():
    """Run every hour to check for character aging"""
    try:
        aged = apply_automatic_aging()
        
        if aged:
            print(f"✨ {len(aged)} characters aged automatically!")
            save_game_state()
    except Exception as e:
        print(f"❌ Error in automatic aging task: {e}")

# Background task for season cycling
@tasks.loop(hours=24)
async def season_cycling_task():
    """Run daily to cycle through seasons"""
    try:
        old_season = season
        new_season = cycle_season()
        
        if old_season != new_season:
            print(f"🌍 Season changed: {old_season} → {new_season}")
            # You could trigger season-specific events here
            save_game_state()
    except Exception as e:
        print(f"❌ Error in season cycling task: {e}")


# ----------------------- GLOBALS -----------------------
characters = {}
pending_hunts = {}
pending_battles = {}
pending_breeding = {}
battle_state = {}
pregnancies = {}
custom_clans = {}
camp_quality = {"Thunder": 75, "River": 75, "Shadow": 75, "Wind": 75}
# ----------------------- INITIAL CLAN PREY -----------------------
# Each clan starts with some prey so kits can eat
clan_prey_piles = {
    "Thunder": 20,
    "River": 20,
    "Shadow": 20,
    "Wind": 20
}

fresh_kill_piles = {
    "Thunder": ["mouse", "rabbit", "vole"],
    "River": ["fish", "frog", "water vole"],
    "Shadow": ["rat", "lizard", "frog"],
    "Wind": ["rabbit", "hare", "mouse"]
}
seasons = ["newleaf", "greenleaf", "leaf-fall", "leafbare"]
season = "greenleaf"

seasonal_pregnancy_modifiers = {
    "newleaf": {"health_mult": 1.1, "max_kits": 5},
    "greenleaf": {"health_mult": 1.0, "max_kits": 4},
    "leaf-fall": {"health_mult": 0.9, "max_kits": 4},
    "leafbare": {"health_mult": 0.8, "max_kits": 3}
}

prey_tables = {
    "Thunder": {"greenleaf": {"mouse":2,"vole":2,"squirrel":3,"rabbit":5},
                "leafbare": {"mouse":2,"vole":2}},
    "River": {"greenleaf": {"fish":4,"frog":2,"water vole":3},
              "leafbare": {"fish":3}},
    "Shadow": {"greenleaf": {"rat":3,"lizard":2,"frog":2},
               "leafbare": {"rat":3}},
    "Wind": {"greenleaf": {"rabbit":5,"hare":4,"mouse":2},
             "leafbare": {"rabbit":4}}
}

hunt_messages = [
    "You crouch low in the undergrowth...",
    "You scent the air carefully...",
    "You stalk through the territory silently...",
    "Your tail flicks as you track movement...",
    "You creep forward pawstep by pawstep..."
]

clan_specialties = {
    "Thunder": "tracking",
    "River": "swimming",
    "Shadow": "stealth",
    "Wind": "endurance"
}

MOVES = {
    "Thunder": [
        {"name": "Claw Swipe", "type": "physical", "stat_multiplier": {"strength": 0.5}},
        {"name": "Pounce", "type": "physical", "stat_multiplier": {"strength": 0.6, "speed": 0.3}},
        {"name": "Roar", "type": "status", "buff": {"defense_up": 1, "attack_down": 1}},
        {"name": "Charge Strike", "type": "charge", "stat_multiplier": {"strength": 1.0}}
    ],
    "River": [
        {"name": "Water Slash", "type": "physical", "stat_multiplier": {"speed": 0.5, "perception": 0.3}},
        {"name": "Dive Attack", "type": "charge", "stat_multiplier": {"speed": 0.8, "dexterity": 0.4}},
        {"name": "Soothing Ripple", "type": "status", "buff": {"heal": 10}}
    ],
    "Shadow": [
        {"name": "Shadow Pounce", "type": "physical", "stat_multiplier": {"dexterity": 0.7, "speed": 0.4}},
        {"name": "Stealth Strike", "type": "status", "buff": {"attack_up": 2}}
    ],
    "Wind": [
        {"name": "Gale Swipe", "type": "physical", "stat_multiplier": {"speed": 0.6, "strength": 0.3}},
        {"name": "Whirlwind", "type": "charge", "stat_multiplier": {"speed": 1.0}},
        {"name": "Endurance Boost", "type": "status", "buff": {"defense_up": 2}}
    ]
}

# ----------------------- BUYABLE MOVES SYSTEM (CLAN-SPECIFIC) -----------------------
BUYABLE_MOVES = {
    "Thunder": [
        {"name": "⚡ Thunder Fang", "type": "physical", "stat_multiplier": {"strength": 1.2, "speed": 0.3}, "cost": 35},
        {"name": "🌩️ Lightning Chain", "type": "charge", "stat_multiplier": {"strength": 1.5, "intelligence": 0.4}, "cost": 50},
        {"name": "🔥 Furious Swipe", "type": "physical", "stat_multiplier": {"strength": 1.4}, "cost": 40},
    ],
    "River": [
        {"name": "💧 Tidal Wave", "type": "physical", "stat_multiplier": {"speed": 1.3, "strength": 0.4}, "cost": 35},
        {"name": "🌊 Aquatic Vortex", "type": "charge", "stat_multiplier": {"speed": 1.4, "perception": 0.3}, "cost": 50},
        {"name": "❄️ Healing Spring", "type": "status", "buff": {"heal": 35}, "cost": 30},
    ],
    "Shadow": [
        {"name": "🗡️ Shadow Slash", "type": "physical", "stat_multiplier": {"dexterity": 1.3, "speed": 0.5}, "cost": 35},
        {"name": "💀 Darkness Engulf", "type": "charge", "stat_multiplier": {"dexterity": 1.4, "intelligence": 0.3}, "cost": 50},
        {"name": "🌑 Shadow Cloak", "type": "status", "buff": {"defense_up": 3, "attack_up": 1}, "cost": 40},
    ],
    "Wind": [
        {"name": "🌪️ Cyclone Claw", "type": "physical", "stat_multiplier": {"speed": 1.3, "dexterity": 0.4}, "cost": 35},
        {"name": "🌀 Whirlwind Rage", "type": "charge", "stat_multiplier": {"speed": 1.5}, "cost": 50},
        {"name": "💨 Wind's Protection", "type": "status", "buff": {"defense_up": 2, "speed": 1}, "cost": 35},
    ]
}

# ----------------------- ACTIVITY POINTS SYSTEM -----------------------
activity_points = {}  # Track activity points per user
ACTIVITY_POINTS_REWARD = 5  # Points per message
AGE_UP_COST = 500  # Points to age up one moon (very expensive - mainly for skipping ahead)
TRAINING_SESSION_COST = 15  # Points to train once

# ----------------------- AUTOMATIC AGING SYSTEM -----------------------
# Each week of real time = 1 moon of character aging
MOON_DURATION_SECONDS = 7 * 24 * 60 * 60  # 1 week = 1 moon (can adjust for testing)

# ----------------------- HEALING ITEMS SYSTEM -----------------------
healing_consumables = {}  # Track consumable healings owned by users: {user_id: {"herb_name": count}}
one_time_purchases = {}  # Track one-time purchases: {user_id: ["item_name"]}

HEALING_ITEMS = {
    "consumable": [
        {"name": "🌿 Healing Herb", "heal": 20, "cost": 8, "max_stack": 999},
        {"name": "🍃 Moonflower Petals", "heal": 35, "cost": 15, "max_stack": 999},
    ],
    "one_time": [
        {"name": "⭐ Legendary Elixir", "heal": 100, "cost": 200},  # Very expensive, full heal
    ]
}

# ----------------------- RANDOM EVENTS SYSTEM -----------------------
clan_events = {}  # Track recent events: {clan_name: [{"event": name, "description": str, "timestamp": time}]}

RANDOM_EVENTS = {
    "MINOR": [
        {
            "name": "🦊 Fox Prowls the Camp",
            "description": "A fox attacked the camp! A few kits went missing.",
            "effect": lambda clan: {
                "camp_quality": -5,
                "clan_prey_piles": -2,
            }
        },
        {
            "name": "🦡 Badger Territory Dispute",
            "description": "A badger wandered into clan territory. Minor skirmish ensued.",
            "effect": lambda clan: {
                "camp_quality": -3,
                "health_damage_random": 2,  # 2 random clan members lose 10 health
            }
        },
        {
            "name": "🍂 Leaf-Bare Chill",
            "description": "An unexpected cold snap struck. Prey became harder to find.",
            "effect": lambda clan: {
                "clan_prey_piles": -3,
                "camp_quality": -2,
            }
        },
        {
            "name": "🌱 Abundant Flowering",
            "description": "Unusual bounty of seeds and berries! The herb supply improved.",
            "effect": lambda clan: {
                "camp_quality": 8,
            }
        },
        {
            "name": "🐦 Migration Season",
            "description": "Birds passed through in large numbers. Hunting was easy!",
            "effect": lambda clan: {
                "clan_prey_piles": 5,
            }
        },
        {
            "name": "🦠 Minor Illness Outbreak",
            "description": "A few cats caught a mild sickness. They recovered quickly.",
            "effect": lambda clan: {
                "health_damage_random": 3,  # 3 random clan members lose 5 health
            }
        },
    ],
    "MODERATE": [
        {
            "name": "🔥 Camp Fire",
            "description": "A fire broke out in the camp! Several nests were destroyed.",
            "effect": lambda clan: {
                "camp_quality": -25,
                "clan_prey_piles": -8,
                "health_damage_random": 5,  # 5 random members lose 15 health
            }
        },
        {
            "name": "🌊 Heavy Rainfall",
            "description": "Torrential rains flooded parts of the territory. Nests ruined.",
            "effect": lambda clan: {
                "camp_quality": -20,
                "clan_prey_piles": -6,
            }
        },
        {
            "name": "⚔️ Rival Clan Attack",
            "description": "A rival clan raided the territory! Fierce battle ensued.",
            "effect": lambda clan: {
                "camp_quality": -15,
                "health_damage_random": 8,  # 8 random members lose health
            }
        },
        {
            "name": "💀 Epidemic",
            "description": "Disease swept through the clan! Many fell ill.",
            "effect": lambda clan: {
                "camp_quality": -12,
                "health_damage_random": 12,  # Major health impact
            }
        },
        {
            "name": "🌳 Tree Down",
            "description": "A massive tree fell in a storm. The camp was damaged.",
            "effect": lambda clan: {
                "camp_quality": -18,
                "clan_prey_piles": -4,
            }
        },
        {
            "name": "🐺 Wolf Pack Warning",
            "description": "Wolves were spotted near clan territory. Patrols increased.",
            "effect": lambda clan: {
                "camp_quality": -10,
            }
        },
    ],
    "MAJOR": [
        {
            "name": "🌋 Catastrophic Fire",
            "description": "A massive wildfire destroyed the entire camp! The clan must rebuild from nothing.",
            "effect": lambda clan: {
                "camp_quality": -50,
                "clan_prey_piles": -15,
                "health_damage_random": 15,  # Devastating health damage
            }
        },
        {
            "name": "💧 Great Flood",
            "description": "Flash floods devastated the territory! Nests destroyed, prey scattered.",
            "effect": lambda clan: {
                "camp_quality": -45,
                "clan_prey_piles": -12,
            }
        },
        {
            "name": "🐻 Bear Invasion",
            "description": "A massive bear attacked the clan! Severe casualties and destruction.",
            "effect": lambda clan: {
                "camp_quality": -40,
                "health_damage_random": 20,  # Very high damage - potentially lethal
            }
        },
        {
            "name": "🦅 Eagle Attacks Nursery",
            "description": "An enormous eagle attacked the nursery multiple times. Kits were lost.",
            "effect": lambda clan: {
                "camp_quality": -30,
                "clan_prey_piles": -5,
                "health_damage_random": 7,  # Targets young cats especially
            }
        },
        {
            "name": "❄️ Harsh Winter",
            "description": "The winter was crueler than expected. Starvation threatened the clan.",
            "effect": lambda clan: {
                "camp_quality": -35,
                "clan_prey_piles": -20,
                "hunger_increase_all": 20,  # All clan members get hungrier
            }
        },
        {
            "name": "🌊 Drought",
            "description": "A terrible drought struck. Water and food became scarce across the entire region.",
            "effect": lambda clan: {
                "camp_quality": -30,
                "clan_prey_piles": -18,
                "hunger_increase_all": 15,
            }
        },
    ]
}

# ----------------------- SAVE/LOAD SYSTEM -----------------------
SAVE_FILE = Path("game_state.json")

def save_game_state():
    """Save all game state to JSON file"""
    state = {
        "characters": characters,
        "pending_hunts": pending_hunts,
        "pending_battles": pending_battles,
        "pending_breeding": pending_breeding,
        "battle_state": {str(k): v for k, v in battle_state.items()},
        "pregnancies": pregnancies,
        "custom_clans": custom_clans,
        "camp_quality": camp_quality,
        "clan_prey_piles": clan_prey_piles,
        "fresh_kill_piles": fresh_kill_piles,
        "season": season,
        "activity_points": {str(k): v for k, v in activity_points.items()},
        "healing_consumables": {str(k): v for k, v in healing_consumables.items()},
        "one_time_purchases": {str(k): v for k, v in one_time_purchases.items()},
        "clan_events": clan_events
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print("✅ Game state saved!")

def load_game_state():
    """Load game state from JSON file if it exists"""
    global characters, pending_hunts, pending_battles, pending_breeding
    global battle_state, pregnancies, custom_clans, camp_quality
    global clan_prey_piles, fresh_kill_piles, season, activity_points
    global healing_consumables, one_time_purchases, clan_events
    
    if not SAVE_FILE.exists():
        print("📂 No save file found. Starting fresh!")
        return
    
    try:
        with open(SAVE_FILE, "r") as f:
            state = json.load(f)
        
        characters = state.get("characters", {})
        pending_hunts = state.get("pending_hunts", {})
        pending_battles = state.get("pending_battles", {})
        pending_breeding = state.get("pending_breeding", {})
        battle_state = {eval(k): v for k, v in state.get("battle_state", {}).items()}
        pregnancies = state.get("pregnancies", {})
        custom_clans = state.get("custom_clans", {})
        camp_quality = state.get("camp_quality", {"Thunder": 75, "River": 75, "Shadow": 75, "Wind": 75})
        clan_prey_piles = state.get("clan_prey_piles", {"Thunder": 20, "River": 20, "Shadow": 20, "Wind": 20})
        fresh_kill_piles = state.get("fresh_kill_piles", {
            "Thunder": ["mouse", "rabbit", "vole"],
            "River": ["fish", "frog", "water vole"],
            "Shadow": ["rat", "lizard", "frog"],
            "Wind": ["rabbit", "hare", "mouse"]
        })
        season = state.get("season", "greenleaf")
        activity_points = {int(k): v for k, v in state.get("activity_points", {}).items()}
        healing_consumables = {int(k): v for k, v in state.get("healing_consumables", {}).items()}
        one_time_purchases = {int(k): v for k, v in state.get("one_time_purchases", {}).items()}
        clan_events = state.get("clan_events", {})
        
        print(f"✅ Game state loaded! Found {len(characters)} characters.")
    except Exception as e:
        print(f"❌ Error loading save file: {e}")

# ----------------------- UTILITY FUNCTIONS -----------------------
def generate_stats():
    return {stat: random.randint(0, 10) for stat in ["strength","perception","dexterity","speed","intelligence","luck","charisma"]}
    
def get_full_name(char):
    return f"{char['prefix']}{char.get('suffix','')}"
    
def check_for_apprentice(uid):
    char = characters[uid]
    if char["rank"] == "kit" and char.get("moons", 0) >= 6:
        char["rank"] = "apprentice"
        char["specialty"] = char.get("clan")  # maybe keep track of mentor later
        return f"🌟 {char['prefix']} has become an apprentice!"
    return None
    
def hunger_status(hunger):
    if hunger <= 0: return "💀 Starving!"
    elif hunger < 20: return "⚠️ Starving — hunt immediately."
    elif hunger < 40: return "🥀 Very hungry."
    elif hunger < 60: return "🍂 Getting hungry."
    elif hunger < 80: return "🍖 Satisfied."
    elif hunger < 100: return "😌 Well fed."
    else: return "🐗 Overstuffed."

def health_status(health):
    if health <= 0: return "💀 Dead."
    elif health < 20: return "🚨 Critically injured! See a medicine cat!"
    elif health < 40: return "⚠️ Badly wounded."
    elif health < 70: return "🩹 Injured."
    else: return "💪 Healthy."

def modify_hunger(char, amount):
    char["hunger"] += amount
    char["hunger"] = max(0, min(100, char["hunger"]))
    if char["hunger"] <= 0:
        char["alive"] = False
        return f"💀 {char['prefix']} has starved."
    if char["hunger"] < 20:
        return "⚠️ You are starving."
    return None

def in_battle(user_id):
    for attacker, defender in battle_state.keys():
        if user_id == attacker or user_id == defender:
            return True
    return False

def end_battle(attacker_id, defender_id):
    battle_state.pop((attacker_id, defender_id), None)
    pending_battles.pop(defender_id, None)

def hunger_modifier(hunger):
    if hunger < 30: return -5
    elif hunger < 50: return -2
    elif hunger < 80: return 2
    elif hunger <= 99: return 0
    else: return -3

def hunting_outcome(char, base_success=70):
    hunger = char["hunger"]
    success_chance = base_success
    if hunger <= 0: success_chance -= 40
    elif hunger < 20: success_chance -= 20
    elif hunger < 40: success_chance -= 10
    elif hunger >= 90: success_chance -= 15
    roll = random.randint(1,100)
    success = roll <= success_chance
    food_gained = random.randint(5,15)
    if hunger < 20: food_gained = max(1, food_gained - 5)
    elif hunger < 40: food_gained = max(3, food_gained - 2)
    elif hunger >=70 and hunger < 90: food_gained += 2
    elif hunger >= 90: food_gained = max(1, food_gained - 3)
    hunger_cost = 5
    if char.get("hunt_streak",0) > 3: hunger_cost += 3
    char["hunger"] = max(char["hunger"] - hunger_cost,0)
    return success, food_gained
    
def process_pregnancy_moon():
    for carrier_id, data in list(pregnancies.items()):
        if not data["active"]:
            continue

        carrier = characters.get(carrier_id)
        if not carrier:
            continue
            
def pregnancy_hunt_modifier(char):
    if not char.get("pregnant"):
        return 0
    return char["pregnant"].get("months", 0) * 5

def pregnancy_train_allowed(char):
    if not char.get("pregnant"):
        return True
    return char["pregnant"]["months"] < 4

def apply_pregnancy_effects(char):
    if not char.get("pregnant"):
        return 1.0

    stage = char["pregnant"].get("months", 0)

    if stage <= 2:
        return 1.0
    elif stage <= 4:
        return 0.8
    else:
        return 0.6

def calculate_stat_damage(char, stat_multiplier):
    """Calculate damage based on character stats and multipliers"""
    if not stat_multiplier:
        return 0
    
    stats = char.get("stats", {})
    base_damage = 10  # Base damage for all moves
    stat_damage = 0
    
    # Calculate damage from each stat
    for stat_name, multiplier in stat_multiplier.items():
        stat_value = stats.get(stat_name, 0)
        stat_damage += stat_value * multiplier * 3  # 3x damage scaling from stats
    
    total_damage = int(base_damage + stat_damage)
    
    # Add hunger modifier
    hunger = char.get("hunger", 50)
    if hunger < 30:
        total_damage -= 5
    elif hunger < 50:
        total_damage -= 2
    elif hunger >= 80:
        total_damage -= 1
    
    return max(1, total_damage)

def create_progress_bar(current, max_val, bar_length=20):
    """Create a visual progress bar for Discord embeds"""
    if max_val <= 0:
        percentage = 0
    else:
        percentage = int((current / max_val) * 100)
    
    filled = int((current / max_val) * bar_length) if max_val > 0 else 0
    empty = bar_length - filled
    
    # Choose emoji based on percentage
    if percentage >= 80:
        emoji = "🟩"
    elif percentage >= 50:
        emoji = "🟨"
    elif percentage >= 25:
        emoji = "🟧"
    else:
        emoji = "🟥"
    
    bar = emoji * filled + "⬜" * empty
    return f"{bar} {percentage}%"

def get_injury_description(degree):
    """Get injury description based on degree"""
    injuries = {
        0: ("None", "🟩 Healthy"),
        1: ("Minor", "🟨 Minor wounds - slight pain"),
        2: ("Moderate", "🟧 Moderate wounds - noticeable pain"),
        3: ("Severe", "🟥 Severe wounds - significant pain"),
        4: ("Critical", "💀 Critical condition - needs urgent healing")
    }
    return injuries.get(degree, ("Unknown", "❓ Unknown status"))

def update_injury_degree(char):
    """Update injury degree based on health percentage"""
    health = char.get("health", 100)
    
    if health >= 80:
        char["injury_degree"] = 0
    elif health >= 60:
        char["injury_degree"] = 1
    elif health >= 40:
        char["injury_degree"] = 2
    elif health >= 20:
        char["injury_degree"] = 3
    else:
        char["injury_degree"] = 4

def apply_hunger_damage(char):
    """Apply health damage if hunger is critically low"""
    hunger = char.get("hunger", 50)
    
    # If hunger < 10, take health damage
    if hunger < 10:
        damage = max(1, 10 - hunger)  # More starving = more damage
        char["health"] = max(0, char["health"] - damage)
        update_injury_degree(char)
        if char["health"] <= 0:
            char["alive"] = False
        return True, damage
    
    return False, 0

def get_clan_members(clan_name):
    """Get all members of a clan"""
    members = []
    for uid, char in characters.items():
        if char.get("clan") == clan_name and char.get("alive", True):
            members.append((uid, char))
    return members

def trigger_random_event(clan_name):
    """Trigger a random event for a clan and return event details"""
    import time
    
    # Determine event severity (weighted)
    severity_roll = random.randint(1, 100)
    if severity_roll <= 60:
        severity = "MINOR"
    elif severity_roll <= 90:
        severity = "MODERATE"
    else:
        severity = "MAJOR"
    
    # Select random event from severity level
    event = random.choice(RANDOM_EVENTS[severity])
    effect_dict = event["effect"](clan_name)
    
    # Apply camp quality change
    if "camp_quality" in effect_dict:
        camp_quality[clan_name] = max(0, min(100, camp_quality[clan_name] + effect_dict["camp_quality"]))
    
    # Apply prey pile change
    if "clan_prey_piles" in effect_dict:
        clan_prey_piles[clan_name] = max(0, clan_prey_piles[clan_name] + effect_dict["clan_prey_piles"])
    
    # Apply health damage to random clan members
    if "health_damage_random" in effect_dict:
        members = get_clan_members(clan_name)
        num_affected = min(effect_dict["health_damage_random"], len(members))
        if num_affected > 0:
            affected_members = random.sample(members, num_affected)
            severity_damage = {"MINOR": 5, "MODERATE": 15, "MAJOR": 25}
            damage_amount = severity_damage[severity]
            for uid, member in affected_members:
                member["health"] = max(0, member["health"] - damage_amount)
                update_injury_degree(member)
                if member["health"] <= 0:
                    member["alive"] = False
    
    # Apply hunger increase to all clan members
    if "hunger_increase_all" in effect_dict:
        for uid, member in get_clan_members(clan_name):
            member["hunger"] = min(100, member["hunger"] + effect_dict["hunger_increase_all"])
    
    # Record event in history
    if clan_name not in clan_events:
        clan_events[clan_name] = []
    
    clan_events[clan_name].append({
        "event": event["name"],
        "description": event["description"],
        "severity": severity,
        "timestamp": int(time.time())
    })
    
    # Keep only last 20 events per clan
    if len(clan_events[clan_name]) > 20:
        clan_events[clan_name] = clan_events[clan_name][-20:]
    
    return event, severity, effect_dict

def age_character_moon(char):
    """Age a character by one moon and handle associated changes"""
    char["moons"] = char.get("moons", 0) + 1
    char["hunger"] = max(char.get("hunger", 100) - 10, 0)
    char["last_aged"] = time.time()
    
    return char["moons"]

def cycle_season():
    """Progress to next season"""
    global season
    season_index = seasons.index(season)
    season = seasons[(season_index + 1) % len(seasons)]
    return season

def apply_automatic_aging():
    """Check all characters and age them if enough time has passed"""
    current_time = time.time()
    aged_characters = []
    
    for uid, char in characters.items():
        if not char.get("alive", True):
            continue
        
        last_aged = char.get("last_aged", current_time)
        time_passed = current_time - last_aged
        
        # Check if enough time has passed for aging
        moons_passed = int(time_passed / MOON_DURATION_SECONDS)
        
        if moons_passed > 0:
            for _ in range(moons_passed):
                new_moon = age_character_moon(char)
            
            aged_characters.append((uid, char, moons_passed))
    
    return aged_characters

def generate_clan_colors(clan_name):
    base_hash = int(hashlib.md5(clan_name.encode()).hexdigest(), 16)

    colors = []
    for i in range(4):
        r = (base_hash >> (i * 6)) & 0xFF
        g = (base_hash >> (i * 12)) & 0xFF
        b = (base_hash >> (i * 18)) & 0xFF

        r = (r % 156) + 100
        g = (g % 156) + 100
        b = (b % 156) + 100

        colors.append(discord.Color.from_rgb(r, g, b))

    return colors


@bot.tree.command(name="create_clan", description="Create a new clan (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def create_clan(interaction: discord.Interaction, clan_name: str, leader: discord.Member):

    creator_id = interaction.user.id
    guild = interaction.guild

    # ---------------- VALIDATION ----------------
    if creator_id not in characters:
        await interaction.response.send_message("❌ You need a character.")
        return

    if leader.id not in characters:
        await interaction.response.send_message("❌ That user doesn't have a character.")
        return

    if characters[leader.id].get("is_leader"):
        await interaction.response.send_message("⚠️ That user is already a leader.")
        return

    clan_name = clan_name.capitalize()

    if clan_name in clan_specialties:
        await interaction.response.send_message("❌ That clan already exists.")
        return

    colors = generate_clan_colors(clan_name)

    # ---------------- COLOR MENU ----------------
    async def show_color_options(i):
        view = View(timeout=180)

        for idx, color in enumerate(colors):

            btn = Button(label=f"Color {idx+1}", style=discord.ButtonStyle.secondary)

            async def pick_callback(inter, chosen=color):
                if inter.user.id != creator_id:
                    await inter.response.send_message("❌ Only the creator can choose.", ephemeral=True)
                    return

                await show_preview(inter, chosen)

            btn.callback = pick_callback
            view.add_item(btn)

        await i.response.edit_message(
            content=f"🎨 Choose a color for **{clan_name}Clan**:",
            embed=None,
            view=view
        )

    # ---------------- PREVIEW ----------------
    async def show_preview(i, chosen_color):
        view = View(timeout=180)

        embed = discord.Embed(
            title=f"{clan_name}Clan Preview",
            description=f"👑 Leader: {characters[leader.id]['prefix']}",
            color=chosen_color
        )

        embed.add_field(
            name="Confirm Clan Creation",
            value="Press **Confirm** to create the clan or **Pick Another** to choose again."
        )

        # ✅ CONFIRM
        async def confirm(inter):
            if inter.user.id != creator_id:
                await inter.response.send_message("❌ Only the creator can confirm.", ephemeral=True)
                return

            role_name = f"{clan_name}Clan"

            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                role = await guild.create_role(
                    name=role_name,
                    colour=chosen_color,
                    mentionable=True,
                    hoist=True
                )

            # Remove old clan roles
            clan_roles = [r for r in guild.roles if r.name.endswith("Clan")]
            member_obj = guild.get_member(leader.id)

            for r in clan_roles:
                if r in member_obj.roles:
                    await member_obj.remove_roles(r)

            await member_obj.add_roles(role)

            # Assign character
            char = characters[leader.id]
            char["clan"] = clan_name
            char["rank"] = "leader"
            char["is_leader"] = True

            # ✅ FIXED specialty (important)
            clan_specialties[clan_name] = "adaptability"

            # Save clan
            custom_clans[clan_name] = {"leader": leader.id}
            clan_prey_piles[clan_name] = 20
            fresh_kill_piles[clan_name] = ["mouse", "rabbit"]

            prey_tables[clan_name] = {
                "greenleaf": {"mouse": 2, "rabbit": 4},
                "leafbare": {"mouse": 2}
            }

            camp_quality[clan_name] = 75

            await inter.response.edit_message(
                content=f"🌟 **{clan_name}Clan has been created!**\n👑 Leader: **{char['prefix']}**",
                embed=None,
                view=None
            )
            save_game_state()

        # ❌ DENY
        async def deny(inter):
            if inter.user.id != creator_id:
                await inter.response.send_message("❌ Only the creator can deny.", ephemeral=True)
                return

            await show_color_options(inter)

        confirm_btn = Button(label="Confirm", style=discord.ButtonStyle.green)
        deny_btn = Button(label="Pick Another", style=discord.ButtonStyle.red)

        confirm_btn.callback = confirm
        deny_btn.callback = deny

        view.add_item(confirm_btn)
        view.add_item(deny_btn)

        await i.response.edit_message(embed=embed, view=view)

    # ---------------- INITIAL BUTTONS ----------------
    view = View(timeout=180)

    for idx, color in enumerate(colors):
        btn = Button(label=f"Color {idx+1}", style=discord.ButtonStyle.secondary)

        async def callback(i, chosen=color):
            if i.user.id != creator_id:
                await i.response.send_message("❌ Only the creator can choose.", ephemeral=True)
                return

            await show_preview(i, chosen)

        btn.callback = callback
        view.add_item(btn)

    await interaction.response.send_message(
        f"🎨 Choose a color for **{clan_name}Clan**:",
        view=view
    )
# ----------------------- EVENTS -----------------------
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands globally")
    print(f"{bot.user} is online!")
    load_game_state()  # Load saved game state on startup
    
    # Start background tasks
    if not automatic_aging_task.is_running():
        automatic_aging_task.start()
        print("✅ Automatic aging task started")
    
    if not season_cycling_task.is_running():
        season_cycling_task.start()
        print("✅ Season cycling task started")

@bot.event
async def on_message(message):
    """Track activity and award points for messages"""
    # Ignore bot messages
    if message.author.bot:
        return
    
    uid = message.author.id
    
    # Award activity points for non-command messages
    if not message.content.startswith("/"):
        if uid not in activity_points:
            activity_points[uid] = 0
        activity_points[uid] += ACTIVITY_POINTS_REWARD
    
    await bot.process_commands(message)

# ----------------------- CHARACTER CREATION -----------------------
@bot.tree.command(name="kit", description="Create your kit")
async def kit(interaction: discord.Interaction, prefix: str):
    uid = interaction.user.id
    if uid in characters:
        await interaction.response.send_message("You already have a character.")
        return

    stats = generate_stats()
    current_time = time.time()
    characters[uid] = {
        "prefix": prefix,
        "rank": "kit",
        "moons": 0,
        "suffix": None,
        "clan": None,
        "health": 100,
        "stats": stats,
        "specialty": None,
        "skill_value": 0,
        "hunger": 50,
        "training_sessions": 0,
        "exhaustion": 0,
        "alive": True,
        "injury_degree": 0,  # 0=none, 1=minor, 2=moderate, 3=severe, 4=critical
        "last_aged": current_time  # Track when character was last aged
    }

    await interaction.response.send_message(
        f"🐾 **{prefix}kit** has been born!"
    )
    save_game_state()
# ----------------------- PREGNANCY SYSTEM -----------------------
# Pregnancy rules:
# - Full warriors, 12 moons minimum
# - 5 moons gestation
# - Increased hunger, affected by camp quality and mother’s activity
# - Battle and training effectiveness reduced
# - Mother and partner consent required

def pregnancy_hunger_modifier(stage):
    """Additional hunger per moon of pregnancy"""
    return stage * 5  # can be adjusted

def battle_penalty(stage):
    """Multiplier for battle effectiveness depending on pregnancy stage"""
    if stage <= 2: 
        return 1.0  # early, no effect
    elif stage <= 4: 
        return 0.8  # mid
    else: 
        return 0.6  # late

def pregnancy_effect_on_kits(mother_char, camp_quality):
    """Determine expected kit health/number based on mother and camp"""
    base_kits = random.randint(1, 4)
    health_modifier = 1.0

    # Reduce if camp is poor
    if camp_quality < 50:
        health_modifier -= 0.2
    if mother_char.get("training_sessions", 0) > 3:
        health_modifier -= 0.1  # overworked
    if mother_char.get("hunger", 50) < 40:
        health_modifier -= 0.2  # underfed

    kit_health = max(1, int(100 * health_modifier))
    return base_kits, kit_health

# ---------------- PROPOSE BREEDING ----------------
@bot.tree.command(name="propose_breeding", description="Propose breeding with another full warrior")
async def propose_breeding(interaction: discord.Interaction, partner: discord.Member, carrier: str):
    """
    carrier: 'mother' or 'father' (who will carry the kits)
    """
    uid = interaction.user.id
    pid = partner.id

    if uid not in characters or pid not in characters:
        await interaction.response.send_message("Both must have characters.")
        return

    mother, father = (characters[uid], characters[pid]) if carrier.lower() == "mother" else (characters[pid], characters[uid])

    # Checks
    for char in [mother, father]:
        if char["rank"] != "warrior":
            await interaction.response.send_message("Both characters must be full warriors.")
            return
        if char.get("moons", 0) < 12:
            await interaction.response.send_message("Both characters must be at least 12 moons old.")
            return
        if char.get("pregnant"):
            await interaction.response.send_message("One of the characters is already pregnant.")
            return

    # Consent check (both must agree)
    breeding_request = {
        "proposer": uid,
        "partner": pid,
        "carrier": carrier.lower()
    }
    pending_breeding[(uid, pid)] = breeding_request

    view = View()

    async def accept(i):
        if i.user.id != pid:
            await i.response.send_message("Only the proposed partner can accept.", ephemeral=True)
            return

        # Start pregnancy
        mother["pregnant"] = {
            "months": 0,
            "partner": father["prefix"],
            "carrier": carrier.lower(),
            "season": season
        }

        pending_breeding.pop((uid, pid), None)

        await i.response.edit_message(content=f"🌱 Pregnancy begun! **{mother['prefix']}** is carrying kits.", view=None)
        save_game_state()

    async def decline(i):
        if i.user.id != pid:
            await i.response.send_message("Only the proposed partner can decline.", ephemeral=True)
            return
        pending_breeding.pop((uid, pid), None)
        await i.response.edit_message(content="❌ Breeding proposal declined.", view=None)

    btn_accept = Button(label="Accept", style=discord.ButtonStyle.green)
    btn_decline = Button(label="Decline", style=discord.ButtonStyle.red)
    btn_accept.callback = accept
    btn_decline.callback = decline
    view.add_item(btn_accept)
    view.add_item(btn_decline)

    await interaction.response.send_message(
        f"🌱 **{characters[uid]['prefix']}** proposes breeding to **{characters[pid]['prefix']}**.\n"
        f"Carrier: {carrier.lower()}. Does {characters[pid]['prefix']} agree?",
        view=view
    )
# ---------------- PREGNANCY STATUS ----------------
@bot.tree.command(name="pregnancy_status", description="Check pregnancy progress")
async def pregnancy_status(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)
    if not char or not char.get("pregnant"):
        await interaction.response.send_message("You are not pregnant.")
        return

    months = char["pregnant"]["months"]
    carrier = char["pregnant"]["carrier"]
    suggestions = []
    if char["hunger"] < 60:
        suggestions.append("Eat more to support your kits.")
    if char.get("training_sessions", 0) > 2:
        suggestions.append("Avoid overtraining to keep kits healthy.")
    if camp_quality[char["clan"]] < 50:
        suggestions.append("Help improve camp quality for kit health.")

    suggestion_msg = "\n".join(suggestions) if suggestions else "You're doing well. Keep resting and eating!"
    await interaction.response.send_message(f"🌱 Month {months+1}/5, Carrier: {carrier}\n💡 Suggestions:\n{suggestion_msg}")
# ----------------------- AGE COMMAND -----------------------
import random

@bot.tree.command(name="age", description="Age up one moon")
async def age(interaction: discord.Interaction):

    uid = interaction.user.id
    char = characters.get(uid)

    if not char:
        await interaction.response.send_message("❌ You don't have a character yet. Use /kit.")
        return

    # Increase age
    char["age"] = char.get("age", 0) + 1

    # Hunger loss from aging
    char["hunger"] = max(char.get("hunger", 100) - 10, 0)

    message = f"🌙 **{char['prefix']}** is now **{char['age']} moons old!**"

    # Apprentice milestone
    if char["age"] == 6:
        message += "\n🐾 You are **old enough to become an apprentice!** Ask a leader for training."

    # Warrior eligibility
    if char["age"] == 12:
        message += "\n⭐ You are **eligible to become a warrior!** A leader may perform your warrior ceremony."

    # Pregnancy progression
    if char.get("pregnant"):

        char["pregnant"]["months"] += 1
        months = char["pregnant"]["months"]

        message += f"\n🤰 Pregnancy progressed to **{months}/5 moons**."

        if months >= 5:

            kits = random.randint(1, 4)

            message += f"\n🐣 **{char['prefix']} has given birth to {kits} kits!**"

            char["pregnant"] = None

    # Check for starvation damage
    damage_applied, damage_amount = apply_hunger_damage(char)
    if damage_applied:
        message += f"\n⚠️ **{char['prefix']} suffered {damage_amount} damage from starvation!**"
        if not char["alive"]:
            message += " **💀 They did not survive!**"
    
    update_injury_degree(char)

    await interaction.response.send_message(message)
    save_game_state()
    
@bot.tree.command(name="choose_suffix", description="Choose your future warrior suffix")
async def choose_suffix(interaction: discord.Interaction, suffix: str):
    uid = interaction.user.id
    char = characters.get(uid)

    if not char:
        await interaction.response.send_message("❌ You don't have a character.")
        return

    if char["rank"] != "apprentice":
        await interaction.response.send_message("⚠️ Only apprentices can choose a warrior suffix.")
        return

    # Clean suffix input
    suffix = suffix.lower().strip()

    # Prevent paw suffix
    if suffix == "paw":
        await interaction.response.send_message("⚠️ You cannot choose 'paw' as a warrior suffix.")
        return

    char["future_suffix"] = suffix

    await interaction.response.send_message(
        f"🌟 Your future warrior name will be **{char['prefix']}{suffix}** when you are promoted."
    )
    
@bot.tree.command(name="make_warrior", description="Promote an apprentice to warrior")
async def make_warrior(interaction: discord.Interaction, member: discord.Member):
    uid = member.id
    char = characters.get(uid)

    if not char:
        await interaction.response.send_message("❌ That user doesn't have a character.")
        return

    if char.get("rank") != "apprentice":
        await interaction.response.send_message("⚠️ Only apprentices can be promoted to warrior.")
        return

    suffix = char.get("future_suffix")
    if not suffix:
        await interaction.response.send_message("⚠️ They need to choose a suffix first using /choose_suffix.")
        return

    moons = char.get("moons", 0)
    if moons < 12:
        await interaction.response.send_message(
            f"⚠️ They are only **{moons} moons old**. Not ready to become a warrior."
        )
        return

    clan = char.get("clan", "Unknown")

    old_name = f"{char['prefix']}paw"
    new_name = f"{char['prefix']}{suffix}"

    # ---------------- PERMANENT STAT BOOST ----------------
    stats = char.get("stats", {})

    stats["strength"] += 2
    stats["speed"] += 1
    stats["dexterity"] += 1

    # Clan bonus
    if clan == "Thunder":
        stats["strength"] += 1
    elif clan == "River":
        stats["perception"] += 1
    elif clan == "Shadow":
        stats["dexterity"] += 1
    elif clan == "Wind":
        stats["speed"] += 1

    char["stats"] = stats

    # ---------------- TEMPORARY BUFF ----------------
    char["warrior_buff"] = {
        "active": True,
        "expires_in": 1,  # lasts 1 moon
        "bonus": {
            "strength": 2,
            "speed": 2
        }
    }

    # Promote
    char["rank"] = "warrior"
    char["suffix"] = suffix
    char.pop("future_suffix", None)

    # Ceremony
    ceremony = (
        "🌟 **Warrior Ceremony** 🌟\n\n"
        "Let all cats old enough to catch their own prey gather beneath the Highrock.\n\n"
        f"\"**{old_name}**, you have trained hard and proven yourself loyal and brave.\"\n\n"
        f"\"From this moment forward, you will be known as **{new_name}**.\"\n\n"
        f"\"StarClan honors your courage and welcomes you as a full warrior.\"\n\n"
        f"🔥 **{new_name} feels a surge of strength and confidence!**\n"
        f"(+Stat boosts & temporary buff for this moon)\n\n"
        f"🎉 **{new_name}! {new_name}! {new_name}!**"
    )

    await interaction.response.send_message(ceremony)
    save_game_state()
# ----------------------- TAKE PREY -----------------------
@bot.tree.command(name="take_prey", description="Take prey from the clan pile to eat")
async def take_prey(interaction: discord.Interaction):

    uid = interaction.user.id
    char = characters.get(uid)

    if not char:
        await interaction.response.send_message("❌ You don't have a character.")
        return

    clan = char.get("clan")

    if not clan:
        await interaction.response.send_message("⚠️ You are not in a clan.")
        return

    if clan_prey_piles.get(clan, 0) <= 0:
        await interaction.response.send_message("❌ The fresh-kill pile is empty.")
        return

    # Take food
    clan_prey_piles[clan] -= 10

    char["hunger"] = min(char["hunger"] + 40, 100)

    await interaction.response.send_message(
        f"🍖 You took prey from the pile and ate.\n"
        f"Hunger: **{char['hunger']}/100**"
    )
    save_game_state()
# ----------------------- PROFILE -----------------------
@bot.tree.command(name="profile", description="View your character profile")
async def profile(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)

    if not char:
        await interaction.response.send_message("❌ You don't have a character yet. Use /kit.")
        return

    name = f"{char['prefix']}{char.get('suffix','')}"
    rank = char.get("rank", "unknown")
    clan = char.get("clan", "None")
    moons = char.get("moons", 0)
    hunger = char.get("hunger", 0)
    health = char.get("health", 100)
    alive = char.get("alive", True)

    status = "Alive 🐾" if alive else "Dead 💀"

    # Create progress bars
    health_bar = create_progress_bar(health, 100)
    hunger_bar = create_progress_bar(hunger, 100)

    stats = char.get("stats", {})

    embed = discord.Embed(
        title=f"🐾 {name}",
        description=f"{rank.title()} of **{clan}Clan**",
        color=discord.Color.green()
    )

    # Health & Status section
    embed.add_field(
        name="❤️ Health",
        value=f"{health_bar}\n**{health}/100 HP**",
        inline=False
    )

    # Hunger section
    embed.add_field(
        name="🍖 Hunger",
        value=f"{hunger_bar}\n**{hunger}/100**",
        inline=False
    )

    # Injury Status
    injury_degree = char.get("injury_degree", 0)
    injury_description = get_injury_description(injury_degree)
    embed.add_field(
        name="🩹 Injury Status",
        value=injury_description,
        inline=False
    )

    # Basic Info
    embed.add_field(
        name="📋 Basic Info",
        value=(
            f"Age: **{moons} moons**\n"
            f"Status: **{status}**"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Stats",
        value=(
            f"Strength: **{stats.get('strength', 0)}**\n"
            f"Perception: **{stats.get('perception', 0)}**\n"
            f"Dexterity: **{stats.get('dexterity', 0)}**\n"
            f"Speed: **{stats.get('speed', 0)}**\n"
            f"Intelligence: **{stats.get('intelligence', 0)}**\n"
            f"Luck: **{stats.get('luck', 0)}**\n"
            f"Charisma: **{stats.get('charisma', 0)}**"
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed)

# ----------------------- ACTIVITY POINTS COMMANDS -----------------------
@bot.tree.command(name="my_points", description="Check your activity points")
async def my_points(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character yet. Use /kit.")
        return
    
    points = activity_points.get(uid, 0)
    char = characters[uid]
    
    embed = discord.Embed(
        title=f"🌟 {char['prefix']}'s Activity Points",
        description=f"You have **{points}** activity points!",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="💰 Shop Prices",
        value=(
            f"• Age up 1 moon: **{AGE_UP_COST} points**\n"
            f"• Train once: **{TRAINING_SESSION_COST} points**"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="battle_moves", description="See all buyable battle moves for your clan")
async def battle_moves(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character. Use /kit to create one.")
        return
    
    char = characters[uid]
    clan = char.get("clan", "Unknown")
    points = activity_points.get(uid, 0)
    
    # Get clan-specific moves
    clan_moves = BUYABLE_MOVES.get(clan, [])
    
    if not clan_moves:
        await interaction.response.send_message(f"❌ {clan}Clan has no special moves available. Join a clan first with /clan!")
        return
    
    embed = discord.Embed(
        title=f"⚔️ {clan}Clan Battle Moves",
        description=f"💰 You have **{points}** activity points\n\nUse these moves in battle via the **Move Shop** button!",
        color=discord.Color.red()
    )
    
    physical_moves = [m for m in clan_moves if m["type"] == "physical"]
    charge_moves = [m for m in clan_moves if m["type"] == "charge"]
    status_moves = [m for m in clan_moves if m["type"] == "status"]
    
    if physical_moves:
        embed.add_field(
            name="💥 Physical Moves",
            value="\n".join([f"• {m['name']} - **{m['cost']}pts**" for m in physical_moves]),
            inline=False
        )
    
    if charge_moves:
        embed.add_field(
            name="⚡ Charge Moves (2-turn)",
            value="\n".join([f"• {m['name']} - **{m['cost']}pts**" for m in charge_moves]),
            inline=False
        )
    
    if status_moves:
        embed.add_field(
            name="✨ Support Moves",
            value="\n".join([f"• {m['name']} - **{m['cost']}pts**" for m in status_moves]),
            inline=False
        )
    
    embed.set_footer(text="💡 Damage scales with your stats! Higher stats = higher damage!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="age_with_points", description="Spend points to age up")
async def age_with_points(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character.")
        return
    
    points = activity_points.get(uid, 0)
    if points < AGE_UP_COST:
        await interaction.response.send_message(
            f"❌ Not enough points! You have **{points}/{AGE_UP_COST}** points needed."
        )
        return
    
    char = characters[uid]
    
    # Deduct points
    activity_points[uid] -= AGE_UP_COST
    
    # Age up the character
    char["moons"] = char.get("moons", 0) + 1
    char["hunger"] = max(char.get("hunger", 100) - 10, 0)
    
    message = f"🌙 **{char['prefix']}** is now **{char['moons']} moons old!**"
    
    # Apprentice milestone
    if char["moons"] == 6:
        message += "\n🐾 You are **old enough to become an apprentice!** Ask a leader for training."
    
    # Warrior eligibility
    if char["moons"] == 12:
        message += "\n⭐ You are **eligible to become a warrior!** A leader may perform your warrior ceremony."
    
    # Pregnancy progression
    if char.get("pregnant"):
        char["pregnant"]["months"] += 1
        months = char["pregnant"]["months"]
        message += f"\n🤰 Pregnancy progressed to **{months}/5 moons**."
        
        if months >= 5:
            kits = random.randint(1, 4)
            message += f"\n🐣 **{char['prefix']} has given birth to {kits} kits!**"
            char["pregnant"] = None
    
    # Check for starvation damage
    damage_applied, damage_amount = apply_hunger_damage(char)
    if damage_applied:
        message += f"\n⚠️ **{char['prefix']} suffered {damage_amount} damage from starvation!**"
        if not char["alive"]:
            message += " **💀 They did not survive!**"
    
    update_injury_degree(char)
    
    message += f"\n\n💸 Spent {AGE_UP_COST} points! Remaining: **{activity_points[uid]}**"
    
    await interaction.response.send_message(message)
    save_game_state()

@bot.tree.command(name="train_with_points", description="Spend points to train")
async def train_with_points(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character.")
        return
    
    points = activity_points.get(uid, 0)
    if points < TRAINING_SESSION_COST:
        await interaction.response.send_message(
            f"❌ Not enough points! You have **{points}/{TRAINING_SESSION_COST}** points needed."
        )
        return
    
    char = characters[uid]
    
    if not char.get("alive", True):
        await interaction.response.send_message("❌ Your character is dead.")
        return
    
    if not pregnancy_train_allowed(char):
        await interaction.response.send_message("⚠️ You are too far along in pregnancy to train safely.")
        return
    
    # Deduct points
    activity_points[uid] -= TRAINING_SESSION_COST
    
    # Train the character
    char["strength"] = char.get("strength", 10) + 1
    char["training_sessions"] = char.get("training_sessions", 0) + 1
    hunger_cost = -5
    char["hunger"] = max(0, char["hunger"] + hunger_cost)
    
    message = f"💪 **{char['prefix']}** trains hard and gains +1 strength!\n"
    message += f"💸 Spent {TRAINING_SESSION_COST} points! Remaining: **{activity_points[uid]}**\n"
    message += f"Hunger: **{char['hunger']}/100**"
    
    await interaction.response.send_message(message)
    save_game_state()

# ----------------------- HEALING ITEMS COMMANDS -----------------------
@bot.tree.command(name="buy_heal", description="Buy healing items with activity points")
async def buy_heal(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character yet. Use /kit.")
        return
    
    points = activity_points.get(uid, 0)
    
    embed = discord.Embed(
        title="🧪 Healing Item Shop",
        description=f"💰 You have **{points}** activity points",
        color=discord.Color.green()
    )
    
    # Consumable items
    embed.add_field(
        name="📦 Consumable Items (Stackable)",
        value="\n".join([f"• {item['name']}: **{item['heal']} HP** - {item['cost']} pts" 
                        for item in HEALING_ITEMS["consumable"]]),
        inline=False
    )
    
    # One-time items
    one_time_text = ""
    for item in HEALING_ITEMS["one_time"]:
        already_bought = item["name"] in one_time_purchases.get(uid, [])
        status = "✅ Already Purchased" if already_bought else "⭐ Available for Purchase"
        one_time_text += f"• {item['name']}: **{item['heal']} HP** - {item['cost']} pts [{status}]\n"
    
    embed.add_field(
        name="💎 One-Time Purchases (Legendary)",
        value=one_time_text,
        inline=False
    )
    
    embed.set_footer(text="Use /use_heal to consume a healing item outside of battle!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy_consumable", description="Buy a consumable healing item")
async def buy_consumable(interaction: discord.Interaction, item_name: str):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character.")
        return
    
    # Find the item
    item = None
    for h_item in HEALING_ITEMS["consumable"]:
        if h_item["name"].lower() == item_name.lower():
            item = h_item
            break
    
    if not item:
        await interaction.response.send_message(f"❌ Item '{item_name}' not found!")
        return
    
    points = activity_points.get(uid, 0)
    if points < item["cost"]:
        await interaction.response.send_message(
            f"❌ Not enough points! You have {points}, need {item['cost']}."
        )
        return
    
    # Deduct points
    activity_points[uid] -= item["cost"]
    
    # Add consumable to inventory
    if uid not in healing_consumables:
        healing_consumables[uid] = {}
    
    if item["name"] not in healing_consumables[uid]:
        healing_consumables[uid][item["name"]] = 0
    
    healing_consumables[uid][item["name"]] += 1
    
    char = characters[uid]
    await interaction.response.send_message(
        f"✅ Purchased **{item['name']}** (Restores {item['heal']} HP)!\n"
        f"💸 Spent {item['cost']} points! Remaining: **{activity_points[uid]}**\n"
        f"📦 Owned: **{healing_consumables[uid][item['name']]}**"
    )
    save_game_state()

@bot.tree.command(name="buy_legendary", description="Buy a one-time legendary healing item")
async def buy_legendary(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character.")
        return
    
    item = HEALING_ITEMS["one_time"][0]  # The legendary elixir
    
    # Check if already purchased
    if uid in one_time_purchases and item["name"] in one_time_purchases[uid]:
        await interaction.response.send_message(
            f"❌ You've already purchased **{item['name']}**! It can only be bought once."
        )
        return
    
    points = activity_points.get(uid, 0)
    if points < item["cost"]:
        await interaction.response.send_message(
            f"❌ Not enough points! You have {points}, need {item['cost']}."
        )
        return
    
    # Deduct points and mark as purchased
    activity_points[uid] -= item["cost"]
    
    if uid not in one_time_purchases:
        one_time_purchases[uid] = []
    one_time_purchases[uid].append(item["name"])
    
    char = characters[uid]
    await interaction.response.send_message(
        f"🌟 **LEGENDARY PURCHASE UNLOCKED!**\n\n"
        f"You now own **{item['name']}** (Full restoration - {item['heal']} HP)!\n"
        f"💸 Spent {item['cost']} points! Remaining: **{activity_points[uid]}**\n"
        f"⭐ This is a one-time only item!"
    )
    save_game_state()

@bot.tree.command(name="use_heal", description="Use a healing item to restore health")
async def use_heal(interaction: discord.Interaction, item_name: str):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character.")
        return
    
    char = characters[uid]
    
    # Check if item is owned
    item = None
    is_consumable = False
    
    # Check consumables
    if uid in healing_consumables and item_name in healing_consumables[uid]:
        for h_item in HEALING_ITEMS["consumable"]:
            if h_item["name"] == item_name:
                item = h_item
                is_consumable = True
                break
    
    # Check one-time items
    if not item and uid in one_time_purchases and item_name in one_time_purchases[uid]:
        for h_item in HEALING_ITEMS["one_time"]:
            if h_item["name"] == item_name:
                item = h_item
                is_consumable = False
                break
    
    if not item:
        await interaction.response.send_message(f"❌ You don't own **{item_name}**!")
        return
    
    # Use the item
    old_health = char["health"]
    char["health"] = min(char["health"] + item["heal"], 100)
    healed = char["health"] - old_health
    
    message = f"🧪 Used **{item['name']}**!\n"
    message += f"❤️ Restored **{healed} HP**!\n"
    message += f"Health: **{char['health']}/100**"
    
    # Remove from inventory
    if is_consumable:
        healing_consumables[uid][item_name] -= 1
        if healing_consumables[uid][item_name] <= 0:
            del healing_consumables[uid][item_name]
        message += f"\n📦 Remaining: **{healing_consumables[uid].get(item_name, 0)}**"
    else:
        message += f"\n⭐ (One-time item - permanently used)"
    
    await interaction.response.send_message(message)
    save_game_state()

@bot.tree.command(name="inventory", description="Check your healing items inventory")
async def inventory(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character.")
        return
    
    char = characters[uid]
    
    embed = discord.Embed(
        title=f"📦 {char['prefix']}'s Inventory",
        color=discord.Color.purple()
    )
    
    # Consumables
    consumable_text = ""
    if uid in healing_consumables and healing_consumables[uid]:
        for item_name, count in healing_consumables[uid].items():
            consumable_text += f"• {item_name} x**{count}**\n"
    else:
        consumable_text = "Empty"
    
    embed.add_field(
        name="📦 Consumables (Stackable)",
        value=consumable_text,
        inline=False
    )
    
    # One-time items
    one_time_text = ""
    if uid in one_time_purchases and one_time_purchases[uid]:
        for item_name in one_time_purchases[uid]:
            one_time_text += f"✅ {item_name}\n"
    else:
        one_time_text = "None"
    
    embed.add_field(
        name="💎 Legendary Items",
        value=one_time_text,
        inline=False
    )
    
    embed.set_footer(text="Use /use_heal <item_name> to consume an item!")
    
    await interaction.response.send_message(embed=embed)

# ----------------------- CLAN COMMAND -----------------------
@bot.tree.command(name="clan", description="Join a clan")
async def clan(interaction: discord.Interaction, clan_name: str):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character.")
        return
    clan_name = clan_name.capitalize()
    if clan_name not in clan_specialties:
        await interaction.response.send_message("Valid clans: Thunder, River, Shadow, Wind.")
        return
    char = characters[uid]
    char["clan"] = clan_name
    char["specialty"] = clan_specialties[clan_name]
    char["skill_value"] = random.randint(4,10)
    member = interaction.guild.get_member(uid)
    role_name = f"{clan_name}Clan"
    clan_roles = ["ThunderClan", "RiverClan", "ShadowClan", "WindClan"]
    for role in interaction.guild.roles:
        if role.name in clan_roles and role in member.roles:
            await member.remove_roles(role)
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
    await interaction.response.send_message(
        f"{char['prefix']} has joined **{clan_name}Clan**!\n"
        f"Clan skill: **{char['specialty']} ({char['skill_value']})** 🐾"
    )
    save_game_state()

@bot.tree.command(name="clan_status", description="Check your clan's status and recent events")
async def clan_status(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character yet. Use /kit.")
        return
    
    char = characters[uid]
    clan_name = char.get("clan")
    
    if not clan_name:
        await interaction.response.send_message("⚠️ You haven't joined a clan yet! Use /clan.")
        return
    
    # Get clan stats
    quality = camp_quality.get(clan_name, 50)
    prey_piles = clan_prey_piles.get(clan_name, 0)
    members = get_clan_members(clan_name)
    
    # Create emoji indicator for quality
    if quality >= 80:
        quality_emoji = "🟩"
    elif quality >= 50:
        quality_emoji = "🟨"
    elif quality >= 20:
        quality_emoji = "🟧"
    else:
        quality_emoji = "🟥"
    
    # Create embed
    embed = discord.Embed(
        title=f"🐾 {clan_name}Clan Status",
        description=f"Camp Condition: {quality_emoji} **{quality}/100**",
        color=discord.Color.blue()
    )
    
    # Clan Status
    embed.add_field(
        name="📊 Clan Status",
        value=(
            f"Members: **{len(members)}**\n"
            f"Prey Piles: **{prey_piles} points**\n"
            f"Camp Quality: **{quality}/100**"
        ),
        inline=False
    )
    
    # Recent Events (last 5)
    if clan_name in clan_events and clan_events[clan_name]:
        recent_events = clan_events[clan_name][-5:]
        events_text = ""
        for evt in reversed(recent_events):
            severity_emoji = {"MINOR": "🟡", "MODERATE": "🟠", "MAJOR": "🔴"}
            emoji = severity_emoji.get(evt["severity"], "⚪")
            events_text += f"{emoji} {evt['event']}\n"
        
        embed.add_field(
            name="📜 Recent Events",
            value=events_text or "No events yet!",
            inline=False
        )
    else:
        embed.add_field(
            name="📜 Recent Events",
            value="No events yet! Your clan is peaceful for now...",
            inline=False
        )
    
    # Clan Members Health Summary
    healthy = sum(1 for uid, m in members if m.get("health", 100) >= 80)
    injured = sum(1 for uid, m in members if 40 <= m.get("health", 100) < 80)
    critical = sum(1 for uid, m in members if m.get("health", 100) < 40)
    
    embed.add_field(
        name="❤️ Member Health Overview",
        value=(
            f"🟩 Healthy: **{healthy}**\n"
            f"🟧 Injured: **{injured}**\n"
            f"🟥 Critical: **{critical}**"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="trigger_event", description="Manually trigger a random event (testing)")
async def trigger_event(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("❌ You don't have a character yet. Use /kit.")
        return
    
    char = characters[uid]
    clan_name = char.get("clan")
    
    if not clan_name:
        await interaction.response.send_message("⚠️ You haven't joined a clan yet! Use /clan.")
        return
    
    # Trigger a random event
    event, severity, effects = trigger_random_event(clan_name)
    
    # Build response message
    severity_emoji = {"MINOR": "🟡", "MODERATE": "🟠", "MAJOR": "🔴"}
    emoji = severity_emoji.get(severity, "⚪")
    
    message = f"{emoji} **{event['name']}**\n{event['description']}\n\n"
    
    # Show effects
    if "camp_quality" in effects:
        new_quality = camp_quality[clan_name]
        message += f"🏕️ Camp Quality: {new_quality}/100\n"
    if "clan_prey_piles" in effects:
        message += f"🍖 Prey Piles: {clan_prey_piles[clan_name]} points\n"
    
    save_game_state()
    
    await interaction.response.send_message(message)

# ----------------------- HUNT / EAT / DONATE -----------------------
from discord.ui import View, Button

@bot.tree.command(name="hunt", description="Go hunting to gather food")
async def hunt(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)

    if not char:
        await interaction.response.send_message("❌ You don't have a character yet. Use /kit.")
        return
    if not char.get("clan"):
        await interaction.response.send_message("⚠️ You need to join a clan first with /clan.")
        return

    # Pregnancy penalty
    preg_penalty = pregnancy_hunt_modifier(char)

    # Base hunt chance
    base_success = 70 - preg_penalty
    hunger = char["hunger"]

    # Modify based on hunger
    if hunger <= 0:
        base_success -= 40
    elif hunger < 20:
        base_success -= 20
    elif hunger < 40:
        base_success -= 10
    elif hunger >= 90:
        base_success -= 15

    roll = random.randint(1, 100)
    success = roll <= base_success

    # Reduce hunger for effort
    char["hunger"] = max(0, char["hunger"] - (5 + preg_penalty))

    if success:
        prey = random.choice(list(prey_tables[char["clan"]][season].keys()))
        value = prey_tables[char["clan"]][season][prey]

        # Store pending hunt
        pending_hunts[uid] = {"prey": prey, "value": value, "clan": char["clan"], "caught": False}

        # Create buttons
        view = View()

        async def eat_callback(i):
            if i.user.id != uid:
                await i.response.send_message("This isn't your hunt!", ephemeral=True)
                return
            # Stealth roll
            stealth_roll = random.randint(1, 100)
            stealth = char.get("stats", {}).get("dexterity", 5) * 10  # dexterity ×10%
            if stealth_roll > stealth:
                pending_hunts[uid]["caught"] = True
                await i.response.edit_message(content=f"❌ You were caught trying to eat the prey! You can't eat again until you age up.", view=None)
                return
            hunger_gain = 50
            if char.get("pregnant"):
                hunger_gain += char["pregnant"]["months"] * 5
            char["hunger"] = min(char["hunger"] + hunger_gain, 100)
            pending_hunts.pop(uid, None)
            await i.response.edit_message(content=f"🍖 You ate the **{prey}**!\nYou feel a little guilty for breaking the Warrior code but it seems like you got away with it.\nHunger: {char['hunger']}/100", view=None)

        async def donate_callback(i):
            if i.user.id != uid:
                await i.response.send_message("This isn't your hunt!", ephemeral=True)
                return
            fresh_kill_piles[char["clan"]].append(prey)
            clan_prey_piles[char["clan"]] += value
            pending_hunts.pop(uid, None)
            await i.response.edit_message(content=f"🐾 Added **{prey}** to **{char['clan']}Clan** fresh kill pile!", view=None)

        btn_eat = Button(label="Eat", style=discord.ButtonStyle.green)
        btn_donate = Button(label="Donate", style=discord.ButtonStyle.blurple)
        btn_eat.callback = eat_callback
        btn_donate.callback = donate_callback
        view.add_item(btn_eat)
        view.add_item(btn_donate)

        await interaction.response.send_message(
            f"🎯 **Hunt successful!** You caught a **{prey}** worth {value} points.\nHunger: {char['hunger']}/100",
            view=view
        )
    else:
        await interaction.response.send_message(
            f"❌ Hunt failed. No prey this time.\nHunger: {char['hunger']}/100"
        )
    save_game_state()
# ----------------------- MEDICINE CAT -----------------------
@bot.tree.command(name="see_medicine_cat", description="Heal yourself via medicine cat")
async def see_medicine_cat(interaction: discord.Interaction):
    uid = interaction.user.id
    if in_battle(uid):
        await interaction.response.send_message("⚔️ You cannot visit the medicine cat during battle.")
        return
    char = characters.get(uid)
    if not char:
        await interaction.response.send_message("You don't have a character.")
        return
    if char["health"] >= 100:
        await interaction.response.send_message("You are already healthy.")
        return
    if not char["clan"]:
        await interaction.response.send_message("Join a clan first.")
        return
    heal = random.randint(10,35)
    old = char["health"]
    char["health"] = min(100, char["health"] + heal)
    healed = char["health"] - old
    clan = char["clan"]
    camp_quality[clan] = max(0, camp_quality[clan] - 2)
    await interaction.response.send_message(f"🌿 The medicine cat treats your wounds.\nRecovered **{healed} HP**.\nHealth: **{char['health']}/100**")
    save_game_state()

# ----------------------- TRAIN COMMAND -----------------------
@bot.tree.command(name="train", description="Train your character to improve stats.")
async def train(interaction: discord.Interaction):
    user_id = interaction.user.id
    char = characters.get(user_id)
    if not char or not char.get("alive", True):
        await interaction.response.send_message("❌ You don't have a living character.")
        return

    if not pregnancy_train_allowed(char):
        await interaction.response.send_message("⚠️ You are too far along in pregnancy to train safely.")
        return

    char["strength"] = char.get("strength", 10) + 1
    hunger_cost = -5
    char["hunger"] = max(0, char["hunger"] + hunger_cost + pregnancy_hunt_modifier(char))

    await interaction.response.send_message(
        f"💪 {char['prefix']} trains and gains +1 strength!\nHunger: {char['hunger']}"
    )
    save_game_state()
# ----------------------- BATTLE SYSTEM -----------------------
from discord.ui import View, Button

@bot.tree.command(name="attack", description="Challenge someone to battle")
async def attack(interaction: discord.Interaction, opponent: discord.Member):
    uid = interaction.user.id
    oid = opponent.id

    if uid == oid:
        await interaction.response.send_message("❌ You cannot fight yourself.")
        return

    attacker = characters.get(uid)
    defender = characters.get(oid)

    if not attacker or not defender:
        await interaction.response.send_message("❌ One of you doesn't have a character.")
        return

    if attacker["hunger"] < 10:
        await interaction.response.send_message(
            f"🥀 {attacker['prefix']} is too hungry to fight!"
        )
        return

    pending_battles[oid] = uid

    view = View()

    async def accept(i):
        if i.user.id != oid:
            await i.response.send_message("❌ Only the challenged player can accept.", ephemeral=True)
            return

        # Initiate battle state
        battle_state[(uid, oid)] = {
            "attacker": uid,
            "defender": oid,
            "turn": uid,
            "charge": {}
        }

        await i.response.edit_message(content="⚔️ Battle accepted!", view=None)
        await prompt_turn(i, uid, oid)

    async def decline(i):
        if i.user.id != oid:
            await i.response.send_message("❌ Only the challenged player can decline.", ephemeral=True)
            return
        pending_battles.pop(oid, None)
        await i.response.edit_message(content="❌ Battle declined.", view=None)

    btn_accept = Button(label="Accept", style=discord.ButtonStyle.green)
    btn_decline = Button(label="Decline", style=discord.ButtonStyle.red)
    btn_accept.callback = accept
    btn_decline.callback = decline
    view.add_item(btn_accept)
    view.add_item(btn_decline)

    await interaction.response.send_message(
        f"⚔️ **{attacker['prefix']}** challenges **{defender['prefix']}**!",
        view=view
    )

async def prompt_turn(interaction, attacker_id, defender_id):
    battle = battle_state.get((attacker_id, defender_id))
    if not battle:
        return

    turn_id = battle["turn"]
    char = characters[turn_id]
    moves = MOVES.get(char["clan"], [])

    view = View(timeout=60)

    for move in moves:
        async def callback(i, move=move):
            if i.user.id != turn_id:
                await i.response.send_message("❌ It's not your turn.", ephemeral=True)
                return
            await execute_move(i, attacker_id, defender_id, move)

        btn = Button(label=move["name"], style=discord.ButtonStyle.blurple)
        btn.callback = callback
        view.add_item(btn)

    # Add shop button
    async def shop_callback(i):
        if i.user.id != turn_id:
            await i.response.send_message("❌ It's not your turn.", ephemeral=True)
            return
        await show_move_shop(i, attacker_id, defender_id)

    shop_btn = Button(label="💰 Move Shop", style=discord.ButtonStyle.success)
    shop_btn.callback = shop_callback
    view.add_item(shop_btn)

    await interaction.followup.send(
        f"🎯 **{char['prefix']}**'s turn! (Activity Points: **{activity_points.get(turn_id, 0)}**)",
        view=view
    )

async def show_move_shop(interaction, attacker_id, defender_id):
    """Show buyable moves during battle"""
    battle = battle_state.get((attacker_id, defender_id))
    if not battle:
        return

    turn_id = battle["turn"]
    char = characters[turn_id]
    clan = char.get("clan", "Unknown")
    points = activity_points.get(turn_id, 0)
    
    # Get clan-specific moves
    clan_moves = BUYABLE_MOVES.get(clan, [])

    view = View(timeout=60)

    for move in clan_moves:
        cost = move["cost"]
        affordable = "✅" if points >= cost else "❌"
        
        async def buy_callback(i, move=move):
            if i.user.id != turn_id:
                await i.response.send_message("❌ It's not your turn.", ephemeral=True)
                return
            
            cost = move["cost"]
            if activity_points.get(turn_id, 0) < cost:
                await i.response.send_message(f"❌ Not enough points! Need {cost}, have {activity_points.get(turn_id, 0)}")
                return
            
            # Deduct points
            activity_points[turn_id] -= cost
            
            # Execute the bought move
            await execute_move(i, attacker_id, defender_id, move)

        style = discord.ButtonStyle.green if points >= cost else discord.ButtonStyle.gray
        btn = Button(label=f"{move['name']} ({cost}pts)", style=style)
        btn.callback = buy_callback
        view.add_item(btn)

    # Back button
    async def back_callback(i):
        if i.user.id != turn_id:
            await i.response.send_message("❌ It's not your turn.", ephemeral=True)
            return
        await prompt_turn(i, attacker_id, defender_id)

    back_btn = Button(label="← Back", style=discord.ButtonStyle.gray)
    back_btn.callback = back_callback
    view.add_item(back_btn)

    move_list = "\n".join([f"• {m['name']} - **{m['cost']} points**" for m in clan_moves])
    
    await interaction.response.send_message(
        f"🛍️ **{clan}Clan Battle Move Shop**\n\n"
        f"💰 Your Points: **{points}**\n\n"
        f"Premium clan-exclusive moves:\n{move_list}",
        view=view,
        ephemeral=False
    )


async def execute_move(interaction, attacker_id, defender_id, move):
    battle = battle_state[(attacker_id, defender_id)]
    turn_id = battle["turn"]
    enemy_id = defender_id if turn_id == attacker_id else attacker_id

    attacker = characters[turn_id]
    defender = characters[enemy_id]

    result = ""
    # ---- Charge Moves ----
    if move["type"] == "charge":
        charge = battle["charge"].get(turn_id)
        if charge:
            # Calculate damage from stats if available, otherwise use fallback
            if "stat_multiplier" in move:
                damage = calculate_stat_damage(attacker, move["stat_multiplier"])
            else:
                damage = move.get("damage", 20)
            
            # Apply pregnancy penalty
            damage = int(damage * apply_pregnancy_effects(attacker))
            defender["health"] = max(defender["health"] - damage, 0)
            battle["charge"].pop(turn_id)
            result = f"💥 {attacker['prefix']} unleashes **{move['name']}** for **{damage} damage**!"
        else:
            battle["charge"][turn_id] = move
            result = f"⚡ {attacker['prefix']} begins charging **{move['name']}**!"

    # ---- Status Moves ----
    elif move["type"] == "status":
        buffs = move.get("buff", {})
        buff_text = ""
        if "heal" in buffs:
            attacker["health"] = min(attacker["health"] + buffs["heal"], 100)
            buff_text += f" +{buffs['heal']} HP"
        if "defense_up" in buffs:
            buff_text += f" +{buffs['defense_up']} Defense"
        if "attack_up" in buffs:
            buff_text += f" +{buffs['attack_up']} Attack"
        if "speed" in buffs:
            buff_text += f" +{buffs['speed']} Speed"
        result = f"✨ {attacker['prefix']} uses **{move['name']}**!{buff_text}"

    # ---- Physical Moves ----
    else:
        # Calculate damage from stats if available, otherwise use fallback
        if "stat_multiplier" in move:
            damage = calculate_stat_damage(attacker, move["stat_multiplier"])
        else:
            damage = move.get("damage", 15)
        
        # Apply pregnancy penalty
        damage = int(damage * apply_pregnancy_effects(attacker))
        damage = max(1, damage)
        defender["health"] = max(defender["health"] - damage, 0)
        result = f"💥 {attacker['prefix']} uses **{move['name']}** for **{damage} damage**!"

    # ---- Switch turn ----
    battle["turn"] = enemy_id
    await interaction.response.send_message(
        f"{result}\n"
        f"❤️ {attacker['prefix']} HP: {attacker['health']}\n"
        f"❤️ {defender['prefix']} HP: {defender['health']}"
    )
    save_game_state()  # Save after each move

    # ---- Check Victory ----
    if attacker["health"] <= 0 or defender["health"] <= 0:
        winner = attacker if attacker["health"] > 0 else defender
        loser = defender if winner == attacker else attacker
        battle_state.pop((attacker_id, defender_id), None)
        await interaction.followup.send(
            f"🏆 **{winner['prefix']}** wins! **{loser['prefix']}** is defeated."
        )
        save_game_state()
        return

    await prompt_turn(interaction, attacker_id, defender_id)
# ----------------------- CAMP COMMANDS -----------------------
@bot.tree.command(name="maintain_camp", description="Help maintain the camp")
async def maintain_camp(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)
    if not char:
        await interaction.response.send_message("Create a character first with /kit.")
        return
    if not char["clan"]:
        await interaction.response.send_message("Join a clan first.")
        return
    clan = char["clan"]
    improvement = random.randint(5,15)
    camp_quality[clan] = min(100, camp_quality[clan]+improvement)
    quality = camp_quality[clan]
    if quality >= 90: condition = "⭐ The camp is in excellent condition! The clan feels energized."
    elif quality >=70: condition = "🌿 The camp is clean and well maintained."
    elif quality >=40: condition = "🪶 The camp is in decent shape."
    elif quality >=15: condition = "⚠️ The camp is getting messy."
    else: condition = "🚨 The camp is falling apart!"
    await interaction.response.send_message(
        f"🧹 You help repair dens and clear debris.\n"
        f"Camp quality improved by **{improvement}** points!\n"
        f"New quality: **{quality}**\n{condition}"
    )
    save_game_state()

@bot.tree.command(name="camp_decay", description="Lower camp quality (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def camp_decay(interaction: discord.Interaction):
    for clan in camp_quality:
        camp_quality[clan] = max(0, camp_quality[clan]-5)
    await interaction.response.send_message("🌧️ Weather and time have worn down the camps. Camp quality decreased.")
    save_game_state()

# ----------------------- SEASON COMMANDS -----------------------
@bot.tree.command(name="season", description="Check the current season")
async def check_season(interaction: discord.Interaction):
    await interaction.response.send_message(f"🍃 The current season is **{season}**.")

@bot.tree.command(name="set_season", description="Change the current season (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def set_season(interaction: discord.Interaction, new_season: str):
    global season
    new_season = new_season.lower()
    if new_season not in seasons:
        await interaction.response.send_message("❌ Invalid season! Valid seasons: newleaf, greenleaf, leaf-fall, leafbare.")
        return
    season = new_season
    await interaction.response.send_message(f"🌿 The season has been changed! It is now **{season.capitalize()}**.")
    save_game_state()

# ----------------------- MANUAL SAVE -----------------------
@bot.tree.command(name="save_game", description="Manually save game state")
async def save_game(interaction: discord.Interaction):
    save_game_state()
    await interaction.response.send_message("💾 Game saved successfully! 🌿")

# ----------------------- PING -----------------------
@bot.tree.command(name="ping", description="Check if the bot is active")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("ClanTracker is active! 🐾")

# ----------------------- RUN BOT -----------------------
bot.run(TOKEN)
