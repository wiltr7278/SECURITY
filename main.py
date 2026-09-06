# =========================
#        START PART 1
#        SECURITY BOT
# =========================

import discord
from discord import app_commands
from discord.ext import commands

import os
import json
import random
import re
import time

from datetime import timedelta
from typing import Optional


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ DISCORD_TOKEN is missing!")


CONFIG_FILE = "config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


config = load_config()


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except OSError as e:
        print(f"Config save error: {e}")


def get_guild_config(guild_id):
    guild_id = str(guild_id)

    if guild_id not in config:
        config[guild_id] = {}

    cfg = config[guild_id]

    # Welcome
    cfg.setdefault("welcome_enabled", True)
    cfg.setdefault("welcome_channel", None)
    cfg.setdefault(
        "welcome_message",
        "Welcome {user} to **{server}**! 🎉"
    )
    cfg.setdefault("welcome_image", None)
    cfg.setdefault("welcome_style", "avatar")
    cfg.setdefault("auto_role", None)

    # Bye
    cfg.setdefault("bye_enabled", True)
    cfg.setdefault("bye_channel", None)
    cfg.setdefault(
        "bye_message",
        "**{username}** has left **{server}**. 👋"
    )
    cfg.setdefault("bye_image", None)
    cfg.setdefault("bye_style", "avatar")

    # Verify
    cfg.setdefault("verify_role", None)
    cfg.setdefault("verify_channel", None)
    cfg.setdefault(
        "verify_message",
        "Click the button below to verify."
    )

    # Levels
    cfg.setdefault("level_enabled", True)
    cfg.setdefault("level_channel", None)
    cfg.setdefault(
        "level_message",
        "GG {user}! You reached level **{level}**! 🎉"
    )
    cfg.setdefault("xp", {})

    # Tickets
    cfg.setdefault("ticket_category", None)
    cfg.setdefault("ticket_staff_role", None)

    # Showcase
    cfg.setdefault("showcase_channel", None)
    cfg.setdefault("showcase_judge_channel", None)
    cfg.setdefault("showcase_judge_role", None)
    cfg.setdefault("showcase_enabled", False)
    cfg.setdefault(
        "showcase_message",
        "Submit your TikTok below! 🎬"
    )

    save_config()
    return cfg


def format_message(message, member, guild):
    return (
        message
        .replace("{user}", member.mention)
        .replace("{username}", member.display_name)
        .replace("{server}", guild.name)
        .replace("{count}", str(guild.member_count))
    )


def extract_tiktok_link(text):
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


intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# =========================
#         END PART 1
# =========================
# =========================
#        START PART 2
#       BOT CONFIGURATION
# =========================


class SecurityBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        self.start_time = time.time()
        self.views_loaded = False


bot = SecurityBot()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.MissingPermissions
    ):
        message = (
            "❌ You don't have permission "
            "to use this command."
        )

    elif isinstance(
        error,
        app_commands.BotMissingPermissions
    ):
        message = (
            "❌ I don't have the required "
            "permissions."
        )

    elif isinstance(
        error,
        app_commands.CommandOnCooldown
    ):
        message = (
            "⏳ This command is on cooldown."
        )

    else:
        print(
            f"Command error: {error}"
        )

        message = (
            "❌ An error occurred while "
            "running this command."
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


# =========================
#         END PART 2
# =========================
# =========================
#        START PART 3
#   WELCOME / AUTO ROLE / BYE
# =========================


async def send_welcome_message(
    channel,
    member
):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    message = format_message(
        cfg["welcome_message"],
        member,
        guild
    )

    embed = discord.Embed(
        description=message,
        color=discord.Color.green()
    )

    style = cfg.get(
        "welcome_style",
        "avatar"
    )

    image = cfg.get(
        "welcome_image"
    )

    if style in ("avatar", "both"):
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

    if style in ("custom", "both") and image:
        embed.set_image(
            url=image
        )

    await channel.send(embed=embed)


async def send_bye_message(
    channel,
    member
):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    message = format_message(
        cfg["bye_message"],
        member,
        guild
    )

    embed = discord.Embed(
        description=message,
        color=discord.Color.red()
    )

    style = cfg.get(
        "bye_style",
        "avatar"
    )

    image = cfg.get(
        "bye_image"
    )

    if style in ("avatar", "both"):
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

    if style in ("custom", "both") and image:
        embed.set_image(
            url=image
        )

    await channel.send(embed=embed)


# =========================
#          WELCOME
# =========================

@bot.tree.command(
    name="welcome",
    description="Set the welcome channel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def welcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_channel"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"✅ Welcome channel set to {channel.mention}."
    )


@bot.tree.command(
    name="welcome-on",
    description="Enable welcome messages"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def welcome_on(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_enabled"] = True
    save_config()

    await interaction.response.send_message(
        "✅ Welcome messages are **ON**."
    )


@bot.tree.command(
    name="welcome-off",
    description="Disable welcome messages"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def welcome_off(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_enabled"] = False
    save_config()

    await interaction.response.send_message(
        "✅ Welcome messages are **OFF**."
    )


@bot.tree.command(
    name="welcome-role",
    description="Set the automatic role"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def welcome_role(
    interaction: discord.Interaction,
    role: discord.Role
):

    guild = interaction.guild
    bot_member = guild.me

    if role.is_default():
        await interaction.response.send_message(
            "❌ You cannot use @everyone.",
            ephemeral=True
        )
        return

    if role.managed:
        await interaction.response.send_message(
            "❌ You cannot use a managed role.",
            ephemeral=True
        )
        return

    if bot_member is None:
        await interaction.response.send_message(
            "❌ I couldn't find my bot member.",
            ephemeral=True
        )
        return

    if role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ My bot role must be above that role.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(guild.id)

    cfg["auto_role"] = role.id
    save_config()

    await interaction.response.send_message(
        f"✅ Auto-role set to {role.mention}."
    )


@bot.tree.command(
    name="welcome-role-off",
    description="Disable automatic role"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def welcome_role_off(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["auto_role"] = None
    save_config()

    await interaction.response.send_message(
        "✅ Auto-role disabled."
    )


@bot.tree.command(
    name="welcome-message",
    description="Set the welcome message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def welcome_message(
    interaction: discord.Interaction,
    message: str
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Welcome message updated."
    )


@bot.tree.command(
    name="welcome-image",
    description="Set the welcome image"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def welcome_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["welcome_image"] = image.url
    save_config()

    await interaction.response.send_message(
        "✅ Welcome image updated."
    )


@bot.tree.command(
    name="welcome-style",
    description="Set welcome image style"
)
@app_commands.checks.has_permissions(
    manage_guild=True
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
            name="Both",
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
        f"✅ Welcome style set to **{style.name}**."
    )


@bot.tree.command(
    name="testwelcome",
    description="Test the welcome message"
)
async def testwelcome(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    channel_id = cfg.get(
        "welcome_channel"
    )

    channel = interaction.guild.get_channel(
        channel_id
    ) if channel_id else None

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        channel = interaction.channel

    await send_welcome_message(
        channel,
        interaction.user
    )

    await interaction.response.send_message(
        "✅ Welcome test sent.",
        ephemeral=True
    )


# =========================
#             BYE
# =========================

@bot.tree.command(
    name="bye",
    description="Set the goodbye channel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def bye(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["bye_channel"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"✅ Goodbye channel set to {channel.mention}."
    )


@bot.tree.command(
    name="bye-on",
    description="Enable goodbye messages"
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
        "✅ Goodbye messages are **ON**."
    )


@bot.tree.command(
    name="bye-off",
    description="Disable goodbye messages"
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
        "✅ Goodbye messages are **OFF**."
    )


@bot.tree.command(
    name="bye-message",
    description="Set the goodbye message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def bye_message(
    interaction: discord.Interaction,
    message: str
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["bye_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Goodbye message updated."
    )


@bot.tree.command(
    name="bye-image",
    description="Set the goodbye image"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def bye_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["bye_image"] = image.url
    save_config()

    await interaction.response.send_message(
        "✅ Goodbye image updated."
    )


@bot.tree.command(
    name="bye-style",
    description="Set goodbye image style"
)
@app_commands.checks.has_permissions(
    manage_guild=True
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
            name="Both",
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
        f"✅ Goodbye style set to **{style.name}**."
    )


@bot.tree.command(
    name="testbye",
    description="Test the goodbye message"
)
async def testbye(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    channel_id = cfg.get(
        "bye_channel"
    )

    channel = interaction.guild.get_channel(
        channel_id
    ) if channel_id else None

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        channel = interaction.channel

    await send_bye_message(
        channel,
        interaction.user
    )

    await interaction.response.send_message(
        "✅ Goodbye test sent.",
        ephemeral=True
    )


# =========================
#         END PART 3
# =========================
# =========================
#        START PART 4
#       VERIFY + TICKETS
# =========================


class VerifyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.success,
        emoji="✅",
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
                "❌ Server only.",
                ephemeral=True
            )
            return

        cfg = get_guild_config(guild.id)

        role_id = cfg.get("verify_role")

        if not role_id:
            await interaction.response.send_message(
                "❌ Verification isn't configured.",
                ephemeral=True
            )
            return

        role = guild.get_role(role_id)

        if role is None:
            await interaction.response.send_message(
                "❌ The verification role no longer exists.",
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
                "❌ I cannot give you the verification role. "
                "Move my bot role above the verification role.",
                ephemeral=True
            )


@bot.tree.command(
    name="verifysetup",
    description="Set the verification role"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def verifysetup(
    interaction: discord.Interaction,
    role: discord.Role
):

    guild = interaction.guild

    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ That role cannot be used.",
            ephemeral=True
        )
        return

    if guild.me and role >= guild.me.top_role:
        await interaction.response.send_message(
            "❌ My bot role must be above the verification role.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(guild.id)

    cfg["verify_role"] = role.id

    save_config()

    await interaction.response.send_message(
        f"✅ Verification role set to {role.mention}."
    )


@bot.tree.command(
    name="verify-message",
    description="Set the verification message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def verify_message(
    interaction: discord.Interaction,
    message: str
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["verify_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Verification message updated."
    )


@bot.tree.command(
    name="verify-panel",
    description="Send the verification panel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def verify_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    embed = discord.Embed(
        title="🛡️ Verification",
        description=cfg["verify_message"],
        color=discord.Color.green()
    )

    await channel.send(
        embed=embed,
        view=VerifyView()
    )

    cfg["verify_channel"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"✅ Verification panel sent to {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify",
    description="Verify a member manually"
)
@app_commands.checks.has_permissions(
    manage_roles=True
)
async def verify(
    interaction: discord.Interaction,
    member: discord.Member
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    role_id = cfg.get("verify_role")

    if not role_id:
        await interaction.response.send_message(
            "❌ Run `/verifysetup` first.",
            ephemeral=True
        )
        return

    role = interaction.guild.get_role(role_id)

    if role is None:
        await interaction.response.send_message(
            "❌ Verification role doesn't exist.",
            ephemeral=True
        )
        return

    try:
        await member.add_roles(
            role,
            reason="Manual SECURITY verification"
        )

        await interaction.response.send_message(
            f"✅ {member.mention} is verified."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot manage that role.",
            ephemeral=True
        )


# =========================
#           TICKETS
# =========================


class TicketCreateView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="security_ticket_create"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild

        if guild is None:
            return

        cfg = get_guild_config(guild.id)

        category_id = cfg.get(
            "ticket_category"
        )

        if not category_id:
            await interaction.response.send_message(
                "❌ Ticket system isn't configured.",
                ephemeral=True
            )
            return

        category = guild.get_channel(
            category_id
        )

        if not isinstance(
            category,
            discord.CategoryChannel
        ):
            await interaction.response.send_message(
                "❌ Ticket category no longer exists.",
                ephemeral=True
            )
            return

        for channel in guild.text_channels:

            if channel.topic == f"ticket:{interaction.user.id}":
                await interaction.response.send_message(
                    f"❌ You already have a ticket: {channel.mention}",
                    ephemeral=True
                )
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )
        }

        staff_role_id = cfg.get(
            "ticket_staff_role"
        )

        if staff_role_id:
            staff_role = guild.get_role(
                staff_role_id
            )

            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"ticket:{interaction.user.id}"
        )

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                "Please explain your issue here.\n"
                "A staff member will help you soon."
            ),
            color=discord.Color.blurple()
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=TicketCloseView()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )


class TicketCloseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
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
            return

        if not channel.topic or not channel.topic.startswith(
            "ticket:"
        ):
            await interaction.response.send_message(
                "❌ This isn't a SECURITY ticket.",
                ephemeral=True
            )
            return

        if not (
            interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "❌ You cannot close this ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Closing ticket..."
        )

        await channel.delete(
            reason=f"Ticket closed by {interaction.user}"
        )


ticket_group = app_commands.Group(
    name="ticket",
    description="Ticket system"
)

bot.tree.add_command(ticket_group)


@ticket_group.command(
    name="setup",
    description="Configure the ticket system"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def ticket_setup(
    interaction: discord.Interaction,
    category: discord.CategoryChannel,
    staff_role: Optional[discord.Role] = None
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["ticket_category"] = category.id
    cfg["ticket_staff_role"] = (
        staff_role.id
        if staff_role
        else None
    )

    save_config()

    staff_text = (
        staff_role.mention
        if staff_role
        else "Not set"
    )

    await interaction.response.send_message(
        "✅ Ticket system configured.\n"
        f"📂 Category: {category.mention}\n"
        f"👮 Staff role: {staff_text}"
    )


@ticket_group.command(
    name="panel",
    description="Send the ticket panel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def ticket_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    embed = discord.Embed(
        title="🎫 Support",
        description=(
            "Need help?\n\n"
            "Click the button below to create a private ticket."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=TicketCreateView()
    )

    await interaction.response.send_message(
        f"✅ Ticket panel sent to {channel.mention}.",
        ephemeral=True
    )


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
            "❌ This is not a text channel.",
            ephemeral=True
        )
        return

    if not channel.topic or not channel.topic.startswith(
        "ticket:"
    ):
        await interaction.response.send_message(
            "❌ This isn't a SECURITY ticket.",
            ephemeral=True
        )
        return

    if not (
        interaction.user.guild_permissions.manage_channels
        or interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "❌ You cannot close this ticket.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔒 Closing ticket..."
    )

    await channel.delete(
        reason=f"Ticket closed by {interaction.user}"
    )


# =========================
#         END PART 4
# =========================
# =========================
#        START PART 5
#         MODERATION
# =========================


@bot.tree.command(
    name="clear",
    description="Delete messages"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clear(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

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


@bot.tree.command(
    name="kick",
    description="Kick a member"
)
@app_commands.checks.has_permissions(
    kick_members=True
)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = "No reason provided"
):

    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot kick yourself.",
            ephemeral=True
        )
        return

    if member >= interaction.user:
        await interaction.response.send_message(
            "❌ You cannot kick someone with an equal or higher role.",
            ephemeral=True
        )
        return

    if interaction.guild.me and member >= interaction.guild.me:
        await interaction.response.send_message(
            "❌ My role is not high enough.",
            ephemeral=True
        )
        return

    await member.kick(reason=reason)

    await interaction.response.send_message(
        f"👢 {member.mention} was kicked.\nReason: {reason}"
    )


@bot.tree.command(
    name="ban",
    description="Ban a member"
)
@app_commands.checks.has_permissions(
    ban_members=True
)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = "No reason provided"
):

    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot ban yourself.",
            ephemeral=True
        )
        return

    if member >= interaction.user:
        await interaction.response.send_message(
            "❌ You cannot ban someone with an equal or higher role.",
            ephemeral=True
        )
        return

    if interaction.guild.me and member >= interaction.guild.me:
        await interaction.response.send_message(
            "❌ My role is not high enough.",
            ephemeral=True
        )
        return

    await member.ban(reason=reason)

    await interaction.response.send_message(
        f"🔨 {member.mention} was banned.\nReason: {reason}"
    )


@bot.tree.command(
    name="timeout",
    description="Timeout a member"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: Optional[str] = "No reason provided"
):

    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot timeout yourself.",
            ephemeral=True
        )
        return

    until = discord.utils.utcnow() + timedelta(
        minutes=minutes
    )

    await member.timeout(
        until,
        reason=reason
    )

    await interaction.response.send_message(
        f"⏳ {member.mention} timed out for **{minutes} minutes**."
    )


@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member
):

    await member.timeout(
        None,
        reason=f"Timeout removed by {interaction.user}"
    )

    await interaction.response.send_message(
        f"✅ Timeout removed from {member.mention}."
    )


@bot.tree.command(
    name="addrole",
    description="Give a role to a member"
)
@app_commands.checks.has_permissions(
    manage_roles=True
)
async def addrole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I cannot manage that role.",
            ephemeral=True
        )
        return

    await member.add_roles(
        role,
        reason=f"Role added by {interaction.user}"
    )

    await interaction.response.send_message(
        f"✅ Added {role.mention} to {member.mention}."
    )


@bot.tree.command(
    name="removerole",
    description="Remove a role from a member"
)
@app_commands.checks.has_permissions(
    manage_roles=True
)
async def removerole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I cannot manage that role.",
            ephemeral=True
        )
        return

    await member.remove_roles(
        role,
        reason=f"Role removed by {interaction.user}"
    )

    await interaction.response.send_message(
        f"✅ Removed {role.mention} from {member.mention}."
    )


@bot.tree.command(
    name="warn",
    description="Warn a member"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    warnings = cfg.setdefault(
        "warnings",
        {}
    )

    user_id = str(member.id)

    warnings.setdefault(
        user_id,
        []
    )

    warnings[user_id].append({
        "reason": reason,
        "moderator": interaction.user.id
    })

    save_config()

    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned.\n"
        f"Reason: {reason}"
    )


@bot.tree.command(
    name="warnings",
    description="View a member's warnings"
)
async def warnings(
    interaction: discord.Interaction,
    member: discord.Member
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    warning_data = cfg.get(
        "warnings",
        {}
    )

    user_warnings = warning_data.get(
        str(member.id),
        []
    )

    if not user_warnings:
        await interaction.response.send_message(
            f"✅ {member.mention} has no warnings."
        )
        return

    text = []

    for index, warning in enumerate(
        user_warnings,
        start=1
    ):
        text.append(
            f"**{index}.** {warning['reason']}"
        )

    embed = discord.Embed(
        title=f"⚠️ Warnings — {member.display_name}",
        description="\n".join(text),
        color=discord.Color.orange()
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#         END PART 5
# =========================
# =========================
#        START PART 6
#          CLEANER
# =========================


@bot.tree.command(
    name="clearuser",
    description="Delete messages from a member"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearuser(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    def check(message):
        return message.author.id == member.id

    deleted = await interaction.channel.purge(
        limit=amount,
        check=check
    )

    await interaction.followup.send(
        f"🧹 Deleted **{len(deleted)}** messages from {member.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearbots",
    description="Delete bot messages"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearbots(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    def check(message):
        return message.author.bot

    deleted = await interaction.channel.purge(
        limit=amount,
        check=check
    )

    await interaction.followup.send(
        f"🤖 Deleted **{len(deleted)}** bot messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearlinks",
    description="Delete messages containing links"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearlinks(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    def check(message):
        return (
            "http://" in message.content.lower()
            or "https://" in message.content.lower()
        )

    deleted = await interaction.channel.purge(
        limit=amount,
        check=check
    )

    await interaction.followup.send(
        f"🔗 Deleted **{len(deleted)}** link messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearinvites",
    description="Delete Discord invite messages"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearinvites(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    def check(message):
        return "discord.gg/" in message.content.lower()

    deleted = await interaction.channel.purge(
        limit=amount,
        check=check
    )

    await interaction.followup.send(
        f"📨 Deleted **{len(deleted)}** invite messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearchannel",
    description="Delete all recent messages"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearchannel(
    interaction: discord.Interaction
):

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await interaction.channel.purge(
        limit=None
    )

    await interaction.followup.send(
        f"🧹 Deleted **{len(deleted)}** messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="slowmode",
    description="Set channel slowmode"
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def slowmode(
    interaction: discord.Interaction,
    seconds: app_commands.Range[int, 0, 21600]
):

    await interaction.channel.edit(
        slowmode_delay=seconds
    )

    await interaction.response.send_message(
        f"🐢 Slowmode set to **{seconds} seconds**."
    )


@bot.tree.command(
    name="lock",
    description="Lock the current channel"
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def lock(
    interaction: discord.Interaction
):

    overwrite = interaction.channel.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = False

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await interaction.response.send_message(
        "🔒 Channel locked."
    )


@bot.tree.command(
    name="unlock",
    description="Unlock the current channel"
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def unlock(
    interaction: discord.Interaction
):

    overwrite = interaction.channel.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = None

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await interaction.response.send_message(
        "🔓 Channel unlocked."
    )


# =========================
#         END PART 6
# =========================
# =========================
#        START PART 7
#          UTILITY
# =========================


@bot.tree.command(
    name="ping",
    description="Check bot latency"
)
async def ping(
    interaction: discord.Interaction
):

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 Pong! **{latency}ms**"
    )


@bot.tree.command(
    name="serverinfo",
    description="Show server information"
)
async def serverinfo(
    interaction: discord.Interaction
):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color.blurple()
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="👑 Owner",
        value=f"<@{guild.owner_id}>",
        inline=True
    )

    embed.add_field(
        name="👥 Members",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="💬 Channels",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="🎭 Roles",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="😀 Emojis",
        value=str(len(guild.emojis)),
        inline=True
    )

    embed.add_field(
        name="🆔 ID",
        value=str(guild.id),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="userinfo",
    description="Show member information"
)
async def userinfo(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):

    member = member or interaction.user

    embed = discord.Embed(
        title=f"👤 {member.display_name}",
        color=member.color
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Username",
        value=member.name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Bot",
        value="Yes" if member.bot else "No",
        inline=True
    )

    embed.add_field(
        name="Created",
        value=discord.utils.format_dt(
            member.created_at,
            style="F"
        ),
        inline=False
    )

    if member.joined_at:
        embed.add_field(
            name="Joined",
            value=discord.utils.format_dt(
                member.joined_at,
                style="F"
            ),
            inline=False
        )

    roles = [
        role.mention
        for role in member.roles
        if role != interaction.guild.default_role
    ]

    embed.add_field(
        name="Roles",
        value=", ".join(roles) if roles else "None",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="avatar",
    description="Show a member's avatar"
)
async def avatar(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):

    member = member or interaction.user

    embed = discord.Embed(
        title=f"🖼️ {member.display_name}'s Avatar",
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="servericon",
    description="Show the server icon"
)
async def servericon(
    interaction: discord.Interaction
):

    guild = interaction.guild

    if not guild.icon:
        await interaction.response.send_message(
            "❌ This server has no icon.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"🖼️ {guild.name} Icon",
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=guild.icon.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="botinfo",
    description="Show SECURITY information"
)
async def botinfo(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🛡️ SECURITY",
        description="Discord server protection bot.",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=bot.user.display_avatar.url
    )

    embed.add_field(
        name="Servers",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="Latency",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )

    embed.add_field(
        name="Library",
        value="discord.py",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="membercount",
    description="Show member count"
)
async def membercount(
    interaction: discord.Interaction
):

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
        f"👥 **Total:** {guild.member_count}\n"
        f"👤 **Humans:** {humans}\n"
        f"🤖 **Bots:** {bots}"
    )


@bot.tree.command(
    name="channelinfo",
    description="Show channel information"
)
async def channelinfo(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None
):

    channel = channel or interaction.channel

    embed = discord.Embed(
        title=f"📺 #{channel.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="ID",
        value=str(channel.id),
        inline=False
    )

    embed.add_field(
        name="Slowmode",
        value=f"{channel.slowmode_delay}s",
        inline=True
    )

    embed.add_field(
        name="Category",
        value=channel.category.mention
        if channel.category
        else "None",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="roleinfo",
    description="Show role information"
)
async def roleinfo(
    interaction: discord.Interaction,
    role: discord.Role
):

    embed = discord.Embed(
        title=f"🎭 {role.name}",
        color=role.color
    )

    embed.add_field(
        name="ID",
        value=str(role.id),
        inline=False
    )

    embed.add_field(
        name="Members",
        value=str(len(role.members)),
        inline=True
    )

    embed.add_field(
        name="Position",
        value=str(role.position),
        inline=True
    )

    embed.add_field(
        name="Managed",
        value="Yes" if role.managed else "No",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#         END PART 7
# =========================
# =========================
#        START PART 8
#           WIPE
# =========================


class WipeView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(
        label="CONFIRM WIPE",
        style=discord.ButtonStyle.danger,
        emoji="💥",
        custom_id="security_wipe_confirm"
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Administrator only.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        await interaction.response.edit_message(
            content="🧹 **Wiping removable channels and roles...**",
            embed=None,
            view=None
        )

        deleted_channels = 0
        deleted_roles = 0

        # Delete channels/categories
        for channel in list(guild.channels):

            try:
                await channel.delete(
                    reason=f"SECURITY wipe by {interaction.user}"
                )
                deleted_channels += 1

            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

        # Delete roles
        if guild.me:

            bot_top_role = guild.me.top_role

            for role in list(guild.roles):

                # NEVER delete @everyone
                if role.is_default():
                    continue

                # NEVER delete managed roles
                if role.managed:
                    continue

                # NEVER attempt roles above/equal to bot
                if role >= bot_top_role:
                    continue

                try:
                    await role.delete(
                        reason=f"SECURITY wipe by {interaction.user}"
                    )
                    deleted_roles += 1

                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    pass

        await interaction.followup.send(
            "✅ **Wipe complete.**\n\n"
            f"🗑️ Channels deleted: **{deleted_channels}**\n"
            f"🎭 Roles deleted: **{deleted_roles}**\n\n"
            "🛡️ The Discord server itself was NOT deleted.\n"
            "👑 @everyone was NOT deleted.\n"
            "🔒 Managed/higher roles were NOT deleted."
        )


@bot.tree.command(
    name="wipe",
    description="Wipe removable channels and roles"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def wipe(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="⚠️ SERVER WIPE",
        description=(
            "This will attempt to delete:\n\n"
            "🗑️ All removable channels\n"
            "📂 All removable categories\n"
            "🎭 All removable roles\n\n"
            "❌ It will NOT delete the Discord server.\n"
            "❌ It will NOT delete @everyone.\n"
            "❌ It will NOT delete managed roles.\n"
            "❌ It will NOT delete roles above SECURITY."
        ),
        color=discord.Color.red()
    )

    await interaction.response.send_message(
        embed=embed,
        view=WipeView(),
        ephemeral=True
    )


# =========================
#         END PART 8
# =========================
# =========================
#        START PART 9
#          LEVELS
# =========================


def get_xp_data(guild, member):

    cfg = get_guild_config(
        guild.id
    )

    xp = cfg.setdefault(
        "xp",
        {}
    )

    user_id = str(member.id)

    if user_id not in xp:
        xp[user_id] = {
            "xp": 0,
            "level": 0
        }

    return xp[user_id]


def xp_needed(level):
    return 100 + (level * 50)


def calculate_level(xp):

    level = 0
    remaining = xp

    while remaining >= xp_needed(level):
        remaining -= xp_needed(level)
        level += 1

    return level


@bot.tree.command(
    name="rank",
    description="Show your rank"
)
async def rank(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):

    member = member or interaction.user

    data = get_xp_data(
        interaction.guild,
        member
    )

    embed = discord.Embed(
        title=f"🏆 {member.display_name}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="⭐ Level",
        value=str(data["level"]),
        inline=True
    )

    embed.add_field(
        name="✨ XP",
        value=str(data["xp"]),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="level",
    description="Show a member's level"
)
async def level(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):

    member = member or interaction.user

    data = get_xp_data(
        interaction.guild,
        member
    )

    await interaction.response.send_message(
        f"⭐ {member.mention} is **Level {data['level']}** "
        f"with **{data['xp']} XP**."
    )


@bot.tree.command(
    name="leaderboard",
    description="Show XP leaderboard"
)
async def leaderboard(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    xp_data = cfg.get(
        "xp",
        {}
    )

    if not xp_data:
        await interaction.response.send_message(
            "📊 No XP data yet."
        )
        return

    sorted_data = sorted(
        xp_data.items(),
        key=lambda x: (
            x[1].get("level", 0),
            x[1].get("xp", 0)
        ),
        reverse=True
    )

    lines = []

    for position, (user_id, data) in enumerate(
        sorted_data[:10],
        start=1
    ):

        member = interaction.guild.get_member(
            int(user_id)
        )

        name = (
            member.display_name
            if member
            else f"User {user_id}"
        )

        lines.append(
            f"**{position}.** {name} — "
            f"Level **{data.get('level', 0)}** "
            f"({data.get('xp', 0)} XP)"
        )

    embed = discord.Embed(
        title="🏆 XP Leaderboard",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="setlevelchannel",
    description="Set level-up channel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setlevelchannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["level_channel"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"✅ Level channel set to {channel.mention}."
    )


@bot.tree.command(
    name="setlevelmessage",
    description="Set level-up message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setlevelmessage(
    interaction: discord.Interaction,
    message: str
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["level_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Level-up message updated."
    )


@bot.tree.command(
    name="togglelevels",
    description="Enable or disable levels"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def togglelevels(
    interaction: discord.Interaction,
    enabled: bool
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["level_enabled"] = enabled
    save_config()

    await interaction.response.send_message(
        f"✅ Levels are now "
        f"**{'ON' if enabled else 'OFF'}**."
    )


@bot.tree.command(
    name="setlevel",
    description="Set a member's level"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setlevel(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 0, 100000]
):

    data = get_xp_data(
        interaction.guild,
        member
    )

    data["level"] = amount
    save_config()

    await interaction.response.send_message(
        f"✅ {member.mention}'s level is now **{amount}**."
    )


@bot.tree.command(
    name="setxp",
    description="Set a member's XP"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setxp(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 0, 100000000]
):

    data = get_xp_data(
        interaction.guild,
        member
    )

    data["xp"] = amount
    save_config()

    await interaction.response.send_message(
        f"✅ {member.mention}'s XP is now **{amount}**."
    )


@bot.tree.command(
    name="resetxp",
    description="Reset a member's XP"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def resetxp(
    interaction: discord.Interaction,
    member: discord.Member
):

    data = get_xp_data(
        interaction.guild,
        member
    )

    data["xp"] = 0
    data["level"] = 0

    save_config()

    await interaction.response.send_message(
        f"🔄 Reset XP for {member.mention}."
    )


# =========================
#         END PART 9
# =========================
# =========================
#        START PART 10
#       EXTRA COMMANDS
# =========================


@bot.tree.command(
    name="say",
    description="Make SECURITY send a message"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def say(
    interaction: discord.Interaction,
    message: str
):

    await interaction.response.send_message(
        "✅ Message sent.",
        ephemeral=True
    )

    await interaction.channel.send(
        message,
        allowed_mentions=discord.AllowedMentions(
            everyone=False,
            users=True,
            roles=True
        )
    )


@bot.tree.command(
    name="announce",
    description="Send an announcement"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def announce(
    interaction: discord.Interaction,
    title: str,
    message: str
):

    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"By {interaction.user.display_name}"
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="uptime",
    description="Show SECURITY uptime"
)
async def uptime(
    interaction: discord.Interaction
):

    seconds = int(
        time.time() - bot.start_time
    )

    days, remainder = divmod(
        seconds,
        86400
    )

    hours, remainder = divmod(
        remainder,
        3600
    )

    minutes, seconds = divmod(
        remainder,
        60
    )

    await interaction.response.send_message(
        f"⏱️ SECURITY uptime: "
        f"**{days}d {hours}h {minutes}m {seconds}s**"
    )


@bot.tree.command(
    name="security-status",
    description="Show SECURITY status"
)
async def security_status(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    embed = discord.Embed(
        title="🛡️ SECURITY STATUS",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🟢 Status",
        value="Online",
        inline=True
    )

    embed.add_field(
        name="🏓 Ping",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )

    embed.add_field(
        name="👋 Welcome",
        value="ON" if cfg["welcome_enabled"] else "OFF",
        inline=True
    )

    embed.add_field(
        name="🚪 Bye",
        value="ON" if cfg["bye_enabled"] else "OFF",
        inline=True
    )

    embed.add_field(
        name="⭐ Levels",
        value="ON" if cfg["level_enabled"] else "OFF",
        inline=True
    )

    embed.add_field(
        name="🎬 Showcase",
        value="ON" if cfg["showcase_enabled"] else "OFF",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="poll",
    description="Create a yes/no poll"
)
async def poll(
    interaction: discord.Interaction,
    question: str
):

    embed = discord.Embed(
        title="📊 Poll",
        description=question,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"Poll by {interaction.user.display_name}"
    )

    await interaction.response.send_message(
        embed=embed
    )

    message = await interaction.original_response()

    await message.add_reaction("👍")
    await message.add_reaction("👎")


# =========================
#         END PART 10
# =========================
# =========================
#        START PART 11
#   SHOWCASE + EVENTS + START
# =========================


class ShowcaseModal(
    discord.ui.Modal,
    title="🎬 Submit TikTok"
):

    tiktok_url = discord.ui.TextInput(
        label="TikTok URL",
        placeholder="https://www.tiktok.com/@user/video/123",
        required=True,
        max_length=500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        cfg = get_guild_config(
            guild.id
        )

        if not cfg["showcase_enabled"]:
            await interaction.response.send_message(
                "❌ TikTok Showcase is disabled.",
                ephemeral=True
            )
            return

        link = extract_tiktok_link(
            str(self.tiktok_url.value)
        )

        if not link:
            await interaction.response.send_message(
                "❌ Invalid TikTok link.",
                ephemeral=True
            )
            return

        judge_channel = guild.get_channel(
            cfg.get("showcase_judge_channel")
        )

        showcase_channel = guild.get_channel(
            cfg.get("showcase_channel")
        )

        if not isinstance(
            judge_channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ Judge channel is not configured.",
                ephemeral=True
            )
            return

        if isinstance(
            showcase_channel,
            discord.TextChannel
        ):

            public_embed = discord.Embed(
                title="🎬 TikTok Submission",
                description=(
                    f"Submitted by {interaction.user.mention}\n\n"
                    f"{link}"
                ),
                color=discord.Color.blurple()
            )

            await showcase_channel.send(
                embed=public_embed
            )

        judge_role_text = ""

        role_id = cfg.get(
            "showcase_judge_role"
        )

        if role_id:

            role = guild.get_role(
                role_id
            )

            if role:
                judge_role_text = role.mention

        judge_embed = discord.Embed(
            title="🎬 New TikTok For Review",
            description=(
                f"**User:** {interaction.user.mention}\n"
                f"**TikTok:** {link}"
            ),
            color=discord.Color.gold()
        )

        await judge_channel.send(
            content=judge_role_text,
            embed=judge_embed
        )

        await interaction.response.send_message(
            "✅ TikTok submitted!",
            ephemeral=True
        )


class ShowcaseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Submit TikTok",
        style=discord.ButtonStyle.primary,
        emoji="🎬",
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


showcase_group = app_commands.Group(
    name="showcase",
    description="TikTok showcase system"
)

bot.tree.add_command(
    showcase_group
)


@showcase_group.command(
    name="setup",
    description="Configure TikTok showcase"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_setup(
    interaction: discord.Interaction,
    showcase_channel: discord.TextChannel,
    judge_channel: discord.TextChannel,
    judge_role: discord.Role
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["showcase_channel"] = showcase_channel.id
    cfg["showcase_judge_channel"] = judge_channel.id
    cfg["showcase_judge_role"] = judge_role.id

    save_config()

    await interaction.response.send_message(
        "✅ Showcase configured.\n"
        f"🎬 Showcase: {showcase_channel.mention}\n"
        f"⚖️ Judge: {judge_channel.mention}\n"
        f"👮 Judge role: {judge_role.mention}"
    )


@showcase_group.command(
    name="on",
    description="Enable TikTok showcase"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_on(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    if not cfg["showcase_channel"]:
        await interaction.response.send_message(
            "❌ Run `/showcase setup` first.",
            ephemeral=True
        )
        return

    cfg["showcase_enabled"] = True
    save_config()

    await interaction.response.send_message(
        "✅ TikTok Showcase is **ON**."
    )


@showcase_group.command(
    name="off",
    description="Disable TikTok showcase"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_off(
    interaction: discord.Interaction
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["showcase_enabled"] = False
    save_config()

    await interaction.response.send_message(
        "✅ TikTok Showcase is **OFF**."
    )


@showcase_group.command(
    name="message",
    description="Set showcase panel message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_message(
    interaction: discord.Interaction,
    message: str
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["showcase_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Showcase message updated."
    )


@showcase_group.command(
    name="panel",
    description="Send showcase panel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    embed = discord.Embed(
        title="🎬 TikTok Showcase",
        description=cfg["showcase_message"],
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=ShowcaseView()
    )

    await interaction.response.send_message(
        f"✅ Showcase panel sent to {channel.mention}.",
        ephemeral=True
    )


# =========================
#       MEMBER JOIN
# =========================


@bot.event
async def on_member_join(
    member: discord.Member
):

    guild = member.guild
    cfg = get_guild_config(
        guild.id
    )

    # AUTO ROLE

    role_id = cfg.get(
        "auto_role"
    )

    if role_id:

        role = guild.get_role(
            role_id
        )

        if (
            role
            and guild.me
            and not role.is_default()
            and not role.managed
            and role < guild.me.top_role
        ):

            try:
                await member.add_roles(
                    role,
                    reason="SECURITY automatic role"
                )
            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

    # WELCOME

    if not cfg.get(
        "welcome_enabled",
        True
    ):
        return

    channel_id = cfg.get(
        "welcome_channel"
    )

    channel = guild.get_channel(
        channel_id
    ) if channel_id else None

    if isinstance(
        channel,
        discord.TextChannel
    ):

        try:
            await send_welcome_message(
                channel,
                member
            )
        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


# =========================
#       MEMBER LEAVE
# =========================


@bot.event
async def on_member_remove(
    member: discord.Member
):

    guild = member.guild

    cfg = get_guild_config(
        guild.id
    )

    if not cfg.get(
        "bye_enabled",
        True
    ):
        return

    channel_id = cfg.get(
        "bye_channel"
    )

    channel = guild.get_channel(
        channel_id
    ) if channel_id else None

    if isinstance(
        channel,
        discord.TextChannel
    ):

        try:
            await send_bye_message(
                channel,
                member
            )
        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


# =========================
#          MESSAGE
# =========================


@bot.event
async def on_message(
    message: discord.Message
):

    if message.author.bot:
        return

    guild = message.guild

    if guild:

        cfg = get_guild_config(
            guild.id
        )

        # LEVEL XP

        if cfg.get(
            "level_enabled",
            True
        ):

            data = get_xp_data(
                guild,
                message.author
            )

            old_level = data["level"]

            data["xp"] += random.randint(
                5,
                15
            )

            new_level = calculate_level(
                data["xp"]
            )

            if new_level > old_level:

                data["level"] = new_level

                channel_id = cfg.get(
                    "level_channel"
                )

                level_channel = guild.get_channel(
                    channel_id
                ) if channel_id else None

                if isinstance(
                    level_channel,
                    discord.TextChannel
                ):

                    text = format_message(
                        cfg["level_message"],
                        message.author,
                        guild
                    )

                    text = text.replace(
                        "{level}",
                        str(new_level)
                    )

                    try:
                        await level_channel.send(
                            text
                        )
                    except (
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        pass

            save_config()

        # TIKTOK AUTO FORWARD

        if cfg.get(
            "showcase_enabled",
            False
        ):

            link = extract_tiktok_link(
                message.content
            )

            if link:

                judge_channel = guild.get_channel(
                    cfg.get(
                        "showcase_judge_channel"
                    )
                )

                if isinstance(
                    judge_channel,
                    discord.TextChannel
                ):

                    role_text = ""

                    role_id = cfg.get(
                        "showcase_judge_role"
                    )

                    if role_id:

                        role = guild.get_role(
                            role_id
                        )

                        if role:
                            role_text = role.mention

                    embed = discord.Embed(
                        title="🎬 TikTok Submitted",
                        description=(
                            f"**Submitted by:** "
                            f"{message.author.mention}\n\n"
                            f"{link}"
                        ),
                        color=discord.Color.gold()
                    )

                    try:
                        await judge_channel.send(
                            content=role_text,
                            embed=embed
                        )
                    except (
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        pass

    await bot.process_commands(
        message
    )


# =========================
#           READY
# =========================


@bot.event
async def on_ready():

    if not bot.views_loaded:

        bot.add_view(
            VerifyView()
        )

        bot.add_view(
            TicketCreateView()
        )

        bot.add_view(
            TicketCloseView()
        )

        bot.add_view(
            ShowcaseView()
        )

        bot.views_loaded = True

    try:
        synced = await bot.tree.sync()

        print(
            f"✅ SECURITY online as {bot.user}"
        )

        print(
            f"📡 Servers: {len(bot.guilds)}"
        )

        print(
            f"🔧 Synced commands: {len(synced)}"
        )

    except Exception as e:

        print(
            f"❌ Command sync error: {e}"
        )


# =========================
#         END PART 11
# =========================
# =========================================================
# PART 12 — MEMBER COUNT
# =========================================================

MEMBERCOUNT_CHANNEL_KEY = "membercount_channel"
MEMBERCOUNT_TYPE_KEY = "membercount_type"


async def update_membercount(guild):
    cfg = get_guild_config(guild.id)

    channel_id = cfg.get(MEMBERCOUNT_CHANNEL_KEY)

    if not channel_id:
        return

    channel = guild.get_channel(int(channel_id))

    if channel is None:
        return

    member_count = guild.member_count or len(guild.members)
    new_name = f"👥・𝒎𝒆𝒎𝒃𝒆𝒓𝒔・{member_count}"

    try:
        if channel.name != new_name:
            await channel.edit(name=new_name)
    except (discord.Forbidden, discord.HTTPException):
        pass


@bot.tree.command(
    name="membercount",
    description="Create a member count channel"
)
@app_commands.describe(
    channel_type="Choose the type of member count channel"
)
@app_commands.choices(
    channel_type=[
        app_commands.Choice(name="Text Channel", value="text"),
        app_commands.Choice(name="Voice Channel", value="voice"),
        app_commands.Choice(name="Category", value="category")
    ]
)
@app_commands.default_permissions(manage_guild=True)
async def membercount(
    interaction: discord.Interaction,
    channel_type: app_commands.Choice[str]
):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used inside a server.",
            ephemeral=True
        )
        return

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "❌ You need **Manage Server** permission.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    cfg = get_guild_config(guild.id)
    member_count = guild.member_count or len(guild.members)

    old_channel_id = cfg.get(MEMBERCOUNT_CHANNEL_KEY)

    if old_channel_id:
        old_channel = guild.get_channel(int(old_channel_id))

        if old_channel:
            try:
                await old_channel.delete(
                    reason="Replacing member count channel"
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

    channel_name = f"👥・𝒎𝒆𝒎𝒃𝒆𝒓𝒔・{member_count}"

    try:
        if channel_type.value == "text":
            channel = await guild.create_text_channel(
                channel_name,
                reason="SECURITY member count"
            )

        elif channel_type.value == "voice":
            channel = await guild.create_voice_channel(
                channel_name,
                reason="SECURITY member count"
            )

        else:
            channel = await guild.create_category(
                channel_name,
                reason="SECURITY member count"
            )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need **Manage Channels** permission.",
            ephemeral=True
        )
        return

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord couldn't create the channel.",
            ephemeral=True
        )
        return

    cfg[MEMBERCOUNT_CHANNEL_KEY] = channel.id
    cfg[MEMBERCOUNT_TYPE_KEY] = channel_type.value
    save_config()

    await interaction.followup.send(
        f"✅ **Member Count Created!**\n\n"
        f"📁 Type: **{channel_type.name}**\n"
        f"👥 Members: **{member_count:,}**\n"
        f"🔄 The number will automatically update.",
        ephemeral=True
    )


# =========================================================
# _____________
# End of Part 12
# _____________
# =========================================================
# =========================
# HELP COMMAND
# =========================

@bot.tree.command(
    name="help",
    description="Show all SECURITY bot commands"
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🛡️ 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — Commands",
        description="Here are all available commands:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome & Auto Role",
        value=(
            "`/welcome` `/welcome-on` `/welcome-off`\n"
            "`/welcome-message` `/welcome-image` `/welcome-style`\n"
            "`/welcome-role` `/welcome-role-off` `/testwelcome`"
        ),
        inline=False
    )

    embed.add_field(
        name="👋 Bye",
        value=(
            "`/bye` `/bye-on` `/bye-off`\n"
            "`/bye-message` `/bye-image` `/bye-style` `/testbye`"
        ),
        inline=False
    )

    embed.add_field(
        name="🔐 Verification",
        value=(
            "`/verifysetup` `/verify-message`\n"
            "`/verify-panel` `/verify`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "`/ticket setup` `/ticket panel` `/ticket close`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "`/clear` `/kick` `/ban` `/timeout` `/untimeout`\n"
            "`/addrole` `/removerole` `/warn` `/warnings`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Cleaner",
        value=(
            "`/clearuser` `/clearbots` `/clearlinks`\n"
            "`/clearinvites` `/clearchannel` `/slowmode`\n"
            "`/lock` `/unlock`"
        ),
        inline=False
    )

    embed.add_field(
        name="💥 Server Wipe",
        value="`/wipe` — Removes removable server channels/categories/roles.",
        inline=False
    )

    embed.add_field(
        name="🔧 Utility",
        value=(
            "`/ping` `/serverinfo` `/userinfo` `/avatar`\n"
            "`/servericon` `/botinfo` `/membercount`\n"
            "`/channelinfo` `/roleinfo` `/uptime`\n"
            "`/security-status` `/say` `/announce` `/poll`"
        ),
        inline=False
    )

    embed.add_field(
        name="📈 Levels",
        value=(
            "`/rank` `/level` `/leaderboard`\n"
            "`/setlevelchannel` `/setlevelmessage` `/togglelevels`\n"
            "`/setlevel` `/setxp` `/resetxp`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎬 TikTok Showcase",
        value=(
            "`/showcase setup` `/showcase on` `/showcase off`\n"
            "`/showcase message` `/showcase panel`"
        ),
        inline=False
    )

    embed.add_field(
        name="❓ Help",
        value="`/help`",
        inline=False
    )

    embed.set_footer(
        text="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 • Security made simple 🛡️"
    )

    await interaction.response.send_message(embed=embed)


# =========================
# START BOT
# =========================

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing!")

bot.run(TOKEN)
