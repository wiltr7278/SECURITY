# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘
# PART 1 — CORE + DATABASE
# ============================================================

import os
import re
import io
import sqlite3
import asyncio
import random
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from discord import app_commands

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    Image = None


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN environment variable is missing!"
    )

PREFIX = "!"

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# ============================================================
# DATABASE
# ============================================================

os.makedirs("data", exist_ok=True)

DB = sqlite3.connect(
    "data/security.db",
    check_same_thread=False
)

DB.row_factory = sqlite3.Row


def db_execute(
    query,
    params=(),
    fetchone=False,
    fetchall=False
):
    cursor = DB.cursor()
    cursor.execute(query, params)
    DB.commit()

    if fetchone:
        return cursor.fetchone()

    if fetchall:
        return cursor.fetchall()

    return None


def init_database():

    db_execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,

            welcome_enabled INTEGER DEFAULT 0,
            welcome_channel_id INTEGER,
            welcome_message TEXT DEFAULT 'Welcome {user} to {server}!',
            welcome_image TEXT,
            welcome_style TEXT DEFAULT 'default',
            welcome_role_id INTEGER,

            bye_enabled INTEGER DEFAULT 0,
            bye_channel_id INTEGER,
            bye_message TEXT DEFAULT 'Goodbye {user}! We will miss you.',
            bye_image TEXT,
            bye_style TEXT DEFAULT 'default',

            verify_enabled INTEGER DEFAULT 0,
            verify_channel_id INTEGER,
            verify_role_id INTEGER,
            verify_message TEXT DEFAULT 'Verify yourself to access the server.',

            ticket_category_id INTEGER,
            ticket_panel_channel_id INTEGER,

            level_enabled INTEGER DEFAULT 1,
            level_channel_id INTEGER,

            social_enabled INTEGER DEFAULT 0,
            social_channel_id INTEGER,
            social_youtube INTEGER DEFAULT 0,
            social_twitch INTEGER DEFAULT 0,
            social_tiktok INTEGER DEFAULT 0,
            social_live INTEGER DEFAULT 1,
            social_post INTEGER DEFAULT 1,

            showcase_enabled INTEGER DEFAULT 0,
            showcase_channel_id INTEGER,
            showcase_review_channel_id INTEGER,
            showcase_message TEXT DEFAULT 'New TikTok submission from {user}!',

            mod_enabled INTEGER DEFAULT 0,
            mute_role_id INTEGER,
            ban_announce_channel_id INTEGER
        )
    """)

    db_execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            guild_id INTEGER,
            user_id INTEGER,
            amount INTEGER DEFAULT 0,
            PRIMARY KEY(guild_id, user_id)
        )
    """)

    db_execute("""
        CREATE TABLE IF NOT EXISTS mod_exempt_roles (
            guild_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY(guild_id, role_id)
        )
    """)

    db_execute("""
        CREATE TABLE IF NOT EXISTS levels (
            guild_id INTEGER,
            user_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            PRIMARY KEY(guild_id, user_id)
        )
    """)

    db_execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            channel_id INTEGER,
            remind_at TEXT,
            message TEXT
        )
    """)

    db_execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            guild_id INTEGER,
            user_id INTEGER,
            channel_id INTEGER,
            PRIMARY KEY(guild_id, user_id)
        )
    """)

    db_execute("""
        CREATE TABLE IF NOT EXISTS stats_channels (
            guild_id INTEGER,
            stat_key TEXT,
            channel_id INTEGER,
            channel_type TEXT,
            message_id INTEGER,
            PRIMARY KEY(guild_id, stat_key)
        )
    """)

    db_execute("""
        CREATE TABLE IF NOT EXISTS showcase_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            url TEXT,
            review_channel_id INTEGER,
            review_message_id INTEGER,
            status TEXT DEFAULT 'pending'
        )
    """)


init_database()


# ============================================================
# DATABASE HELPERS
# ============================================================

def ensure_guild(guild_id):

    db_execute(
        """
        INSERT OR IGNORE INTO guild_settings(guild_id)
        VALUES(?)
        """,
        (guild_id,)
    )


def get_settings(guild_id):

    ensure_guild(guild_id)

    return db_execute(
        """
        SELECT *
        FROM guild_settings
        WHERE guild_id = ?
        """,
        (guild_id,),
        fetchone=True
    )


def update_setting(
    guild_id,
    column,
    value
):

    allowed = {
        "welcome_enabled",
        "welcome_channel_id",
        "welcome_message",
        "welcome_image",
        "welcome_style",
        "welcome_role_id",

        "bye_enabled",
        "bye_channel_id",
        "bye_message",
        "bye_image",
        "bye_style",

        "verify_enabled",
        "verify_channel_id",
        "verify_role_id",
        "verify_message",

        "ticket_category_id",
        "ticket_panel_channel_id",

        "level_enabled",
        "level_channel_id",

        "social_enabled",
        "social_channel_id",
        "social_youtube",
        "social_twitch",
        "social_tiktok",
        "social_live",
        "social_post",

        "showcase_enabled",
        "showcase_channel_id",
        "showcase_review_channel_id",
        "showcase_message",

        "mod_enabled",
        "mute_role_id",
        "ban_announce_channel_id"
    }

    if column not in allowed:
        raise ValueError(
            f"Invalid database setting: {column}"
        )

    ensure_guild(guild_id)

    db_execute(
        f"""
        UPDATE guild_settings
        SET {column} = ?
        WHERE guild_id = ?
        """,
        (value, guild_id)
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def is_admin(interaction):

    return interaction.user.guild_permissions.administrator


async def require_admin(interaction):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ You need Administrator permission.",
            ephemeral=True
        )

        return False

    return True


def make_embed(
    title,
    description=None
):

    e = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.dark_grey(),
        timestamp=datetime.now(timezone.utc)
    )

    e.set_footer(
        text="🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘"
    )

    return e


def replace_placeholders(
    text,
    member
):

    return (
        text
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace(
            "{membercount}",
            str(member.guild.member_count)
        )
    )


async def get_channel(
    guild,
    channel_id
):

    if not channel_id:
        return None

    channel = guild.get_channel(
        int(channel_id)
    )

    if channel:
        return channel

    try:
        return await guild.fetch_channel(
            int(channel_id)
        )
    except Exception:
        return None


# ============================================================
# END OF PART 1
# ============================================================
# ============================================================
# 👋 PART 2 — WELCOME + BYE
# ============================================================


# ============================================================
# WELCOME SETUP
# ============================================================

@bot.tree.command(
    name="welcome-setup",
    description="Configure the Welcome system"
)
@app_commands.describe(
    channel="Welcome channel",
    message="Welcome message",
    image="Welcome image URL",
    style="Welcome style",
    role="Automatic role",
    enabled="Turn Welcome on or off"
)
@app_commands.choices(
    style=[
        app_commands.Choice(name="Default", value="default"),
        app_commands.Choice(name="Avatar", value="avatar"),
        app_commands.Choice(name="Custom Image", value="custom_image")
    ],
    enabled=[
        app_commands.Choice(
            name="On",
            value="on"
        ),
        app_commands.Choice(
            name="Off",
            value="off"
        )
    ]
)
async def welcome_setup(
    interaction,
    channel: discord.TextChannel,
    message: str = None,
    image: str = None,
    style: str = "default",
    role: discord.Role = None,
    enabled: app_commands.Choice[str] = None
):

    if not await require_admin(interaction):
        return

    gid = interaction.guild.id

    update_setting(
        gid,
        "welcome_channel_id",
        channel.id
    )

    if message is not None:
        update_setting(
            gid,
            "welcome_message",
            message
        )

    if image is not None:
        update_setting(
            gid,
            "welcome_image",
            image
        )

    update_setting(
        gid,
        "welcome_style",
        style
    )

    if role is not None:
        update_setting(
            gid,
            "welcome_role_id",
            role.id
        )

    if enabled is not None:
        update_setting(
            gid,
            "welcome_enabled",
            1 if enabled.value == "on" else 0
        )

    style_label = {
        "default": "Default",
        "avatar": "Avatar",
        "custom_image": "Custom Image"
    }.get(style, "Default")

    await interaction.response.send_message(
        "✅ **Welcome setup saved.**\n\n"
        f"📢 Channel: {channel.mention}\n"
        f"🎨 Style: **{style_label}**\n"
        f"🎭 Auto-role: "
        f"{role.mention if role else 'Not changed'}\n"
        f"🖼️ Custom image: "
        f"{'Saved' if image else 'Not set'}\n"
        f"🟢 Status: "
        f"{'ON' if not enabled or enabled.value == 'on' else 'OFF'}\n\n"
        "📝 **Welcome placeholders:**\n"
        "`{user}` — mentions the new member\n"
        "`{username}` — member username\n"
        "`{server}` — server name\n"
        "`{membercount}` — current member count",
        ephemeral=True
    )


@bot.tree.command(
    name="welcome",
    description="View Welcome settings"
)
async def welcome(interaction):

    s = get_settings(
        interaction.guild.id
    )

    channel = (
        interaction.guild.get_channel(
            s["welcome_channel_id"]
        )
        if s["welcome_channel_id"]
        else None
    )

    role = (
        interaction.guild.get_role(
            s["welcome_role_id"]
        )
        if s["welcome_role_id"]
        else None
    )

    await interaction.response.send_message(
        embed=make_embed(
            "👋 Welcome System",
            f"**Status:** "
            f"{'🟢 ON' if s['welcome_enabled'] else '🔴 OFF'}\n"
            f"**Channel:** "
            f"{channel.mention if channel else 'Not set'}\n"
            f"**Auto-role:** "
            f"{role.mention if role else 'Not set'}\n"
            f"**Style:** `{s['welcome_style']}`\n"
            f"**Image:** "
            f"{'✅ Saved' if s['welcome_image'] else '❌ None'}\n\n"
            f"**Message:**\n{s['welcome_message']}"
        ),
        ephemeral=True
    )


@bot.tree.command(
    name="testwelcome",
    description="Test the Welcome system"
)
async def testwelcome(interaction):

    await send_welcome(
        interaction.guild,
        interaction.user
    )

    await interaction.response.send_message(
        "✅ Welcome test sent.",
        ephemeral=True
    )


async def send_welcome(
    guild,
    member
):

    s = get_settings(guild.id)

    if not s["welcome_enabled"]:
        return

    channel = await get_channel(
        guild,
        s["welcome_channel_id"]
    )

    if not channel:
        return

    text = replace_placeholders(
        s["welcome_message"],
        member
    )

    e = make_embed(
        "👋 Welcome!",
        text
    )

    style = (s["welcome_style"] or "default").lower()

    # Welcome style controls which visual is shown.
    if style == "avatar":
        avatar = member.display_avatar.url
        e.set_thumbnail(url=avatar)
    elif style == "custom_image":
        if s["welcome_image"]:
            e.set_image(url=s["welcome_image"])
    elif style == "default" and s["welcome_image"]:
        # Keep compatibility with older settings that already saved an image.
        e.set_image(url=s["welcome_image"])

    await channel.send(
        content=member.mention,
        embed=e
    )

    if s["welcome_role_id"]:

        role = guild.get_role(
            s["welcome_role_id"]
        )

        if role:

            try:
                await member.add_roles(
                    role,
                    reason="SECURITY automatic welcome role"
                )
            except Exception:
                pass


# ============================================================
# BYE SETUP
# ============================================================

@bot.tree.command(
    name="bye-setup",
    description="Configure the Bye system"
)
@app_commands.describe(
    channel="Bye channel",
    message="Goodbye message",
    image="Goodbye image URL",
    style="Bye style",
    enabled="Turn Bye on or off"
)
@app_commands.choices(
    enabled=[
        app_commands.Choice(
            name="On",
            value="on"
        ),
        app_commands.Choice(
            name="Off",
            value="off"
        )
    ]
)
async def bye_setup(
    interaction,
    channel: discord.TextChannel,
    message: str = None,
    image: str = None,
    style: str = "default",
    enabled: app_commands.Choice[str] = None
):

    if not await require_admin(interaction):
        return

    gid = interaction.guild.id

    update_setting(
        gid,
        "bye_channel_id",
        channel.id
    )

    if message is not None:
        update_setting(
            gid,
            "bye_message",
            message
        )

    if image is not None:
        update_setting(
            gid,
            "bye_image",
            image
        )

    update_setting(
        gid,
        "bye_style",
        style
    )

    if enabled is not None:
        update_setting(
            gid,
            "bye_enabled",
            1 if enabled.value == "on" else 0
        )

    await interaction.response.send_message(
        "✅ **Bye setup saved permanently.**",
        ephemeral=True
    )


@bot.tree.command(
    name="bye",
    description="View Bye settings"
)
async def bye(interaction):

    s = get_settings(
        interaction.guild.id
    )

    channel = (
        interaction.guild.get_channel(
            s["bye_channel_id"]
        )
        if s["bye_channel_id"]
        else None
    )

    await interaction.response.send_message(
        embed=make_embed(
            "👋 Bye System",
            f"**Status:** "
            f"{'🟢 ON' if s['bye_enabled'] else '🔴 OFF'}\n"
            f"**Channel:** "
            f"{channel.mention if channel else 'Not set'}\n"
            f"**Style:** `{s['bye_style']}`\n"
            f"**Image:** "
            f"{'✅ Saved' if s['bye_image'] else '❌ None'}\n\n"
            f"**Message:**\n{s['bye_message']}"
        ),
        ephemeral=True
    )


@bot.tree.command(
    name="testbye",
    description="Test the Bye system"
)
async def testbye(interaction):

    await send_bye(
        interaction.guild,
        interaction.user
    )

    await interaction.response.send_message(
        "✅ Bye test sent.",
        ephemeral=True
    )


async def send_bye(
    guild,
    member
):

    s = get_settings(guild.id)

    if not s["bye_enabled"]:
        return

    channel = await get_channel(
        guild,
        s["bye_channel_id"]
    )

    if not channel:
        return

    text = replace_placeholders(
        s["bye_message"],
        member
    )

    e = make_embed(
        "👋 Goodbye!",
        text
    )

    if s["bye_image"]:
        e.set_image(
            url=s["bye_image"]
        )

    await channel.send(
        embed=e
    )


@bot.event
async def on_member_join(member):

    await send_welcome(
        member.guild,
        member
    )


@bot.event
async def on_member_remove(member):

    await send_bye(
        member.guild,
        member
    )


# ============================================================
# END OF PART 2
# ============================================================
# ============================================================
# ✅ PART 3 — VERIFICATION
# ============================================================


class VerifyPanel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="security_verify_button"
    )
    async def verify_button(
        self,
        interaction,
        button
    ):

        s = get_settings(
            interaction.guild.id
        )

        role_id = s["verify_role_id"]

        if not role_id:

            await interaction.response.send_message(
                "❌ Verification role is not configured.",
                ephemeral=True
            )

            return

        role = interaction.guild.get_role(
            role_id
        )

        if not role:

            await interaction.response.send_message(
                "❌ Verification role no longer exists.",
                ephemeral=True
            )

            return

        if role in interaction.user.roles:

            await interaction.response.send_message(
                "✅ You are already verified.",
                ephemeral=True
            )

            return

        try:

            await interaction.user.add_roles(
                role,
                reason="SECURITY verification"
            )

            await interaction.response.send_message(
                "✅ You have been verified!",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot give that role. "
                "Move my bot role above the verification role.",
                ephemeral=True
            )


@bot.tree.command(
    name="verifysetup",
    description="Configure verification"
)
@app_commands.describe(
    channel="Verification channel",
    role="Verification role",
    message="Verification message"
)
async def verifysetup(
    interaction,
    channel: discord.TextChannel,
    role: discord.Role,
    message: str = "Click the button below to verify."
):

    if not await require_admin(interaction):
        return

    gid = interaction.guild.id

    update_setting(
        gid,
        "verify_channel_id",
        channel.id
    )

    update_setting(
        gid,
        "verify_role_id",
        role.id
    )

    update_setting(
        gid,
        "verify_message",
        message
    )

    update_setting(
        gid,
        "verify_enabled",
        1
    )

    await interaction.response.send_message(
        "✅ Verification setup saved.",
        ephemeral=True
    )


@bot.tree.command(
    name="verifymessage",
    description="Change verification message"
)
@app_commands.describe(
    message="New verification message"
)
async def verifymessage(
    interaction,
    message: str
):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "verify_message",
        message
    )

    await interaction.response.send_message(
        "✅ Verification message updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="verifyrole",
    description="Change verification role"
)
@app_commands.describe(
    role="New verification role"
)
async def verifyrole(
    interaction,
    role: discord.Role
):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "verify_role_id",
        role.id
    )

    await interaction.response.send_message(
        f"✅ Verification role set to {role.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify-panel",
    description="Send verification panel"
)
async def verify_panel(interaction):

    if not await require_admin(interaction):
        return

    s = get_settings(
        interaction.guild.id
    )

    if not s["verify_role_id"]:

        await interaction.response.send_message(
            "❌ Run `/verifysetup` first.",
            ephemeral=True
        )

        return

    e = make_embed(
        "🔐 Verification",
        s["verify_message"]
    )

    await interaction.channel.send(
        embed=e,
        view=VerifyPanel()
    )

    await interaction.response.send_message(
        "✅ Verification panel sent.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify",
    description="Verify yourself"
)
async def verify(interaction):

    s = get_settings(
        interaction.guild.id
    )

    role = interaction.guild.get_role(
        s["verify_role_id"]
    ) if s["verify_role_id"] else None

    if not role:

        await interaction.response.send_message(
            "❌ Verification is not configured.",
            ephemeral=True
        )

        return

    try:

        await interaction.user.add_roles(
            role,
            reason="SECURITY verification"
        )

        await interaction.response.send_message(
            "✅ You are verified!",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot assign the verification role.",
            ephemeral=True
        )


# ============================================================
# END OF PART 3
# ============================================================
# ============================================================
# 🎫 PART 4 — TICKETS + CLEANER
# ============================================================


class TicketPanel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="security_ticket_create"
    )
    async def create_ticket(
        self,
        interaction,
        button
    ):

        guild = interaction.guild
        user = interaction.user

        existing = db_execute(
            """
            SELECT channel_id
            FROM tickets
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (guild.id, user.id),
            fetchone=True
        )

        if existing:

            old_channel = guild.get_channel(
                existing["channel_id"]
            )

            if old_channel:

                await interaction.response.send_message(
                    f"❌ You already have a ticket: "
                    f"{old_channel.mention}",
                    ephemeral=True
                )

                return

        s = get_settings(
            guild.id
        )

        category = None

        if s["ticket_category_id"]:

            category = guild.get_channel(
                s["ticket_category_id"]
            )

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites,
            reason="SECURITY ticket"
        )

        db_execute(
            """
            INSERT OR REPLACE INTO tickets
            (guild_id, user_id, channel_id)
            VALUES (?, ?, ?)
            """,
            (
                guild.id,
                user.id,
                channel.id
            )
        )

        await channel.send(
            content=user.mention,
            embed=make_embed(
                "🎫 Support Ticket",
                "Please explain your issue here.\n\n"
                "Use `/ticket-close` when finished."
            )
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )


@bot.tree.command(
    name="ticket-setup",
    description="Configure tickets"
)
@app_commands.describe(
    category="Private ticket category",
    panel_channel="Ticket panel channel"
)
async def ticket_setup(
    interaction,
    category: discord.CategoryChannel,
    panel_channel: discord.TextChannel
):

    if not await require_admin(interaction):
        return

    gid = interaction.guild.id

    update_setting(
        gid,
        "ticket_category_id",
        category.id
    )

    update_setting(
        gid,
        "ticket_panel_channel_id",
        panel_channel.id
    )

    await interaction.response.send_message(
        "✅ Ticket settings saved.",
        ephemeral=True
    )


@bot.tree.command(
    name="ticket-panel",
    description="Send ticket panel"
)
async def ticket_panel(interaction):

    if not await require_admin(interaction):
        return

    await interaction.channel.send(
        embed=make_embed(
            "🎫 Support Tickets",
            "Need help?\n\n"
            "Click **Create Ticket** to open a private ticket."
        ),
        view=TicketPanel()
    )

    await interaction.response.send_message(
        "✅ Ticket panel sent.",
        ephemeral=True
    )


@bot.tree.command(
    name="ticket",
    description="Create a ticket"
)
async def ticket(interaction):

    await interaction.response.defer(
        ephemeral=True
    )

    guild = interaction.guild
    user = interaction.user

    existing = db_execute(
        """
        SELECT channel_id
        FROM tickets
        WHERE guild_id = ?
        AND user_id = ?
        """,
        (guild.id, user.id),
        fetchone=True
    )

    if existing:

        channel = guild.get_channel(
            existing["channel_id"]
        )

        if channel:

            await interaction.followup.send(
                f"❌ You already have {channel.mention}.",
                ephemeral=True
            )

            return

    s = get_settings(guild.id)

    category = (
        guild.get_channel(
            s["ticket_category_id"]
        )
        if s["ticket_category_id"]
        else None
    )

    overwrites = {
        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
    }

    channel = await guild.create_text_channel(
        f"ticket-{user.name}",
        category=category,
        overwrites=overwrites
    )

    db_execute(
        """
        INSERT OR REPLACE INTO tickets
        VALUES (?, ?, ?)
        """,
        (
            guild.id,
            user.id,
            channel.id
        )
    )

    await channel.send(
        content=user.mention,
        embed=make_embed(
            "🎫 Ticket Opened",
            "Please describe your problem.\n"
            "Staff will help you soon."
        )
    )

    await interaction.followup.send(
        f"✅ Ticket created: {channel.mention}",
        ephemeral=True
    )


@bot.tree.command(
    name="ticket-close",
    description="Close the current ticket"
)
async def ticket_close(interaction):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):

        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )

        return

    row = db_execute(
        """
        SELECT user_id
        FROM tickets
        WHERE channel_id = ?
        """,
        (interaction.channel.id,),
        fetchone=True
    )

    if not row:

        await interaction.response.send_message(
            "❌ This channel is not a SECURITY ticket.",
            ephemeral=True
        )

        return

    if (
        interaction.user.id != row["user_id"]
        and not interaction.user.guild_permissions.manage_channels
    ):

        await interaction.response.send_message(
            "❌ You cannot close this ticket.",
            ephemeral=True
        )

        return

    owner = interaction.guild.get_member(
        row["user_id"]
    )

    if owner:

        await interaction.channel.set_permissions(
            owner,
            view_channel=False
        )

    await interaction.channel.edit(
        name=f"closed-{interaction.channel.name}"
    )

    db_execute(
        """
        DELETE FROM tickets
        WHERE channel_id = ?
        """,
        (interaction.channel.id,)
    )

    await interaction.response.send_message(
        "🔒 Ticket closed."
    )


@bot.tree.command(
    name="ticket-add",
    description="Add a member to a ticket"
)
@app_commands.describe(
    member="Member to add"
)
async def ticket_add(
    interaction,
    member: discord.Member
):

    if not interaction.user.guild_permissions.manage_channels:

        await interaction.response.send_message(
            "❌ Manage Channels permission required.",
            ephemeral=True
        )

        return

    await interaction.channel.set_permissions(
        member,
        view_channel=True,
        send_messages=True,
        read_message_history=True
    )

    await interaction.response.send_message(
        f"✅ Added {member.mention}."
    )


@bot.tree.command(
    name="ticket-remove",
    description="Remove a member from a ticket"
)
@app_commands.describe(
    member="Member to remove"
)
async def ticket_remove(
    interaction,
    member: discord.Member
):

    if not interaction.user.guild_permissions.manage_channels:

        await interaction.response.send_message(
            "❌ Manage Channels permission required.",
            ephemeral=True
        )

        return

    await interaction.channel.set_permissions(
        member,
        overwrite=None
    )

    await interaction.response.send_message(
        f"✅ Removed {member.mention}."
    )


# ============================================================
# CLEANER
# ============================================================

@bot.tree.command(
    name="clear",
    description="Delete messages"
)
@app_commands.describe(
    amount="Number of messages to delete"
)
async def clear(
    interaction,
    amount: app_commands.Range[int, 1, 100]
):

    if not interaction.user.guild_permissions.manage_messages:

        await interaction.response.send_message(
            "❌ Manage Messages permission required.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await interaction.channel.purge(
        limit=amount
    )

    await interaction.followup.send(
        f"🧹 Deleted **{len(deleted)}** messages.",
        ephemeral=True
    )


# ============================================================
# END OF PART 4
# ============================================================
# ============================================================
# 📊 PART 5 — SERVER STATS
# ============================================================


STAT_NAMES = {
    "members": "👥 Members",
    "bots": "🤖 Bots",
    "online": "🟢 Online",
    "server": "📊 Server"
}


class StatsChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(self, stat_key):

        self.stat_key = stat_key

        super().__init__(
            placeholder=f"Choose {STAT_NAMES[stat_key]} channel",
            min_values=1,
            max_values=1,
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.voice
            ]
        )

    async def callback(self, interaction):

        channel = self.values[0]

        channel_type = (
            "voice"
            if channel.type == discord.ChannelType.voice
            else "text"
        )

        db_execute(
            """
            INSERT OR REPLACE INTO stats_channels
            (
                guild_id,
                stat_key,
                channel_id,
                channel_type,
                message_id
            )
            VALUES (?, ?, ?, ?, COALESCE(
                (
                    SELECT message_id
                    FROM stats_channels
                    WHERE guild_id = ?
                    AND stat_key = ?
                ),
                NULL
            ))
            """,
            (
                interaction.guild.id,
                self.stat_key,
                channel.id,
                channel_type,
                interaction.guild.id,
                self.stat_key
            )
        )

        await interaction.response.send_message(
            f"✅ {STAT_NAMES[self.stat_key]} "
            f"set to {channel.mention}.",
            ephemeral=True
        )


class StatsSetupView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=300
        )

        self.add_item(
            StatsChannelSelect("members")
        )

        self.add_item(
            StatsChannelSelect("bots")
        )

        self.add_item(
            StatsChannelSelect("online")
        )

        self.add_item(
            StatsChannelSelect("server")
        )


@bot.tree.command(
    name="stats-setup",
    description="Configure member/stat channels"
)
async def stats_setup(interaction):

    if not await require_admin(interaction):
        return

    await interaction.response.send_message(
        embed=make_embed(
            "📊 Stats Setup",
            "Choose a **text channel or voice channel** "
            "for each statistic.\n\n"
            "👥 Members\n"
            "🤖 Bots\n"
            "🟢 Online\n"
            "📊 Server"
        ),
        view=StatsSetupView(),
        ephemeral=True
    )


async def update_stat_channels():

    for guild in bot.guilds:

        rows = db_execute(
            """
            SELECT *
            FROM stats_channels
            WHERE guild_id = ?
            """,
            (guild.id,),
            fetchall=True
        )

        members = guild.member_count

        bots = sum(
            1
            for member in guild.members
            if member.bot
        )

        online = sum(
            1
            for member in guild.members
            if member.status != discord.Status.offline
            and not member.bot
        )

        server = (
            f"{len(guild.channels)} channels • "
            f"{len(guild.roles)} roles"
        )

        values = {
            "members": f"👥 Members: {members}",
            "bots": f"🤖 Bots: {bots}",
            "online": f"🟢 Online: {online}",
            "server": f"📊 {server}"
        }

        for row in rows:

            channel = guild.get_channel(
                row["channel_id"]
            )

            if not channel:
                continue

            value = values[row["stat_key"]]

            if row["channel_type"] == "voice":

                try:

                    if channel.name != value:
                        await channel.edit(
                            name=value
                        )

                except Exception:
                    pass

            else:

                try:

                    message = None

                    if row["message_id"]:

                        try:
                            message = await channel.fetch_message(
                                row["message_id"]
                            )
                        except Exception:
                            message = None

                    if message:

                        if message.content != value:
                            await message.edit(
                                content=value
                            )

                    else:

                        message = await channel.send(
                            value
                        )

                        db_execute(
                            """
                            UPDATE stats_channels
                            SET message_id = ?
                            WHERE guild_id = ?
                            AND stat_key = ?
                            """,
                            (
                                message.id,
                                guild.id,
                                row["stat_key"]
                            )
                        )

                except Exception:
                    pass


@bot.tree.command(
    name="stats",
    description="View server statistics"
)
async def stats(interaction):

    guild = interaction.guild

    members = guild.member_count

    bots = sum(
        1
        for member in guild.members
        if member.bot
    )

    online = sum(
        1
        for member in guild.members
        if member.status != discord.Status.offline
    )

    await interaction.response.send_message(
        embed=make_embed(
            "📊 Server Statistics",
            f"👥 **Members:** {members}\n"
            f"🤖 **Bots:** {bots}\n"
            f"🟢 **Online:** {online}\n"
            f"📁 **Channels:** {len(guild.channels)}\n"
            f"🎭 **Roles:** {len(guild.roles)}"
        )
    )


# ============================================================
# END OF PART 5
# ============================================================
# ============================================================
# ⭐ PART 6 — LEVELS
# ============================================================


xp_cooldowns = {}


def xp_required(level):

    return 100 + (level * 50)


def get_level_data(
    guild_id,
    user_id
):

    row = db_execute(
        """
        SELECT *
        FROM levels
        WHERE guild_id = ?
        AND user_id = ?
        """,
        (guild_id, user_id),
        fetchone=True
    )

    if not row:

        db_execute(
            """
            INSERT INTO levels
            VALUES (?, ?, 0, 0)
            """,
            (
                guild_id,
                user_id
            )
        )

        return {
            "xp": 0,
            "level": 0
        }

    return {
        "xp": row["xp"],
        "level": row["level"]
    }


def get_rank(
    guild_id,
    user_id
):

    rows = db_execute(
        """
        SELECT user_id
        FROM levels
        WHERE guild_id = ?
        ORDER BY xp DESC
        """,
        (guild_id,),
        fetchall=True
    )

    for index, row in enumerate(rows, start=1):

        if row["user_id"] == user_id:
            return index

    return 1


async def add_xp(
    message
):

    if message.author.bot:
        return

    guild = message.guild

    if not guild:
        return

    s = get_settings(guild.id)

    if not s["level_enabled"]:
        return

    key = (
        guild.id,
        message.author.id
    )

    now = datetime.now(
        timezone.utc
    ).timestamp()

    last = xp_cooldowns.get(key, 0)

    if now - last < 45:
        return

    xp_cooldowns[key] = now

    amount = random.randint(
        15,
        25
    )

    data = get_level_data(
        guild.id,
        message.author.id
    )

    old_level = data["level"]

    new_xp = data["xp"] + amount
    new_level = old_level

    while new_xp >= xp_required(new_level):

        new_xp -= xp_required(new_level)

        new_level += 1

    db_execute(
        """
        INSERT OR REPLACE INTO levels
        VALUES (?, ?, ?, ?)
        """,
        (
            guild.id,
            message.author.id,
            new_xp,
            new_level
        )
    )

    if new_level > old_level:

        await level_up(
            message,
            new_level,
            new_xp
        )


async def level_up(
    message,
    level,
    xp
):

    s = get_settings(
        message.guild.id
    )

    channel = await get_channel(
        message.guild,
        s["level_channel_id"]
    )

    if not channel:
        channel = message.channel

    rank = get_rank(
        message.guild.id,
        message.author.id
    )

    if Image:

        try:

            image_bytes = await create_level_image(
                message.author,
                level,
                xp,
                rank
            )

            file = discord.File(
                image_bytes,
                filename="level-up.png"
            )

            await channel.send(
                content=message.author.mention,
                embed=make_embed(
                    "⭐ LEVEL UP!",
                    f"Congratulations {message.author.mention}!\n\n"
                    f"**Level:** {level}\n"
                    f"**Rank:** #{rank}"
                ),
                file=file
            )

            return

        except Exception as error:

            print(
                f"Level image error: {error}"
            )

    await channel.send(
        f"⭐ Congratulations {message.author.mention}! "
        f"You reached **Level {level}**!"
    )


async def create_level_image(
    member,
    level,
    xp,
    rank
):

    image = Image.new(
        "RGB",
        (1000, 350),
        (15, 15, 15)
    )

    draw = ImageDraw.Draw(image)

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    bold = None
    normal = None

    for path in font_paths:

        if os.path.exists(path):

            try:

                bold = ImageFont.truetype(
                    path,
                    48
                )

                normal = ImageFont.truetype(
                    path,
                    28
                )

                break

            except Exception:
                pass

    if bold is None:

        bold = ImageFont.load_default()
        normal = ImageFont.load_default()

    try:

        avatar_bytes = await member.display_avatar.read()

        avatar = Image.open(
            io.BytesIO(avatar_bytes)
        ).convert("RGB")

        avatar = ImageOps.fit(
            avatar,
            (220, 220)
        )

        mask = Image.new(
            "L",
            (220, 220),
            0
        )

        mask_draw = ImageDraw.Draw(mask)

        mask_draw.ellipse(
            (0, 0, 220, 220),
            fill=255
        )

        image.paste(
            avatar,
            (60, 65),
            mask
        )

    except Exception:
        pass

    draw.text(
        (330, 75),
        str(member),
        font=bold,
        fill="white"
    )

    draw.text(
        (330, 145),
        f"LEVEL {level}",
        font=normal,
        fill="white"
    )

    draw.text(
        (330, 190),
        f"XP {xp}   •   RANK #{rank}",
        font=normal,
        fill="white"
    )

    draw.rounded_rectangle(
        (330, 245, 900, 275),
        radius=15,
        outline="white",
        width=2
    )

    required = xp_required(level)

    progress = min(
        xp / required,
        1
    )

    draw.rounded_rectangle(
        (
            335,
            250,
            335 + int(560 * progress),
            270
        ),
        radius=10,
        fill="white"
    )

    output = io.BytesIO()

    image.save(
        output,
        format="PNG"
    )

    output.seek(0)

    return output


@bot.tree.command(
    name="levels-setup",
    description="Configure level-up announcements"
)
@app_commands.describe(
    channel="Level-up announcement channel"
)
async def levels_setup(
    interaction,
    channel: discord.TextChannel
):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "level_channel_id",
        channel.id
    )

    await interaction.response.send_message(
        f"✅ Level-up channel set to {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="levels-on",
    description="Enable levels"
)
async def levels_on(interaction):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "level_enabled",
        1
    )

    await interaction.response.send_message(
        "⭐ Levels are now **ON**.",
        ephemeral=True
    )


@bot.tree.command(
    name="levels-off",
    description="Disable levels"
)
async def levels_off(interaction):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "level_enabled",
        0
    )

    await interaction.response.send_message(
        "⭐ Levels are now **OFF**.",
        ephemeral=True
    )


@bot.tree.command(
    name="rank",
    description="View your rank"
)
@app_commands.describe(
    member="Member to check"
)
async def rank(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    data = get_level_data(
        interaction.guild.id,
        member.id
    )

    position = get_rank(
        interaction.guild.id,
        member.id
    )

    await interaction.response.send_message(
        embed=make_embed(
            f"⭐ {member.display_name}'s Rank",
            f"**Level:** {data['level']}\n"
            f"**XP:** {data['xp']}\n"
            f"**Rank:** #{position}"
        )
    )


@bot.tree.command(
    name="level",
    description="View a member's level"
)
@app_commands.describe(
    member="Member to check"
)
async def level(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    data = get_level_data(
        interaction.guild.id,
        member.id
    )

    await interaction.response.send_message(
        embed=make_embed(
            "⭐ Level",
            f"**Member:** {member.mention}\n"
            f"**Level:** {data['level']}\n"
            f"**XP:** {data['xp']}"
        )
    )


@bot.tree.command(
    name="leaderboard",
    description="View the XP leaderboard"
)
async def leaderboard(interaction):

    rows = db_execute(
        """
        SELECT user_id, xp, level
        FROM levels
        WHERE guild_id = ?
        ORDER BY level DESC, xp DESC
        LIMIT 10
        """,
        (interaction.guild.id,),
        fetchall=True
    )

    lines = []

    for index, row in enumerate(
        rows,
        start=1
    ):

        member = interaction.guild.get_member(
            row["user_id"]
        )

        name = (
            member.display_name
            if member
            else f"User {row['user_id']}"
        )

        lines.append(
            f"**#{index}** {name} — "
            f"Level {row['level']} • {row['xp']} XP"
        )

    if not lines:
        lines.append(
            "No XP data yet."
        )

    await interaction.response.send_message(
        embed=make_embed(
            "🏆 Level Leaderboard",
            "\n".join(lines)
        )
    )


# ============================================================
# END OF PART 6
# ============================================================
# ============================================================
# 🎬 PART 7 — TIKTOK SHOWCASE
# ============================================================


def is_tiktok_url(text):

    return (
        "tiktok.com/" in text.lower()
        or "vt.tiktok.com/" in text.lower()
    )


# ============================================================
# 🎬 TIKTOK SHOWCASE
# ============================================================

class ShowcaseReviewView(
    discord.ui.View
):

    def __init__(
        self,
        review_id
    ):

        super().__init__(
            timeout=None
        )

        self.review_id = review_id

    @discord.ui.button(
        label="Approve",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="security_showcase_approve"
    )
    async def approve(
        self,
        interaction,
        button
    ):

        if not interaction.user.guild_permissions.manage_messages:

            await interaction.response.send_message(
                "❌ Staff permission required.",
                ephemeral=True
            )

            return

        row = db_execute(
            """
            SELECT *
            FROM showcase_reviews
            WHERE id = ?
            """,
            (self.review_id,),
            fetchone=True
        )

        if not row or row["status"] != "pending":

            await interaction.response.send_message(
                "❌ This review is no longer pending.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        s = get_settings(
            guild.id
        )

        channel = await get_channel(
            guild,
            s["showcase_channel_id"]
        )

        if not channel:

            await interaction.response.send_message(
                "❌ Showcase channel is missing.",
                ephemeral=True
            )

            return

        member = guild.get_member(
            row["user_id"]
        )

        name = (
            member.mention
            if member
            else "Creator"
        )

        await channel.send(
            embed=make_embed(
                "🎬 TikTok Showcase",
                f"👤 **Creator:** {name}\n\n"
                f"🔗 {row['url']}"
            )
        )

        db_execute(
            """
            UPDATE showcase_reviews
            SET status = 'approved'
            WHERE id = ?
            """,
            (self.review_id,)
        )

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="✅ **Approved and posted.**",
            view=self
        )

    @discord.ui.button(
        label="Reject",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="security_showcase_reject"
    )
    async def reject(
        self,
        interaction,
        button
    ):

        if not interaction.user.guild_permissions.manage_messages:

            await interaction.response.send_message(
                "❌ Staff permission required.",
                ephemeral=True
            )

            return

        db_execute(
            """
            UPDATE showcase_reviews
            SET status = 'rejected'
            WHERE id = ?
            """,
            (self.review_id,)
        )

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="❌ **Showcase submission rejected.**",
            view=self
        )


@bot.tree.command(
    name="showcase-setup",
    description="Configure TikTok Showcase"
)
@app_commands.describe(
    showcase_channel="Public showcase channel",
    review_channel="Staff review channel"
)
async def showcase_setup(
    interaction,
    showcase_channel: discord.TextChannel,
    review_channel: discord.TextChannel
):

    if not await require_admin(interaction):
        return

    gid = interaction.guild.id

    update_setting(
        gid,
        "showcase_channel_id",
        showcase_channel.id
    )

    update_setting(
        gid,
        "showcase_review_channel_id",
        review_channel.id
    )

    await interaction.response.send_message(
        "✅ TikTok Showcase settings saved.",
        ephemeral=True
    )


@bot.tree.command(
    name="showcase-message",
    description="Change showcase review message"
)
@app_commands.describe(
    message="Showcase message"
)
async def showcase_message(
    interaction,
    message: str
):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "showcase_message",
        message
    )

    await interaction.response.send_message(
        "✅ Showcase message saved.",
        ephemeral=True
    )


@bot.tree.command(
    name="showcase-on",
    description="Enable TikTok Showcase"
)
async def showcase_on(interaction):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "showcase_enabled",
        1
    )

    await interaction.response.send_message(
        "🎬 TikTok Showcase is now **ON**.",
        ephemeral=True
    )


@bot.tree.command(
    name="showcase-panel",
    description="Send the TikTok Showcase submission panel"
)
async def showcase_panel(interaction):

    if not interaction.guild:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    s = get_settings(interaction.guild.id)
    channel_id = s["showcase_channel_id"]

    if not channel_id:
        await interaction.response.send_message(
            "❌ Configure the showcase channel first with `/showcase-setup`.",
            ephemeral=True
        )
        return

    channel = await get_channel(interaction.guild, channel_id)

    if not channel:
        await interaction.response.send_message(
            "❌ The configured showcase channel no longer exists. Run `/showcase-setup` again.",
            ephemeral=True
        )
        return

    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label="🎬 Submit Showcase",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{interaction.guild.id}/{channel.id}"
        )
    )

    await interaction.response.send_message(
        embed=make_embed(
            "🎬 TikTok Showcase",
            "Share your TikTok edit in the showcase channel.\n\n"
            "Click the button below to go directly to the showcase channel."
        ),
        view=view
    )


@bot.tree.command(
    name="showcase-review",
    description="Send a TikTok submission for review"
)
@app_commands.describe(
    url="TikTok URL"
)
async def showcase_review(
    interaction,
    url: str
):

    if not await require_admin(interaction):
        return

    if not is_tiktok_url(url):

        await interaction.response.send_message(
            "❌ That does not look like a TikTok URL.",
            ephemeral=True
        )

        return

    s = get_settings(
        interaction.guild.id
    )

    review_channel = await get_channel(
        interaction.guild,
        s["showcase_review_channel_id"]
    )

    if not review_channel:

        await interaction.response.send_message(
            "❌ Configure the review channel first.",
            ephemeral=True
        )

        return

    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO showcase_reviews
        (
            guild_id,
            user_id,
            url,
            review_channel_id,
            status
        )
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (
            interaction.guild.id,
            interaction.user.id,
            url,
            review_channel.id
        )
    )

    review_id = cursor.lastrowid

    db.commit()

    message = await review_channel.send(
        embed=make_embed(
            "🎬 TikTok Review",
            f"**Submitted by:** "
            f"{interaction.user.mention}\n\n"
            f"🔗 {url}\n\n"
            f"Choose **Approve** or **Reject**."
        ),
        view=ShowcaseReviewView(
            review_id
        )
    )

    db_execute(
        """
        UPDATE showcase_reviews
        SET review_message_id = ?
        WHERE id = ?
        """,
        (
            message.id,
            review_id
        )
    )

    await interaction.response.send_message(
        "✅ Submission sent to the review channel.",
        ephemeral=True
    )


async def handle_showcase_message(
    message
):

    if message.author.bot:
        return

    s = get_settings(
        message.guild.id
    )

    if not s["showcase_enabled"]:
        return

    if not is_tiktok_url(message.content):
        return

    if (
        s["showcase_channel_id"]
        and message.channel.id != s["showcase_channel_id"]
    ):
        return

    review_channel = await get_channel(
        message.guild,
        s["showcase_review_channel_id"]
    )

    if not review_channel:
        return

    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO showcase_reviews
        (
            guild_id,
            user_id,
            url,
            review_channel_id,
            status
        )
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (
            message.guild.id,
            message.author.id,
            message.content,
            review_channel.id
        )
    )

    review_id = cursor.lastrowid

    db.commit()

    review_message = await review_channel.send(
        embed=make_embed(
            "🎬 TikTok Submission",
            f"**Creator:** {message.author.mention}\n\n"
            f"🔗 {message.content}\n\n"
            f"Staff review required."
        ),
        view=ShowcaseReviewView(
            review_id
        )
    )

    db_execute(
        """
        UPDATE showcase_reviews
        SET review_message_id = ?
        WHERE id = ?
        """,
        (
            review_message.id,
            review_id
        )
    )


# ============================================================
# END OF PART 7
# ============================================================
# ============================================================
# 🛡️ PART 9 — MODERATION
# ============================================================


spam_tracker = defaultdict(
    lambda: deque(maxlen=6)
)


def has_exempt_role(
    member
):

    rows = db_execute(
        """
        SELECT role_id
        FROM mod_exempt_roles
        WHERE guild_id = ?
        """,
        (member.guild.id,),
        fetchall=True
    )

    exempt = {
        row["role_id"]
        for row in rows
    }

    return any(
        role.id in exempt
        for role in member.roles
    )


async def give_warning(
    message
):

    guild = message.guild
    member = message.author

    row = db_execute(
        """
        SELECT warnings
        FROM warnings
        WHERE guild_id = ?
        AND user_id = ?
        """,
        (
            guild.id,
            member.id
        ),
        fetchone=True
    )

    amount = (
        row["warnings"]
        if row
        else 0
    )

    amount += 1

    db_execute(
        """
        INSERT OR REPLACE INTO warnings
        VALUES (?, ?, ?)
        """,
        (
            guild.id,
            member.id,
            amount
        )
    )

    if amount == 1:

        text = (
            f"⚠️ {member.mention}, "
            f"you received **Warning 1/4**.\n"
            f"Your message was removed."
        )

        try:
            notice = await message.channel.send(
                text
            )

            await asyncio.sleep(8)

            await notice.delete()

        except Exception:
            pass

    elif amount == 2:

        await mute_member(
            guild,
            member,
            1
        )

        await message.channel.send(
            f"🔇 {member.mention} received "
            f"**Warning 2/4** and was muted for **1 day**."
        )

    elif amount == 3:

        await mute_member(
            guild,
            member,
            3
        )

        await message.channel.send(
            f"🔇 {member.mention} received "
            f"**Warning 3/4** and was muted for **3 days**."
        )

    else:

        try:

            await guild.ban(
                member,
                reason="SECURITY automatic Warning 4/4"
            )

            await announce_ban(
                guild,
                member
            )

        except Exception:
            pass


async def mute_member(
    guild,
    member,
    days
):

    s = get_settings(
        guild.id
    )

    role = (
        guild.get_role(
            s["mute_role_id"]
        )
        if s["mute_role_id"]
        else None
    )

    if role:

        try:
            await member.add_roles(
                role,
                reason="SECURITY automatic moderation"
            )
        except Exception:
            pass

    else:

        try:

            await member.timeout(
                timedelta(days=days),
                reason="SECURITY automatic moderation"
            )

        except Exception:
            pass


async def announce_ban(
    guild,
    member
):

    s = get_settings(
        guild.id
    )

    channel = await get_channel(
        guild,
        s["ban_announce_channel_id"]
    )

    if channel:

        await channel.send(
            embed=make_embed(
                "🔨 Member Banned",
                f"**User:** {member.mention}\n"
                f"**Reason:** Automatic Warning 4/4"
            )
        )


async def handle_moderation(
    message
):

    if not message.guild:
        return False

    if message.author.bot:
        return False

    s = get_settings(
        message.guild.id
    )

    if not s["mod_enabled"]:
        return False

    if has_exempt_role(
        message.author
    ):
        return False

    now = datetime.now(
        timezone.utc
    ).timestamp()

    key = (
        message.guild.id,
        message.author.id
    )

    spam_tracker[key].append(
        (
            now,
            message.content
        )
    )

    recent = [
        item
        for item in spam_tracker[key]
        if now - item[0] <= 8
    ]

    violation = False

    # Excessive mentions
    if len(message.mentions) >= 6:
        violation = True

    # Repeated spam
    if len(recent) >= 4:

        contents = [
            item[1]
            for item in recent
        ]

        if len(set(contents)) <= 2:
            violation = True

    if not violation:
        return False

    try:
        await message.delete()
    except Exception:
        pass

    await give_warning(
        message
    )

    return True


@bot.tree.command(
    name="mod-setup",
    description="Configure automatic moderation"
)
@app_commands.describe(
    mute_role="Role used for automatic mutes",
    ban_channel="Ban announcement channel"
)
async def mod_setup(
    interaction,
    mute_role: discord.Role,
    ban_channel: discord.TextChannel
):

    if not await require_admin(interaction):
        return

    gid = interaction.guild.id

    update_setting(
        gid,
        "mute_role_id",
        mute_role.id
    )

    update_setting(
        gid,
        "ban_announce_channel_id",
        ban_channel.id
    )

    await interaction.response.send_message(
        "✅ Moderation setup saved.\n\n"
        f"🔇 Mute role: {mute_role.mention}\n"
        f"🔨 Ban announcements: {ban_channel.mention}\n\n"
        "Automatic warning system:\n"
        "1️⃣ Warning 1 → Delete message\n"
        "2️⃣ Warning 2 → Mute 1 day\n"
        "3️⃣ Warning 3 → Mute 3 days\n"
        "4️⃣ Warning 4 → Ban",
        ephemeral=True
    )


@bot.tree.command(
    name="mod-on",
    description="Enable automatic moderation"
)
async def mod_on(interaction):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "mod_enabled",
        1
    )

    await interaction.response.send_message(
        "🛡️ Automatic moderation is now **ON**.",
        ephemeral=True
    )


@bot.tree.command(
    name="mod-off",
    description="Disable automatic moderation"
)
async def mod_off(interaction):

    if not await require_admin(interaction):
        return

    update_setting(
        interaction.guild.id,
        "mod_enabled",
        0
    )

    await interaction.response.send_message(
        "🛡️ Automatic moderation is now **OFF**.",
        ephemeral=True
    )


# ============================================================
# END OF PART 9
# ============================================================
# ============================================================
# 🔧 PART 10 — UTILITY
# ============================================================


@bot.tree.command(
    name="ping",
    description="Check bot latency"
)
async def ping(interaction):

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 **Pong!** `{latency}ms`"
    )


@bot.tree.command(
    name="botinfo",
    description="View bot information"
)
async def botinfo(interaction):

    await interaction.response.send_message(
        embed=make_embed(
            "🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘",
            f"**Servers:** {len(bot.guilds)}\n"
            f"**Users:** {sum(g.member_count or 0 for g in bot.guilds)}\n"
            f"**Latency:** "
            f"{round(bot.latency * 1000)}ms\n"
            f"**Library:** discord.py"
        )
    )


@bot.tree.command(
    name="membercount",
    description="View server member count"
)
async def membercount(interaction):

    guild = interaction.guild

    humans = sum(
        1
        for member in guild.members
        if not member.bot
    )

    bots = sum(
        1
        for member in guild.members
        if member.bot
    )

    await interaction.response.send_message(
        embed=make_embed(
            "👥 Member Count",
            f"👥 **Total:** {guild.member_count}\n"
            f"👤 **Humans:** {humans}\n"
            f"🤖 **Bots:** {bots}"
        )
    )


@bot.tree.command(
    name="userinfo",
    description="View user information"
)
@app_commands.describe(
    member="Member to inspect"
)
async def userinfo(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    roles = [
        role.mention
        for role in member.roles
        if role != interaction.guild.default_role
    ]

    await interaction.response.send_message(
        embed=make_embed(
            f"👤 {member.display_name}",
            f"**Username:** {member}\n"
            f"**ID:** `{member.id}`\n"
            f"**Joined:** "
            f"<t:{int(member.joined_at.timestamp())}:F>\n"
            f"**Created:** "
            f"<t:{int(member.created_at.timestamp())}:F>\n\n"
            f"**Roles:** "
            f"{', '.join(roles) if roles else 'None'}"
        )
    )


@bot.tree.command(
    name="avatar",
    description="View a member avatar"
)
@app_commands.describe(
    member="Member"
)
async def avatar(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    e = make_embed(
        f"🖼️ {member.display_name}'s Avatar"
    )

    e.set_image(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=e
    )


@bot.tree.command(
    name="emojiinfo",
    description="View custom emoji information"
)
@app_commands.describe(
    emoji="Custom emoji"
)
async def emojiinfo(
    interaction,
    emoji: str
):

    match = re.search(
        r"<(a?):(\w+):(\d+)>",
        emoji
    )

    if not match:

        await interaction.response.send_message(
            embed=make_embed(
                "😀 Emoji",
                f"**Emoji:** {emoji}\n"
                f"**Type:** Unicode emoji"
            )
        )

        return

    animated = bool(
        match.group(1)
    )

    name = match.group(2)
    emoji_id = match.group(3)

    url = (
        f"https://cdn.discordapp.com/emojis/"
        f"{emoji_id}.{'gif' if animated else 'png'}"
    )

    e = make_embed(
        "😀 Emoji Information",
        f"**Name:** `{name}`\n"
        f"**ID:** `{emoji_id}`\n"
        f"**Animated:** "
        f"{'Yes' if animated else 'No'}"
    )

    e.set_thumbnail(
        url=url
    )

    await interaction.response.send_message(
        embed=e
    )


@bot.tree.command(
    name="say",
    description="Make SECURITY send a message"
)
@app_commands.describe(
    message="Message to send"
)
async def say(
    interaction,
    message: str
):

    if not interaction.user.guild_permissions.manage_messages:

        await interaction.response.send_message(
            "❌ Manage Messages permission required.",
            ephemeral=True
        )

        return

    await interaction.channel.send(
        message
    )

    await interaction.response.send_message(
        "✅ Message sent.",
        ephemeral=True
    )


# ============================================================
# HELP
# ============================================================

@bot.tree.command(
    name="help",
    description="View all SECURITY commands"
)
async def help_command(interaction):

    e = make_embed(
        "🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — COMMAND PANEL",
        "Professional Discord server management."
    )

    e.add_field(
        name="👋 Welcome / Bye",
        value=(
            "`/welcome-setup` `/welcome` `/testwelcome`\n"
            "`/bye-setup` `/bye` `/testbye`"
        ),
        inline=False
    )

    e.add_field(
        name="✅ Verification",
        value=(
            "`/verifysetup` `/verify`\n"
            "`/verify-panel` `/verifyrole` `/verifymessage`"
        ),
        inline=False
    )

    e.add_field(
        name="🎫 Tickets",
        value=(
            "`/ticket-setup` `/ticket-panel` `/ticket`\n"
            "`/ticket-close` `/ticket-add` `/ticket-remove`"
        ),
        inline=False
    )

    e.add_field(
        name="📊 Stats",
        value=(
            "`/stats-setup` `/stats`"
        ),
        inline=False
    )

    e.add_field(
        name="⭐ Levels",
        value=(
            "`/levels-setup` `/levels-on` `/levels-off`\n"
            "`/rank` `/level` `/leaderboard`"
        ),
        inline=False
    )

    e.add_field(
        name="🎬 TikTok Showcase",
        value=(
            "`/showcase-setup` `/showcase-message`\n"
            "`/showcase-on` `/showcase-review`"
        ),
        inline=False
    )

    e.add_field(
        name="🛡️ Moderation",
        value=(
            "`/mod-setup` `/mod-on` `/mod-off`"
        ),
        inline=False
    )

    e.add_field(
        name="🔧 Utility",
        value=(
            "`/clear` `/ping` `/botinfo`\n"
            "`/membercount` `/userinfo` `/avatar`\n"
            "`/emojiinfo` `/say`"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=e,
        ephemeral=True
    )


# ============================================================
# END OF PART 10
# ============================================================
# ============================================================
# ⏰ PART 11 — REMINDERS + MESSAGE EVENTS
# ============================================================


def parse_duration(text):

    match = re.fullmatch(
        r"(\d+)(s|m|h|d|w)",
        text.lower().strip()
    )

    if not match:
        return None

    amount = int(
        match.group(1)
    )

    unit = match.group(2)

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800
    }

    return timedelta(
        seconds=amount * multipliers[unit]
    )


@bot.tree.command(
    name="remind",
    description="Set a reminder"
)
@app_commands.describe(
    time="Example: 10m, 2h, 1d",
    message="Reminder message"
)
async def remind(
    interaction,
    time: str,
    message: str
):

    duration = parse_duration(
        time
    )

    if not duration:

        await interaction.response.send_message(
            "❌ Invalid time.\n"
            "Use examples like `10m`, `2h`, `1d`.",
            ephemeral=True
        )

        return

    remind_at = (
        datetime.now(timezone.utc)
        + duration
    )

    db_execute(
        """
        INSERT INTO reminders
        (
            guild_id,
            user_id,
            channel_id,
            remind_at,
            message
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            interaction.guild.id,
            interaction.user.id,
            interaction.channel.id,
            remind_at.isoformat(),
            message
        )
    )

    await interaction.response.send_message(
        f"⏰ Reminder set for "
        f"<t:{int(remind_at.timestamp())}:R>.",
        ephemeral=True
    )


async def reminder_worker():

    while True:

        try:

            now = datetime.now(
                timezone.utc
            )

            rows = db_execute(
                """
                SELECT *
                FROM reminders
                """,
                fetchall=True
            )

            for row in rows:

                try:

                    remind_at = datetime.fromisoformat(
                        row["remind_at"]
                    )

                    if remind_at > now:
                        continue

                    channel = None

                    guild = bot.get_guild(
                        row["guild_id"]
                    )

                    if guild:

                        channel = guild.get_channel(
                            row["channel_id"]
                        )

                    if channel:

                        await channel.send(
                            f"<@{row['user_id']}> ⏰ "
                            f"**Reminder:** {row['message']}"
                        )

                    db_execute(
                        """
                        DELETE FROM reminders
                        WHERE id = ?
                        """,
                        (row["id"],)
                    )

                except Exception as error:

                    print(
                        f"Reminder error: {error}"
                    )

        except Exception as error:

            print(
                f"Reminder worker error: {error}"
            )

        await asyncio.sleep(5)


# ============================================================
# MESSAGE EVENT
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        return

    # Automatic moderation
    blocked = await handle_moderation(
        message
    )

    if blocked:
        return

    # XP
    await add_xp(
        message
    )

    # TikTok showcase
    await handle_showcase_message(
        message
    )

    await bot.process_commands(
        message
    )


# ============================================================
# END OF PART 11
# ============================================================
# ============================================================
# 🔐 FINAL PART — STARTUP
# ============================================================


background_started = False
persistent_views_added = False


@bot.event
async def on_ready():

    global background_started
    global persistent_views_added

    print(
        f"🚀 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 ONLINE: {bot.user}"
    )

    # --------------------------------------------------------
    # Persistent buttons
    # --------------------------------------------------------

    if not persistent_views_added:

        try:

            bot.add_view(
                VerifyPanel()
            )

            bot.add_view(
                TicketPanel()
            )

            # Restore pending showcase review buttons
            reviews = db_execute(
                """
                SELECT id, review_message_id
                FROM showcase_reviews
                WHERE status = 'pending'
                AND review_message_id IS NOT NULL
                """,
                fetchall=True
            )

            for review in reviews:

                try:

                    bot.add_view(
                        ShowcaseReviewView(
                            review["id"]
                        ),
                        message_id=review["review_message_id"]
                    )

                except Exception as error:

                    print(
                        f"Review view error: {error}"
                    )

            persistent_views_added = True

        except Exception as error:

            print(
                f"Persistent view error: {error}"
            )

    # --------------------------------------------------------
    # Background workers
    # --------------------------------------------------------

    if not background_started:

        background_started = True

        asyncio.create_task(
            reminder_worker()
        )

        asyncio.create_task(
            stats_worker()
        )

    # --------------------------------------------------------
    # Slash commands
    # --------------------------------------------------------

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ Synced {len(synced)} slash commands."
        )

    except Exception as error:

        print(
            f"❌ Slash command sync failed: {error}"
        )


async def stats_worker():

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:

            await update_stat_channels()

        except Exception as error:

            print(
                f"Stats worker error: {error}"
            )

        await asyncio.sleep(60)


# ============================================================
# FINAL START
# ============================================================

print(
    "🚀 SECURITY Python file started!"
)

bot.run(TOKEN)

# ============================================================
# END OF 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 BOT
# ============================================================
