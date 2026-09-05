import os
import sqlite3
import asyncio
import random
import time
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands


# =========================
# SECURITY BOT
# =========================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

DB = sqlite3.connect(
    "security.db",
    check_same_thread=False
)

DB.row_factory = sqlite3.Row


# =========================
# DATABASE
# =========================

DB.execute("""
CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER PRIMARY KEY,

    welcome_enabled INTEGER DEFAULT 0,
    welcome_channel INTEGER,
    welcome_message TEXT DEFAULT 'Welcome {user} to {server}!',

    bye_enabled INTEGER DEFAULT 0,
    bye_channel INTEGER,
    bye_message TEXT DEFAULT '{username} has left {server}.',

    verify_channel INTEGER,
    verify_role INTEGER,
    verify_message TEXT DEFAULT 'Click the button below to verify.',

    ticket_category INTEGER,
    ticket_support INTEGER,

    chatbot_enabled INTEGER DEFAULT 0,
    chatbot_channel INTEGER,

    autorole INTEGER,

    xp_enabled INTEGER DEFAULT 0,
    xp_per_message INTEGER DEFAULT 5,
    xp_cooldown INTEGER DEFAULT 60,

    automod_enabled INTEGER DEFAULT 0,
    automod_links INTEGER DEFAULT 0,
    automod_spam INTEGER DEFAULT 0,
    automod_caps INTEGER DEFAULT 0,
    automod_invites INTEGER DEFAULT 0
)
""")

DB.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT,
    created INTEGER
)
""")

DB.execute("""
CREATE TABLE IF NOT EXISTS levels (
    guild_id INTEGER,
    user_id INTEGER,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    PRIMARY KEY(guild_id,user_id)
)
""")

DB.commit()


def setup_guild(guild_id):
    DB.execute(
        "INSERT OR IGNORE INTO settings (guild_id) VALUES (?)",
        (guild_id,)
    )
    DB.commit()


def settings(guild_id):
    setup_guild(guild_id)

    return DB.execute(
        "SELECT * FROM settings WHERE guild_id=?",
        (guild_id,)
    ).fetchone()


def set_setting(guild_id, name, value):
    setup_guild(guild_id)

    allowed = {
        "welcome_enabled",
        "welcome_channel",
        "welcome_message",

        "bye_enabled",
        "bye_channel",
        "bye_message",

        "verify_channel",
        "verify_role",
        "verify_message",

        "ticket_category",
        "ticket_support",

        "chatbot_enabled",
        "chatbot_channel",

        "autorole",

        "xp_enabled",
        "xp_per_message",
        "xp_cooldown",

        "automod_enabled",
        "automod_links",
        "automod_spam",
        "automod_caps",
        "automod_invites"
    }

    if name not in allowed:
        return

    DB.execute(
        f"UPDATE settings SET {name}=? WHERE guild_id=?",
        (value, guild_id)
    )

    DB.commit()


def variables(text, member):
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


async def reply(
    interaction,
    content=None,
    embed=None,
    ephemeral=True
):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                content=content,
                embed=embed,
                ephemeral=ephemeral
            )
        else:
            await interaction.response.send_message(
                content=content,
                embed=embed,
                ephemeral=ephemeral
            )
    except discord.HTTPException:
        pass


def admin():
    async def check(interaction):
        return (
            interaction.guild is not None
            and interaction.user.guild_permissions.administrator
        )

    return app_commands.check(check)


def moderator():
    async def check(interaction):
        if not interaction.guild:
            return False

        p = interaction.user.guild_permissions

        return (
            p.administrator
            or p.kick_members
            or p.ban_members
            or p.moderate_members
        )

    return app_commands.check(check)


def can_target(interaction, member):
    guild = interaction.guild

    if member == guild.owner:
        return False

    if member == interaction.user:
        return False

    if member.top_role >= interaction.user.top_role:
        return False

    if member.top_role >= guild.me.top_role:
        return False

    return True


# =========================
# READY
# =========================

@bot.event
async def on_ready():

    try:
        synced = await bot.tree.sync()

        print(
            f"✅ SECURITY is online as {bot.user}"
        )

        print(
            f"✅ Synced {len(synced)} slash commands"
        )

        await bot.change_presence(
            activity=discord.Game(
                name="/help | SECURITY"
            )
        )

    except Exception as e:
        print(f"❌ Sync error: {e}")


# =========================
# WELCOME
# =========================

welcome = app_commands.Group(
    name="welcome",
    description="Welcome system"
)


@welcome.command(
    name="setup",
    description="Set the welcome channel"
)
@admin()
async def welcome_setup(
    interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "welcome_channel",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "welcome_enabled",
        1
    )

    await reply(
        interaction,
        f"✅ Welcome channel set to {channel.mention}"
    )


@welcome.command(
    name="enable",
    description="Enable welcome messages"
)
@admin()
async def welcome_enable(interaction):

    set_setting(
        interaction.guild.id,
        "welcome_enabled",
        1
    )

    await reply(
        interaction,
        "✅ Welcome system enabled."
    )


@welcome.command(
    name="disable",
    description="Disable welcome messages"
)
@admin()
async def welcome_disable(interaction):

    set_setting(
        interaction.guild.id,
        "welcome_enabled",
        0
    )

    await reply(
        interaction,
        "✅ Welcome system disabled."
    )


@welcome.command(
    name="message",
    description="Change welcome message"
)
@admin()
async def welcome_message(
    interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "welcome_message",
        message
    )

    await reply(
        interaction,
        "✅ Welcome message saved."
    )


@welcome.command(
    name="test",
    description="Test the welcome message"
)
@admin()
async def welcome_test(interaction):

    row = settings(
        interaction.guild.id
    )

    text = variables(
        row["welcome_message"],
        interaction.user
    )

    await reply(
        interaction,
        text,
        ephemeral=False
    )


bot.tree.add_command(welcome)


# =========================
# GOODBYE
# =========================

bye = app_commands.Group(
    name="bye",
    description="Goodbye system"
)


@bye.command(
    name="setup",
    description="Set goodbye channel"
)
@admin()
async def bye_setup(
    interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "bye_channel",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "bye_enabled",
        1
    )

    await reply(
        interaction,
        f"✅ Goodbye channel set to {channel.mention}"
    )


@bye.command(
    name="enable",
    description="Enable goodbye messages"
)
@admin()
async def bye_enable(interaction):

    set_setting(
        interaction.guild.id,
        "bye_enabled",
        1
    )

    await reply(
        interaction,
        "✅ Goodbye system enabled."
    )


@bye.command(
    name="disable",
    description="Disable goodbye messages"
)
@admin()
async def bye_disable(interaction):

    set_setting(
        interaction.guild.id,
        "bye_enabled",
        0
    )

    await reply(
        interaction,
        "✅ Goodbye system disabled."
    )


@bye.command(
    name="message",
    description="Change goodbye message"
)
@admin()
async def bye_message(
    interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "bye_message",
        message
    )

    await reply(
        interaction,
        "✅ Goodbye message saved."
    )


@bye.command(
    name="test",
    description="Test goodbye message"
)
@admin()
async def bye_test(interaction):

    row = settings(
        interaction.guild.id
    )

    text = variables(
        row["bye_message"],
        interaction.user
    )

    await reply(
        interaction,
        text,
        ephemeral=False
    )


bot.tree.add_command(bye)


# =========================
# MEMBER JOIN
# =========================

@bot.event
async def on_member_join(member):

    row = settings(
        member.guild.id
    )

    # AUTO ROLE
    if row["autorole"]:

        role = member.guild.get_role(
            row["autorole"]
        )

        if (
            role
            and member.guild.me.guild_permissions.manage_roles
            and role < member.guild.me.top_role
        ):
            try:
                await member.add_roles(role)
            except discord.HTTPException:
                pass

    # WELCOME
    if not row["welcome_enabled"]:
        return

    if not row["welcome_channel"]:
        return

    channel = member.guild.get_channel(
        row["welcome_channel"]
    )

    if not channel:
        return

    message = variables(
        row["welcome_message"],
        member
    )

    try:
        await channel.send(message)
    except discord.HTTPException:
        pass


# =========================
# MEMBER LEAVE
# =========================

@bot.event
async def on_member_remove(member):

    row = settings(
        member.guild.id
    )

    if not row["bye_enabled"]:
        return

    if not row["bye_channel"]:
        return

    channel = member.guild.get_channel(
        row["bye_channel"]
    )

    if not channel:
        return

    message = variables(
        row["bye_message"],
        member
    )

    try:
        await channel.send(message)
    except discord.HTTPException:
        pass
# =========================
# VERIFICATION SYSTEM
# =========================

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="security_verify"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.guild:
            return

        row = settings(
            interaction.guild.id
        )

        role_id = row["verify_role"]

        if not role_id:
            await reply(
                interaction,
                "❌ Verification has not been configured."
            )
            return

        role = interaction.guild.get_role(
            role_id
        )

        if not role:
            await reply(
                interaction,
                "❌ The verification role no longer exists."
            )
            return

        if role >= interaction.guild.me.top_role:
            await reply(
                interaction,
                "❌ I cannot give this role because it is above my bot role."
            )
            return

        try:
            await interaction.user.add_roles(role)

            await reply(
                interaction,
                f"✅ You are now verified and received {role.mention}."
            )

        except discord.Forbidden:
            await reply(
                interaction,
                "❌ I don't have permission to give that role."
            )

        except discord.HTTPException:
            await reply(
                interaction,
                "❌ Discord rejected the request. Try again."
            )


verify_group = app_commands.Group(
    name="verify",
    description="Verification system"
)


@verify_group.command(
    name="setup",
    description="Configure the verification system"
)
@admin()
async def verify_setup(
    interaction,
    channel: discord.TextChannel,
    role: discord.Role,
    message: str = "Click the button below to verify."
):

    if role.is_default():
        await reply(
            interaction,
            "❌ You cannot use @everyone as the verification role."
        )
        return

    if role >= interaction.guild.me.top_role:
        await reply(
            interaction,
            "❌ The verification role must be below my bot role."
        )
        return

    set_setting(
        interaction.guild.id,
        "verify_channel",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "verify_role",
        role.id
    )

    set_setting(
        interaction.guild.id,
        "verify_message",
        message
    )

    embed = discord.Embed(
        title="Verification",
        description=message,
        color=discord.Color.green()
    )

    embed.set_footer(
        text=interaction.guild.name
    )

    try:
        await channel.send(
            embed=embed,
            view=VerifyView()
        )

        await reply(
            interaction,
            f"✅ Verification panel sent to {channel.mention}."
        )

    except discord.Forbidden:
        await reply(
            interaction,
            "❌ I cannot send messages in that channel."
        )


@verify_group.command(
    name="panel",
    description="Send the verification panel again"
)
@admin()
async def verify_panel(interaction):

    row = settings(
        interaction.guild.id
    )

    if not row["verify_channel"]:
        await reply(
            interaction,
            "❌ Run `/verify setup` first."
        )
        return

    channel = interaction.guild.get_channel(
        row["verify_channel"]
    )

    if not channel:
        await reply(
            interaction,
            "❌ The verification channel no longer exists."
        )
        return

    embed = discord.Embed(
        title="Verification",
        description=row["verify_message"],
        color=discord.Color.green()
    )

    await channel.send(
        embed=embed,
        view=VerifyView()
    )

    await reply(
        interaction,
        "✅ Verification panel sent."
    )


bot.tree.add_command(verify_group)


# =========================
# TICKET SYSTEM
# =========================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="security_create_ticket"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild

        if not guild:
            return

        # CHECK FOR EXISTING TICKET
        for channel in guild.text_channels:

            if channel.topic == f"ticket-owner:{interaction.user.id}":

                await reply(
                    interaction,
                    f"❌ You already have a ticket: {channel.mention}"
                )
                return

        row = settings(
            guild.id
        )

        category = None

        if row["ticket_category"]:
            category = guild.get_channel(
                row["ticket_category"]
            )

        support_role = None

        if row["ticket_support"]:
            support_role = guild.get_role(
                row["ticket_support"]
            )

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                ),

            guild.me:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    read_message_history=True
                )
        }

        if support_role:

            overwrites[support_role] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
            )

        name = (
            f"ticket-{interaction.user.name}"
            .lower()
            .replace(" ", "-")
        )

        name = name[:90]

        try:

            channel = await guild.create_text_channel(
                name=name,
                category=category,
                overwrites=overwrites,
                topic=f"ticket-owner:{interaction.user.id}"
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
                content=(
                    interaction.user.mention
                    + (
                        f" {support_role.mention}"
                        if support_role
                        else ""
                    )
                ),
                embed=embed,
                view=TicketControlView()
            )

            await reply(
                interaction,
                f"✅ Ticket created: {channel.mention}"
            )

        except discord.Forbidden:

            await reply(
                interaction,
                "❌ I don't have permission to create ticket channels."
            )

        except discord.HTTPException:

            await reply(
                interaction,
                "❌ Discord could not create the ticket."
            )


class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.secondary,
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

        if not channel.topic:
            await reply(
                interaction,
                "❌ This isn't a SECURITY ticket."
            )
            return

        await reply(
            interaction,
            "🔒 Ticket closed."
        )

        try:

            await channel.set_permissions(
                interaction.guild.default_role,
                view_channel=False
            )

            owner_id = channel.topic.replace(
                "ticket-owner:",
                ""
            )

            owner = interaction.guild.get_member(
                int(owner_id)
            )

            if owner:

                await channel.set_permissions(
                    owner,
                    send_messages=False,
                    view_channel=True
                )

        except Exception:
            pass


    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="security_ticket_delete"
    )
    async def delete_ticket(
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

        if not channel.topic:
            await reply(
                interaction,
                "❌ This isn't a SECURITY ticket."
            )
            return

        # STAFF OR TICKET OWNER
        owner_id = channel.topic.replace(
            "ticket-owner:",
            ""
        )

        is_owner = (
            str(interaction.user.id)
            == owner_id
        )

        is_staff = (
            interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.administrator
        )

        if not is_owner and not is_staff:

            await reply(
                interaction,
                "❌ You cannot delete this ticket."
            )
            return

        await reply(
            interaction,
            "🗑️ Deleting ticket..."
        )

        await asyncio.sleep(2)

        try:
            await channel.delete(
                reason="SECURITY ticket deletion"
            )

        except discord.HTTPException:
            pass


ticket_group = app_commands.Group(
    name="ticket",
    description="Ticket system"
)


@ticket_group.command(
    name="setup",
    description="Configure the ticket system"
)
@admin()
async def ticket_setup(
    interaction,
    category: discord.CategoryChannel,
    support_role: discord.Role
):

    set_setting(
        interaction.guild.id,
        "ticket_category",
        category.id
    )

    set_setting(
        interaction.guild.id,
        "ticket_support",
        support_role.id
    )

    await reply(
        interaction,
        (
            "✅ Ticket system configured.\n"
            f"Category: {category.name}\n"
            f"Support role: {support_role.mention}"
        )
    )


@ticket_group.command(
    name="panel",
    description="Send the ticket creation panel"
)
@admin()
async def ticket_panel(
    interaction,
    channel: discord.TextChannel = None
):

    target = channel or interaction.channel

    if not isinstance(
        target,
        discord.TextChannel
    ):
        await reply(
            interaction,
            "❌ Invalid channel."
        )
        return

    row = settings(
        interaction.guild.id
    )

    if not row["ticket_category"]:

        await reply(
            interaction,
            "❌ Run `/ticket setup` first."
        )
        return

    embed = discord.Embed(
        title="🎫 Support Tickets",
        description=(
            "Need help?\n\n"
            "Click **Create Ticket** below "
            "to open a private support ticket."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="SECURITY Ticket System"
    )

    try:

        await target.send(
            embed=embed,
            view=TicketView()
        )

        await reply(
            interaction,
            f"✅ Ticket panel sent to {target.mention}."
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I cannot send messages there."
        )


@ticket_group.command(
    name="delete",
    description="Delete the current ticket"
)
@moderator()
async def ticket_delete(
    interaction
):

    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        await reply(
            interaction,
            "❌ This command can only be used in a ticket."
        )
        return

    if not channel.topic or not channel.topic.startswith(
        "ticket-owner:"
    ):

        await reply(
            interaction,
            "❌ This is not a SECURITY ticket."
        )
        return

    await reply(
        interaction,
        "🗑️ Deleting ticket in 3 seconds..."
    )

    await asyncio.sleep(3)

    try:
        await channel.delete(
            reason="SECURITY ticket deletion"
        )
    except discord.HTTPException:
        pass


bot.tree.add_command(ticket_group)


# =========================
# PERSISTENT BUTTONS
# =========================

bot.add_view(
    VerifyView()
)

bot.add_view(
    TicketView()
)

bot.add_view(
    TicketControlView()
        )
# =========================
# CLEAN / PURGE
# =========================

@bot.tree.command(
    name="clean",
    description="Delete messages from a channel"
)
@moderator()
@app_commands.describe(
    amount="Number of messages to delete (1-100)"
)
async def clean(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        await reply(
            interaction,
            "❌ This command can only be used in a text channel."
        )
        return

    if not interaction.channel.permissions_for(
        interaction.guild.me
    ).manage_messages:

        await reply(
            interaction,
            "❌ I need the **Manage Messages** permission."
        )
        return

    await reply(
        interaction,
        f"🧹 Cleaning **{amount}** messages..."
    )

    try:

        deleted = await interaction.channel.purge(
            limit=amount
        )

        await interaction.edit_original_response(
            content=f"✅ Deleted **{len(deleted)}** messages."
        )

    except discord.Forbidden:

        await interaction.edit_original_response(
            content="❌ I don't have permission to delete messages."
        )

    except discord.HTTPException:

        await interaction.edit_original_response(
            content="❌ Discord rejected the request."
        )


@bot.tree.command(
    name="purge",
    description="Delete messages from a channel"
)
@moderator()
@app_commands.describe(
    amount="Number of messages to delete (1-100)"
)
async def purge(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await clean.callback(
        interaction,
        amount
    )


# =========================
# WIPE CONFIRMATION
# =========================

class WipeConfirmView(discord.ui.View):

    def __init__(
        self,
        interaction: discord.Interaction,
        wipe_type: str
    ):

        super().__init__(timeout=30)

        self.original_user = interaction.user
        self.wipe_type = wipe_type
        self.confirmed = False

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        if interaction.user.id != self.original_user.id:

            await reply(
                interaction,
                "❌ Only the person who started the wipe can confirm it."
            )

            return False

        return True

    @discord.ui.button(
        label="YES, WIPE",
        style=discord.ButtonStyle.danger,
        emoji="⚠️"
    )
    async def yes(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.confirmed = True

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="⚠️ Wipe confirmed. Starting...",
            view=self
        )

        self.stop()

    @discord.ui.button(
        label="NO, CANCEL",
        style=discord.ButtonStyle.secondary,
        emoji="❌"
    )
    async def no(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="❌ Wipe cancelled.",
            view=self
        )

        self.stop()


# =========================
# WIPE SERVER
# =========================

@bot.tree.command(
    name="wipe",
    description="Safely wipe selected server content"
)
@admin()
@app_commands.describe(
    messages="Delete messages",
    channels="Delete channels",
    categories="Delete categories"
)
async def wipe(
    interaction: discord.Interaction,
    messages: bool = False,
    channels: bool = False,
    categories: bool = False
):

    guild = interaction.guild

    if not any([
        messages,
        channels,
        categories
    ]):

        await reply(
            interaction,
            (
                "❌ You didn't select anything.\n\n"
                "Choose at least one:\n"
                "🗑️ Messages\n"
                "📁 Channels\n"
                "📂 Categories"
            )
        )

        return

    embed = discord.Embed(
        title="⚠️ SERVER WIPE WARNING",
        description=(
            "**This action can permanently delete server content.**\n\n"
            f"🗑️ Messages: {'YES' if messages else 'NO'}\n"
            f"📺 Channels: {'YES' if channels else 'NO'}\n"
            f"📂 Categories: {'YES' if categories else 'NO'}\n\n"
            "**IMPORTANT:**\n"
            "❌ The Discord server itself will NOT be deleted.\n"
            "❌ Roles will NOT be deleted.\n"
            "❌ @everyone will NOT be deleted.\n"
            "❌ Members will NOT be banned or removed.\n"
            "❌ Bot roles will NOT be deleted.\n\n"
            "**Press YES only if you are absolutely sure.**"
        ),
        color=discord.Color.red()
    )

    view = WipeConfirmView(
        interaction,
        "server"
    )

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

    await view.wait()

    if not view.confirmed:
        return

    # =====================
    # DELETE MESSAGES
    # =====================

    if messages:

        for channel in list(guild.text_channels):

            try:

                if channel.permissions_for(
                    guild.me
                ).manage_messages:

                    await channel.purge(
                        limit=100,
                        bulk=True
                    )

            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                continue

    # =====================
    # DELETE CHANNELS
    # =====================

    if channels:

        for channel in list(guild.channels):

            # NEVER delete roles.
            # NEVER delete the server.
            # NEVER delete members.

            if isinstance(
                channel,
                discord.TextChannel
            ):

                try:
                    await channel.delete(
                        reason="SECURITY server wipe"
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    continue

            elif isinstance(
                channel,
                discord.VoiceChannel
            ):

                try:
                    await channel.delete(
                        reason="SECURITY server wipe"
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    continue

            elif isinstance(
                channel,
                discord.StageChannel
            ):

                try:
                    await channel.delete(
                        reason="SECURITY server wipe"
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    continue

            elif isinstance(
                channel,
                discord.ForumChannel
            ):

                try:
                    await channel.delete(
                        reason="SECURITY server wipe"
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    continue

    # =====================
    # DELETE CATEGORIES
    # =====================

    if categories and not channels:

        for category in list(
            guild.categories
        ):

            try:

                await category.delete(
                    reason="SECURITY category wipe"
                )

            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                continue

    try:

        await interaction.followup.send(
            (
                "✅ **Server wipe completed.**\n\n"
                "The server itself was NOT deleted.\n"
                "Roles were NOT deleted.\n"
                "Members were NOT removed."
            ),
            ephemeral=True
        )

    except discord.HTTPException:
        pass


# =========================
# WIPE CHANNEL
# =========================

@bot.tree.command(
    name="wipechannel",
    description="Delete and recreate a channel"
)
@admin()
async def wipechannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    embed = discord.Embed(
        title="⚠️ Wipe Channel",
        description=(
            f"You are about to delete {channel.mention}.\n\n"
            "The channel will be recreated.\n"
            "❌ Roles will not be deleted.\n"
            "❌ The server will not be deleted.\n\n"
            "**Continue?**"
        ),
        color=discord.Color.red()
    )

    view = WipeConfirmView(
        interaction,
        "channel"
    )

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

    await view.wait()

    if not view.confirmed:
        return

    old_name = channel.name
    old_topic = channel.topic
    old_category = channel.category
    old_position = channel.position
    old_slowmode = channel.slowmode_delay

    try:

        new_channel = await channel.clone(
            name=old_name,
            reason="SECURITY channel wipe"
        )

        if old_topic:
            try:
                await new_channel.edit(
                    topic=old_topic
                )
            except discord.HTTPException:
                pass

        try:
            await new_channel.edit(
                slowmode_delay=old_slowmode
            )
        except discord.HTTPException:
            pass

        try:
            await new_channel.edit(
                position=old_position
            )
        except discord.HTTPException:
            pass

        await channel.delete(
            reason="SECURITY channel wipe"
        )

        await interaction.followup.send(
            f"✅ Channel wiped: {new_channel.mention}",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ I don't have permission to manage this channel.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.followup.send(
            "❌ Discord rejected the channel wipe.",
            ephemeral=True
        )


# =========================
# WIPE CATEGORY
# =========================

@bot.tree.command(
    name="wipecategory",
    description="Delete a category and its channels"
)
@admin()
async def wipecategory(
    interaction: discord.Interaction,
    category: discord.CategoryChannel
):

    channel_count = len(
        category.channels
    )

    embed = discord.Embed(
        title="⚠️ Wipe Category",
        description=(
            f"Category: **{category.name}**\n"
            f"Channels inside: **{channel_count}**\n\n"
            "This will delete the category and its channels.\n\n"
            "❌ Roles will NOT be deleted.\n"
            "❌ Members will NOT be removed.\n"
            "❌ The server will NOT be deleted.\n\n"
            "**Continue?**"
        ),
        color=discord.Color.red()
    )

    view = WipeConfirmView(
        interaction,
        "category"
    )

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

    await view.wait()

    if not view.confirmed:
        return

    try:

        # Delete channels inside category first.
        for channel in list(
            category.channels
        ):

            try:
                await channel.delete(
                    reason="SECURITY category wipe"
                )

            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                continue

        # Delete category itself.
        await category.delete(
            reason="SECURITY category wipe"
        )

        await interaction.followup.send(
            "✅ Category wiped successfully.\n"
            "❌ No roles were deleted.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ I don't have permission to delete this category.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.followup.send(
            "❌ Discord rejected the category wipe.",
            ephemeral=True
            )
# =========================
# MODERATION
# =========================

@bot.tree.command(
    name="ban",
    description="Ban a member"
)
@moderator()
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if not can_target(interaction, member):

        await reply(
            interaction,
            "❌ I cannot ban this member."
        )
        return

    if not interaction.guild.me.guild_permissions.ban_members:

        await reply(
            interaction,
            "❌ I need the **Ban Members** permission."
        )
        return

    try:

        await member.ban(
            reason=reason
        )

        await reply(
            interaction,
            f"🔨 **{member}** has been banned.\nReason: {reason}",
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I don't have permission to ban this member."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the ban."
        )


@bot.tree.command(
    name="kick",
    description="Kick a member"
)
@moderator()
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if not can_target(interaction, member):

        await reply(
            interaction,
            "❌ I cannot kick this member."
        )
        return

    if not interaction.guild.me.guild_permissions.kick_members:

        await reply(
            interaction,
            "❌ I need the **Kick Members** permission."
        )
        return

    try:

        await member.kick(
            reason=reason
        )

        await reply(
            interaction,
            f"👢 **{member}** has been kicked.\nReason: {reason}",
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I don't have permission to kick this member."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the kick."
        )


@bot.tree.command(
    name="timeout",
    description="Timeout a member"
)
@moderator()
@app_commands.describe(
    minutes="Timeout duration in minutes"
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason provided"
):

    if not can_target(interaction, member):

        await reply(
            interaction,
            "❌ I cannot timeout this member."
        )
        return

    if not interaction.guild.me.guild_permissions.moderate_members:

        await reply(
            interaction,
            "❌ I need the **Moderate Members** permission."
        )
        return

    try:

        until = discord.utils.utcnow() + timedelta(
            minutes=minutes
        )

        await member.timeout(
            until,
            reason=reason
        )

        await reply(
            interaction,
            (
                f"⏳ **{member}** has been timed out "
                f"for **{minutes} minutes**.\n"
                f"Reason: {reason}"
            ),
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I cannot timeout this member."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the timeout."
        )


@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout"
)
@moderator()
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member
):

    if not can_target(interaction, member):

        await reply(
            interaction,
            "❌ I cannot modify this member."
        )
        return

    try:

        await member.timeout(
            None,
            reason="Timeout removed by SECURITY"
        )

        await reply(
            interaction,
            f"✅ Timeout removed from **{member}**.",
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I cannot remove this timeout."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the request."
        )


@bot.tree.command(
    name="warn",
    description="Warn a member"
)
@moderator()
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if member.bot:

        await reply(
            interaction,
            "❌ You cannot warn a bot."
        )
        return

    DB.execute(
        """
        INSERT INTO warnings
        (guild_id,user_id,moderator_id,reason,created)
        VALUES (?,?,?,?,?)
        """,
        (
            interaction.guild.id,
            member.id,
            interaction.user.id,
            reason,
            int(time.time())
        )
    )

    DB.commit()

    count = DB.execute(
        """
        SELECT COUNT(*) AS total
        FROM warnings
        WHERE guild_id=? AND user_id=?
        """,
        (
            interaction.guild.id,
            member.id
        )
    ).fetchone()["total"]

    await reply(
        interaction,
        (
            f"⚠️ **{member}** has been warned.\n"
            f"Reason: {reason}\n"
            f"Total warnings: **{count}**"
        ),
        ephemeral=False
    )

    try:

        await member.send(
            (
                f"⚠️ You were warned in **{interaction.guild.name}**.\n"
                f"Reason: {reason}"
            )
        )

    except discord.HTTPException:
        pass


@bot.tree.command(
    name="warnings",
    description="View a member's warnings"
)
@moderator()
async def warnings(
    interaction: discord.Interaction,
    member: discord.Member
):

    rows = DB.execute(
        """
        SELECT *
        FROM warnings
        WHERE guild_id=? AND user_id=?
        ORDER BY id DESC
        LIMIT 10
        """,
        (
            interaction.guild.id,
            member.id
        )
    ).fetchall()

    if not rows:

        await reply(
            interaction,
            f"✅ **{member}** has no warnings."
        )
        return

    embed = discord.Embed(
        title=f"Warnings — {member}",
        color=discord.Color.orange()
    )

    for i, row in enumerate(rows, 1):

        moderator_user = interaction.guild.get_member(
            row["moderator_id"]
        )

        moderator_name = (
            moderator_user.mention
            if moderator_user
            else "Unknown moderator"
        )

        embed.add_field(
            name=f"Warning #{i}",
            value=(
                f"**Reason:** {row['reason']}\n"
                f"**Moderator:** {moderator_name}"
            ),
            inline=False
        )

    await reply(
        interaction,
        embed=embed
    )


@bot.tree.command(
    name="clearwarnings",
    description="Clear all warnings for a member"
)
@admin()
async def clearwarnings(
    interaction: discord.Interaction,
    member: discord.Member
):

    DB.execute(
        """
        DELETE FROM warnings
        WHERE guild_id=? AND user_id=?
        """,
        (
            interaction.guild.id,
            member.id
        )
    )

    DB.commit()

    await reply(
        interaction,
        f"✅ Cleared all warnings for **{member}**.",
        ephemeral=False
    )


# =========================
# AUTO ROLE
# =========================

@bot.tree.command(
    name="autorole",
    description="Automatically give a role to new members"
)
@admin()
async def autorole(
    interaction: discord.Interaction,
    role: discord.Role = None
):

    if role is None:

        set_setting(
            interaction.guild.id,
            "autorole",
            None
        )

        await reply(
            interaction,
            "✅ Auto-role disabled."
        )

        return

    if role.is_default():

        await reply(
            interaction,
            "❌ You cannot use @everyone."
        )
        return

    if role >= interaction.guild.me.top_role:

        await reply(
            interaction,
            "❌ That role is above my bot role."
        )
        return

    set_setting(
        interaction.guild.id,
        "autorole",
        role.id
    )

    await reply(
        interaction,
        f"✅ New members will automatically receive {role.mention}.",
        ephemeral=False
    )


# =========================
# ROLE MANAGEMENT
# =========================

@bot.tree.command(
    name="addrole",
    description="Give a role to a member"
)
@moderator()
async def addrole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):

    if role.is_default():

        await reply(
            interaction,
            "❌ You cannot manually give @everyone."
        )
        return

    if role >= interaction.guild.me.top_role:

        await reply(
            interaction,
            "❌ That role is above my bot role."
        )
        return

    if member == interaction.guild.owner:

        await reply(
            interaction,
            "❌ You cannot modify the server owner's roles."
        )
        return

    try:

        await member.add_roles(
            role,
            reason=f"Role added by {interaction.user}"
        )

        await reply(
            interaction,
            f"✅ Added {role.mention} to {member.mention}.",
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I cannot give that role."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the request."
        )


@bot.tree.command(
    name="removerole",
    description="Remove a role from a member"
)
@moderator()
async def removerole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):

    if role.is_default():

        await reply(
            interaction,
            "❌ You cannot remove @everyone."
        )
        return

    if role >= interaction.guild.me.top_role:

        await reply(
            interaction,
            "❌ That role is above my bot role."
        )
        return

    try:

        await member.remove_roles(
            role,
            reason=f"Role removed by {interaction.user}"
        )

        await reply(
            interaction,
            f"✅ Removed {role.mention} from {member.mention}.",
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I cannot remove that role."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the request."
        )


@bot.tree.command(
    name="roleinfo",
    description="Show information about a role"
)
async def roleinfo(
    interaction: discord.Interaction,
    role: discord.Role
):

    embed = discord.Embed(
        title="Role Information",
        color=role.color
    )

    embed.add_field(
        name="Name",
        value=role.name,
        inline=True
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

    embed.add_field(
        name="Mentionable",
        value="Yes" if role.mentionable else "No",
        inline=True
    )

    embed.add_field(
        name="Managed",
        value="Yes" if role.managed else "No",
        inline=True
    )

    await reply(
        interaction,
        embed=embed
    )


@bot.tree.command(
    name="createrole",
    description="Create a new role"
)
@admin()
async def createrole(
    interaction: discord.Interaction,
    name: str
):

    if len(name) > 100:

        await reply(
            interaction,
            "❌ Role name must be 100 characters or less."
        )
        return

    try:

        role = await interaction.guild.create_role(
            name=name,
            reason=f"Created by {interaction.user}"
        )

        await reply(
            interaction,
            f"✅ Created role {role.mention}.",
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I don't have permission to create roles."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the request."
        )


@bot.tree.command(
    name="deleterole",
    description="Delete a role"
)
@admin()
async def deleterole(
    interaction: discord.Interaction,
    role: discord.Role
):

    if role.is_default():

        await reply(
            interaction,
            "❌ You cannot delete @everyone."
        )
        return

    if role.managed:

        await reply(
            interaction,
            "❌ Managed/integration roles cannot be deleted."
        )
        return

    if role >= interaction.guild.me.top_role:

        await reply(
            interaction,
            "❌ That role is above my bot role."
        )
        return

    try:

        await role.delete(
            reason=f"Deleted by {interaction.user}"
        )

        await reply(
            interaction,
            "🗑️ Role deleted.",
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I cannot delete that role."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the request."
        )


@bot.tree.command(
    name="nick",
    description="Change a member's nickname"
)
@moderator()
async def nick(
    interaction: discord.Interaction,
    member: discord.Member,
    nickname: str
):

    if not can_target(interaction, member):

        await reply(
            interaction,
            "❌ I cannot change this member's nickname."
        )
        return

    if len(nickname) > 32:

        await reply(
            interaction,
            "❌ Nickname must be 32 characters or less."
        )
        return

    try:

        await member.edit(
            nick=nickname,
            reason=f"Nickname changed by {interaction.user}"
        )

        await reply(
            interaction,
            f"✅ Nickname changed for {member.mention}.",
            ephemeral=False
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I cannot change that nickname."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the request."
    )
# =========================
# AUTOMOD
# =========================

BAD_WORDS = [
    "discord.gg/",
    "discord.com/invite/"
]

SPAM_CACHE = {}


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        return

    row = settings(message.guild.id)

    # =====================
    # AUTOMOD
    # =====================

    if row["automod_enabled"]:

        content = message.content.lower()

        # INVITES
        if row["automod_invites"]:

            if any(word in content for word in BAD_WORDS):

                if not message.author.guild_permissions.manage_messages:

                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass

                    try:
                        await message.channel.send(
                            f"⚠️ {message.author.mention}, Discord invites are not allowed.",
                            delete_after=5
                        )
                    except discord.HTTPException:
                        pass

                    return

        # CAPS
        if row["automod_caps"]:

            letters = [
                x for x in message.content
                if x.isalpha()
            ]

            if len(letters) >= 10:

                upper = sum(
                    x.isupper()
                    for x in letters
                )

                if upper / len(letters) >= 0.8:

                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass

                    return

        # SPAM
        if row["automod_spam"]:

            now = time.time()

            user_id = message.author.id

            if user_id not in SPAM_CACHE:
                SPAM_CACHE[user_id] = []

            SPAM_CACHE[user_id] = [
                t for t in SPAM_CACHE[user_id]
                if now - t < 5
            ]

            SPAM_CACHE[user_id].append(now)

            if len(SPAM_CACHE[user_id]) >= 6:

                try:
                    await message.delete()
                except discord.HTTPException:
                    pass

                try:
                    await message.author.timeout(
                        timedelta(seconds=30),
                        reason="SECURITY AutoMod spam"
                    )
                except discord.HTTPException:
                    pass

                SPAM_CACHE[user_id] = []

                return

    # =====================
    # LEVELING
    # =====================

    if row["xp_enabled"]:

        user_id = message.author.id

        existing = DB.execute(
            """
            SELECT *
            FROM levels
            WHERE guild_id=? AND user_id=?
            """,
            (
                message.guild.id,
                user_id
            )
        ).fetchone()

        if not existing:

            DB.execute(
                """
                INSERT INTO levels
                (guild_id,user_id,xp,level)
                VALUES (?,?,?,?)
                """,
                (
                    message.guild.id,
                    user_id,
                    0,
                    0
                )
            )

            DB.commit()

            existing = {
                "xp": 0,
                "level": 0
            }

        xp_gain = random.randint(
            1,
            max(1, row["xp_per_message"])
        )

        xp = existing["xp"] + xp_gain
        level = existing["level"]

        required = (
            100 + (level * 50)
        )

        if xp >= required:

            xp -= required
            level += 1

            try:

                await message.channel.send(
                    f"🎉 {message.author.mention} reached **Level {level}**!"
                )

            except discord.HTTPException:
                pass

        DB.execute(
            """
            UPDATE levels
            SET xp=?, level=?
            WHERE guild_id=? AND user_id=?
            """,
            (
                xp,
                level,
                message.guild.id,
                user_id
            )
        )

        DB.commit()

    await bot.process_commands(message)


# =========================
# AUTOMOD SETTINGS
# =========================

automod = app_commands.Group(
    name="automod",
    description="Auto moderation system"
)


@automod.command(
    name="enable",
    description="Enable AutoMod"
)
@admin()
async def automod_enable(interaction):

    set_setting(
        interaction.guild.id,
        "automod_enabled",
        1
    )

    await reply(
        interaction,
        "✅ AutoMod enabled."
    )


@automod.command(
    name="disable",
    description="Disable AutoMod"
)
@admin()
async def automod_disable(interaction):

    set_setting(
        interaction.guild.id,
        "automod_enabled",
        0
    )

    await reply(
        interaction,
        "✅ AutoMod disabled."
    )


@automod.command(
    name="invites",
    description="Toggle Discord invite protection"
)
@admin()
async def automod_invites(
    interaction,
    enabled: bool
):

    set_setting(
        interaction.guild.id,
        "automod_invites",
        int(enabled)
    )

    await reply(
        interaction,
        f"✅ Invite protection: **{'ON' if enabled else 'OFF'}**"
    )


@automod.command(
    name="spam",
    description="Toggle spam protection"
)
@admin()
async def automod_spam(
    interaction,
    enabled: bool
):

    set_setting(
        interaction.guild.id,
        "automod_spam",
        int(enabled)
    )

    await reply(
        interaction,
        f"✅ Spam protection: **{'ON' if enabled else 'OFF'}**"
    )


@automod.command(
    name="caps",
    description="Toggle excessive caps protection"
)
@admin()
async def automod_caps(
    interaction,
    enabled: bool
):

    set_setting(
        interaction.guild.id,
        "automod_caps",
        int(enabled)
    )

    await reply(
        interaction,
        f"✅ Caps protection: **{'ON' if enabled else 'OFF'}**"
    )


bot.tree.add_command(automod)


# =========================
# LEVELING
# =========================

@bot.tree.command(
    name="level",
    description="Show your level"
)
async def level(
    interaction: discord.Interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    row = DB.execute(
        """
        SELECT *
        FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        (
            interaction.guild.id,
            member.id
        )
    ).fetchone()

    if not row:

        xp = 0
        level_number = 0

    else:

        xp = row["xp"]
        level_number = row["level"]

    required = 100 + (
        level_number * 50
    )

    embed = discord.Embed(
        title="📊 Level",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Member",
        value=member.mention
    )

    embed.add_field(
        name="Level",
        value=str(level_number)
    )

    embed.add_field(
        name="XP",
        value=f"{xp}/{required}"
    )

    await reply(
        interaction,
        embed=embed
    )


@bot.tree.command(
    name="rank",
    description="Show your rank"
)
async def rank(
    interaction: discord.Interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    rows = DB.execute(
        """
        SELECT user_id, xp, level
        FROM levels
        WHERE guild_id=?
        ORDER BY level DESC, xp DESC
        """,
        (interaction.guild.id,)
    ).fetchall()

    position = None

    for i, row in enumerate(rows, 1):

        if row["user_id"] == member.id:
            position = i
            break

    if position is None:
        position = "Unranked"

    await reply(
        interaction,
        (
            f"🏆 **{member.display_name}**\n"
            f"Rank: **#{position}**"
        )
    )


@bot.tree.command(
    name="leveling",
    description="Enable or disable leveling"
)
@admin()
async def leveling(
    interaction: discord.Interaction,
    enabled: bool
):

    set_setting(
        interaction.guild.id,
        "xp_enabled",
        int(enabled)
    )

    await reply(
        interaction,
        f"✅ Leveling: **{'ON' if enabled else 'OFF'}**"
    )


# =========================
# SAY
# =========================

@bot.tree.command(
    name="say",
    description="Make SECURITY send a message"
)
@moderator()
async def say(
    interaction: discord.Interaction,
    message: str,
    channel: discord.TextChannel = None
):

    target = channel or interaction.channel

    try:

        await target.send(message)

        await reply(
            interaction,
            f"✅ Message sent to {target.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:

        await reply(
            interaction,
            "❌ I cannot send messages there."
        )

    except discord.HTTPException:

        await reply(
            interaction,
            "❌ Discord rejected the message."
        )


# =========================
# CHATBOT
# =========================

@bot.tree.command(
    name="chatbot",
    description="Configure the chatbot channel"
)
@admin()
async def chatbot(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
    enabled: bool = True
):

    if not enabled:

        set_setting(
            interaction.guild.id,
            "chatbot_enabled",
            0
        )

        await reply(
            interaction,
            "✅ Chatbot disabled."
        )

        return

    if not channel:

        await reply(
            interaction,
            "❌ Please select a chatbot channel."
        )

        return

    set_setting(
        interaction.guild.id,
        "chatbot_channel",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "chatbot_enabled",
        1
    )

    await reply(
        interaction,
        f"✅ Chatbot enabled in {channel.mention}."
    )


@bot.tree.command(
    name="chat",
    description="Chat with SECURITY"
)
async def chat(
    interaction: discord.Interaction,
    message: str
):

    text = message.lower()

    if "hello" in text or "hi" in text:

        answer = (
            f"Hello {interaction.user.mention}! 👋"
        )

    elif "how are you" in text:

        answer = (
            "I'm doing great! 🤖"
        )

    elif "help" in text:

        answer = (
            "Use `/help` to see my commands."
        )

    elif "who are you" in text:

        answer = (
            "I'm **𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘**, your Discord server bot. 🛡️"
        )

    else:

        answer = (
            f"🤖 You said: **{message}**"
        )

    await reply(
        interaction,
        answer,
        ephemeral=False
    )


# =========================
# SERVER INFO
# =========================

@bot.tree.command(
    name="serverinfo",
    description="Show server information"
)
async def serverinfo(
    interaction: discord.Interaction
):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"🛡️ {guild.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Owner",
        value=guild.owner.mention
        if guild.owner else "Unknown",
        inline=True
    )

    embed.add_field(
        name="Members",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="Channels",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="Roles",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="Server ID",
        value=str(guild.id),
        inline=True
    )

    embed.add_field(
        name="Created",
        value=discord.utils.format_dt(
            guild.created_at,
            style="D"
        ),
        inline=True
    )

    await reply(
        interaction,
        embed=embed
    )


# =========================
# SETTINGS
# =========================

@bot.tree.command(
    name="settings",
    description="Show SECURITY settings"
)
@admin()
async def show_settings(
    interaction: discord.Interaction
):

    row = settings(
        interaction.guild.id
    )

    embed = discord.Embed(
        title="⚙️ SECURITY Settings",
        color=discord.Color.blurple()
    )

    welcome = (
        f"<#{row['welcome_channel']}>"
        if row["welcome_channel"]
        else "Not set"
    )

    bye = (
        f"<#{row['bye_channel']}>"
        if row["bye_channel"]
        else "Not set"
    )

    verify = (
        f"<#{row['verify_channel']}>"
        if row["verify_channel"]
        else "Not set"
    )

    tickets = (
        f"<#{row['ticket_category']}>"
        if row["ticket_category"]
        else "Not set"
    )

    auto = (
        f"<@&{row['autorole']}>"
        if row["autorole"]
        else "Disabled"
    )

    chatbot_channel = (
        f"<#{row['chatbot_channel']}>"
        if row["chatbot_channel"]
        else "Not set"
    )

    embed.add_field(
        name="Welcome",
        value=(
            f"{'🟢' if row['welcome_enabled'] else '🔴'} "
            f"{welcome}"
        ),
        inline=False
    )

    embed.add_field(
        name="Goodbye",
        value=(
            f"{'🟢' if row['bye_enabled'] else '🔴'} "
            f"{bye}"
        ),
        inline=False
    )

    embed.add_field(
        name="Verification",
        value=verify,
        inline=False
    )

    embed.add_field(
        name="Tickets",
        value=tickets,
        inline=False
    )

    embed.add_field(
        name="Auto Role",
        value=auto,
        inline=False
    )

    embed.add_field(
        name="Chatbot",
        value=(
            f"{'🟢' if row['chatbot_enabled'] else '🔴'} "
            f"{chatbot_channel}"
        ),
        inline=False
    )

    embed.add_field(
        name="Leveling",
        value=(
            "🟢 Enabled"
            if row["xp_enabled"]
            else "🔴 Disabled"
        ),
        inline=False
    )

    embed.add_field(
        name="AutoMod",
        value=(
            "🟢 Enabled"
            if row["automod_enabled"]
            else "🔴 Disabled"
        ),
        inline=False
    )

    await reply(
        interaction,
        embed=embed
    )


# =========================
# HELP
# =========================

@bot.tree.command(
    name="help",
    description="Show SECURITY commands"
)
async def help_command(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🛡️ 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘",
        description=(
            "Professional Discord server management.\n\n"
            "Use the command groups below."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🟢 Welcome",
        value=(
            "`/welcome setup`\n"
            "`/welcome enable`\n"
            "`/welcome disable`\n"
            "`/welcome message`\n"
            "`/welcome test`"
        ),
        inline=False
    )

    embed.add_field(
        name="👋 Goodbye",
        value=(
            "`/bye setup`\n"
            "`/bye enable`\n"
            "`/bye disable`\n"
            "`/bye message`\n"
            "`/bye test`"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ Verification",
        value=(
            "`/verify setup`\n"
            "`/verify panel`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "`/ticket setup`\n"
            "`/ticket panel`\n"
            "`/ticket delete`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Cleaning",
        value=(
            "`/clean`\n"
            "`/purge`"
        ),
        inline=False
    )

    embed.add_field(
        name="⚠️ Wipe",
        value=(
            "`/wipe`\n"
            "`/wipechannel`\n"
            "`/wipecategory`"
        ),
        inline=False
    )

    embed.add_field(
        name="🔨 Moderation",
        value=(
            "`/ban`\n"
            "`/kick`\n"
            "`/timeout`\n"
            "`/untimeout`\n"
            "`/warn`\n"
            "`/warnings`\n"
            "`/clearwarnings`\n"
            "`/nick`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎭 Roles",
        value=(
            "`/autorole`\n"
            "`/addrole`\n"
            "`/removerole`\n"
            "`/roleinfo`\n"
            "`/createrole`\n"
            "`/deleterole`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ AutoMod",
        value=(
            "`/automod enable`\n"
            "`/automod disable`\n"
            "`/automod invites`\n"
            "`/automod spam`\n"
            "`/automod caps`"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Leveling",
        value=(
            "`/level`\n"
            "`/rank`\n"
            "`/leveling`"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 Chatbot",
        value=(
            "`/chatbot`\n"
            "`/chat`"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Server",
        value=(
            "`/serverinfo`\n"
            "`/settings`\n"
            "`/say`"
        ),
        inline=False
    )

    embed.set_footer(
        text="SECURITY • Use /help anytime"
    )

    await reply(
        interaction,
        embed=embed
    )


# =========================
# ERROR HANDLER
# =========================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.CheckFailure
    ):

        await reply(
            interaction,
            "❌ You don't have permission to use this command."
        )

        return

    if isinstance(
        error,
        app_commands.CommandOnCooldown
    ):

        await reply(
            interaction,
            "⏳ Please slow down and try again."
        )

        return

    if isinstance(
        error,
        app_commands.MissingPermissions
    ):

        await reply(
            interaction,
            "❌ You don't have the required permissions."
        )

        return

    if isinstance(
        error,
        app_commands.BotMissingPermissions
    ):

        await reply(
            interaction,
            "❌ I don't have the permissions required for this action."
        )

        return

    print(
        f"❌ Command error: {error}"
    )

    await reply(
        interaction,
        "❌ Something went wrong while running that command."
    )


# =========================
# NORMAL ERROR HANDLER
# =========================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    print(
        f"❌ Discord event error: {event}"
    )


# =========================
# START BOT
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN is missing from Railway Variables."
    )

print("🚀 Starting SECURITY...")

bot.run(TOKEN)
