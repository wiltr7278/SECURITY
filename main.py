import os
import sqlite3
import asyncio
import random
import re
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# DATABASE
# ============================================================

DB = "security.db"

db = sqlite3.connect(DB)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER PRIMARY KEY,

    welcome_enabled INTEGER DEFAULT 0,
    welcome_channel INTEGER DEFAULT 0,
    welcome_message TEXT DEFAULT 'Welcome {user} to {server}! 👋',
    welcome_image TEXT DEFAULT '',

    bye_enabled INTEGER DEFAULT 0,
    bye_channel INTEGER DEFAULT 0,
    bye_message TEXT DEFAULT '{user} has left the server. 👋',
    bye_image TEXT DEFAULT '',

    verify_channel INTEGER DEFAULT 0,
    verify_role INTEGER DEFAULT 0,
    verify_message TEXT DEFAULT 'Click the button below to verify.',

    ticket_category INTEGER DEFAULT 0,
    ticket_support INTEGER DEFAULT 0,

    chatbot_enabled INTEGER DEFAULT 0,
    chatbot_channel INTEGER DEFAULT 0,

    autorole INTEGER DEFAULT 0,

    xp_enabled INTEGER DEFAULT 0,
    xp_per_message INTEGER DEFAULT 5,
    xp_cooldown INTEGER DEFAULT 30,

    automod_enabled INTEGER DEFAULT 0,
    automod_links INTEGER DEFAULT 0,
    automod_spam INTEGER DEFAULT 0,
    automod_caps INTEGER DEFAULT 0,
    automod_invites INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT,
    created_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS levels (
    guild_id INTEGER,
    user_id INTEGER,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
)
""")

db.commit()
db.close()


# ============================================================
# DATABASE HELPERS
# ============================================================

def setup_guild(guild_id):

    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO settings (guild_id) VALUES (?)",
        (guild_id,)
    )

    db.commit()
    db.close()


def get_settings(guild_id):

    setup_guild(guild_id)

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    cur.execute(
        "SELECT * FROM settings WHERE guild_id=?",
        (guild_id,)
    )

    row = cur.fetchone()

    db.close()

    return row


def set_setting(guild_id, name, value):

    setup_guild(guild_id)

    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        f"UPDATE settings SET {name}=? WHERE guild_id=?",
        (value, guild_id)
    )

    db.commit()
    db.close()


# ============================================================
# PERMISSION CHECKS
# ============================================================

def admin():
    async def predicate(interaction):

        if not interaction.user.guild_permissions.administrator:
            raise app_commands.CheckFailure(
                "Administrator required."
            )

        return True

    return app_commands.check(predicate)


def moderator():
    async def predicate(interaction):

        perms = interaction.user.guild_permissions

        if not (
            perms.administrator
            or perms.manage_messages
            or perms.moderate_members
            or perms.kick_members
            or perms.ban_members
        ):
            raise app_commands.CheckFailure(
                "Moderator permission required."
            )

        return True

    return app_commands.check(predicate)


def can_target(actor, target):

    if actor.id == target.id:
        return False

    if target.id == actor.guild.owner_id:
        return False

    if actor.id != actor.guild.owner_id:
        if target.top_role >= actor.top_role:
            return False

    me = actor.guild.me

    if me and target.top_role >= me.top_role:
        return False

    return True


# ============================================================
# FORMAT MESSAGE
# ============================================================

def format_message(text, member):

    return (
        text
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace("{membercount}", str(member.guild.member_count))
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    for guild in bot.guilds:
        setup_guild(guild.id)

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Sync error: {e}")

    await bot.change_presence(
        activity=discord.Game(
            name="/help | 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘"
        )
    )

    print(
        f"✅ SECURITY is online as {bot.user}"
    )


# ============================================================
# WELCOME
# ============================================================

welcome_group = app_commands.Group(
    name="welcome",
    description="Configure welcome messages"
)


@welcome_group.command(
    name="setup",
    description="Set up the welcome system"
)
@app_commands.describe(
    channel="Welcome channel",
    message="Welcome message",
    image="Optional image URL"
)
@admin()
async def welcome_setup(
    interaction,
    channel: discord.TextChannel,
    message: str = "Welcome {user} to {server}! 👋",
    image: str = ""
):

    set_setting(
        interaction.guild.id,
        "welcome_channel",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "welcome_message",
        message
    )

    set_setting(
        interaction.guild.id,
        "welcome_image",
        image
    )

    set_setting(
        interaction.guild.id,
        "welcome_enabled",
        1
    )

    await interaction.response.send_message(
        f"✅ Welcome system enabled in {channel.mention}.",
        ephemeral=True
    )


@welcome_group.command(
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

    await interaction.response.send_message(
        "✅ Welcome messages enabled.",
        ephemeral=True
    )


@welcome_group.command(
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

    await interaction.response.send_message(
        "🛑 Welcome messages disabled.",
        ephemeral=True
    )


@welcome_group.command(
    name="test",
    description="Test the welcome message"
)
@admin()
async def welcome_test(interaction):

    s = get_settings(interaction.guild.id)

    channel_id = s["welcome_channel"]

    channel = interaction.guild.get_channel(
        channel_id
    )

    if not channel:
        await interaction.response.send_message(
            "❌ Welcome channel is not configured.",
            ephemeral=True
        )
        return

    message = format_message(
        s["welcome_message"],
        interaction.user
    )

    embed = discord.Embed(
        description=message,
        color=discord.Color.green()
    )

    if s["welcome_image"]:
        embed.set_image(
            url=s["welcome_image"]
        )

    await channel.send(embed=embed)

    await interaction.response.send_message(
        "✅ Welcome test sent.",
        ephemeral=True
    )


bot.tree.add_command(welcome_group)


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    s = get_settings(member.guild.id)

    # Autorole
    role_id = s["autorole"]

    if role_id:
        role = member.guild.get_role(role_id)

        if role and role < member.guild.me.top_role:
            try:
                await member.add_roles(role)
            except discord.HTTPException:
                pass

    # Welcome
    if not s["welcome_enabled"]:
        return

    channel = member.guild.get_channel(
        s["welcome_channel"]
    )

    if not channel:
        return

    text = format_message(
        s["welcome_message"],
        member
    )

    embed = discord.Embed(
        description=text,
        color=discord.Color.green()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    if s["welcome_image"]:
        embed.set_image(
            url=s["welcome_image"]
        )

    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


# ============================================================
# GOODBYE
# ============================================================

bye_group = app_commands.Group(
    name="bye",
    description="Configure goodbye messages"
)


@bye_group.command(
    name="setup",
    description="Set up goodbye messages"
)
@app_commands.describe(
    channel="Goodbye channel",
    message="Goodbye message",
    image="Optional image URL"
)
@admin()
async def bye_setup(
    interaction,
    channel: discord.TextChannel,
    message: str = "{user} has left the server. 👋",
    image: str = ""
):

    set_setting(
        interaction.guild.id,
        "bye_channel",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "bye_message",
        message
    )

    set_setting(
        interaction.guild.id,
        "bye_image",
        image
    )

    set_setting(
        interaction.guild.id,
        "bye_enabled",
        1
    )

    await interaction.response.send_message(
        f"✅ Goodbye system enabled in {channel.mention}.",
        ephemeral=True
    )


@bye_group.command(
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

    await interaction.response.send_message(
        "✅ Goodbye messages enabled.",
        ephemeral=True
    )


@bye_group.command(
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

    await interaction.response.send_message(
        "🛑 Goodbye messages disabled.",
        ephemeral=True
    )


bot.tree.add_command(bye_group)


@bot.event
async def on_member_remove(member):

    s = get_settings(member.guild.id)

    if not s["bye_enabled"]:
        return

    channel = member.guild.get_channel(
        s["bye_channel"]
    )

    if not channel:
        return

    text = format_message(
        s["bye_message"],
        member
    )

    embed = discord.Embed(
        description=text,
        color=discord.Color.red()
    )

    if s["bye_image"]:
        embed.set_image(
            url=s["bye_image"]
        )

    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass
# ============================================================
# PART 2 — VERIFICATION + TICKETS
# ============================================================


# ============================================================
# VERIFICATION BUTTON
# ============================================================

class VerifyView(discord.ui.View):

    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

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
        member = interaction.user

        role = guild.get_role(self.role_id)

        if role is None:
            await interaction.response.send_message(
                "❌ The verification role no longer exists. "
                "Ask an administrator to create a new verification panel.",
                ephemeral=True
            )
            return

        me = guild.me

        if role >= me.top_role:
            await interaction.response.send_message(
                "❌ SECURITY cannot give this role.\n\n"
                "Move the SECURITY bot role **above** the verification role.",
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
                f"✅ Verification successful! "
                f"You received {role.mention}.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I don't have permission to give you the role.",
                ephemeral=True
            )


# ============================================================
# VERIFY COMMAND
# ============================================================

@bot.tree.command(
    name="verify",
    description="Create a verification panel"
)
@app_commands.describe(
    channel="Channel for the verification panel",
    role="Role given after verification",
    message="Verification message"
)
@admin()
async def verify(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    role: discord.Role,
    message: str = "Click the button below to verify yourself."
):

    me = interaction.guild.me

    if role.is_default():
        await interaction.response.send_message(
            "❌ You cannot use @everyone.",
            ephemeral=True
        )
        return

    if role >= me.top_role:
        await interaction.response.send_message(
            "❌ The verification role must be BELOW the SECURITY bot role.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🛡️ Verification",
        description=message,
        color=discord.Color.green()
    )

    embed.set_footer(
        text="𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 • Verification"
    )

    try:

        await channel.send(
            embed=embed,
            view=VerifyView(role.id)
        )

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

        await interaction.response.send_message(
            f"✅ Verification panel created in {channel.mention}.\n"
            f"✅ Role: {role.mention}",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot send messages in that channel.",
            ephemeral=True
        )


# ============================================================
# TICKET BUTTON
# ============================================================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="security_create_ticket"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild
        member = interaction.user

        s = get_settings(guild.id)

        category = guild.get_channel(
            s["ticket_category"]
        )

        support_role = guild.get_role(
            s["ticket_support"]
        )

        existing = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{member.id}"
        )

        if existing:

            await interaction.response.send_message(
                f"❌ You already have a ticket: {existing.mention}",
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
                read_message_history=True
            ),

            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True
            )
        }

        if support_role:

            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        try:

            channel = await guild.create_text_channel(
                name=f"ticket-{member.id}",
                category=category if isinstance(
                    category,
                    discord.CategoryChannel
                ) else None,
                overwrites=overwrites,
                reason="SECURITY ticket"
            )

            embed = discord.Embed(
                title="🎫 Support Ticket",
                description=(
                    f"Welcome {member.mention}!\n\n"
                    "Please explain your issue here.\n"
                    "Staff will help you soon."
                ),
                color=discord.Color.blurple()
            )

            await channel.send(
                content=(
                    support_role.mention
                    if support_role else None
                ),
                embed=embed,
                view=TicketControlView()
            )

            await interaction.response.send_message(
                f"✅ Ticket created: {channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I don't have permission to create tickets.",
                ephemeral=True
            )


# ============================================================
# TICKET CONTROL
# ============================================================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="security_ticket_close"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            view_channel=False
        )

        await interaction.response.send_message(
            "🔒 Ticket closed."
        )

    @discord.ui.button(
        label="Delete",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="security_ticket_delete"
    )
    async def delete_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not (
            interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.administrator
        ):

            await interaction.response.send_message(
                "❌ You need Manage Channels.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🗑️ Deleting ticket..."
        )

        await asyncio.sleep(2)

        try:
            await interaction.channel.delete(
                reason="SECURITY ticket deleted"
            )
        except discord.HTTPException:
            pass


# ============================================================
# TICKET SETUP
# ============================================================

@bot.tree.command(
    name="ticket",
    description="Configure the ticket system"
)
@app_commands.describe(
    category="Ticket category",
    support_role="Staff support role"
)
@admin()
async def ticket(
    interaction: discord.Interaction,
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

    await interaction.response.send_message(
        f"✅ Ticket system configured.\n"
        f"📁 Category: {category.mention}\n"
        f"🛡️ Staff: {support_role.mention}",
        ephemeral=True
    )


# ============================================================
# TICKET PANEL
# ============================================================

@bot.tree.command(
    name="ticket-panel",
    description="Send the ticket creation panel"
)
@app_commands.describe(
    channel="Channel for the ticket panel"
)
@admin()
async def ticket_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    embed = discord.Embed(
        title="🎫 Support Tickets",
        description=(
            "Need help?\n\n"
            "Click **Create Ticket** below."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=TicketView()
    )

    await interaction.response.send_message(
        f"✅ Ticket panel sent to {channel.mention}.",
        ephemeral=True
    )


# ============================================================
# PERSISTENT VIEWS
# ============================================================

bot.add_view(
    VerifyView(0)
)

bot.add_view(
    TicketView()
)

bot.add_view(
    TicketControlView()
        )
# ============================================================
# PART 3 — CLEAN + SAFE WIPE
# ============================================================


# ============================================================
# CLEAN
# ============================================================

@bot.tree.command(
    name="clean",
    description="Delete messages from this channel"
)
@app_commands.describe(
    amount="Number of messages to delete (1-100)"
)
@moderator()
async def clean(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

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
            "❌ I don't have permission to delete messages.",
            ephemeral=True
        )


# ============================================================
# PURGE
# ============================================================

@bot.tree.command(
    name="purge",
    description="Delete messages from this channel"
)
@app_commands.describe(
    amount="Number of messages (1-100)"
)
@moderator()
async def purge(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        deleted = await interaction.channel.purge(
            limit=amount
        )

        await interaction.followup.send(
            f"🧹 Purged **{len(deleted)}** messages.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ I cannot delete messages here.",
            ephemeral=True
        )


# ============================================================
# WIPE CONFIRMATION
# ============================================================

class WipeView(discord.ui.View):

    def __init__(
        self,
        interaction_user_id,
        messages,
        channels,
        categories
    ):

        super().__init__(timeout=60)

        self.owner_id = interaction_user_id
        self.messages = messages
        self.channels = channels
        self.categories = categories

    async def interaction_check(
        self,
        interaction
    ):

        if interaction.user.id != self.owner_id:

            await interaction.response.send_message(
                "❌ Only the person who started the wipe can confirm it.",
                ephemeral=True
            )

            return False

        return True

    @discord.ui.button(
        label="YES — WIPE",
        emoji="⚠️",
        style=discord.ButtonStyle.danger
    )
    async def yes(
        self,
        interaction,
        button
    ):

        await interaction.response.edit_message(
            content="⏳ Wipe started...",
            embed=None,
            view=None
        )

        guild = interaction.guild

        # -------------------------
        # MESSAGES
        # -------------------------

        if self.messages:

            for channel in guild.text_channels:

                try:

                    await channel.purge(
                        limit=100
                    )

                except discord.HTTPException:
                    pass

        # -------------------------
        # CHANNELS
        # -------------------------

        if self.channels:

            for channel in list(guild.channels):

                if isinstance(
                    channel,
                    discord.CategoryChannel
                ):
                    continue

                try:
                    await channel.delete(
                        reason="SECURITY server wipe"
                    )
                except discord.HTTPException:
                    pass

        # -------------------------
        # CATEGORIES
        # -------------------------

        if self.categories:

            for category in list(guild.categories):

                try:
                    await category.delete(
                        reason="SECURITY server wipe"
                    )
                except discord.HTTPException:
                    pass

        await interaction.followup.send(
            "✅ Wipe completed.\n\n"
            "🛡️ Roles were NOT deleted.\n"
            "👥 Members were NOT removed.\n"
            "🏠 The Discord server itself was NOT deleted.",
            ephemeral=True
        )

    @discord.ui.button(
        label="NO — CANCEL",
        emoji="❌",
        style=discord.ButtonStyle.secondary
    )
    async def no(
        self,
        interaction,
        button
    ):

        await interaction.response.edit_message(
            content="❌ Wipe cancelled.",
            embed=None,
            view=None
        )


# ============================================================
# WIPE SERVER
# ============================================================

@bot.tree.command(
    name="wipe",
    description="Safely wipe selected server content"
)
@app_commands.describe(
    messages="Delete messages",
    channels="Delete channels",
    categories="Delete categories"
)
@admin()
async def wipe(
    interaction,
    messages: bool = False,
    channels: bool = False,
    categories: bool = False
):

    if not any([
        messages,
        channels,
        categories
    ]):

        await interaction.response.send_message(
            "❌ Select at least one option.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="⚠️ SECURITY SERVER WIPE",
        description=(
            "You are about to perform a destructive action.\n\n"
            f"🧹 Messages: **{'YES' if messages else 'NO'}**\n"
            f"📺 Channels: **{'YES' if channels else 'NO'}**\n"
            f"📁 Categories: **{'YES' if categories else 'NO'}**\n\n"
            "**This will NOT delete:**\n"
            "🛡️ Roles\n"
            "👥 Members\n"
            "🏠 The Discord server\n\n"
            "Press **YES — WIPE** only if you are sure."
        ),
        color=discord.Color.red()
    )

    await interaction.response.send_message(
        embed=embed,
        view=WipeView(
            interaction.user.id,
            messages,
            channels,
            categories
        ),
        ephemeral=True
    )


# ============================================================
# WIPE CHANNEL
# ============================================================

@bot.tree.command(
    name="wipe-channel",
    description="Delete and recreate a channel"
)
@app_commands.describe(
    channel="Channel to wipe"
)
@admin()
async def wipe_channel(
    interaction,
    channel: discord.TextChannel
):

    await interaction.response.send_message(
        f"⚠️ Wiping {channel.mention}...",
        ephemeral=True
    )

    try:

        new_channel = await channel.clone(
            reason="SECURITY channel wipe"
        )

        await new_channel.edit(
            position=channel.position,
            reason="SECURITY channel wipe"
        )

        await channel.delete(
            reason="SECURITY channel wipe"
        )

        await new_channel.send(
            "🧹 This channel has been wiped by **𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘**."
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ I don't have permission to wipe this channel.",
            ephemeral=True
        )


# ============================================================
# WIPE CATEGORY
# ============================================================

@bot.tree.command(
    name="wipe-category",
    description="Delete a category and its channels"
)
@app_commands.describe(
    category="Category to wipe"
)
@admin()
async def wipe_category(
    interaction,
    category: discord.CategoryChannel
):

    await interaction.response.send_message(
        f"⚠️ Wiping category **{category.name}**...",
        ephemeral=True
    )

    try:

        for channel in list(category.channels):

            try:
                await channel.delete(
                    reason="SECURITY category wipe"
                )
            except discord.HTTPException:
                pass

        await category.delete(
            reason="SECURITY category wipe"
        )

        await interaction.followup.send(
            "✅ Category wiped.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ I don't have permission to wipe this category.",
            ephemeral=True
        )
# ============================================================
# PART 4 — MODERATION + ROLE MANAGEMENT
# ============================================================


# ============================================================
# BAN
# ============================================================

@bot.tree.command(
    name="ban",
    description="Ban a member"
)
@app_commands.describe(
    member="Member to ban",
    reason="Reason"
)
@moderator()
async def ban(
    interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if not can_target(
        interaction.user,
        member
    ):

        await interaction.response.send_message(
            "❌ You cannot target this member.",
            ephemeral=True
        )
        return

    try:

        await member.ban(
            reason=reason,
            delete_message_seconds=86400
        )

        await interaction.response.send_message(
            f"🔨 Banned {member.mention}.\n"
            f"Reason: `{reason}`"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot ban that member.",
            ephemeral=True
        )


# ============================================================
# KICK
# ============================================================

@bot.tree.command(
    name="kick",
    description="Kick a member"
)
@app_commands.describe(
    member="Member to kick",
    reason="Reason"
)
@moderator()
async def kick(
    interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if not can_target(
        interaction.user,
        member
    ):

        await interaction.response.send_message(
            "❌ You cannot target this member.",
            ephemeral=True
        )
        return

    try:

        await member.kick(
            reason=reason
        )

        await interaction.response.send_message(
            f"👢 Kicked {member.mention}.\n"
            f"Reason: `{reason}`"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot kick that member.",
            ephemeral=True
        )


# ============================================================
# TIMEOUT
# ============================================================

@bot.tree.command(
    name="timeout",
    description="Timeout a member"
)
@app_commands.describe(
    member="Member",
    minutes="Timeout duration",
    reason="Reason"
)
@moderator()
async def timeout(
    interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason provided"
):

    if not can_target(
        interaction.user,
        member
    ):

        await interaction.response.send_message(
            "❌ You cannot target this member.",
            ephemeral=True
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

        await interaction.response.send_message(
            f"⏳ {member.mention} timed out for "
            f"**{minutes} minutes**."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot timeout that member.",
            ephemeral=True
        )


# ============================================================
# UNTIMEOUT
# ============================================================

@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout"
)
@app_commands.describe(
    member="Member"
)
@moderator()
async def untimeout(
    interaction,
    member: discord.Member
):

    if not can_target(
        interaction.user,
        member
    ):

        await interaction.response.send_message(
            "❌ You cannot target this member.",
            ephemeral=True
        )
        return

    try:

        await member.timeout(
            None,
            reason=f"Untimeout by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Removed timeout from {member.mention}."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot remove that timeout.",
            ephemeral=True
        )


# ============================================================
# WARN
# ============================================================

@bot.tree.command(
    name="warn",
    description="Warn a member"
)
@app_commands.describe(
    member="Member",
    reason="Reason"
)
@moderator()
async def warn(
    interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if not can_target(
        interaction.user,
        member
    ):

        await interaction.response.send_message(
            "❌ You cannot target this member.",
            ephemeral=True
        )
        return

    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        """
        INSERT INTO warnings
        (guild_id,user_id,moderator_id,reason,created_at)
        VALUES (?,?,?,?,?)
        """,
        (
            interaction.guild.id,
            member.id,
            interaction.user.id,
            reason,
            datetime.utcnow().isoformat()
        )
    )

    db.commit()
    db.close()

    await interaction.response.send_message(
        f"⚠️ Warned {member.mention}.\n"
        f"Reason: `{reason}`"
    )


# ============================================================
# WARNINGS
# ============================================================

@bot.tree.command(
    name="warnings",
    description="Show a member's warnings"
)
@app_commands.describe(
    member="Member"
)
@moderator()
async def warnings(
    interaction,
    member: discord.Member
):

    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        """
        SELECT reason, created_at
        FROM warnings
        WHERE guild_id=? AND user_id=?
        ORDER BY id DESC
        """,
        (
            interaction.guild.id,
            member.id
        )
    )

    rows = cur.fetchall()

    db.close()

    if not rows:

        await interaction.response.send_message(
            f"✅ {member.mention} has no warnings."
        )

        return

    text = ""

    for i, row in enumerate(rows[:20], 1):

        text += (
            f"**{i}.** {row[0]}\n"
            f"`{row[1][:10]}`\n\n"
        )

    embed = discord.Embed(
        title=f"⚠️ Warnings — {member}",
        description=text,
        color=discord.Color.orange()
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# CLEAR WARNINGS
# ============================================================

@bot.tree.command(
    name="clearwarnings",
    description="Clear a member's warnings"
)
@app_commands.describe(
    member="Member"
)
@moderator()
async def clearwarnings(
    interaction,
    member: discord.Member
):

    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        """
        DELETE FROM warnings
        WHERE guild_id=? AND user_id=?
        """,
        (
            interaction.guild.id,
            member.id
        )
    )

    db.commit()
    db.close()

    await interaction.response.send_message(
        f"✅ Cleared warnings for {member.mention}."
    )


# ============================================================
# AUTOROLE
# ============================================================

@bot.tree.command(
    name="autorole",
    description="Set the automatic join role"
)
@app_commands.describe(
    role="Role given to new members"
)
@admin()
async def autorole(
    interaction,
    role: discord.Role
):

    if role >= interaction.guild.me.top_role:

        await interaction.response.send_message(
            "❌ That role must be below my bot role.",
            ephemeral=True
        )
        return

    set_setting(
        interaction.guild.id,
        "autorole",
        role.id
    )

    await interaction.response.send_message(
        f"✅ New members will receive {role.mention}."
    )


# ============================================================
# ADD ROLE
# ============================================================

@bot.tree.command(
    name="addrole",
    description="Give a role to a member"
)
@app_commands.describe(
    member="Member",
    role="Role"
)
@moderator()
async def addrole(
    interaction,
    member: discord.Member,
    role: discord.Role
):

    if role >= interaction.guild.me.top_role:

        await interaction.response.send_message(
            "❌ That role is too high for me.",
            ephemeral=True
        )
        return

    if not can_target(
        interaction.user,
        member
    ):

        await interaction.response.send_message(
            "❌ You cannot target that member.",
            ephemeral=True
        )
        return

    try:

        await member.add_roles(role)

        await interaction.response.send_message(
            f"✅ Added {role.mention} to {member.mention}."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot give that role.",
            ephemeral=True
        )


# ============================================================
# REMOVE ROLE
# ============================================================

@bot.tree.command(
    name="removerole",
    description="Remove a role from a member"
)
@app_commands.describe(
    member="Member",
    role="Role"
)
@moderator()
async def removerole(
    interaction,
    member: discord.Member,
    role: discord.Role
):

    if role >= interaction.guild.me.top_role:

        await interaction.response.send_message(
            "❌ That role is too high for me.",
            ephemeral=True
        )
        return

    try:

        await member.remove_roles(role)

        await interaction.response.send_message(
            f"✅ Removed {role.mention} from {member.mention}."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot remove that role.",
            ephemeral=True
        )


# ============================================================
# ROLE INFO
# ============================================================

@bot.tree.command(
    name="roleinfo",
    description="Show role information"
)
@app_commands.describe(
    role="Role"
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
        name="Mentionable",
        value=str(role.mentionable),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )
# ============================================================
# PART 5 — AUTOMOD + LEVELING
# ============================================================


# ============================================================
# AUTOMOD SETTINGS
# ============================================================

automod_group = app_commands.Group(
    name="automod",
    description="Configure AutoMod"
)


@automod_group.command(
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

    await interaction.response.send_message(
        "🛡️ AutoMod enabled.",
        ephemeral=True
    )


@automod_group.command(
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

    await interaction.response.send_message(
        "🛡️ AutoMod disabled.",
        ephemeral=True
    )


@automod_group.command(
    name="links",
    description="Toggle link protection"
)
@app_commands.describe(
    enabled="Enable or disable"
)
@admin()
async def automod_links(
    interaction,
    enabled: bool
):

    set_setting(
        interaction.guild.id,
        "automod_links",
        int(enabled)
    )

    await interaction.response.send_message(
        f"🔗 Link protection: "
        f"**{'ON' if enabled else 'OFF'}**",
        ephemeral=True
    )


@automod_group.command(
    name="invites",
    description="Toggle Discord invite protection"
)
@app_commands.describe(
    enabled="Enable or disable"
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

    await interaction.response.send_message(
        f"🚫 Invite protection: "
        f"**{'ON' if enabled else 'OFF'}",
        ephemeral=True
    )


@automod_group.command(
    name="caps",
    description="Toggle excessive caps protection"
)
@app_commands.describe(
    enabled="Enable or disable"
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

    await interaction.response.send_message(
        f"🔠 Caps protection: "
        f"**{'ON' if enabled else 'OFF'}",
        ephemeral=True
    )


@automod_group.command(
    name="spam",
    description="Toggle spam protection"
)
@app_commands.describe(
    enabled="Enable or disable"
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

    await interaction.response.send_message(
        f"💬 Spam protection: "
        f"**{'ON' if enabled else 'OFF'}",
        ephemeral=True
    )


bot.tree.add_command(automod_group)


# ============================================================
# AUTOMOD ENGINE
# ============================================================

spam_cache = {}


async def run_automod(message):

    if message.author.bot:
        return

    s = get_settings(
        message.guild.id
    )

    if not s["automod_enabled"]:
        return

    content = message.content

    # Discord invites
    if s["automod_invites"]:

        if (
            "discord.gg/" in content.lower()
            or "discord.com/invite/" in content.lower()
        ):

            try:
                await message.delete()

                await message.channel.send(
                    f"🚫 {message.author.mention}, Discord invites "
                    "are not allowed here.",
                    delete_after=5
                )

            except discord.HTTPException:
                pass

            return

    # Links
    if s["automod_links"]:

        if re.search(
            r"https?://\S+",
            content,
            re.IGNORECASE
        ):

            try:
                await message.delete()

                await message.channel.send(
                    f"🚫 {message.author.mention}, links are not allowed.",
                    delete_after=5
                )

            except discord.HTTPException:
                pass

            return

    # Caps
    if s["automod_caps"]:

        letters = [
            c for c in content
            if c.isalpha()
        ]

        if len(letters) >= 10:

            upper = sum(
                c.isupper()
                for c in letters
            )

            if upper / len(letters) >= 0.8:

                try:
                    await message.delete()

                    await message.channel.send(
                        f"🔠 {message.author.mention}, "
                        "please don't use excessive caps.",
                        delete_after=5
                    )

                except discord.HTTPException:
                    pass

                return

    # Spam
    if s["automod_spam"]:

        key = (
            message.guild.id,
            message.author.id
        )

        now = asyncio.get_event_loop().time()

        history = spam_cache.get(
            key,
            []
        )

        history = [
            t for t in history
            if now - t < 5
        ]

        history.append(now)

        spam_cache[key] = history

        if len(history) >= 5:

            try:

                await message.delete()

                await message.channel.send(
                    f"💬 {message.author.mention}, slow down!",
                    delete_after=5
                )

            except discord.HTTPException:
                pass


# ============================================================
# LEVELING
# ============================================================

xp_cooldowns = {}


async def add_xp(message):

    if message.author.bot:
        return

    s = get_settings(
        message.guild.id
    )

    if not s["xp_enabled"]:
        return

    key = (
        message.guild.id,
        message.author.id
    )

    now = asyncio.get_event_loop().time()

    last = xp_cooldowns.get(
        key,
        0
    )

    if now - last < s["xp_cooldown"]:
        return

    xp_cooldowns[key] = now

    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO levels
        (guild_id,user_id,xp,level)
        VALUES (?,?,0,0)
        """,
        (
            message.guild.id,
            message.author.id
        )
    )

    cur.execute(
        """
        SELECT xp, level
        FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        (
            message.guild.id,
            message.author.id
        )
    )

    row = cur.fetchone()

    xp = row[0] + s["xp_per_message"]
    level = row[1]

    needed = (
        (level + 1) * 100
    )

    if xp >= needed:

        level += 1

        await message.channel.send(
            f"🎉 {message.author.mention} reached "
            f"**Level {level}**!",
            delete_after=8
        )

    cur.execute(
        """
        UPDATE levels
        SET xp=?, level=?
        WHERE guild_id=? AND user_id=?
        """,
        (
            xp,
            level,
            message.guild.id,
            message.author.id
        )
    )

    db.commit()
    db.close()


# ============================================================
# LEVELING COMMAND
# ============================================================

@bot.tree.command(
    name="leveling",
    description="Enable or disable leveling"
)
@app_commands.describe(
    enabled="Enable or disable leveling"
)
@admin()
async def leveling(
    interaction,
    enabled: bool
):

    set_setting(
        interaction.guild.id,
        "xp_enabled",
        int(enabled)
    )

    await interaction.response.send_message(
        f"📈 Leveling: "
        f"**{'ON' if enabled else 'OFF'}**",
        ephemeral=True
    )


# ============================================================
# LEVEL
# ============================================================

@bot.tree.command(
    name="level",
    description="Show a member's level"
)
@app_commands.describe(
    member="Member"
)
async def level(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        """
        SELECT xp, level
        FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        (
            interaction.guild.id,
            member.id
        )
    )

    row = cur.fetchone()

    db.close()

    if not row:

        xp = 0
        level_number = 0

    else:

        xp = row[0]
        level_number = row[1]

    await interaction.response.send_message(
        f"📈 {member.mention}\n"
        f"Level: **{level_number}**\n"
        f"XP: **{xp}**"
    )


# ============================================================
# RANK
# ============================================================

@bot.tree.command(
    name="rank",
    description="Show your server rank"
)
async def rank(
    interaction
):

    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute(
        """
        SELECT user_id, xp
        FROM levels
        WHERE guild_id=?
        ORDER BY xp DESC
        """,
        (interaction.guild.id,)
    )

    rows = cur.fetchall()

    db.close()

    rank_number = None

    for i, row in enumerate(rows, 1):

        if row[0] == interaction.user.id:

            rank_number = i
            xp = row[1]
            break

    if rank_number is None:

        await interaction.response.send_message(
            "📈 You haven't earned any XP yet."
        )

        return

    await interaction.response.send_message(
        f"🏆 Your rank is **#{rank_number}**\n"
        f"⭐ XP: **{xp}**"
    )
# ============================================================
# PART 6 — CHATBOT + SERVER COMMANDS + HELP + START
# ============================================================


# ============================================================
# FREE CHATBOT
# ============================================================

def chatbot_reply(text, member):

    text = text.lower().strip()

    if any(x in text for x in [
        "hello",
        "hi",
        "hey",
        "yo",
        "sup"
    ]):
        return f"Hey {member.mention}! 👋"

    if "your name" in text:
        return "I'm **𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘** 🛡️"

    if "who are you" in text:
        return "I'm **𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘**, your server assistant. 🛡️"

    if "how are you" in text:
        return "I'm doing great! 🛡️ Ready to protect the server."

    if "rules" in text:
        return "Make sure you read the server rules before chatting. 📜"

    if "verify" in text:
        return "Click the verification button to get verified. ✅"

    if "ticket" in text:
        return "Need staff help? 🎫 Open a ticket."

    if "help" in text:
        return "Use `/help` to see all my commands."

    if "thanks" in text or "thank you" in text:
        return "You're welcome! 😎"

    if "good bot" in text:
        return "Thank you! 🫡"

    if text.endswith("?"):
        return "Hmm 🤔 I'm not sure about that yet."

    return random.choice([
        "Got it! 👍",
        "Interesting 👀",
        "I'm listening.",
        "Alright 😎",
        "Got you! 🛡️",
        "Tell me more!",
        "Okay! 👍"
    ])


chatbot_cooldowns = {}


# ============================================================
# CHATBOT SETUP
# ============================================================

@bot.tree.command(
    name="chatbot",
    description="Configure the automatic chatbot"
)
@app_commands.describe(
    channel="Channel where SECURITY will automatically chat"
)
@admin()
async def chatbot(
    interaction,
    channel: discord.TextChannel
):

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

    await interaction.response.send_message(
        f"🤖 Automatic chatbot enabled in {channel.mention}!\n\n"
        "SECURITY will automatically reply to messages there.",
        ephemeral=True
    )


# ============================================================
# CHATBOT DISABLE
# ============================================================

@bot.tree.command(
    name="chatbot-disable",
    description="Disable the automatic chatbot"
)
@admin()
async def chatbot_disable(
    interaction
):

    set_setting(
        interaction.guild.id,
        "chatbot_enabled",
        0
    )

    await interaction.response.send_message(
        "🛑 Automatic chatbot disabled.",
        ephemeral=True
    )


# ============================================================
# SAY
# ============================================================

@bot.tree.command(
    name="say",
    description="Make SECURITY send a message"
)
@app_commands.describe(
    message="Message to send",
    channel="Channel to send it in"
)
@admin()
async def say(
    interaction,
    message: str,
    channel: discord.TextChannel = None
):

    channel = channel or interaction.channel

    try:

        await channel.send(
            message
        )

        await interaction.response.send_message(
            f"✅ Sent in {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I cannot send messages there.",
            ephemeral=True
        )


# ============================================================
# PING
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
        f"🏓 Pong! `{latency}ms`"
    )


# ============================================================
# SERVER INFO
# ============================================================

@bot.tree.command(
    name="serverinfo",
    description="Show server information"
)
async def serverinfo(interaction):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"🛡️ {guild.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Members",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="📺 Channels",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="🎭 Roles",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="🆔 ID",
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


# ============================================================
# USER INFO
# ============================================================

@bot.tree.command(
    name="userinfo",
    description="Show user information"
)
@app_commands.describe(
    member="Member"
)
async def userinfo(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    roles = member.roles[1:]

    role_text = (
        " ".join(
            role.mention
            for role in roles[-10:]
        )
        if roles
        else "None"
    )

    embed = discord.Embed(
        title=f"👤 {member}",
        color=member.color
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="🆔 ID",
        value=str(member.id),
        inline=False
    )

    embed.add_field(
        name="📅 Joined",
        value=(
            discord.utils.format_dt(
                member.joined_at,
                "F"
            )
            if member.joined_at
            else "Unknown"
        ),
        inline=False
    )

    embed.add_field(
        name="🎭 Roles",
        value=role_text,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# AVATAR
# ============================================================

@bot.tree.command(
    name="avatar",
    description="Show a user's avatar"
)
@app_commands.describe(
    member="Member"
)
async def avatar(
    interaction,
    member: discord.Member = None
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


# ============================================================
# MEMBER COUNT
# ============================================================

@bot.tree.command(
    name="membercount",
    description="Show the member count"
)
async def membercount(
    interaction
):

    await interaction.response.send_message(
        f"👥 This server has "
        f"**{interaction.guild.member_count}** members."
    )


# ============================================================
# HELP
# ============================================================

@bot.tree.command(
    name="help",
    description="Show SECURITY commands"
)
async def help_command(
    interaction
):

    embed = discord.Embed(
        title="🛡️ 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘",
        description="Server protection and management commands.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome",
        value=(
            "`/welcome setup`\n"
            "`/welcome enable`\n"
            "`/welcome disable`\n"
            "`/welcome test`"
        ),
        inline=False
    )

    embed.add_field(
        name="👋 Goodbye",
        value=(
            "`/bye setup`\n"
            "`/bye enable`\n"
            "`/bye disable`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Verification",
        value="`/verify`",
        inline=True
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "`/ticket`\n"
            "`/ticket-panel`"
        ),
        inline=True
    )

    embed.add_field(
        name="🤖 Chatbot",
        value=(
            "`/chatbot`\n"
            "`/chatbot-disable`"
        ),
        inline=True
    )

    embed.add_field(
        name="🧹 Cleaning",
        value=(
            "`/clean`\n"
            "`/purge`\n"
            "`/wipe`\n"
            "`/wipe-channel`\n"
            "`/wipe-category`"
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
            "`/clearwarnings`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎭 Roles",
        value=(
            "`/autorole`\n"
            "`/addrole`\n"
            "`/removerole`\n"
            "`/roleinfo`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ AutoMod",
        value=(
            "`/automod enable`\n"
            "`/automod disable`\n"
            "`/automod links`\n"
            "`/automod invites`\n"
            "`/automod caps`\n"
            "`/automod spam`"
        ),
        inline=False
    )

    embed.add_field(
        name="📈 Leveling",
        value=(
            "`/leveling`\n"
            "`/level`\n"
            "`/rank`"
        ),
        inline=True
    )

    embed.add_field(
        name="📊 Utility",
        value=(
            "`/ping`\n"
            "`/serverinfo`\n"
            "`/userinfo`\n"
            "`/avatar`\n"
            "`/membercount`\n"
            "`/say`"
        ),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# AUTOMATIC MESSAGE HANDLER
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    # --------------------------------
    # AUTOMOD FIRST
    # --------------------------------

    try:

        await run_automod(message)

    except Exception as e:

        print(
            f"AutoMod error: {e}"
        )

    # --------------------------------
    # CHATBOT
    # --------------------------------

    s = get_settings(
        message.guild.id
    )

    if (
        s["chatbot_enabled"]
        and s["chatbot_channel"] == message.channel.id
    ):

        user_id = message.author.id

        now = asyncio.get_event_loop().time()

        last = chatbot_cooldowns.get(
            user_id,
            0
        )

        if now - last >= 3:

            chatbot_cooldowns[user_id] = now

            try:

                await asyncio.sleep(1)

                response = chatbot_reply(
                    message.content,
                    message.author
                )

                await message.reply(
                    response,
                    mention_author=False
                )

            except discord.HTTPException:
                pass

    # --------------------------------
    # LEVELING
    # --------------------------------

    try:

        await add_xp(message)

    except Exception as e:

        print(
            f"Leveling error: {e}"
        )

    await bot.process_commands(
        message
    )


# ============================================================
# COMMAND ERROR HANDLER
# ============================================================

@bot.tree.error
async def command_error(
    interaction,
    error
):

    print(
        f"❌ Command error: {repr(error)}"
    )

    if isinstance(
        error,
        app_commands.CheckFailure
    ):

        text = (
            "❌ You don't have permission "
            "to use this command."
        )

    elif isinstance(
        error,
        app_commands.CommandOnCooldown
    ):

        text = (
            "⏳ Please wait before trying again."
        )

    else:

        text = (
            "❌ Something went wrong. "
            "Check the Railway logs."
        )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                text,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                text,
                ephemeral=True
            )

    except Exception:
        pass


# ============================================================
# TOKEN
# ============================================================

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if not TOKEN:

    raise RuntimeError(
        "❌ DISCORD_TOKEN is missing from Railway Variables."
    )


# ============================================================
# START
# ============================================================

bot.run(TOKEN)    
