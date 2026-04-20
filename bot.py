import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import io
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────────────────────────
TOKEN = "MTQ5NTYzMjMxNTM2NjI0ODQ1OA.GDVQy5.HUcm-DX1A5h5Veig1VlZgpVAWkDQT1UY1TjqjQ"   # paste your bot token here
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "players.json")

TIERS = ["Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"]
REGIONS = ["NA", "AU", "EU", "AS"]
MODES = ["overall", "ltm", "vanilla", "uhc", "pot", "nethop", "smp", "sword", "axe", "mace", "diamondsmp", "cart"]

TIER_COLORS = {
    "Tier 1": 0xFFD700,
    "Tier 2": 0xF5820A,
    "Tier 3": 0xE05252,
    "Tier 4": 0x9B7BF7,
    "Tier 5": 0x6A6A7E,
    None:     0x2B2D35,
}

# ── DATA HELPERS ─────────────────────────────────────────────────────────────
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"players": {}}

def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── BOT SETUP ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

def is_admin():
    """Check decorator — only server administrators."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Only **administrators** can use OF Tiers bot commands.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

def tier_choices():
    return [app_commands.Choice(name=t, value=t) for t in TIERS]

def region_choices():
    return [app_commands.Choice(name=r, value=r) for r in REGIONS]

def mode_choices():
    return [app_commands.Choice(name=m.upper(), value=m) for m in MODES]

# ── EVENTS ───────────────────────────────────────────────────────────────────
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = str(error)
    if isinstance(error, app_commands.CheckFailure):
        return  # already handled inside the check
    if not interaction.response.is_done():
        await interaction.response.send_message(f"❌ An error occurred: {msg}", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ An error occurred: {msg}", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name="PVP Rankings"
    ))
    print(f"✅  OF Tiers Bot is online as {bot.user}")

# ── /addplayer ────────────────────────────────────────────────────────────────
@tree.command(name="addplayer", description="Add a player to OF Tiers (tier is optional)")
@app_commands.describe(
    name="Player's Minecraft username",
    region="Player's region",
    overall_tier="Overall tier (optional — leave blank to add without a tier)",
)
@app_commands.choices(
    region=region_choices(),
    overall_tier=tier_choices(),
)
@is_admin()
async def addplayer(
    interaction: discord.Interaction,
    name: str,
    region: app_commands.Choice[str],
    overall_tier: app_commands.Choice[str] = None,
):
    data = load_data()
    key = name.lower()

    if key in data["players"]:
        await interaction.response.send_message(
            f"⚠️ **{name}** is already in the rankings. Use `/settier` to update their tier.",
            ephemeral=True
        )
        return

    tier_val = overall_tier.value if overall_tier else None

    data["players"][key] = {
        "name": name,
        "region": region.value,
        "tiers": {"overall": tier_val} if tier_val else {},
        "added": datetime.utcnow().isoformat(),
    }
    save_data(data)

    color = TIER_COLORS.get(tier_val, TIER_COLORS[None])
    embed = discord.Embed(
        title="✅ Player Added",
        description=f"**{name}** has been added to OF Tiers.",
        color=color
    )
    embed.add_field(name="Region", value=region.value, inline=True)
    embed.add_field(name="Overall Tier", value=tier_val or "*(unranked)*", inline=True)
    embed.set_footer(text=f"Added by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ── /removeplayer ─────────────────────────────────────────────────────────────
@tree.command(name="removeplayer", description="Remove a player from OF Tiers completely")
@app_commands.describe(name="Player's Minecraft username")
@is_admin()
async def removeplayer(interaction: discord.Interaction, name: str):
    data = load_data()
    key = name.lower()
    if key not in data["players"]:
        await interaction.response.send_message(f"❌ **{name}** was not found.", ephemeral=True)
        return
    actual_name = data["players"][key]["name"]
    del data["players"][key]
    save_data(data)
    await interaction.response.send_message(
        embed=discord.Embed(title="🗑️ Player Removed", description=f"**{actual_name}** has been removed from OF Tiers.", color=0xFF4444)
    )

# ── /settier ──────────────────────────────────────────────────────────────────
@tree.command(name="settier", description="Set or update a player's tier for a specific mode")
@app_commands.describe(
    name="Player's Minecraft username",
    mode="Game mode to set the tier for",
    tier="Tier to assign",
)
@app_commands.choices(mode=mode_choices(), tier=tier_choices())
@is_admin()
async def settier(
    interaction: discord.Interaction,
    name: str,
    mode: app_commands.Choice[str],
    tier: app_commands.Choice[str],
):
    data = load_data()
    key = name.lower()
    if key not in data["players"]:
        await interaction.response.send_message(
            f"❌ **{name}** not found. Use `/addplayer` first.", ephemeral=True
        )
        return

    data["players"][key]["tiers"][mode.value] = tier.value
    save_data(data)

    embed = discord.Embed(
        title="🏆 Tier Updated",
        description=f"**{data['players'][key]['name']}** — {mode.name.upper()} → **{tier.value}**",
        color=TIER_COLORS.get(tier.value, 0x4ade80)
    )
    embed.set_footer(text=f"Updated by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ── /cleartier ────────────────────────────────────────────────────────────────
@tree.command(name="cleartier", description="Remove a player's tier for a specific mode (keeps them listed)")
@app_commands.describe(name="Player's Minecraft username", mode="Mode to clear the tier for")
@app_commands.choices(mode=mode_choices())
@is_admin()
async def cleartier(interaction: discord.Interaction, name: str, mode: app_commands.Choice[str]):
    data = load_data()
    key = name.lower()
    if key not in data["players"]:
        await interaction.response.send_message(f"❌ **{name}** not found.", ephemeral=True)
        return
    data["players"][key]["tiers"].pop(mode.value, None)
    save_data(data)
    await interaction.response.send_message(
        f"🧹 Cleared **{mode.name.upper()}** tier for **{data['players'][key]['name']}**."
    )

# ── /setregion ────────────────────────────────────────────────────────────────
@tree.command(name="setregion", description="Update a player's region")
@app_commands.describe(name="Player's Minecraft username", region="New region")
@app_commands.choices(region=region_choices())
@is_admin()
async def setregion(interaction: discord.Interaction, name: str, region: app_commands.Choice[str]):
    data = load_data()
    key = name.lower()
    if key not in data["players"]:
        await interaction.response.send_message(f"❌ **{name}** not found.", ephemeral=True)
        return
    data["players"][key]["region"] = region.value
    save_data(data)
    await interaction.response.send_message(
        f"🌍 Updated **{data['players'][key]['name']}**'s region to **{region.value}**."
    )

# ── /player ───────────────────────────────────────────────────────────────────
@tree.command(name="player", description="Look up a player's profile")
@app_commands.describe(name="Player's Minecraft username")
async def player(interaction: discord.Interaction, name: str):
    data = load_data()
    key = name.lower()
    if key not in data["players"]:
        await interaction.response.send_message(f"❌ **{name}** not found in OF Tiers.", ephemeral=True)
        return
    p = data["players"][key]
    overall = p["tiers"].get("overall", "*(unranked)*")
    color = TIER_COLORS.get(p["tiers"].get("overall"), TIER_COLORS[None])

    embed = discord.Embed(title=f"👤 {p['name']}", color=color)
    embed.add_field(name="Region", value=p["region"], inline=True)
    embed.add_field(name="Overall", value=overall, inline=True)

    mode_tiers = {k: v for k, v in p["tiers"].items() if k != "overall"}
    if mode_tiers:
        embed.add_field(
            name="Mode Tiers",
            value="\n".join(f"**{k.upper()}**: {v}" for k, v in mode_tiers.items()),
            inline=False
        )
    await interaction.response.send_message(embed=embed)

# ── /listplayers ──────────────────────────────────────────────────────────────
@tree.command(name="listplayers", description="List all players in OF Tiers")
@app_commands.describe(mode="Filter by mode (default: overall)")
@app_commands.choices(mode=mode_choices())
async def listplayers(interaction: discord.Interaction, mode: app_commands.Choice[str] = None):
    data = load_data()
    players = list(data["players"].values())
    if not players:
        await interaction.response.send_message("No players added yet.", ephemeral=True)
        return

    mode_key = mode.value if mode else "overall"

    ranked = [p for p in players if p["tiers"].get(mode_key)]
    unranked = [p for p in players if not p["tiers"].get(mode_key)]

    ranked.sort(key=lambda p: TIERS.index(p["tiers"][mode_key]))

    lines = []
    for i, p in enumerate(ranked, 1):
        t = p["tiers"][mode_key]
        lines.append(f"`{i:>3}.` **{p['name']}** — {t} [{p['region']}]")
    for p in unranked:
        lines.append(f"`  -` **{p['name']}** — *(unranked)* [{p['region']}]")

    mode_label = (mode.name.upper() if mode else "Overall")
    embed = discord.Embed(
        title=f"📋 OF Tiers — {mode_label} ({len(players)} players)",
        description="\n".join(lines) if lines else "No players yet.",
        color=0x4ade80
    )
    embed.set_footer(text=f"{len(ranked)} ranked · {len(unranked)} unranked")
    await interaction.response.send_message(embed=embed)

# ── /export ───────────────────────────────────────────────────────────────────
@tree.command(name="export", description="Export all player data as a JSON file (for the website)")
@is_admin()
async def export(interaction: discord.Interaction):
    data = load_data()
    players = list(data["players"].values())

    # Build website-ready format
    website_data = []
    for p in players:
        website_data.append({
            "name": p["name"],
            "region": p["region"],
            "tiers": p.get("tiers", {}),
        })

    json_bytes = json.dumps({"players": website_data}, indent=2).encode()
    file = discord.File(io.BytesIO(json_bytes), filename="oftiers_players.json")

    await interaction.response.send_message(
        content=f"📦 Exported **{len(players)}** players. Drop `oftiers_players.json` into your website folder.",
        file=file
    )

# ── /bulkadd ──────────────────────────────────────────────────────────────────
@tree.command(name="bulkadd", description="Add multiple players at once (one per line: name,region,tier)")
@app_commands.describe(
    players_list='One player per line — format: "name,region,tier" OR just "name,region" for unranked'
)
@is_admin()
async def bulkadd(interaction: discord.Interaction, players_list: str):
    data = load_data()
    added, skipped, errors = [], [], []

    for line in players_list.strip().splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) < 2:
            errors.append(f"`{line}` — needs at least name and region")
            continue
        name, region = parts[0], parts[1].upper()
        tier = parts[2].upper() if len(parts) >= 3 else None

        if region not in REGIONS:
            errors.append(f"`{name}` — unknown region `{region}`")
            continue
        if tier and tier not in TIERS:
            errors.append(f"`{name}` — unknown tier `{tier}`")
            continue

        key = name.lower()
        if key in data["players"]:
            skipped.append(name)
            continue

        data["players"][key] = {
            "name": name,
            "region": region,
            "tiers": {"overall": tier} if tier else {},
            "added": datetime.utcnow().isoformat(),
        }
        added.append(name)

    save_data(data)

    lines = []
    if added:    lines.append(f"✅ Added ({len(added)}): " + ", ".join(f"**{n}**" for n in added))
    if skipped:  lines.append(f"⚠️ Already existed ({len(skipped)}): " + ", ".join(skipped))
    if errors:   lines.append(f"❌ Errors ({len(errors)}):\n" + "\n".join(errors))

    embed = discord.Embed(title="📥 Bulk Add Results", description="\n\n".join(lines) or "Nothing processed.", color=0x4ade80)
    await interaction.response.send_message(embed=embed)

# ── /help ─────────────────────────────────────────────────────────────────────
@tree.command(name="help", description="Show all OF Tiers bot commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="⚔️ OF Tiers Bot — Commands", color=0x4ade80)
    embed.add_field(name="🔒 Admin Only", value="All commands below require **Administrator** permission.", inline=False)
    cmds = [
        ("/addplayer",    "Add a player (tier is optional)"),
        ("/bulkadd",      "Add many players at once via text"),
        ("/removeplayer", "Remove a player entirely"),
        ("/settier",      "Set a player's tier for any mode"),
        ("/cleartier",    "Remove a tier for a mode (keeps player)"),
        ("/setregion",    "Update a player's region"),
        ("/export",       "Export all data as JSON for the website"),
        ("/listplayers",  "List all players (anyone can use)"),
        ("/player",       "Look up a single player (anyone can use)"),
    ]
    embed.add_field(
        name="Commands",
        value="\n".join(f"`{c}` — {d}" for c, d in cmds),
        inline=False
    )
    embed.add_field(
        name="Tiers",
        value=" › ".join(TIERS),
        inline=False
    )
    embed.set_footer(text="OF Tiers — Only Finest")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ── RUN ───────────────────────────────────────────────────────────────────────
bot.run(TOKEN)
