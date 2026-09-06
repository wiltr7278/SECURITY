# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 1/13
# CORE BOT SETUP
# ============================================================

import discord
from discord import app_commands
from discord.ext import commands

import os
import json
import asyncio
import random
import re
import time

from datetime import timedelta
from typing import Optional


# ============================================================
# 🔑 TOKEN
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "❌ DISCORD_TOKEN is missing. "
        "Add DISCORD_TOKEN to your hosting platform's Variables."
    )


# ============================================================
# 📁 CONFIG
# ============================================================

CONFIG_FILE = "config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {}

        return data

    except (json.JSONDecodeError, OSError):
        return {}


config = load_config()


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

    except OSError as error:
        print(f"❌ Config save error: {error}")


# ============================================================
# ⚙️ GUILD CONFIG
# ============================================================

def get_guild_config(guild_id: int):
    guild_id = str(guild_id)

    if guild_id not in config:
        config[guild_id] = {}

    cfg = config[guild_id]

    # ---------------- WELCOME ----------------

    cfg.setdefault("welcome_channel", None)
    cfg.setdefault("welcome_enabled", True)
    cfg.setdefault(
        "welcome_message",
        "👋 Welcome {user} to **{server}**!\n"
        "🔐 Please **verify before chatting**.\n"
        "Enjoy your stay! 🛡️"
    )
    cfg.setdefault("welcome_image", None)
    cfg.setdefault("welcome_style", "avatar")
    cfg.setdefault("auto_role", None)

    # ---------------- BYE ----------------

    cfg.setdefault("bye_channel", None)
    cfg.setdefault("bye_enabled", True)
    cfg.setdefault(
        "bye_message",
        "**{username}** has left **{server}**. 👋"
    )
    cfg.setdefault("bye_image", None)
    cfg.setdefault("bye_style", "avatar")

    # ---------------- VERIFICATION ----------------

    cfg.setdefault("verify_role", None)
    cfg.setdefault("verify_channel", None)
    cfg.setdefault(
        "verify_message",
        "Click the button below to verify."
    )

    # ---------------- LEVELS ----------------

    cfg.setdefault("level_enabled", True)
    cfg.setdefault("level_channel", None)
    cfg.setdefault(
        "level_message",
        "GG {user}! You reached level **{level}**! 🎉"
    )
    cfg.setdefault("xp", {})

    # ---------------- TICKETS ----------------

    cfg.setdefault("ticket_category", None)
    cfg.setdefault("ticket_staff_role", None)

    # ---------------- TIKTOK SHOWCASE ----------------

    cfg.setdefault("showcase_channel", None)
    cfg.setdefault("showcase_judge_channel", None)
    cfg.setdefault("showcase_judge_role", None)
    cfg.setdefault("showcase_enabled", False)
    cfg.setdefault(
        "showcase_message",
        "Submit your TikTok below! 🎬"
    )

    # ---------------- MEMBER COUNT ----------------
    # Stores the channel created by /membercount.

    cfg.setdefault("membercount_channel", None)
    cfg.setdefault("membercount_type", None)

    save_config()

    return cfg


# ============================================================
# 📝 MESSAGE PLACEHOLDERS
# ============================================================

def format_message(
    message: str,
    member: discord.Member,
    guild: discord.Guild
):
    return (
        message
        .replace("{user}", member.mention)
        .replace("{username}", member.display_name)
        .replace("{server}", guild.name)
        .replace(
            "{count}",
            str(guild.member_count or len(guild.members))
        )
    )


# ============================================================
# 🎬 TIKTOK LINK DETECTOR
# ============================================================

def extract_tiktok_link(text: str):
    pattern = (
        r"(https?://(?:www\.)?"
        r"(?:tiktok\.com|vm\.tiktok\.com|"
        r"vt\.tiktok\.com|m\.tiktok\.com)"
        r"[^\s<>]+)"
    )

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return match.group(1).rstrip(".,!?)]}")

    return None


# ============================================================
# 🤖 DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()

# Required for member join/leave, roles and member count.
intents.members = True

# Required for levels, TikTok submissions and message commands.
intents.message_content = True


# ============================================================
# 🛡️ BASIC PERMISSION CHECK
# ============================================================

def bot_can_manage_role(
    guild: discord.Guild,
    role: discord.Role
) -> tuple[bool, str]:

    if role.is_default():
        return False, "❌ You cannot use the @everyone role."

    if role.managed:
        return False, "❌ That role is managed by Discord/integration."

    me = guild.me

    if me is None:
        return False, "❌ I cannot find my member information."

    if not me.guild_permissions.manage_roles:
        return False, "❌ I need the **Manage Roles** permission."

    if role >= me.top_role:
        return (
            False,
            "❌ My highest role must be **above** that role."
        )

    return True, ""


# ============================================================
# 🔐 SECURITY BOT
# ============================================================

class SecurityBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        self.start_time = time.time()


# ============================================================
# 🚀 CREATE BOT
# ============================================================

bot = SecurityBot()


# ============================================================
# ❌ GLOBAL SLASH COMMAND ERROR HANDLER
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    if isinstance(error, app_commands.MissingPermissions):
        message = (
            "❌ You don't have permission to use this command."
        )

    elif isinstance(error, app_commands.BotMissingPermissions):
        message = (
            "❌ I don't have the required permissions."
        )

    elif isinstance(error, app_commands.CommandOnCooldown):
        message = (
            "⏳ This command is on cooldown. Try again later."
        )

    elif isinstance(error, app_commands.CheckFailure):
        message = (
            "❌ You cannot use this command here."
        )

    else:
        print(
            f"❌ Slash command error: "
            f"{type(error).__name__}: {error}"
        )

        message = (
            "❌ An error occurred while running "
            "this command."
        )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except discord.HTTPException:
        pass


# ============================================================
# 🔐 END OF PART 1
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 2/13
# BOT STARTUP + COMMAND SYNC
# ============================================================


# ============================================================
# 🎛️ PERSISTENT VIEW PLACEHOLDERS
# ============================================================
# The actual button classes will be added in later parts.
# These lists prevent duplicate registration if startup runs again.

_registered_views = False


# ============================================================
# 🚀 BOT STARTUP
# ============================================================

@bot.event
async def setup_hook():

    global _registered_views

    if not _registered_views:
        # Persistent views from later parts will be added here.
        # We don't register anything yet because their classes
        # are created in Parts 5, 6, and 11.

        _registered_views = True

    # --------------------------------------------------------
    # SYNC SLASH COMMANDS
    # --------------------------------------------------------

    try:
        synced = await bot.tree.sync()

        print(
            f"✅ Successfully synced "
            f"{len(synced)} slash command(s)."
        )

    except Exception as error:
        print(
            f"❌ Slash command sync failed: "
            f"{type(error).__name__}: {error}"
        )


# ============================================================
# 🟢 BOT READY
# ============================================================

@bot.event
async def on_ready():

    print("========================================")
    print("🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 is online!")
    print(f"🤖 Logged in as: {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Servers: {len(bot.guilds)}")
    print("🛡️ Protect • Moderate • Secure")
    print("========================================")


# ============================================================
# 🔄 MEMBER COUNT HELPER
# ============================================================
# The actual /membercount command comes later.
# This helper is used by the automatic join/leave system.

async def get_real_member_count(
    guild: discord.Guild
) -> int:

    # Discord's member_count is normally the best source.
    # Fall back to cached members if necessary.

    if guild.member_count is not None:
        return guild.member_count

    return len(guild.members)


# ============================================================
# 🧹 SAFE CHANNEL FETCHER
# ============================================================

async def get_configured_channel(
    guild: discord.Guild,
    channel_id
):

    if not channel_id:
        return None

    try:
        channel_id = int(channel_id)
    except (TypeError, ValueError):
        return None

    channel = guild.get_channel(channel_id)

    if channel is not None:
        return channel

    try:
        return await guild.fetch_channel(channel_id)
    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        return None


# ============================================================
# 🛡️ SAFE ROLE FETCHER
# ============================================================

async def get_configured_role(
    guild: discord.Guild,
    role_id
):

    if not role_id:
        return None

    try:
        role_id = int(role_id)
    except (TypeError, ValueError):
        return None

    role = guild.get_role(role_id)

    if role is not None:
        return role

    try:
        return await guild.fetch_role(role_id)
    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        return None


# ============================================================
# 🔐 END OF PART 2
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 3/13
# 👋 WELCOME SYSTEM
# ============================================================


# ============================================================
# 👋 SEND WELCOME MESSAGE
# ============================================================

async def send_welcome_message(
    member: discord.Member,
    test: bool = False
):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    if not cfg.get("welcome_enabled", True) and not test:
        return

    channel_id = cfg.get("welcome_channel")

    if not channel_id:
        return

    channel = await get_configured_channel(
        guild,
        channel_id
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    text = format_message(
        cfg.get(
            "welcome_message",
            "👋 Welcome {user} to **{server}**!"
        ),
        member,
        guild
    )

    style = cfg.get("welcome_style", "avatar")
    image = cfg.get("welcome_image")

    embed = discord.Embed(
        description=text,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"{guild.name} • Member #{guild.member_count or len(guild.members)}"
    )

    # --------------------------------------------------------
    # WELCOME IMAGE
    # --------------------------------------------------------

    if style in ("avatar", "both"):
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

    if style in ("custom", "both") and image:
        embed.set_image(url=image)

    try:
        await channel.send(embed=embed)

    except discord.Forbidden:
        print(
            f"❌ Cannot send welcome message in "
            f"#{channel.name} ({guild.name})."
        )

    except discord.HTTPException as error:
        print(
            f"❌ Welcome message error: {error}"
        )


# ============================================================
# 👋 AUTOMATIC MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(
    member: discord.Member
):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    # --------------------------------------------------------
    # AUTO ROLE
    # --------------------------------------------------------

    role_id = cfg.get("auto_role")

    if role_id:

        role = await get_configured_role(
            guild,
            role_id
        )

        if role is not None:

            can_manage, reason = bot_can_manage_role(
                guild,
                role
            )

            if can_manage:

                try:
                    await member.add_roles(
                        role,
                        reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 automatic welcome role"
                    )

                except discord.Forbidden:
                    print(
                        f"❌ Cannot give auto-role "
                        f"{role.name} in {guild.name}."
                    )

                except discord.HTTPException as error:
                    print(
                        f"❌ Auto-role error: {error}"
                    )

            else:
                print(
                    f"❌ Auto-role unavailable: {reason}"
                )

    # --------------------------------------------------------
    # WELCOME
    # --------------------------------------------------------

    await send_welcome_message(member)


# ============================================================
# ⚙️ /welcome
# ============================================================

@bot.tree.command(
    name="welcome",
    description="Configure the welcome channel"
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    channel="The channel where welcome messages are sent"
)
async def welcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_channel"] = channel.id
    cfg["welcome_enabled"] = True

    save_config()

    await interaction.response.send_message(
        f"✅ Welcome messages will now be sent in {channel.mention}.",
        ephemeral=True
    )


# ============================================================
# 🟢 /welcome-on
# ============================================================

@bot.tree.command(
    name="welcome-on",
    description="Turn welcome messages on"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_on(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_enabled"] = True
    save_config()

    await interaction.response.send_message(
        "✅ Welcome messages are now **ON**.",
        ephemeral=True
    )


# ============================================================
# 🔴 /welcome-off
# ============================================================

@bot.tree.command(
    name="welcome-off",
    description="Turn welcome messages off"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_off(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_enabled"] = False
    save_config()

    await interaction.response.send_message(
        "🔴 Welcome messages are now **OFF**.",
        ephemeral=True
    )


# ============================================================
# 💬 /welcome-message
# ============================================================

@bot.tree.command(
    name="welcome-message",
    description="Set the welcome message"
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    message="Welcome message. Use {user}, {username}, {server}, {count}"
)
async def welcome_message(
    interaction: discord.Interaction,
    message: str
):

    if not message.strip():
        await interaction.response.send_message(
            "❌ The message cannot be empty.",
            ephemeral=True
        )
        return

    if len(message) > 2000:
        await interaction.response.send_message(
            "❌ The message must be 2000 characters or less.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Welcome message updated.",
        ephemeral=True
    )


# ============================================================
# 🖼️ /welcome-image
# ============================================================

@bot.tree.command(
    name="welcome-image",
    description="Set or remove the welcome image"
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    image_url="Image URL, or leave empty to remove it"
)
async def welcome_image(
    interaction: discord.Interaction,
    image_url: Optional[str] = None
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    if image_url:
        if not image_url.startswith(
            ("http://", "https://")
        ):
            await interaction.response.send_message(
                "❌ Please provide a valid image URL.",
                ephemeral=True
            )
            return

        cfg["welcome_image"] = image_url
        save_config()

        await interaction.response.send_message(
            "✅ Welcome image updated.",
            ephemeral=True
        )

    else:
        cfg["welcome_image"] = None
        save_config()

        await interaction.response.send_message(
            "✅ Welcome custom image removed.",
            ephemeral=True
        )


# ============================================================
# 🎨 /welcome-style
# ============================================================

@bot.tree.command(
    name="welcome-style",
    description="Choose the welcome image style"
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    style="Choose avatar, custom, or both"
)
@app_commands.choices(
    style=[
        app_commands.Choice(
            name="Avatar",
            value="avatar"
        ),
        app_commands.Choice(
            name="Custom Image",
            value="custom"
        ),
        app_commands.Choice(
            name="Avatar + Custom",
            value="both"
        )
    ]
)
async def welcome_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_style"] = style.value
    save_config()

    await interaction.response.send_message(
        f"✅ Welcome style set to **{style.name}**.",
        ephemeral=True
    )


# ============================================================
# 🛡️ /welcome-role
# ============================================================
# IMPORTANT:
# This uses discord.Role.
# Discord provides a real role selector.
# NO manual role ID is required.

@bot.tree.command(
    name="welcome-role",
    description="Set the automatic role for new members"
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    role="Select the role new members should receive"
)
async def welcome_role(
    interaction: discord.Interaction,
    role: discord.Role
):

    guild = interaction.guild

    can_manage, reason = bot_can_manage_role(
        guild,
        role
    )

    if not can_manage:
        await interaction.response.send_message(
            reason,
            ephemeral=True
        )
        return

    cfg = get_guild_config(
        guild.id
    )

    cfg["auto_role"] = role.id
    save_config()

    await interaction.response.send_message(
        f"✅ Auto-role set to {role.mention}.\n"
        "New members will receive this role automatically.",
        ephemeral=True
    )


# ============================================================
# 🔴 /welcome-role-off
# ============================================================

@bot.tree.command(
    name="welcome-role-off",
    description="Disable the automatic welcome role"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_role_off(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["auto_role"] = None
    save_config()

    await interaction.response.send_message(
        "✅ Automatic welcome role disabled.",
        ephemeral=True
    )


# ============================================================
# 🧪 /testwelcome
# ============================================================

@bot.tree.command(
    name="testwelcome",
    description="Test your welcome message"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def testwelcome(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    channel_id = cfg.get("welcome_channel")

    if not channel_id:
        await interaction.response.send_message(
            "❌ Set a welcome channel first with `/welcome`.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    await send_welcome_message(
        interaction.user,
        test=True
    )

    await interaction.followup.send(
        "✅ Welcome test sent.",
        ephemeral=True
    )


# ============================================================
# 🔐 END OF PART 3
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 4/13
# 👋 BYE SYSTEM
# ============================================================


# ============================================================
# 👋 SEND BYE MESSAGE
# ============================================================

async def send_bye_message(
    member: discord.Member,
    test: bool = False
):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    if not cfg.get("bye_enabled", True) and not test:
        return

    channel_id = cfg.get("bye_channel")

    if not channel_id:
        return

    channel = await get_configured_channel(
        guild,
        channel_id
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    text = format_message(
        cfg.get(
            "bye_message",
            "**{username}** has left **{server}**. 👋"
        ),
        member,
        guild
    )

    style = cfg.get("bye_style", "avatar")
    image = cfg.get("bye_image")

    embed = discord.Embed(
        description=text,
        color=discord.Color.red()
    )

    # --------------------------------------------------------
    # AVATAR
    # --------------------------------------------------------

    if style in ("avatar", "both"):
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

    # --------------------------------------------------------
    # CUSTOM IMAGE
    # --------------------------------------------------------

    if style in ("custom", "both") and image:
        embed.set_image(
            url=image
        )

    embed.set_footer(
        text=f"{guild.name} • Goodbye 👋"
    )

    try:
        await channel.send(
            embed=embed
        )

    except discord.Forbidden:
        print(
            f"❌ Cannot send bye message in "
            f"#{channel.name} ({guild.name})."
        )

    except discord.HTTPException as error:
        print(
            f"❌ Bye message error: {error}"
        )


# ============================================================
# 👋 AUTOMATIC MEMBER LEAVE
# ============================================================

@bot.event
async def on_member_remove(
    member: discord.Member
):

    await send_bye_message(
        member
    )


# ============================================================
# ⚙️ /bye
# ============================================================

@bot.tree.command(
    name="bye",
    description="Configure the bye channel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    channel="The channel where bye messages are sent"
)
async def bye(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["bye_channel"] = channel.id
    cfg["bye_enabled"] = True

    save_config()

    await interaction.response.send_message(
        f"✅ Bye messages will now be sent in "
        f"{channel.mention}.",
        ephemeral=True
    )


# ============================================================
# 🟢 /bye-on
# ============================================================

@bot.tree.command(
    name="bye-on",
    description="Turn bye messages on"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def bye_on(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["bye_enabled"] = True

    save_config()

    await interaction.response.send_message(
        "✅ Bye messages are now **ON**.",
        ephemeral=True
    )


# ============================================================
# 🔴 /bye-off
# ============================================================

@bot.tree.command(
    name="bye-off",
    description="Turn bye messages off"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def bye_off(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["bye_enabled"] = False

    save_config()

    await interaction.response.send_message(
        "🔴 Bye messages are now **OFF**.",
        ephemeral=True
    )


# ============================================================
# 💬 /bye-message
# ============================================================

@bot.tree.command(
    name="bye-message",
    description="Set the bye message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    message="Bye message. Use {user}, {username}, {server}, {count}"
)
async def bye_message(
    interaction: discord.Interaction,
    message: str
):

    if not message.strip():
        await interaction.response.send_message(
            "❌ The message cannot be empty.",
            ephemeral=True
        )
        return

    if len(message) > 2000:
        await interaction.response.send_message(
            "❌ The message must be 2000 characters or less.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["bye_message"] = message

    save_config()

    await interaction.response.send_message(
        "✅ Bye message updated.",
        ephemeral=True
    )


# ============================================================
# 🖼️ /bye-image
# ============================================================

@bot.tree.command(
    name="bye-image",
    description="Set or remove the bye image"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    image_url="Image URL, or leave empty to remove it"
)
async def bye_image(
    interaction: discord.Interaction,
    image_url: Optional[str] = None
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    if image_url:

        if not image_url.startswith(
            ("http://", "https://")
        ):
            await interaction.response.send_message(
                "❌ Please provide a valid image URL.",
                ephemeral=True
            )
            return

        cfg["bye_image"] = image_url

        save_config()

        await interaction.response.send_message(
            "✅ Bye image updated.",
            ephemeral=True
        )

    else:

        cfg["bye_image"] = None

        save_config()

        await interaction.response.send_message(
            "✅ Bye custom image removed.",
            ephemeral=True
        )


# ============================================================
# 🎨 /bye-style
# ============================================================

@bot.tree.command(
    name="bye-style",
    description="Choose the bye image style"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    style="Choose avatar, custom, or both"
)
@app_commands.choices(
    style=[
        app_commands.Choice(
            name="Avatar",
            value="avatar"
        ),
        app_commands.Choice(
            name="Custom Image",
            value="custom"
        ),
        app_commands.Choice(
            name="Avatar + Custom",
            value="both"
        )
    ]
)
async def bye_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["bye_style"] = style.value

    save_config()

    await interaction.response.send_message(
        f"✅ Bye style set to **{style.name}**.",
        ephemeral=True
    )


# ============================================================
# 🧪 /testbye
# ============================================================

@bot.tree.command(
    name="testbye",
    description="Test your bye message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def testbye(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    if not cfg.get("bye_channel"):
        await interaction.response.send_message(
            "❌ Set a bye channel first with `/bye`.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    # Use the command user as the test member.
    await send_bye_message(
        interaction.user,
        test=True
    )

    await interaction.followup.send(
        "✅ Bye test sent.",
        ephemeral=True
    )


# ============================================================
# 🔐 END OF PART 4
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 5/13
# ✅ VERIFICATION + 🎫 TICKETS
# ============================================================


# ============================================================
# ✅ VERIFICATION BUTTON
# ============================================================

class VerifyButton(discord.ui.View):

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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True
            )
            return

        cfg = get_guild_config(guild.id)

        role_id = cfg.get("verify_role")

        if not role_id:
            await interaction.response.send_message(
                "❌ Verification has not been configured yet.",
                ephemeral=True
            )
            return

        role = await get_configured_role(
            guild,
            role_id
        )

        if role is None:
            await interaction.response.send_message(
                "❌ The configured verification role no longer exists.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "✅ You are already verified!",
                ephemeral=True
            )
            return

        can_manage, reason = bot_can_manage_role(
            guild,
            role
        )

        if not can_manage:
            await interaction.response.send_message(
                reason,
                ephemeral=True
            )
            return

        try:
            await interaction.user.add_roles(
                role,
                reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 verification"
            )

            await interaction.response.send_message(
                f"✅ You are now verified and received "
                f"{role.mention}!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I cannot give you the verification role. "
                "Make sure my role is above the verification role.",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Discord rejected the role update. Try again.",
                ephemeral=True
            )


# ============================================================
# ⚙️ /verifysetup
# ============================================================
# Uses discord.Role so Discord gives you a real role selector.

@bot.tree.command(
    name="verifysetup",
    description="Configure the verification system"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    role="Select the role members receive after verification",
    channel="Select the verification channel"
)
async def verifysetup(
    interaction: discord.Interaction,
    role: discord.Role,
    channel: discord.TextChannel
):

    guild = interaction.guild

    can_manage, reason = bot_can_manage_role(
        guild,
        role
    )

    if not can_manage:
        await interaction.response.send_message(
            reason,
            ephemeral=True
        )
        return

    cfg = get_guild_config(
        guild.id
    )

    cfg["verify_role"] = role.id
    cfg["verify_channel"] = channel.id

    save_config()

    await interaction.response.send_message(
        f"✅ Verification configured!\n\n"
        f"🎯 Role: {role.mention}\n"
        f"📍 Channel: {channel.mention}",
        ephemeral=True
    )


# ============================================================
# 💬 /verify-message
# ============================================================

@bot.tree.command(
    name="verify-message",
    description="Set the verification message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    message="Message shown in the verification panel"
)
async def verify_message(
    interaction: discord.Interaction,
    message: str
):

    if not message.strip():
        await interaction.response.send_message(
            "❌ The message cannot be empty.",
            ephemeral=True
        )
        return

    if len(message) > 4000:
        await interaction.response.send_message(
            "❌ The message is too long.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["verify_message"] = message

    save_config()

    await interaction.response.send_message(
        "✅ Verification message updated.",
        ephemeral=True
    )


# ============================================================
# 📋 /verify-panel
# ============================================================

@bot.tree.command(
    name="verify-panel",
    description="Send the verification panel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    channel="Channel where the verification panel will be sent"
)
async def verify_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    guild = interaction.guild
    cfg = get_guild_config(guild.id)

    role_id = cfg.get("verify_role")

    if not role_id:
        await interaction.response.send_message(
            "❌ Run `/verifysetup` first.",
            ephemeral=True
        )
        return

    role = await get_configured_role(
        guild,
        role_id
    )

    if role is None:
        await interaction.response.send_message(
            "❌ The verification role no longer exists. "
            "Run `/verifysetup` again.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 Verification",
        description=cfg.get(
            "verify_message",
            "Click the button below to verify."
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 • Verification"
    )

    try:
        await channel.send(
            embed=embed,
            view=VerifyButton()
        )

        cfg["verify_channel"] = channel.id
        save_config()

        await interaction.response.send_message(
            f"✅ Verification panel sent to {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot send messages in that channel.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the verification panel.",
            ephemeral=True
        )


# ============================================================
# ✅ /verify
# ============================================================

@bot.tree.command(
    name="verify",
    description="Verify yourself"
)
async def verify(
    interaction: discord.Interaction
):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(
        guild.id
    )

    role_id = cfg.get("verify_role")

    if not role_id:
        await interaction.response.send_message(
            "❌ Verification has not been configured.",
            ephemeral=True
        )
        return

    role = await get_configured_role(
        guild,
        role_id
    )

    if role is None:
        await interaction.response.send_message(
            "❌ The verification role no longer exists.",
            ephemeral=True
        )
        return

    if role in interaction.user.roles:
        await interaction.response.send_message(
            "✅ You are already verified!",
            ephemeral=True
        )
        return

    can_manage, reason = bot_can_manage_role(
        guild,
        role
    )

    if not can_manage:
        await interaction.response.send_message(
            reason,
            ephemeral=True
        )
        return

    try:
        await interaction.user.add_roles(
            role,
            reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 verification command"
        )

        await interaction.response.send_message(
            f"✅ Verification successful! "
            f"You received {role.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot give you that role. "
            "Move my bot role above the verification role.",
            ephemeral=True
        )


# ============================================================
# 🎫 TICKET CREATE BUTTON
# ============================================================

class TicketCreateButton(discord.ui.View):

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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True
            )
            return

        cfg = get_guild_config(
            guild.id
        )

        category_id = cfg.get(
            "ticket_category"
        )

        category = None

        if category_id:
            category = guild.get_channel(
                int(category_id)
            )

            if category is not None and not isinstance(
                category,
                discord.CategoryChannel
            ):
                category = None

        # ----------------------------------------------------
        # CHECK FOR EXISTING TICKET
        # ----------------------------------------------------

        for channel in guild.text_channels:

            if channel.topic == f"ticket:{interaction.user.id}":
                await interaction.response.send_message(
                    f"❌ You already have a ticket: "
                    f"{channel.mention}",
                    ephemeral=True
                )
                return

        # ----------------------------------------------------
        # BOT MEMBER
        # ----------------------------------------------------

        bot_member = guild.me

        if bot_member is None:
            await interaction.response.send_message(
                "❌ I cannot find my bot member.",
                ephemeral=True
            )
            return

        # ----------------------------------------------------
        # PERMISSIONS
        # ----------------------------------------------------

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
        }

        # ----------------------------------------------------
        # STAFF ROLE
        # ----------------------------------------------------

        staff_role_id = cfg.get(
            "ticket_staff_role"
        )

        if staff_role_id:

            staff_role = guild.get_role(
                int(staff_role_id)
            )

            if staff_role:

                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True
                )

        # ----------------------------------------------------
        # CREATE TICKET
        # ----------------------------------------------------

        try:

            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                category=category,
                topic=f"ticket:{interaction.user.id}",
                overwrites=overwrites,
                reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 ticket created"
            )

            embed = discord.Embed(
                title="🎫 Ticket Created",
                description=(
                    f"Welcome {interaction.user.mention}!\n\n"
                    "Please explain your issue and a staff member "
                    "will help you.\n\n"
                    "When finished, use the button below to close "
                    "this ticket."
                ),
                color=discord.Color.blurple()
            )

            await ticket_channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=TicketCloseButton()
            )

            await interaction.response.send_message(
                f"✅ Ticket created: "
                f"{ticket_channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I cannot create ticket channels. "
                "Give me **Manage Channels** permission.",
                ephemeral=True
            )

        except discord.HTTPException as error:
            print(
                f"❌ Ticket creation error: {error}"
            )

            await interaction.response.send_message(
                "❌ I couldn't create the ticket.",
                ephemeral=True
            )


# ============================================================
# 🔒 TICKET CLOSE BUTTON
# ============================================================

class TicketCloseButton(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="security_ticket_close"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.channel

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )
            return

        if not channel.topic:
            await interaction.response.send_message(
                "❌ This channel is not registered as a ticket.",
                ephemeral=True
            )
            return

        if not channel.topic.startswith(
            "ticket:"
        ):
            await interaction.response.send_message(
                "❌ This channel is not registered as a ticket.",
                ephemeral=True
            )
            return

        if not (
            interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "❌ You need **Manage Channels** to close this ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Closing ticket...",
            ephemeral=True
        )

        try:
            await channel.delete(
                reason=(
                    f"Ticket closed by "
                    f"{interaction.user}"
                )
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I cannot delete this ticket channel.",
                ephemeral=True
            )

        except discord.HTTPException:
            pass


# ============================================================
# 🎫 TICKET COMMAND GROUP
# ============================================================

ticket_group = app_commands.Group(
    name="ticket",
    description="Ticket system"
)

bot.tree.add_command(
    ticket_group
)


# ============================================================
# ⚙️ /ticket setup
# ============================================================

@ticket_group.command(
    name="setup",
    description="Configure the ticket system"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    category="Category where tickets will be created",
    staff_role="Optional staff role with ticket access"
)
async def ticket_setup(
    interaction: discord.Interaction,
    category: discord.CategoryChannel,
    staff_role: Optional[discord.Role] = None
):

    guild = interaction.guild

    if staff_role is not None:

        if staff_role.is_default():
            await interaction.response.send_message(
                "❌ You cannot use @everyone as the staff role.",
                ephemeral=True
            )
            return

        if staff_role.managed:
            await interaction.response.send_message(
                "❌ That role is managed by Discord.",
                ephemeral=True
            )
            return

    cfg = get_guild_config(
        guild.id
    )

    cfg["ticket_category"] = category.id

    if staff_role:
        cfg["ticket_staff_role"] = staff_role.id
    else:
        cfg["ticket_staff_role"] = None

    save_config()

    staff_text = (
        staff_role.mention
        if staff_role
        else "Not configured"
    )

    await interaction.response.send_message(
        f"✅ Ticket system configured!\n\n"
        f"📂 Category: {category.mention}\n"
        f"🛡️ Staff role: {staff_text}",
        ephemeral=True
    )


# ============================================================
# 📋 /ticket panel
# ============================================================

@ticket_group.command(
    name="panel",
    description="Send the ticket creation panel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    channel="Channel where the ticket panel will be sent"
)
async def ticket_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    if not cfg.get("ticket_category"):
        await interaction.response.send_message(
            "❌ Run `/ticket setup` first.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎫 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 Support",
        description=(
            "Need help?\n\n"
            "Click **Create Ticket** below to open "
            "a private support ticket."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 • Ticket System"
    )

    try:

        await channel.send(
            embed=embed,
            view=TicketCreateButton()
        )

        await interaction.response.send_message(
            f"✅ Ticket panel sent to {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot send messages in that channel.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the ticket panel.",
            ephemeral=True
        )


# ============================================================
# 🔒 /ticket close
# ============================================================

@ticket_group.command(
    name="close",
    description="Close the current ticket"
)
async def ticket_close(
    interaction: discord.Interaction
):

    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )
        return

    if not channel.topic or not channel.topic.startswith(
        "ticket:"
    ):
        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )
        return

    if not (
        interaction.user.guild_permissions.manage_channels
        or interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "❌ You need **Manage Channels** to close this ticket.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔒 Closing ticket...",
        ephemeral=True
    )

    try:

        await channel.delete(
            reason=(
                f"Ticket closed by "
                f"{interaction.user}"
            )
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I cannot delete this ticket channel.",
            ephemeral=True
        )

    except discord.HTTPException:
        pass


# ============================================================
# 🔐 END OF PART 5
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 6/13
# 🛡️ MODERATION SYSTEM
# ============================================================


# ============================================================
# ⚠️ WARNING STORAGE HELPER
# ============================================================

def get_warnings(
    guild_id: int,
    user_id: int
):
    cfg = get_guild_config(guild_id)

    warnings = cfg.setdefault("warnings", {})

    user_key = str(user_id)

    if user_key not in warnings:
        warnings[user_key] = []

    return warnings[user_key]


def save_warning(
    guild_id: int,
    user: discord.Member,
    moderator: discord.Member,
    reason: str
):

    cfg = get_guild_config(guild_id)

    warnings = cfg.setdefault(
        "warnings",
        {}
    )

    user_key = str(user.id)

    if user_key not in warnings:
        warnings[user_key] = []

    warnings[user_key].append({
        "reason": reason,
        "moderator": moderator.id,
        "timestamp": int(time.time())
    })

    save_config()

    return len(warnings[user_key])


# ============================================================
# 🧹 /clear
# ============================================================

@bot.tree.command(
    name="clear",
    description="Delete messages from this channel"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
@app_commands.describe(
    amount="Number of messages to delete (1-100)"
)
async def clear(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ This command can only be used in a text channel.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        deleted = await interaction.channel.purge(
            limit=amount
        )

        await interaction.followup.send(
            f"🧹 Deleted **{len(deleted)}** message(s).",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need **Manage Messages** permission.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord could not delete those messages.",
            ephemeral=True
        )


# ============================================================
# 👢 /kick
# ============================================================

@bot.tree.command(
    name="kick",
    description="Kick a member"
)
@app_commands.checks.has_permissions(
    kick_members=True
)
@app_commands.describe(
    member="Member to kick",
    reason="Reason for the kick"
)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    guild = interaction.guild

    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot kick yourself.",
            ephemeral=True
        )
        return

    if member == guild.me:
        await interaction.response.send_message(
            "❌ I cannot kick myself.",
            ephemeral=True
        )
        return

    if member.top_role >= interaction.user.top_role and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You cannot kick a member with an equal or higher role.",
            ephemeral=True
        )
        return

    if guild.me and member.top_role >= guild.me.top_role:
        await interaction.response.send_message(
            "❌ My highest role must be above that member.",
            ephemeral=True
        )
        return

    try:

        await member.kick(
            reason=f"{reason} | By {interaction.user}"
        )

        await interaction.response.send_message(
            f"👢 **{member}** was kicked.\n"
            f"📝 Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot kick that member.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the kick.",
            ephemeral=True
        )


# ============================================================
# 🔨 /ban
# ============================================================

@bot.tree.command(
    name="ban",
    description="Ban a member"
)
@app_commands.checks.has_permissions(
    ban_members=True
)
@app_commands.describe(
    member="Member to ban",
    reason="Reason for the ban"
)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    guild = interaction.guild

    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot ban yourself.",
            ephemeral=True
        )
        return

    if member == guild.me:
        await interaction.response.send_message(
            "❌ I cannot ban myself.",
            ephemeral=True
        )
        return

    if (
        member.top_role >= interaction.user.top_role
        and not interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "❌ You cannot ban a member with an equal or higher role.",
            ephemeral=True
        )
        return

    if guild.me and member.top_role >= guild.me.top_role:
        await interaction.response.send_message(
            "❌ My highest role must be above that member.",
            ephemeral=True
        )
        return

    try:

        await member.ban(
            reason=f"{reason} | By {interaction.user}"
        )

        await interaction.response.send_message(
            f"🔨 **{member}** was banned.\n"
            f"📝 Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot ban that member.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the ban.",
            ephemeral=True
        )


# ============================================================
# ⏱️ /timeout
# ============================================================

@bot.tree.command(
    name="timeout",
    description="Timeout a member"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
@app_commands.describe(
    member="Member to timeout",
    minutes="Timeout duration in minutes",
    reason="Reason for the timeout"
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason provided"
):

    guild = interaction.guild

    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot timeout yourself.",
            ephemeral=True
        )
        return

    if member == guild.me:
        await interaction.response.send_message(
            "❌ I cannot timeout myself.",
            ephemeral=True
        )
        return

    if (
        member.top_role >= interaction.user.top_role
        and not interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "❌ You cannot timeout a member with an equal or higher role.",
            ephemeral=True
        )
        return

    if guild.me and member.top_role >= guild.me.top_role:
        await interaction.response.send_message(
            "❌ My highest role must be above that member.",
            ephemeral=True
        )
        return

    try:

        until = discord.utils.utcnow() + timedelta(
            minutes=minutes
        )

        await member.edit(
            timed_out_until=until,
            reason=f"{reason} | By {interaction.user}"
        )

        await interaction.response.send_message(
            f"⏱️ **{member}** was timed out for "
            f"**{minutes} minute(s)**.\n"
            f"📝 Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot timeout that member.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the timeout.",
            ephemeral=True
        )


# ============================================================
# 🔓 /untimeout
# ============================================================

@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
@app_commands.describe(
    member="Member to untimeout",
    reason="Reason for removing the timeout"
)
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    guild = interaction.guild

    if (
        member.top_role >= interaction.user.top_role
        and not interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "❌ You cannot manage a member with an equal or higher role.",
            ephemeral=True
        )
        return

    if guild.me and member.top_role >= guild.me.top_role:
        await interaction.response.send_message(
            "❌ My highest role must be above that member.",
            ephemeral=True
        )
        return

    try:

        await member.edit(
            timed_out_until=None,
            reason=f"{reason} | By {interaction.user}"
        )

        await interaction.response.send_message(
            f"🔓 Timeout removed from **{member}**.\n"
            f"📝 Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot remove that timeout.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the request.",
            ephemeral=True
        )


# ============================================================
# ➕ /addrole
# ============================================================

@bot.tree.command(
    name="addrole",
    description="Give a role to a member"
)
@app_commands.checks.has_permissions(
    manage_roles=True
)
@app_commands.describe(
    member="Member who receives the role",
    role="Role to give"
)
async def addrole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):

    guild = interaction.guild

    can_manage, reason = bot_can_manage_role(
        guild,
        role
    )

    if not can_manage:
        await interaction.response.send_message(
            reason,
            ephemeral=True
        )
        return

    if role in member.roles:
        await interaction.response.send_message(
            f"ℹ️ {member.mention} already has {role.mention}.",
            ephemeral=True
        )
        return

    try:

        await member.add_roles(
            role,
            reason=f"Role added by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Added {role.mention} to {member.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot give that role. "
            "Make sure my highest role is above it.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the role change.",
            ephemeral=True
        )


# ============================================================
# ➖ /removerole
# ============================================================

@bot.tree.command(
    name="removerole",
    description="Remove a role from a member"
)
@app_commands.checks.has_permissions(
    manage_roles=True
)
@app_commands.describe(
    member="Member who loses the role",
    role="Role to remove"
)
async def removerole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):

    guild = interaction.guild

    can_manage, reason = bot_can_manage_role(
        guild,
        role
    )

    if not can_manage:
        await interaction.response.send_message(
            reason,
            ephemeral=True
        )
        return

    if role not in member.roles:
        await interaction.response.send_message(
            f"ℹ️ {member.mention} doesn't have {role.mention}.",
            ephemeral=True
        )
        return

    try:

        await member.remove_roles(
            role,
            reason=f"Role removed by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Removed {role.mention} from {member.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot remove that role.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the role change.",
            ephemeral=True
        )


# ============================================================
# ⚠️ /warn
# ============================================================

@bot.tree.command(
    name="warn",
    description="Warn a member"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
@app_commands.describe(
    member="Member to warn",
    reason="Reason for the warning"
)
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    guild = interaction.guild

    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot warn yourself.",
            ephemeral=True
        )
        return

    if (
        member.top_role >= interaction.user.top_role
        and not interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "❌ You cannot warn a member with an equal or higher role.",
            ephemeral=True
        )
        return

    total = save_warning(
        guild.id,
        member,
        interaction.user,
        reason
    )

    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned.\n"
        f"📝 Reason: {reason}\n"
        f"🔢 Total warnings: **{total}**"
    )


# ============================================================
# 📋 /warnings
# ============================================================

@bot.tree.command(
    name="warnings",
    description="View a member's warnings"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
@app_commands.describe(
    member="Member whose warnings you want to view"
)
async def warnings(
    interaction: discord.Interaction,
    member: discord.Member
):

    warning_list = get_warnings(
        interaction.guild.id,
        member.id
    )

    if not warning_list:
        await interaction.response.send_message(
            f"✅ **{member}** has no warnings.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"⚠️ Warnings — {member}",
        color=discord.Color.orange()
    )

    for index, warning in enumerate(
        warning_list[-10:],
        start=1
    ):

        moderator = interaction.guild.get_member(
            warning.get("moderator")
        )

        moderator_name = (
            moderator.mention
            if moderator
            else f"ID {warning.get('moderator')}"
        )

        timestamp = warning.get(
            "timestamp",
            0
        )

        embed.add_field(
            name=f"Warning #{index}",
            value=(
                f"📝 {warning.get('reason', 'No reason')}\n"
                f"👮 Moderator: {moderator_name}\n"
                f"🕐 <t:{timestamp}:R>"
            ),
            inline=False
        )

    embed.set_footer(
        text=f"Total warnings: {len(warning_list)}"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# 🔐 END OF PART 6
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 7/13
# 🧹 CLEANER
# ============================================================

@bot.tree.command(name="clearuser", description="Delete messages from a user")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(member="User whose messages to delete", amount="Maximum messages to scan")
async def clearuser(interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda m: m.author.id == member.id
        )
        await interaction.followup.send(
            f"🧹 Deleted **{len(deleted)}** message(s) from {member.mention}.",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ I need Manage Messages.", ephemeral=True)
    except discord.HTTPException:
        await interaction.followup.send("❌ Discord rejected the request.", ephemeral=True)


@bot.tree.command(name="clearbots", description="Delete messages sent by bots")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount="Maximum messages to scan")
async def clearbots(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda m: m.author.bot
        )
        await interaction.followup.send(
            f"🤖 Deleted **{len(deleted)}** bot message(s).",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ I need Manage Messages.", ephemeral=True)
    except discord.HTTPException:
        await interaction.followup.send("❌ Discord rejected the request.", ephemeral=True)


@bot.tree.command(name="clearlinks", description="Delete messages containing links")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount="Maximum messages to scan")
async def clearlinks(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    url_pattern = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda m: bool(url_pattern.search(m.content))
        )
        await interaction.followup.send(
            f"🔗 Deleted **{len(deleted)}** message(s) containing links.",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ I need Manage Messages.", ephemeral=True)
    except discord.HTTPException:
        await interaction.followup.send("❌ Discord rejected the request.", ephemeral=True)


@bot.tree.command(name="clearinvites", description="Delete Discord invite messages")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount="Maximum messages to scan")
async def clearinvites(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    invite_pattern = re.compile(
        r"(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)",
        re.IGNORECASE
    )

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda m: bool(invite_pattern.search(m.content))
        )
        await interaction.followup.send(
            f"📨 Deleted **{len(deleted)}** invite message(s).",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ I need Manage Messages.", ephemeral=True)
    except discord.HTTPException:
        await interaction.followup.send("❌ Discord rejected the request.", ephemeral=True)


@bot.tree.command(name="clearchannel", description="Delete and recreate the current channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def clearchannel(interaction: discord.Interaction):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        new_channel = await channel.clone(
            reason=f"Channel cleared by {interaction.user}"
        )
        await channel.delete(
            reason=f"Channel cleared by {interaction.user}"
        )
        await new_channel.send(
            f"🧹 Channel cleared by {interaction.user.mention}."
        )
    except discord.Forbidden:
        if not interaction.response.is_done():
            await interaction.followup.send("❌ I need Manage Channels.", ephemeral=True)
    except discord.HTTPException:
        pass


@bot.tree.command(name="slowmode", description="Set channel slowmode")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.describe(seconds="Slowmode seconds, 0 to disable")
async def slowmode(interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
        return

    try:
        await interaction.channel.edit(
            slowmode_delay=seconds,
            reason=f"Slowmode changed by {interaction.user}"
        )
        await interaction.response.send_message(
            f"🐌 Slowmode set to **{seconds} seconds**."
        )
    except discord.Forbidden:
        await interaction.response.send_message("❌ I need Manage Channels.", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("❌ Discord rejected the request.", ephemeral=True)


@bot.tree.command(name="lock", description="Lock the current channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
        return

    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            send_messages=False,
            reason=f"Channel locked by {interaction.user}"
        )
        await interaction.response.send_message("🔒 Channel locked.")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I need Manage Channels.", ephemeral=True)


@bot.tree.command(name="unlock", description="Unlock the current channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
        return

    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            send_messages=None,
            reason=f"Channel unlocked by {interaction.user}"
        )
        await interaction.response.send_message("🔓 Channel unlocked.")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I need Manage Channels.", ephemeral=True)


# ============================================================
# END OF PART 7
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 8/13
# ☢️ SERVER WIPE + 🔧 UTILITY
# ============================================================

@bot.tree.command(name="wipe", description="Wipe channels and categories from the server")
@app_commands.checks.has_permissions(administrator=True)
async def wipe(interaction: discord.Interaction):
    guild = interaction.guild

    await interaction.response.send_message(
        "☢️ Starting server wipe... The server itself will NOT be deleted.",
        ephemeral=True
    )

    deleted = 0

    for channel in list(guild.channels):
        try:
            await channel.delete(
                reason=f"Server wipe by {interaction.user}"
            )
            deleted += 1
        except (discord.Forbidden, discord.HTTPException):
            pass

    await interaction.followup.send(
        f"☢️ Wipe finished. Deleted **{deleted}** channels/categories.",
        ephemeral=True
    )


@bot.tree.command(name="ping", description="Show bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏓 Pong! **{round(bot.latency * 1000)}ms**"
    )


@bot.tree.command(name="serverinfo", description="Show server information")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color.blurple()
    )
    embed.add_field(name="👑 Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="👥 Members", value=str(guild.member_count or len(guild.members)), inline=True)
    embed.add_field(name="💬 Channels", value=str(len(guild.channels)), inline=True)
    embed.add_field(name="🎭 Roles", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="🆔 Server ID", value=str(guild.id), inline=True)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="userinfo", description="Show user information")
@app_commands.describe(member="Member to inspect")
async def userinfo(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user

    embed = discord.Embed(
        title=f"👤 {member}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🆔 ID", value=str(member.id), inline=False)
    embed.add_field(name="📅 Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown")
    embed.add_field(name="🎭 Roles", value=str(max(0, len(member.roles) - 1)))

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="avatar", description="Show a user's avatar")
@app_commands.describe(member="Member whose avatar you want")
async def avatar(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user

    embed = discord.Embed(
        title=f"🖼️ {member.display_name}'s Avatar",
        color=discord.Color.blurple()
    )
    embed.set_image(url=member.display_avatar.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="servericon", description="Show the server icon")
async def servericon(interaction: discord.Interaction):
    guild = interaction.guild

    if not guild.icon:
        await interaction.response.send_message(
            "❌ This server doesn't have an icon.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"🖼️ {guild.name}",
        color=discord.Color.blurple()
    )
    embed.set_image(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="botinfo", description="Show bot information")
async def botinfo(interaction: discord.Interaction):
    uptime = int(time.time() - bot.start_time)

    embed = discord.Embed(
        title="🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘",
        description="Protect • Moderate • Secure",
        color=discord.Color.blurple()
    )
    embed.add_field(name="🤖 Bot", value=str(bot.user), inline=True)
    embed.add_field(name="🌐 Servers", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="⏱️ Uptime", value=f"{uptime}s", inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="membercount", description="Create a live member-count channel")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.describe(channel_type="Choose the type of member-count channel")
@app_commands.choices(
    channel_type=[
        app_commands.Choice(name="Text Channel", value="text"),
        app_commands.Choice(name="Voice Channel", value="voice"),
        app_commands.Choice(name="Category", value="category")
    ]
)
async def membercount(
    interaction: discord.Interaction,
    channel_type: app_commands.Choice[str]
):
    guild = interaction.guild
    cfg = get_guild_config(guild.id)

    old_id = cfg.get("membercount_channel")

    if old_id:
        old_channel = guild.get_channel(int(old_id))
        if old_channel:
            try:
                await old_channel.delete(
                    reason="Replacing member count channel"
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

    count = await get_real_member_count(guild)
    name = f"👥・members・{count}"

    try:
        if channel_type.value == "text":
            channel = await guild.create_text_channel(
                name=name,
                reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 member count"
            )

        elif channel_type.value == "voice":
            channel = await guild.create_voice_channel(
                name=name,
                reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 member count"
            )

        else:
            channel = await guild.create_category(
                name=name,
                reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 member count"
            )

        cfg["membercount_channel"] = channel.id
        cfg["membercount_type"] = channel_type.value
        save_config()

        await interaction.response.send_message(
            f"✅ Created {channel_type.name}: {channel.mention if hasattr(channel, 'mention') else channel.name}\n"
            "👥 The name will update automatically.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I need Manage Channels permission.",
            ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord rejected the channel creation.",
            ephemeral=True
        )


async def update_membercount(guild: discord.Guild):
    cfg = get_guild_config(guild.id)
    channel_id = cfg.get("membercount_channel")

    if not channel_id:
        return

    channel = guild.get_channel(int(channel_id))

    if channel is None:
        return

    count = await get_real_member_count(guild)
    new_name = f"👥・members・{count}"

    try:
        if channel.name != new_name:
            await channel.edit(
                name=new_name,
                reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 automatic member count update"
            )
    except (discord.Forbidden, discord.HTTPException):
        pass


@bot.tree.command(name="channelinfo", description="Show channel information")
@app_commands.describe(channel="Channel to inspect")
async def channelinfo(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None
):
    channel = channel or interaction.channel

    await interaction.response.send_message(
        f"📋 **Channel Information**\n"
        f"Name: {channel.mention}\n"
        f"ID: `{channel.id}`\n"
        f"Category: `{channel.category.name if channel.category else 'None'}`"
    )


@bot.tree.command(name="roleinfo", description="Show role information")
@app_commands.describe(role="Role to inspect")
async def roleinfo(
    interaction: discord.Interaction,
    role: discord.Role
):
    await interaction.response.send_message(
        f"🎭 **Role Information**\n"
        f"Name: {role.mention}\n"
        f"ID: `{role.id}`\n"
        f"Members: **{len(role.members)}**\n"
        f"Position: **{role.position}**"
    )


@bot.tree.command(name="uptime", description="Show bot uptime")
async def uptime(interaction: discord.Interaction):
    seconds = int(time.time() - bot.start_time)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    await interaction.response.send_message(
        f"⏱️ Uptime: **{days}d {hours}h {minutes}m {seconds}s**"
    )


@bot.tree.command(name="security-status", description="Show SECURITY status")
async def security_status(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🔐 **𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 STATUS**\n"
        "🟢 Bot: Online\n"
        f"📡 Ping: {round(bot.latency * 1000)}ms\n"
        f"🌐 Servers: {len(bot.guilds)}"
    )


@bot.tree.command(name="say", description="Make the bot say something")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(message="Message to send")
async def say(interaction: discord.Interaction, message: str):
    if len(message) > 2000:
        await interaction.response.send_message("❌ Message too long.", ephemeral=True)
        return

    await interaction.response.send_message("✅ Sent.", ephemeral=True)
    await interaction.channel.send(message)


@bot.tree.command(name="announce", description="Send an announcement")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(message="Announcement text")
async def announce(interaction: discord.Interaction, message: str):
    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"By {interaction.user}")

    await interaction.response.send_message("✅ Announcement sent.", ephemeral=True)
    await interaction.channel.send(embed=embed)


@bot.tree.command(name="poll", description="Create a simple poll")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(question="Poll question")
async def poll(interaction: discord.Interaction, question: str):
    if len(question) > 1900:
        await interaction.response.send_message("❌ Question too long.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🗳️ Poll",
        description=question,
        color=discord.Color.blurple()
    )

    await interaction.response.send_message("✅ Poll created.", ephemeral=True)

    message = await interaction.channel.send(embed=embed)
    await message.add_reaction("👍")
    await message.add_reaction("👎")


# ============================================================
# END OF PART 8
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 9/13
# ⭐ LEVEL SYSTEM
# ============================================================

def xp_needed(level: int) -> int:
    return max(100, level * level * 100)


def get_user_xp_data(guild_id: int, user_id: int):
    cfg = get_guild_config(guild_id)

    xp_data = cfg.setdefault("xp", {})
    user_key = str(user_id)

    if user_key not in xp_data:
        xp_data[user_key] = {
            "xp": 0,
            "level": 0
        }

    return xp_data[user_key]


@bot.tree.command(name="rank", description="Show your rank")
@app_commands.describe(member="Member to check")
async def rank(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user
    data = get_user_xp_data(interaction.guild.id, member.id)

    await interaction.response.send_message(
        f"🏆 **{member.display_name}'s Rank**\n"
        f"⭐ Level: **{data['level']}**\n"
        f"✨ XP: **{data['xp']}**"
    )


@bot.tree.command(name="level", description="Show your level")
@app_commands.describe(member="Member to check")
async def level(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user
    data = get_user_xp_data(interaction.guild.id, member.id)

    await interaction.response.send_message(
        f"⭐ {member.mention} is level **{data['level']}** with **{data['xp']} XP**."
    )


@bot.tree.command(name="leaderboard", description="Show the XP leaderboard")
async def leaderboard(interaction: discord.Interaction):
    cfg = get_guild_config(interaction.guild.id)
    xp_data = cfg.get("xp", {})

    if not xp_data:
        await interaction.response.send_message(
            "⭐ No XP has been earned yet."
        )
        return

    ranked = sorted(
        xp_data.items(),
        key=lambda item: (
            item[1].get("level", 0),
            item[1].get("xp", 0)
        ),
        reverse=True
    )[:10]

    lines = []

    for index, (user_id, data) in enumerate(ranked, start=1):
        member = interaction.guild.get_member(int(user_id))
        name = member.display_name if member else f"User {user_id}"

        lines.append(
            f"**{index}.** {name} — Level **{data.get('level', 0)}** "
            f"• {data.get('xp', 0)} XP"
        )

    await interaction.response.send_message(
        "🏆 **XP LEADERBOARD**\n\n" + "\n".join(lines)
    )


@bot.tree.command(name="setlevelchannel", description="Set the level-up channel")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(channel="Level-up channel")
async def setlevelchannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    cfg = get_guild_config(interaction.guild.id)
    cfg["level_channel"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"✅ Level-up messages will be sent in {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(name="setlevelmessage", description="Set the level-up message")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(message="Use {user}, {level}, {server}")
async def setlevelmessage(
    interaction: discord.Interaction,
    message: str
):
    if len(message) > 2000:
        await interaction.response.send_message(
            "❌ Message too long.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(interaction.guild.id)
    cfg["level_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Level-up message updated.",
        ephemeral=True
    )


@bot.tree.command(name="togglelevels", description="Turn levels on or off")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(enabled="Enable or disable levels")
async def togglelevels(
    interaction: discord.Interaction,
    enabled: bool
):
    cfg = get_guild_config(interaction.guild.id)
    cfg["level_enabled"] = enabled
    save_config()

    await interaction.response.send_message(
        f"⭐ Levels are now **{'ON' if enabled else 'OFF'}**.",
        ephemeral=True
    )


@bot.tree.command(name="setlevel", description="Set a member's level")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(member="Member", level_number="Level")
async def setlevel(
    interaction: discord.Interaction,
    member: discord.Member,
    level_number: app_commands.Range[int, 0, 1000]
):
    data = get_user_xp_data(
        interaction.guild.id,
        member.id
    )

    data["level"] = level_number
    save_config()

    await interaction.response.send_message(
        f"✅ {member.mention} is now level **{level_number}**.",
        ephemeral=True
    )


@bot.tree.command(name="setxp", description="Set a member's XP")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(member="Member", xp_amount="XP amount")
async def setxp(
    interaction: discord.Interaction,
    member: discord.Member,
    xp_amount: app_commands.Range[int, 0, 100000000]
):
    data = get_user_xp_data(
        interaction.guild.id,
        member.id
    )

    data["xp"] = xp_amount
    save_config()

    await interaction.response.send_message(
        f"✅ {member.mention} now has **{xp_amount} XP**.",
        ephemeral=True
    )


@bot.tree.command(name="resetxp", description="Reset a member's XP")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(member="Member")
async def resetxp(
    interaction: discord.Interaction,
    member: discord.Member
):
    data = get_user_xp_data(
        interaction.guild.id,
        member.id
    )

    data["xp"] = 0
    data["level"] = 0

    save_config()

    await interaction.response.send_message(
        f"🔄 XP reset for {member.mention}.",
        ephemeral=True
    )


# ============================================================
# END OF PART 9
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 10/13
# 🎬 TIKTOK SHOWCASE
# ============================================================

class ShowcaseModal(discord.ui.Modal, title="🎬 Submit Your TikTok"):

    link = discord.ui.TextInput(
        label="TikTok URL",
        placeholder="https://www.tiktok.com/@user/video/...",
        required=True,
        max_length=500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        guild = interaction.guild
        cfg = get_guild_config(guild.id)

        if not cfg.get("showcase_enabled", False):
            await interaction.response.send_message(
                "❌ TikTok showcase is currently OFF.",
                ephemeral=True
            )
            return

        url = extract_tiktok_link(str(self.link))

        if not url:
            await interaction.response.send_message(
                "❌ Please submit a valid TikTok link.",
                ephemeral=True
            )
            return

        judge_channel_id = cfg.get(
            "showcase_judge_channel"
        )

        judge_channel = await get_configured_channel(
            guild,
            judge_channel_id
        )

        if not isinstance(
            judge_channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ The judge channel is not configured.",
                ephemeral=True
            )
            return

        judge_role_text = ""

        judge_role_id = cfg.get(
            "showcase_judge_role"
        )

        if judge_role_id:
            role = await get_configured_role(
                guild,
                judge_role_id
            )

            if role:
                judge_role_text = role.mention

        embed = discord.Embed(
            title="🎬 New TikTok Submission",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Submitted by",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="🔗 TikTok",
            value=url,
            inline=False
        )

        await judge_channel.send(
            content=judge_role_text,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                roles=True
            )
        )

        # Deliberately no public response/deletion.
        await interaction.response.send_message(
            "✅ Your TikTok was submitted!",
            ephemeral=True
        )


class ShowcaseButton(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Submit TikTok",
        emoji="🎬",
        style=discord.ButtonStyle.primary,
        custom_id="security_showcase_submit"
    )
    async def submit(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            ShowcaseModal()
        )


@bot.tree.command(
    name="showcase",
    description="TikTok showcase system"
)
async def showcase_command(
    interaction: discord.Interaction
):
    await interaction.response.send_message(
        "Use `/showcase setup`, `/showcase on`, `/showcase off`, "
        "`/showcase message`, or `/showcase panel`."
    )


showcase_group = app_commands.Group(
    name="showcase",
    description="TikTok showcase system"
)

# Remove the temporary command above before registering the group.
try:
    bot.tree.remove_command(
        "showcase",
        type=discord.AppCommandType.chat_input
    )
except Exception:
    pass

bot.tree.add_command(
    showcase_group
)


@showcase_group.command(
    name="setup",
    description="Configure TikTok showcase"
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    channel="Public showcase channel",
    judge_channel="Private judge channel",
    judge_role="Optional judge role"
)
async def showcase_setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    judge_channel: discord.TextChannel,
    judge_role: Optional[discord.Role] = None
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["showcase_channel"] = channel.id
    cfg["showcase_judge_channel"] = judge_channel.id
    cfg["showcase_judge_role"] = (
        judge_role.id if judge_role else None
    )

    save_config()

    await interaction.response.send_message(
        "✅ TikTok showcase configured.",
        ephemeral=True
    )


@showcase_group.command(
    name="on",
    description="Turn TikTok showcase on"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_on(
    interaction: discord.Interaction
):
    cfg = get_guild_config(interaction.guild.id)
    cfg["showcase_enabled"] = True
    save_config()

    await interaction.response.send_message(
        "🟢 TikTok showcase is now ON.",
        ephemeral=True
    )


@showcase_group.command(
    name="off",
    description="Turn TikTok showcase off"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_off(
    interaction: discord.Interaction
):
    cfg = get_guild_config(interaction.guild.id)
    cfg["showcase_enabled"] = False
    save_config()

    await interaction.response.send_message(
        "🔴 TikTok showcase is now OFF.",
        ephemeral=True
    )


@showcase_group.command(
    name="message",
    description="Set the showcase panel message"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_message(
    interaction: discord.Interaction,
    message: str
):
    if len(message) > 4000:
        await interaction.response.send_message(
            "❌ Message too long.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(interaction.guild.id)
    cfg["showcase_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Showcase message updated.",
        ephemeral=True
    )


@showcase_group.command(
    name="panel",
    description="Send the TikTok showcase panel"
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    channel="Channel where the panel will be sent"
)
async def showcase_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    cfg = get_guild_config(interaction.guild.id)

    if not cfg.get("showcase_judge_channel"):
        await interaction.response.send_message(
            "❌ Run `/showcase setup` first.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎬 TikTok Showcase",
        description=cfg.get(
            "showcase_message",
            "Submit your TikTok below! 🎬"
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=ShowcaseButton()
    )

    await interaction.response.send_message(
        f"✅ Showcase panel sent to {channel.mention}.",
        ephemeral=True
    )


# ============================================================
# END OF PART 10
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 11/13
# 💬 MESSAGE EVENTS + LEVEL XP
# ============================================================

@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        await bot.process_commands(message)
        return

    if message.guild is None:
        await bot.process_commands(message)
        return

    guild = message.guild
    cfg = get_guild_config(guild.id)

    # --------------------------------------------------------
    # ⭐ LEVEL XP
    # --------------------------------------------------------

    if cfg.get("level_enabled", True):

        data = get_user_xp_data(
            guild.id,
            message.author.id
        )

        gained = random.randint(5, 15)
        data["xp"] += gained

        current_level = data.get("level", 0)

        while data["xp"] >= xp_needed(
            current_level + 1
        ):
            current_level += 1
            data["level"] = current_level

            level_channel_id = cfg.get(
                "level_channel"
            )

            level_channel = await get_configured_channel(
                guild,
                level_channel_id
            )

            if isinstance(
                level_channel,
                discord.TextChannel
            ):
                text = cfg.get(
                    "level_message",
                    "GG {user}! You reached level **{level}**! 🎉"
                )

                text = (
                    text
                    .replace(
                        "{user}",
                        message.author.mention
                    )
                    .replace(
                        "{username}",
                        message.author.display_name
                    )
                    .replace(
                        "{server}",
                        guild.name
                    )
                    .replace(
                        "{level}",
                        str(current_level)
                    )
                )

                try:
                    await level_channel.send(text)
                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    pass

        data["level"] = current_level
        save_config()

    # --------------------------------------------------------
    # 🎬 TIKTOK DIRECT SUBMISSION
    # --------------------------------------------------------

    showcase_channel_id = cfg.get(
        "showcase_channel"
    )

    if (
        cfg.get("showcase_enabled", False)
        and showcase_channel_id
        and message.channel.id == int(showcase_channel_id)
    ):

        url = extract_tiktok_link(
            message.content
        )

        if url:

            judge_channel = await get_configured_channel(
                guild,
                cfg.get("showcase_judge_channel")
            )

            if isinstance(
                judge_channel,
                discord.TextChannel
            ):

                judge_role_text = ""

                role_id = cfg.get(
                    "showcase_judge_role"
                )

                if role_id:
                    role = await get_configured_role(
                        guild,
                        role_id
                    )

                    if role:
                        judge_role_text = role.mention

                embed = discord.Embed(
                    title="🎬 New TikTok Submission",
                    color=discord.Color.blurple()
                )

                embed.add_field(
                    name="👤 Submitted by",
                    value=message.author.mention,
                    inline=False
                )

                embed.add_field(
                    name="🔗 TikTok",
                    value=url,
                    inline=False
                )

                try:
                    await judge_channel.send(
                        content=judge_role_text,
                        embed=embed,
                        allowed_mentions=discord.AllowedMentions(
                            roles=True
                        )
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    pass

    await bot.process_commands(message)


# ============================================================
# END OF PART 11
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 12/13
# 👥 AUTOMATIC MEMBER COUNT
# ============================================================


# ============================================================
# 👤 MEMBER JOIN
# ============================================================
# NOTE:
# Part 3 already has the main on_member_join.
# This helper is called from Part 13's unified event setup.

async def handle_membercount_join(
    member: discord.Member
):
    await update_membercount(
        member.guild
    )


# ============================================================
# 👋 MEMBER LEAVE
# ============================================================

async def handle_membercount_leave(
    member: discord.Member
):
    await update_membercount(
        member.guild
    )


# ============================================================
# 🔄 PERIODIC MEMBER COUNT UPDATE
# ============================================================

async def membercount_loop():
    await bot.wait_until_ready()

    while not bot.is_closed():

        for guild in list(bot.guilds):

            try:
                await update_membercount(guild)
            except Exception as error:
                print(
                    f"❌ Member count update error "
                    f"in {guild.name}: {error}"
                )

        await asyncio.sleep(60)


membercount_task = None


# ============================================================
# END OF PART 12
# ============================================================
# ============================================================
# 🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — PART 13/13
# ❓ HELP + FINAL STARTUP
# ============================================================


# ============================================================
# ❓ /help
# ============================================================

@bot.tree.command(
    name="help",
    description="Show all SECURITY commands"
)
async def help_command(
    interaction: discord.Interaction
):

    text = """
╔══════════════════════════════════╗
║       🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 🔐           ║
║          COMMAND PANEL           ║
╚══════════════════════════════════╝

👋 **WELCOME**
`/welcome` `/welcome-on` `/welcome-off`
`/welcome-message` `/welcome-image` `/welcome-style`
`/welcome-role` `/welcome-role-off` `/testwelcome`

👋 **BYE**
`/bye` `/bye-on` `/bye-off`
`/bye-message` `/bye-image` `/bye-style` `/testbye`

✅ **VERIFICATION**
`/verifysetup` `/verify-message`
`/verify-panel` `/verify`

🎫 **TICKETS**
`/ticket setup` `/ticket panel` `/ticket close`

🛡️ **MODERATION**
`/clear` `/kick` `/ban` `/timeout` `/untimeout`
`/addrole` `/removerole` `/warn` `/warnings`

🧹 **CLEANER**
`/clearuser` `/clearbots` `/clearlinks`
`/clearinvites` `/clearchannel` `/slowmode`
`/lock` `/unlock`

☢️ **SERVER WIPE**
`/wipe`

🔧 **UTILITY**
`/ping` `/serverinfo` `/userinfo`
`/avatar` `/servericon` `/botinfo`
`/membercount` `/channelinfo` `/roleinfo`
`/uptime` `/security-status` `/say`
`/announce` `/poll`

⭐ **LEVEL SYSTEM**
`/rank` `/level` `/leaderboard`
`/setlevelchannel` `/setlevelmessage`
`/togglelevels` `/setlevel` `/setxp` `/resetxp`

🎬 **TIKTOK SHOWCASE**
`/showcase setup`
`/showcase on`
`/showcase off`
`/showcase message`
`/showcase panel`

❓ **HELP**
`/help`

╔══════════════════════════════════╗
║       🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 🔐           ║
║     PROTECT • MODERATE • SECURE  ║
╚══════════════════════════════════╝
"""

    await interaction.response.send_message(
        text,
        ephemeral=True
    )


# ============================================================
# 🔄 FINAL STARTUP HOOK
# ============================================================
# This replaces the simple setup_hook from Part 2.
# It registers ALL persistent buttons safely.

@bot.event
async def setup_hook():

    global membercount_task

    # --------------------------------------------------------
    # PERSISTENT BUTTONS
    # --------------------------------------------------------

    bot.add_view(
        VerifyButton()
    )

    bot.add_view(
        TicketCreateButton()
    )

    bot.add_view(
        TicketCloseButton()
    )

    bot.add_view(
        ShowcaseButton()
    )

    # --------------------------------------------------------
    # SYNC SLASH COMMANDS
    # --------------------------------------------------------

    try:
        synced = await bot.tree.sync()

        print(
            f"✅ Successfully synced "
            f"{len(synced)} slash command(s)."
        )

    except Exception as error:
        print(
            f"❌ Slash command sync failed: "
            f"{type(error).__name__}: {error}"
        )

    # --------------------------------------------------------
    # MEMBER COUNT LOOP
    # --------------------------------------------------------

    if membercount_task is None:
        membercount_task = asyncio.create_task(
            membercount_loop()
        )


# ============================================================
# 👤 FINAL MEMBER JOIN HANDLER
# ============================================================
# This replaces the Part 3 join handler so both welcome
# and member-count updates happen from ONE event.

@bot.event
async def on_member_join(
    member: discord.Member
):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    # --------------------------------------------------------
    # AUTO ROLE
    # --------------------------------------------------------

    role_id = cfg.get("auto_role")

    if role_id:

        role = await get_configured_role(
            guild,
            role_id
        )

        if role:

            can_manage, reason = bot_can_manage_role(
                guild,
                role
            )

            if can_manage:

                try:
                    await member.add_roles(
                        role,
                        reason="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 automatic welcome role"
                    )

                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    pass

            else:
                print(
                    f"❌ Auto-role: {reason}"
                )

    # --------------------------------------------------------
    # WELCOME
    # --------------------------------------------------------

    await send_welcome_message(
        member
    )

    # --------------------------------------------------------
    # MEMBER COUNT
    # --------------------------------------------------------

    await handle_membercount_join(
        member
    )


# ============================================================
# 👋 FINAL MEMBER LEAVE HANDLER
# ============================================================
# This replaces the Part 4 leave handler so bye + member
# count happen from ONE event.

@bot.event
async def on_member_remove(
    member: discord.Member
):

    await send_bye_message(
        member
    )

    await handle_membercount_leave(
        member
    )


# ============================================================
# 🟢 FINAL READY MESSAGE
# ============================================================

@bot.event
async def on_ready():

    print("========================================")
    print("🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 IS ONLINE!")
    print(f"🤖 Logged in as: {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Servers: {len(bot.guilds)}")
    print("🛡️ PROTECT • MODERATE • SECURE")
    print("========================================")


# ============================================================
# 🔐 START BOT
# ============================================================

bot.run(TOKEN)


_____________
End of Part 13
_____________
