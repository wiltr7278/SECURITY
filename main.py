# =========================
#        START PART 1
# =========================

import discord
from discord import app_commands
from discord.ext import commands

from datetime import timedelta
from typing import Optional

import os
import json
import asyncio
import random
import re
import time


# =========================
#          TOKEN
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ DISCORD_TOKEN environment variable is missing!")


# =========================
#         CONFIG
# =========================

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

    # =========================
    # WELCOME
    # =========================

    cfg.setdefault("welcome_channel", None)
    cfg.setdefault("welcome_enabled", True)
    cfg.setdefault(
        "welcome_message",
        "Welcome {user} to **{server}**! 🎉"
    )
    cfg.setdefault("welcome_image", None)
    cfg.setdefault("welcome_style", "avatar")

    # =========================
    # AUTO ROLE
    # =========================

    cfg.setdefault("auto_role", None)

    # =========================
    # BYE
    # =========================

    cfg.setdefault("bye_channel", None)
    cfg.setdefault("bye_enabled", True)
    cfg.setdefault(
        "bye_message",
        "**{username}** has left **{server}**. 👋"
    )
    cfg.setdefault("bye_image", None)
    cfg.setdefault("bye_style", "avatar")

    save_config()

    return cfg


# =========================
#      MESSAGE FORMAT
# =========================

def format_message(message, member, guild):

    return (
        message
        .replace("{user}", member.mention)
        .replace("{username}", member.display_name)
        .replace("{server}", guild.name)
        .replace("{count}", str(guild.member_count))
    )


# =========================
#       TIKTOK LINK
# =========================

def extract_tiktok_link(text):

    pattern = (
        r"(https?://(?:www\.)?"
        r"(?:tiktok\.com|vm\.tiktok\.com|"
        r"vt\.tiktok\.com|m\.tiktok\.com)"
        r"[^\s<>]+)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1).rstrip(
            ".,!?)]}"
        )

    return None


# =========================
#          INTENTS
# =========================

intents = discord.Intents.default()

intents.members = True
intents.message_content = True


# =========================
#         END PART 1
# =========================
# =========================
#        START PART 2
# =========================

class SecurityBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        self.start_time = time.time()


bot = SecurityBot()


# =========================
#      ERROR HANDLER
# =========================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    if isinstance(
        error,
        app_commands.MissingPermissions
    ):
        message = "❌ You don't have permission to use this command."

    elif isinstance(
        error,
        app_commands.BotMissingPermissions
    ):
        message = "❌ I don't have the required permissions."

    elif isinstance(
        error,
        app_commands.CommandOnCooldown
    ):
        message = "⏳ This command is on cooldown. Try again later."

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

    except discord.HTTPException:
        pass


# =========================
#         END PART 2
# =========================
# =========================
#        START PART 3
# =========================

# =========================
#          WELCOME
# =========================

@bot.tree.command(name="welcome", description="Set the welcome channel")
@app_commands.describe(channel="Channel for welcome messages")
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
        f"✅ Welcome channel set to {channel.mention}",
        ephemeral=True
    )


@bot.tree.command(name="welcome-on", description="Enable welcome messages")
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_on(interaction: discord.Interaction):
    cfg = get_guild_config(interaction.guild.id)

    cfg["welcome_enabled"] = True
    save_config()

    await interaction.response.send_message(
        "✅ Welcome messages are now **ON**.",
        ephemeral=True
    )


@bot.tree.command(name="welcome-off", description="Disable welcome messages")
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_off(interaction: discord.Interaction):
    cfg = get_guild_config(interaction.guild.id)

    cfg["welcome_enabled"] = False
    save_config()

    await interaction.response.send_message(
        "❌ Welcome messages are now **OFF**.",
        ephemeral=True
    )


# =========================
#         AUTO ROLE
# =========================

@bot.tree.command(
    name="welcome-role",
    description="Set the role automatically given to new members"
)
@app_commands.describe(
    role="Role to give automatically when someone joins"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_role(
    interaction: discord.Interaction,
    role: discord.Role
):
    cfg = get_guild_config(interaction.guild.id)

    if role.is_default():
        await interaction.response.send_message(
            "❌ You cannot use the @everyone role.",
            ephemeral=True
        )
        return

    if role.managed:
        await interaction.response.send_message(
            "❌ You cannot use a managed/integration role.",
            ephemeral=True
        )
        return

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I can't give this role because it is higher than or equal to my highest role.\n"
            "Move my bot role above the role you want me to give.",
            ephemeral=True
        )
        return

    cfg["auto_role"] = role.id
    save_config()

    await interaction.response.send_message(
        f"✅ Auto-role set to {role.mention}.\n"
        "New members will automatically receive this role.",
        ephemeral=True
    )


@bot.tree.command(
    name="welcome-role-off",
    description="Disable the automatic member role"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_role_off(interaction: discord.Interaction):
    cfg = get_guild_config(interaction.guild.id)

    cfg["auto_role"] = None
    save_config()

    await interaction.response.send_message(
        "✅ Automatic role has been disabled.",
        ephemeral=True
    )


@bot.tree.command(
    name="welcome-message",
    description="Set the welcome message"
)
@app_commands.describe(message="Welcome message")
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_message(
    interaction: discord.Interaction,
    message: str
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["welcome_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Welcome message updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="welcome-image",
    description="Set the custom welcome image"
)
@app_commands.describe(image="Upload the welcome image")
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["welcome_image"] = image.url
    save_config()

    await interaction.response.send_message(
        "✅ Welcome image updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="welcome-style",
    description="Choose the welcome image style"
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
            name="Both",
            value="both"
        )
    ]
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["welcome_style"] = style.value
    save_config()

    await interaction.response.send_message(
        f"✅ Welcome style set to **{style.value}**.",
        ephemeral=True
    )


@bot.tree.command(
    name="testwelcome",
    description="Test the welcome message"
)
async def testwelcome(interaction: discord.Interaction):
    cfg = get_guild_config(interaction.guild.id)

    if not cfg.get("welcome_channel"):
        await interaction.response.send_message(
            "❌ Set a welcome channel first using `/welcome`.",
            ephemeral=True
        )
        return

    await send_welcome_message(
        interaction.guild,
        interaction.user,
        test_channel=interaction.channel
    )

    await interaction.response.send_message(
        "✅ Welcome test sent.",
        ephemeral=True
    )


# =========================
#            BYE
# =========================

@bot.tree.command(
    name="bye",
    description="Set the goodbye channel"
)
@app_commands.describe(
    channel="Channel for goodbye messages"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["bye_channel"] = channel.id
    cfg["bye_enabled"] = True
    save_config()

    await interaction.response.send_message(
        f"✅ Goodbye channel set to {channel.mention}",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-on",
    description="Enable goodbye messages"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_on(interaction: discord.Interaction):
    cfg = get_guild_config(interaction.guild.id)

    cfg["bye_enabled"] = True
    save_config()

    await interaction.response.send_message(
        "✅ Goodbye messages are now **ON**.",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-off",
    description="Disable goodbye messages"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_off(interaction: discord.Interaction):
    cfg = get_guild_config(interaction.guild.id)

    cfg["bye_enabled"] = False
    save_config()

    await interaction.response.send_message(
        "❌ Goodbye messages are now **OFF**.",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-message",
    description="Set the goodbye message"
)
@app_commands.describe(message="Goodbye message")
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_message(
    interaction: discord.Interaction,
    message: str
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["bye_message"] = message
    save_config()

    await interaction.response.send_message(
        "✅ Goodbye message updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-image",
    description="Set the custom goodbye image"
)
@app_commands.describe(image="Upload the goodbye image")
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["bye_image"] = image.url
    save_config()

    await interaction.response.send_message(
        "✅ Goodbye image updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-style",
    description="Choose the goodbye image style"
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
            name="Both",
            value="both"
        )
    ]
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["bye_style"] = style.value
    save_config()

    await interaction.response.send_message(
        f"✅ Goodbye style set to **{style.value}**.",
        ephemeral=True
    )


@bot.tree.command(
    name="testbye",
    description="Test the goodbye message"
)
async def testbye(interaction: discord.Interaction):
    cfg = get_guild_config(interaction.guild.id)

    if not cfg.get("bye_channel"):
        await interaction.response.send_message(
            "❌ Set a goodbye channel first using `/bye`.",
            ephemeral=True
        )
        return

    await send_bye_message(
        interaction.guild,
        interaction.user,
        test_channel=interaction.channel
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

# =========================
#           VERIFY
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
                "❌ This button can only be used inside a server.",
                ephemeral=True
            )
            return

        cfg = get_guild_config(guild.id)
        role_id = cfg.get("verify_role")

        if not role_id:
            await interaction.response.send_message(
                "❌ Verification has not been set up yet.",
                ephemeral=True
            )
            return

        role = guild.get_role(int(role_id))

        if role is None:
            await interaction.response.send_message(
                "❌ The verification role no longer exists.",
                ephemeral=True
            )
            return

        member = guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ I couldn't find your member information.",
                ephemeral=True
            )
            return

        if role in member.roles:
            await interaction.response.send_message(
                "✅ You are already verified!",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(
                role,
                reason="SECURITY verification"
            )

            await interaction.response.send_message(
                f"✅ You are now verified and received {role.mention}!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I can't give you the verification role. "
                "Make sure my bot role is above the verification role.",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Discord returned an error while giving the role.",
                ephemeral=True
            )


@bot.tree.command(
    name="verifysetup",
    description="Set up the verification role"
)
@app_commands.describe(
    role="Role members receive after verifying"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verifysetup(
    interaction: discord.Interaction,
    role: discord.Role
):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    if role.is_default():
        await interaction.response.send_message(
            "❌ You cannot use @everyone as the verification role.",
            ephemeral=True
        )
        return

    if role.managed:
        await interaction.response.send_message(
            "❌ You cannot use a managed/integration role.",
            ephemeral=True
        )
        return

    if guild.me and role >= guild.me.top_role:
        await interaction.response.send_message(
            "❌ My highest role must be above the verification role.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(guild.id)
    cfg["verify_role"] = role.id

    save_config()

    await interaction.response.send_message(
        f"✅ Verification role set to {role.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify-message",
    description="Set the verification message"
)
@app_commands.describe(
    message="Message shown in the verification panel"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verify_message(
    interaction: discord.Interaction,
    message: str
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["verify_message"] = message

    save_config()

    await interaction.response.send_message(
        "✅ Verification message updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify-panel",
    description="Send the verification panel"
)
@app_commands.describe(
    channel="Channel where the verification panel will be sent"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verify_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    guild = interaction.guild
    cfg = get_guild_config(guild.id)

    if not cfg.get("verify_role"):
        await interaction.response.send_message(
            "❌ Run `/verifysetup @role` first.",
            ephemeral=True
        )
        return

    role = guild.get_role(
        int(cfg["verify_role"])
    )

    if role is None:
        await interaction.response.send_message(
            "❌ The verification role no longer exists.",
            ephemeral=True
        )
        return

    cfg["verify_channel"] = channel.id
    save_config()

    embed = discord.Embed(
        title="🛡️ Verification",
        description=cfg.get(
            "verify_message",
            "Click the button below to verify."
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text="SECURITY • Verification System"
    )

    try:
        await channel.send(
            embed=embed,
            view=VerifyView()
        )

        await interaction.response.send_message(
            f"✅ Verification panel sent to {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to send messages in that channel.",
            ephemeral=True
        )


@bot.tree.command(
    name="verify",
    description="Manually give a member the verification role"
)
@app_commands.describe(
    member="Member to verify"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def verify(
    interaction: discord.Interaction,
    member: discord.Member
):
    guild = interaction.guild
    cfg = get_guild_config(guild.id)

    role_id = cfg.get("verify_role")

    if not role_id:
        await interaction.response.send_message(
            "❌ Verification has not been set up.",
            ephemeral=True
        )
        return

    role = guild.get_role(int(role_id))

    if role is None:
        await interaction.response.send_message(
            "❌ The verification role no longer exists.",
            ephemeral=True
        )
        return

    if guild.me and role >= guild.me.top_role:
        await interaction.response.send_message(
            "❌ My bot role must be above the verification role.",
            ephemeral=True
        )
        return

    try:
        await member.add_roles(
            role,
            reason=f"Manual verification by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ {member.mention} has been verified.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to give that role.",
            ephemeral=True
        )


# =========================
#           TICKET
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
        member = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "❌ This can only be used in a server.",
                ephemeral=True
            )
            return

        cfg = get_guild_config(guild.id)

        category_id = cfg.get("ticket_category")

        if not category_id:
            await interaction.response.send_message(
                "❌ Tickets have not been set up yet.",
                ephemeral=True
            )
            return

        category = guild.get_channel(
            int(category_id)
        )

        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "❌ The configured ticket category no longer exists.",
                ephemeral=True
            )
            return

        # Prevent duplicate tickets
        for channel in guild.text_channels:
            if channel.topic == f"ticket:{member.id}":
                await interaction.response.send_message(
                    f"❌ You already have a ticket: {channel.mention}",
                    ephemeral=True
                )
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )
        }

        staff_role_id = cfg.get("ticket_staff_role")

        if staff_role_id:
            staff_role = guild.get_role(
                int(staff_role_id)
            )

            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True
                )

        try:
            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{member.name}".lower()[:90],
                category=category,
                overwrites=overwrites,
                topic=f"ticket:{member.id}",
                reason="SECURITY ticket creation"
            )

            embed = discord.Embed(
                title="🎫 Support Ticket",
                description=(
                    f"Welcome {member.mention}!\n\n"
                    "Please explain your issue here.\n"
                    "A staff member will help you shortly."
                ),
                color=discord.Color.blurple()
            )

            await ticket_channel.send(
                content=member.mention,
                embed=embed,
                view=TicketCloseView()
            )

            await interaction.response.send_message(
                f"✅ Your ticket has been created: "
                f"{ticket_channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to create ticket channels.",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Discord returned an error while creating the ticket.",
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

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )
            return

        if not channel.topic or not channel.topic.startswith("ticket:"):
            await interaction.response.send_message(
                "❌ This is not a SECURITY ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Closing ticket...",
            ephemeral=True
        )

        await asyncio.sleep(2)

        try:
            await channel.delete(
                reason=f"Ticket closed by {interaction.user}"
            )

        except discord.Forbidden:
            pass

        except discord.HTTPException:
            pass


@bot.tree.command(
    name="ticket",
    description="Ticket system"
)
@app_commands.describe(
    action="Choose a ticket action"
)
@app_commands.choices(
    action=[
        app_commands.Choice(
            name="setup",
            value="setup"
        ),
        app_commands.Choice(
            name="panel",
            value="panel"
        ),
        app_commands.Choice(
            name="close",
            value="close"
        )
    ]
)
async def ticket(
    interaction: discord.Interaction,
    action: app_commands.Choice[str]
):
    # This base command exists only to provide
    # the /ticket command group structure.
    #
    # The actual ticket setup/panel/close commands
    # are added separately below.

    await interaction.response.send_message(
        "Use `/ticket setup`, `/ticket panel`, or `/ticket close`.",
        ephemeral=True
    )


# =========================
#     TICKET SETUP
# =========================

@bot.tree.command(
    name="ticket-setup",
    description="Configure the ticket system"
)
@app_commands.describe(
    category="Category where tickets will be created",
    staff_role="Optional staff role that can see tickets"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_setup(
    interaction: discord.Interaction,
    category: discord.CategoryChannel,
    staff_role: Optional[discord.Role] = None
):
    cfg = get_guild_config(interaction.guild.id)

    cfg["ticket_category"] = category.id
    cfg["ticket_staff_role"] = (
        staff_role.id if staff_role else None
    )

    save_config()

    if staff_role:
        role_text = staff_role.mention
    else:
        role_text = "None"

    await interaction.response.send_message(
        f"✅ Ticket system configured.\n"
        f"📁 Category: {category.mention}\n"
        f"🛡️ Staff role: {role_text}",
        ephemeral=True
    )


# =========================
#      TICKET PANEL
# =========================

@bot.tree.command(
    name="ticket-panel",
    description="Send the ticket creation panel"
)
@app_commands.describe(
    channel="Channel where the panel will be sent"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    cfg = get_guild_config(interaction.guild.id)

    if not cfg.get("ticket_category"):
        await interaction.response.send_message(
            "❌ Run `/ticket-setup` first.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎫 Support Tickets",
        description=(
            "Need help?\n\n"
            "Click the button below to create a private "
            "support ticket."
        ),
        color=discord.Color.blurple()
    )

    try:
        await channel.send(
            embed=embed,
            view=TicketCreateView()
        )

        await interaction.response.send_message(
            f"✅ Ticket panel sent to {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to send messages there.",
            ephemeral=True
        )


# =========================
#      TICKET CLOSE
# =========================

@bot.tree.command(
    name="ticket-close",
    description="Close the current ticket"
)
async def ticket_close(interaction: discord.Interaction):

    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )
        return

    if not channel.topic or not channel.topic.startswith("ticket:"):
        await interaction.response.send_message(
            "❌ This is not a SECURITY ticket.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔒 Closing ticket...",
        ephemeral=True
    )

    await asyncio.sleep(2)

    try:
        await channel.delete(
            reason=f"Ticket closed by {interaction.user}"
        )

    except discord.Forbidden:
        pass

    except discord.HTTPException:
        pass


# =========================
#         END PART 4
# =========================
# =========================
#        START PART 5
#       MODERATION
# =========================

# =========================
#           CLEAR
# =========================

@bot.tree.command(
    name="clear",
    description="Delete messages from a channel"
)
@app_commands.describe(
    amount="Number of messages to delete"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(
            limit=amount
        )

        await interaction.followup.send(
            f"🧹 Deleted **{len(deleted)}** messages.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to manage messages.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord returned an error while deleting messages.",
            ephemeral=True
        )


# =========================
#           KICK
# =========================

@bot.tree.command(
    name="kick",
    description="Kick a member from the server"
)
@app_commands.describe(
    member="Member to kick",
    reason="Reason for the kick"
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = None
):
    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot kick yourself.",
            ephemeral=True
        )
        return

    if member == interaction.guild.owner:
        await interaction.response.send_message(
            "❌ You cannot kick the server owner.",
            ephemeral=True
        )
        return

    if interaction.guild.me and member.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I cannot kick this member because their highest role "
            "is higher than or equal to mine.",
            ephemeral=True
        )
        return

    try:
        await member.kick(
            reason=reason or f"Kicked by {interaction.user}"
        )

        await interaction.response.send_message(
            f"👢 **{member}** has been kicked.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to kick this member.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error while kicking the member.",
            ephemeral=True
        )


# =========================
#            BAN
# =========================

@bot.tree.command(
    name="ban",
    description="Ban a member from the server"
)
@app_commands.describe(
    member="Member to ban",
    reason="Reason for the ban"
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = None
):
    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot ban yourself.",
            ephemeral=True
        )
        return

    if member == interaction.guild.owner:
        await interaction.response.send_message(
            "❌ You cannot ban the server owner.",
            ephemeral=True
        )
        return

    if interaction.guild.me and member.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I cannot ban this member because their highest role "
            "is higher than or equal to mine.",
            ephemeral=True
        )
        return

    try:
        await member.ban(
            reason=reason or f"Banned by {interaction.user}"
        )

        await interaction.response.send_message(
            f"🔨 **{member}** has been banned.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to ban this member.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error while banning the member.",
            ephemeral=True
        )


# =========================
#          TIMEOUT
# =========================

@bot.tree.command(
    name="timeout",
    description="Timeout a member"
)
@app_commands.describe(
    member="Member to timeout",
    minutes="Timeout duration in minutes",
    reason="Reason for the timeout"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: Optional[str] = None
):
    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot timeout yourself.",
            ephemeral=True
        )
        return

    if member == interaction.guild.owner:
        await interaction.response.send_message(
            "❌ You cannot timeout the server owner.",
            ephemeral=True
        )
        return

    if interaction.guild.me and member.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I cannot timeout this member because their highest role "
            "is higher than or equal to mine.",
            ephemeral=True
        )
        return

    try:
        await member.timeout(
            timedelta(minutes=minutes),
            reason=reason or f"Timed out by {interaction.user}"
        )

        await interaction.response.send_message(
            f"⏳ **{member}** has been timed out for **{minutes} minutes**.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to timeout this member.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error while applying the timeout.",
            ephemeral=True
        )


# =========================
#        UNTIMEOUT
# =========================

@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout"
)
@app_commands.describe(
    member="Member to untimeout",
    reason="Reason"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = None
):
    try:
        await member.timeout(
            None,
            reason=reason or f"Timeout removed by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Timeout removed from **{member}**.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to remove this timeout.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#          ADDROLE
# =========================

@bot.tree.command(
    name="addrole",
    description="Give a role to a member"
)
@app_commands.describe(
    member="Member who receives the role",
    role="Role to give"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def addrole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ That role cannot be manually assigned.",
            ephemeral=True
        )
        return

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ That role is higher than or equal to my highest role.",
            ephemeral=True
        )
        return

    try:
        await member.add_roles(
            role,
            reason=f"Role added by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Added {role.mention} to {member.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to give that role.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#        REMOVEROLE
# =========================

@bot.tree.command(
    name="removerole",
    description="Remove a role from a member"
)
@app_commands.describe(
    member="Member who loses the role",
    role="Role to remove"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def removerole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ That role cannot be manually removed.",
            ephemeral=True
        )
        return

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ That role is higher than or equal to my highest role.",
            ephemeral=True
        )
        return

    try:
        await member.remove_roles(
            role,
            reason=f"Role removed by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Removed {role.mention} from {member.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to remove that role.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#            WARN
# =========================

@bot.tree.command(
    name="warn",
    description="Warn a member"
)
@app_commands.describe(
    member="Member to warn",
    reason="Reason for the warning"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = None
):
    cfg = get_guild_config(interaction.guild.id)

    warnings = cfg.setdefault("warnings", {})

    user_id = str(member.id)

    if user_id not in warnings:
        warnings[user_id] = []

    warnings[user_id].append({
        "reason": reason or "No reason provided",
        "moderator": interaction.user.id
    })

    save_config()

    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned.\n"
        f"**Reason:** {reason or 'No reason provided'}",
        ephemeral=True
    )


# =========================
#         WARNINGS
# =========================

@bot.tree.command(
    name="warnings",
    description="View a member's warnings"
)
@app_commands.describe(
    member="Member whose warnings you want to view"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def warnings(
    interaction: discord.Interaction,
    member: discord.Member
):
    cfg = get_guild_config(interaction.guild.id)

    all_warnings = cfg.get("warnings", {})
    user_warnings = all_warnings.get(
        str(member.id),
        []
    )

    if not user_warnings:
        await interaction.response.send_message(
            f"✅ **{member}** has no warnings.",
            ephemeral=True
        )
        return

    lines = []

    for index, warning in enumerate(
        user_warnings,
        start=1
    ):
        reason = warning.get(
            "reason",
            "No reason provided"
        )

        lines.append(
            f"**{index}.** {reason}"
        )

    embed = discord.Embed(
        title=f"⚠️ Warnings — {member}",
        description="\n".join(lines),
        color=discord.Color.orange()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================
#         END PART 5
# =========================
# =========================
#        START PART 6
#          CLEANER
# =========================


# =========================
#        CLEAR USER
# =========================

@bot.tree.command(
    name="clearuser",
    description="Delete messages from a specific user"
)
@app_commands.describe(
    member="User whose messages should be deleted",
    amount="Number of messages to check"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearuser(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda message: message.author.id == member.id
        )

        await interaction.followup.send(
            f"🧹 Deleted **{len(deleted)}** messages from {member.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to delete messages.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#        CLEAR BOTS
# =========================

@bot.tree.command(
    name="clearbots",
    description="Delete messages sent by bots"
)
@app_commands.describe(
    amount="Number of messages to check"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearbots(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda message: message.author.bot
        )

        await interaction.followup.send(
            f"🤖 Deleted **{len(deleted)}** bot messages.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to delete messages.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#        CLEAR LINKS
# =========================

@bot.tree.command(
    name="clearlinks",
    description="Delete messages containing links"
)
@app_commands.describe(
    amount="Number of messages to check"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearlinks(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    url_pattern = re.compile(
        r"https?://\S+|www\.\S+",
        re.IGNORECASE
    )

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda message: bool(
                url_pattern.search(message.content)
            )
        )

        await interaction.followup.send(
            f"🔗 Deleted **{len(deleted)}** messages containing links.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to delete messages.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#       CLEAR INVITES
# =========================

@bot.tree.command(
    name="clearinvites",
    description="Delete messages containing Discord invites"
)
@app_commands.describe(
    amount="Number of messages to check"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearinvites(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    invite_pattern = re.compile(
        r"(discord\.gg/|discord\.com/invite/)\S+",
        re.IGNORECASE
    )

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda message: bool(
                invite_pattern.search(message.content)
            )
        )

        await interaction.followup.send(
            f"📨 Deleted **{len(deleted)}** Discord invite messages.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to delete messages.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#       CLEAR CHANNEL
# =========================

@bot.tree.command(
    name="clearchannel",
    description="Delete recent messages from the current channel"
)
@app_commands.describe(
    amount="Number of messages to delete"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearchannel(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(
            limit=amount
        )

        await interaction.followup.send(
            f"🧹 Cleared **{len(deleted)}** messages from this channel.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to manage this channel.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#          SLOWMODE
# =========================

@bot.tree.command(
    name="slowmode",
    description="Set the channel slowmode"
)
@app_commands.describe(
    seconds="Slowmode delay in seconds (0-21600)"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(
    interaction: discord.Interaction,
    seconds: app_commands.Range[int, 0, 21600]
):
    try:
        await interaction.channel.edit(
            slowmode_delay=seconds,
            reason=f"Slowmode changed by {interaction.user}"
        )

        if seconds == 0:
            text = "🚀 Slowmode disabled."
        else:
            text = f"🐢 Slowmode set to **{seconds} seconds**."

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to change slowmode.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#           LOCK
# =========================

@bot.tree.command(
    name="lock",
    description="Lock the current channel"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):

    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ This command can only be used in a text channel.",
            ephemeral=True
        )
        return

    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            send_messages=False,
            reason=f"Channel locked by {interaction.user}"
        )

        await interaction.response.send_message(
            "🔒 This channel has been locked."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to lock this channel.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#          UNLOCK
# =========================

@bot.tree.command(
    name="unlock",
    description="Unlock the current channel"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):

    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ This command can only be used in a text channel.",
            ephemeral=True
        )
        return

    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            send_messages=None,
            reason=f"Channel unlocked by {interaction.user}"
        )

        await interaction.response.send_message(
            "🔓 This channel has been unlocked."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to unlock this channel.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord returned an error.",
            ephemeral=True
        )


# =========================
#         END PART 6
# =========================
# =========================
#        START PART 8
#          WIPE SYSTEM
# =========================


class WipeConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(
        label="Confirm Wipe",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="security_wipe_confirm"
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Only administrators can confirm a server wipe.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="🧹 **Wiping the server...**",
            embed=None,
            view=None
        )

        # =========================
        # DELETE CHANNELS
        # =========================

        deleted_channels = 0

        for channel in list(guild.channels):

            try:
                await channel.delete(
                    reason=f"Server wipe by {interaction.user}"
                )
                deleted_channels += 1

            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

        # =========================
        # DELETE ROLES
        # =========================

        deleted_roles = 0

        bot_member = guild.me

        if bot_member is not None:

            bot_top_role = bot_member.top_role

            for role in list(guild.roles):

                # NEVER delete @everyone
                if role.is_default():
                    continue

                # NEVER delete managed roles
                if role.managed:
                    continue

                # Bot cannot delete roles equal to
                # or higher than its highest role
                if role >= bot_top_role:
                    continue

                try:
                    await role.delete(
                        reason=f"Server wipe by {interaction.user}"
                    )
                    deleted_roles += 1

                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    pass

        # =========================
        # FINISHED
        # =========================

        try:
            await interaction.followup.send(
                "✅ **Server wipe completed.**\n\n"
                f"🗑️ Channels deleted: **{deleted_channels}**\n"
                f"🎭 Roles deleted: **{deleted_roles}**\n\n"
                "🛡️ The Discord server itself was **NOT deleted**.\n"
                "👑 `@everyone` was **NOT deleted**.\n"
                "🔒 Roles the bot cannot manage were **NOT deleted**.",
                ephemeral=False
            )

        except discord.HTTPException:
            pass


@bot.tree.command(
    name="wipe",
    description="Wipe all removable channels, categories and roles"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def wipe(
    interaction: discord.Interaction
):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    bot_member = guild.me

    if bot_member is None:
        await interaction.response.send_message(
            "❌ I couldn't find myself in this server.",
            ephemeral=True
        )
        return

    removable_channels = len(guild.channels)

    removable_roles = sum(
        1
        for role in guild.roles
        if not role.is_default()
        and not role.managed
        and role < bot_member.top_role
    )

    embed = discord.Embed(
        title="⚠️ SERVER WIPE",
        description=(
            "You are about to wipe this server.\n\n"
            "This will attempt to delete:\n"
            "🗑️ **All removable channels**\n"
            "📂 **All removable categories**\n"
            "🎭 **All removable roles**\n\n"
            "⚠️ **The Discord server itself will NOT be deleted.**\n"
            "👑 `@everyone` will NOT be deleted.\n"
            "🔒 Managed/higher roles will NOT be deleted.\n\n"
            f"Channels found: **{removable_channels}**\n"
            f"Roles removable by bot: **{removable_roles}**"
        ),
        color=discord.Color.red()
    )

    embed.set_footer(
        text="This action cannot be easily undone."
    )

    await interaction.response.send_message(
        embed=embed,
        view=WipeConfirmView(),
        ephemeral=True
    )


# =========================
#       END PART 8
# =========================
# =========================
#        START PART 9
#        LEVEL SYSTEM
# =========================


def get_xp_data(guild, user):
    cfg = get_guild_config(guild.id)

    xp_data = cfg.setdefault("xp", {})

    user_id = str(user.id)

    if user_id not in xp_data:
        xp_data[user_id] = {
            "xp": 0,
            "level": 0
        }

    return xp_data[user_id]


def xp_needed(level):
    return 100 + (level * 50)


def get_level_from_xp(xp):
    level = 0

    while xp >= xp_needed(level):
        xp -= xp_needed(level)
        level += 1

    return level


# =========================
#          RANK
# =========================

@bot.tree.command(
    name="rank",
    description="Show your current level and XP"
)
@app_commands.describe(
    member="Member to check"
)
async def rank(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):

    member = member or interaction.user
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    data = get_xp_data(guild, member)

    embed = discord.Embed(
        title=f"🏆 {member.display_name}'s Rank",
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

    embed.add_field(
        name="🎯 Next Level",
        value=str(xp_needed(data["level"])),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#          LEVEL
# =========================

@bot.tree.command(
    name="level",
    description="Show a member's level"
)
@app_commands.describe(
    member="Member to check"
)
async def level(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):

    member = member or interaction.user
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    data = get_xp_data(guild, member)

    await interaction.response.send_message(
        f"⭐ {member.mention} is **Level {data['level']}** "
        f"with **{data['xp']} XP**."
    )


# =========================
#       LEADERBOARD
# =========================

@bot.tree.command(
    name="leaderboard",
    description="Show the server XP leaderboard"
)
async def leaderboard(
    interaction: discord.Interaction
):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    cfg = get_guild_config(guild.id)
    xp_data = cfg.get("xp", {})

    if not xp_data:
        await interaction.response.send_message(
            "📊 No XP data yet."
        )
        return

    sorted_users = sorted(
        xp_data.items(),
        key=lambda item: (
            item[1].get("level", 0),
            item[1].get("xp", 0)
        ),
        reverse=True
    )

    lines = []

    for position, (user_id, data) in enumerate(
        sorted_users[:10],
        start=1
    ):

        member = guild.get_member(int(user_id))

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

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


# =========================
#    LEVEL CHANNEL
# =========================

@bot.tree.command(
    name="setlevelchannel",
    description="Set the channel for level-up messages"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    channel="Level-up channel"
)
async def setlevelchannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    cfg = get_guild_config(interaction.guild.id)

    cfg["level_channel"] = channel.id

    save_config()

    await interaction.response.send_message(
        f"✅ Level-up messages will be sent in {channel.mention}."
    )


# =========================
#     LEVEL MESSAGE
# =========================

@bot.tree.command(
    name="setlevelmessage",
    description="Set the level-up message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    message="Level-up message"
)
async def setlevelmessage(
    interaction: discord.Interaction,
    message: str
):

    cfg = get_guild_config(interaction.guild.id)

    cfg["level_message"] = message

    save_config()

    await interaction.response.send_message(
        "✅ Level-up message updated."
    )


# =========================
#      TOGGLE LEVELS
# =========================

@bot.tree.command(
    name="togglelevels",
    description="Enable or disable the level system"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    enabled="Enable or disable levels"
)
async def togglelevels(
    interaction: discord.Interaction,
    enabled: bool
):

    cfg = get_guild_config(interaction.guild.id)

    cfg["level_enabled"] = enabled

    save_config()

    status = "enabled" if enabled else "disabled"

    await interaction.response.send_message(
        f"✅ Level system **{status}**."
    )


# =========================
#        SET LEVEL
# =========================

@bot.tree.command(
    name="setlevel",
    description="Set a member's level"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    member="Member",
    amount="Level amount"
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


# =========================
#          SET XP
# =========================

@bot.tree.command(
    name="setxp",
    description="Set a member's XP"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    member="Member",
    amount="XP amount"
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


# =========================
#         RESET XP
# =========================

@bot.tree.command(
    name="resetxp",
    description="Reset a member's XP"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    member="Member"
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
        f"🔄 {member.mention}'s XP has been reset."
    )


# =========================
#         END PART 9
# =========================
# =========================
#        START PART 10
#       EXTRA UTILITIES
# =========================


# =========================
#            SAY
# =========================

@bot.tree.command(
    name="say",
    description="Make SECURITY send a message"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
@app_commands.describe(
    message="Message to send"
)
async def say(
    interaction: discord.Interaction,
    message: str
):

    channel = interaction.channel

    await interaction.response.send_message(
        "✅ Message sent.",
        ephemeral=True
    )

    try:
        await channel.send(
            message,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=True,
                everyone=False
            )
        )
    except discord.HTTPException:
        pass


# =========================
#         ANNOUNCE
# =========================

@bot.tree.command(
    name="announce",
    description="Send an announcement embed"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
@app_commands.describe(
    title="Announcement title",
    message="Announcement message"
)
async def announce(
    interaction: discord.Interaction,
    title: str,
    message: str
):

    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow()
    )

    embed.set_footer(
        text=f"Announcement by {interaction.user.display_name}"
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#          UPTIME
# =========================

@bot.tree.command(
    name="uptime",
    description="Show how long SECURITY has been online"
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

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    parts.append(f"{seconds}s")

    await interaction.response.send_message(
        f"⏱️ SECURITY uptime: **{' '.join(parts)}**"
    )


# =========================
#      SECURITY STATUS
# =========================

@bot.tree.command(
    name="security-status",
    description="Show SECURITY's current status"
)
async def security_status(
    interaction: discord.Interaction
):

    guild = interaction.guild

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
        name="🌐 Servers",
        value=str(len(bot.guilds)),
        inline=True
    )

    if guild:
        cfg = get_guild_config(guild.id)

        embed.add_field(
            name="👋 Welcome",
            value="ON" if cfg["welcome_enabled"] else "OFF",
            inline=True
        )

        embed.add_field(
            name="🚪 Goodbye",
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


# =========================
#            POLL
# =========================

@bot.tree.command(
    name="poll",
    description="Create a simple yes/no poll"
)
@app_commands.describe(
    question="Question for the poll"
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
#           HELP
# =========================


@bot.tree.command(
    name="help",
    description="Show all SECURITY commands"
)
async def help_command(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🛡️ SECURITY — Help",
        description=(
            "Here are the commands available in SECURITY.\n"
            "Use the categories below to find what you need."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome & Goodbye",
        value=(
            "`/welcome`\n"
            "`/welcome-on`\n"
            "`/welcome-off`\n"
            "`/welcome-role`\n"
            "`/welcome-role-off`\n"
            "`/welcome-message`\n"
            "`/welcome-image`\n"
            "`/welcome-style`\n"
            "`/testwelcome`\n"
            "`/bye`\n"
            "`/bye-on`\n"
            "`/bye-off`\n"
            "`/bye-message`\n"
            "`/bye-image`\n"
            "`/bye-style`\n"
            "`/testbye`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Verification",
        value=(
            "`/verifysetup`\n"
            "`/verify-message`\n"
            "`/verify-panel`\n"
            "`/verify`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "`/ticket setup`\n"
            "`/ticket panel`\n"
            "`/ticket close`"
        ),
        inline=False
    )

    embed.add_field(
        name="🔨 Moderation",
        value=(
            "`/clear`\n"
            "`/kick`\n"
            "`/ban`\n"
            "`/timeout`\n"
            "`/untimeout`\n"
            "`/addrole`\n"
            "`/removerole`\n"
            "`/warn`\n"
            "`/warnings`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Cleaner",
        value=(
            "`/clearuser`\n"
            "`/clearbots`\n"
            "`/clearlinks`\n"
            "`/clearinvites`\n"
            "`/clearchannel`\n"
            "`/slowmode`\n"
            "`/lock`\n"
            "`/unlock`"
        ),
        inline=False
    )

    embed.add_field(
        name="💥 Server Wipe",
        value="`/wipe`",
        inline=False
    )

    embed.add_field(
        name="⭐ Levels",
        value=(
            "`/rank`\n"
            "`/level`\n"
            "`/leaderboard`\n"
            "`/setlevelchannel`\n"
            "`/setlevelmessage`\n"
            "`/togglelevels`\n"
            "`/setlevel`\n"
            "`/setxp`\n"
            "`/resetxp`"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Utility",
        value=(
            "`/ping`\n"
            "`/serverinfo`\n"
            "`/userinfo`\n"
            "`/avatar`\n"
            "`/servericon`\n"
            "`/botinfo`\n"
            "`/membercount`\n"
            "`/channelinfo`\n"
            "`/roleinfo`\n"
            "`/say`\n"
            "`/announce`\n"
            "`/uptime`\n"
            "`/security-status`\n"
            "`/poll`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎬 TikTok Showcase",
        value=(
            "`/showcase setup`\n"
            "`/showcase on`\n"
            "`/showcase off`\n"
            "`/showcase message`\n"
            "`/showcase panel`"
        ),
        inline=False
    )

    embed.set_footer(
        text="SECURITY • Server Protection"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================
#         END PART 11
# =========================
# =========================
#        START PART 12
#      EVENTS + SHOWCASE
#        + BOT START
# =========================


# =========================
#      TIKTOK SHOWCASE
# =========================


class ShowcaseModal(discord.ui.Modal, title="🎬 Submit TikTok"):

    tiktok_url = discord.ui.TextInput(
        label="TikTok URL",
        placeholder="https://www.tiktok.com/@user/video/123456789",
        required=True,
        max_length=500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This can only be used in a server.",
                ephemeral=True
            )
            return

        cfg = get_guild_config(guild.id)

        if not cfg.get("showcase_enabled", False):
            await interaction.response.send_message(
                "❌ TikTok Showcase is currently disabled.",
                ephemeral=True
            )
            return

        link = extract_tiktok_link(
            str(self.tiktok_url.value)
        )

        if not link:
            await interaction.response.send_message(
                "❌ Please provide a valid TikTok link.",
                ephemeral=True
            )
            return

        showcase_channel_id = cfg.get(
            "showcase_channel"
        )

        judge_channel_id = cfg.get(
            "showcase_judge_channel"
        )

        judge_role_id = cfg.get(
            "showcase_judge_role"
        )

        showcase_channel = guild.get_channel(
            showcase_channel_id
        ) if showcase_channel_id else None

        judge_channel = guild.get_channel(
            judge_channel_id
        ) if judge_channel_id else None

        if not isinstance(
            showcase_channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ Showcase channel is not configured.",
                ephemeral=True
            )
            return

        if not isinstance(
            judge_channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ Judge channel is not configured.",
                ephemeral=True
            )
            return

        public_embed = discord.Embed(
            title="🎬 TikTok Submitted",
            description=(
                f"Submitted by {interaction.user.mention}\n\n"
                f"{link}"
            ),
            color=discord.Color.blurple()
        )

        await showcase_channel.send(
            embed=public_embed,
            allowed_mentions=discord.AllowedMentions(
                users=True
            )
        )

        judge_role_text = ""

        if judge_role_id:
            judge_role = guild.get_role(
                judge_role_id
            )

            if judge_role:
                judge_role_text = judge_role.mention

        judge_embed = discord.Embed(
            title="🎬 New TikTok Submission",
            description=(
                f"**User:** {interaction.user.mention}\n"
                f"**Link:** {link}"
            ),
            color=discord.Color.gold()
        )

        await judge_channel.send(
            content=judge_role_text,
            embed=judge_embed,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=True
            )
        )

        await interaction.response.send_message(
            "✅ Your TikTok has been submitted!",
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
    async def submit_tiktok(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            ShowcaseModal()
        )


# =========================
#      SHOWCASE GROUP
# =========================


showcase_group = app_commands.Group(
    name="showcase",
    description="TikTok showcase system"
)

bot.tree.add_command(showcase_group)


@showcase_group.command(
    name="setup",
    description="Configure the TikTok showcase"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    showcase_channel="Public showcase channel",
    judge_channel="Private judge channel",
    judge_role="Role to notify"
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
        "✅ TikTok Showcase has been configured.\n\n"
        f"🎬 Showcase: {showcase_channel.mention}\n"
        f"⚖️ Judge: {judge_channel.mention}\n"
        f"👮 Judge role: {judge_role.mention}"
    )


@showcase_group.command(
    name="on",
    description="Enable TikTok Showcase"
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

    if not cfg.get("showcase_channel"):
        await interaction.response.send_message(
            "❌ Run `/showcase setup` first.",
            ephemeral=True
        )
        return

    cfg["showcase_enabled"] = True

    save_config()

    await interaction.response.send_message(
        "✅ TikTok Showcase is now **ON**."
    )


@showcase_group.command(
    name="off",
    description="Disable TikTok Showcase"
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
        "✅ TikTok Showcase is now **OFF**."
    )


@showcase_group.command(
    name="message",
    description="Change the showcase panel message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    message="Panel message"
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
    description="Send the TikTok submission panel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    channel="Channel for the panel"
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
        description=cfg.get(
            "showcase_message",
            "Submit your TikTok below! 🎬"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="SECURITY • TikTok Showcase"
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


async def on_member_join(
    member: discord.Member
):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    # =========================
    #        AUTO ROLE
    # =========================

    role_id = cfg.get("auto_role")

    if role_id:

        role = guild.get_role(role_id)

        if role:

            bot_member = guild.me

            if (
                bot_member
                and not role.is_default()
                and not role.managed
                and role < bot_member.top_role
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

    # =========================
    #         WELCOME
    # =========================

    if cfg.get("welcome_enabled", True):

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


async def on_member_remove(
    member: discord.Member
):

    guild = member.guild
    cfg = get_guild_config(guild.id)

    if not cfg.get("bye_enabled", True):
        return

    channel_id = cfg.get(
        "bye_channel"
    )

    channel = guild.get_channel(
        channel_id
    ) if channel_id else None

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

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

    if guild is not None:

        cfg = get_guild_config(
            guild.id
        )

        # =========================
        #       LEVEL XP
        # =========================

        if cfg.get("level_enabled", True):

            data = get_xp_data(
                guild,
                message.author
            )

            old_level = data.get(
                "level",
                0
            )

            data["xp"] = data.get(
                "xp",
                0
            ) + random.randint(
                5,
                15
            )

            new_level = get_level_from_xp(
                data["xp"]
            )

            if new_level > old_level:

                data["level"] = new_level

                level_channel_id = cfg.get(
                    "level_channel"
                )

                level_channel = guild.get_channel(
                    level_channel_id
                ) if level_channel_id else None

                if isinstance(
                    level_channel,
                    discord.TextChannel
                ):

                    level_text = format_message(
                        cfg.get(
                            "level_message",
                            "GG {user}! You reached level **{level}**! 🎉"
                        ),
                        message.author,
                        guild
                    )

                    level_text = level_text.replace(
                        "{level}",
                        str(new_level)
                    )

                    try:
                        await level_channel.send(
                            level_text
                        )
                    except (
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        pass

                save_config()

            else:
                save_config()

        # =========================
        #       TIKTOK LINKS
        # =========================

        if cfg.get(
            "showcase_enabled",
            False
        ):

            link = extract_tiktok_link(
                message.content
            )

            if link:

                judge_channel_id = cfg.get(
                    "showcase_judge_channel"
                )

                judge_channel = guild.get_channel(
                    judge_channel_id
                ) if judge_channel_id else None

                judge_role_id = cfg.get(
                    "showcase_judge_role"
                )

                if isinstance(
                    judge_channel,
                    discord.TextChannel
                ):

                    role_text = ""

                    if judge_role_id:

                        judge_role = guild.get_role(
                            judge_role_id
                        )

                        if judge_role:
                            role_text = judge_role.mention

                    embed = discord.Embed(
                        title="🎬 New TikTok",
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
                            embed=embed,
                            allowed_mentions=discord.AllowedMentions(
                                users=True,
                                roles=True
                            )
                        )
                    except (
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        pass

    await bot.process_commands(message)


# =========================
#           READY
# =========================


_views_loaded = False


@bot.event
async def on_ready():

    global _views_loaded

    if not _views_loaded:

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

        _views_loaded = True

    print(
        f"✅ SECURITY is online as {bot.user}"
    )

    print(
        f"📡 Connected to {len(bot.guilds)} server(s)"
    )


# =========================
#         START BOT
# =========================


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. "
        "Add it to your hosting platform's environment variables."
    )

bot.run(TOKEN)


# =========================
#         END PART 12
# =========================
