# ============================================================
# START OF PART 1 — 👋 WELCOME
# ============================================================

import os
import io
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
DB_FILE = "security.db"

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,

            welcome_enabled INTEGER DEFAULT 0,
            welcome_channel_id INTEGER,
            welcome_message TEXT DEFAULT
                'Welcome {user} to {server}! You are member #{membercount}.',
            welcome_style TEXT DEFAULT 'default',
            welcome_role_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS stored_images (
            guild_id INTEGER,
            image_type TEXT,
            image_data BLOB,
            filename TEXT,
            PRIMARY KEY (guild_id, image_type)
        )
    """)

    conn.commit()
    conn.close()


def ensure_guild(guild_id: int):
    conn = get_db()

    conn.execute("""
        INSERT OR IGNORE INTO guild_settings (guild_id)
        VALUES (?)
    """, (guild_id,))

    conn.commit()
    conn.close()


def get_setting(guild_id: int, name: str):
    ensure_guild(guild_id)

    conn = get_db()

    row = conn.execute(
        f"SELECT {name} FROM guild_settings WHERE guild_id = ?",
        (guild_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return row[name]


def set_setting(guild_id: int, name: str, value):
    ensure_guild(guild_id)

    conn = get_db()

    conn.execute(
        f"UPDATE guild_settings SET {name} = ? WHERE guild_id = ?",
        (value, guild_id)
    )

    conn.commit()
    conn.close()


def replace_variables(text: str, member: discord.Member):
    guild = member.guild

    return (
        text
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", guild.name)
        .replace("{membercount}", str(guild.member_count))
    )


# ---------------- WELCOME SENDER ----------------

async def send_welcome(member: discord.Member):

    guild = member.guild

    if not get_setting(guild.id, "welcome_enabled"):
        return

    channel_id = get_setting(guild.id, "welcome_channel_id")

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if channel is None:
        return

    message = get_setting(
        guild.id,
        "welcome_message"
    )

    message = replace_variables(message, member)

    style = get_setting(
        guild.id,
        "welcome_style"
    )

    # Load persistent image from SQLite
    conn = get_db()

    image = conn.execute("""
        SELECT image_data, filename
        FROM stored_images
        WHERE guild_id = ?
        AND image_type = 'welcome'
    """, (guild.id,)).fetchone()

    conn.close()

    file = None

    if image:
        file = discord.File(
            io.BytesIO(image["image_data"]),
            filename=image["filename"] or "welcome.png"
        )

    if style == "embed":

        embed = discord.Embed(
            title="👋 Welcome!",
            description=message
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        if file:
            await channel.send(
                embed=embed,
                file=file
            )
        else:
            await channel.send(
                embed=embed
            )

    else:

        if file:
            await channel.send(
                content=message,
                file=file
            )
        else:
            await channel.send(
                content=message
            )

    # Automatic role
    role_id = get_setting(
        guild.id,
        "welcome_role_id"
    )

    if role_id:

        role = guild.get_role(role_id)

        if role and guild.me:

            if guild.me.top_role > role:

                try:
                    await member.add_roles(
                        role,
                        reason="SECURITY Welcome Auto Role"
                    )
                except discord.HTTPException:
                    pass


# ---------------- /welcome ----------------

@bot.tree.command(
    name="welcome",
    description="View Welcome system settings"
)
async def welcome(interaction: discord.Interaction):

    enabled = get_setting(
        interaction.guild.id,
        "welcome_enabled"
    )

    channel_id = get_setting(
        interaction.guild.id,
        "welcome_channel_id"
    )

    role_id = get_setting(
        interaction.guild.id,
        "welcome_role_id"
    )

    channel_text = (
        f"<#{channel_id}>"
        if channel_id
        else "Not set"
    )

    role_text = (
        f"<@&{role_id}>"
        if role_id
        else "Not set"
    )

    embed = discord.Embed(
        title="👋 Welcome Settings",
        description=(
            f"**Status:** {'🟢 ON' if enabled else '🔴 OFF'}\n"
            f"**Channel:** {channel_text}\n"
            f"**Auto Role:** {role_text}"
        )
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ---------------- /welcome-on ----------------

@bot.tree.command(
    name="welcome-on",
    description="Enable the Welcome system"
)
@app_commands.checks.has_permissions(administrator=True)
async def welcome_on(interaction: discord.Interaction):

    set_setting(
        interaction.guild.id,
        "welcome_enabled",
        1
    )

    await interaction.response.send_message(
        "✅ **Welcome system enabled.**",
        ephemeral=True
    )


# ---------------- /welcome-off ----------------

@bot.tree.command(
    name="welcome-off",
    description="Disable the Welcome system"
)
@app_commands.checks.has_permissions(administrator=True)
async def welcome_off(interaction: discord.Interaction):

    set_setting(
        interaction.guild.id,
        "welcome_enabled",
        0
    )

    await interaction.response.send_message(
        "✅ **Welcome system disabled.**",
        ephemeral=True
    )


# ---------------- /welcome-message ----------------

@bot.tree.command(
    name="welcome-message",
    description="Set the Welcome message"
)
@app_commands.describe(
    message="Welcome message"
)
@app_commands.checks.has_permissions(administrator=True)
async def welcome_message(
    interaction: discord.Interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "welcome_message",
        message
    )

    await interaction.response.send_message(
        "✅ **Welcome message saved.**\n\n"
        "Available variables:\n"
        "`{user}` `{username}` `{server}` `{membercount}`",
        ephemeral=True
    )


# ---------------- /welcome-image ----------------

@bot.tree.command(
    name="welcome-image",
    description="Set a permanent Welcome image"
)
@app_commands.describe(
    image="Upload the Welcome image"
)
@app_commands.checks.has_permissions(administrator=True)
async def welcome_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):

    if not image.content_type:
        await interaction.response.send_message(
            "❌ Please upload an image.",
            ephemeral=True
        )
        return

    if not image.content_type.startswith("image/"):
        await interaction.response.send_message(
            "❌ That file is not an image.",
            ephemeral=True
        )
        return

    image_data = await image.read()

    if len(image_data) > 10 * 1024 * 1024:
        await interaction.response.send_message(
            "❌ The image must be 10 MB or smaller.",
            ephemeral=True
        )
        return

    conn = get_db()

    conn.execute("""
        INSERT OR REPLACE INTO stored_images
        (guild_id, image_type, image_data, filename)
        VALUES (?, ?, ?, ?)
    """, (
        interaction.guild.id,
        "welcome",
        image_data,
        image.filename
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        "✅ **Welcome image saved permanently.**\n"
        "The bot stores the image itself instead of depending on "
        "the temporary Discord attachment URL.",
        ephemeral=True
    )


# ---------------- /welcome-style ----------------

@bot.tree.command(
    name="welcome-style",
    description="Change Welcome style"
)
@app_commands.describe(
    style="default or embed"
)
@app_commands.choices(
    style=[
        app_commands.Choice(
            name="Default",
            value="default"
        ),
        app_commands.Choice(
            name="Embed",
            value="embed"
        )
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def welcome_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):

    set_setting(
        interaction.guild.id,
        "welcome_style",
        style.value
    )

    await interaction.response.send_message(
        f"✅ Welcome style changed to **{style.name}**.",
        ephemeral=True
    )


# ---------------- /welcome-role ----------------

@bot.tree.command(
    name="welcome-role",
    description="Set the automatic Welcome role"
)
@app_commands.describe(
    role="Role new members should receive"
)
@app_commands.checks.has_permissions(administrator=True)
async def welcome_role(
    interaction: discord.Interaction,
    role: discord.Role
):

    me = interaction.guild.me

    if me and role >= me.top_role:
        await interaction.response.send_message(
            "❌ I cannot give that role.\n"
            "Move my bot role above the selected role.",
            ephemeral=True
        )
        return

    set_setting(
        interaction.guild.id,
        "welcome_role_id",
        role.id
    )

    await interaction.response.send_message(
        f"✅ Automatic Welcome role set to {role.mention}.",
        ephemeral=True
    )


# ---------------- /welcome-role-off ----------------

@bot.tree.command(
    name="welcome-role-off",
    description="Disable the Welcome automatic role"
)
@app_commands.checks.has_permissions(administrator=True)
async def welcome_role_off(
    interaction: discord.Interaction
):

    set_setting(
        interaction.guild.id,
        "welcome_role_id",
        None
    )

    await interaction.response.send_message(
        "✅ Welcome automatic role disabled.",
        ephemeral=True
    )


# ---------------- /testwelcome ----------------

@bot.tree.command(
    name="testwelcome",
    description="Test the Welcome system"
)
@app_commands.checks.has_permissions(administrator=True)
async def testwelcome(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        "✅ Sending a Welcome test...",
        ephemeral=True
    )

    await send_welcome(
        interaction.user
    )


# ---------------- MEMBER JOIN EVENT ----------------

@bot.event
async def on_member_join(
    member: discord.Member
):

    await send_welcome(member)


# ============================================================
# END OF PART 1 — 👋 WELCOME
# ============================================================
# ============================================================
# START OF PART 2 — 👋 BYE
# ============================================================

async def send_bye(member: discord.Member):

    guild = member.guild

    if not get_setting(
        guild.id,
        "bye_enabled"
    ):
        return

    channel_id = get_setting(
        guild.id,
        "bye_channel_id"
    )

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if channel is None:
        return

    message = get_setting(
        guild.id,
        "bye_message"
    )

    message = (
        message
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", guild.name)
        .replace(
            "{membercount}",
            str(guild.member_count)
        )
    )

    style = get_setting(
        guild.id,
        "bye_style"
    )

    conn = get_db()

    image = conn.execute("""
        SELECT image_data, filename
        FROM stored_images
        WHERE guild_id = ?
        AND image_type = 'bye'
    """, (guild.id,)).fetchone()

    conn.close()

    file = None

    if image:

        file = discord.File(
            io.BytesIO(image["image_data"]),
            filename=image["filename"] or "bye.png"
        )

    if style == "embed":

        embed = discord.Embed(
            title="👋 Goodbye!",
            description=message
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        if file:
            await channel.send(
                embed=embed,
                file=file
            )
        else:
            await channel.send(
                embed=embed
            )

    else:

        if file:
            await channel.send(
                content=message,
                file=file
            )
        else:
            await channel.send(
                content=message
            )


@bot.tree.command(
    name="bye",
    description="View Bye system settings"
)
async def bye(interaction: discord.Interaction):

    enabled = get_setting(
        interaction.guild.id,
        "bye_enabled"
    )

    channel_id = get_setting(
        interaction.guild.id,
        "bye_channel_id"
    )

    embed = discord.Embed(
        title="👋 Bye Settings",
        description=(
            f"**Status:** "
            f"{'🟢 ON' if enabled else '🔴 OFF'}\n"
            f"**Channel:** "
            f"{f'<#{channel_id}>' if channel_id else 'Not set'}"
        )
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="bye-on",
    description="Enable the Bye system"
)
@app_commands.checks.has_permissions(administrator=True)
async def bye_on(interaction: discord.Interaction):

    set_setting(
        interaction.guild.id,
        "bye_enabled",
        1
    )

    await interaction.response.send_message(
        "✅ **Bye system enabled.**",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-off",
    description="Disable the Bye system"
)
@app_commands.checks.has_permissions(administrator=True)
async def bye_off(interaction: discord.Interaction):

    set_setting(
        interaction.guild.id,
        "bye_enabled",
        0
    )

    await interaction.response.send_message(
        "✅ **Bye system disabled.**",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-message",
    description="Set the Bye message"
)
@app_commands.describe(
    message="Bye message"
)
@app_commands.checks.has_permissions(administrator=True)
async def bye_message(
    interaction: discord.Interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "bye_message",
        message
    )

    await interaction.response.send_message(
        "✅ **Bye message saved.**\n"
        "`{user}` `{username}` `{server}` `{membercount}`",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-image",
    description="Set a permanent Bye image"
)
@app_commands.describe(
    image="Upload the Bye image"
)
@app_commands.checks.has_permissions(administrator=True)
async def bye_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):

    if not image.content_type:
        return await interaction.response.send_message(
            "❌ Please upload an image.",
            ephemeral=True
        )

    if not image.content_type.startswith("image/"):
        return await interaction.response.send_message(
            "❌ Please upload an image file.",
            ephemeral=True
        )

    image_data = await image.read()

    if len(image_data) > 10 * 1024 * 1024:
        return await interaction.response.send_message(
            "❌ The image must be 10 MB or smaller.",
            ephemeral=True
        )

    conn = get_db()

    conn.execute("""
        INSERT OR REPLACE INTO stored_images
        (guild_id, image_type, image_data, filename)
        VALUES (?, ?, ?, ?)
    """, (
        interaction.guild.id,
        "bye",
        image_data,
        image.filename
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        "✅ **Bye image saved permanently.**",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-style",
    description="Change Bye style"
)
@app_commands.choices(
    style=[
        app_commands.Choice(
            name="Default",
            value="default"
        ),
        app_commands.Choice(
            name="Embed",
            value="embed"
        )
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def bye_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):

    set_setting(
        interaction.guild.id,
        "bye_style",
        style.value
    )

    await interaction.response.send_message(
        f"✅ Bye style changed to **{style.name}**.",
        ephemeral=True
    )


@bot.tree.command(
    name="testbye",
    description="Test the Bye system"
)
@app_commands.checks.has_permissions(administrator=True)
async def testbye(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        "✅ Sending a Bye test...",
        ephemeral=True
    )

    await send_bye(
        interaction.user
    )


@bot.event
async def on_member_remove(
    member: discord.Member
):

    await send_bye(member)


# ============================================================
# END OF PART 2 — 👋 BYE
# ============================================================
# ============================================================
# START OF PART 3 — 🛡️ VERIFICATION
# ============================================================

# Add these columns to the database automatically if they
# don't already exist. This also fixes the Bye settings from Part 2.

def migrate_settings():
    conn = get_db()

    columns = {
        "bye_enabled": "INTEGER DEFAULT 0",
        "bye_channel_id": "INTEGER",
        "bye_message": "TEXT DEFAULT 'Goodbye {username}! We will miss you.'",
        "bye_style": "TEXT DEFAULT 'default'",
        "verify_enabled": "INTEGER DEFAULT 0",
        "verify_channel_id": "INTEGER",
        "verify_role_id": "INTEGER",
        "verify_message": "TEXT DEFAULT 'Verify yourself to access the server.'"
    }

    existing = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(guild_settings)"
        ).fetchall()
    }

    for name, definition in columns.items():
        if name not in existing:
            conn.execute(
                f"ALTER TABLE guild_settings ADD COLUMN {name} {definition}"
            )

    conn.commit()
    conn.close()


class VerifyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        emoji="✅",
        style=discord.ButtonStyle.secondary,
        custom_id="security_verify_button"
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild

        if guild is None:
            return await interaction.response.send_message(
                "❌ This button can only be used inside a server.",
                ephemeral=True
            )

        role_id = get_setting(
            guild.id,
            "verify_role_id"
        )

        if not role_id:
            return await interaction.response.send_message(
                "❌ Verification has not been configured.",
                ephemeral=True
            )

        role = guild.get_role(role_id)

        if role is None:
            return await interaction.response.send_message(
                "❌ The verification role no longer exists.",
                ephemeral=True
            )

        if role in interaction.user.roles:
            return await interaction.response.send_message(
                "✅ You are already verified.",
                ephemeral=True
            )

        if guild.me and role >= guild.me.top_role:
            return await interaction.response.send_message(
                "❌ I cannot give the verification role. "
                "Move my bot role above it.",
                ephemeral=True
            )

        try:
            await interaction.user.add_roles(
                role,
                reason="SECURITY verification"
            )

            await interaction.response.send_message(
                f"✅ You are now verified and received {role.mention}.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to give that role.",
                ephemeral=True
            )


@bot.tree.command(
    name="verifysetup",
    description="Set up the verification system"
)
@app_commands.describe(
    channel="Verification channel",
    role="Role users receive after verification"
)
@app_commands.checks.has_permissions(administrator=True)
async def verifysetup(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    role: discord.Role
):

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            "❌ Move my bot role above the verification role.",
            ephemeral=True
        )

    set_setting(
        interaction.guild.id,
        "verify_channel_id",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "verify_role_id",
        role.id
    )

    set_setting(
        interaction.guild.id,
        "verify_enabled",
        1
    )

    message = get_setting(
        interaction.guild.id,
        "verify_message"
    )

    embed = discord.Embed(
        title="🛡️ Verification",
        description=message
    )

    embed.set_footer(
        text="SECURITY • Verification"
    )

    await channel.send(
        embed=embed,
        view=VerifyView()
    )

    await interaction.response.send_message(
        f"✅ Verification panel created in {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verifymessage",
    description="Change the verification message"
)
@app_commands.describe(
    message="Verification message"
)
@app_commands.checks.has_permissions(administrator=True)
async def verifymessage(
    interaction: discord.Interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "verify_message",
        message
    )

    await interaction.response.send_message(
        "✅ Verification message saved.",
        ephemeral=True
    )


@bot.tree.command(
    name="verifyrole",
    description="Change the verification role"
)
@app_commands.checks.has_permissions(administrator=True)
async def verifyrole(
    interaction: discord.Interaction,
    role: discord.Role
):

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            "❌ I cannot manage that role.",
            ephemeral=True
        )

    set_setting(
        interaction.guild.id,
        "verify_role_id",
        role.id
    )

    await interaction.response.send_message(
        f"✅ Verification role set to {role.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verifychannel",
    description="Change the verification channel"
)
@app_commands.checks.has_permissions(administrator=True)
async def verifychannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "verify_channel_id",
        channel.id
    )

    await interaction.response.send_message(
        f"✅ Verification channel set to {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify-on",
    description="Enable verification"
)
@app_commands.checks.has_permissions(administrator=True)
async def verify_on(interaction: discord.Interaction):

    set_setting(
        interaction.guild.id,
        "verify_enabled",
        1
    )

    await interaction.response.send_message(
        "✅ Verification enabled.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify-off",
    description="Disable verification"
)
@app_commands.checks.has_permissions(administrator=True)
async def verify_off(interaction: discord.Interaction):

    set_setting(
        interaction.guild.id,
        "verify_enabled",
        0
    )

    await interaction.response.send_message(
        "✅ Verification disabled.",
        ephemeral=True
    )


@bot.tree.command(
    name="verifytest",
    description="Send a test verification panel"
)
@app_commands.checks.has_permissions(administrator=True)
async def verifytest(interaction: discord.Interaction):

    role_id = get_setting(
        interaction.guild.id,
        "verify_role_id"
    )

    if not role_id:
        return await interaction.response.send_message(
            "❌ Set up verification first.",
            ephemeral=True
        )

    embed = discord.Embed(
        title="🛡️ Verification",
        description=get_setting(
            interaction.guild.id,
            "verify_message"
        )
    )

    await interaction.response.send_message(
        embed=embed,
        view=VerifyView()
    )


# ============================================================
# END OF PART 3 — 🛡️ VERIFICATION
# ============================================================
# ============================================================
# START OF PART 4 — 🎫 TICKETS
# ============================================================

@bot.tree.command(
    name="ticketsetup",
    description="Set up the ticket system"
)
@app_commands.describe(
    category="Private ticket category",
    staff_role="Staff role that can see tickets"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticketsetup(
    interaction: discord.Interaction,
    category: discord.CategoryChannel,
    staff_role: discord.Role
):

    set_setting(
        interaction.guild.id,
        "ticket_category_id",
        category.id
    )

    set_setting(
        interaction.guild.id,
        "ticket_role_id",
        staff_role.id
    )

    await interaction.response.send_message(
        "✅ Ticket system configured.\n"
        f"Category: {category.mention}\n"
        f"Staff role: {staff_role.mention}",
        ephemeral=True
    )


@bot.tree.command(
    name="ticketcategory",
    description="Set the ticket category"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticketcategory(
    interaction: discord.Interaction,
    category: discord.CategoryChannel
):

    set_setting(
        interaction.guild.id,
        "ticket_category_id",
        category.id
    )

    await interaction.response.send_message(
        f"✅ Ticket category set to {category.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="ticketrole",
    description="Set the ticket staff role"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticketrole(
    interaction: discord.Interaction,
    role: discord.Role
):

    set_setting(
        interaction.guild.id,
        "ticket_role_id",
        role.id
    )

    await interaction.response.send_message(
        f"✅ Ticket staff role set to {role.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="ticketchannel",
    description="Set the channel for the ticket panel"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticketchannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "ticket_channel_id",
        channel.id
    )

    await interaction.response.send_message(
        f"✅ Ticket panel channel set to {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="ticket",
    description="Create a private support ticket"
)
async def ticket(
    interaction: discord.Interaction
):

    guild = interaction.guild
    member = interaction.user

    category_id = get_setting(
        guild.id,
        "ticket_category_id"
    )

    staff_role_id = get_setting(
        guild.id,
        "ticket_role_id"
    )

    if not category_id:
        return await interaction.response.send_message(
            "❌ Tickets are not configured yet.",
            ephemeral=True
        )

    category = guild.get_channel(category_id)
    staff_role = (
        guild.get_role(staff_role_id)
        if staff_role_id
        else None
    )

    if not isinstance(category, discord.CategoryChannel):
        return await interaction.response.send_message(
            "❌ Ticket category no longer exists.",
            ephemeral=True
        )

    # Prevent duplicate tickets
    existing = discord.utils.get(
        guild.text_channels,
        name=f"ticket-{member.id}"
    )

    if existing:
        return await interaction.response.send_message(
            f"🎫 You already have a ticket: {existing.mention}",
            ephemeral=True
        )

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),
        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
    }

    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True
        )

    channel = await guild.create_text_channel(
        name=f"ticket-{member.id}",
        category=category,
        overwrites=overwrites,
        reason="SECURITY ticket"
    )

    embed = discord.Embed(
        title="🎫 Support Ticket",
        description=(
            f"Welcome {member.mention}!\n\n"
            "Please explain your issue here.\n"
            "A staff member will help you shortly."
        )
    )

    await channel.send(
        content=member.mention,
        embed=embed
    )

    await interaction.response.send_message(
        f"🎫 Ticket created: {channel.mention}",
        ephemeral=True
    )


@bot.tree.command(
    name="close",
    description="Close the current ticket"
)
async def close(
    interaction: discord.Interaction
):

    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message(
            "❌ This is not a text channel.",
            ephemeral=True
        )

    if not channel.name.startswith("ticket-"):
        return await interaction.response.send_message(
            "❌ This command can only be used inside a ticket.",
            ephemeral=True
        )

    if not (
        interaction.user.guild_permissions.manage_channels
        or channel.name == f"ticket-{interaction.user.id}"
    ):
        return await interaction.response.send_message(
            "❌ You cannot close this ticket.",
            ephemeral=True
        )

    await interaction.response.send_message(
        "🔒 Closing ticket..."
    )

    await asyncio.sleep(2)

    await channel.delete(
        reason="SECURITY ticket closed"
    )


@bot.tree.command(
    name="add",
    description="Add a member to the current ticket"
)
@app_commands.describe(
    member="Member to add"
)
async def add(
    interaction: discord.Interaction,
    member: discord.Member
):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.response.send_message(
            "❌ This isn't a ticket.",
            ephemeral=True
        )

    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message(
            "❌ This isn't a ticket.",
            ephemeral=True
        )

    if not (
        interaction.user.guild_permissions.manage_channels
        or interaction.channel.name == f"ticket-{interaction.user.id}"
    ):
        return await interaction.response.send_message(
            "❌ You cannot add members to this ticket.",
            ephemeral=True
        )

    await interaction.channel.set_permissions(
        member,
        view_channel=True,
        send_messages=True,
        read_message_history=True
    )

    await interaction.response.send_message(
        f"✅ {member.mention} was added to the ticket."
    )


@bot.tree.command(
    name="remove",
    description="Remove a member from the current ticket"
)
@app_commands.describe(
    member="Member to remove"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def remove(
    interaction: discord.Interaction,
    member: discord.Member
):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.response.send_message(
            "❌ This isn't a ticket.",
            ephemeral=True
        )

    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message(
            "❌ This isn't a ticket.",
            ephemeral=True
        )

    await interaction.channel.set_permissions(
        member,
        overwrite=None
    )

    await interaction.response.send_message(
        f"✅ {member.mention} was removed from the ticket."
    )


# ============================================================
# END OF PART 4 — 🎫 TICKETS
# ============================================================
# ============================================================
# START OF PART 5 — 🧹 CLEANER
# ============================================================

async def clean_messages(
    channel: discord.TextChannel,
    amount: int,
    user: discord.Member | None = None,
    bots: bool = False,
    links: bool = False,
    attachments: bool = False
):

    deleted = []

    async for message in channel.history(
        limit=None if amount <= 0 else amount
    ):

        if user and message.author.id != user.id:
            continue

        if bots and not message.author.bot:
            continue

        if links and not URL_RE.search(message.content):
            continue

        if attachments and not message.attachments:
            continue

        deleted.append(message)

        if amount > 0 and len(deleted) >= amount:
            break

    for message in deleted:
        try:
            await message.delete()
        except discord.HTTPException:
            pass

    return len(deleted)


@bot.tree.command(
    name="clear",
    description="Delete messages from this channel"
)
@app_commands.describe(
    amount="Number of messages to delete"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 500]
):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.response.send_message(
            "❌ This is not a text channel.",
            ephemeral=True
        )

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await clean_messages(
        interaction.channel,
        amount
    )

    await interaction.followup.send(
        f"🧹 Deleted **{deleted}** messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clean",
    description="Quickly clean messages"
)
@app_commands.describe(
    amount="Number of messages"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clean(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 500]
):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.response.send_message(
            "❌ This is not a text channel.",
            ephemeral=True
        )

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await clean_messages(
        interaction.channel,
        amount
    )

    await interaction.followup.send(
        f"🧹 Cleaned **{deleted}** messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clean-message",
    description="Clean messages from a selected channel"
)
@app_commands.describe(
    channel="Channel to clean",
    amount="Messages to remove; 0 means all available messages"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clean_message(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    amount: app_commands.Range[int, 0, 5000]
):

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await clean_messages(
        channel,
        amount
    )

    await interaction.followup.send(
        f"🧹 Cleaned **{deleted}** messages from {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="clear-user",
    description="Delete messages from a specific member"
)
@app_commands.describe(
    user="Member whose messages should be removed",
    amount="Maximum messages to inspect"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_user(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: app_commands.Range[int, 1, 500]
):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.response.send_message(
            "❌ This is not a text channel.",
            ephemeral=True
        )

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await clean_messages(
        interaction.channel,
        amount,
        user=user
    )

    await interaction.followup.send(
        f"🧹 Deleted **{deleted}** messages from {user.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="clear-bots",
    description="Delete bot messages"
)
@app_commands.describe(
    amount="Maximum messages to inspect"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_bots(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 500]
):

    await interaction.response.defer(
        ephemeral=True
    )

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.followup.send(
            "❌ This is not a text channel.",
            ephemeral=True
        )

    deleted = await clean_messages(
        interaction.channel,
        amount,
        bots=True
    )

    await interaction.followup.send(
        f"🤖 Deleted **{deleted}** bot messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clear-links",
    description="Delete messages containing links"
)
@app_commands.describe(
    amount="Maximum messages to inspect"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_links(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 500]
):

    await interaction.response.defer(
        ephemeral=True
    )

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.followup.send(
            "❌ This is not a text channel.",
            ephemeral=True
        )

    deleted = await clean_messages(
        interaction.channel,
        amount,
        links=True
    )

    await interaction.followup.send(
        f"🔗 Deleted **{deleted}** link messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clear-attachments",
    description="Delete messages containing attachments"
)
@app_commands.describe(
    amount="Maximum messages to inspect"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_attachments(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 500]
):

    await interaction.response.defer(
        ephemeral=True
    )

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.followup.send(
            "❌ This is not a text channel.",
            ephemeral=True
        )

    deleted = await clean_messages(
        interaction.channel,
        amount,
        attachments=True
    )

    await interaction.followup.send(
        f"🖼️ Deleted **{deleted}** messages with attachments.",
        ephemeral=True
    )


# ============================================================
# END OF PART 5 — 🧹 CLEANER
# ============================================================
# ============================================================
# START OF PART 6 — ☢️ SERVER WIPE
# ============================================================

@bot.tree.command(
    name="wipe",
    description="FULL SERVER WIPE — deletes channels and roles"
)
@app_commands.describe(
    confirm="You MUST select True to confirm the full wipe"
)
@app_commands.checks.has_permissions(administrator=True)
async def wipe(
    interaction: discord.Interaction,
    confirm: bool
):

    if not confirm:
        return await interaction.response.send_message(
            "⚠️ **FULL SERVER WIPE NOT CONFIRMED**\n\n"
            "This command can delete the server's channels and "
            "manageable roles.\n\n"
            "Run `/wipe confirm:True` if you really want to continue.",
            ephemeral=True
        )

    guild = interaction.guild

    await interaction.response.send_message(
        "☢️ **SERVER WIPE STARTING...**\n"
        "Deleting manageable channels and roles.",
        ephemeral=False
    )

    # Delete channels first
    for channel in list(guild.channels):

        try:
            await channel.delete(
                reason="SECURITY full server wipe"
            )

            await asyncio.sleep(0.3)

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

    # Delete manageable roles
    for role in list(guild.roles):

        if role.is_default():
            continue

        if role.managed:
            continue

        if guild.me and role >= guild.me.top_role:
            continue

        try:
            await role.delete(
                reason="SECURITY full server wipe"
            )

            await asyncio.sleep(0.3)

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


# ============================================================
# END OF PART 6 — ☢️ SERVER WIPE
# ============================================================
# ============================================================
# START OF PART 7 — ⭐ LEVELS
# ============================================================

def xp_needed(level: int):
    return 100 + (level * 50)


def get_xp(guild_id: int, user_id: int):
    conn = get_db()

    row = conn.execute("""
        SELECT xp, level
        FROM xp
        WHERE guild_id=? AND user_id=?
    """, (guild_id, user_id)).fetchone()

    conn.close()

    if row:
        return row["xp"], row["level"]

    return 0, 0


def save_xp(guild_id, user_id, xp_amount, level):
    conn = get_db()

    conn.execute("""
        INSERT OR REPLACE INTO xp
        (guild_id,user_id,xp,level)
        VALUES(?,?,?,?)
    """, (
        guild_id,
        user_id,
        xp_amount,
        level
    ))

    conn.commit()
    conn.close()


async def create_level_card(
    member: discord.Member,
    level: int,
    xp_amount: int
):

    width = 1000
    height = 350

    image = Image.new(
        "RGB",
        (width, height),
        (20, 20, 20)
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
            bold = ImageFont.truetype(path, 58)
            normal = ImageFont.truetype(path, 32)
            break

    if bold is None:
        bold = ImageFont.load_default()
        normal = ImageFont.load_default()

    avatar_data = await member.display_avatar.read()

    avatar = Image.open(
        io.BytesIO(avatar_data)
    ).convert("RGB")

    avatar = avatar.resize(
        (210, 210)
    )

    mask = Image.new(
        "L",
        (210, 210),
        0
    )

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.ellipse(
        (0, 0, 210, 210),
        fill=255
    )

    image.paste(
        avatar,
        (70, 70),
        mask
    )

    draw.text(
        (330, 65),
        f"LEVEL {level}",
        font=bold,
        fill=(255, 255, 255)
    )

    draw.text(
        (335, 140),
        member.name,
        font=normal,
        fill=(220, 220, 220)
    )

    draw.text(
        (335, 195),
        f"XP: {xp_amount:,}",
        font=normal,
        fill=(180, 180, 180)
    )

    draw.text(
        (335, 245),
        "SECURITY • LEVEL UP",
        font=normal,
        fill=(255, 255, 255)
    )

    output = io.BytesIO()

    image.save(
        output,
        format="PNG"
    )

    output.seek(0)

    return discord.File(
        output,
        filename="level-up.png"
    )


@bot.tree.command(
    name="setuplevel",
    description="Set the level-up announcement channel"
)
@app_commands.describe(
    channel="Channel where level-ups are announced"
)
@app_commands.checks.has_permissions(administrator=True)
async def setuplevel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "level_channel_id",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "level_enabled",
        1
    )

    await interaction.response.send_message(
        f"⭐ Level system enabled in {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="level",
    description="Check your level"
)
@app_commands.describe(
    member="Member to check"
)
async def level(
    interaction: discord.Interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    xp_amount, level_number = get_xp(
        interaction.guild.id,
        member.id
    )

    needed = xp_needed(level_number)

    embed = discord.Embed(
        title=f"⭐ {member.name}'s Level",
        description=(
            f"**Level:** {level_number}\n"
            f"**XP:** {xp_amount:,} / {needed:,}"
        )
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="leaderboard",
    description="Show the server level leaderboard"
)
async def leaderboard(
    interaction: discord.Interaction
):

    conn = get_db()

    rows = conn.execute("""
        SELECT user_id, xp, level
        FROM xp
        WHERE guild_id=?
        ORDER BY level DESC, xp DESC
        LIMIT 10
    """, (
        interaction.guild.id,
    )).fetchall()

    conn.close()

    if not rows:
        return await interaction.response.send_message(
            "⭐ No level data yet."
        )

    lines = []

    for index, row in enumerate(rows, 1):

        member = interaction.guild.get_member(
            row["user_id"]
        )

        name = (
            member.display_name
            if member
            else f"User {row['user_id']}"
        )

        lines.append(
            f"**{index}.** {name} — "
            f"Level {row['level']} • "
            f"{row['xp']:,} XP"
        )

    embed = discord.Embed(
        title="🏆 Level Leaderboard",
        description="\n".join(lines)
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="levelrole",
    description="Give a role automatically at a level"
)
@app_commands.describe(
    level_number="Required level",
    role="Role to give"
)
@app_commands.checks.has_permissions(administrator=True)
async def levelrole(
    interaction: discord.Interaction,
    level_number: app_commands.Range[int, 1, 1000],
    role: discord.Role
):

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            "❌ I cannot manage that role.",
            ephemeral=True
        )

    conn = get_db()

    conn.execute("""
        INSERT OR REPLACE INTO level_roles
        (guild_id,level,role_id)
        VALUES(?,?,?)
    """, (
        interaction.guild.id,
        level_number,
        role.id
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ {role.mention} will be awarded at level "
        f"**{level_number}**.",
        ephemeral=True
    )


@bot.tree.command(
    name="levelrole-remove",
    description="Remove an automatic level role"
)
@app_commands.describe(
    level_number="Level to remove"
)
@app_commands.checks.has_permissions(administrator=True)
async def levelrole_remove(
    interaction: discord.Interaction,
    level_number: int
):

    conn = get_db()

    conn.execute("""
        DELETE FROM level_roles
        WHERE guild_id=? AND level=?
    """, (
        interaction.guild.id,
        level_number
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ Level {level_number} role removed.",
        ephemeral=True
    )


@bot.tree.command(
    name="levelmessage",
    description="Set the level-up message"
)
@app_commands.describe(
    message="Level-up message"
)
@app_commands.checks.has_permissions(administrator=True)
async def levelmessage(
    interaction: discord.Interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "level_message",
        message
    )

    await interaction.response.send_message(
        "✅ Level-up message saved.\n"
        "`{user}` `{username}` `{level}` `{xp}` `{server}`",
        ephemeral=True
    )


@bot.tree.command(
    name="level-on",
    description="Enable the level system"
)
@app_commands.checks.has_permissions(administrator=True)
async def level_on(
    interaction: discord.Interaction
):

    set_setting(
        interaction.guild.id,
        "level_enabled",
        1
    )

    await interaction.response.send_message(
        "✅ Level system enabled.",
        ephemeral=True
    )


@bot.tree.command(
    name="level-off",
    description="Disable the level system"
)
@app_commands.checks.has_permissions(administrator=True)
async def level_off(
    interaction: discord.Interaction
):

    set_setting(
        interaction.guild.id,
        "level_enabled",
        0
    )

    await interaction.response.send_message(
        "✅ Level system disabled.",
        ephemeral=True
    )


@bot.tree.command(
    name="levelimage",
    description="Show level-card image status"
)
async def levelimage(
    interaction: discord.Interaction
):

    enabled = get_setting(
        interaction.guild.id,
        "level_image_enabled"
    )

    await interaction.response.send_message(
        f"🖼️ Level cards: "
        f"{'🟢 ON' if enabled else '🔴 OFF'}",
        ephemeral=True
    )


@bot.tree.command(
    name="levelimage-on",
    description="Enable black-and-white level cards"
)
@app_commands.checks.has_permissions(administrator=True)
async def levelimage_on(
    interaction: discord.Interaction
):

    set_setting(
        interaction.guild.id,
        "level_image_enabled",
        1
    )

    await interaction.response.send_message(
        "✅ Black-and-white level cards enabled.",
        ephemeral=True
    )


@bot.tree.command(
    name="levelimage-off",
    description="Disable level cards"
)
@app_commands.checks.has_permissions(administrator=True)
async def levelimage_off(
    interaction: discord.Interaction
):

    set_setting(
        interaction.guild.id,
        "level_image_enabled",
        0
    )

    await interaction.response.send_message(
        "✅ Level cards disabled.",
        ephemeral=True
    )


@bot.tree.command(
    name="leveltest",
    description="Test your level-up card"
)
@app_commands.checks.has_permissions(administrator=True)
async def leveltest(
    interaction: discord.Interaction
):

    file = await create_level_card(
        interaction.user,
        1,
        100
    )

    await interaction.response.send_message(
        content="⭐ **LEVEL 1**",
        file=file
    )


# ============================================================
# END OF PART 7 — ⭐ LEVELS
# ============================================================
# ============================================================
# START OF PART 8 — ⭐ LEVEL XP EVENT
# ============================================================

# Prevents XP being awarded repeatedly from every message.
level_cooldowns = {}


async def process_level_xp(
    message: discord.Message
):

    if not message.guild:
        return

    if message.author.bot:
        return

    if not get_setting(
        message.guild.id,
        "level_enabled"
    ):
        return

    key = (
        message.guild.id,
        message.author.id
    )

    current = time.time()

    # 60 second XP cooldown
    if current - level_cooldowns.get(key, 0) < 60:
        return

    level_cooldowns[key] = current

    old_xp, old_level = get_xp(
        message.guild.id,
        message.author.id
    )

    gained = random.randint(10, 20)

    new_xp = old_xp + gained
    new_level = old_level

    while new_xp >= xp_needed(new_level):
        new_xp -= xp_needed(new_level)
        new_level += 1

    save_xp(
        message.guild.id,
        message.author.id,
        new_xp,
        new_level
    )

    if new_level <= old_level:
        return

    channel_id = get_setting(
        message.guild.id,
        "level_channel_id"
    )

    channel = (
        message.guild.get_channel(channel_id)
        if channel_id
        else message.channel
    )

    if channel is None:
        return

    text = get_setting(
        message.guild.id,
        "level_message"
    )

    text = (
        text
        .replace("{user}", message.author.mention)
        .replace("{username}", message.author.name)
        .replace("{level}", str(new_level))
        .replace("{xp}", str(new_xp))
        .replace("{server}", message.guild.name)
    )

    image_enabled = get_setting(
        message.guild.id,
        "level_image_enabled"
    )

    file = None

    if image_enabled:
        file = await create_level_card(
            message.author,
            new_level,
            new_xp
        )

    if file:
        await channel.send(
            content=text,
            file=file
        )
    else:
        await channel.send(
            content=text
        )

    # Automatic level role
    conn = get_db()

    role_row = conn.execute("""
        SELECT role_id
        FROM level_roles
        WHERE guild_id=? AND level=?
    """, (
        message.guild.id,
        new_level
    )).fetchone()

    conn.close()

    if role_row:

        role = message.guild.get_role(
            role_row["role_id"]
        )

        if (
            role
            and message.guild.me
            and role < message.guild.me.top_role
        ):

            try:
                await message.author.add_roles(
                    role,
                    reason=f"Reached level {new_level}"
                )
            except discord.HTTPException:
                pass


# ============================================================
# END OF PART 8 — ⭐ LEVEL XP EVENT
# ============================================================
# ============================================================
# START OF PART 9 — 📊 STATISTICS
# ============================================================

@bot.tree.command(
    name="memberstats",
    description="Show server member statistics"
)
async def memberstats(
    interaction: discord.Interaction
):

    guild = interaction.guild

    humans = sum(
        not member.bot
        for member in guild.members
    )

    bots = sum(
        member.bot
        for member in guild.members
    )

    online = sum(
        member.status != discord.Status.offline
        for member in guild.members
    )

    embed = discord.Embed(
        title="📊 Member Statistics",
        description=(
            f"👥 Total: **{guild.member_count}**\n"
            f"👤 Humans: **{humans}**\n"
            f"🤖 Bots: **{bots}**\n"
            f"🟢 Online: **{online}**"
        )
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="botstats",
    description="Show SECURITY bot statistics"
)
async def botstats(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🤖 SECURITY Statistics",
        description=(
            f"🏠 Servers: **{len(bot.guilds)}**\n"
            f"👥 Users cached: **{len(bot.users)}**\n"
            f"⚡ Latency: **{round(bot.latency * 1000)}ms**\n"
            f"⏱️ Uptime: **{human_uptime()}**"
        )
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="serverstats",
    description="Show complete server statistics"
)
async def serverstats(
    interaction: discord.Interaction
):

    guild = interaction.guild

    categories = len(guild.categories)
    text = len(guild.text_channels)
    voice = len(guild.voice_channels)
    roles = len(guild.roles)
    emojis = len(guild.emojis)
    stickers = len(guild.stickers)

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        description=(
            f"👥 Members: **{guild.member_count}**\n"
            f"📂 Categories: **{categories}**\n"
            f"💬 Text channels: **{text}**\n"
            f"🔊 Voice channels: **{voice}**\n"
            f"🎭 Roles: **{roles}**\n"
            f"😀 Emojis: **{emojis}**\n"
            f"🎨 Stickers: **{stickers}**\n"
            f"🚀 Boosts: **{guild.premium_subscription_count}**"
        )
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="channelstats",
    description="Show channel statistics"
)
async def channelstats(
    interaction: discord.Interaction
):

    guild = interaction.guild

    text = len(guild.text_channels)
    voice = len(guild.voice_channels)
    categories = len(guild.categories)
    forums = sum(
        isinstance(c, discord.ForumChannel)
        for c in guild.channels
    )

    await interaction.response.send_message(
        embed=discord.Embed(
            title="📊 Channel Statistics",
            description=(
                f"💬 Text: **{text}**\n"
                f"🔊 Voice: **{voice}**\n"
                f"📂 Categories: **{categories}**\n"
                f"📰 Forums: **{forums}**"
            )
        )
    )


@bot.tree.command(
    name="rolestats",
    description="Show role statistics"
)
async def rolestats(
    interaction: discord.Interaction
):

    guild = interaction.guild

    managed = sum(
        role.managed
        for role in guild.roles
    )

    normal = len(guild.roles) - managed

    await interaction.response.send_message(
        embed=discord.Embed(
            title="📊 Role Statistics",
            description=(
                f"🎭 Total roles: **{len(guild.roles)}**\n"
                f"🛠️ Normal roles: **{normal}**\n"
                f"🔗 Managed roles: **{managed}**"
            )
        )
    )


@bot.tree.command(
    name="booststats",
    description="Show server boost statistics"
)
async def booststats(
    interaction: discord.Interaction
):

    guild = interaction.guild

    boosters = len(guild.premium_subscribers)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="🚀 Boost Statistics",
            description=(
                f"Boosts: **{guild.premium_subscription_count or 0}**\n"
                f"Boost level: **{guild.premium_tier}**\n"
                f"Boosters: **{boosters}**"
            )
        )
    )


@bot.tree.command(
    name="activitystats",
    description="Show server activity statistics"
)
async def activitystats(
    interaction: discord.Interaction
):

    conn = get_db()

    row = conn.execute("""
        SELECT messages
        FROM activity
        WHERE guild_id=?
    """, (
        interaction.guild.id,
    )).fetchone()

    conn.close()

    messages = row["messages"] if row else 0

    await interaction.response.send_message(
        embed=discord.Embed(
            title="📈 Activity Statistics",
            description=(
                f"💬 Messages tracked: **{messages:,}**"
            )
        )
    )


@bot.tree.command(
    name="servercount",
    description="Show the number of servers SECURITY is in"
)
async def servercount(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        f"🌐 SECURITY is currently in **{len(bot.guilds)} servers**."
    )


# ============================================================
# END OF PART 9 — 📊 STATISTICS
# ============================================================
# ============================================================
# START OF PART 10 — 🔗 ANTI-LINK
# ============================================================

antilink_group = app_commands.Group(
    name="antilink",
    description="Anti-Link protection"
)


@antilink_group.command(
    name="setup",
    description="Configure Anti-Link protection"
)
@app_commands.describe(
    channel="Channel where links are forbidden"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "antilink_channel_id",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "antilink_enabled",
        1
    )

    await interaction.response.send_message(
        f"🔗 Anti-Link enabled in {channel.mention}.",
        ephemeral=True
    )


@antilink_group.command(
    name="on",
    description="Enable Anti-Link"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_on(
    interaction: discord.Interaction
):

    set_setting(
        interaction.guild.id,
        "antilink_enabled",
        1
    )

    await interaction.response.send_message(
        "🔗 Anti-Link is now **ON**.",
        ephemeral=True
    )


@antilink_group.command(
    name="off",
    description="Disable Anti-Link"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_off(
    interaction: discord.Interaction
):

    set_setting(
        interaction.guild.id,
        "antilink_enabled",
        0
    )

    await interaction.response.send_message(
        "🔗 Anti-Link is now **OFF**.",
        ephemeral=True
    )


@antilink_group.command(
    name="channel",
    description="Choose the Anti-Link channel"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "antilink_channel_id",
        channel.id
    )

    await interaction.response.send_message(
        f"✅ Anti-Link channel: {channel.mention}",
        ephemeral=True
    )


@antilink_group.command(
    name="message",
    description="Set the Anti-Link warning message"
)
@app_commands.describe(
    message="Warning message"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_message(
    interaction: discord.Interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "antilink_message",
        message
    )

    await interaction.response.send_message(
        "✅ Anti-Link warning saved.",
        ephemeral=True
    )


@antilink_group.command(
    name="mute-role",
    description="Set the Anti-Link mute role"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_mute_role(
    interaction: discord.Interaction,
    role: discord.Role
):

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            "❌ I cannot manage that role.",
            ephemeral=True
        )

    set_setting(
        interaction.guild.id,
        "antilink_mute_role_id",
        role.id
    )

    await interaction.response.send_message(
        f"🔇 Mute role set to {role.mention}.",
        ephemeral=True
    )


@antilink_group.command(
    name="exempt-role",
    description="Add a role that is exempt from Anti-Link"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_exempt_role(
    interaction: discord.Interaction,
    role: discord.Role
):

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS antilink_exempt_roles (
            guild_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY(guild_id,role_id)
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO antilink_exempt_roles
        VALUES(?,?)
    """, (
        interaction.guild.id,
        role.id
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"🛡️ {role.mention} is now exempt from Anti-Link.",
        ephemeral=True
    )


@antilink_group.command(
    name="remove-exempt-role",
    description="Remove an Anti-Link exempt role"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_remove_exempt(
    interaction: discord.Interaction,
    role: discord.Role
):

    conn = get_db()

    conn.execute("""
        DELETE FROM antilink_exempt_roles
        WHERE guild_id=? AND role_id=?
    """, (
        interaction.guild.id,
        role.id
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ {role.mention} is no longer exempt.",
        ephemeral=True
    )


@antilink_group.command(
    name="warnings",
    description="Show a member's Anti-Link warnings"
)
async def antilink_warnings(
    interaction: discord.Interaction,
    member: discord.Member
):

    conn = get_db()

    row = conn.execute("""
        SELECT count
        FROM warnings
        WHERE guild_id=? AND user_id=?
    """, (
        interaction.guild.id,
        member.id
    )).fetchone()

    conn.close()

    count = row["count"] if row else 0

    await interaction.response.send_message(
        f"🔗 {member.mention} has **{count}/4** Anti-Link warnings.",
        ephemeral=True
    )


@antilink_group.command(
    name="reset",
    description="Reset Anti-Link warnings"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_reset(
    interaction: discord.Interaction,
    member: discord.Member
):

    conn = get_db()

    conn.execute("""
        DELETE FROM warnings
        WHERE guild_id=? AND user_id=?
    """, (
        interaction.guild.id,
        member.id
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ Anti-Link warnings reset for {member.mention}.",
        ephemeral=True
    )


@antilink_group.command(
    name="log",
    description="Set the Anti-Link log channel"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_log(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "antilink_log_channel_id",
        channel.id
    )

    await interaction.response.send_message(
        f"📋 Anti-Link logs: {channel.mention}",
        ephemeral=True
    )


@antilink_group.command(
    name="ban-channel",
    description="Set the Anti-Link ban announcement channel"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_ban_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "antilink_ban_channel_id",
        channel.id
    )

    await interaction.response.send_message(
        f"🔨 Ban announcements: {channel.mention}",
        ephemeral=True
    )


@antilink_group.command(
    name="ban-message",
    description="Set the Anti-Link ban announcement"
)
@app_commands.checks.has_permissions(administrator=True)
async def antilink_ban_message(
    interaction: discord.Interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "antilink_ban_message",
        message
    )

    await interaction.response.send_message(
        "✅ Ban announcement saved.",
        ephemeral=True
    )


bot.tree.add_command(antilink_group)

# ============================================================
# END OF PART 10 — 🔗 ANTI-LINK
# ============================================================
# ============================================================
# START OF PART 11 — 🔗 ANTI-LINK ENFORCEMENT
# ============================================================

async def is_antilink_exempt(member: discord.Member):

    if member.guild.owner_id == member.id:
        return True

    if member.guild_permissions.administrator:
        return True

    conn = get_db()

    try:
        rows = conn.execute("""
            SELECT role_id
            FROM antilink_exempt_roles
            WHERE guild_id=?
        """, (member.guild.id,)).fetchall()
    except sqlite3.OperationalError:
        rows = []

    conn.close()

    exempt_ids = {
        row["role_id"]
        for row in rows
    }

    return any(
        role.id in exempt_ids
        for role in member.roles
    )


async def get_antilink_warning(
    guild_id: int,
    user_id: int
):

    conn = get_db()

    row = conn.execute("""
        SELECT count
        FROM warnings
        WHERE guild_id=? AND user_id=?
    """, (
        guild_id,
        user_id
    )).fetchone()

    conn.close()

    return row["count"] if row else 0


async def add_antilink_warning(
    guild_id: int,
    user_id: int
):

    current = await get_antilink_warning(
        guild_id,
        user_id
    )

    new_count = current + 1

    conn = get_db()

    conn.execute("""
        INSERT OR REPLACE INTO warnings
        (guild_id,user_id,count)
        VALUES(?,?,?)
    """, (
        guild_id,
        user_id,
        new_count
    ))

    conn.commit()
    conn.close()

    return new_count


async def antilink_log_action(
    guild: discord.Guild,
    text: str
):

    channel_id = get_setting(
        guild.id,
        "antilink_log_channel_id"
    )

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if channel:
        try:
            await channel.send(text)
        except discord.HTTPException:
            pass


async def punish_antilink(
    message: discord.Message
):

    guild = message.guild
    member = message.author

    if not guild or member.bot:
        return

    if not get_setting(
        guild.id,
        "antilink_enabled"
    ):
        return

    configured_channel = get_setting(
        guild.id,
        "antilink_channel_id"
    )

    if configured_channel:
        if message.channel.id != configured_channel:
            return

    if not URL_RE.search(message.content):
        return

    if await is_antilink_exempt(member):
        return

    try:
        await message.delete()
    except discord.HTTPException:
        pass

    warnings = await add_antilink_warning(
        guild.id,
        member.id
    )

    warning_message = get_setting(
        guild.id,
        "antilink_message"
    )

    warning_message = (
        warning_message
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{warnings}", str(warnings))
        .replace("{server}", guild.name)
        .replace("{channel}", message.channel.mention)
    )

    if warnings < 4:

        try:
            await message.channel.send(
                warning_message,
                delete_after=10
            )
        except discord.HTTPException:
            pass

    # 2nd violation = 24 hour mute
    if warnings == 2:

        role_id = get_setting(
            guild.id,
            "antilink_mute_role_id"
        )

        role = (
            guild.get_role(role_id)
            if role_id
            else None
        )

        if role and guild.me and role < guild.me.top_role:

            try:
                await member.add_roles(
                    role,
                    reason="SECURITY Anti-Link: warning 2"
                )
            except discord.HTTPException:
                pass

    # 3rd violation = 7 day mute
    elif warnings == 3:

        role_id = get_setting(
            guild.id,
            "antilink_mute_role_id"
        )

        role = (
            guild.get_role(role_id)
            if role_id
            else None
        )

        if role and guild.me and role < guild.me.top_role:

            try:
                await member.add_roles(
                    role,
                    reason="SECURITY Anti-Link: warning 3"
                )
            except discord.HTTPException:
                pass

    # 4th violation = BAN
    elif warnings >= 4:

        try:
            await guild.ban(
                member,
                reason="SECURITY Anti-Link: 4 violations"
            )

            ban_channel_id = get_setting(
                guild.id,
                "antilink_ban_channel_id"
            )

            ban_channel = (
                guild.get_channel(ban_channel_id)
                if ban_channel_id
                else None
            )

            ban_text = get_setting(
                guild.id,
                "antilink_ban_message"
            )

            ban_text = (
                ban_text
                .replace("{user}", member.mention)
                .replace("{username}", member.name)
                .replace("{warnings}", str(warnings))
                .replace("{server}", guild.name)
                .replace("{channel}", message.channel.mention)
            )

            if ban_channel:
                await ban_channel.send(
                    ban_text
                )

            await antilink_log_action(
                guild,
                f"🔨 Banned **{member}** for repeated links."
            )

        except discord.HTTPException:
            pass


# ============================================================
# END OF PART 11
# ============================================================
# ============================================================
# START OF PART 12 — 🛡️ MODERATION
# ============================================================

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction, member: discord.Member, reason: str = "No reason provided"):

    if member == interaction.user:
        return await interaction.response.send_message(
            "❌ You cannot kick yourself.",
            ephemeral=True
        )

    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(
            f"👢 **{member}** was kicked.\nReason: {reason}"
        )
    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ I could not kick that member.",
            ephemeral=True
        )


@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction, member: discord.Member, reason: str = "No reason provided"):

    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(
            f"🔨 **{member}** was banned.\nReason: {reason}"
        )
    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ I could not ban that member.",
            ephemeral=True
        )


@bot.tree.command(name="unban", description="Unban a user")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction, user_id: str):

    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)

        await interaction.response.send_message(
            f"✅ **{user}** was unbanned."
        )

    except (ValueError, discord.HTTPException):
        await interaction.response.send_message(
            "❌ Invalid user ID or user is not banned.",
            ephemeral=True
        )


@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason provided"
):

    until = discord.utils.utcnow() + timedelta(
        minutes=minutes
    )

    try:
        await member.timeout(
            until,
            reason=reason
        )

        await interaction.response.send_message(
            f"⏳ {member.mention} timed out for **{minutes} minutes**."
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ I could not timeout that member.",
            ephemeral=True
        )


@bot.tree.command(name="untimeout", description="Remove a timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction, member: discord.Member):

    try:
        await member.timeout(None)

        await interaction.response.send_message(
            f"✅ Timeout removed from {member.mention}."
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ I could not remove the timeout.",
            ephemeral=True
        )


@bot.tree.command(name="warn", description="Warn a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction, member: discord.Member, reason: str):

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS moderation_warnings (
            guild_id INTEGER,
            user_id INTEGER,
            reason TEXT,
            created INTEGER
        )
    """)

    conn.execute("""
        INSERT INTO moderation_warnings
        VALUES(?,?,?,?)
    """, (
        interaction.guild.id,
        member.id,
        reason,
        int(time.time())
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned.\n"
        f"Reason: {reason}"
    )


@bot.tree.command(name="warnings", description="View member warnings")
async def warnings(interaction, member: discord.Member):

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS moderation_warnings (
            guild_id INTEGER,
            user_id INTEGER,
            reason TEXT,
            created INTEGER
        )
    """)

    rows = conn.execute("""
        SELECT reason
        FROM moderation_warnings
        WHERE guild_id=? AND user_id=?
        ORDER BY created DESC
        LIMIT 10
    """, (
        interaction.guild.id,
        member.id
    )).fetchall()

    conn.close()

    if not rows:
        return await interaction.response.send_message(
            f"✅ {member.mention} has no warnings.",
            ephemeral=True
        )

    text = "\n".join(
        f"• {row['reason']}"
        for row in rows
    )

    await interaction.response.send_message(
        f"⚠️ Warnings for {member.mention}:\n{text}",
        ephemeral=True
    )


@bot.tree.command(name="clearwarns", description="Clear member warnings")
@app_commands.checks.has_permissions(moderate_members=True)
async def clearwarns(interaction, member: discord.Member):

    conn = get_db()

    conn.execute("""
        DELETE FROM moderation_warnings
        WHERE guild_id=? AND user_id=?
    """, (
        interaction.guild.id,
        member.id
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ Warnings cleared for {member.mention}."
    )


@bot.tree.command(name="mute", description="Mute a member using a role")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction, member: discord.Member, role: discord.Role):

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            "❌ I cannot manage that role.",
            ephemeral=True
        )

    try:
        await member.add_roles(
            role,
            reason="SECURITY mute"
        )

        await interaction.response.send_message(
            f"🔇 {member.mention} has been muted."
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ I could not mute that member.",
            ephemeral=True
        )


@bot.tree.command(name="unmute", description="Unmute a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction, member: discord.Member, role: discord.Role):

    try:
        await member.remove_roles(
            role,
            reason="SECURITY unmute"
        )

        await interaction.response.send_message(
            f"🔊 {member.mention} has been unmuted."
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ I could not unmute that member.",
            ephemeral=True
        )


@bot.tree.command(name="nick", description="Change a member nickname")
@app_commands.checks.has_permissions(manage_nicknames=True)
async def nick(interaction, member: discord.Member, nickname: str):

    try:
        await member.edit(
            nick=nickname
        )

        await interaction.response.send_message(
            f"✅ Nickname changed for {member.mention}."
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ I could not change that nickname.",
            ephemeral=True
        )


@bot.tree.command(name="slowmode", description="Set channel slowmode")
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(
    interaction,
    seconds: app_commands.Range[int, 0, 21600]
):

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):
        return await interaction.response.send_message(
            "❌ This is not a text channel.",
            ephemeral=True
        )

    await interaction.channel.edit(
        slowmode_delay=seconds
    )

    await interaction.response.send_message(
        f"🐢 Slowmode set to **{seconds} seconds**."
    )


# ============================================================
# END OF PART 12 — 🛡️ MODERATION
# ============================================================
# ============================================================
# START OF PART 13 — 🤖 OTHER AUTOMOD
# ============================================================

@bot.tree.command(name="automod", description="Show AutoMod settings")
async def automod(interaction):

    guild_id = interaction.guild.id

    embed = discord.Embed(
        title="🤖 SECURITY AutoMod",
        description=(
            f"Main AutoMod: "
            f"{'🟢 ON' if get_setting(guild_id,'automod_enabled') else '🔴 OFF'}\n"
            f"Anti-Spam: "
            f"{'🟢 ON' if get_setting(guild_id,'anti_spam_enabled') else '🔴 OFF'}\n"
            f"Anti-Invite: "
            f"{'🟢 ON' if get_setting(guild_id,'anti_invite_enabled') else '🔴 OFF'}\n"
            f"Anti-Mention: "
            f"{'🟢 ON' if get_setting(guild_id,'anti_mention_enabled') else '🔴 OFF'}"
        )
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(name="automod-on", description="Enable AutoMod")
@app_commands.checks.has_permissions(administrator=True)
async def automod_on(interaction):

    set_setting(
        interaction.guild.id,
        "automod_enabled",
        1
    )

    await interaction.response.send_message(
        "🤖 AutoMod enabled.",
        ephemeral=True
    )


@bot.tree.command(name="automod-off", description="Disable AutoMod")
@app_commands.checks.has_permissions(administrator=True)
async def automod_off(interaction):

    set_setting(
        interaction.guild.id,
        "automod_enabled",
        0
    )

    await interaction.response.send_message(
        "🤖 AutoMod disabled.",
        ephemeral=True
    )


@bot.tree.command(name="anti-spam", description="Toggle Anti-Spam")
@app_commands.checks.has_permissions(administrator=True)
async def anti_spam(interaction, enabled: bool):

    set_setting(
        interaction.guild.id,
        "anti_spam_enabled",
        int(enabled)
    )

    await interaction.response.send_message(
        f"🚫 Anti-Spam: {'🟢 ON' if enabled else '🔴 OFF'}",
        ephemeral=True
    )


@bot.tree.command(name="anti-invite", description="Toggle Discord invite blocking")
@app_commands.checks.has_permissions(administrator=True)
async def anti_invite(interaction, enabled: bool):

    set_setting(
        interaction.guild.id,
        "anti_invite_enabled",
        int(enabled)
    )

    await interaction.response.send_message(
        f"🔗 Anti-Invite: {'🟢 ON' if enabled else '🔴 OFF'}",
        ephemeral=True
    )


@bot.tree.command(name="anti-mention", description="Toggle excessive mention protection")
@app_commands.checks.has_permissions(administrator=True)
async def anti_mention(interaction, enabled: bool):

    set_setting(
        interaction.guild.id,
        "anti_mention_enabled",
        int(enabled)
    )

    await interaction.response.send_message(
        f"📣 Anti-Mention: {'🟢 ON' if enabled else '🔴 OFF'}",
        ephemeral=True
    )


@bot.tree.command(name="wordfilter", description="Add or remove a filtered word")
@app_commands.choices(
    action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove")
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def wordfilter(
    interaction,
    action: app_commands.Choice[str],
    word: str
):

    word = word.lower().strip()

    conn = get_db()

    if action.value == "add":

        conn.execute("""
            INSERT OR IGNORE INTO filtered_words
            VALUES(?,?)
        """, (
            interaction.guild.id,
            word
        ))

    else:

        conn.execute("""
            DELETE FROM filtered_words
            WHERE guild_id=? AND word=?
        """, (
            interaction.guild.id,
            word
        ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ Word filter **{action.name}**: `{word}`.",
        ephemeral=True
    )


# ============================================================
# END OF PART 13 — 🤖 OTHER AUTOMOD
# ============================================================
# ============================================================
# START OF PART 14 — 🎬 CREATOR NOTIFICATIONS
# ============================================================

creator_group = app_commands.Group(
    name="creator",
    description="TikTok, YouTube and Twitch notifications"
)


@creator_group.command(
    name="setup",
    description="Set up Creator Notifications"
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_setup(
    interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "creator_channel_id",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "creator_enabled",
        1
    )

    await interaction.response.send_message(
        f"🎬 Creator notifications will be sent to {channel.mention}.",
        ephemeral=True
    )


@creator_group.command(
    name="add",
    description="Add a creator"
)
@app_commands.choices(
    platform=[
        app_commands.Choice(
            name="🎵 TikTok",
            value="TikTok"
        ),
        app_commands.Choice(
            name="▶️ YouTube",
            value="YouTube"
        ),
        app_commands.Choice(
            name="🟣 Twitch",
            value="Twitch"
        )
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_add(
    interaction,
    platform: app_commands.Choice[str],
    username: str
):

    conn = get_db()

    conn.execute("""
        INSERT INTO creators
        (guild_id,platform,username)
        VALUES(?,?,?)
    """, (
        interaction.guild.id,
        platform.value,
        username.strip()
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ Added **{username}** as a "
        f"**{platform.name}** creator.",
        ephemeral=True
    )


@creator_group.command(
    name="remove",
    description="Remove a creator"
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_remove(
    interaction,
    username: str
):

    conn = get_db()

    conn.execute("""
        DELETE FROM creators
        WHERE guild_id=? AND username=?
    """, (
        interaction.guild.id,
        username
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ Removed `{username}`.",
        ephemeral=True
    )


@creator_group.command(
    name="list",
    description="List creators"
)
async def creator_list(interaction):

    conn = get_db()

    rows = conn.execute("""
        SELECT platform,username
        FROM creators
        WHERE guild_id=?
        ORDER BY platform,username
    """, (
        interaction.guild.id,
    )).fetchall()

    conn.close()

    if not rows:
        return await interaction.response.send_message(
            "🎬 No creators have been added.",
            ephemeral=True
        )

    text = "\n".join(
        f"• **{row['platform']}** — `{row['username']}`"
        for row in rows
    )

    await interaction.response.send_message(
        embed=discord.Embed(
            title="🎬 Creators",
            description=text
        ),
        ephemeral=True
    )


@creator_group.command(
    name="channel",
    description="Change creator notification channel"
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_channel(
    interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "creator_channel_id",
        channel.id
    )

    await interaction.response.send_message(
        f"✅ Creator channel: {channel.mention}",
        ephemeral=True
    )


@creator_group.command(
    name="message",
    description="Set creator notification message"
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_message(
    interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "creator_message",
        message
    )

    await interaction.response.send_message(
        "✅ Creator message saved.\n"
        "Variables: `{user}` `{username}` `{platform}` "
        "`{title}` `{url}` `{channel}` `{thumbnail}` `{date}`",
        ephemeral=True
    )


@creator_group.command(
    name="role",
    description="Set creator notification ping role"
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_role(
    interaction,
    role: discord.Role
):

    set_setting(
        interaction.guild.id,
        "creator_role_id",
        role.id
    )

    await interaction.response.send_message(
        f"✅ Creator notification role: {role.mention}",
        ephemeral=True
    )


@creator_group.command(
    name="role-off",
    description="Disable creator role ping"
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_role_off(interaction):

    set_setting(
        interaction.guild.id,
        "creator_role_id",
        None
    )

    await interaction.response.send_message(
        "✅ Creator role ping disabled.",
        ephemeral=True
    )


@creator_group.command(
    name="on",
    description="Enable creator notifications"
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_on(interaction):

    set_setting(
        interaction.guild.id,
        "creator_enabled",
        1
    )

    await interaction.response.send_message(
        "🎬 Creator notifications enabled.",
        ephemeral=True
    )


@creator_group.command(
    name="off",
    description="Disable creator notifications"
)
@app_commands.checks.has_permissions(administrator=True)
async def creator_off(interaction):

    set_setting(
        interaction.guild.id,
        "creator_enabled",
        0
    )

    await interaction.response.send_message(
        "🎬 Creator notifications disabled.",
        ephemeral=True
    )


@creator_group.command(
    name="test",
    description="Test creator notification"
)
async def creator_test(interaction):

    channel_id = get_setting(
        interaction.guild.id,
        "creator_channel_id"
    )

    channel = (
        interaction.guild.get_channel(channel_id)
        if channel_id
        else interaction.channel
    )

    message = get_setting(
        interaction.guild.id,
        "creator_message"
    )

    message = (
        message
        .replace("{user}", interaction.user.mention)
        .replace("{username}", interaction.user.name)
        .replace("{platform}", "YouTube")
        .replace("{title}", "Test Creator Post")
        .replace("{url}", "https://youtube.com/")
        .replace("{channel}", channel.mention)
        .replace("{thumbnail}", "")
        .replace("{date}", str(datetime.now(timezone.utc).date()))
    )

    role_id = get_setting(
        interaction.guild.id,
        "creator_role_id"
    )

    ping = (
        f"<@&{role_id}> "
        if role_id
        else ""
    )

    await channel.send(
        content=ping + message
    )

    await interaction.response.send_message(
        "✅ Creator notification test sent.",
        ephemeral=True
    )


bot.tree.add_command(creator_group)


# ============================================================
# END OF PART 14 — 🎬 CREATOR
# ============================================================
# ============================================================
# START OF PART 15 — 🎬 TIKTOK SHOWCASE
# ============================================================

showcase_group = app_commands.Group(
    name="showcase",
    description="TikTok and editing showcase system"
)


@showcase_group.command(
    name="setup",
    description="Set up the showcase"
)
@app_commands.checks.has_permissions(administrator=True)
async def showcase_setup(
    interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "showcase_channel_id",
        channel.id
    )

    set_setting(
        interaction.guild.id,
        "showcase_enabled",
        1
    )

    await interaction.response.send_message(
        f"🎬 Showcase channel: {channel.mention}",
        ephemeral=True
    )


@showcase_group.command(
    name="message",
    description="Set showcase message"
)
@app_commands.checks.has_permissions(administrator=True)
async def showcase_message(
    interaction,
    message: str
):

    set_setting(
        interaction.guild.id,
        "showcase_message",
        message
    )

    await interaction.response.send_message(
        "✅ Showcase message saved.",
        ephemeral=True
    )


@showcase_group.command(
    name="on",
    description="Enable showcase"
)
@app_commands.checks.has_permissions(administrator=True)
async def showcase_on(interaction):

    set_setting(
        interaction.guild.id,
        "showcase_enabled",
        1
    )

    await interaction.response.send_message(
        "🎬 Showcase enabled.",
        ephemeral=True
    )


@showcase_group.command(
    name="off",
    description="Disable showcase"
)
@app_commands.checks.has_permissions(administrator=True)
async def showcase_off(interaction):

    set_setting(
        interaction.guild.id,
        "showcase_enabled",
        0
    )

    await interaction.response.send_message(
        "🎬 Showcase disabled.",
        ephemeral=True
    )


@showcase_group.command(
    name="channel",
    description="Change showcase channel"
)
@app_commands.checks.has_permissions(administrator=True)
async def showcase_channel(
    interaction,
    channel: discord.TextChannel
):

    set_setting(
        interaction.guild.id,
        "showcase_channel_id",
        channel.id
    )

    await interaction.response.send_message(
        f"✅ Showcase channel: {channel.mention}",
        ephemeral=True
    )


@showcase_group.command(
    name="role",
    description="Set showcase ping role"
)
@app_commands.checks.has_permissions(administrator=True)
async def showcase_role(
    interaction,
    role: discord.Role
):

    set_setting(
        interaction.guild.id,
        "showcase_role_id",
        role.id
    )

    await interaction.response.send_message(
        f"✅ Showcase role: {role.mention}",
        ephemeral=True
    )


bot.tree.add_command(showcase_group)


# ============================================================
# END OF PART 15 — 🎬 SHOWCASE
# ============================================================
# ============================================================
# START OF PART 16 — 🔧 UTILITY
# ============================================================

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction):

    await interaction.response.send_message(
        f"🏓 **Pong!** `{round(bot.latency * 1000)}ms`"
    )


@bot.tree.command(name="botinfo", description="Show bot information")
async def botinfo(interaction):

    embed = discord.Embed(
        title="🔐 SECURITY",
        description=(
            "**Professional Discord security and community bot.**\n\n"
            f"Servers: **{len(bot.guilds)}**\n"
            f"Users: **{len(bot.users)}**\n"
            f"Uptime: **{human_uptime()}**\n"
            f"Latency: **{round(bot.latency * 1000)}ms**"
        )
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(name="serverinfo", description="Show server information")
async def serverinfo(interaction):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"🏠 {guild.name}",
        description=(
            f"Owner: <@{guild.owner_id}>\n"
            f"Members: **{guild.member_count}**\n"
            f"Roles: **{len(guild.roles)}**\n"
            f"Channels: **{len(guild.channels)}**\n"
            f"Boosts: **{guild.premium_subscription_count or 0}**\n"
            f"Boost Level: **{guild.premium_tier}**"
        )
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(name="userinfo", description="Show member information")
async def userinfo(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    embed = discord.Embed(
        title=f"👤 {member}",
        description=(
            f"ID: `{member.id}`\n"
            f"Bot: **{'Yes' if member.bot else 'No'}**\n"
            f"Joined: <t:{int(member.joined_at.timestamp())}:F>\n"
            f"Created: <t:{int(member.created_at.timestamp())}:F>"
        )
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(name="avatar", description="Show a member avatar")
async def avatar(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    embed = discord.Embed(
        title=f"🖼️ {member.display_name}'s Avatar"
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(name="banner", description="Show a user's banner")
async def banner(
    interaction,
    user: discord.User = None
):

    user = user or interaction.user

    user = await bot.fetch_user(user.id)

    if not user.banner:
        return await interaction.response.send_message(
            "❌ This user doesn't have a banner.",
            ephemeral=True
        )

    embed = discord.Embed(
        title=f"🖼️ {user.name}'s Banner"
    )

    embed.set_image(
        url=user.banner.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(name="roleinfo", description="Show role information")
async def roleinfo(
    interaction,
    role: discord.Role
):

    await interaction.response.send_message(
        embed=discord.Embed(
            title=f"🎭 {role.name}",
            description=(
                f"ID: `{role.id}`\n"
                f"Members: **{len(role.members)}**\n"
                f"Position: **{role.position}**\n"
                f"Mentionable: **{role.mentionable}**\n"
                f"Managed: **{role.managed}**"
            )
        )
    )


@bot.tree.command(name="channelinfo", description="Show channel information")
async def channelinfo(
    interaction,
    channel: discord.TextChannel = None
):

    channel = channel or interaction.channel

    await interaction.response.send_message(
        embed=discord.Embed(
            title=f"💬 #{channel.name}",
            description=(
                f"ID: `{channel.id}`\n"
                f"Category: **{channel.category}**\n"
                f"Slowmode: **{channel.slowmode_delay}s**\n"
                f"Position: **{channel.position}**"
            )
        )
    )


@bot.tree.command(name="emojiinfo", description="Show emoji information")
async def emojiinfo(
    interaction: discord.Interaction,
    emoji: str
):
    await interaction.response.send_message(
        f"😀 **Emoji Information**\n\n"
        f"Emoji: {emoji}"
    )
    
@bot.tree.command(name="permissions", description="Show your permissions")
async def permissions(interaction):

    perms = interaction.user.guild_permissions

    important = [
        "administrator",
        "manage_guild",
        "manage_channels",
        "manage_roles",
        "manage_messages",
        "kick_members",
        "ban_members",
        "moderate_members",
        "mention_everyone"
    ]

    text = "\n".join(
        f"{'✅' if getattr(perms, p) else '❌'} {p.replace('_',' ').title()}"
        for p in important
    )

    await interaction.response.send_message(
        text,
        ephemeral=True
    )


@bot.tree.command(name="uptime", description="Show bot uptime")
async def uptime(interaction):

    await interaction.response.send_message(
        f"⏱️ SECURITY uptime: **{human_uptime()}**"
    )


# ============================================================
# END OF PART 16 — 🔧 UTILITY
# ============================================================
# ============================================================
# START OF PART 17 — 🎉 FUN & COMMUNITY
# ============================================================

@bot.tree.command(name="8ball", description="Ask the magic 8-ball")
async def eightball(interaction, question: str):

    answers = [
        "Yes.",
        "No.",
        "Definitely.",
        "Probably.",
        "Probably not.",
        "Ask again later.",
        "Absolutely.",
        "I don't think so."
    ]

    await interaction.response.send_message(
        f"🎱 **Question:** {question}\n"
        f"**Answer:** {random.choice(answers)}"
    )


@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction):

    await interaction.response.send_message(
        f"🪙 **{random.choice(['Heads', 'Tails'])}!**"
    )


@bot.tree.command(name="roll", description="Roll a dice")
async def roll(
    interaction,
    sides: app_commands.Range[int, 2, 1000] = 6
):

    await interaction.response.send_message(
        f"🎲 You rolled **{random.randint(1, sides)}** / {sides}."
    )


@bot.tree.command(name="choose", description="Choose between options")
async def choose(
    interaction,
    options: str
):

    choices = [
        x.strip()
        for x in options.split(",")
        if x.strip()
    ]

    if len(choices) < 2:
        return await interaction.response.send_message(
            "❌ Give at least two choices separated by commas.",
            ephemeral=True
        )

    await interaction.response.send_message(
        f"🎯 I choose **{random.choice(choices)}**!"
    )


@bot.tree.command(name="ship", description="Ship two members")
async def ship(
    interaction,
    member1: discord.Member,
    member2: discord.Member
):

    score = random.randint(0, 100)

    await interaction.response.send_message(
        f"💘 {member1.mention} + {member2.mention}\n"
        f"**Compatibility: {score}%**"
    )


@bot.tree.command(name="rate", description="Rate something")
async def rate(
    interaction,
    thing: str
):

    score = random.randint(1, 10)

    await interaction.response.send_message(
        f"⭐ I rate **{thing}** **{score}/10**."
    )


@bot.tree.command(name="poll", description="Create a simple poll")
@app_commands.checks.has_permissions(manage_messages=True)
async def poll(
    interaction,
    question: str
):

    embed = discord.Embed(
        title="📊 Poll",
        description=question
    )

    await interaction.response.send_message(
        embed=embed
    )

    message = await interaction.original_response()

    await message.add_reaction("👍")
    await message.add_reaction("👎")


@bot.tree.command(name="afk", description="Set your AFK message")
async def afk(
    interaction,
    message: str = "I am AFK."
):

    set_setting(
        interaction.guild.id,
        f"afk_{interaction.user.id}",
        message
    )

    await interaction.response.send_message(
        f"💤 AFK enabled: {message}",
        ephemeral=True
    )


@bot.tree.command(name="remind", description="Set a reminder")
async def remind(
    interaction,
    minutes: app_commands.Range[int, 1, 10080],
    message: str
):

    remind_at = int(
        time.time() + minutes * 60
    )

    conn = get_db()

    conn.execute("""
        INSERT INTO reminders
        (user_id,channel_id,message,remind_at)
        VALUES(?,?,?,?)
    """, (
        interaction.user.id,
        interaction.channel.id,
        message,
        remind_at
    ))

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"⏰ Reminder set for **{minutes} minutes**."
    )


@bot.tree.command(name="giveaway", description="Create a basic giveaway")
@app_commands.checks.has_permissions(manage_messages=True)
async def giveaway(
    interaction,
    minutes: app_commands.Range[int, 1, 10080],
    prize: str
):

    end = int(time.time() + minutes * 60)

    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=(
            f"Prize: **{prize}**\n\n"
            "React with 🎉 to enter!\n"
            f"Ends <t:{end}:R>"
        )
    )

    await interaction.response.send_message(
        embed=embed
    )

    message = await interaction.original_response()

    await message.add_reaction("🎉")


@bot.tree.command(name="reroll", description="Reroll a giveaway message")
@app_commands.checks.has_permissions(manage_messages=True)
async def reroll(
    interaction,
    message_id: str
):

    try:
        message = await interaction.channel.fetch_message(
            int(message_id)
        )

        reaction = discord.utils.get(
            message.reactions,
            emoji="🎉"
        )

        if not reaction:
            return await interaction.response.send_message(
                "❌ No 🎉 reaction found.",
                ephemeral=True
            )

        users = [
            user async for user in reaction.users()
            if not user.bot
        ]

        if not users:
            return await interaction.response.send_message(
                "❌ No entries.",
                ephemeral=True
            )

        winner = random.choice(users)

        await interaction.response.send_message(
            f"🎉 New winner: {winner.mention}!"
        )

    except (ValueError, discord.HTTPException):
        await interaction.response.send_message(
            "❌ Invalid message ID.",
            ephemeral=True
        )


# ============================================================
# END OF PART 17 — 🎉 FUN & COMMUNITY
# ============================================================
# ============================================================
# START OF PART 18 — 🖼️ MEDIA
# ============================================================

@bot.tree.command(name="emoji", description="Show an emoji")
async def emoji_command(
    interaction,
    emoji: discord.Emoji
):

    await interaction.response.send_message(
        str(emoji)
    )


@bot.tree.command(name="emojilist", description="List server emojis")
async def emojilist(interaction):

    emojis = interaction.guild.emojis

    if not emojis:
        return await interaction.response.send_message(
            "😀 This server has no custom emojis."
        )

    text = " ".join(
        str(emoji)
        for emoji in emojis[:100]
    )

    await interaction.response.send_message(
        text
    )


@bot.tree.command(name="sticker", description="Show a server sticker")
async def sticker(
    interaction,
    sticker: discord.GuildSticker
):

    await interaction.response.send_message(
        sticker.url
    )


@bot.tree.command(name="stickerlist", description="List server stickers")
async def stickerlist(interaction):

    stickers = interaction.guild.stickers

    if not stickers:
        return await interaction.response.send_message(
            "🎨 No server stickers."
        )

    text = "\n".join(
        f"• {sticker.name}"
        for sticker in stickers
    )

    await interaction.response.send_message(
        text
    )


@bot.tree.command(name="roleicon", description="Show a role icon")
async def roleicon(
    interaction,
    role: discord.Role
):

    if not role.icon:
        return await interaction.response.send_message(
            "❌ That role has no icon.",
            ephemeral=True
        )

    await interaction.response.send_message(
        role.icon.url
    )


@bot.tree.command(name="banner-user", description="Show a user's banner")
async def banner_user(
    interaction,
    user: discord.User = None
):

    user = user or interaction.user

    user = await bot.fetch_user(
        user.id
    )

    if not user.banner:
        return await interaction.response.send_message(
            "❌ No banner found.",
            ephemeral=True
        )

    embed = discord.Embed(
        title=f"🖼️ {user.name}"
    )

    embed.set_image(
        url=user.banner.url
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# END OF PART 18 — 🖼️ MEDIA
# ============================================================
# ============================================================
# START OF PART 19 — 🔐 SECURITY
# ============================================================

@bot.tree.command(name="auditlog", description="Show recent audit actions")
@app_commands.checks.has_permissions(view_audit_log=True)
async def auditlog(interaction):

    lines = []

    async for entry in interaction.guild.audit_logs(limit=10):

        lines.append(
            f"• **{entry.action.name}** — "
            f"{entry.user}"
        )

    if not lines:
        lines.append("No audit entries found.")

    await interaction.response.send_message(
        "\n".join(lines),
        ephemeral=True
    )


@bot.tree.command(name="securitycheck", description="Check SECURITY bot permissions")
async def securitycheck(interaction):

    me = interaction.guild.me

    required = {
        "View Channel": me.guild_permissions.view_channel,
        "Send Messages": me.guild_permissions.send_messages,
        "Manage Messages": me.guild_permissions.manage_messages,
        "Manage Roles": me.guild_permissions.manage_roles,
        "Kick Members": me.guild_permissions.kick_members,
        "Ban Members": me.guild_permissions.ban_members,
        "Moderate Members": me.guild_permissions.moderate_members,
        "Manage Channels": me.guild_permissions.manage_channels
    }

    text = "\n".join(
        f"{'✅' if value else '❌'} {name}"
        for name, value in required.items()
    )

    await interaction.response.send_message(
        f"🔐 **SECURITY Permission Check**\n\n{text}",
        ephemeral=True
    )


@bot.tree.command(name="adminlist", description="List server administrators")
@app_commands.checks.has_permissions(administrator=True)
async def adminlist(interaction):

    members = [
        member.mention
        for member in interaction.guild.members
        if member.guild_permissions.administrator
    ]

    await interaction.response.send_message(
        "👑 **Administrators**\n" +
        ("\n".join(members) if members else "None"),
        ephemeral=True
    )


@bot.tree.command(name="stafflist", description="List staff members")
@app_commands.checks.has_permissions(administrator=True)
async def stafflist(interaction):

    found = []

    keywords = (
        "staff",
        "mod",
        "admin",
        "owner",
        "helper"
    )

    for member in interaction.guild.members:

        if any(
            any(
                word in role.name.lower()
                for word in keywords
            )
            for role in member.roles
        ):
            found.append(member.mention)

    found = list(dict.fromkeys(found))

    await interaction.response.send_message(
        "🛡️ **Staff Members**\n" +
        ("\n".join(found) if found else "None"),
        ephemeral=True
    )


@bot.tree.command(name="botlist", description="List bots in the server")
async def botlist(interaction):

    bots = [
        member.mention
        for member in interaction.guild.members
        if member.bot
    ]

    await interaction.response.send_message(
        "🤖 **Bots**\n" +
        ("\n".join(bots) if bots else "None")
    )


@bot.tree.command(name="recentjoins", description="Show recent joins")
async def recentjoins(interaction):

    conn = get_db()

    rows = conn.execute("""
        SELECT username,created
        FROM member_events
        WHERE guild_id=? AND event='join'
        ORDER BY created DESC
        LIMIT 10
    """, (
        interaction.guild.id,
    )).fetchall()

    conn.close()

    text = "\n".join(
        f"• {row['username']} — <t:{row['created']}:R>"
        for row in rows
    )

    await interaction.response.send_message(
        "📥 **Recent Joins**\n" +
        (text or "No data yet.")
    )


@bot.tree.command(name="recentleaves", description="Show recent leaves")
async def recentleaves(interaction):

    conn = get_db()

    rows = conn.execute("""
        SELECT username,created
        FROM member_events
        WHERE guild_id=? AND event='leave'
        ORDER BY created DESC
        LIMIT 10
    """, (
        interaction.guild.id,
    )).fetchall()

    conn.close()

    text = "\n".join(
        f"• {row['username']} — <t:{row['created']}:R>"
        for row in rows
    )

    await interaction.response.send_message(
        "📤 **Recent Leaves**\n" +
        (text or "No data yet.")
    )


@bot.tree.command(name="accountage", description="Show account age")
async def accountage(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    await interaction.response.send_message(
        f"📅 {member.mention} created their account "
        f"<t:{int(member.created_at.timestamp())}:R>."
    )


@bot.tree.command(name="permissions-check", description="Check another member's permissions")
async def permissions_check(
    interaction,
    member: discord.Member = None
):

    member = member or interaction.user

    perms = member.guild_permissions

    important = [
        "administrator",
        "manage_guild",
        "manage_channels",
        "manage_roles",
        "manage_messages",
        "kick_members",
        "ban_members",
        "moderate_members"
    ]

    text = "\n".join(
        f"{'✅' if getattr(perms, p) else '❌'} "
        f"{p.replace('_',' ').title()}"
        for p in important
    )

    await interaction.response.send_message(
        f"🔐 Permissions for {member.mention}\n\n{text}",
        ephemeral=True
    )


# ============================================================
# END OF PART 19 — 🔐 SECURITY
# ============================================================
# ============================================================
# START OF PART 20 — 🏆 COMMUNITY
# ============================================================

@bot.tree.command(name="topmembers", description="Show members with the highest levels")
async def topmembers(interaction):

    conn = get_db()

    rows = conn.execute("""
        SELECT user_id,level,xp
        FROM xp
        WHERE guild_id=?
        ORDER BY level DESC,xp DESC
        LIMIT 10
    """, (
        interaction.guild.id,
    )).fetchall()

    conn.close()

    if not rows:
        return await interaction.response.send_message(
            "🏆 No member data yet."
        )

    text = []

    for index, row in enumerate(rows, 1):

        member = interaction.guild.get_member(
            row["user_id"]
        )

        name = (
            member.display_name
            if member
            else str(row["user_id"])
        )

        text.append(
            f"**{index}.** {name} — "
            f"Level {row['level']} • {row['xp']} XP"
        )

    await interaction.response.send_message(
        "🏆 **Top Members**\n\n" +
        "\n".join(text)
    )


@bot.tree.command(name="oldestmember", description="Show the oldest server member")
async def oldestmember(interaction):

    members = [
        m for m in interaction.guild.members
        if not m.bot
    ]

    if not members:
        return await interaction.response.send_message(
            "No members found."
        )

    member = min(
        members,
        key=lambda m: m.joined_at or discord.utils.utcnow()
    )

    await interaction.response.send_message(
        f"👴 Oldest member by server join date: "
        f"{member.mention}"
    )


@bot.tree.command(name="newestmember", description="Show the newest server member")
async def newestmember(interaction):

    members = [
        m for m in interaction.guild.members
        if not m.bot and m.joined_at
    ]

    if not members:
        return await interaction.response.send_message(
            "No members found."
        )

    member = max(
        members,
        key=lambda m: m.joined_at
    )

    await interaction.response.send_message(
        f"🆕 Newest member: {member.mention}"
    )


@bot.tree.command(name="boosters", description="Show server boosters")
async def boosters(interaction):

    members = interaction.guild.premium_subscribers

    text = "\n".join(
        member.mention
        for member in members
    )

    await interaction.response.send_message(
        "🚀 **Boosters**\n" +
        (text or "No boosters.")
    )


@bot.tree.command(name="boostlevel", description="Show server boost level")
async def boostlevel(interaction):

    guild = interaction.guild

    await interaction.response.send_message(
        f"🚀 **Boost Level:** {guild.premium_tier}\n"
        f"**Boosts:** {guild.premium_subscription_count or 0}"
    )


@bot.tree.command(name="serverroles", description="List server roles")
async def serverroles(interaction):

    roles = [
        role.mention
        for role in reversed(interaction.guild.roles)
        if not role.is_default()
    ]

    if len(roles) > 100:
        roles = roles[:100]

    await interaction.response.send_message(
        "🎭 **Server Roles**\n" +
        "\n".join(roles)
    )


# ============================================================
# END OF PART 20 — 🏆 COMMUNITY
# ============================================================
# ============================================================
# START OF PART 21 — ❓ HELP
# ============================================================

HELP_CATEGORIES = {
    "👋 Welcome": [
        "/welcome",
        "/welcome-on",
        "/welcome-off",
        "/welcome-message",
        "/welcome-image",
        "/welcome-style",
        "/welcome-role",
        "/welcome-role-off",
        "/testwelcome"
    ],

    "👋 Bye": [
        "/bye",
        "/bye-on",
        "/bye-off",
        "/bye-message",
        "/bye-image",
        "/bye-style",
        "/testbye"
    ],

    "🛡️ Verification": [
        "/verifysetup",
        "/verifymessage",
        "/verifyrole",
        "/verifychannel",
        "/verify-on",
        "/verify-off",
        "/verifytest"
    ],

    "🎫 Tickets": [
        "/ticketsetup",
        "/ticket",
        "/close",
        "/add",
        "/remove",
        "/ticketcategory",
        "/ticketchannel",
        "/ticketrole"
    ],

    "🧹 Cleaner": [
        "/clear",
        "/clean",
        "/clean-message",
        "/clear-user",
        "/clear-bots",
        "/clear-links",
        "/clear-attachments"
    ],

    "☢️ Server Wipe": [
        "/wipe"
    ],

    "⭐ Levels": [
        "/setuplevel",
        "/level",
        "/leaderboard",
        "/levelrole",
        "/levelrole-remove",
        "/levelmessage",
        "/level-on",
        "/level-off",
        "/levelimage",
        "/levelimage-on",
        "/levelimage-off",
        "/leveltest"
    ],

    "📊 Statistics": [
        "/memberstats",
        "/botstats",
        "/serverstats",
        "/channelstats",
        "/rolestats",
        "/booststats",
        "/activitystats",
        "/servercount"
    ],

    "🔗 Anti-Link": [
        "/antilink setup",
        "/antilink on",
        "/antilink off",
        "/antilink channel",
        "/antilink message",
        "/antilink warnings",
        "/antilink reset",
        "/antilink mute-role",
        "/antilink exempt-role",
        "/antilink remove-exempt-role",
        "/antilink log",
        "/antilink ban-channel",
        "/antilink ban-message"
    ],

    "🛡️ Moderation": [
        "/kick",
        "/ban",
        "/unban",
        "/timeout",
        "/untimeout",
        "/warn",
        "/warnings",
        "/clearwarns",
        "/mute",
        "/unmute",
        "/nick",
        "/slowmode"
    ],

    "🤖 AutoMod": [
        "/automod",
        "/automod-on",
        "/automod-off",
        "/anti-spam",
        "/anti-invite",
        "/anti-mention",
        "/wordfilter"
    ],

    "🎬 Creator": [
        "/creator setup",
        "/creator add",
        "/creator remove",
        "/creator list",
        "/creator channel",
        "/creator message",
        "/creator role",
        "/creator role-off",
        "/creator on",
        "/creator off",
        "/creator test"
    ],

    "🎬 Showcase": [
        "/showcase setup",
        "/showcase message",
        "/showcase on",
        "/showcase off",
        "/showcase channel",
        "/showcase role"
    ],

    "🔧 Utility": [
        "/ping",
        "/botinfo",
        "/serverinfo",
        "/userinfo",
        "/avatar",
        "/banner",
        "/roleinfo",
        "/channelinfo",
        "/emojiinfo",
        "/permissions",
        "/uptime"
    ],

    "🎉 Fun": [
        "/8ball",
        "/coinflip",
        "/roll",
        "/choose",
        "/ship",
        "/rate",
        "/poll",
        "/giveaway",
        "/reroll",
        "/afk",
        "/remind"
    ],

    "🖼️ Media": [
        "/emoji",
        "/emojilist",
        "/sticker",
        "/stickerlist",
        "/roleicon",
        "/banner-user"
    ],

    "🔐 Security": [
        "/auditlog",
        "/securitycheck",
        "/adminlist",
        "/stafflist",
        "/botlist",
        "/recentjoins",
        "/recentleaves",
        "/accountage",
        "/permissions-check"
    ],

    "🏆 Community": [
        "/topmembers",
        "/oldestmember",
        "/newestmember",
        "/boosters",
        "/boostlevel",
        "/serverroles"
    ]
}


@bot.tree.command(
    name="help",
    description="Show the SECURITY command panel"
)
async def help_command(interaction):

    embed = discord.Embed(
        title="🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘 — COMMAND PANEL",
        description=(
            "Professional Discord security, "
            "moderation and community tools."
        )
    )

    for category, commands_list in HELP_CATEGORIES.items():

        value = "\n".join(
            f"`{command}`"
            for command in commands_list
        )

        # Discord embed field limit
        if len(value) > 1024:
            value = value[:1000] + "\n..."

        embed.add_field(
            name=category,
            value=value,
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="commands",
    description="Show all SECURITY commands"
)
async def commands_command(interaction):

    await help_command(interaction)


@bot.tree.command(
    name="about",
    description="About SECURITY"
)
async def about(interaction):

    embed = discord.Embed(
        title="🔐 𝐒𝐄𝐂𝐔𝐑𝐈𝐓𝐘",
        description=(
            "**Professional Discord Security Bot**\n\n"
            "🛡️ Moderation\n"
            "🔗 Anti-Link protection\n"
            "⭐ Level system\n"
            "🎫 Tickets\n"
            "👋 Welcome & Bye\n"
            "🛡️ Verification\n"
            "🎬 Creator notifications\n"
            "📊 Statistics\n"
            "🎉 Community tools\n\n"
            "No chatbot feature."
        )
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# END OF PART 21 — ❓ HELP
# ============================================================
# ============================================================
# START OF PART 22 — ⚙️ EVENTS + PERSISTENCE
# ============================================================

message_spam_cache = {}


async def process_other_automod(
    message: discord.Message
):

    if not message.guild:
        return

    if message.author.bot:
        return

    if not get_setting(
        message.guild.id,
        "automod_enabled"
    ):
        return

    member = message.author

    if member.guild_permissions.administrator:
        return

    # Anti-invite
    if get_setting(
        message.guild.id,
        "anti_invite_enabled"
    ):

        if re.search(
            r"(discord\.gg/|discord\.com/invite/)",
            message.content,
            re.I
        ):

            try:
                await message.delete()

                await message.channel.send(
                    f"🚫 {member.mention}, Discord invites are not allowed here.",
                    delete_after=5
                )

            except discord.HTTPException:
                pass

            return

    # Anti-mention
    if get_setting(
        message.guild.id,
        "anti_mention_enabled"
    ):

        if len(message.mentions) >= 5:

            try:
                await message.delete()

                await message.channel.send(
                    f"📣 {member.mention}, too many mentions.",
                    delete_after=5
                )

            except discord.HTTPException:
                pass

            return

    # Word filter
    conn = get_db()

    words = conn.execute("""
        SELECT word
        FROM filtered_words
        WHERE guild_id=?
    """, (
        message.guild.id,
    )).fetchall()

    conn.close()

    content_lower = message.content.lower()

    for row in words:

        if row["word"].lower() in content_lower:

            try:
                await message.delete()

                await message.channel.send(
                    f"⚠️ {member.mention}, that word is not allowed here.",
                    delete_after=5
                )

            except discord.HTTPException:
                pass

            return

    # Simple anti-spam
    if get_setting(
        message.guild.id,
        "anti_spam_enabled"
    ):

        key = (
            message.guild.id,
            member.id
        )

        current = time.time()

        timestamps = message_spam_cache.setdefault(
            key,
            []
        )

        timestamps[:] = [
            x for x in timestamps
            if current - x < 5
        ]

        timestamps.append(current)

        if len(timestamps) >= 6:

            try:
                await message.delete()
                await member.timeout(
                    discord.utils.utcnow()
                    + timedelta(minutes=1),
                    reason="SECURITY Anti-Spam"
                )

                timestamps.clear()

                await message.channel.send(
                    f"🚫 {member.mention} was temporarily "
                    "timed out for spam.",
                    delete_after=7
                )

            except discord.HTTPException:
                pass


@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    # Activity counter
    if message.guild:

        conn = get_db()

        conn.execute("""
            INSERT INTO activity(guild_id,messages)
            VALUES(?,1)
            ON CONFLICT(guild_id)
            DO UPDATE SET messages=messages+1
        """, (
            message.guild.id,
        ))

        conn.commit()
        conn.close()

    await punish_antilink(message)

    await process_other_automod(message)

    await process_level_xp(message)

    await bot.process_commands(message)


@bot.event
async def on_member_join(member: discord.Member):

    ensure(member.guild.id)

    conn = get_db()

    conn.execute("""
        INSERT INTO member_events
        (guild_id,user_id,username,event,created)
        VALUES(?,?,?,?,?)
    """, (
        member.guild.id,
        member.id,
        str(member),
        "join",
        int(time.time())
    ))

    conn.commit()
    conn.close()

    await send_welcome(member)


@bot.event
async def on_member_remove(member: discord.Member):

    ensure(member.guild.id)

    conn = get_db()

    conn.execute("""
        INSERT INTO member_events
        (guild_id,user_id,username,event,created)
        VALUES(?,?,?,?,?)
    """, (
        member.guild.id,
        member.id,
        str(member),
        "leave",
        int(time.time())
    ))

    conn.commit()
    conn.close()

    await send_bye(member)


# ============================================================
# END OF PART 22 — ⚙️ EVENTS
# ============================================================
# ============================================================
# START OF PART 23 — 🚨 ERROR HANDLER
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        message = (
            "❌ You don't have the required permissions "
            "to use this command."
        )

    elif isinstance(
        error,
        app_commands.errors.BotMissingPermissions
    ):

        message = (
            "❌ I don't have the required permissions "
            "to perform this command."
        )

    elif isinstance(
        error,
        app_commands.errors.CommandOnCooldown
    ):

        message = (
            f"⏳ Try again in "
            f"**{error.retry_after:.1f}s**."
        )

    elif isinstance(
        error,
        app_commands.errors.TransformerError
    ):

        message = (
            "❌ One of the values you selected is invalid."
        )

    else:

        print(
            "SECURITY COMMAND ERROR:",
            repr(error)
        )

        message = (
            "❌ Something went wrong while executing "
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

    except discord.HTTPException:
        pass


# ============================================================
# END OF PART 23 — 🚨 ERROR HANDLER
# ============================================================
# ============================================================
# START OF FINAL PART — 🚀 STARTUP
# ============================================================

@bot.event
async def on_ready():

    print(
        f"🚀 SECURITY is online as "
        f"{bot.user} ({bot.user.id})"
    )

    print(
        f"🌐 Servers: {len(bot.guilds)}"
    )

    print(
        f"⚡ Ping: {round(bot.latency * 1000)}ms"
    )

    # Make sure database exists
    init_database()

    # Add migrations safely
    try:
        migrate_settings()
    except Exception as error:
        print(
            "Database migration warning:",
            repr(error)
        )

    # Persistent verification button
    try:
        bot.add_view(
            VerifyView()
        )
    except Exception:
        pass

    # Sync slash commands
    try:
        synced = await bot.tree.sync()

        print(
            f"✅ Synced {len(synced)} slash commands."
        )

    except Exception as error:

        print(
            "❌ Slash command sync error:",
            repr(error)
        )


# ============================================================
# START BOT
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN environment variable is missing!"
    )

init_database()

bot.run(TOKEN)

# ============================================================
# END OF FINAL PART
# ============================================================
