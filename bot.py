import discord
from discord.ext import commands
from discord import app_commands
import os
import random

TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------- GLOBALS -----------------------
characters = {}
pending_hunts = {}
pending_battles = {}
battle_state = {}
camp_quality = {"Thunder": 75, "River": 75, "Shadow": 75, "Wind": 75}
# ----------------------- INITIAL CLAN PREY -----------------------
# Each clan starts with some prey so kits can eat
clan_prey_piles = {
    "Thunder": 20,
    "River": 20,
    "Shadow": 20,
    "Wind": 20
}

fresh_kill_piles = {
    "Thunder": ["mouse", "rabbit", "vole"],
    "River": ["fish", "frog", "water vole"],
    "Shadow": ["rat", "lizard", "frog"],
    "Wind": ["rabbit", "hare", "mouse"]
}
seasons = ["newleaf", "greenleaf", "leaf-fall", "leafbare"]
season = "greenleaf"

prey_tables = {
    "Thunder": {"greenleaf": {"mouse":2,"vole":2,"squirrel":3,"rabbit":5},
                "leafbare": {"mouse":2,"vole":2}},
    "River": {"greenleaf": {"fish":4,"frog":2,"water vole":3},
              "leafbare": {"fish":3}},
    "Shadow": {"greenleaf": {"rat":3,"lizard":2,"frog":2},
               "leafbare": {"rat":3}},
    "Wind": {"greenleaf": {"rabbit":5,"hare":4,"mouse":2},
             "leafbare": {"rabbit":4}}
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

MOVES = {
    "Thunder": [
        {"name": "Claw Swipe", "type": "physical", "damage": 15},
        {"name": "Pounce", "type": "physical", "damage": 20},
        {"name": "Roar", "type": "status", "buff": {"defense_up": 1, "attack_down": 1}},
        {"name": "Charge Strike", "type": "charge", "damage": 35}
    ],
    "River": [
        {"name": "Water Slash", "type": "physical", "damage": 15},
        {"name": "Dive Attack", "type": "charge", "damage": 30},
        {"name": "Soothing Ripple", "type": "status", "buff": {"heal": 10}}
    ],
    "Shadow": [
        {"name": "Shadow Pounce", "type": "physical", "damage": 20},
        {"name": "Stealth Strike", "type": "status", "buff": {"attack_up": 2}}
    ],
    "Wind": [
        {"name": "Gale Swipe", "type": "physical", "damage": 15},
        {"name": "Whirlwind", "type": "charge", "damage": 25},
        {"name": "Endurance Boost", "type": "status", "buff": {"defense_up": 2}}
    ]
}

# ----------------------- UTILITY FUNCTIONS -----------------------
def generate_stats():
    return {stat: random.randint(0, 10) for stat in ["strength","perception","dexterity","speed","intelligence","luck","charisma"]}

def hunger_status(hunger):
    if hunger <= 0: return "💀 Starving!"
    elif hunger < 20: return "⚠️ Starving — hunt immediately."
    elif hunger < 40: return "🥀 Very hungry."
    elif hunger < 60: return "🍂 Getting hungry."
    elif hunger < 80: return "🍖 Satisfied."
    elif hunger < 100: return "😌 Well fed."
    else: return "🐗 Overstuffed."

def health_status(health):
    if health <= 0: return "💀 Dead."
    elif health < 20: return "🚨 Critically injured! See a medicine cat!"
    elif health < 40: return "⚠️ Badly wounded."
    elif health < 70: return "🩹 Injured."
    else: return "💪 Healthy."

def modify_hunger(char, amount):
    char["hunger"] += amount
    char["hunger"] = max(0, min(100, char["hunger"]))
    if char["hunger"] <= 0:
        char["alive"] = False
        return f"💀 {char['prefix']} has starved."
    if char["hunger"] < 20:
        return "⚠️ You are starving."
    return None

def in_battle(user_id):
    for attacker, defender in battle_state.keys():
        if user_id == attacker or user_id == defender:
            return True
    return False

def end_battle(attacker_id, defender_id):
    battle_state.pop((attacker_id, defender_id), None)
    pending_battles.pop(defender_id, None)

def hunger_modifier(hunger):
    if hunger < 30: return -5
    elif hunger < 50: return -2
    elif hunger < 80: return 2
    elif hunger <= 99: return 0
    else: return -3

def hunting_outcome(char, base_success=70):
    hunger = char["hunger"]
    success_chance = base_success
    if hunger <= 0: success_chance -= 40
    elif hunger < 20: success_chance -= 20
    elif hunger < 40: success_chance -= 10
    elif hunger >= 90: success_chance -= 15
    roll = random.randint(1,100)
    success = roll <= success_chance
    food_gained = random.randint(5,15)
    if hunger < 20: food_gained = max(1, food_gained - 5)
    elif hunger < 40: food_gained = max(3, food_gained - 2)
    elif hunger >=70 and hunger < 90: food_gained += 2
    elif hunger >= 90: food_gained = max(1, food_gained - 3)
    hunger_cost = 5
    if char.get("hunt_streak",0) > 3: hunger_cost += 3
    char["hunger"] = max(char["hunger"] - hunger_cost,0)
    return success, food_gained
    
def process_pregnancy_moon():
    for carrier_id, data in list(pregnancies.items()):
        if not data["active"]:
            continue

        carrier = characters.get(carrier_id)
        if not carrier:
            continue

        # Seasonal modifier
        season_mod = seasonal_pregnancy_modifiers.get(season, {"health_mult": 1.0, "max_kits": 4})

        # Increase hunger due to pregnancy
        carrier["hunger"] = min(100, carrier["hunger"] + 10)

        # Factor in exhaustion, training, and camp quality
        exhaustion = carrier.get("exhaustion", 0)
        training = carrier.get("training_sessions", 0)
        camp = camp_quality.get(carrier["clan"], 50)

        base_kit_health = max(0, 100 - (exhaustion * 5 + training * 5))
        kit_health = int(base_kit_health * season_mod["health_mult"])
        data["kit_health_estimate"] = kit_health

        # Check if pregnancy is complete
        current_moon = carrier.get("moons", 0)
        if current_moon - data["start_moon"] >= 5:
            # Number of kits depends on camp + season + mother condition
            max_kits = season_mod["max_kits"]
            kit_count = max(1, min(max_kits, int((camp/25) * (kit_health/50))))
            data["kit_count"] = kit_count

            # Reset mother's status
            data["active"] = False
            carrier["hunger"] = max(carrier["hunger"] - 10, 0)

            # Spawn kits
            for _ in range(kit_count):
                kit_stats = generate_stats()
                kit_id = f"kit_{carrier_id}_{random.randint(1000,9999)}"
                characters[kit_id] = {
                    "prefix": f"{carrier['prefix']}kit",
                    "rank": "kit",
                    "moons": 0,
                    "suffix": None,
                    "clan": carrier["clan"],
                    "health": kit_health,
                    "stats": kit_stats,
                    "specialty": None,
                    "skill_value": 0,
                    "hunger": 50
                }
# ----------------------- EVENTS -----------------------
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands globally")
    print(f"{bot.user} is online!")

# ----------------------- CHARACTER CREATION -----------------------
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
        "hunger": 50,
        "training_sessions":0,
        "exhaustion":0,
        "alive": True
    }
    await interaction.response.send_message(
        f"🐾 **{prefix}kit** has been born!\n"
        f"**Stats**:\n" + "\n".join(f"{k.capitalize()}: {v}" for k,v in stats.items())
    )
# ----------------------- PREGNANCY SYSTEM -----------------------
# Pregnancy rules:
# - Full warriors, 12 moons minimum
# - 5 moons gestation
# - Increased hunger, affected by camp quality and mother’s activity
# - Battle and training effectiveness reduced
# - Mother and partner consent required

def pregnancy_hunger_modifier(stage):
    """Additional hunger per moon of pregnancy"""
    return stage * 5  # can be adjusted

def battle_penalty(stage):
    """Multiplier for battle effectiveness depending on pregnancy stage"""
    if stage <= 2: 
        return 1.0  # early, no effect
    elif stage <= 4: 
        return 0.8  # mid
    else: 
        return 0.6  # late

def pregnancy_effect_on_kits(mother_char, camp_quality):
    """Determine expected kit health/number based on mother and camp"""
    base_kits = random.randint(1, 4)
    health_modifier = 1.0

    # Reduce if camp is poor
    if camp_quality < 50:
        health_modifier -= 0.2
    if mother_char.get("training_sessions", 0) > 3:
        health_modifier -= 0.1  # overworked
    if mother_char.get("hunger", 50) < 40:
        health_modifier -= 0.2  # underfed

    kit_health = max(1, int(100 * health_modifier))
    return base_kits, kit_health

# ---------------- PROPOSE BREEDING ----------------
@bot.tree.command(name="propose_breeding", description="Propose breeding with another full warrior")
async def propose_breeding(interaction: discord.Interaction, partner: discord.Member, carrier: str):
    """
    carrier: 'mother' or 'father' (who will carry the kits)
    """
    uid = interaction.user.id
    pid = partner.id

    if uid not in characters or pid not in characters:
        await interaction.response.send_message("Both must have characters.")
        return

    mother, father = (characters[uid], characters[pid]) if carrier.lower() == "mother" else (characters[pid], characters[uid])

    # Checks
    for char in [mother, father]:
        if char["rank"] != "warrior":
            await interaction.response.send_message("Both characters must be full warriors.")
            return
        if char.get("moons", 0) < 12:
            await interaction.response.send_message("Both characters must be at least 12 moons old.")
            return
        if char.get("pregnant"):
            await interaction.response.send_message("One of the characters is already pregnant.")
            return

    # Consent check (both must agree)
    breeding_request = {
        "proposer": uid,
        "partner": pid,
        "carrier": carrier.lower()
    }
    pending_breeding[(uid, pid)] = breeding_request

    view = View()

    async def accept(i):
        if i.user.id != pid:
            await i.response.send_message("Only the proposed partner can accept.", ephemeral=True)
            return

        # Start pregnancy
        mother["pregnant"] = {
            "months": 0,
            "partner": father["prefix"],
            "carrier": carrier.lower(),
            "season": season
        }

        pending_breeding.pop((uid, pid), None)

        await i.response.edit_message(content=f"🌱 Pregnancy begun! **{mother['prefix']}** is carrying kits.", view=None)

    async def decline(i):
        if i.user.id != pid:
            await i.response.send_message("Only the proposed partner can decline.", ephemeral=True)
            return
        pending_breeding.pop((uid, pid), None)
        await i.response.edit_message(content="❌ Breeding proposal declined.", view=None)

    btn_accept = Button(label="Accept", style=discord.ButtonStyle.green)
    btn_decline = Button(label="Decline", style=discord.ButtonStyle.red)
    btn_accept.callback = accept
    btn_decline.callback = decline
    view.add_item(btn_accept)
    view.add_item(btn_decline)

    await interaction.response.send_message(
        f"🌱 **{characters[uid]['prefix']}** proposes breeding to **{characters[pid]['prefix']}**.\n"
        f"Carrier: {carrier.lower()}. Does {characters[pid]['prefix']} agree?",
        view=view
    )
# ---------------- PREGNANCY STATUS ----------------
@bot.tree.command(name="pregnancy_status", description="Check pregnancy progress")
async def pregnancy_status(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)

    if not char or not char.get("pregnant"):
        await interaction.response.send_message("You are not pregnant.")
        return

    months = char["pregnant"]["months"]
    carrier = char["pregnant"]["carrier"]
    stage_msg = f"🌱 Month {months+1} of 5. Carrier: {carrier}"

    suggestions = []
    if char["hunger"] < 60:
        suggestions.append("Eat more to support your kits.")
    if char.get("training_sessions", 0) > 2:
        suggestions.append("Avoid overtraining to keep kits healthy.")
    if camp_quality[char["clan"]] < 50:
        suggestions.append("Help improve camp quality to benefit kit health.")

    suggestion_msg = "\n".join(suggestions) if suggestions else "You're doing well. Keep resting and eating!"

    await interaction.response.send_message(
        f"{stage_msg}\n\n💡 Suggestions:\n{suggestion_msg}"
    )

# ---------------- UPDATE COMMANDS TO INCLUDE PREGNANCY EFFECT ----------------
# Example: battle_effect
def apply_pregnancy_effects(char, context="battle"):
    if not char.get("pregnant"):
        return 1.0  # no penalty

    stage = char["pregnant"]["months"]
    if context == "battle":
        return battle_penalty(stage)
    return 1.0

# Example usage in battle:
# damage = int(base_damage * apply_pregnancy_effects(attacker_char))

# ---------------- UPDATE HUNTING ----------------
def pregnancy_hunt_modifier(char):
    if not char.get("pregnant"):
        return 0
    stage = char["pregnant"]["months"]
    return stage * 2  # more hunger per stage

# Example usage: char["hunger"] -= base_hunger_cost + pregnancy_hunt_modifier(char)

# ---------------- UPDATE TRAINING ----------------
def pregnancy_train_allowed(char):
    if not char.get("pregnant"):
        return True
    stage = char["pregnant"]["months"]
    return stage <= 2  # only early pregnancy allows light training
# ----------------------- AGE COMMAND -----------------------
@bot.tree.command(name="age", description="Age your character by one moon.")
async def age(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)
    if not char or not char.get("alive", True):
        await interaction.response.send_message("❌ You don't have a living character.")
        return

    # Aging reduces hunger
    char["moons"] = char.get("moons", 0) + 1
    hunger_cost = -10
    char["hunger"] = max(0, char["hunger"] + hunger_cost)

    # Reset training sessions and exhaustion each moon
    char["training_sessions"] = 0
    char["exhaustion"] = 0

    # Hunger warnings
    msg = ""
    if char["hunger"] <= 0:
        char["alive"] = False
        await interaction.response.send_message(f"💀 {char['prefix']} has starved to death.")
        return
    elif char["hunger"] < 20:
        msg = "⚠️ You are starving and need to eat soon!"

    await interaction.response.send_message(
        f"🌙 {char['prefix']} ages one moon.\n"
        f"Age: {char['moons']} moons\n"
        f"Hunger -10 → {char['hunger']}\n"
        f"{msg}"
    )

# ----------------------- PREYPILE COMMAND -----------------------
@bot.tree.command(name="preypile", description="View your clan's prey pile")
async def preypile(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character yet! Use /kit.")
        return

    char = characters[uid]

    if not char.get("clan"):
        await interaction.response.send_message("You haven't joined a clan yet!")
        return

    clan = char["clan"]

    # Ensure starting food exists
    if clan_prey_piles.get(clan, 0) == 0:
        clan_prey_piles[clan] = 10  # starting food points
        fresh_kill_piles[clan] = ["mouse", "rabbit", "vole"]  # starter prey

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
# ----------------------- PROFILE -----------------------
@bot.tree.command(name="profile", description="View your character profile")
async def profile(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)
    if not char:
        await interaction.response.send_message("❌ You don't have a character yet.")
        return
    embed = discord.Embed(title=f"{char['prefix']}'s Profile", color=discord.Color.green())
    embed.add_field(name="Clan", value=char["clan"], inline=True)
    embed.add_field(name="Age", value=f"{char['moons']} moons", inline=True)
    embed.add_field(name="Health ❤️", value=f"{char['health']}/100\n{health_status(char['health'])}", inline=False)
    embed.add_field(name="Hunger 🍖", value=f"{char['hunger']}/100\n{hunger_status(char['hunger'])}", inline=False)
    await interaction.response.send_message(embed=embed)

# ----------------------- CLAN COMMAND -----------------------
@bot.tree.command(name="clan", description="Join a clan")
async def clan(interaction: discord.Interaction, clan_name: str):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("You don't have a character.")
        return
    clan_name = clan_name.capitalize()
    if clan_name not in clan_specialties:
        await interaction.response.send_message("Valid clans: Thunder, River, Shadow, Wind.")
        return
    char = characters[uid]
    char["clan"] = clan_name
    char["specialty"] = clan_specialties[clan_name]
    char["skill_value"] = random.randint(4,10)
    member = interaction.guild.get_member(uid)
    role_name = f"{clan_name}Clan"
    clan_roles = ["ThunderClan", "RiverClan", "ShadowClan", "WindClan"]
    for role in interaction.guild.roles:
        if role.name in clan_roles and role in member.roles:
            await member.remove_roles(role)
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
    await interaction.response.send_message(
        f"{char['prefix']} has joined **{clan_name}Clan**!\n"
        f"Clan skill: **{char['specialty']} ({char['skill_value']})** 🐾"
    )

# ----------------------- HUNT / EAT / DONATE -----------------------
@bot.tree.command(name="hunt", description="Hunt for prey")
async def hunt(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in characters:
        await interaction.response.send_message("Create a character first with /kit.")
        return
    char = characters[uid]
    if in_battle(uid):
        await interaction.response.send_message("⚔️ You can't hunt during battle.")
        return
    if not char["clan"]:
        await interaction.response.send_message("Join a clan first.")
        return
    clan = char["clan"]
    table = prey_tables.get(clan, {}).get(season, {})
    if not table:
        await interaction.response.send_message("No prey available this season.")
        return
    success, food = hunting_outcome(char)
    if not success:
        await interaction.response.send_message(f"{random.choice(hunt_messages)}\n❌ The prey escaped.")
        return
    prey = random.choice(list(table.keys()))
    value = table[prey]
    pending_hunts[uid] = {"prey": prey, "value": value, "clan": clan}
    await interaction.response.send_message(f"{random.choice(hunt_messages)}\n🐾 You caught a **{prey}**! Use /eat or /donate.")

@bot.tree.command(name="eat", description="Eat hunted prey")
async def eat(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in pending_hunts:
        await interaction.response.send_message("You have no prey waiting. Go hunt first!")
        return
    char = characters[uid]
    prey_info = pending_hunts.pop(uid)
    char["hunger"] = min(char["hunger"] + 50, 100)
    await interaction.response.send_message(f"🍖 You ate the **{prey_info['prey']}**!\nHunger: **{char['hunger']}**")

@bot.tree.command(name="donate", description="Add prey to clan pile")
async def donate(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in pending_hunts:
        await interaction.response.send_message("You have no prey waiting. Go hunt first!")
        return
    prey_info = pending_hunts.pop(uid)
    fresh_kill_piles[prey_info["clan"]].append(prey_info["prey"])
    clan_prey_piles[prey_info["clan"]] += prey_info["value"]
    await interaction.response.send_message(f"🐾 Added **{prey_info['prey']}** to **{prey_info['clan']}Clan** fresh kill pile!")

# ----------------------- MEDICINE CAT -----------------------
@bot.tree.command(name="see_medicine_cat", description="Heal yourself via medicine cat")
async def see_medicine_cat(interaction: discord.Interaction):
    uid = interaction.user.id
    if in_battle(uid):
        await interaction.response.send_message("⚔️ You cannot visit the medicine cat during battle.")
        return
    char = characters.get(uid)
    if not char:
        await interaction.response.send_message("You don't have a character.")
        return
    if char["health"] >= 100:
        await interaction.response.send_message("You are already healthy.")
        return
    if not char["clan"]:
        await interaction.response.send_message("Join a clan first.")
        return
    heal = random.randint(10,35)
    old = char["health"]
    char["health"] = min(100, char["health"] + heal)
    healed = char["health"] - old
    clan = char["clan"]
    camp_quality[clan] = max(0, camp_quality[clan] - 2)
    await interaction.response.send_message(f"🌿 The medicine cat treats your wounds.\nRecovered **{healed} HP**.\nHealth: **{char['health']}/100**")

# ----------------------- TRAIN COMMAND -----------------------
@bot.tree.command(name="train", description="Train your character")
async def train(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)
    if not char or not char.get("alive",True):
        await interaction.response.send_message("❌ No living character.")
        return
    max_sessions = 3
    base_hunger_cost = -5
    sessions = char.get("training_sessions",0)
    hunger_cost = base_hunger_cost * (1 + sessions)
    msg = modify_hunger(char,hunger_cost)
    if msg and not char.get("alive",True):
        await interaction.response.send_message(msg)
        return
    char["training_sessions"] = sessions + 1
    if char["training_sessions"] > max_sessions:
        char["exhaustion"] = char.get("exhaustion",0) +1
    if char.get("exhaustion",0) > 5:
        await interaction.response.send_message(f"💤 {char['prefix']} is too exhausted to train this moon!")
        return
    char["stats"]["strength"] = char["stats"].get("strength",10)+1
    await interaction.response.send_message(f"💪 {char['prefix']} trains +1 strength!\nHunger: {char['hunger']}\nExhaustion: {char.get('exhaustion',0)}\n{msg or ''}")

# ----------------------- BATTLE SYSTEM -----------------------
from discord.ui import View, Button

@bot.tree.command(name="attack", description="Challenge someone to battle")
async def attack(interaction: discord.Interaction, opponent: discord.Member):
    uid = interaction.user.id
    oid = opponent.id
    if uid == oid:
        await interaction.response.send_message("❌ You cannot fight yourself.")
        return
    attacker = characters.get(uid)
    defender = characters.get(oid)
    if not attacker or not defender:
        await interaction.response.send_message("❌ One of you doesn't have a character.")
        return
    if attacker["hunger"] < 10:
        await interaction.response.send_message(f"🥀 {attacker['prefix']} is too hungry to fight!")
        return
    pending_battles[oid] = uid
    view = View()
    async def accept(i):
        if i.user.id != oid:
            await i.response.send_message("❌ Only the challenged player can accept.",ephemeral=True)
            return
        battle_state[(uid,oid)] = {"attacker": uid,"defender":oid,"turn":uid,"charge":{}}
        await i.response.edit_message("⚔️ Battle accepted!", view=None)
        await prompt_turn(i, uid, oid)
    async def decline(i):
        if i.user.id != oid:
            await i.response.send_message("❌ Only the challenged player can decline.",ephemeral=True)
            return
        pending_battles.pop(oid,None)
        await i.response.edit_message("❌ Battle declined.",view=None)
    btn_accept = Button(label="Accept",style=discord.ButtonStyle.green)
    btn_decline = Button(label="Decline",style=discord.ButtonStyle.red)
    btn_accept.callback = accept
    btn_decline.callback = decline
    view.add_item(btn_accept)
    view.add_item(btn_decline)
    await interaction.response.send_message(f"⚔️ **{attacker['prefix']}** challenges **{defender['prefix']}**!",view=view)

async def prompt_turn(interaction, attacker_id, defender_id):
    battle = battle_state.get((attacker_id,defender_id))
    if not battle: return
    turn_id = battle["turn"]
    char = characters[turn_id]
    moves = MOVES.get(char["clan"],[])
    view = View(timeout=60)
    for move in moves:
        async def callback(i, move=move):
            if i.user.id != turn_id:
                await i.response.send_message("❌ It's not your turn.",ephemeral=True)
                return
            await execute_move(i, attacker_id, defender_id, move)
        btn = Button(label=move["name"], style=discord.ButtonStyle.blurple)
        btn.callback = callback
        view.add_item(btn)
    await interaction.followup.send(
        f"🎯 **{char['prefix']}**'s turn!",
        view=view
    )

async def execute_move(interaction, attacker_id, defender_id, move):
    battle = battle_state.get((attacker_id, defender_id))
    if not battle:
        await interaction.response.send_message("❌ Battle not found.", ephemeral=True)
        return

    turn_id = battle["turn"]
    enemy_id = defender_id if turn_id == attacker_id else attacker_id

    if interaction.user.id != turn_id:
        await interaction.response.send_message("❌ It's not your turn.", ephemeral=True)
        return

    attacker = characters[turn_id]
    defender = characters[enemy_id]
    result = ""

    # -------- Charge Moves --------
    if move["type"] == "charge":
        charge = battle["charge"].get(turn_id)
        if charge:
            damage = move["damage"]
            defender["health"] = max(defender["health"] - damage, 0)
            battle["charge"].pop(turn_id)
            result = f"💥 {attacker['prefix']} unleashes **{move['name']}** for {damage} damage!"
        else:
            battle["charge"][turn_id] = move
            result = f"⚡ {attacker['prefix']} begins charging **{move['name']}**!"

    # -------- Status Moves --------
    elif move["type"] == "status":
        buffs = move.get("buff", {})
        if "heal" in buffs:
            attacker["health"] = min(attacker["health"] + buffs["heal"], 100)
            result = f"✨ {attacker['prefix']} uses **{move['name']}** and heals {buffs['heal']} HP!"
        else:
            # Can extend for attack_up, defense_up etc.
            result = f"✨ {attacker['prefix']} uses **{move['name']}**!"

    # -------- Physical Moves --------
    else:
        damage = move.get("damage", 5) + hunger_modifier(attacker["hunger"])
        damage = max(1, damage)
        defender["health"] = max(defender["health"] - damage, 0)
        result = f"💥 {attacker['prefix']} uses **{move['name']}** for **{damage} damage**!"

    # Switch turn
    battle["turn"] = enemy_id

    await interaction.response.send_message(
        f"{result}\n"
        f"❤️ {attacker['prefix']} HP: {attacker['health']}\n"
        f"❤️ {defender['prefix']} HP: {defender['health']}"
    )

    # Check victory
    if attacker["health"] <= 0 or defender["health"] <= 0:
        winner = attacker if attacker["health"] > 0 else defender
        loser = defender if winner == attacker else attacker
        end_battle(attacker_id, defender_id)
        await interaction.followup.send(f"🏆 **{winner['prefix']}** wins! **{loser['prefix']}** is defeated.")
        return

    # Continue battle
    await prompt_turn(interaction, attacker_id, defender_id)

# ----------------------- CAMP COMMANDS -----------------------
@bot.tree.command(name="maintain_camp", description="Help maintain the camp")
async def maintain_camp(interaction: discord.Interaction):
    uid = interaction.user.id
    char = characters.get(uid)
    if not char:
        await interaction.response.send_message("Create a character first with /kit.")
        return
    if not char["clan"]:
        await interaction.response.send_message("Join a clan first.")
        return
    clan = char["clan"]
    improvement = random.randint(5,15)
    camp_quality[clan] = min(100, camp_quality[clan]+improvement)
    quality = camp_quality[clan]
    if quality >= 90: condition = "⭐ The camp is in excellent condition! The clan feels energized."
    elif quality >=70: condition = "🌿 The camp is clean and well maintained."
    elif quality >=40: condition = "🪶 The camp is in decent shape."
    elif quality >=15: condition = "⚠️ The camp is getting messy."
    else: condition = "🚨 The camp is falling apart!"
    await interaction.response.send_message(
        f"🧹 You help repair dens and clear debris.\n"
        f"Camp quality improved by **{improvement}** points!\n"
        f"New quality: **{quality}**\n{condition}"
    )

@bot.tree.command(name="camp_decay", description="Lower camp quality (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def camp_decay(interaction: discord.Interaction):
    for clan in camp_quality:
        camp_quality[clan] = max(0, camp_quality[clan]-5)
    await interaction.response.send_message("🌧️ Weather and time have worn down the camps. Camp quality decreased.")

# ----------------------- SEASON COMMANDS -----------------------
@bot.tree.command(name="season", description="Check the current season")
async def check_season(interaction: discord.Interaction):
    await interaction.response.send_message(f"🍃 The current season is **{season}**.")

@bot.tree.command(name="set_season", description="Change the current season (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def set_season(interaction: discord.Interaction, new_season: str):
    global season
    new_season = new_season.lower()
    if new_season not in seasons:
        await interaction.response.send_message("❌ Invalid season! Valid seasons: newleaf, greenleaf, leaf-fall, leafbare.")
        return
    season = new_season
    await interaction.response.send_message(f"🌿 The season has been changed! It is now **{season.capitalize()}**.")

# ----------------------- PING -----------------------
@bot.tree.command(name="ping", description="Check if the bot is active")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("ClanTracker is active! 🐾")

# ----------------------- RUN BOT -----------------------
bot.run(TOKEN)
