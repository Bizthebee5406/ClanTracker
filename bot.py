import discord
from discord.ext import commands
import os
import random 

TOKEN = os.environ["TOKEN"]

# Intents (required for message content)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

kits = {}  # Stores all kits/apprentices/warriors

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
async def create_kit(ctx, *, name):
    """Create a new kit with automatic 'kit' suffix."""
    first_name = name.strip().split()[0]  # Take the first word as internal name

    if first_name in kits:
        await ctx.send(f"A kit named {display_name(kits[first_name])} already exists!")
        return

    kits[first_name] = {
        "first_name": first_name,
        "second_name": None,
        "rank": "kit",
        "strength": random.randint(1, 10),
        "agility": random.randint(1, 10),
        "intelligence": random.randint(1, 10),
        "age": 0,
        "clan": "None"
    }

    await ctx.send(f"🐣 {display_name(kits[first_name])} has been born!")


@bot.command()
async def age(ctx, *, name):
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
async def ping(ctx):
    await ctx.send("ClanTracker is active! 🐾")

bot.run(TOKEN)
