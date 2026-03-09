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
    # ----------------- Battle Imports -----------------
#
 from discord.ui import View, Button
import random
import discord

# ----------------- MOVES SETUP -----------------
# Each move has: 'type' (damage/buff/debuff/charge), 'power', 'target', 'duration' if needed
MOVES = {
    "Thunder": [
        {"name": "Claw Swipe", "type": "damage", "power": 15},
        {"name": "Pounce", "type": "damage", "power": 20},
        {"name": "Thunder Roar", "type": "buff", "stat": "strength", "amount": 5, "duration": 1}
    ],
    "River": [
        {"name": "Water Slash", "type": "damage", "power": 15},
        {"name": "Dive Attack", "type": "damage", "power": 20},
        {"name": "Soothing Splash", "type": "buff", "stat": "defense", "amount": 5, "duration": 1}
    ],
    "Shadow": [
        {"name": "Shadow Strike", "type": "damage", "power": 18},
        {"name": "Stealth Move", "type": "buff", "stat": "speed", "amount": 5, "duration": 1},
        {"name": "Night Pounce", "type": "charge", "power": 35, "charge_turns": 2}
    ],
    "Wind": [
        {"name": "Wind Slash", "type": "damage", "power": 15},
        {"name": "Tail Sweep", "type": "damage", "power": 12},
        {"name": "Speed Boost", "type": "buff", "stat": "speed", "amount": 5, "duration": 1}
    ]
}

# ----------------- BATTLE STATE -----------------
# Track ongoing battle turns, charge moves, and stat modifications
battle_state = {}  # key: tuple(attacker_id, defender_id) -> dict

# ----------------- START BATTLE FUNCTION -----------------
async def start_battle(interaction: discord.Interaction, opponent: discord.Member):
    attacker_id = interaction.user.id
    defender_id = opponent.id

    pending_battles[defender_id] = {"attacker": attacker_id, "opponent": defender_id}

    battle_state[(attacker_id, defender_id)] = {
        "turn": "attacker",
        "charge": {},        # who has a move charging
        "modifiers": {attacker_id: {}, defender_id: {}}
    }

    await interaction.followup.send(
        f"⚔️ **{characters[attacker_id]['prefix']}** has challenged **{opponent.display_name}**!\n"
        f"{opponent.mention}, do you accept? Use the **Accept Battle** button below."
    )

    # Create accept/decline buttons for the defender
    view = View()
    
    async def accept_callback(i: discord.Interaction):
        await i.response.edit_message(content=f"✅ **{opponent.display_name}** accepted the battle!", view=None)
        await prompt_move(i, attacker_id, defender_id)

    async def decline_callback(i: discord.Interaction):
        pending_battles.pop(defender_id, None)
        battle_state.pop((attacker_id, defender_id), None)
        await i.response.edit_message(content=f"❌ **{opponent.display_name}** declined the battle.", view=None)

    accept_btn = Button(label="Accept Battle", style=discord.ButtonStyle.green)
    decline_btn = Button(label="Decline Battle", style=discord.ButtonStyle.red)
    accept_btn.callback = accept_callback
    decline_btn.callback = decline_callback
    view.add_item(accept_btn)
    view.add_item(decline_btn)

    await interaction.followup.send(view=view)

# ----------------- MOVE SELECTION -----------------
async def prompt_move(interaction: discord.Interaction, attacker_id, defender_id):
    # Determine whose turn
    battle = battle_state[(attacker_id, defender_id)]
    turn_user = attacker_id if battle["turn"] == "attacker" else defender_id
    user_char = characters[turn_user]

    # Check for low health warning
    max_health = 100
    low_health_threshold = 25
    if user_char["health"] <= low_health_threshold:
        # Show warning with Continue/Flee
        view = View()

        async def continue_callback(i: discord.Interaction):
            await i.response.edit_message(content=f"⚔️ **{user_char['prefix']}** chooses to continue!", view=None)
            await prompt_move_turn(i, attacker_id, defender_id)

        async def flee_callback(i: discord.Interaction):
            target_id = defender_id if turn_user == attacker_id else attacker_id
            target_char = characters[target_id]
            flee_damage = 5  # small penalty
            user_char["health"] = max(user_char["health"] - flee_damage, 0)
            battle_state.pop((attacker_id, defender_id), None)
            pending_battles.pop(defender_id, None)
            await i.response.edit_message(
                content=f"💨 **{user_char['prefix']}** flees from battle!\n"
                        f"They take **{flee_damage} damage** for retreat.\n"
                        f"💖 HP now: {user_char['health']}",
                view=None
            )

        btn_continue = Button(label="Continue", style=discord.ButtonStyle.green)
        btn_flee = Button(label="Flee", style=discord.ButtonStyle.red)
        btn_continue.callback = continue_callback
        btn_flee.callback = flee_callback
        view.add_item(btn_continue)
        view.add_item(btn_flee)

        await interaction.followup.send(
            f"⚠️ **{user_char['prefix']}'s health is low ({user_char['health']} HP)!**\n"
            "Do you want to continue or flee?",
            view=view
        )
        return

    # Normal turn if not low health
    await prompt_move_turn(interaction, attacker_id, defender_id)

# ----------------- PROMPT TURN FUNCTION -----------------
async def prompt_move_turn(interaction: discord.Interaction, attacker_id, defender_id):
    battle = battle_state[(attacker_id, defender_id)]
    turn_user = attacker_id if battle["turn"] == "attacker" else defender_id
    user_char = characters[turn_user]

    # Prepare buttons for all moves (including charge moves)
    view = View()
    clan_moves = MOVES.get(user_char["clan"], [])

    for move in clan_moves:
        async def move_callback(i: discord.Interaction, move=move):
            await execute_move(i, attacker_id, defender_id, turn_user, move)

        btn = Button(label=move["name"], style=discord.ButtonStyle.blurple)
        btn.callback = move_callback
        view.add_item(btn)

    await interaction.followup.send(
        f"🎯 **{user_char['prefix']}'s turn!** Choose a move:",
        view=view
    )

# ----------------- EXECUTE MOVE -----------------
async def execute_move(interaction: discord.Interaction, attacker_id, defender_id, user_id, move):
    battle = battle_state[(attacker_id, defender_id)]
    target_id = defender_id if user_id == attacker_id else attacker_id
    user_char = characters[user_id]
    target_char = characters[target_id]

    result_text = f"**{user_char['prefix']}** used **{move['name']}**!\n"

    # Handle charge moves
    if move["type"] == "charge":
        if user_id in battle["charge"]:
            # Attack now
            power = move["power"]
            damage = max(power, 0)
            target_char["health"] = max(target_char["health"] - damage, 0)
            result_text += f"💥 Charged move hits for **{damage} damage**!\n"
            battle["charge"].pop(user_id)
        else:
            # Start charging
            battle["charge"][user_id] = {"move": move, "turns_left": move["charge_turns"]}
            result_text += f"⚡ {move['name']} is charging! Will be ready in {move['charge_turns']} turn(s).\n"

from discord.ui import View, Button
import random

# ---------------- GLOBAL BATTLE STATE ----------------
battle_state = {}  # keys: (attacker_id, defender_id), values: battle info

# ---------------- MOVES ----------------
# Example moves: name, type (physical/magic/status), effect
MOVES = {
    "Thunder": [
        {"name": "Claw Swipe", "type": "physical", "damage": 15},
        {"name": "Pounce", "type": "physical", "damage": 20},
        {"name": "Roar", "type": "status", "buff": {"defense_up": 1, "attack_down": 1}},
        {"name": "Charge Strike", "type": "charge", "damage": 35, "charge_turns": 2},
    ],
    "River": [
        {"name": "Water Slash", "type": "physical", "damage": 15},
        {"name": "Dive Attack", "type": "charge", "damage": 30, "charge_turns": 2},
        {"name": "Soothing Ripple", "type": "status", "buff": {"heal": 10}},
    ],
    "Shadow": [
        {"name": "Shadow Pounce", "type": "physical", "damage": 20},
        {"name": "Stealth Strike", "type": "status", "buff": {"attack_up": 2}},
    ],
    "Wind": [
        {"name": "Gale Swipe", "type": "physical", "damage": 15},
        {"name": "Whirlwind", "type": "charge", "damage": 25, "charge_turns": 1},
        {"name": "Endurance Boost", "type": "status", "buff": {"defense_up": 2}},
    ]
}

# ---------------- HUNGER MODIFIER ----------------
def hunger_modifier_battle(hunger):
    if hunger < 30:
        return -5
    elif hunger < 50:
        return -2
    elif hunger < 80:
        return 2
    elif hunger <= 99:
        return 0
    else:
        return -3

# ---------------- START BATTLE ----------------
async def start_battle(interaction, opponent):
    uid = interaction.user.id
    oid = opponent.id

    attacker = characters[uid]
    # Hunger warning
    if attacker["hunger"] < 20:
        view = View()

        async def confirm_callback(interact):
            await interact.response.edit_message(content="You bravely proceed despite hunger!", view=None)
            await initiate_battle(interaction, opponent)

        async def cancel_callback(interact):
            await interact.response.edit_message(content="Battle cancelled due to hunger.", view=None)
        
        view.add_item(Button(label="Yes", style=discord.ButtonStyle.green, callback=confirm_callback))
        view.add_item(Button(label="No", style=discord.ButtonStyle.red, callback=cancel_callback))
        await interaction.response.send_message(
            "⚠️ You are too hungry to fight! Proceed?", view=view
        )
        return

    await initiate_battle(interaction, opponent)

# ---------------- INITIATE BATTLE ----------------
async def initiate_battle(interaction, opponent):
    uid = interaction.user.id
    oid = opponent.id
    pending_battles[oid] = {"attacker": uid, "opponent": oid}
    battle_state[(uid, oid)] = {
        "turn": "attacker",
        "charge": {}  # track charge moves
    }

    await interaction.followup.send(
        f"⚔️ **{characters[uid]['prefix']}** has challenged **{opponent.display_name}**!\n"
        f"{opponent.mention}, do you accept? Use `/fight` to fight or `/flee` to flee."
    )

# ---------------- PROMPT MOVE ----------------
async def prompt_move(interaction, attacker_id, defender_id):
    battle = battle_state.get((attacker_id, defender_id))
    if not battle:
        await interaction.response.send_message("No active battle found.")
        return

    turn_id = attacker_id if battle["turn"] == "attacker" else defender_id
    char = characters[turn_id]

    # Low health warning
    low_health = 25
    if char["health"] <= low_health:
        view = View()
        async def cont(i):
            await i.response.edit_message(content=f"{char['prefix']} continues the fight!", view=None)
            await prompt_turn(interaction, attacker_id, defender_id)
        async def flee(i):
            other_id = defender_id if turn_id == attacker_id else attacker_id
            characters[turn_id]["health"] = max(char["health"] - 5, 0)
            battle_state.pop((attacker_id, defender_id))
            pending_battles.pop(defender_id, None)
            await i.response.edit_message(
                content=f"{char['prefix']} flees! 💨\nHealth: {char['health']}", view=None
            )
        view.add_item(Button(label="Continue", style=discord.ButtonStyle.green, callback=cont))
        view.add_item(Button(label="Flee", style=discord.ButtonStyle.red, callback=flee))
        await interaction.followup.send(
            f"⚠️ {char['prefix']}'s health is low ({char['health']})! Continue or flee?", view=view
        )
        return

    await prompt_turn(interaction, attacker_id, defender_id)

# ---------------- PROMPT TURN ----------------
async def prompt_turn(interaction, attacker_id, defender_id):
    battle = battle_state[(attacker_id, defender_id)]
    turn_id = attacker_id if battle["turn"] == "attacker" else defender_id
    char = characters[turn_id]

    moves = MOVES.get(char["clan"], [])
    view = View()
    for move in moves:
        async def move_callback(i, move=move):
            await execute_move(i, attacker_id, defender_id, turn_id, move)
        btn = Button(label=move["name"], style=discord.ButtonStyle.blurple)
        btn.callback = move_callback
        view.add_item(btn)
    
    await interaction.followup.send(f"🎯 {char['prefix']}'s turn! Choose a move:", view=view)

# ---------------- EXECUTE MOVE ----------------
async def execute_move(interaction, attacker_id, defender_id, turn_id, move):
    battle = battle_state[(attacker_id, defender_id)]
    attacker_char = characters[turn_id]
    defender_id_actual = defender_id if turn_id == attacker_id else attacker_id
    defender_char = characters[defender_id_actual]

    # Charge moves
    if move["type"] == "charge":
        charge_info = battle["charge"].get(turn_id, {"turns_left": move["charge_turns"], "move": move})
        if charge_info["turns_left"] > 1:
            charge_info["turns_left"] -= 1
            battle["charge"][turn_id] = charge_info
            await interaction.response.send_message(
                f"⚡ {attacker_char['prefix']} is charging **{move['name']}** ({charge_info['turns_left']} turns left)"
            )
            battle["turn"] = "defender" if battle["turn"] == "attacker" else "attacker"
            await prompt_move(interaction, attacker_id, defender_id)
            return
        else:
            # Execute charged move
            damage = move["damage"]
            defender_char["health"] = max(defender_char["health"] - damage, 0)
            battle["charge"].pop(turn_id)
            result_text = f"💥 {attacker_char['prefix']} executes **{move['name']}** for {damage} damage!"
    elif move["type"] == "status":
        # Apply buffs/debuffs (simplified for this example)
        buffs = move.get("buff", {})
        if "heal" in buffs:
            attacker_char["health"] = min(attacker_char["health"] + buffs["heal"], 100)
        result_text = f"✨ {attacker_char['prefix']} uses **{move['name']}** and applies effects: {buffs}"
    else:  # physical move
        damage = move.get("damage", 10) + hunger_modifier_battle(attacker_char["hunger"])
        defender_char["health"] = max(defender_char["health"] - damage, 0)
        result_text = f"💥 {attacker_char['prefix']} uses **{move['name']}** for {damage} damage!"

    # Switch turn
    battle["turn"] = "defender" if battle["turn"] == "attacker" else "attacker"

    await interaction.response.send_message(
        f"{result_text}\n💖 {attacker_char['prefix']} HP: {attacker_char['health']}, {defender_char['prefix']} HP: {defender_char['health']}"
    )

    # Check if battle is over
    if attacker_char["health"] <= 0 or defender_char["health"] <= 0:
        winner = attacker_char if attacker_char["health"] > 0 else defender_char
        loser = defender_char if winner == attacker_char else attacker_char
        battle_state.pop((attacker_id, defender_id))
        pending_battles.pop(defender_id, None)
        await interaction.followup.send(f"🏆 **{winner['prefix']}** wins! **{loser['prefix']}** is defeated.")

    else:
        await prompt_move(interaction, attacker_id, defender_id)
# ----------------- Camp Maintenance -----------------
#
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
