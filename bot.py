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


# ------------------------
# BOT READY
# ------------------------

@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user} is online and ready!")


# ------------------------
# CREATE KIT
# ------------------------

@tree.command(name="kit", description="Create your kit")
async def kit(interaction: discord.Interaction, prefix: str):

    characters[interaction.user.id] = {
        "prefix": prefix,
        "rank": "kit",
        "moons": 0,
        "suffix": None,
        "clan": None,
        "prey": 0,
        "health": 100
    }

    await interaction.response.send_message(
        f"🐾 **{prefix}kit** has been born into the Clan!"
    )


# ------------------------
# AGE
# ------------------------

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


# ------------------------
# STATS
# ------------------------

@tree.command(name="stats", description="View your character")
async def stats(interaction: discord.Interaction):

    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet.")
        return

    char = characters[uid]

    if char["rank"] == "kit":
        display = f"{char['prefix']}kit"
    elif char["rank"] == "apprentice":
        display = f"{char['prefix']}paw"
    elif char["rank"] == "warrior":
        display = f"{char['prefix']}{char['suffix']}"
    else:
        display = char["prefix"]

    clan = char["clan"] if char["clan"] else "None"

    await interaction.response.send_message(
        f"📜 **{display}**\n"
        f"Rank: {char['rank']}\n"
        f"Age: {char['moons']} moons\n"
        f"Clan: {clan}\n"
        f"Prey caught: {char['prey']}\n"
        f"Health: {char['health']}"
    )


# ------------------------
# JOIN CLAN
# ------------------------

@tree.command(name="clan", description="Join a clan")
async def clan(interaction: discord.Interaction, clan_name: str):

    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character.")
        return

    characters[uid]["clan"] = clan_name

    await interaction.response.send_message(
        f"{characters[uid]['prefix']} has joined **{clan_name} Clan**! 🐾"
    )


# ------------------------
# CHOOSE WARRIOR NAME
# ------------------------

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
        f"Your future warrior name will be **{char['prefix']}{suffix}**."
    )


# ------------------------
# HUNT
# ------------------------

prey_list = ["mouse", "vole", "rabbit", "lizard", "frog", "squirrel"]

@tree.command(name="hunt", description="Go hunting")
async def hunt(interaction: discord.Interaction):

    uid = interaction.user.id

    if uid not in characters:
        await interaction.response.send_message("Create a character first with /kit.")
        return

    success = random.randint(1, 100)

    if success <= 70:
        prey = random.choice(prey_list)
        characters[uid]["prey"] += 1

        await interaction.response.send_message(
            f"🌿 You stalk through the forest...\n"
            f"🐾 You caught a **{prey}**!"
        )
    else:
        await interaction.response.send_message(
            "🌿 You hunt for a while but catch nothing..."
        )


# ------------------------
# BATTLE
# ------------------------

@tree.command(name="battle", description="Battle another cat")
async def battle(interaction: discord.Interaction, opponent: discord.Member):

    uid = interaction.user.id
    oid = opponent.id

    if uid not in characters:
        await interaction.response.send_message("You don't have a character.")
        return

    if oid not in characters:
        await interaction.response.send_message("That player has no character.")
        return

    player_roll = random.randint(1, 20)
    opponent_roll = random.randint(1, 20)

    player_name = characters[uid]["prefix"]
    opponent_name = characters[oid]["prefix"]

    if player_roll > opponent_roll:
        result = f"⚔️ {player_name} defeats {opponent_name} in battle!"
    elif opponent_roll > player_roll:
        result = f"⚔️ {opponent_name} defeats {player_name} in battle!"
    else:
        result = "⚔️ The battle ends in a draw!"

    await interaction.response.send_message(
        f"🐾 Battle Begins!\n"
        f"{player_name} rolled **{player_roll}**\n"
        f"{opponent_name} rolled **{opponent_roll}**\n\n"
        f"{result}"
    )


# ------------------------
# ADMIN PROMOTIONS
# ------------------------

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
        f"{member.mention} has been named **{name}**, apprentice of the Clan! 🐾"
    )


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
        f"{member.mention} is now **{name}**, a warrior of the Clan! 🐾"
    )


# ------------------------
# PING
# ------------------------

@tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("ClanTracker is active! 🐾")


# ------------------------
# HELP
# ------------------------

@tree.command(name="help")
async def help(interaction: discord.Interaction):

    await interaction.response.send_message(
        "**🐾 ClanTracker Commands**\n\n"
        "/kit prefix — Create a character\n"
        "/age moons — Age your cat\n"
        "/stats — View character info\n"
        "/clan name — Join a clan\n"
        "/choose_suffix suffix — Pick warrior name\n\n"
        "**Game Commands**\n"
        "/hunt — Catch prey\n"
        "/battle @user — Fight another cat\n\n"
        "**Admin**\n"
        "/make_apprentice @user\n"
        "/make_warrior @user"
    )


bot.run(TOKEN)
