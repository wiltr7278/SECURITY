import os
import random
import asyncio
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# CONFIG
# =========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

settings = {}
xp_data = {}


def get_settings(guild_id):
    if guild_id not in settings:
        settings[guild_id] = {
            "welcome_channel": None,
            "goodbye_channel": None,
            "welcome_message": "👋 Welcome {user} to {server}!",
            "goodbye_message": "👋 Goodbye {user}!",
            "verify_channel": None,
            "verify_role": None,
            "autorole": None,
            "ai_channel": None,
            "log_channel": None,
        }

    return settings[guild_id]


# =========================================================
# STARTUP
# =========================================================

@bot.event
async def on_ready():
    print(f"✅ SECURITY is online as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as error:
        print(f"❌ Slash sync error: {error}")

    await bot.change_presence(
        activity=discord.Game(
            name="/help | SECURITY"
        )
    )


# =========================================================
# WELCOME
# =========================================================

@bot.event
async def on_member_join(member):
    data = get_settings(member.guild.id)

    role_id = data["autorole"]

    if role_id:
        role = member.guild.get_role(role_id)

        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

    channel_id = data["welcome_channel"]

    if channel_id:
        channel = member.guild.get_channel(channel_id)

        if channel:
            message = data["welcome_message"]

            message = message.replace(
                "{user}",
                member.mention
            )

            message = message.replace(
                "{username}",
                member.name
            )

            message = message.replace(
                "{server}",
                member.guild.name
            )

            await channel.send(message)

    await send_log(
        member.guild,
        f"📥 **Member Joined**\n"
        f"{member.mention} joined the server."
    )


# =========================================================
# GOODBYE
# =========================================================

@bot.event
async def on_member_remove(member):
    data = get_settings(member.guild.id)

    channel_id = data["goodbye_channel"]

    if channel_id:
        channel = member.guild.get_channel(channel_id)

        if channel:
            message = data["goodbye_message"]

            message = message.replace(
                "{user}",
                member.name
            )

            message = message.replace(
                "{username}",
                member.name
            )

            message = message.replace(
                "{server}",
                member.guild.name
            )

            await channel.send(message)

    await send_log(
        member.guild,
        f"📤 **Member Left**\n"
        f"`{member}` left the server."
    )


# =========================================================
# WELCOME SETTINGS
# =========================================================

@bot.tree.command(
    name="setwelcome",
    description="Set the welcome channel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setwelcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    data = get_settings(interaction.guild.id)

    data["welcome_channel"] = channel.id

    await interaction.response.send_message(
        f"👋 Welcome channel set to {channel.mention}."
    )


@bot.tree.command(
    name="setwelcomemessage",
    description="Set the welcome message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setwelcomemessage(
    interaction: discord.Interaction,
    message: str
):
    data = get_settings(interaction.guild.id)

    data["welcome_message"] = message

    await interaction.response.send_message(
        "✅ Welcome message updated."
    )


# =========================================================
# GOODBYE SETTINGS
# =========================================================

@bot.tree.command(
    name="setgoodbye",
    description="Set the goodbye channel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setgoodbye(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    data = get_settings(interaction.guild.id)

    data["goodbye_channel"] = channel.id

    await interaction.response.send_message(
        f"👋 Goodbye channel set to {channel.mention}."
    )


@bot.tree.command(
    name="setgoodbyemessage",
    description="Set the goodbye message"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setgoodbyemessage(
    interaction: discord.Interaction,
    message: str
):
    data = get_settings(interaction.guild.id)

    data["goodbye_message"] = message

    await interaction.response.send_message(
        "✅ Goodbye message updated."
    )# =========================================================
# VERIFICATION
# =========================================================

class VerifyView(discord.ui.View):

    def __init__(self, role_id):
        super().__init__(timeout=None)

        self.role_id = role_id

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.green,
        emoji="✅",
        custom_id="security_verify"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        role = interaction.guild.get_role(
            self.role_id
        )

        if role is None:
            await interaction.response.send_message(
                "❌ Verification role no longer exists.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.add_roles(role)

            await interaction.response.send_message(
                "✅ You are verified!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I cannot give you the verification role.",
                ephemeral=True
            )


@bot.tree.command(
    name="verifysetup",
    description="Set up the verification system"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def verifysetup(
    interaction: discord.Interaction,
    role: discord.Role,
    channel: discord.TextChannel
):
    data = get_settings(interaction.guild.id)

    data["verify_role"] = role.id
    data["verify_channel"] = channel.id

    await channel.send(
        "✅ **Verification**\n\n"
        "Click the button below to verify yourself.",
        view=VerifyView(role.id)
    )

    await interaction.response.send_message(
        f"✅ Verification setup in {channel.mention}."
    )


# =========================================================
# TICKETS
# =========================================================

@bot.tree.command(
    name="ticket",
    description="Create a support ticket"
)
async def ticket(
    interaction: discord.Interaction
):
    guild = interaction.guild

    category = discord.utils.get(
        guild.categories,
        name="🎫 Tickets"
    )

    if category is None:
        category = await guild.create_category(
            "🎫 Tickets"
        )

    channel = await guild.create_text_channel(
        f"ticket-{interaction.user.name}",
        category=category
    )

    await channel.set_permissions(
        interaction.user,
        read_messages=True,
        send_messages=True
    )

    await channel.send(
        f"🎫 Welcome {interaction.user.mention}!\n\n"
        "A staff member will help you soon.\n"
        "Use `/close` to close this ticket."
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
    if not interaction.channel.name.startswith(
        "ticket-"
    ):
        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔒 Closing ticket in 3 seconds..."
    )

    await asyncio.sleep(3)

    await interaction.channel.delete()
    # =========================================================
# BAN
# =========================================================

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
    reason: str = "No reason provided"
):
    await member.ban(reason=reason)

    await interaction.response.send_message(
        f"🔨 {member.mention} has been banned.\n"
        f"Reason: `{reason}`"
    )

    await send_log(
        interaction.guild,
        f"🔨 **Ban**\n"
        f"{member} was banned by "
        f"{interaction.user}.\n"
        f"Reason: {reason}"
    )


# =========================================================
# KICK
# =========================================================

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
    reason: str = "No reason provided"
):
    await member.kick(reason=reason)

    await interaction.response.send_message(
        f"👢 {member.mention} has been kicked.\n"
        f"Reason: `{reason}`"
    )

    await send_log(
        interaction.guild,
        f"👢 **Kick**\n"
        f"{member} was kicked by "
        f"{interaction.user}.\n"
        f"Reason: {reason}"
    )


# =========================================================
# TIMEOUT
# =========================================================

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
    minutes: int = 10
):
    await member.timeout(
        timedelta(minutes=minutes)
    )

    await interaction.response.send_message(
        f"⏱️ {member.mention} timed out "
        f"for `{minutes}` minutes."
    )

    await send_log(
        interaction.guild,
        f"⏱️ **Timeout**\n"
        f"{member} was timed out by "
        f"{interaction.user}."
    )


# =========================================================
# WARN
# =========================================================

@bot.tree.command(
    name="warn",
    description="Warn a member"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned.\n"
        f"Reason: `{reason}`"
    )

    await send_log(
        interaction.guild,
        f"⚠️ **Warning**\n"
        f"{member} was warned by "
        f"{interaction.user}.\n"
        f"Reason: {reason}"
    )


# =========================================================
# CLEAR
# =========================================================

@bot.tree.command(
    name="clear",
    description="Delete messages"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clear(
    interaction: discord.Interaction,
    amount: int
):
    if amount < 1:
        await interaction.response.send_message(
            "❌ Amount must be at least 1.",
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
        f"🧹 Deleted `{len(deleted)}` messages.",
        ephemeral=True
    )


# =========================================================
# AUTO ROLE
# =========================================================

@bot.tree.command(
    name="autorole",
    description="Set the automatic member role"
)
@app_commands.checks.has_permissions(
    manage_roles=True
)
async def autorole(
    interaction: discord.Interaction,
    role: discord.Role
):
    data = get_settings(interaction.guild.id)

    data["autorole"] = role.id

    await interaction.response.send_message(
        f"🎚️ Auto-role set to {role.mention}."
    )# =========================================================
# AI CHANNEL
# =========================================================

@bot.tree.command(
    name="setai",
    description="Set the AI chat channel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setai(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    data = get_settings(interaction.guild.id)

    data["ai_channel"] = channel.id

    await interaction.response.send_message(
        f"🤖 AI channel set to {channel.mention}."
    )


@bot.tree.command(
    name="ai",
    description="Chat with SECURITY"
)
async def ai(
    interaction: discord.Interaction,
    message: str
):
    data = get_settings(interaction.guild.id)

    if data["ai_channel"]:
        if interaction.channel.id != data["ai_channel"]:
            await interaction.response.send_message(
                "❌ AI chat is only available "
                "in the configured AI channel.",
                ephemeral=True
            )
            return

    text = message.lower()

    if "hello" in text or "hi" in text:
        response = (
            f"👋 Hello {interaction.user.mention}!"
        )

    elif "how are you" in text:
        response = (
            "🤖 I'm doing great! Thanks for asking."
        )

    elif "help" in text:
        response = (
            "🤖 Try asking me a question!"
        )

    else:
        response = (
            f"🤖 You said: **{message}**\n"
            "I'm your SECURITY bot assistant."
        )

    await interaction.response.send_message(
        response
    )


# =========================================================
# SAY
# =========================================================

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
        "📢 Message sent!",
        ephemeral=True
    )

    await interaction.channel.send(
        message
    )


# =========================================================
# LEVELING
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    guild_id = message.guild.id
    user_id = message.author.id

    if guild_id not in xp_data:
        xp_data[guild_id] = {}

    if user_id not in xp_data[guild_id]:
        xp_data[guild_id][user_id] = {
            "xp": 0,
            "level": 1
        }

    user = xp_data[guild_id][user_id]

    user["xp"] += random.randint(5, 15)

    needed = user["level"] * 100

    if user["xp"] >= needed:

        user["xp"] -= needed
        user["level"] += 1

        try:
            await message.channel.send(
                f"🎉 {message.author.mention} "
                f"leveled up to "
                f"**Level {user['level']}**!"
            )
        except:
            pass

    await bot.process_commands(message)


@bot.tree.command(
    name="level",
    description="Show your level and XP"
)
async def level(
    interaction: discord.Interaction
):
    user = xp_data.get(
        interaction.guild.id,
        {}
    ).get(
        interaction.user.id,
        {
            "xp": 0,
            "level": 1
        }
    )

    await interaction.response.send_message(
        f"📊 {interaction.user.mention}\n"
        f"Level: **{user['level']}**\n"
        f"XP: **{user['xp']}**"
    )


@bot.tree.command(
    name="rank",
    description="Show a member's rank"
)
async def rank(
    interaction: discord.Interaction,
    member: discord.Member = None
):
    member = member or interaction.user

    user = xp_data.get(
        interaction.guild.id,
        {}
    ).get(
        member.id,
        {
            "xp": 0,
            "level": 1
        }
    )

    await interaction.response.send_message(
        f"📊 **{member.display_name}'s Rank**\n"
        f"Level: **{user['level']}**\n"
        f"XP: **{user['xp']}**"
    )# =========================================================
# SERVER INFO
# =========================================================

@bot.tree.command(
    name="serverinfo",
    description="Show server information"
)
async def serverinfo(
    interaction: discord.Interaction
):
    guild = interaction.guild

    embed = discord.Embed(
        title=f"🔧 {guild.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Members",
        value=str(guild.member_count)
    )

    embed.add_field(
        name="📁 Channels",
        value=str(len(guild.channels))
    )

    embed.add_field(
        name="🎚️ Roles",
        value=str(len(guild.roles))
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# SETTINGS
# =========================================================

@bot.tree.command(
    name="settings",
    description="Show SECURITY settings"
)
async def settings_command(
    interaction: discord.Interaction
):
    data = get_settings(
        interaction.guild.id
    )

    def channel(value):
        if value:
            return f"<#{value}>"
        return "Not set"

    def role(value):
        if value:
            return f"<@&{value}>"
        return "Not set"

    embed = discord.Embed(
        title="⚙️ SECURITY Settings",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome",
        value=channel(
            data["welcome_channel"]
        ),
        inline=False
    )

    embed.add_field(
        name="👋 Goodbye",
        value=channel(
            data["goodbye_channel"]
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 AI",
        value=channel(
            data["ai_channel"]
        ),
        inline=False
    )

    embed.add_field(
        name="📜 Logs",
        value=channel(
            data["log_channel"]
        ),
        inline=False
    )

    embed.add_field(
        name="🎚️ Auto Role",
        value=role(
            data["autorole"]
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# GIVEAWAY
# =========================================================

@bot.tree.command(
    name="giveaway",
    description="Start a giveaway"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def giveaway(
    interaction: discord.Interaction,
    seconds: int,
    prize: str
):
    if seconds < 5:
        await interaction.response.send_message(
            "❌ Giveaway must last at least 5 seconds.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=(
            f"🎁 Prize: **{prize}**\n\n"
            "React with 🎉 to enter!\n"
            f"⏰ Ends in **{seconds} seconds**."
        ),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed
    )

    message = await interaction.original_response()

    await message.add_reaction("🎉")

    await asyncio.sleep(seconds)

    try:
        message = await interaction.channel.fetch_message(
            message.id
        )

        reaction = discord.utils.get(
            message.reactions,
            emoji="🎉"
        )

        users = []

        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)

        if not users:
            await interaction.channel.send(
                "🎉 Giveaway ended, but nobody entered."
            )
            return

        winner = random.choice(users)

        await interaction.channel.send(
            f"🎉 Congratulations {winner.mention}!\n"
            f"You won **{prize}**!"
        )

    except Exception as error:
        print(
            f"Giveaway error: {error}"
        )


# =========================================================
# SUGGESTIONS
# =========================================================

@bot.tree.command(
    name="suggest",
    description="Submit a suggestion"
)
async def suggest(
    interaction: discord.Interaction,
    suggestion: str
):
    embed = discord.Embed(
        title="📝 New Suggestion",
        description=suggestion,
        color=discord.Color.blurple()
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )

    message = await interaction.original_response()

    await message.add_reaction("✅")
    await message.add_reaction("❌")


# =========================================================
# LOGGING
# =========================================================

async def send_log(
    guild,
    message
):
    data = get_settings(
        guild.id
    )

    channel_id = data["log_channel"]

    if not channel_id:
        return

    channel = guild.get_channel(
        channel_id
    )

    if channel:
        try:
            await channel.send(message)
        except:
            pass


@bot.tree.command(
    name="setlog",
    description="Set the logging channel"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setlog(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    data = get_settings(
        interaction.guild.id
    )

    data["log_channel"] = channel.id

    await interaction.response.send_message(
        f"📜 Logging channel set to {channel.mention}."
)

# =========================================================
# HELP
# =========================================================

@bot.tree.command(
    name="help",
    description="Show all SECURITY commands"
)
async def help_command(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="🛡️ SECURITY Commands",
        description="All available slash commands:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome / Goodbye",
        value=(
            "`/setwelcome`\n"
            "`/setwelcomemessage`\n"
            "`/setgoodbye`\n"
            "`/setgoodbyemessage`"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ Verification",
        value="`/verifysetup`",
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets",
        value="`/ticket` • `/close`",
        inline=False
    )

    embed.add_field(
        name="🤖 AI / Chat",
        value="`/setai` • `/ai`",
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "`/ban`\n"
            "`/kick`\n"
            "`/timeout`\n"
            "`/warn`\n"
            "`/clear`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎚️ Auto Role",
        value="`/autorole`",
        inline=False
    )

    embed.add_field(
        name="📊 Leveling",
        value="`/level` • `/rank`",
        inline=False
    )

    embed.add_field(
        name="📢 Say",
        value="`/say`",
        inline=False
    )

    embed.add_field(
        name="🔧 Server",
        value="`/serverinfo` • `/settings`",
        inline=False
    )

    embed.add_field(
        name="🎉 Giveaway",
        value="`/giveaway`",
        inline=False
    )

    embed.add_field(
        name="📝 Suggestions",
        value="`/suggest`",
        inline=False
    )

    embed.add_field(
        name="📜 Logging",
        value="`/setlog`",
        inline=False
    )

    embed.add_field(
        name="🧹 Cleanup",
        value=(
            "`/deletechannels`\n"
            "`/deletecategories`\n"
            "`/wipe`"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# DELETE CHANNELS
# =========================================================

@bot.tree.command(
    name="deletechannels",
    description="Delete all server channels"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def deletechannels(
    interaction: discord.Interaction
):
    await interaction.response.send_message(
        "🧹 Deleting all channels..."
    )

    for channel in list(
        interaction.guild.channels
    ):
        try:
            await channel.delete()
        except:
            pass


# =========================================================
# DELETE CATEGORIES
# =========================================================

@bot.tree.command(
    name="deletecategories",
    description="Delete all server categories"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def deletecategories(
    interaction: discord.Interaction
):
    await interaction.response.send_message(
        "🧹 Deleting all categories..."
    )

    for category in list(
        interaction.guild.categories
    ):
        try:
            await category.delete()
        except:
            pass


# =========================================================
# WIPE
# =========================================================

@bot.tree.command(
    name="wipe",
    description="Delete channels and categories"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def wipe(
    interaction: discord.Interaction
):
    await interaction.response.send_message(
        "⚠️ **SERVER WIPE STARTING**\n"
        "Channels and categories will be deleted.\n"
        "Roles and the server itself will remain."
    )

    await asyncio.sleep(3)

    for channel in list(
        interaction.guild.channels
    ):
        try:
            await channel.delete()
        except:
            pass

    try:
        channel = await interaction.guild.create_text_channel(
            "security-wipe-complete"
        )

        await channel.send(
            "🧹 **Wipe complete!**\n"
            "Channels and categories were deleted.\n"
            "The server and roles were NOT deleted."
        )

    except Exception as error:
        print(
            f"Wipe error: {error}"
        )


# =========================================================
# SLASH COMMAND ERROR HANDLER
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        message = (
            "❌ You don't have permission "
            "to use this command."
        )

    elif isinstance(
        error,
        app_commands.errors.CommandOnCooldown
    ):
        message = (
            "⏳ This command is on cooldown."
        )

    else:
        print(
            f"Slash command error: {error}"
        )

        message = (
            "❌ Something went wrong "
            "while running the command."
        )

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


# =========================================================
# TOKEN
# =========================================================

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is not configured."
    )

bot.run(TOKEN)
