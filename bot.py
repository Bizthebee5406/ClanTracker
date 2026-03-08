import discord
from discord.ext import commands
from discord import app_commands
import os
import random

TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

characters = {}

clan_prey_piles = {
    "Thunder": 0,
    "River": 0,
    "Shadow": 0,
    "Wind": 0
}

seasons = ["newleaf", "greenleaf", "leaf-fall", "leafbare"]

prey_tables = {

    "Thunder": {
        "greenleaf": {
            "mouse": 2,
            "vole": 2,
            "squirrel": 3,
            "rabbit": 5
        },
        "leafbare": {
            "mouse": 2,
            "vole": 2
        }
    },

    "River": {
        "greenleaf": {
            "fish": 4,
            "frog": 2,
            "water vole": 3
        },
        "leafbare": {
            "fish": 3
        }
    },

    "Shadow": {
        "greenleaf": {
            "rat": 3,
            "lizard": 2,
            "frog": 2
        },
        "leafbare": {
            "rat": 3
        }
    },

    "Wind": {
        "greenleaf": {
            "rabbit": 5,
            "hare": 4,
            "mouse": 2
        },
        "leafbare": {
            "rabbit": 4
        }
    }
}

hunt_messages = [
    "You crouch low in the undergrowth...",
    "You scent the air carefully...",
    "You stalk through the territory silently...",
    "Your tail flicks as you track movement...",
    "You creep forward pawstep by pawstep..."
]

def generate_stats():
    return {
        "strength": random.randint(0,10),
        "perception": random.randint(0,10),
        "dexterity": random.randint(0,10),
        "speed": random.randint(0,10),
        "intelligence": random.randint(0,10),
        "luck": random.randint(0,10),
        "charisma": random.randint(0,10)}

clan_specialties = {
    "Thunder": "tracking",
    "River": "swimming",
    "Shadow": "stealth",
    "Wind": "endurance"}

@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

    print(f"{bot.user} is online and ready!")

@tree.command(name="kit", description="Create your kit")
async def kit(interaction: discord.Interaction, prefix: str):

    if interaction.user.id in characters:
        await interaction.response.send_message("You already have a character.")
        return

    stats = {
        "strength": random.randint(0,10),
        "perception": random.randint(0,10),
        "dexterity": random.randint(0,10),
        "speed": random.randint(0,10),
        "intelligence": random.randint(0,10),
        "luck": random.randint(0,10),
        "charisma": random.randint(0,10)
    }

    characters[interaction.user.id] = {
        "prefix": prefix,
        "rank": "kit",
        "moons": 0,
        "suffix": None,
        "clan": None,
        "health": 100,
        "stats": stats,
        "specialty": None,
        "skill_value": 0
    }

    await interaction.response.send_message(
        f"🐾 **{prefix}kit** has been born into the Clan!\n\n"
        f"**Base Stats**\n"
        f"Strength: {stats['strength']}\n"
        f"Perception: {stats['perception']}\n"
        f"Dexterity: {stats['dexterity']}\n"
        f"Speed: {stats['speed']}\n"
        f"Intelligence: {stats['intelligence']}\n"
        f"Luck: {stats['luck']}\n"
        f"Charisma: {stats['charisma']}")
    
@tree.command(name="age", description="Age your character")
async def age(interaction: discord.Interaction, moons: int):

    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet. Use /kit.")
        return

    characters[uid]["moons"] += moons
    moons_now = characters[uid]["moons"]

    if characters[uid]["rank"] == "kit" and moons_now >= 6:
        characters[uid]["rank"] = "apprentice"
        name = f"{characters[uid]['prefix']}paw"

        await interaction.response.send_message(
            f"🌙 You are now {moons_now} moons old!\n"
            f"You have become **{name}**, an apprentice! 🐾"
        )
        return

    await interaction.response.send_message(f"🌙 You are now **{moons_now} moons** old!")

@tree.command(name="clan", description="Join a clan")
async def clan(interaction: discord.Interaction, clan_name: str):

    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character.")
        return

    clan_name = clan_name.capitalize()

    if clan_name not in ["Thunder", "River", "Shadow", "Wind"]:
        await interaction.response.send_message(
            "Valid clans are: Thunder, River, Shadow, Wind."
        )
        return

    char = characters[uid]
    char["clan"] = clan_name

    # Clan skills
    clan_skills = {
        "Thunder": "tracking",
        "River": "swimming",
        "Shadow": "stealth",
        "Wind": "endurance"
    }

    specialty = clan_skills[clan_name]

    char["specialty"] = specialty
    char["skill_value"] = random.randint(4,10)

    member = interaction.guild.get_member(uid)

    # Role names
    role_name = f"{clan_name}Clan"

    # Remove other clan roles
    clan_roles = ["ThunderClan", "RiverClan", "ShadowClan", "WindClan"]

    for role in interaction.guild.roles:
        if role.name in clan_roles and role in member.roles:
            await member.remove_roles(role)

    # Add new clan role
    role = discord.utils.get(interaction.guild.roles, name=role_name)

    if role:
        await member.add_roles(role)

    await interaction.response.send_message(
        f"{char['prefix']} has joined **{clan_name}Clan**!\n"
        f"Clan skill gained: **{specialty} ({char['skill_value']})** 🐾"
    )
    
@tree.command(name="choose_suffix", description="Choose your warrior suffix")
async def choose_suffix(interaction: discord.Interaction, suffix: str):

    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character.")
        return

    char = characters[uid]

    if char["rank"] != "apprentice":
        await interaction.response.send_message("Only apprentices can choose a warrior suffix.")
        return

    char["suffix"] = suffix

    await interaction.response.send_message(
        f"Your future warrior name will be **{char['prefix']}{suffix}**.")

@tree.command(name="stats", description="View your character stats")
async def stats(interaction: discord.Interaction):

    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet.")
        return

    char = characters[uid]
    stats = char["stats"]

    clan = char["clan"] if char["clan"] else "None"

    if char["rank"] == "kit":
        display = f"{char['prefix']}kit"
    elif char["rank"] == "apprentice":
        display = f"{char['prefix']}paw"
    elif char["rank"] == "warrior":
        display = f"{char['prefix']}{char['suffix']}"
    else:
        display = char["prefix"]

    await interaction.response.send_message(
        f"📜 **{display}**\n"
        f"Rank: {char['rank']}\n"
        f"Age: {char['moons']} moons\n"
        f"Clan: {clan}\n\n"

        f"**Attributes**\n"
        f"Strength: {stats['strength']}\n"
        f"Perception: {stats['perception']}\n"
        f"Dexterity: {stats['dexterity']}\n"
        f"Speed: {stats['speed']}\n"
        f"Intelligence: {stats['intelligence']}\n"
        f"Luck: {stats['luck']}\n"
        f"Charisma: {stats['charisma']}\n\n"

        f"Clan Skill: {char['specialty']} ({char['skill_value']})"
    )

@tree.command(name="set_season", description="Change the current season")
@app_commands.checks.has_permissions(administrator=True)
async def set_season(interaction: discord.Interaction, new_season: str):

    global season

    new_season = new_season.lower()

    if new_season not in seasons:
        await interaction.response.send_message(
            "Valid seasons: newleaf, greenleaf, leaf-fall, leafbare"
        )
        return

    season = new_season

    await interaction.response.send_message(
        f"🌿 The season has changed! It is now **{season}**."
    )

@tree.command(name="season", description="Check the current season")
async def check_season(interaction: discord.Interaction):

    await interaction.response.send_message(
        f"🍃 The current season is **{season}**."
    )
    
@tree.command(name="hunt", description="Go hunting for the clan")
async def hunt(interaction: discord.Interaction):

    uid = interaction.user.id

    # Check if player has a character
    if uid not in characters:
        await interaction.response.send_message("Create a character first with /kit.")
        return

    char = characters[uid]

    # Kits cannot hunt
    if char["rank"] == "kit":
        await interaction.response.send_message("Kits are too young to hunt!")
        return

    # Must belong to a clan
    if not char["clan"]:
        await interaction.response.send_message("Join a clan first with /clan.")
        return

    stats = char["stats"]

    # Base hunting skill
    hunt_skill = (
        stats["perception"] +
        stats["dexterity"] +
        stats["luck"]
    )

    # Add clan specialty bonus
    hunt_skill += char["skill_value"]

    # Dice roll
    roll = random.randint(1, 20)
    total = hunt_skill + roll

    clan = char["clan"]

    # Get prey pool for clan + season
    prey_pool = prey_tables[clan][season]

    # Random hunt intro message
    intro = random.choice(hunt_messages)

    if total >= 20:

        prey = random.choice(list(prey_pool.keys()))
        value = prey_pool[prey]

        # Add prey to correct clan pile
        clan_prey_piles[clan] += value

        await interaction.response.send_message(
            f"{intro}\n\n"
            f"🎯 Hunting roll: **{roll}**\n"
            f"Skill bonus: **{hunt_skill}**\n\n"
            f"🐾 You caught a **{prey}**!\n"
            f"🍖 It adds **{value} prey** to the clan pile.\n\n"
            f"Clan prey pile: **{clan_prey_piles[clan]}**"
        )

    else:

        await interaction.response.send_message(
            f"{intro}\n\n"
            f"🎯 Hunting roll: **{roll}**\n"
            f"Skill bonus: **{hunt_skill}**\n\n"
            "💨 The prey escapes!"
        )
        
@tree.command(name="battle", description="Challenge another cat")
async def battle(interaction: discord.Interaction, opponent: discord.Member):

    uid = interaction.user.id
    oid = opponent.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character.")
        return

    if oid not in characters:
        await interaction.response.send_message("That player has no character.")
        return

    attacker = characters[uid]
    defender = characters[oid]

    atk_stats = attacker["stats"]
    def_stats = defender["stats"]

    # Calculate combat power
    attack_power = (
        atk_stats["strength"] +
        atk_stats["speed"] +
        atk_stats["dexterity"] +
        atk_stats["luck"]
    )

    defense_power = (
        def_stats["strength"] +
        def_stats["speed"] +
        def_stats["dexterity"] +
        def_stats["intelligence"]
    )

    atk_roll = random.randint(1,20)
    def_roll = random.randint(1,20)

    atk_total = attack_power + atk_roll
    def_total = defense_power + def_roll

    def full_name(char):
        if char["rank"] == "kit":
            return f"{char['prefix']}kit"
        elif char["rank"] == "apprentice":
            return f"{char['prefix']}paw"
        elif char["rank"] == "warrior":
            return f"{char['prefix']}{char['suffix']}"
        else:
            return char["prefix"]

    attacker_name = full_name(attacker)
    defender_name = full_name(defender)

    if atk_total > def_total:

        result = f"⚔️ **{attacker_name}** wins the battle!"

    elif def_total > atk_total:

        result = f"⚔️ **{defender_name}** wins the battle!"

    else:

        result = "⚔️ The battle ends in a draw!"

    await interaction.response.send_message(
        f"🐾 Battle Begins!\n\n"
        f"{attacker_name} roll: **{atk_roll}** + {attack_power}\n"
        f"{defender_name} roll: **{def_roll}** + {defense_power}\n\n"
        f"{result}")
    
@tree.command(name="make_apprentice")
@app_commands.checks.has_permissions(administrator=True)
async def make_apprentice(interaction: discord.Interaction, member: discord.Member):

    uid = member.id

    if uid not in characters:
        await interaction.response.send_message("That player has no character.")
        return

    char = characters[uid]
    char["rank"] = "apprentice"

    name = f"{char['prefix']}paw"

    await interaction.response.send_message(
        f"{member.mention} has been named **{name}**, apprentice of the Clan! 🐾")


@tree.command(name="make_warrior")
@app_commands.checks.has_permissions(administrator=True)
async def make_warrior(interaction: discord.Interaction, member: discord.Member):

    uid = member.id

    if uid not in characters:
        await interaction.response.send_message("That player has no character.")
        return

    char = characters[uid]

    if not char["suffix"]:
        await interaction.response.send_message("They haven't chosen a suffix yet.")
        return

    char["rank"] = "warrior"

    name = f"{char['prefix']}{char['suffix']}"

    await interaction.response.send_message(
        f"{member.mention} is now **{name}**, a warrior of the Clan! 🐾")
    
@tree.command(name="preypile", description="View your clan's prey pile")
async def preypile(interaction: discord.Interaction):

    uid = interaction.user.id

    # Check if player has a character
    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet! Use /kit to create one.")
        return

    char = characters[uid]

    # Must belong to a clan
    if not char["clan"]:
        await interaction.response.send_message("You haven't joined a clan yet! Use /clan to join one.")
        return

    clan = char["clan"]
    prey_count = clan_prey_piles.get(clan, 0)

    await interaction.response.send_message(
        f"🍖 **{clan}Clan's prey pile:** {prey_count} prey")
    from datetime import datetime

@tree.command(name="time", description="Check the current season and moon")
async def time(interaction: discord.Interaction):
    global season
    # You can add moons later when you track them
    await interaction.response.send_message(
        f"🌿 The current season is **{season.capitalize()}**.\n"
        f"🌓 Moons tracking will be added soon!"
    )
    
@tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("ClanTracker is active! 🐾")

@bot.tree.command(name="help", description="Shows all commands")
async def help_command(interaction: discord.Interaction):

    help_text = """
🐾 **Warriors RPG Bot Commands**

🌿 **Character**
/create – Create your warrior
/profile – View your character
/age – Gain a moon
/rank – Check your rank

🍖 **Clan Life**
/hunt – Hunt for prey
/preypile – View clan prey pile
/donate – Add prey to the pile

⚔️ **Combat**
/battle – Fight another warrior
/train – Practice to improve skills

🌎 **World**
/season – Check the current season
/time – Check the current moon

📖 **Other**
/help – Shows this command list
"""

    await interaction.response.send_message(help_text)

bot.run(TOKEN)
