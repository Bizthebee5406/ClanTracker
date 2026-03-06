import discord
from discord.ext import commands
import os
import random 
import json

TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

kits = {}
characters = {}

def display_name(kit):
    """Return the full display name based on rank."""
    first = kit["first_name"]
    rank = kit["rank"]

    if rank == "kit":
        return f"{first}kit"
    elif rank == "apprentice":
        return f"{first}paw"
    elif rank == "warrior":
        second = kit.get("second_name", "")
        return f"{first}{second}" if second else f"{first}"

@bot.event
async def on_ready():
    print(f"{bot.user} is online and ready!")

@bot.command()
async def create_kit(ctx, prefix):
    name = f"{prefix}kit"

    characters[ctx.author.id] = {
        "prefix": prefix,
        "rank": "kit",
        "moons": 0,
        "suffix": None
    }

    save_characters()

    await ctx.send(f"{name} has been born into the Clan! 🐾")

@bot.command()
async def age(ctx, name):
    first_name = name.strip().split()[0]

    if first_name not in kits:
        await ctx.send("That kit does not exist.")
        return

    kits[first_name]["age"] += 1
    kit = kits[first_name]

    # Example: promote to apprentice at age 3
    if kit["age"] >= 3 and kit["rank"] == "kit":
        kit["rank"] = "apprentice"
        await ctx.send(f"🌙 {display_name(kit)} is now an apprentice!")
    else:
        await ctx.send(f"🌙 {display_name(kit)} is now {kit['age']} moons old!")

@bot.command()
async def stats(ctx, *, name):
    first_name = name.strip().split()[0]

    if first_name not in kits:
        await ctx.send("That kit does not exist.")
        return

    kit = kits[first_name]

    await ctx.send(
        f"📜 Stats for {display_name(kit)}:\n"
        f"Strength: {kit['strength']}\n"
        f"Agility: {kit['agility']}\n"
        f"Intelligence: {kit['intelligence']}\n"
        f"Age: {kit['age']}\n"
        f"Clan: {kit['clan']}"
    )

@bot.command()
async def clan(ctx, *, args):
    parts = args.strip().split()
    if len(parts) < 2:
        await ctx.send("Usage: !clan <kit_name> <clan_name>")
        return

    first_name = parts[0]
    clan_name = " ".join(parts[1:])

    if first_name not in kits:
        await ctx.send("That kit does not exist.")
        return

    kits[first_name]["clan"] = clan_name
    await ctx.send(f"{display_name(kits[first_name])} has joined {clan_name} Clan!")

@bot.command()
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
