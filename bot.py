import discord
from discord.ext import commands
from discord import app_commands
import os
import random

TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------- GLOBALS -----------------------
characters = {}
pending_hunts = {}
pending_battles = {}
battle_state = {}
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
        {"name": "Claw Swipe", "type": "physical", "damage": 15},
        {"name": "Pounce", "type": "physical", "damage": 20},
        {"name": "Roar", "type": "status", "buff": {"defense_up": 1, "attack_down": 1}},
        {"name": "Charge Strike", "type": "charge", "damage": 35}
    ],
    "River": [
        {"name": "Water Slash", "type": "physical", "damage": 15},
        {"name": "Dive Attack", "type": "charge", "damage": 30},
        {"name": "Soothing Ripple", "type": "status", "buff": {"heal": 10}}
    ],
    "Shadow": [
        {"name": "Shadow Pounce", "type": "physical", "damage": 20},
        {"name": "Stealth Strike", "type": "status", "buff": {"attack_up": 2}}
    ],
    "Wind": [
        {"name": "Gale Swipe", "type": "physical", "damage": 15},
        {"name": "Whirlwind", "type": "charge", "damage": 25},
        {"name": "Endurance Boost", "type": "status", "buff": {"defense_up": 2}}
    ]
}

# ----------------------- UTILITY FUNCTIONS -----------------------
def generate_stats():
    return {stat: random.randint(0, 10) for stat in ["strength","perception","dexterity","speed","intelligence","luck","charisma"]}

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

        # Seasonal modifier
        season_mod = seasonal_pregnancy_modifiers.get(season, {"health_mult": 1.0, "max_kits": 4})

        # Increase hunger due to pregnancy
        carrier["hunger"] = min(100, carrier["hunger"] + 10)

        # Factor in exhaustion, training, and camp quality
        exhaustion = carrier.get("exhaustion", 0)
        training = carrier.get("training_sessions", 0)
        camp = camp_quality.get(carrier["clan"], 50)

        base_kit_health = max(0, 100 - (exhaustion * 5 + training * 5))
        kit_health = int(base_kit_health * season_mod["health_mult"])
        data["kit_health_estimate"] = kit_health

        # Check if pregnancy is complete
        current_moon = carrier.get("moons", 0)
        if current_moon - data["start_moon"] >= 5:
            # Number of kits depends on camp + season + mother condition
            max_kits = season_mod["max_kits"]
            kit_count = max(1, min(max_kits, int((camp/25) * (kit_health/50))))
            data["kit_count"] = kit_count

            # Reset mother's status
            data["active"] = False
            carrier["hunger"] = max(carrier["hunger"] - 10, 0)

            # Spawn kits
            for _ in range(kit_count):
                kit_stats = generate_stats()
                kit_id = f"kit_{carrier_id}_{random.randint(1000,9999)}"
                characters[kit_id] = {
                    "prefix": f"{carrier['prefix']}kit",
                    "rank": "kit",
                    "moons": 0,
                    "suffix": None,
                    "clan": carrier["clan"],
                    "health": kit_health,
                    "stats": kit_stats,
                    "specialty": None,
                    "skill_value": 0,
                    "hunger": 50
                }
# ----------------------- EVENTS -----------------------
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands globally")
    print(f"{bot.user} is online!")

# ----------------------- CHARACTER CREATION -----------------------
@bot.tree.command(name="kit", description="Create your kit")
async def kit(interaction: discord.Interaction, prefix: str):
    uid = interaction.user.id
    if uid in characters:
        await interaction.response.send_message("You already have a character.")
        return
    stats = generate_stats()
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
        "training_sessions":0,
        "exhaustion":0,
        "alive": True
    }
    await interaction.response.send_message(
        f"🐾 **{prefix}kit** has been born!\n"
        f"**Stats**:\n" + "\n".join(f"{k.capitalize()}: {v}" for k,v in stats.items())
    )
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
@bot.tree.command(name="age", description="Age your character by one moon.")
async def age(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)
    if not char or not char.get("alive", True):
        await interaction.response.send_message("❌ You don't have a living character.")
        return

    # Age character by one moon
    char["moons"] = char.get("moons", 0) + 1

    # Reduce hunger slightly each moon
    hunger_cost = -10
    char["hunger"] = max(0, char["hunger"] + hunger_cost)

    # Reset training sessions and exhaustion each moon
    char["training_sessions"] = 0
    char["exhaustion"] = 0

    # Promotion: Kit → Apprentice at 6 moons
    promotion_msg = ""
    if char["rank"] == "kit" and char.get("moons", 0) >= 6:
        char["rank"] = "apprentice"
        char["suffix"] = "paw"  # update suffix to 'paw'
        promotion_msg = f"🌟 {char['prefix']} has grown into an apprentice and now has the suffix 'paw'!"

    # Hunger warnings
    hunger_msg = ""
    if char["hunger"] <= 0:
        char["alive"] = False
        await interaction.response.send_message(f"💀 {char['prefix']} has starved to death.")
        return
    elif char["hunger"] < 20:
        hunger_msg = "⚠️ You are starving and need to eat soon!"

    # Combine messages
    final_msg = "\n".join(filter(None, [hunger_msg, promotion_msg]))

    await interaction.response.send_message(
        f"🌙 {char['prefix']} ages one moon.\n"
        f"Age: {char['moons']} moons\n"
        f"Hunger -10 → {char['hunger']}\n"
        f"{final_msg}"
    )
    
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
# ----------------------- PREYPILE COMMAND -----------------------
from discord.ui import View, Button

@bot.tree.command(name="preypile", description="Check or take prey from your clan's fresh kill pile")
async def preypile(interaction: discord.Interaction):
    uid = interaction.user.id

    # Ensure character exists
    char = characters.get(uid)
    if not char:
        await interaction.response.send_message("❌ You don't have a character yet! Use /kit.")
        return

    # Ensure character has a clan
    clan = char.get("clan")
    if not clan:
        await interaction.response.send_message("⚠️ Join a clan first with /clan.")
        return

    # Ensure fresh kill pile exists
    pile = fresh_kill_piles.get(clan)
    if pile is None:
        fresh_kill_piles[clan] = []
        pile = fresh_kill_piles[clan]

    # If empty, add starter prey
    if not pile:
        starter_prey = ["mouse", "rabbit", "vole"]
        pile.extend(starter_prey)
        await interaction.response.send_message(
            f"🐾 The fresh kill pile was empty. Added starter prey: {', '.join(starter_prey)}."
        )
        return

    # Pop first prey
    prey = pile.pop(0)

    # Hunger gain
    hunger_gain = 40
    if char.get("pregnant"):
        stage = char["pregnant"].get("months", 0)
        hunger_gain += stage * 5

    char["hunger"] = min(char.get("hunger", 50) + hunger_gain, 100)

    # Reduce camp quality safely
    camp_quality[clan] = max(0, camp_quality.get(clan, 50) - 2)

    await interaction.response.send_message(
        f"🍖 You take a **{prey}** from the fresh kill pile and eat it.\n"
        f"Your hunger is now **{char['hunger']}/100**\n"
        f"🏕 Camp quality slightly decreased: **{camp_quality[clan]}**"
    )

@bot.tree.command(name="make_warrior", description="Promote an apprentice to warrior")
async def make_warrior(interaction: discord.Interaction, member: discord.Member):
    uid = member.id
    char = characters.get(uid)

    if not char:
        await interaction.response.send_message("❌ That user doesn't have a character.")
        return

    if char["rank"] != "apprentice":
        await interaction.response.send_message("⚠️ Only apprentices can be promoted.")
        return

    suffix = char.get("future_suffix")
    if not suffix:
        await interaction.response.send_message("⚠️ That apprentice has not chosen a warrior suffix yet.")
        return

    clan = char.get("clan", "Unknown")

    # Promote the apprentice
    char["rank"] = "warrior"
    char["suffix"] = suffix
    char.pop("future_suffix", None)

    apprentice_name = f"{char['prefix']}paw"
    warrior_name = f"{char['prefix']}{suffix}"

    ceremony = (
        "🌟 **Warrior Ceremony** 🌟\n\n"
        "Let all cats old enough to catch their own prey join for a clan meeting.\n\n"
        f"I, leader of **{clan}Clan**, call upon my warrior ancestors to look down on this apprentice.\n\n"
        f"**{apprentice_name}**, you have trained hard and proven yourself loyal and brave.\n\n"
        f"From this moment forward, you will be known as **{warrior_name}**.\n\n"
        f"StarClan honors your courage and welcomes you as a full warrior of **{clan}Clan**!\n\n"
        f"🎉 Everyone chant **{warrior_name}! {warrior_name}! {warrior_name}!**"
    )

    await interaction.response.send_message(ceremony)
# ----------------------- TAKE PREY -----------------------
from discord.ui import View, Button

@bot.tree.command(name="take_prey", description="Take prey from your clan's fresh kill pile")
async def take_prey(interaction: discord.Interaction):
    uid = interaction.user.id

    # Ensure the user has a character
    char = characters.get(uid)
    if not char:
        await interaction.response.send_message("❌ You don't have a character yet! Use /kit.")
        return

    # Ensure the character has a clan
    clan = char.get("clan")
    if not clan:
        await interaction.response.send_message("⚠️ Join a clan first with /clan.")
        return

    # Ensure fresh kill pile exists
    pile = fresh_kill_piles.get(clan)
    if pile is None:
        fresh_kill_piles[clan] = []
        pile = fresh_kill_piles[clan]

    # If empty, provide starter prey
    if not pile:
        starter_prey = ["mouse", "rabbit", "vole"]
        pile.extend(starter_prey)
        await interaction.response.send_message(
            f"🐾 The fresh kill pile was empty. Added starter prey: {', '.join(starter_prey)}."
        )
        return

    # Take the first prey
    prey = pile.pop(0)

    # Base hunger gain
    hunger_gain = 40

    # Extra nourishment if pregnant
    if char.get("pregnant"):
        stage = char["pregnant"].get("months", 0)
        hunger_gain += stage * 5  # More for kits

    # Update hunger safely
    char["hunger"] = min(char.get("hunger", 50) + hunger_gain, 100)

    # Reduce camp quality safely
    camp_quality[clan] = max(0, camp_quality.get(clan, 50) - 2)

    # Send feedback message
    await interaction.response.send_message(
        f"🍖 You take a **{prey}** from the fresh kill pile and eat it.\n"
        f"Your hunger is now **{char['hunger']}/100**\n"
        f"🏕 Camp quality slightly decreased: **{camp_quality[clan]}**"
    )
# ----------------------- PROFILE -----------------------
import discord

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
    alive = char.get("alive", True)

    status = "Alive 🐾" if alive else "Dead 💀"

    stats = char.get("stats", {})

    strength = stats.get("strength", 0)
    agility = stats.get("agility", 0)
    intelligence = stats.get("intelligence", 0)
    stealth = stats.get("stealth", 0)
    perception = stats.get("perception", 0)

    mentor = char.get("mentor", "None")
    apprentice = char.get("apprentice", "None")
    mate = char.get("mate", "None")
    kits = char.get("kits", [])

    if isinstance(kits, list):
        kits = ", ".join(kits) if kits else "None"

    embed = discord.Embed(
        title=f"🐾 {name}",
        description=f"{rank.title()} of **{clan}Clan**",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Basic Info",
        value=(
            f"Age: **{moons} moons**\n"
            f"Hunger: **{hunger}/100**\n"
            f"Status: **{status}**"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Stats",
        value=(
            f"Strength: **{strength}**\n"
            f"Agility: **{agility}**\n"
            f"Intelligence: **{intelligence}**\n"
            f"Stealth: **{stealth}**\n"
            f"Perception: **{perception}**"
        ),
        inline=False
    )

    embed.add_field(
        name="Relationships",
        value=(
            f"Mentor: **{mentor}**\n"
            f"Apprentice: **{apprentice}**\n"
            f"Mate: **{mate}**\n"
            f"Kits: **{kits}**"
        ),
        inline=False
    )

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

# ----------------------- HUNT / EAT / DONATE -----------------------
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

    # Pregnancy check: harder to hunt if pregnant
    preg_penalty = pregnancy_hunt_modifier(char)

    # Base hunt success chance
    base_success = 70 - preg_penalty
    hunger = char["hunger"]

    # Modify success based on hunger
    if hunger <= 0:
        base_success -= 40
    elif hunger < 20:
        base_success -= 20
    elif hunger < 40:
        base_success -= 10
    elif hunger >= 90:
        base_success -= 15

    # Random roll
    roll = random.randint(1, 100)
    success = roll <= base_success

    # Determine food gained
    food_gained = random.randint(5, 15)
    if hunger < 20:
        food_gained = max(1, food_gained - 5)
    elif hunger >= 70:
        food_gained += 2

    # Reduce food if pregnant
    if char.get("pregnant"):
        food_gained = max(1, food_gained - char["pregnant"]["months"] * 2)

    # Reduce hunger for effort
    hunger_cost = 5 + preg_penalty
    char["hunger"] = max(char["hunger"] - hunger_cost, 0)

    if success:
        prey = random.choice(list(prey_tables[char["clan"]][season].keys()))
        value = prey_tables[char["clan"]][season][prey]

        pending_hunts[uid] = {"prey": prey, "value": value, "clan": char["clan"]}

        await interaction.response.send_message(
            f"🎯 **Hunt successful!** You caught a **{prey}** worth {value} points.\n"
            f"Hunger: {char['hunger']}/100"
        )
    else:
        await interaction.response.send_message(
            f"❌ Hunt failed. No prey this time.\nHunger: {char['hunger']}/100"
        )
        
@bot.tree.command(name="eat", description="Eat the prey you just hunted")
async def eat(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in pending_hunts:
        await interaction.response.send_message("You have no prey waiting. Go hunt first!")
        return

    char = characters[uid]
    prey_info = pending_hunts.pop(uid)

    # Eating restores hunger
    hunger_gain = 50
    if char.get("pregnant"):
        # Pregnant cats need more food
        hunger_gain += char["pregnant"]["months"] * 5
    char["hunger"] = min(char["hunger"] + hunger_gain, 100)

    await interaction.response.send_message(
        f"🍖 You ate the **{prey_info['prey']}**!\n"
        f"Your hunger is now **{char['hunger']}/100**"
    )
    
@bot.tree.command(name="donate", description="Add prey to clan pile")
async def donate(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in pending_hunts:
        await interaction.response.send_message("You have no prey waiting. Go hunt first!")
        return
    prey_info = pending_hunts.pop(uid)
    fresh_kill_piles[prey_info["clan"]].append(prey_info["prey"])
    clan_prey_piles[prey_info["clan"]] += prey_info["value"]
    await interaction.response.send_message(f"🐾 Added **{prey_info['prey']}** to **{prey_info['clan']}Clan** fresh kill pile!")
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

    await interaction.followup.send(
        f"🎯 **{char['prefix']}**'s turn!",
        view=view
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
            damage = move["damage"]
            # Apply pregnancy penalty
            damage = int(damage * apply_pregnancy_effects(attacker))
            defender["health"] = max(defender["health"] - damage, 0)
            battle["charge"].pop(turn_id)
            result = f"💥 {attacker['prefix']} unleashes **{move['name']}** for {damage} damage!"
        else:
            battle["charge"][turn_id] = move
            result = f"⚡ {attacker['prefix']} begins charging **{move['name']}**!"

    # ---- Status Moves ----
    elif move["type"] == "status":
        buffs = move.get("buff", {})
        if "heal" in buffs:
            attacker["health"] = min(attacker["health"] + buffs["heal"], 100)
        result = f"✨ {attacker['prefix']} uses **{move['name']}**!"

    # ---- Physical Moves ----
    else:
        damage = move["damage"] + hunger_modifier(attacker["hunger"])
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

    # ---- Check Victory ----
    if attacker["health"] <= 0 or defender["health"] <= 0:
        winner = attacker if attacker["health"] > 0 else defender
        loser = defender if winner == attacker else attacker
        battle_state.pop((attacker_id, defender_id), None)
        await interaction.followup.send(
            f"🏆 **{winner['prefix']}** wins! **{loser['prefix']}** is defeated."
        )
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

@bot.tree.command(name="camp_decay", description="Lower camp quality (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def camp_decay(interaction: discord.Interaction):
    for clan in camp_quality:
        camp_quality[clan] = max(0, camp_quality[clan]-5)
    await interaction.response.send_message("🌧️ Weather and time have worn down the camps. Camp quality decreased.")

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

# ----------------------- PING -----------------------
@bot.tree.command(name="ping", description="Check if the bot is active")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("ClanTracker is active! 🐾")

# ----------------------- RUN BOT -----------------------
bot.run(TOKEN)
