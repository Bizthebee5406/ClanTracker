import discord
from discord.ext import commands
from discord import app_commands
import os
import random

TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

characters = {}

clan_prey_piles = {
    "Thunder": 0,
    "River": 0,
    "Shadow": 0,
    "Wind": 0
}

fresh_kill_piles = {
    "Thunder": [],
    "River": [],
    "Shadow": [],
    "Wind": []
}

seasons = ["newleaf", "greenleaf", "leaf-fall", "leafbare"]
season = "greenleaf"  # default

prey_tables = {
    "Thunder": {
        "greenleaf": {"mouse": 2, "vole": 2, "squirrel": 3, "rabbit": 5},
        "leafbare": {"mouse": 2, "vole": 2}
    },
    "River": {
        "greenleaf": {"fish": 4, "frog": 2, "water vole": 3},
        "leafbare": {"fish": 3}
    },
    "Shadow": {
        "greenleaf": {"rat": 3, "lizard": 2, "frog": 2},
        "leafbare": {"rat": 3}
    },
    "Wind": {
        "greenleaf": {"rabbit": 5, "hare": 4, "mouse": 2},
        "leafbare": {"rabbit": 4}
    }
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

def generate_stats():
    return {stat: random.randint(0, 10) for stat in 
            ["strength","perception","dexterity","speed","intelligence","luck","charisma"]}

# ----------------------- READY -----------------------
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands globally")
    print(f"{bot.user} is online!")

# ----------------------- KIT COMMAND -----------------------
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
        "skill_value": 0
    }

    await interaction.response.send_message(
        f"🐾 **{prefix}kit** has been born into the Clan!\n\n"
        f"**Base Stats**\n" +
        "\n".join(f"{k.capitalize()}: {v}" for k,v in stats.items())
    )

# ----------------------- AGE COMMAND -----------------------
@bot.tree.command(name="age", description="Age your character")
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

# ----------------------- CLAN COMMAND -----------------------
@bot.tree.command(name="clan", description="Join a clan")
async def clan(interaction: discord.Interaction, clan_name: str):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character.")
        return

    clan_name = clan_name.capitalize()
    if clan_name not in clan_specialties:
        await interaction.response.send_message(
            "Valid clans are: Thunder, River, Shadow, Wind."
        )
        return

    char = characters[uid]
    char["clan"] = clan_name
    char["specialty"] = clan_specialties[clan_name]
    char["skill_value"] = random.randint(4, 10)

    member = interaction.guild.get_member(uid)
    role_name = f"{clan_name}Clan"
    clan_roles = ["ThunderClan", "RiverClan", "ShadowClan", "WindClan"]

    # Remove old roles
    for role in interaction.guild.roles:
        if role.name in clan_roles and role in member.roles:
            await member.remove_roles(role)

    # Add new role
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if role:
        await member.add_roles(role)

    await interaction.response.send_message(
        f"{char['prefix']} has joined **{clan_name}Clan**!\n"
        f"Clan skill gained: **{char['specialty']} ({char['skill_value']})** 🐾"
    )

# ----------------------- PROFILE COMMAND -----------------------
@bot.tree.command(name="profile", description="View your full character profile")
async def profile(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet! Use /kit.")
        return

    char = characters[uid]
    stats = char["stats"]
    if char["rank"] == "kit":
        display_name = f"{char['prefix']}kit"
    elif char["rank"] == "apprentice":
        display_name = f"{char['prefix']}paw"
    elif char["rank"] == "warrior":
        display_name = f"{char['prefix']}{char['suffix']}"
    else:
        display_name = char["prefix"]

    clan = char["clan"] or "None"
    specialty = f"{char['specialty']} ({char['skill_value']})" if char["specialty"] else "None"
    prey_contribution = clan_prey_piles.get(char["clan"], 0) if char["clan"] else 0

    await interaction.response.send_message(
        f"📖 **{display_name}**'s Profile\n\n"
        f"**Rank:** {char['rank']}\n"
        f"**Age:** {char['moons']} moons\n"
        f"**Clan:** {clan}\n"
        f"**Clan Skill:** {specialty}\n"
        f"**Prey Contributed:** {prey_contribution}\n\n" +
        "\n".join(f"**{k.capitalize()}:** {v}" for k,v in stats.items())
    )

# ----------------------- HUNT COMMAND -----------------------
@tree.command(name="hunt", description="Go hunting for the clan")
async def hunt(interaction: discord.Interaction):
    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("Create a character first with /kit.")
        return

    char = characters[uid]

    if char["rank"] == "kit":
        await interaction.response.send_message("Kits are too young to hunt!")
        return

    if not char["clan"]:
        await interaction.response.send_message("Join a clan first with /clan.")
        return

    stats = char["stats"]
    hunt_skill = stats["perception"] + stats["dexterity"] + stats["luck"]
    if char["specialty"]:
        hunt_skill += char["skill_value"]

    roll = random.randint(1, 20)
    total = hunt_skill + roll
    clan = char["clan"]
    prey_pool = prey_tables[clan][season]
    intro = random.choice(hunt_messages)

    if total >= 20:
        prey = random.choice(list(prey_pool.keys()))
        value = prey_pool[prey]

        # Prompt the player: eat or add to fresh kill pile
        await interaction.response.send_message(
            f"{intro}\n\n"
            f"🎯 Hunting roll: **{roll}**\n"
            f"Skill bonus: **{hunt_skill}**\n\n"
            f"🐾 You caught a **{prey}**!\n"
            f"Do you want to **eat it** or **add it to the fresh kill pile**?"
        )

        pending_hunts = {}  # temporary storage for decisions

@tree.command(name="eat", description="Eat the prey you just hunted")
async def eat(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in pending_hunts:
        await interaction.response.send_message("You have no prey waiting. Go hunt first!")
        return

    char = characters[uid]
    prey_info = pending_hunts.pop(uid)

    # Eating reduces hunger
    char["hunger"] = min(char["hunger"] + 50, 100)

    await interaction.response.send_message(
        f"🍖 You ate the **{prey_info['prey']}**!\n"
        f"Your hunger is now **{char['hunger']}**"
    )

@tree.command(name="donate", description="Add your hunted prey to the clan's fresh kill pile")
async def donate(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in pending_hunts:
        await interaction.response.send_message("You have no prey waiting. Go hunt first!")
        return

    prey_info = pending_hunts.pop(uid)
    fresh_kill_piles[prey_info["clan"]].append(prey_info["prey"])
    clan_prey_piles[prey_info["clan"]] += prey_info["value"]

    await interaction.response.send_message(
        f"🐾 You added **{prey_info['prey']}** to the fresh kill pile of **{prey_info['clan']}Clan**!"
    )

@tree.command(name="preypile", description="View your clan's prey pile")
async def preypile(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet! Use /kit.")
        return

    char = characters[uid]

    if not char["clan"]:
        await interaction.response.send_message("You haven't joined a clan yet! Use /clan to join one.")
        return

    clan = char["clan"]
    total_prey = clan_prey_piles.get(clan, 0)
    fresh = ", ".join(fresh_kill_piles[clan]) if fresh_kill_piles[clan] else "None"

    await interaction.response.send_message(
        f"🍖 **{clan}Clan's total prey:** {total_prey}\n"
        f"🪶 **Fresh kill pile:** {fresh}"
    )

        # Save the context somewhere, e.g. in a temp dict
        pending_hunts[uid] = {
            "prey": prey,
            "value": value,
            "clan": clan
        }

    else:
        # Reduce hunger for effort
        char["hunger"] = max(char["hunger"] - 10, 0)

        await interaction.response.send_message(
            f"{intro}\n\n"
            f"🎯 Hunting roll: **{roll}**\n"
            f"Skill bonus: **{hunt_skill}**\n\n"
            f"💨 The prey escapes!\n"
            f"🍽️ Your hunger is now **{char['hunger']}**"
        )

# ----------------------- BATTLE COMMAND -----------------------
@bot.tree.command(name="battle", description="Challenge another cat")
async def battle(interaction: discord.Interaction, opponent: discord.Member):
    uid = interaction.user.id
    oid = opponent.id

    if uid not in characters or oid not in characters:
        await interaction.response.send_message("Both players must have a character to battle!")
        return

    attacker = characters[uid]
    defender = characters[oid]

    atk_power = attacker["stats"]["strength"] + attacker["stats"]["speed"] + attacker["stats"]["dexterity"] + attacker["stats"]["luck"]
    def_power = defender["stats"]["strength"] + defender["stats"]["speed"] + defender["stats"]["dexterity"] + defender["stats"]["intelligence"]

    atk_roll = random.randint(1, 20)
    def_roll = random.randint(1, 20)

    atk_total = atk_power + atk_roll
    def_total = def_power + def_roll

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
        f"{attacker_name} roll: **{atk_roll}** + {atk_power}\n"
        f"{defender_name} roll: **{def_roll}** + {def_power}\n\n"
        f"{result}"
    )

# ----------------------- TRAIN COMMAND -----------------------
@bot.tree.command(name="train", description="Train a stat to improve your abilities")
async def train(interaction: discord.Interaction, stat: str):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet! Use /kit.")
        return

    char = characters[uid]
    if char["rank"] == "kit":
        await interaction.response.send_message("Kits are too young to train!")
        return

    stat = stat.lower()
    if stat not in char["stats"]:
        await interaction.response.send_message(
            "Invalid stat! Choose from strength, perception, dexterity, speed, intelligence, luck, charisma."
        )
        return

    gain = random.randint(1, 3)
    if char["specialty"] and stat == char["specialty"]:
        gain += 1

    char["stats"][stat] += gain
    await interaction.response.send_message(
        f"💪 {char['prefix']} trained **{stat.capitalize()}** and gained **{gain}** points!\n"
        f"New {stat.capitalize()}: **{char['stats'][stat]}**"
    )

# ----------------------- CHOOSE_SUFFIX COMMAND -----------------------
@bot.tree.command(name="choose_suffix", description="Choose your warrior suffix")
async def choose_suffix(interaction: discord.Interaction, suffix: str):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet! Use /kit.")
        return

    char = characters[uid]
    if char["rank"] != "apprentice":
        await interaction.response.send_message("Only apprentices can choose a warrior suffix.")
        return

    char["suffix"] = suffix
    await interaction.response.send_message(
        f"Your future warrior name will be **{char['prefix']}{suffix}**."
    )
    
@bot.tree.command(name="assign_mentor", description="Assign a mentor to an apprentice")
async def assign_mentor(interaction: discord.Interaction, mentee: discord.Member, mentor: discord.Member):
    mentee_id = mentee.id
    mentor_id = mentor.id

    # Check if characters exist
    if mentee_id not in characters:
        await interaction.response.send_message("The mentee has no character.")
        return
    if mentor_id not in characters:
        await interaction.response.send_message("The mentor has no character.")
        return

    mentee_char = characters[mentee_id]
    mentor_char = characters[mentor_id]

    # Rank restrictions
    if mentee_char["rank"] != "apprentice":
        await interaction.response.send_message("Only apprentices can be assigned a mentor.")
        return
    if mentor_char["rank"] != "warrior":
        await interaction.response.send_message("Only warriors can be mentors.")
        return

    # Permission check: must be admin or the mentor themselves
    if interaction.user.id != mentor_id and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only an administrator or the chosen mentor can assign this mentorship.")
        return

    # Cannot mentor self
    if mentee_id == mentor_id:
        await interaction.response.send_message("You cannot mentor yourself!")
        return

    # Assign mentor
    mentee_char["mentor"] = mentor_id
    await interaction.response.send_message(
        f"🌟 **{mentor.display_name}** is now mentoring **{mentee.display_name}**!"
    )

# ----------------------- SEASON COMMAND -----------------------
@bot.tree.command(name="season", description="Check the current season")
async def check_season(interaction: discord.Interaction):
    await interaction.response.send_message(f"🍃 The current season is **{season}**.")

@bot.tree.command(name="set_season", description="Change the current season (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def set_season(interaction: discord.Interaction, new_season: str):
    global season  # update the global season variable

    new_season = new_season.lower()
    if new_season not in ["newleaf", "greenleaf", "leaf-fall", "leafbare"]:
        await interaction.response.send_message(
            "❌ Invalid season! Valid seasons are: newleaf, greenleaf, leaf-fall, leafbare."
        )
        return

    season = new_season
    await interaction.response.send_message(f"🌿 The season has been changed! It is now **{season.capitalize()}**.")

# ----------------------- PING COMMAND -----------------------
@bot.tree.command(name="ping", description="Check if the bot is active")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("ClanTracker is active! 🐾")
# ----------------------- RUN BOT -----------------------
bot.run(TOKEN)
