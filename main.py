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

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ DISCORD_TOKEN is missing!")

CONFIG_FILE = "config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


config = load_config()


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)
    except Exception as error:
        print(f"Config save error: {error}")


def get_guild_config(guild_id):
    guild_id = str(guild_id)

    if guild_id not in config:
        config[guild_id] = {}

    cfg = config[guild_id]

    cfg.setdefault("welcome_enabled", True)
    cfg.setdefault("welcome_channel", None)
    cfg.setdefault(
        "welcome_message",
        "👋 Welcome {user} to **{server}**!"
    )
    cfg.setdefault("welcome_image", None)
    cfg.setdefault("welcome_style", "avatar")
    cfg.setdefault("welcome_role", None)

    cfg.setdefault("bye_enabled", True)
    cfg.setdefault("bye_channel", None)
    cfg.setdefault(
        "bye_message",
        "👋 **{username}** has left **{server}**."
    )
    cfg.setdefault("bye_image", None)
    cfg.setdefault("bye_style", "avatar")

    cfg.setdefault("verify_role", None)
    cfg.setdefault("verify_channel", None)
    cfg.setdefault(
        "verify_message",
        "✅ Click the button below to verify."
    )

    cfg.setdefault("ticket_category", None)
    cfg.setdefault("ticket_staff_role", None)

    cfg.setdefault("level_enabled", True)
    cfg.setdefault("level_channel", None)
    cfg.setdefault(
        "level_message",
        "🎉 GG {user}! You reached level **{level}**!"
    )
    cfg.setdefault("xp", {})

    cfg.setdefault("showcase_channel", None)
    cfg.setdefault("showcase_judge_channel", None)
    cfg.setdefault("showcase_judge_role", None)
    cfg.setdefault("showcase_enabled", False)
    cfg.setdefault(
        "showcase_message",
        "🎬 Submit your TikTok below!"
    )

    cfg.setdefault("membercount_channel", None)
    cfg.setdefault("membercount_type", None)

    save_config()
    return cfg


def format_message(message, member, guild):
    return (
        message
        .replace("{user}", member.mention)
        .replace("{username}", member.display_name)
        .replace("{server}", guild.name)
        .replace("{count}", str(guild.member_count or len(guild.members)))
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
class SecurityBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        self.start_time = time.time()


bot = SecurityBot()


@bot.tree.error
async def on_app_command_error(interaction, error):

    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ You don't have permission to use this command."

    elif isinstance(error, app_commands.BotMissingPermissions):
        message = "❌ I don't have the required permissions."

    elif isinstance(error, app_commands.CommandOnCooldown):
        message = "⏳ This command is on cooldown."

    else:
        print(f"Command error: {error}")
        message = "❌ An error occurred while running this command."

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
    except Exception:
        pass
def get_configured_channel(guild, channel_id):

    if not channel_id:
        return None

    channel = guild.get_channel(int(channel_id))

    if isinstance(channel, discord.TextChannel):
        return channel

    return None


def get_configured_role(guild, role_id):

    if not role_id:
        return None

    try:
        return guild.get_role(int(role_id))
    except Exception:
        return None


def bot_can_manage_role(guild, role):

    if role is None:
        return False

    if role.is_default():
        return False

    if role.managed:
        return False

    me = guild.me

    if me is None:
        return False

    return (
        me.guild_permissions.manage_roles
        and role < me.top_role
    )


def get_real_member_count(guild):

    if guild.member_count is not None:
        return guild.member_count

    return len(guild.members)


async def send_welcome_message(member):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    if not cfg.get("welcome_enabled", True):
        return

    channel = get_configured_channel(
        guild,
        cfg.get("welcome_channel")
    )

    if channel is None:
        return

    text = format_message(
        cfg.get("welcome_message"),
        member,
        guild
    )

    embed = discord.Embed(
        description=text,
        color=discord.Color.blurple()
    )

    style = cfg.get("welcome_style", "avatar")
    image = cfg.get("welcome_image")

    if style in ("avatar", "both"):
        embed.set_thumbnail(url=member.display_avatar.url)

    if style in ("custom", "both") and image:
        embed.set_image(url=image)

    try:
        await channel.send(embed=embed)
    except Exception as error:
        print(f"Welcome error: {error}")


async def send_bye_message(member):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    if not cfg.get("bye_enabled", True):
        return

    channel = get_configured_channel(
        guild,
        cfg.get("bye_channel")
    )

    if channel is None:
        return

    text = format_message(
        cfg.get("bye_message"),
        member,
        guild
    )

    embed = discord.Embed(
        description=text,
        color=discord.Color.red()
    )

    style = cfg.get("bye_style", "avatar")
    image = cfg.get("bye_image")

    if style in ("avatar", "both"):
        embed.set_thumbnail(url=member.display_avatar.url)

    if style in ("custom", "both") and image:
        embed.set_image(url=image)

    try:
        await channel.send(embed=embed)
    except Exception as error:
        print(f"Bye error: {error}")


@bot.tree.command(
    name="welcome",
    description="Configure the welcome channel"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["welcome_channel"] = channel.id
    cfg["welcome_enabled"] = True
    save_config()

    await interaction.response.send_message(
        f"✅ Welcome channel set to {channel.mention}"
    )


@bot.tree.command(
    name="welcome-on",
    description="Turn welcome messages on"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_on(interaction):

    cfg = get_guild_config(interaction.guild.id)
    cfg["welcome_enabled"] = True
    save_config()

    await interaction.response.send_message(
        "✅ Welcome messages are ON."
    )


@bot.tree.command(
    name="welcome-off",
    description="Turn welcome messages off"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_off(interaction):

    cfg = get_guild_config(interaction.guild.id)
    cfg["welcome_enabled"] = False
    save_config()

    await interaction.response.send_message(
        "✅ Welcome messages are OFF."
    )


@bot.tree.command(
    name="welcome-message",
    description="Change the welcome message"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_message(
    interaction,
    message: str
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["welcome_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Welcome message updated."
    )


@bot.tree.command(
    name="welcome-image",
    description="Set a custom welcome image"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_image(
    interaction,
    image_url: str
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["welcome_image"] = image_url
    save_config()

    await interaction.response.send_message(
        "✅ Welcome image updated."
    )


@bot.tree.command(
    name="welcome-style",
    description="Set welcome image style"
)
@app_commands.choices(style=[
    app_commands.Choice(name="Avatar", value="avatar"),
    app_commands.Choice(name="Custom Image", value="custom"),
    app_commands.Choice(name="Both", value="both")
])
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_style(
    interaction,
    style: app_commands.Choice[str]
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["welcome_style"] = style.value
    save_config()

    await interaction.response.send_message(
        f"✅ Welcome style set to **{style.name}**."
    )


@bot.tree.command(
    name="welcome-role",
    description="Automatically give a role to new members"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def welcome_role(
    interaction,
    role: discord.Role
):

    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ That role cannot be used.",
            ephemeral=True
        )
        return

    if not bot_can_manage_role(interaction.guild, role):
        await interaction.response.send_message(
            "❌ I cannot manage that role. Make sure my bot role is above it.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(interaction.guild.id)
    cfg["welcome_role"] = role.id
    save_config()

    await interaction.response.send_message(
        f"✅ New members will receive {role.mention}."
    )


@bot.tree.command(
    name="welcome-role-off",
    description="Disable automatic welcome role"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def welcome_role_off(interaction):

    cfg = get_guild_config(interaction.guild.id)
    cfg["welcome_role"] = None
    save_config()

    await interaction.response.send_message(
        "✅ Automatic welcome role disabled."
    )


@bot.tree.command(
    name="testwelcome",
    description="Test the welcome message"
)
async def testwelcome(interaction):

    await interaction.response.defer(ephemeral=True)

    await send_welcome_message(interaction.user)

    await interaction.followup.send(
        "✅ Welcome message tested.",
        ephemeral=True
    )


@bot.tree.command(
    name="bye",
    description="Configure the bye channel"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye(
    interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["bye_channel"] = channel.id
    cfg["bye_enabled"] = True
    save_config()

    await interaction.response.send_message(
        f"✅ Bye channel set to {channel.mention}"
    )


@bot.tree.command(
    name="bye-on",
    description="Turn bye messages on"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_on(interaction):

    cfg = get_guild_config(interaction.guild.id)
    cfg["bye_enabled"] = True
    save_config()

    await interaction.response.send_message(
        "✅ Bye messages are ON."
    )


@bot.tree.command(
    name="bye-off",
    description="Turn bye messages off"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_off(interaction):

    cfg = get_guild_config(interaction.guild.id)
    cfg["bye_enabled"] = False
    save_config()

    await interaction.response.send_message(
        "✅ Bye messages are OFF."
    )


@bot.tree.command(
    name="bye-message",
    description="Change the bye message"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_message(
    interaction,
    message: str
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["bye_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Bye message updated."
    )


@bot.tree.command(
    name="bye-image",
    description="Set a custom bye image"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_image(
    interaction,
    image_url: str
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["bye_image"] = image_url
    save_config()

    await interaction.response.send_message(
        "✅ Bye image updated."
    )


@bot.tree.command(
    name="bye-style",
    description="Set bye image style"
)
@app_commands.choices(style=[
    app_commands.Choice(name="Avatar", value="avatar"),
    app_commands.Choice(name="Custom Image", value="custom"),
    app_commands.Choice(name="Both", value="both")
])
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_style(
    interaction,
    style: app_commands.Choice[str]
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["bye_style"] = style.value
    save_config()

    await interaction.response.send_message(
        f"✅ Bye style set to **{style.name}**."
    )


@bot.tree.command(
    name="testbye",
    description="Test the bye message"
)
async def testbye(interaction):

    await interaction.response.send_message(
        "👋 Bye test message.",
        ephemeral=True
    )     


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
            return

        cfg = get_guild_config(guild.id)

        role = get_configured_role(
            guild,
            cfg.get("verify_role")
        )

        if role is None:
            await interaction.response.send_message(
                "❌ Verification role is not configured.",
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
            await interaction.user.add_roles(role)

            await interaction.response.send_message(
                "✅ You are now verified!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I cannot give you the verification role. "
                "Make sure my bot role is above the verification role.",
                ephemeral=True
            )


@bot.tree.command(
    name="verifysetup",
    description="Configure verification"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verifysetup(
    interaction,
    role: discord.Role,
    channel: discord.TextChannel
):

    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ That role cannot be used.",
            ephemeral=True
        )
        return

    if not bot_can_manage_role(interaction.guild, role):
        await interaction.response.send_message(
            "❌ I cannot manage that role. Put my bot role above it.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(interaction.guild.id)

    cfg["verify_role"] = role.id
    cfg["verify_channel"] = channel.id

    save_config()

    await interaction.response.send_message(
        f"✅ Verification configured.\n"
        f"Role: {role.mention}\n"
        f"Channel: {channel.mention}"
    )


@bot.tree.command(
    name="verify-message",
    description="Change verification message"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verify_message(
    interaction,
    message: str
):

    cfg = get_guild_config(interaction.guild.id)
    cfg["verify_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Verification message updated."
    )


@bot.tree.command(
    name="verify-panel",
    description="Send the verification panel"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verify_panel(interaction):

    cfg = get_guild_config(interaction.guild.id)

    channel = get_configured_channel(
        interaction.guild,
        cfg.get("verify_channel")
    )

    if channel is None:
        await interaction.response.send_message(
            "❌ Run `/verifysetup` first.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔐 Verification",
        description=cfg.get(
            "verify_message",
            "Click the button below to verify."
        ),
        color=discord.Color.green()
    )

    await channel.send(
        embed=embed,
        view=VerifyButton()
    )

    await interaction.response.send_message(
        f"✅ Verification panel sent to {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify",
    description="Verify yourself"
)
async def verify(interaction):

    cfg = get_guild_config(interaction.guild.id)

    role = get_configured_role(
        interaction.guild,
        cfg.get("verify_role")
    )

    if role is None:
        await interaction.response.send_message(
            "❌ Verification is not configured.",
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
        await interaction.user.add_roles(role)

        await interaction.response.send_message(
            "✅ You are now verified!",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot give you the verification role.",
            ephemeral=True
        )
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
        user = interaction.user

        if guild is None:
            return

        cfg = get_guild_config(guild.id)

        category = None

        if cfg.get("ticket_category"):
            category = guild.get_channel(
                int(cfg["ticket_category"])
            )

        for channel in guild.text_channels:

            if channel.topic == f"ticket:{user.id}":
                await interaction.response.send_message(
                    f"❌ You already have a ticket: {channel.mention}",
                    ephemeral=True
                )
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
        }

        staff_role = get_configured_role(
            guild,
            cfg.get("ticket_staff_role")
        )

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{user.name}",
                category=category,
                overwrites=overwrites,
                topic=f"ticket:{user.id}"
            )

            embed = discord.Embed(
                title="🎫 Support Ticket",
                description=(
                    f"Hello {user.mention}!\n\n"
                    "Please explain your issue here.\n"
                    "A staff member will help you soon."
                ),
                color=discord.Color.blurple()
            )

            await channel.send(
                embed=embed,
                view=TicketCloseButton()
            )

            await interaction.response.send_message(
                f"✅ Ticket created: {channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to create ticket channels.",
                ephemeral=True
            )


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

        if not (
            interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.manage_guild
        ):
            await interaction.response.send_message(
                "❌ You need Manage Channels to close this ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Closing ticket..."
        )

        await asyncio.sleep(2)

        try:
            await interaction.channel.delete(
                reason=f"Ticket closed by {interaction.user}"
            )
        except Exception:
            pass


ticket_group = app_commands.Group(
    name="ticket",
    description="Ticket system"
)

bot.tree.add_command(ticket_group)


@ticket_group.command(
    name="setup",
    description="Configure the ticket system"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_setup(
    interaction,
    category: discord.CategoryChannel,
    staff_role: discord.Role
):

    if staff_role.is_default() or staff_role.managed:
        await interaction.response.send_message(
            "❌ That staff role cannot be used.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(interaction.guild.id)

    cfg["ticket_category"] = category.id
    cfg["ticket_staff_role"] = staff_role.id

    save_config()

    await interaction.response.send_message(
        f"✅ Ticket system configured.\n"
        f"Category: {category.name}\n"
        f"Staff role: {staff_role.mention}"
    )


@ticket_group.command(
    name="panel",
    description="Send the ticket panel"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_panel(interaction):

    embed = discord.Embed(
        title="🎫 Support Tickets",
        description=(
            "Need help?\n\n"
            "Click **Create Ticket** below to open a private ticket."
        ),
        color=discord.Color.blurple()
    )

    await interaction.channel.send(
        embed=embed,
        view=TicketCreateButton()
    )

    await interaction.response.send_message(
        "✅ Ticket panel sent.",
        ephemeral=True
    )


@ticket_group.command(
    name="close",
    description="Close the current ticket"
)
async def ticket_close(interaction):

    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "❌ This is not a text channel.",
            ephemeral=True
        )
        return

    if not channel.topic or not channel.topic.startswith("ticket:"):
        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )
        return

    if not (
        interaction.user.guild_permissions.manage_channels
        or interaction.user.guild_permissions.manage_guild
    ):
        await interaction.response.send_message(
            "❌ You need Manage Channels to close this ticket.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔒 Closing ticket..."
    )

    await asyncio.sleep(2)

    try:
        await channel.delete()
    except Exception:
        pass
@bot.tree.command(
    name="clearuser",
    description="Delete messages from a user"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearuser(
    interaction,
    user: discord.Member,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(
        limit=amount,
        check=lambda message: message.author.id == user.id
    )

    await interaction.followup.send(
        f"🧹 Deleted **{len(deleted)}** messages from {user.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearbots",
    description="Delete bot messages"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearbots(
    interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(
        limit=amount,
        check=lambda message: message.author.bot
    )

    await interaction.followup.send(
        f"🧹 Deleted **{len(deleted)}** bot messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearlinks",
    description="Delete messages containing links"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearlinks(
    interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(ephemeral=True)

    def has_link(message):
        return bool(
            re.search(
                r"https?://\S+",
                message.content,
                re.IGNORECASE
            )
        )

    deleted = await interaction.channel.purge(
        limit=amount,
        check=has_link
    )

    await interaction.followup.send(
        f"🧹 Deleted **{len(deleted)}** messages containing links.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearinvites",
    description="Delete Discord invite messages"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearinvites(
    interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(ephemeral=True)

    def has_invite(message):
        return bool(
            re.search(
                r"(discord\.gg/|discord\.com/invite/)",
                message.content,
                re.IGNORECASE
            )
        )

    deleted = await interaction.channel.purge(
        limit=amount,
        check=has_invite
    )

    await interaction.followup.send(
        f"🧹 Deleted **{len(deleted)}** invite messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearchannel",
    description="Replace the current channel"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def clearchannel(interaction):

    old_channel = interaction.channel

    if not isinstance(old_channel, discord.TextChannel):
        await interaction.response.send_message(
            "❌ This command only works in text channels.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🧹 Recreating channel...",
        ephemeral=True
    )

    try:
        new_channel = await old_channel.clone(
            reason=f"Channel cleaned by {interaction.user}"
        )

        await old_channel.delete(
            reason=f"Channel cleaned by {interaction.user}"
        )

        await new_channel.send(
            "🧹 Channel cleaned successfully."
        )

    except Exception as error:
        print(f"Clear channel error: {error}")


@bot.tree.command(
    name="slowmode",
    description="Set channel slowmode"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(
    interaction,
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
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction):

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
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction):

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
    
@bot.tree.command(
    name="wipe",
    description="Delete all server channels and categories"
)
@app_commands.checks.has_permissions(administrator=True)
async def wipe(interaction):

    guild = interaction.guild

    await interaction.response.send_message(
        "☢️ **Server wipe started.** Deleting channels and categories...",
        ephemeral=True
    )

    deleted = 0

    for channel in list(guild.channels):

        try:
            await channel.delete(
                reason=f"Server wipe by {interaction.user}"
            )
            deleted += 1

        except Exception as error:
            print(
                f"Could not delete {channel}: {error}"
            )

    print(
        f"☢️ Wipe completed in {guild.name}. "
        f"Deleted {deleted} channels."
    )


@bot.tree.command(
    name="ping",
    description="Check bot latency"
)
async def ping(interaction):

    latency = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"🏓 Pong! **{latency}ms**"
    )


@bot.tree.command(
    name="serverinfo",
    description="Show server information"
)
async def serverinfo(interaction):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👑 Owner",
        value=f"<@{guild.owner_id}>",
        inline=True
    )

    embed.add_field(
        name="👥 Members",
        value=str(get_real_member_count(guild)),
        inline=True
    )

    embed.add_field(
        name="📁 Channels",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="🎭 Roles",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="🆔 Server ID",
        value=str(guild.id),
        inline=False
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="userinfo",
    description="Show user information"
)
async def userinfo(
    interaction,
    user: discord.Member = None
):

    user = user or interaction.user

    embed = discord.Embed(
        title=f"👤 {user.display_name}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    embed.add_field(
        name="Username",
        value=user.name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(user.id),
        inline=True
    )

    embed.add_field(
        name="Joined",
        value=discord.utils.format_dt(
            user.joined_at,
            "R"
        ) if user.joined_at else "Unknown",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="avatar",
    description="Show a user's avatar"
)
async def avatar(
    interaction,
    user: discord.Member = None
):

    user = user or interaction.user

    embed = discord.Embed(
        title=f"🖼️ {user.display_name}'s Avatar"
    )

    embed.set_image(
        url=user.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="servericon",
    description="Show the server icon"
)
async def servericon(interaction):

    guild = interaction.guild

    if not guild.icon:
        await interaction.response.send_message(
            "❌ This server has no icon.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"🖼️ {guild.name} Icon"
    )

    embed.set_image(
        url=guild.icon.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="botinfo",
    description="Show bot information"
)
async def botinfo(interaction):

    uptime = int(
        time.time() - bot.start_time
    )

    hours = uptime // 3600
    minutes = (uptime % 3600) // 60

    embed = discord.Embed(
        title="🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘",
        description="Protect • Moderate • Secure",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🏠 Servers",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="👥 Users",
        value=str(len(bot.users)),
        inline=True
    )

    embed.add_field(
        name="⏱️ Uptime",
        value=f"{hours}h {minutes}m",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="channelinfo",
    description="Show channel information"
)
async def channelinfo(interaction):

    channel = interaction.channel

    embed = discord.Embed(
        title=f"📺 #{channel.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="ID",
        value=str(channel.id),
        inline=True
    )

    embed.add_field(
        name="Type",
        value=str(channel.type),
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
    interaction,
    role: discord.Role
):

    embed = discord.Embed(
        title=f"🎭 {role.name}",
        color=role.color
    )

    embed.add_field(
        name="ID",
        value=str(role.id),
        inline=True
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

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="uptime",
    description="Show bot uptime"
)
async def uptime(interaction):

    seconds = int(
        time.time() - bot.start_time
    )

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    await interaction.response.send_message(
        f"⏱️ Uptime: **{days}d {hours}h {minutes}m**"
    )


@bot.tree.command(
    name="security-status",
    description="Show security bot status"
)
async def security_status(interaction):

    await interaction.response.send_message(
        "🔐 **𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 is online and protecting this server.** 🛡️"
    )


@bot.tree.command(
    name="say",
    description="Make the bot say something"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def say(
    interaction,
    message: str
):

    await interaction.response.send_message(
        "✅ Sent.",
        ephemeral=True
    )

    await interaction.channel.send(
        message
    )


@bot.tree.command(
    name="announce",
    description="Send an announcement"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def announce(
    interaction,
    message: str
):

    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"Sent by {interaction.user.display_name}"
    )

    await interaction.channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        "✅ Announcement sent.",
        ephemeral=True
    )


@bot.tree.command(
    name="poll",
    description="Create a simple yes/no poll"
)
async def poll(
    interaction,
    question: str
):

    message = await interaction.channel.send(
        f"📊 **Poll**\n\n{question}\n\n"
        "👍 = Yes\n"
        "👎 = No"
    )

    await message.add_reaction("👍")
    await message.add_reaction("👎")

    await interaction.response.send_message(
        "✅ Poll created.",
        ephemeral=True
    )
async def update_membercount(guild):

    cfg = get_guild_config(guild.id)

    channel_id = cfg.get("membercount_channel")
    channel_type = cfg.get("membercount_type")

    if not channel_id or not channel_type:
        return

    channel = guild.get_channel(
        int(channel_id)
    )

    count = get_real_member_count(guild)

    new_name = f"👥・members・{count}"

    if channel is None:
        return

    try:

        if channel_type == "text":
            if isinstance(channel, discord.TextChannel):
                await channel.edit(
                    name=new_name
                )

        elif channel_type == "voice":
            if isinstance(channel, discord.VoiceChannel):
                await channel.edit(
                    name=new_name
                )

        elif channel_type == "category":
            if isinstance(channel, discord.CategoryChannel):
                await channel.edit(
                    name=new_name
                )

    except Exception as error:
        print(
            f"Member count update error: {error}"
        )


@bot.tree.command(
    name="membercount",
    description="Create a live member count channel"
)
@app_commands.choices(channel_type=[
    app_commands.Choice(
        name="Text Channel",
        value="text"
    ),
    app_commands.Choice(
        name="Voice Channel",
        value="voice"
    ),
    app_commands.Choice(
        name="Category",
        value="category"
    )
])
@app_commands.checks.has_permissions(manage_channels=True)
async def membercount(
    interaction,
    channel_type: app_commands.Choice[str]
):

    guild = interaction.guild
    cfg = get_guild_config(guild.id)

    old_id = cfg.get("membercount_channel")

    if old_id:
        old_channel = guild.get_channel(
            int(old_id)
        )

        if old_channel:
            try:
                await old_channel.delete(
                    reason="Replacing member count channel"
                )
            except Exception as error:
                print(
                    f"Old member count deletion error: {error}"
                )

    count = get_real_member_count(guild)
    name = f"👥・members・{count}"

    try:

        if channel_type.value == "text":

            channel = await guild.create_text_channel(
                name=name
            )

        elif channel_type.value == "voice":

            channel = await guild.create_voice_channel(
                name=name
            )

        else:

            channel = await guild.create_category(
                name=name
            )

        cfg["membercount_channel"] = channel.id
        cfg["membercount_type"] = channel_type.value

        save_config()

        await interaction.response.send_message(
            f"✅ Member count created!\n"
            f"Type: **{channel_type.name}**\n"
            f"Members: **{count}**"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I need Manage Channels permission.",
            ephemeral=True
        )


async def handle_membercount_join(member):

    await update_membercount(
        member.guild
    )


async def handle_membercount_leave(member):

    await update_membercount(
        member.guild
    )


async def membercount_loop():

    await bot.wait_until_ready()

    while not bot.is_closed():

        for guild in list(bot.guilds):

            try:
                await update_membercount(guild)

            except Exception as error:
                print(
                    f"Member count loop error: {error}"
                )

        await asyncio.sleep(60)


membercount_task = None
def xp_needed(level):

    return 100 + ((level - 1) * 50)


def get_user_xp_data(guild_id, user_id):

    cfg = get_guild_config(guild_id)

    xp_data = cfg.setdefault("xp", {})

    user_id = str(user_id)

    if user_id not in xp_data:
        xp_data[user_id] = {
            "xp": 0,
            "level": 1
        }

    return xp_data[user_id]


@bot.tree.command(
    name="rank",
    description="Show your rank"
)
async def rank(
    interaction,
    user: discord.Member = None
):

    user = user or interaction.user

    data = get_user_xp_data(
        interaction.guild.id,
        user.id
    )

    needed = xp_needed(
        data["level"]
    )

    embed = discord.Embed(
        title=f"🏆 {user.display_name}'s Rank",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    embed.add_field(
        name="⭐ Level",
        value=str(data["level"]),
        inline=True
    )

    embed.add_field(
        name="✨ XP",
        value=f"{data['xp']} / {needed}",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="level",
    description="Show a user's level"
)
async def level(
    interaction,
    user: discord.Member = None
):

    user = user or interaction.user

    data = get_user_xp_data(
        interaction.guild.id,
        user.id
    )

    await interaction.response.send_message(
        f"⭐ {user.mention} is **Level {data['level']}** "
        f"with **{data['xp']} XP**."
    )


@bot.tree.command(
    name="leaderboard",
    description="Show the level leaderboard"
)
async def leaderboard(interaction):

    cfg = get_guild_config(
        interaction.guild.id
    )

    xp_data = cfg.get("xp", {})

    if not xp_data:
        await interaction.response.send_message(
            "📊 No XP data yet."
        )
        return

    sorted_users = sorted(
        xp_data.items(),
        key=lambda item: (
            item[1].get("level", 1),
            item[1].get("xp", 0)
        ),
        reverse=True
    )

    lines = []

    for index, (user_id, data) in enumerate(
        sorted_users[:10],
        start=1
    ):

        member = interaction.guild.get_member(
            int(user_id)
        )

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        lines.append(
            f"**{index}.** {name} — "
            f"Level {data.get('level', 1)} "
            f"({data.get('xp', 0)} XP)"
        )

    embed = discord.Embed(
        title="🏆 Level Leaderboard",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="setlevelchannel",
    description="Set the level-up channel"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setlevelchannel(
    interaction,
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
    description="Set the level-up message"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setlevelmessage(
    interaction,
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
    description="Turn levels on or off"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def togglelevels(interaction):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["level_enabled"] = not cfg.get(
        "level_enabled",
        True
    )

    save_config()

    status = (
        "ON"
        if cfg["level_enabled"]
        else "OFF"
    )

    await interaction.response.send_message(
        f"⭐ Levels are now **{status}**."
    )


@bot.tree.command(
    name="setlevel",
    description="Set a user's level"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setlevel(
    interaction,
    user: discord.Member,
    level_number: app_commands.Range[int, 1, 1000]
):

    data = get_user_xp_data(
        interaction.guild.id,
        user.id
    )

    data["level"] = level_number
    data["xp"] = 0

    save_config()

    await interaction.response.send_message(
        f"✅ {user.mention} is now Level **{level_number}**."
    )


@bot.tree.command(
    name="setxp",
    description="Set a user's XP"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setxp(
    interaction,
    user: discord.Member,
    xp: app_commands.Range[int, 0, 1000000]
):

    data = get_user_xp_data(
        interaction.guild.id,
        user.id
    )

    data["xp"] = xp

    while data["xp"] >= xp_needed(data["level"]):
        data["xp"] -= xp_needed(data["level"])
        data["level"] += 1

    save_config()

    await interaction.response.send_message(
        f"✅ {user.mention} now has "
        f"**{data['xp']} XP** at Level **{data['level']}**."
    )


@bot.tree.command(
    name="resetxp",
    description="Reset a user's XP"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def resetxp(
    interaction,
    user: discord.Member
):

    data = get_user_xp_data(
        interaction.guild.id,
        user.id
    )

    data["xp"] = 0
    data["level"] = 1

    save_config()

    await interaction.response.send_message(
        f"♻️ Reset XP for {user.mention}."
)
class ShowcaseModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="🎬 TikTok Showcase"
        )

        self.tiktok = discord.ui.TextInput(
            label="TikTok Link",
            placeholder="Paste your TikTok link here",
            required=True,
            max_length=500
        )

        self.description = discord.ui.TextInput(
            label="Description",
            placeholder="Tell us about your edit...",
            required=False,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )

        self.add_item(self.tiktok)
        self.add_item(self.description)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild
        cfg = get_guild_config(guild.id)

        link = extract_tiktok_link(
            self.tiktok.value
        )

        if not link:
            await interaction.response.send_message(
                "❌ Please provide a valid TikTok link.",
                ephemeral=True
            )
            return

        channel = get_configured_channel(
            guild,
            cfg.get("showcase_judge_channel")
        )

        if channel is None:
            channel = get_configured_channel(
                guild,
                cfg.get("showcase_channel")
            )

        if channel is None:
            await interaction.response.send_message(
                "❌ Showcase channel is not configured.",
                ephemeral=True
            )
            return

        judge_role = get_configured_role(
            guild,
            cfg.get("showcase_judge_role")
        )

        embed = discord.Embed(
            title="🎬 New TikTok Submission",
            description=(
                f"**Creator:** {interaction.user.mention}\n\n"
                f"**TikTok:** {link}\n\n"
                f"**Description:** "
                f"{self.description.value or 'No description'}"
            ),
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        content = (
            judge_role.mention
            if judge_role
            else None
        )

        await channel.send(
            content=content,
            embed=embed
        )

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

        cfg = get_guild_config(
            interaction.guild.id
        )

        if not cfg.get(
            "showcase_enabled",
            False
        ):
            await interaction.response.send_message(
                "❌ TikTok showcase is currently OFF.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            ShowcaseModal()
        )


showcase_group = app_commands.Group(
    name="showcase",
    description="TikTok showcase system"
)

bot.tree.add_command(showcase_group)


@showcase_group.command(
    name="setup",
    description="Configure TikTok showcase"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_setup(
    interaction,
    channel: discord.TextChannel,
    judge_channel: discord.TextChannel,
    judge_role: discord.Role
):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["showcase_channel"] = channel.id
    cfg["showcase_judge_channel"] = judge_channel.id
    cfg["showcase_judge_role"] = judge_role.id

    save_config()

    await interaction.response.send_message(
        "✅ TikTok showcase configured."
    )


@showcase_group.command(
    name="on",
    description="Turn TikTok showcase on"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_on(interaction):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["showcase_enabled"] = True

    save_config()

    await interaction.response.send_message(
        "🎬 TikTok showcase is **ON**."
    )


@showcase_group.command(
    name="off",
    description="Turn TikTok showcase off"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_off(interaction):

    cfg = get_guild_config(
        interaction.guild.id
    )

    cfg["showcase_enabled"] = False

    save_config()

    await interaction.response.send_message(
        "🎬 TikTok showcase is **OFF**."
    )


@showcase_group.command(
    name="message",
    description="Change showcase panel message"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_message(
    interaction,
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
    description="Send TikTok showcase panel"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_panel(interaction):

    cfg = get_guild_config(
        interaction.guild.id
    )

    channel = get_configured_channel(
        interaction.guild,
        cfg.get("showcase_channel")
    )

    if channel is None:
        await interaction.response.send_message(
            "❌ Run `/showcase setup` first.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎬 TikTok Showcase",
        description=cfg.get(
            "showcase_message",
            "Submit your TikTok below!"
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
@bot.tree.command(
    name="help",
    description="Show all SECURITY commands"
)
async def help_command(interaction):

    embed = discord.Embed(
        title="🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — COMMANDS",
        description="Protect • Moderate • Secure",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 WELCOME",
        value=(
            "`/welcome`\n"
            "`/welcome-on` `/welcome-off`\n"
            "`/welcome-message`\n"
            "`/welcome-image`\n"
            "`/welcome-style`\n"
            "`/welcome-role` `/welcome-role-off`\n"
            "`/testwelcome`"
        ),
        inline=False
    )

    embed.add_field(
        name="👋 BYE",
        value=(
            "`/bye`\n"
            "`/bye-on` `/bye-off`\n"
            "`/bye-message`\n"
            "`/bye-image`\n"
            "`/bye-style`\n"
            "`/testbye`"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ VERIFICATION",
        value=(
            "`/verifysetup`\n"
            "`/verify-message`\n"
            "`/verify-panel`\n"
            "`/verify`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 TICKETS",
        value=(
            "`/ticket setup`\n"
            "`/ticket panel`\n"
            "`/ticket close`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 CLEANER",
        value=(
            "`/clearuser` `/clearbots`\n"
            "`/clearlinks` `/clearinvites`\n"
            "`/clearchannel`\n"
            "`/slowmode`\n"
            "`/lock` `/unlock`"
        ),
        inline=False
    )

    embed.add_field(
        name="☢️ SERVER WIPE",
        value="`/wipe`",
        inline=False
    )

    embed.add_field(
        name="🔧 UTILITY",
        value=(
            "`/ping` `/serverinfo` `/userinfo`\n"
            "`/avatar` `/servericon` `/botinfo`\n"
            "`/channelinfo` `/roleinfo` `/uptime`\n"
            "`/security-status` `/say`\n"
            "`/announce` `/poll`"
        ),
        inline=False
    )

    embed.add_field(
        name="👥 MEMBER COUNT",
        value="`/membercount`",
        inline=False
    )

    embed.add_field(
        name="⭐ LEVELS",
        value=(
            "`/rank` `/level` `/leaderboard`\n"
            "`/setlevelchannel` `/setlevelmessage`\n"
            "`/togglelevels` `/setlevel`\n"
            "`/setxp` `/resetxp`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎬 TIKTOK SHOWCASE",
        value=(
            "`/showcase setup`\n"
            "`/showcase on` `/showcase off`\n"
            "`/showcase message`\n"
            "`/showcase panel`"
        ),
        inline=False
    )

    embed.set_footer(
        text="🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ==============================
# LEVEL + TIKTOK MESSAGE SYSTEM
# ==============================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    guild = message.guild

    if guild is None:
        await bot.process_commands(message)
        return

    cfg = get_guild_config(guild.id)

    # LEVEL SYSTEM
    if cfg.get("level_enabled", True):

        data = get_user_xp_data(
            guild.id,
            message.author.id
        )

        data["xp"] += random.randint(5, 15)

        leveled_up = False

        while data["xp"] >= xp_needed(data["level"]):

            data["xp"] -= xp_needed(data["level"])
            data["level"] += 1
            leveled_up = True

        if leveled_up:

            channel = get_configured_channel(
                guild,
                cfg.get("level_channel")
            )

            if channel:

                level_text = format_message(
                    cfg.get("level_message"),
                    message.author,
                    guild
                )

                level_text = level_text.replace(
                    "{level}",
                    str(data["level"])
                )

                try:
                    await channel.send(
                        level_text
                    )
                except Exception:
                    pass

        save_config()

    # TIKTOK DIRECT SUBMISSION
    if cfg.get("showcase_enabled", False):

        link = extract_tiktok_link(
            message.content
        )

        showcase_channel = get_configured_channel(
            guild,
            cfg.get("showcase_channel")
        )

        judge_channel = get_configured_channel(
            guild,
            cfg.get("showcase_judge_channel")
        )

        if (
            link
            and showcase_channel
            and judge_channel
            and message.channel.id == showcase_channel.id
        ):

            judge_role = get_configured_role(
                guild,
                cfg.get("showcase_judge_role")
            )

            embed = discord.Embed(
                title="🎬 New TikTok Submission",
                description=(
                    f"**Creator:** {message.author.mention}\n\n"
                    f"**TikTok:** {link}"
                ),
                color=discord.Color.blurple()
            )

            embed.set_thumbnail(
                url=message.author.display_avatar.url
            )

            content = (
                judge_role.mention
                if judge_role
                else None
            )

            try:
                await judge_channel.send(
                    content=content,
                    embed=embed
                )
            except Exception as error:
                print(
                    f"TikTok submission error: {error}"
                )

    await bot.process_commands(message)


# ==============================
# MEMBER JOIN / LEAVE
# ==============================

@bot.event
async def on_member_join(member):

    cfg = get_guild_config(
        member.guild.id
    )

    # AUTO ROLE
    role = get_configured_role(
        member.guild,
        cfg.get("welcome_role")
    )

    if role and bot_can_manage_role(
        member.guild,
        role
    ):

        try:
            await member.add_roles(
                role,
                reason="Automatic welcome role"
            )
        except Exception as error:
            print(
                f"Auto role error: {error}"
            )

    # WELCOME
    await send_welcome_message(member)

    # MEMBER COUNT
    await handle_membercount_join(member)


@bot.event
async def on_member_remove(member):

    # BYE
    await send_bye_message(member)

    # MEMBER COUNT
    await handle_membercount_leave(member)


# ==============================
# READY
# ==============================

_views_registered = False
_membercount_started = False


@bot.event
async def on_ready():

    global _views_registered
    global _membercount_started

    if not _views_registered:

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

        _views_registered = True

    if not _membercount_started:

        asyncio.create_task(
            membercount_loop()
        )

        _membercount_started = True

    try:

        await bot.tree.sync()

    except Exception as error:

        print(
            f"Command sync error: {error}"
        )

    print(
        f"🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 is online as {bot.user}"
    )


# ==============================
# START BOT
# ==============================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN environment variable is missing!"
    )


bot.run(TOKEN)

_____________
End of Part 11
_____________
