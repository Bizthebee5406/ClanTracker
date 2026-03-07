import discord
from discord.ext import commands
import os
import random 
import json
from discord import app_commands

TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

characters = {}

@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user} is online and ready!")
    
@tree.command(name="kit")
async def kit(interaction: discord.Interaction, prefix: str):
    name = f"{prefix}kit"

    characters[interaction.user.id] = {
        "prefix": prefix,
        "rank": "kit",
        "moons": 0,
        "suffix": None
    }

    await interaction.response.send_message(f"{name} has been born into the Clan! 🐾")
    
@tree.command(name="age")
async def age(interaction: discord.Interaction, moons: int):

    if interaction.user.id not in characters:
        await interaction.response.send_message("You don't have a character yet. Use /kit first.")
        return

    characters[interaction.user.id]["moons"] += moons
    moons_now = characters[interaction.user.id]["moons"]

    if characters[interaction.user.id]["rank"] == "kit" and moons_now >= 6:
        characters[interaction.user.id]["rank"] = "apprentice"
        name = f"{characters[interaction.user.id]['prefix']}paw"

        await interaction.response.send_message(
            f"🌙 You are now {moons_now} moons old and have been promoted to **apprentice**! Your name is now **{name}** 🐾"
        )
    else:
        await interaction.response.send_message(f"🌙 You are now {moons_now} moons old!")
        
@tree.command(name="stats")
async def stats(interaction: discord.Interaction):

    if interaction.user.id not in characters:
        await interaction.response.send_message("You don't have a character yet. Use /kit first.")
        return

    char = characters[interaction.user.id]

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
        f"Age: {char['moons']} moons"
    )
    
@tree.command()
async def clan(ctx, *, clan_name):
    # Make sure the player has a character
    if ctx.author.id not in characters:
        await ctx.send("You don't have a character yet. Use !kit <name> first.")
        return

    char = characters[ctx.author.id]
    char["clan"] = clan_name
    await ctx.send(f"{char['prefix']} has joined **{clan_name} Clan**! 🐾")
@tree.command()
@commands.has_permissions(administrator=True)
async def make_apprentice(ctx, member: discord.Member):
    if member.id not in characters:
        await ctx.send("That player has no character.")
        return

    char = characters[member.id]

    if char["rank"] != "kit":
        await ctx.send("They are not a kit.")
        return

    if char["moons"] < 6:
        await ctx.send("They must be at least 6 moons old to become an apprentice.")
        return

    char["rank"] = "apprentice"
    name = f"{char['prefix']}paw"

    await ctx.send(f"{member.mention} has been named **{name}**, apprentice of the Clan! 🐾")

@bot.command()
async def choose_suffix(ctx, suffix):
    if ctx.author.id not in characters:
        await ctx.send("You don't have a character.")
        return

    char = characters[ctx.author.id]

    if char["rank"] != "apprentice":
        await ctx.send("Only apprentices can choose their warrior suffix.")
        return

    char["suffix"] = suffix

    await ctx.send(f"You have chosen the warrior name **{char['prefix']}{suffix}**.")

@bot.command()
@commands.has_permissions(administrator=True)
async def make_warrior(ctx, member: discord.Member):
    if member.id not in characters:
        await ctx.send("That player has no character.")
        return

    char = characters[member.id]

    if char["rank"] != "apprentice":
        await ctx.send("They are not an apprentice.")
        return

    if not char["suffix"]:
        await ctx.send("They have not chosen their warrior suffix yet.")
        return

    char["rank"] = "warrior"
    name = f"{char['prefix']}{char['suffix']}"

    await ctx.send(f"{member.mention} is now **{name}**, a warrior of the Clan! 🐾")

@bot.command()
async def ping(ctx):
    await ctx.send("ClanTracker is active! 🐾")

bot.run(TOKEN)
