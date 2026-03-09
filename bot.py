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
# ----------------------- GLOBALS -----------------------
pending_hunts = {}  # stores prey for eat/donate
pending_battles = {}  # stores pending battle invitations
camp_quality = 50  # 0=terrible, 100=perfect

# ----------------------- HUNGER MODIFIERS -----------------------
def hunger_modifier_hunt(hunger):
    if hunger < 30:
        return -5
    elif hunger < 50:
        return -2
    elif hunger < 80:
        return 2   # just right bonus
    elif hunger <= 99:
        return 0
    else:
        return -3  # overstuffed

def hunger_modifier_battle(hunger):
    if hunger < 30:
        return -5
    elif hunger < 50:
        return -2
    elif hunger < 80:
        return 2  # just right bonus
    elif hunger <= 99:
        return 0
    else:
        return -3  # overstuffed

camp_quality = {
    "Thunder": 75,
    "River": 75,
    "Shadow": 75,
    "Wind": 75
}

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
    "skill_value": 0,
    "hunger": 50 }

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

@bot.tree.command(name="make_warrior", description="Promote an apprentice to warrior")
@app_commands.checks.has_permissions(administrator=True)
async def make_warrior(interaction: discord.Interaction, member: discord.Member):

    uid = member.id

    if uid not in characters:
        await interaction.response.send_message("That player doesn't have a character.")
        return

    char = characters[uid]

    if char["rank"] != "apprentice":
        await interaction.response.send_message("Only apprentices can be promoted to warrior.")
        return

    if not char["suffix"]:
        await interaction.response.send_message(
            "This apprentice hasn't chosen a warrior suffix yet. Use /choose_suffix first."
        )
        return

    prefix = char["prefix"]
    suffix = char["suffix"]
    clan = char["clan"]

    apprentice_name = f"{prefix}paw"
    warrior_name = f"{prefix}{suffix}"

    char["rank"] = "warrior"

    ceremony = (
        f"🌟 **Warrior Ceremony** 🌟\n\n"
        f"I, leader of {clan}Clan, call upon my warrior ancestors to look down on this apprentice.\n\n"
        f"{apprentice_name}, you have trained hard and proven yourself loyal and brave.\n\n"
        f"From this moment forward, you will be known as **{warrior_name}**.\n\n"
        f"StarClan honors your courage and welcomes you as a full warrior of **{clan}Clan**!\n\n"
        f"🎉 Everyone chant **{warrior_name}! {warrior_name}! {warrior_name}!**"
    )

    await interaction.response.send_message(ceremony)

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
@bot.tree.command(name="hunt", description="Go hunting for the clan")
async def hunt(interaction: discord.Interaction):
    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("Create a character first with /kit.")
        return

    char = characters[uid]

    if not char["clan"]:
        await interaction.response.send_message("Join a clan first with /clan.")
        return

    stats = char["stats"]
    hunt_skill = stats["perception"] + stats["dexterity"] + stats["luck"]
    if char["specialty"]:
        hunt_skill += char["skill_value"]

    roll = random.randint(1, 20)
    hunger_mod = hunger_modifier_hunt(char["hunger"])
    total = hunt_skill + roll + hunger_mod
    clan = char["clan"]
    prey_pool = prey_tables[clan][season]
    intro = random.choice(hunt_messages)

    # Message about hunger
    if hunger_mod > 0:
        hunger_msg = "You feel energetic and focused. (+{0} bonus)".format(hunger_mod)
    elif hunger_mod < 0:
        hunger_msg = "You feel weak or sluggish. ({0} penalty)".format(hunger_mod)
    else:
        hunger_msg = ""

    if total >= 20:
        prey = random.choice(list(prey_pool.keys()))
        value = prey_pool[prey]

        # Save prey info for eat/donate
        pending_hunts[uid] = {
            "prey": prey,
            "value": value,
            "clan": clan
        }

        await interaction.response.send_message(
            f"{intro}\n{hunger_msg}\n\n"
            f"🎯 Hunting roll: **{roll}** + skill {hunt_skill} = **{total}**\n\n"
            f"🐾 You caught a **{prey}**!\n"
            f"Do you want to **eat it** or **add it to the fresh kill pile**? Use /eat or /donate."
        )
    else:
        char["hunger"] = max(char["hunger"] - 10, 0)
        await interaction.response.send_message(
            f"{intro}\n{hunger_msg}\n\n"
            f"🎯 Hunting roll: **{roll}** + skill {hunt_skill} = **{total}**\n"
            f"💨 The prey escapes!\n"
            f"🍽️ Your hunger is now **{char['hunger']}**"
        )

@bot.tree.command(name="eat", description="Eat the prey you just hunted")
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

@bot.tree.command(name="donate", description="Add your hunted prey to the clan's fresh kill pile")
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

@bot.tree.command(name="preypile", description="View your clan's prey pile")
async def preypile(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet! Use /kit.")
        return

    char = characters[uid]
    if not char["clan"]:
        await interaction.response.send_message("You haven't joined a clan yet!")
        return

    clan = char["clan"]
    total_prey = clan_prey_piles.get(clan, 0)
    fresh = ", ".join(fresh_kill_piles[clan]) if fresh_kill_piles[clan] else "None"

    warning = ""
    if total_prey < 10:
        warning = "⚠️ Prey looks low. The clan might go hungry soon!"

    await interaction.response.send_message(
        f"🍖 **{clan}Clan's total prey:** {total_prey}\n"
        f"🪶 **Fresh kill pile:** {fresh}\n"
        f"{warning}"
    )

@bot.tree.command(name="take_prey", description="Take prey from your clan's fresh kill pile")
async def take_prey(interaction: discord.Interaction):

    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet! Use /kit.")
        return

    char = characters[uid]

    if not char["clan"]:
        await interaction.response.send_message("Join a clan first with /clan.")
        return

    clan = char["clan"]

    if not fresh_kill_piles[clan]:
        await interaction.response.send_message(
            "The fresh kill pile is empty!"
        )
        return

    prey = fresh_kill_piles[clan].pop(0)

    # restore hunger
    char["hunger"] = min(char["hunger"] + 40, 100)

    await interaction.response.send_message(
        f"🍖 You take a **{prey}** from the fresh kill pile and eat it.\n"
        f"Your hunger is now **{char['hunger']}**."
    )
# ----------------------- BATTLE COMMAND -----------------------

from discord.ui import View, Button

# ----------------------- BATTLE COMMAND WITH BUTTONS -----------------------
@bot.tree.command(name="battle", description="Challenge another cat")
async def battle(interaction: discord.Interaction, opponent: discord.Member):
    uid = interaction.user.id
    oid = opponent.id

    if uid not in characters or oid not in characters:
        await interaction.response.send_message("Both players must have a character to battle!")
        return

    if oid in pending_battles:
        await interaction.response.send_message("That cat already has a pending battle!")
        return

    attacker = characters[uid]

    # Hunger warning for attacker
    if attacker["hunger"] < 20:
        view = View()

        async def confirm_callback(interact: discord.Interaction):
            await start_battle(interaction, opponent)
            for item in view.children:
                item.disabled = True
            await interact.message.edit(view=view)

        async def cancel_callback(interact: discord.Interaction):
            await interact.response.send_message("⚠️ Battle cancelled due to hunger.", ephemeral=True)
            for item in view.children:
                item.disabled = True
            await interact.message.edit(view=view)

        yes_btn = Button(label="Yes", style=discord.ButtonStyle.green)
        yes_btn.callback = confirm_callback
        no_btn = Button(label="No", style=discord.ButtonStyle.red)
        no_btn.callback = cancel_callback

        view.add_item(yes_btn)
        view.add_item(no_btn)

        await interaction.response.send_message(
            "⚠️ You are too hungry to fight! Your hunger is low. Proceed with battle?",
            view=view
        )
        return

    # No hunger warning, start battle directly
    await start_battle(interaction, opponent)

# ----------------------- START BATTLE FUNCTION -----------------------
async def start_battle(interaction: discord.Interaction, opponent: discord.Member):
    uid = interaction.user.id
    oid = opponent.id

    # Save battle invitation
    pending_battles[oid] = {"attacker": uid, "opponent": oid}

    await interaction.followup.send(
        f"⚔️ **{characters[uid]['prefix']}** has challenged **{opponent.display_name}**!\n"
        f"{opponent.mention}, do you accept? Use `/fight` to fight or `/flee` to flee."
    )

# ----------------------- FIGHT COMMAND -----------------------
@bot.tree.command(name="fight", description="Accept a pending battle")
async def fight(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in pending_battles:
        await interaction.response.send_message("You have no battle invitations!")
        return

    info = pending_battles.pop(uid)
    attacker = characters[info["attacker"]]
    defender = characters[info["opponent"]]

    # Rolls
    atk_stats = attacker["stats"]
    def_stats = defender["stats"]

    atk_roll = random.randint(1, 20)
    def_roll = random.randint(1, 20)

    atk_total = atk_stats["strength"] + atk_stats["speed"] + atk_stats["dexterity"] + atk_stats["luck"] + atk_roll
    def_total = def_stats["strength"] + def_stats["speed"] + def_stats["dexterity"] + def_stats["intelligence"] + def_roll

    # Hunger modifiers
    atk_total += hunger_modifier_battle(attacker["hunger"])
    def_total += hunger_modifier_battle(defender["hunger"])

    # Camp bonus
    clan = defender["clan"]
    if camp_quality.get(clan, 50) >= 80:
        def_total += 2

    # Resolve full names
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

    # Determine result and apply damage
    if atk_total > def_total:
        result = f"⚔️ **{attacker_name}** wins the battle!"
        defender["health"] = max(defender["health"] - 20, 0)
    elif def_total > atk_total:
        result = f"⚔️ **{defender_name}** wins the battle!"
        attacker["health"] = max(attacker["health"] - 20, 0)
    else:
        result = "⚔️ The battle ends in a draw!"

    await interaction.response.send_message(
        f"🐾 Battle Begins!\n\n"
        f"{attacker_name} roll: **{atk_roll}** + stats = **{atk_total}**\n"
        f"{defender_name} roll: **{def_roll}** + stats = **{def_total}**\n\n"
        f"{result}\n\n"
        f"💖 {attacker_name} HP: {attacker['health']}, {defender_name} HP: {defender['health']}"
    )

# ----------------------- FLEE COMMAND -----------------------
@bot.tree.command(name="flee", description="Flee a pending battle")
async def flee(interaction: discord.Interaction):
    uid = interaction.user.id
    found = None
    for key, val in pending_battles.items():
        if val["opponent"] == uid:
            found = key
            break

    if not found:
        await interaction.response.send_message("You have no battle invitations!")
        return

    info = pending_battles.pop(found)
    flee_damage = 5
    defender_char = characters[uid]
    defender_char["health"] = max(defender_char["health"] - flee_damage, 0)

    await interaction.response.send_message(
        f"💨 **{defender_char['prefix']}** flees from battle!\n"
        f"They take **{flee_damage} damage** but avoid full combat.\n"
        f"💖 HP now: {defender_char['health']}"
            )
    
@bot.tree.command(name="maintain_camp", description="Help maintain the camp")
@bot.tree.command(name="maintain_camp", description="Help maintain the camp")
async def maintain_camp(interaction: discord.Interaction):

    uid = interaction.user.id

    # Make sure the user has a character
    if uid not in characters:
        await interaction.response.send_message("Create a character first with /kit.")
        return

    char = characters[uid]

    # Make sure the character has joined a clan
    if not char["clan"]:
        await interaction.response.send_message("Join a clan first with /clan.")
        return

    clan = char["clan"]

    # Random improvement amount
    improvement = random.randint(5, 15)
    camp_quality[clan] = min(100, camp_quality[clan] + improvement)

    # Display condition message based on new quality
    quality = camp_quality[clan]
    if quality >= 90:
        condition = "⭐ The camp is in excellent condition! The clan feels energized."
    elif quality >= 70:
        condition = "🌿 The camp is clean and well maintained."
    elif quality >= 40:
        condition = "🪶 The camp is in decent shape."
    elif quality >= 15:
        condition = "⚠️ The camp is getting messy."
    else:
        condition = "🚨 The camp is falling apart!"

    await interaction.response.send_message(
        f"🧹 You help repair dens and clear debris.\n"
        f"Camp quality improved by **{improvement}** points!\n"
        f"New quality: **{quality}**\n"
        f"{condition}"
    )
    
@bot.tree.command(name="camp_decay", description="Lower camp quality (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def camp_decay(interaction: discord.Interaction):

    for clan in camp_quality:
        camp_quality[clan] = max(0, camp_quality[clan] - 5)

    await interaction.response.send_message(
        "🌧️ Weather and time have worn down the camps. Camp quality decreased."
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
