import os
import sqlite3
import asyncio
import random
import re
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


# =========================
# BOT
# =========================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================
# DATABASE
# =========================

DB = "security.db"

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER PRIMARY KEY,

    welcome_enabled INTEGER DEFAULT 0,
    welcome_channel INTEGER,
    welcome_message TEXT DEFAULT 'Welcome {user} to {server}!',

    welcome_image TEXT,
    welcome_avatar INTEGER DEFAULT 1,

    bye_enabled INTEGER DEFAULT 0,
    bye_channel INTEGER,
    bye_message TEXT DEFAULT 'Goodbye {user}!',

    bye_image TEXT,
    bye_avatar INTEGER DEFAULT 1,

    verify_channel INTEGER,
    verify_role INTEGER,
    verify_message TEXT DEFAULT 'Click the button below to verify.',

    ticket_category INTEGER,
    ticket_support INTEGER,

    chatbot_enabled INTEGER DEFAULT 0,
    chatbot_channel INTEGER,
    chatbot_prompt TEXT DEFAULT 'You are a friendly Discord server assistant. Keep replies helpful and reasonably short.',

    autorole INTEGER,

    xp_enabled INTEGER DEFAULT 0,
    xp_per_message INTEGER DEFAULT 10,
    xp_cooldown INTEGER DEFAULT 60,

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
    PRIMARY KEY(guild_id, user_id)
)
""")

db.commit()


# =========================
# DATABASE HELPERS
# =========================

def setup_guild(guild_id):
    cur.execute(
        "INSERT OR IGNORE INTO settings (guild_id) VALUES (?)",
        (guild_id,)
    )
    db.commit()


def settings(guild_id):
    setup_guild(guild_id)

    cur.execute(
        "SELECT * FROM settings WHERE guild_id=?",
        (guild_id,)
    )

    return cur.fetchone()


def set_setting(guild_id, column, value):
    setup_guild(guild_id)

    allowed = {
        "welcome_enabled",
        "welcome_channel",
        "welcome_message",
        "welcome_image",
        "welcome_avatar",

        "bye_enabled",
        "bye_channel",
        "bye_message",
        "bye_image",
        "bye_avatar",

        "verify_channel",
        "verify_role",
        "verify_message",

        "ticket_category",
        "ticket_support",

        "chatbot_enabled",
        "chatbot_channel",
        "chatbot_prompt",

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

    if column not in allowed:
        raise ValueError("Invalid setting.")

    cur.execute(
        f"UPDATE settings SET {column}=? WHERE guild_id=?",
        (value, guild_id)
    )

    db.commit()


def fmt(text, member, guild):
    if not text:
        return ""

    return (
        text
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", guild.name)
        .replace("{member_count}", str(guild.member_count))
        .replace("{user_id}", str(member.id))
    )


# =========================
# PERMISSIONS
# =========================

def admin():
    async def predicate(interaction):
        if not interaction.user.guild_permissions.administrator:
            raise app_commands.CheckFailure(
                "Administrator permission required."
            )
        return True

    return app_commands.check(predicate)


def moderator():
    async def predicate(interaction):
        if not (
            interaction.user.guild_permissions.manage_messages
            or interaction.user.guild_permissions.moderate_members
            or interaction.user.guild_permissions.administrator
        ):
            raise app_commands.CheckFailure(
                "Moderator permission required."
            )
        return True

    return app_commands.check(predicate)


def can_target(interaction, member):
    if member == interaction.user:
        return False, "You cannot target yourself."

    if member == interaction.guild.owner:
        return False, "You cannot target the server owner."

    if member.top_role >= interaction.user.top_role:
        return False, "That member has an equal or higher role than you."

    if member.top_role >= interaction.guild.me.top_role:
        return False, "That member has an equal or higher role than the bot."

    return True, None


# =========================
# READY
# =========================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print("Slash sync error:", e)

    await bot.change_presence(
        activity=discord.Game("/help • SECURITY")
    )

    print(f"✅ SECURITY is online as {bot.user}")


# =========================
# WELCOME
# =========================

welcome = app_commands.Group(
    name="welcome",
    description="Welcome system"
)


@welcome.command(name="setup")
@app_commands.describe(
    channel="Welcome channel",
    message="Welcome message",
    image="Optional image URL",
    avatar="Show the member's avatar"
)
@admin()
async def welcome_setup(
    interaction,
    channel: discord.TextChannel,
    message: str,
    image: str = None,
    avatar: bool = True
):
    set_setting(interaction.guild.id, "welcome_channel", channel.id)
    set_setting(interaction.guild.id, "welcome_message", message)
    set_setting(interaction.guild.id, "welcome_image", image)
    set_setting(interaction.guild.id, "welcome_avatar", int(avatar))

    embed = discord.Embed(
        title="Welcome System",
        description="Welcome system configured successfully.",
        color=discord.Color.blurple()
    )

    embed.add_field(name="Channel", value=channel.mention)
    embed.add_field(name="Avatar", value="Enabled" if avatar else "Disabled")

    if image:
        embed.add_field(name="Custom Image", value="Configured")

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@welcome.command(name="enable")
@admin()
async def welcome_enable(interaction):
    set_setting(interaction.guild.id, "welcome_enabled", 1)

    await interaction.response.send_message(
        "✅ Welcome messages enabled.",
        ephemeral=True
    )


@welcome.command(name="disable")
@admin()
async def welcome_disable(interaction):
    set_setting(interaction.guild.id, "welcome_enabled", 0)

    await interaction.response.send_message(
        "✅ Welcome messages disabled.",
        ephemeral=True
    )


@welcome.command(name="message")
@app_commands.describe(message="New welcome message")
@admin()
async def welcome_message(interaction, message: str):
    set_setting(interaction.guild.id, "welcome_message", message)

    await interaction.response.send_message(
        f"✅ Welcome message changed.\n\nPreview:\n{fmt(message, interaction.user, interaction.guild)}",
        ephemeral=True
    )


@welcome.command(name="image")
@app_commands.describe(
    image="Image URL. Leave empty to remove the image."
)
@admin()
async def welcome_image(interaction, image: str = None):
    set_setting(interaction.guild.id, "welcome_image", image)

    await interaction.response.send_message(
        "✅ Welcome image updated.",
        ephemeral=True
    )


@welcome.command(name="test")
@admin()
async def welcome_test(interaction):
    row = settings(interaction.guild.id)

    embed = discord.Embed(
        description=fmt(
            row["welcome_message"],
            interaction.user,
            interaction.guild
        ),
        color=discord.Color.blurple(),
        timestamp=datetime.utcnow()
    )

    if row["welcome_avatar"]:
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

    if row["welcome_image"]:
        embed.set_image(url=row["welcome_image"])

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


bot.tree.add_command(welcome)


# =========================
# BYE
# =========================

bye = app_commands.Group(
    name="bye",
    description="Goodbye system"
)


@bye.command(name="setup")
@app_commands.describe(
    channel="Goodbye channel",
    message="Goodbye message",
    image="Optional image URL",
    avatar="Show the member's avatar"
)
@admin()
async def bye_setup(
    interaction,
    channel: discord.TextChannel,
    message: str,
    image: str = None,
    avatar: bool = True
):
    set_setting(interaction.guild.id, "bye_channel", channel.id)
    set_setting(interaction.guild.id, "bye_message", message)
    set_setting(interaction.guild.id, "bye_image", image)
    set_setting(interaction.guild.id, "bye_avatar", int(avatar))

    await interaction.response.send_message(
        "✅ Goodbye system configured.",
        ephemeral=True
    )


@bye.command(name="enable")
@admin()
async def bye_enable(interaction):
    set_setting(interaction.guild.id, "bye_enabled", 1)

    await interaction.response.send_message(
        "✅ Goodbye messages enabled.",
        ephemeral=True
    )


@bye.command(name="disable")
@admin()
async def bye_disable(interaction):
    set_setting(interaction.guild.id, "bye_enabled", 0)

    await interaction.response.send_message(
        "✅ Goodbye messages disabled.",
        ephemeral=True
    )


@bye.command(name="message")
@app_commands.describe(message="New goodbye message")
@admin()
async def bye_message(interaction, message: str):
    set_setting(interaction.guild.id, "bye_message", message)

    await interaction.response.send_message(
        "✅ Goodbye message changed.",
        ephemeral=True
    )


@bye.command(name="image")
@app_commands.describe(
    image="Image URL. Leave empty to remove."
)
@admin()
async def bye_image(interaction, image: str = None):
    set_setting(interaction.guild.id, "bye_image", image)

    await interaction.response.send_message(
        "✅ Goodbye image updated.",
        ephemeral=True
    )


@bye.command(name="test")
@admin()
async def bye_test(interaction):
    row = settings(interaction.guild.id)

    embed = discord.Embed(
        description=fmt(
            row["bye_message"],
            interaction.user,
            interaction.guild
        ),
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )

    if row["bye_avatar"]:
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

    if row["bye_image"]:
        embed.set_image(url=row["bye_image"])

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


bot.tree.add_command(bye)


# =========================
# MEMBER JOIN / LEAVE
# =========================

@bot.event
async def on_member_join(member):
    row = settings(member.guild.id)

    # Autorole
    if row["autorole"]:
        role = member.guild.get_role(row["autorole"])

        if role:
            try:
                await member.add_roles(
                    role,
                    reason="SECURITY autorole"
                )
            except Exception:
                pass

    if not row["welcome_enabled"]:
        return

    channel = member.guild.get_channel(
        row["welcome_channel"]
    )

    if not channel:
        return

    embed = discord.Embed(
        description=fmt(
            row["welcome_message"],
            member,
            member.guild
        ),
        color=discord.Color.blurple(),
        timestamp=datetime.utcnow()
    )

    if row["welcome_avatar"]:
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

    if row["welcome_image"]:
        embed.set_image(
            url=row["welcome_image"]
        )

    try:
        await channel.send(embed=embed)
    except Exception:
        pass


@bot.event
async def on_member_remove(member):
    row = settings(member.guild.id)

    if not row["bye_enabled"]:
        return

    channel = member.guild.get_channel(
        row["bye_channel"]
    )

    if not channel:
        return

    embed = discord.Embed(
        description=fmt(
            row["bye_message"],
            member,
            member.guild
        ),
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )

    if row["bye_avatar"]:
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

    if row["bye_image"]:
        embed.set_image(
            url=row["bye_image"]
        )

    try:
        await channel.send(embed=embed)
    except Exception:
        pass
# =========================
# VERIFICATION
# =========================

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.success,
        custom_id="security_verify"
    )
    async def verify_button(self, interaction, button):
        row = settings(interaction.guild.id)

        role_id = row["verify_role"]

        if not role_id:
            await interaction.response.send_message(
                "❌ Verification role is not configured.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(role_id)

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
                "✅ You are now verified!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I cannot give that role. Move my bot role above the verification role.",
                ephemeral=True
            )


@bot.tree.command(
    name="verify",
    description="Verification system"
)
@app_commands.describe(
    channel="Verification channel",
    role="Role given after verification",
    message="Verification message"
)
@admin()
async def verify(
    interaction,
    channel: discord.TextChannel,
    role: discord.Role,
    message: str = "Click the button below to verify."
):
    set_setting(interaction.guild.id, "verify_channel", channel.id)
    set_setting(interaction.guild.id, "verify_role", role.id)
    set_setting(interaction.guild.id, "verify_message", message)

    embed = discord.Embed(
        title="Verification",
        description=message,
        color=discord.Color.green()
    )

    await channel.send(
        embed=embed,
        view=VerifyView()
    )

    await interaction.response.send_message(
        f"✅ Verification panel sent to {channel.mention}.",
        ephemeral=True
    )


# =========================
# TICKETS
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
    async def create_ticket(self, interaction, button):
        guild = interaction.guild
        row = settings(guild.id)

        category = None

        if row["ticket_category"]:
            category = guild.get_channel(
                row["ticket_category"]
            )

        existing = discord.utils.find(
            lambda c:
                isinstance(c, discord.TextChannel)
                and c.topic == f"ticket:{interaction.user.id}",
            guild.text_channels
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
            interaction.user: discord.PermissionOverwrite(
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

        support_role = None

        if row["ticket_support"]:
            support_role = guild.get_role(
                row["ticket_support"]
            )

            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        try:
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
                    "A staff member will help you soon."
                ),
                color=discord.Color.blurple()
            )

            await channel.send(
                embed=embed,
                view=TicketControlView()
            )

            await interaction.response.send_message(
                f"✅ Ticket created: {channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I need Manage Channels permission.",
                ephemeral=True
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
    async def close(self, interaction, button):
        owner_id = None

        if interaction.channel.topic:
            if interaction.channel.topic.startswith("ticket:"):
                try:
                    owner_id = int(
                        interaction.channel.topic.split(":")[1]
                    )
                except:
                    pass

        if (
            owner_id != interaction.user.id
            and not interaction.user.guild_permissions.manage_channels
        ):
            await interaction.response.send_message(
                "❌ You cannot close this ticket.",
                ephemeral=True
            )
            return

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            view_channel=False
        )

        await interaction.response.send_message(
            "🔒 Ticket closed."
        )


    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="security_ticket_delete"
    )
    async def delete(self, interaction, button):
        if not (
            interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "❌ Staff only.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🗑️ Deleting ticket..."
        )

        await asyncio.sleep(1)

        try:
            await interaction.channel.delete(
                reason="SECURITY ticket deletion"
            )
        except:
            pass


@bot.tree.command(
    name="ticket",
    description="Ticket system"
)
@app_commands.describe(
    category="Ticket category",
    support_role="Support role"
)
@admin()
async def ticket(
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

    await interaction.response.send_message(
        "✅ Ticket system configured.",
        ephemeral=True
    )


@bot.tree.command(
    name="ticket-panel",
    description="Send the ticket panel"
)
@app_commands.describe(
    channel="Channel where the panel will be sent"
)
@admin()
async def ticket_panel(
    interaction,
    channel: discord.TextChannel = None
):
    channel = channel or interaction.channel

    embed = discord.Embed(
        title="🎫 Support",
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
        "✅ Ticket panel sent.",
        ephemeral=True
    )


# Persistent views
bot.add_view(VerifyView())
bot.add_view(TicketView())
bot.add_view(TicketControlView())
# =========================
# CLEAN / PURGE
# =========================

async def clean_messages(channel, amount):
    deleted = await channel.purge(
        limit=amount,
        reason="SECURITY clean/purge"
    )

    return len(deleted)


@bot.tree.command(
    name="clean",
    description="Delete messages"
)
@app_commands.describe(
    amount="Number of messages to delete (1-100)"
)
@moderator()
async def clean(interaction, amount: app_commands.Range[int, 1, 100]):
    if not interaction.channel.permissions_for(
        interaction.guild.me
    ).manage_messages:
        await interaction.response.send_message(
            "❌ I need Manage Messages permission.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    try:
        count = await clean_messages(
            interaction.channel,
            amount
        )

        await interaction.followup.send(
            f"🧹 Deleted **{count}** messages.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to delete messages.",
            ephemeral=True
        )


@bot.tree.command(
    name="purge",
    description="Delete messages"
)
@app_commands.describe(
    amount="Number of messages to delete (1-100)"
)
@moderator()
async def purge(interaction, amount: app_commands.Range[int, 1, 100]):
    await clean(interaction, amount)


# =========================
# WIPE CONFIRMATION
# =========================

class WipeConfirmView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.value = None

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the person who started this wipe can confirm it.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="YES — WIPE",
        style=discord.ButtonStyle.danger
    )
    async def yes(self, interaction, button):
        self.value = True

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="🧨 Wipe confirmed. Starting...",
            view=self
        )

        self.stop()

    @discord.ui.button(
        label="NO — CANCEL",
        style=discord.ButtonStyle.secondary
    )
    async def no(self, interaction, button):
        self.value = False

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

    if not any([messages, channels, categories]):
        await interaction.response.send_message(
            "❌ Select at least one option.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="⚠️ SERVER WIPE WARNING",
        description=(
            "**This will permanently delete the selected content.**\n\n"
            f"🧹 Messages: {'YES' if messages else 'NO'}\n"
            f"📁 Channels: {'YES' if channels else 'NO'}\n"
            f"📂 Categories: {'YES' if categories else 'NO'}\n\n"
            "**IMPORTANT:**\n"
            "• The Discord server itself will NOT be deleted.\n"
            "• Roles will NOT be deleted.\n"
            "• Members will NOT be banned or removed.\n"
            "• @everyone will NOT be deleted.\n\n"
            "Press **YES — WIPE** only if you are sure."
        ),
        color=discord.Color.red()
    )

    view = WipeConfirmView(interaction.user.id)

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

    await view.wait()

    if view.value is not True:
        return

    guild = interaction.guild

    deleted_messages = 0
    deleted_channels = 0
    deleted_categories = 0

    # =========================
    # DELETE MESSAGES
    # =========================

    if messages:
        for channel in list(guild.text_channels):
            try:
                while True:
                    deleted = await channel.purge(
                        limit=100,
                        reason="SECURITY server wipe"
                    )

                    deleted_messages += len(deleted)

                    if len(deleted) < 100:
                        break

                    await asyncio.sleep(0.5)

            except Exception:
                continue

    # =========================
    # DELETE CHANNELS
    # =========================

    if channels:
        for channel in list(guild.channels):

            # NEVER delete categories here.
            if isinstance(channel, discord.CategoryChannel):
                continue

            try:
                await channel.delete(
                    reason="SECURITY server wipe"
                )

                deleted_channels += 1

            except Exception:
                continue

            await asyncio.sleep(0.3)

    # =========================
    # DELETE CATEGORIES
    # =========================

    # FIX:
    # This runs even when channels=True.
    # Categories are deliberately handled separately.
    if categories:
        for category in list(guild.categories):
            try:
                await category.delete(
                    reason="SECURITY server wipe"
                )

                deleted_categories += 1

            except Exception:
                continue

            await asyncio.sleep(0.3)

    result = discord.Embed(
        title="✅ Wipe Complete",
        description=(
            "The selected content has been wiped.\n\n"
            f"🧹 Messages deleted: **{deleted_messages}**\n"
            f"📺 Channels deleted: **{deleted_channels}**\n"
            f"📂 Categories deleted: **{deleted_categories}**\n\n"
            "🔐 **Roles were NOT deleted.**\n"
            "👥 **Members were NOT removed.**\n"
            "🏠 **The Discord server itself was NOT deleted.**"
        ),
        color=discord.Color.green()
    )

    await interaction.followup.send(
        embed=result,
        ephemeral=True
    )


# =========================
# WIPE CHANNEL
# =========================

class ChannelWipeView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=30)
        self.owner_id = owner_id
        self.confirmed = False

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ You cannot confirm this.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="YES",
        style=discord.ButtonStyle.danger
    )
    async def yes(self, interaction, button):
        self.confirmed = True

        await interaction.response.edit_message(
            content="🗑️ Deleting channel...",
            view=None
        )

        self.stop()

    @discord.ui.button(
        label="NO",
        style=discord.ButtonStyle.secondary
    )
    async def no(self, interaction, button):
        await interaction.response.edit_message(
            content="❌ Cancelled.",
            view=None
        )

        self.stop()


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
    if channel == interaction.channel:
        pass

    view = ChannelWipeView(interaction.user.id)

    await interaction.response.send_message(
        f"⚠️ Delete and recreate {channel.mention}?",
        view=view,
        ephemeral=True
    )

    await view.wait()

    if not view.confirmed:
        return

    try:
        new_channel = await channel.clone(
            reason="SECURITY channel wipe"
        )

        await channel.delete(
            reason="SECURITY channel wipe"
        )

        await interaction.followup.send(
            f"✅ Channel wiped: {new_channel.mention}",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need Manage Channels permission.",
            ephemeral=True
        )


# =========================
# WIPE CATEGORY
# =========================

@bot.tree.command(
    name="wipe-category",
    description="Delete a category"
)
@app_commands.describe(
    category="Category to delete"
)
@admin()
async def wipe_category(
    interaction,
    category: discord.CategoryChannel
):
    view = ChannelWipeView(interaction.user.id)

    await interaction.response.send_message(
        f"⚠️ Delete category **{category.name}**?\n\n"
        "This does not delete roles or members.",
        view=view,
        ephemeral=True
    )

    await view.wait()

    if not view.confirmed:
        return

    try:
        await category.delete(
            reason="SECURITY category wipe"
        )

        await interaction.followup.send(
            "✅ Category deleted.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need Manage Channels permission.",
            ephemeral=True
        )
# =========================
# BAN
# =========================

@bot.tree.command(name="ban", description="Ban a member")
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
    ok, error = can_target(interaction, member)

    if not ok:
        await interaction.response.send_message(
            f"❌ {error}",
            ephemeral=True
        )
        return

    try:
        await member.ban(
            reason=reason,
            delete_message_seconds=86400
        )

        await interaction.response.send_message(
            f"🔨 Banned **{member}**.\nReason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot ban that member.",
            ephemeral=True
        )


# =========================
# KICK
# =========================

@bot.tree.command(name="kick", description="Kick a member")
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
    ok, error = can_target(interaction, member)

    if not ok:
        await interaction.response.send_message(
            f"❌ {error}",
            ephemeral=True
        )
        return

    try:
        await member.kick(reason=reason)

        await interaction.response.send_message(
            f"👢 Kicked **{member}**.\nReason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot kick that member.",
            ephemeral=True
        )


# =========================
# TIMEOUT
# =========================

@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.describe(
    member="Member",
    minutes="Timeout length",
    reason="Reason"
)
@moderator()
async def timeout(
    interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason provided"
):
    ok, error = can_target(interaction, member)

    if not ok:
        await interaction.response.send_message(
            f"❌ {error}",
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
            f"⏳ Timed out **{member}** for **{minutes} minutes**."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot timeout that member.",
            ephemeral=True
        )


# =========================
# UNTIMEOUT
# =========================

@bot.tree.command(name="untimeout", description="Remove timeout")
@moderator()
async def untimeout(
    interaction,
    member: discord.Member
):
    try:
        await member.timeout(None)

        await interaction.response.send_message(
            f"✅ Removed timeout from **{member}**."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot remove that timeout.",
            ephemeral=True
        )


# =========================
# WARN
# =========================

@bot.tree.command(name="warn", description="Warn a member")
@app_commands.describe(
    member="Member",
    reason="Reason"
)
@moderator()
async def warn(
    interaction,
    member: discord.Member,
    reason: str
):
    ok, error = can_target(interaction, member)

    if not ok:
        await interaction.response.send_message(
            f"❌ {error}",
            ephemeral=True
        )
        return

    cur.execute("""
        INSERT INTO warnings
        (guild_id,user_id,moderator_id,reason,created_at)
        VALUES (?,?,?,?,?)
    """, (
        interaction.guild.id,
        member.id,
        interaction.user.id,
        reason,
        datetime.utcnow().isoformat()
    ))

    db.commit()

    await interaction.response.send_message(
        f"⚠️ **{member}** has been warned.\nReason: {reason}"
    )


# =========================
# WARNINGS
# =========================

@bot.tree.command(
    name="warnings",
    description="View warnings"
)
@moderator()
async def warnings(
    interaction,
    member: discord.Member
):
    cur.execute("""
        SELECT reason, moderator_id, created_at
        FROM warnings
        WHERE guild_id=? AND user_id=?
        ORDER BY id DESC
    """, (
        interaction.guild.id,
        member.id
    ))

    rows = cur.fetchall()

    if not rows:
        await interaction.response.send_message(
            f"✅ **{member}** has no warnings.",
            ephemeral=True
        )
        return

    text = ""

    for i, row in enumerate(rows[:10], 1):
        text += (
            f"**{i}.** {row['reason']}\n"
            f"<@{row['moderator_id']}> • {row['created_at'][:10]}\n\n"
        )

    embed = discord.Embed(
        title=f"Warnings — {member}",
        description=text,
        color=discord.Color.orange()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================
# CLEAR WARNINGS
# =========================

@bot.tree.command(
    name="clearwarnings",
    description="Clear all warnings"
)
@admin()
async def clearwarnings(
    interaction,
    member: discord.Member
):
    cur.execute("""
        DELETE FROM warnings
        WHERE guild_id=? AND user_id=?
    """, (
        interaction.guild.id,
        member.id
    ))

    db.commit()

    await interaction.response.send_message(
        f"✅ Cleared warnings for **{member}**."
    )


# =========================
# AUTOROLE
# =========================

@bot.tree.command(
    name="autorole",
    description="Set automatic member role"
)
@app_commands.describe(
    role="Role to automatically give. Leave empty to disable."
)
@admin()
async def autorole(
    interaction,
    role: discord.Role = None
):
    if role is None:
        set_setting(
            interaction.guild.id,
            "autorole",
            None
        )

        await interaction.response.send_message(
            "✅ Autorole disabled."
        )
        return

    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ My bot role must be above that role.",
            ephemeral=True
        )
        return

    set_setting(
        interaction.guild.id,
        "autorole",
        role.id
    )

    await interaction.response.send_message(
        f"✅ Autorole set to {role.mention}."
    )


# =========================
# ADD ROLE
# =========================

@bot.tree.command(
    name="addrole",
    description="Give a role"
)
@moderator()
async def addrole(
    interaction,
    member: discord.Member,
    role: discord.Role
):
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I cannot manage that role.",
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
            "❌ I cannot add that role.",
            ephemeral=True
        )


# =========================
# REMOVE ROLE
# =========================

@bot.tree.command(
    name="removerole",
    description="Remove a role"
)
@moderator()
async def removerole(
    interaction,
    member: discord.Member,
    role: discord.Role
):
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I cannot manage that role.",
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


# =========================
# ROLE INFO
# =========================

@bot.tree.command(
    name="roleinfo",
    description="View role information"
)
async def roleinfo(
    interaction,
    role: discord.Role
):
    embed = discord.Embed(
        title=f"Role Info — {role.name}",
        color=role.color
    )

    embed.add_field(
        name="ID",
        value=str(role.id)
    )

    embed.add_field(
        name="Members",
        value=str(len(role.members))
    )

    embed.add_field(
        name="Position",
        value=str(role.position)
    )

    embed.add_field(
        name="Mentionable",
        value=str(role.mentionable)
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
# CREATE ROLE
# =========================

@bot.tree.command(
    name="createrole",
    description="Create a role"
)
@admin()
async def createrole(
    interaction,
    name: str
):
    try:
        role = await interaction.guild.create_role(
            name=name,
            reason="SECURITY role creation"
        )

        await interaction.response.send_message(
            f"✅ Created {role.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I need Manage Roles permission.",
            ephemeral=True
        )


# =========================
# DELETE ROLE
# =========================

@bot.tree.command(
    name="deleterole",
    description="Delete a role"
)
@admin()
async def deleterole(
    interaction,
    role: discord.Role
):
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ I cannot delete that role.",
            ephemeral=True
        )
        return

    try:
        await role.delete(
            reason="SECURITY role deletion"
        )

        await interaction.response.send_message(
            "✅ Role deleted."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot delete that role.",
            ephemeral=True
    )
# =========================
# AUTOMOD
# =========================

automod_spam_cache = {}


@bot.tree.command(
    name="automod",
    description="Configure AutoMod"
)
@app_commands.describe(
    enabled="Enable or disable AutoMod"
)
@admin()
async def automod(
    interaction,
    enabled: bool
):
    set_setting(
        interaction.guild.id,
        "automod_enabled",
        int(enabled)
    )

    await interaction.response.send_message(
        f"🛡️ AutoMod {'enabled' if enabled else 'disabled'}."
    )


@bot.tree.command(
    name="automod-invites",
    description="Block Discord invites"
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
        f"🛡️ Invite protection {'enabled' if enabled else 'disabled'}."
    )


@bot.tree.command(
    name="automod-links",
    description="Block links"
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
        f"🛡️ Link protection {'enabled' if enabled else 'disabled'}."
    )


@bot.tree.command(
    name="automod-spam",
    description="Enable spam protection"
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
        f"🛡️ Spam protection {'enabled' if enabled else 'disabled'}."
    )


@bot.tree.command(
    name="automod-caps",
    description="Enable excessive caps protection"
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
        f"🛡️ Caps protection {'enabled' if enabled else 'disabled'}."
    )


# =========================
# LEVELING
# =========================

level_cooldowns = {}


def xp_needed(level):
    return 100 + (level * 50)


async def add_xp(message):
    guild_id = message.guild.id
    user_id = message.author.id

    row = settings(guild_id)

    if not row["xp_enabled"]:
        return

    key = (guild_id, user_id)

    now = datetime.utcnow().timestamp()

    last = level_cooldowns.get(key, 0)

    if now - last < row["xp_cooldown"]:
        return

    level_cooldowns[key] = now

    amount = random.randint(
        max(1, row["xp_per_message"] // 2),
        row["xp_per_message"]
    )

    cur.execute("""
        INSERT OR IGNORE INTO levels
        (guild_id,user_id,xp,level)
        VALUES (?,?,0,0)
    """, (
        guild_id,
        user_id
    ))

    cur.execute("""
        UPDATE levels
        SET xp=xp+?
        WHERE guild_id=? AND user_id=?
    """, (
        amount,
        guild_id,
        user_id
    ))

    cur.execute("""
        SELECT xp,level
        FROM levels
        WHERE guild_id=? AND user_id=?
    """, (
        guild_id,
        user_id
    ))

    data = cur.fetchone()

    if data:
        current_xp = data["xp"]
        current_level = data["level"]

        needed = xp_needed(current_level)

        if current_xp >= needed:
            new_level = current_level + 1

            cur.execute("""
                UPDATE levels
                SET level=?, xp=xp-?
                WHERE guild_id=? AND user_id=?
            """, (
                new_level,
                needed,
                guild_id,
                user_id
            ))

            db.commit()

            try:
                await message.channel.send(
                    f"🎉 {message.author.mention} reached "
                    f"**Level {new_level}**!"
                )
            except:
                pass

    db.commit()


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
        f"⭐ Leveling {'enabled' if enabled else 'disabled'}."
    )


@bot.tree.command(
    name="level",
    description="View a member's level"
)
async def level(
    interaction,
    member: discord.Member = None
):
    member = member or interaction.user

    cur.execute("""
        SELECT xp,level
        FROM levels
        WHERE guild_id=? AND user_id=?
    """, (
        interaction.guild.id,
        member.id
    ))

    row = cur.fetchone()

    if not row:
        xp = 0
        lvl = 0
    else:
        xp = row["xp"]
        lvl = row["level"]

    embed = discord.Embed(
        title=f"⭐ {member.display_name}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Level",
        value=str(lvl)
    )

    embed.add_field(
        name="XP",
        value=str(xp)
    )

    embed.add_field(
        name="Next Level",
        value=str(xp_needed(lvl))
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="rank",
    description="View your rank"
)
async def rank(
    interaction,
    member: discord.Member = None
):
    member = member or interaction.user

    cur.execute("""
        SELECT level,xp
        FROM levels
        WHERE guild_id=? AND user_id=?
    """, (
        interaction.guild.id,
        member.id
    ))

    row = cur.fetchone()

    if not row:
        await interaction.response.send_message(
            "⭐ You have not earned XP yet."
        )
        return

    cur.execute("""
        SELECT user_id
        FROM levels
        WHERE guild_id=?
        ORDER BY level DESC, xp DESC
    """, (
        interaction.guild.id,
    ))

    users = [x["user_id"] for x in cur.fetchall()]

    try:
        rank_number = users.index(member.id) + 1
    except ValueError:
        rank_number = "?"

    await interaction.response.send_message(
        f"🏆 **{member.display_name}** is rank **#{rank_number}**."
    )
# =========================
# PART 6 — CHATBOT + SAY + HELP + ERRORS
# =========================

import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# -------------------------
# FREE CHATBOT RESPONSES
# -------------------------

def free_chat_response(message: str, member: discord.Member) -> str:
    text = message.lower().strip()

    # Greetings
    if any(x in text for x in ["hello", "hi", "hey", "yo", "sup"]):
        return f"Hey {member.mention}! 👋 How can I help?"

    # Bot questions
    if "your name" in text or "who are you" in text:
        return "I'm **𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘**, your server assistant 🛡️"

    # Help
    if "help" in text:
        return "Sure! 😎 Use `/help` to see my available commands."

    # Server questions
    if "server" in text and any(x in text for x in ["info", "information"]):
        return "You can use `/serverinfo` to see information about this server."

    # Verification
    if "verify" in text or "verification" in text:
        return "Use the verification panel in the server to verify yourself. ✅"

    # Tickets
    if "ticket" in text:
        return "Need help from staff? 🎫 Use the ticket panel to open a ticket."

    # Rules
    if "rule" in text or "rules" in text:
        return "Please read the server rules before chatting. 📜"

    # Thanks
    if any(x in text for x in ["thanks", "thank you", "thx", "ty"]):
        return "You're welcome! 😎"

    # Goodbye
    if any(x in text for x in ["bye", "goodbye", "cya"]):
        return "See you later! 👋"

    # How are you
    if "how are you" in text:
        return "I'm doing great! 🛡️ Ready to protect the server."

    # Questions
    if text.endswith("?"):
        return "Hmm 🤔 I'm not sure about that yet, but I'm here to help!"

    # Default
    responses = [
        "Got it! 👍",
        "Interesting 👀",
        "I'm listening.",
        "Alright 😎",
        "Got you! 🛡️",
        "Tell me more!",
        "Okay! 👍",
    ]

    import random
    return random.choice(responses)


# -------------------------
# CHATBOT COMMAND
# -------------------------

chatbot_group = app_commands.Group(
    name="chatbot",
    description="Configure the automatic chatbot"
)

@chatbot_group.command(
    name="setup",
    description="Set the chatbot channel"
)
@app_commands.describe(
    channel="Channel where SECURITY will automatically chat"
)
@admin()
async def chatbot_setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    set_setting(
        interaction.guild.id,
        "chatbot_channel",
        str(channel.id)
    )

    set_setting(
        interaction.guild.id,
        "chatbot_enabled",
        "1"
    )

    await interaction.response.send_message(
        f"✅ Chatbot enabled in {channel.mention}!\n\n"
        f"SECURITY will automatically reply to messages there.",
        ephemeral=True
    )


@chatbot_group.command(
    name="enable",
    description="Enable the automatic chatbot"
)
@admin()
async def chatbot_enable(interaction: discord.Interaction):

    set_setting(
        interaction.guild.id,
        "chatbot_enabled",
        "1"
    )

    await interaction.response.send_message(
        "✅ Automatic chatbot enabled!",
        ephemeral=True
    )


@chatbot_group.command(
    name="disable",
    description="Disable the automatic chatbot"
)
@admin()
async def chatbot_disable(interaction: discord.Interaction):

    set_setting(
        interaction.guild.id,
        "chatbot_enabled",
        "0"
    )

    await interaction.response.send_message(
        "🛑 Automatic chatbot disabled.",
        ephemeral=True
    )


bot.tree.add_command(chatbot_group)


# -------------------------
# AUTOMATIC CHATBOT
# -------------------------

chatbot_cooldowns = {}


@bot.event
async def on_message(message: discord.Message):

    # Ignore bots
    if message.author.bot:
        return

    # Ignore DMs
    if message.guild is None:
        return

    guild_settings = settings(message.guild.id)

    # -------------------------
    # AUTOMATIC CHATBOT
    # -------------------------

    chatbot_enabled = guild_settings["chatbot_enabled"] == "1"

    chatbot_channel = guild_settings["chatbot_channel"]

    if (
        chatbot_enabled
        and chatbot_channel
        and str(message.channel.id) == str(chatbot_channel)
    ):

        user_id = message.author.id
        now = asyncio.get_event_loop().time()

        # 3-second cooldown per user
        last_message = chatbot_cooldowns.get(user_id, 0)

        if now - last_message >= 3:

            chatbot_cooldowns[user_id] = now

            await asyncio.sleep(1)

            try:
                response = free_chat_response(
                    message.content,
                    message.author
                )

                await message.reply(
                    response,
                    mention_author=False
                )

            except discord.HTTPException:
                pass

    # -------------------------
    # AUTOMOD
    # -------------------------

    try:
        await run_automod(message)
    except Exception:
        pass

    # -------------------------
    # LEVELING
    # -------------------------

    try:
        await add_xp(message)
    except Exception:
        pass

    # -------------------------
    # PREFIX COMMANDS
    # -------------------------

    await bot.process_commands(message)


# -------------------------
# SAY COMMAND
# -------------------------

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
    interaction: discord.Interaction,
    message: str,
    channel: discord.TextChannel = None
):

    target = channel or interaction.channel

    try:
        await target.send(message)

        await interaction.response.send_message(
            f"✅ Message sent in {target.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to send messages there.",
            ephemeral=True
        )


# -------------------------
# SERVER INFO
# -------------------------

@bot.tree.command(
    name="serverinfo",
    description="Show server information"
)
async def serverinfo(interaction: discord.Interaction):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"🛡️ {guild.name}",
        description="Server information",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Members",
        value=str(guild.member_count),
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
        embed.set_thumbnail(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)


# -------------------------
# SETTINGS
# -------------------------

@bot.tree.command(
    name="settings",
    description="Show SECURITY settings"
)
@admin()
async def settings_command(interaction: discord.Interaction):

    s = settings(interaction.guild.id)

    embed = discord.Embed(
        title="⚙️ SECURITY Settings",
        color=discord.Color.dark_grey()
    )

    embed.add_field(
        name="👋 Welcome",
        value="Enabled" if s["welcome_enabled"] else "Disabled",
        inline=True
    )

    embed.add_field(
        name="👋 Goodbye",
        value="Enabled" if s["bye_enabled"] else "Disabled",
        inline=True
    )

    embed.add_field(
        name="🛡️ AutoMod",
        value="Enabled" if s["automod_enabled"] else "Disabled",
        inline=True
    )

    embed.add_field(
        name="🤖 Chatbot",
        value="Enabled" if s["chatbot_enabled"] else "Disabled",
        inline=True
    )

    embed.add_field(
        name="📈 Leveling",
        value="Enabled" if s["xp_enabled"] else "Disabled",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# -------------------------
# HELP
# -------------------------

@bot.tree.command(
    name="help",
    description="Show SECURITY commands"
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🛡️ 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 Help",
        description="Use the commands below.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome",
        value="`/welcome setup`\n`/welcome enable`\n`/welcome disable`\n`/welcome test`",
        inline=False
    )

    embed.add_field(
        name="👋 Goodbye",
        value="`/bye setup`\n`/bye enable`\n`/bye disable`\n`/bye test`",
        inline=False
    )

    embed.add_field(
        name="🛡️ Verification",
        value="`/verify`",
        inline=True
    )

    embed.add_field(
        name="🎫 Tickets",
        value="`/ticket`\n`/ticket-panel`",
        inline=True
    )

    embed.add_field(
        name="🤖 Chatbot",
        value="`/chatbot setup`\n`/chatbot enable`\n`/chatbot disable`",
        inline=True
    )

    embed.add_field(
        name="🧹 Cleaning",
        value="`/clean`\n`/purge`",
        inline=True
    )

    embed.add_field(
        name="☢️ Wipe",
        value="`/wipe`\n`/wipe-channel`\n`/wipe-category`",
        inline=True
    )

    embed.add_field(
        name="🔨 Moderation",
        value="`/ban`\n`/kick`\n`/timeout`\n`/warn`\n`/warnings`",
        inline=True
    )

    embed.add_field(
        name="🎭 Roles",
        value="`/autorole`\n`/addrole`\n`/removerole`\n`/roleinfo`",
        inline=True
    )

    embed.add_field(
        name="🤖 AutoMod",
        value="`/automod`\n`/automod-links`\n`/automod-spam`\n`/automod-caps`\n`/automod-invites`",
        inline=True
    )

    embed.add_field(
        name="📈 Leveling",
        value="`/leveling`\n`/level`\n`/rank`",
        inline=True
    )

    embed.add_field(
        name="📊 Server",
        value="`/serverinfo`\n`/settings`",
        inline=True
    )

    embed.add_field(
        name="📢 Other",
        value="`/say`",
        inline=True
    )

    await interaction.response.send_message(embed=embed)


# -------------------------
# ERROR HANDLING
# -------------------------

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    if isinstance(error, app_commands.CheckFailure):

        message = "❌ You don't have permission to use this command."

    elif isinstance(error, app_commands.CommandOnCooldown):

        message = "⏳ Please wait before using this command again."

    elif isinstance(error, app_commands.MissingPermissions):

        message = "❌ You don't have the required Discord permissions."

    elif isinstance(error, app_commands.BotMissingPermissions):

        message = "❌ I don't have the required Discord permissions."

    else:

        print(
            f"Slash command error: {repr(error)}"
        )

        message = (
            "❌ Something went wrong while running "
            "that command."
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

    except Exception:

        pass


# -------------------------
# BOT ERROR LOGGING
# -------------------------

@bot.event
async def on_error(event, *args, **kwargs):

    import traceback

    print(
        f"❌ Error in event: {event}"
    )

    traceback.print_exc()


# -------------------------
# START BOT
# -------------------------

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing from Railway Variables."
    )

bot.run(TOKEN)    
