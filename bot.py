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
@bot.tree.command(name="age", description="Age your character by one moon.")
async def age(interaction: discord.Interaction):
    user_id = interaction.user.id
    char = characters.get(user_id)

    if not char or not char.get("alive", True):
        await interaction.response.send_message("❌ You don't have a living character.")
        return

    hunger_cost = -10
    msg = modify_hunger(char, hunger_cost)

    if msg and not char.get("alive", True):
        await interaction.response.send_message(msg)
        return

    char["age"] = char.get("age", 0) + 1
    char["training_sessions"] = 0
    char["exhaustion"] = 0

    await interaction.response.send_message(
        f"🌙 {char['prefix']} ages one moon.\n"
        f"Age: {char['age']} moons\n"
        f"Hunger -10\n"
        f"{msg or ''}"
    )
    
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
def hunting_outcome(char, base_success=70):
    """
    Determines the success of a hunt based on hunger.
    Returns: success (bool), food_gained (int)
    """
    hunger = char["hunger"]
    success_chance = base_success

    # Modify success based on hunger
    if hunger <= 0:
        success_chance -= 40  # almost impossible to hunt
    elif hunger < 20:
        success_chance -= 20  # weak, less accurate
    elif hunger < 40:
        success_chance -= 10
    elif hunger < 70:
        pass  # normal
    elif hunger < 90:
        success_chance += 5  # slightly stronger, energetic
    elif hunger <= 100:
        success_chance -= 15  # overstuffed: too slow or heavy

    # Random outcome
    roll = random.randint(1, 100)
    success = roll <= success_chance

    # Food gained is reduced if starving, increased if well-fed
    food_gained = random.randint(5, 15)
    if hunger < 20:
        food_gained = max(1, food_gained - 5)
    elif hunger < 40:
        food_gained = max(3, food_gained - 2)
    elif hunger >= 70 and hunger < 90:
        food_gained += 2
    elif hunger >= 90:
        food_gained = max(1, food_gained - 3)  # overstuffed, inefficient

    # Reduce hunger for effort
    hunger_cost = 5
    if char.get("hunt_streak", 0) > 3:
        hunger_cost += 3  # extra hunger if overused

    char["hunger"] = max(char["hunger"] - hunger_cost, 0)

    return success, food_gained

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
from discord.ui import View, Button
import discord

# ---------------- GLOBAL STATE ----------------
battle_state = {}
pending_battles = {}

# ---------------- MOVES ----------------
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

@bot.tree.command(name="attack", description="Challenge another player to battle")
async def attack(interaction: discord.Interaction, opponent: discord.Member):

    attacker_id = interaction.user.id
    defender_id = opponent.id

    attacker_char = characters.get(attacker_id)
    defender_char = characters.get(defender_id)

    if not attacker_char or not defender_char:
        await interaction.response.send_message("❌ One of you doesn't have a character.")
        return

    if attacker_char["hunger"] < 10:
        await interaction.response.send_message(
            f"🥀 {attacker_char['prefix']} is too hungry to fight!"
        )
        return

    battle_state[(attacker_id, defender_id)] = {
        "attacker": attacker_char,
        "defender": defender_char,
        "turn": "attacker"
    }

    # RESPOND FIRST
    await interaction.response.send_message(
        f"⚔️ **{attacker_char['prefix']}** challenges **{defender_char['prefix']}** to battle!"
    )

    # THEN show move menu
    await prompt_move(interaction, attacker_id, defender_id)

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

        async def confirm(i):
            await i.response.edit_message(
                content="⚠️ You fight despite hunger!",
                view=None
            )
            await initiate_battle(i, opponent)

        async def cancel(i):
            await i.response.edit_message(
                content="Battle cancelled due to hunger.",
                view=None
            )

        btn_yes = Button(label="Fight Anyway", style=discord.ButtonStyle.green)
        btn_no = Button(label="Cancel", style=discord.ButtonStyle.red)

        btn_yes.callback = confirm
        btn_no.callback = cancel

        view.add_item(btn_yes)
        view.add_item(btn_no)

        await interaction.response.send_message(
            "⚠️ You are very hungry! Fight anyway?",
            view=view
        )
        return

    await initiate_battle(interaction, opponent)

# ---------------- INITIATE BATTLE ----------------
async def initiate_battle(interaction, opponent):

    uid = interaction.user.id
    oid = opponent.id

    pending_battles[oid] = {"attacker": uid}

    battle_state[(uid, oid)] = {
        "turn": "attacker",
        "charge": {}
    }

    view = View()

    async def accept(i):
        await i.response.edit_message(content="⚔️ Battle accepted!", view=None)
        await prompt_move(i, uid, oid)

    async def decline(i):
        pending_battles.pop(oid, None)
        battle_state.pop((uid, oid), None)

        await i.response.edit_message(
            content="❌ Battle declined.",
            view=None
        )

    btn_accept = Button(label="Accept Battle", style=discord.ButtonStyle.green)
    btn_decline = Button(label="Decline Battle", style=discord.ButtonStyle.red)

    btn_accept.callback = accept
    btn_decline.callback = decline

    view.add_item(btn_accept)
    view.add_item(btn_decline)

    await interaction.followup.send(
        f"⚔️ **{characters[uid]['prefix']}** has challenged **{opponent.display_name}**!",
        view=view
    )

# ---------------- PROMPT MOVE ----------------
async def prompt_move(interaction, attacker_id, defender_id):
async def prompt_move(interaction, attacker_id, defender_id):
    battle = battle_state.get((attacker_id, defender_id))

    if not battle:
        await interaction.followup.send("⚠️ Battle not found.")
        return

    attacker = battle["attacker"]
    defender = battle["defender"]

    class MoveView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)

        @discord.ui.button(label="Strike", style=discord.ButtonStyle.red)
        async def strike(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != attacker_id:
                await button_interaction.response.send_message(
                    "❌ It's not your turn.", ephemeral=True
                )
                return

            damage = random.randint(8, 15)

            # Hunger weakness modifier
            if attacker["hunger"] < 20:
                damage = int(damage * 0.7)

            defender["health"] -= damage

            await button_interaction.response.send_message(
                f"⚔️ **{attacker['prefix']}** strikes **{defender['prefix']}** for **{damage} damage!**"
            )

            if defender["health"] <= 0:
                await button_interaction.followup.send(
                    f"💀 **{defender['prefix']}** has been defeated!"
                )
                del battle_state[(attacker_id, defender_id)]
                return

            await prompt_move(button_interaction, defender_id, attacker_id)

        @discord.ui.button(label="Heavy Strike", style=discord.ButtonStyle.blurple)
        async def heavy_strike(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != attacker_id:
                await button_interaction.response.send_message(
                    "❌ It's not your turn.", ephemeral=True
                )
                return

            damage = random.randint(15, 25)

            if attacker["hunger"] < 20:
                damage = int(damage * 0.6)

            defender["health"] -= damage

            await button_interaction.response.send_message(
                f"💥 **{attacker['prefix']}** unleashes a **Heavy Strike** for **{damage} damage!**"
            )

            if defender["health"] <= 0:
                await button_interaction.followup.send(
                    f"💀 **{defender['prefix']}** has been defeated!"
                )
                del battle_state[(attacker_id, defender_id)]
                return

            await prompt_move(button_interaction, defender_id, attacker_id)

        @discord.ui.button(label="Flee", style=discord.ButtonStyle.gray)
        async def flee(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != attacker_id:
                await button_interaction.response.send_message(
                    "❌ You can't flee from someone else's battle.", ephemeral=True
                )
                return

            await button_interaction.response.send_message(
                f"🏃 **{attacker['prefix']}** flees from battle!"
            )

            del battle_state[(attacker_id, defender_id)]

    view = MoveView()

    await interaction.followup.send(
        f"⚔️ **{attacker['prefix']}'s turn!**\nChoose your move:",
        view=view
    )
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

    await interaction.followup.send(
        f"🎯 {char['prefix']}'s turn! Choose a move:",
        view=view
    )

# ---------------- EXECUTE MOVE ----------------
async def execute_move(interaction, attacker_id, defender_id, turn_id, move):

    battle = battle_state[(attacker_id, defender_id)]

    attacker_char = characters[turn_id]
    defender_id_actual = defender_id if turn_id == attacker_id else attacker_id
    defender_char = characters[defender_id_actual]

    # Charge move
    if move["type"] == "charge":

        charge = battle["charge"].get(turn_id)

        if charge:
            damage = move["damage"]

            defender_char["health"] = max(
                defender_char["health"] - damage,
                0
            )

            battle["charge"].pop(turn_id)

            result = f"💥 {attacker_char['prefix']} unleashes **{move['name']}** for {damage} damage!"

        else:
            battle["charge"][turn_id] = move
            result = f"⚡ {attacker_char['prefix']} begins charging **{move['name']}**!"

    elif move["type"] == "status":

        buffs = move.get("buff", {})

        if "heal" in buffs:
            attacker_char["health"] = min(
                attacker_char["health"] + buffs["heal"],
                100
            )

        result = f"✨ {attacker_char['prefix']} uses **{move['name']}**!"

    else:

        damage = move.get("damage", 10) + hunger_modifier_battle(attacker_char["hunger"])

        defender_char["health"] = max(
            defender_char["health"] - damage,
            0
        )

        result = f"💥 {attacker_char['prefix']} hits for **{damage} damage**!"

    # Switch turn
    battle["turn"] = "defender" if battle["turn"] == "attacker" else "attacker"

    await interaction.response.send_message(
        f"{result}\n"
        f"❤️ {attacker_char['prefix']} HP: {attacker_char['health']}\n"
        f"❤️ {defender_char['prefix']} HP: {defender_char['health']}"
    )

    # Battle end
    if attacker_char["health"] <= 0 or defender_char["health"] <= 0:

        winner = attacker_char if attacker_char["health"] > 0 else defender_char
        loser = defender_char if winner == attacker_char else attacker_char

        battle_state.pop((attacker_id, defender_id), None)
        pending_battles.pop(defender_id, None)

        await interaction.followup.send(
            f"🏆 **{winner['prefix']}** wins! **{loser['prefix']}** is defeated."
        )

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
@bot.tree.command(name="train", description="Train to improve your skills.")
@bot.tree.command(name="train", description="Train your character to improve stats.")
async def train(interaction: discord.Interaction):
    user_id = interaction.user.id
    char = characters.get(user_id)

    if not char or not char.get("alive", True):
        await interaction.response.send_message("❌ You don't have a living character.")
        return

    max_sessions = 3
    base_hunger_cost = -5

    # Calculate hunger cost multiplier for repeated training
    sessions_this_moon = char.get("training_sessions", 0)
    hunger_cost = base_hunger_cost * (1 + sessions_this_moon)  # more training = more hunger

    msg = modify_hunger(char, hunger_cost)
    if msg and not char.get("alive", True):
        await interaction.response.send_message(msg)
        return

    # Exhaustion logic
    char["training_sessions"] = sessions_this_moon + 1
    if char["training_sessions"] > max_sessions:
        char["exhaustion"] = char.get("exhaustion", 0) + 1

    if char.get("exhaustion", 0) > 5:
        await interaction.response.send_message(f"💤 {char['prefix']} is too exhausted to train further this moon!")
        return

    # Apply stat gains (example)
    char["strength"] = char.get("strength", 10) + 1

    await interaction.response.send_message(
        f"💪 {char['prefix']} trains and gains +1 strength!\n"
        f"Hunger: {char['hunger']}\n"
        f"Exhaustion: {char.get('exhaustion',0)}\n"
        f"{msg or ''}"
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
