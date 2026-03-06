import discord
from discord.ext import commands
import os
import random 

TOKEN = os.environ["TOKEN"]

# Intents (required for message content)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is online and ready!")

# Command: ping
@bot.command()
async def ping(ctx):
    await ctx.send("ClanTracker is active! 🐾")

# Example: create_kit command (optional)
@bot.command()
async def create_kit(ctx, name):
    stats = {
        "strength": random.randint(1, 10),
        "speed": random.randint(1, 10),
        "intelligence": random.randint(1, 10)
    }
    await ctx.send(f"Kit {name} created with stats: {stats}")

bot.run(TOKEN)
