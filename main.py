import os
import asyncio
from datetime import timedelta

import discord
from discord.ext import commands


# =========================================================
# SECURITY BOT CONFIG
# =========================================================

PREFIX = "!"

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

# Temporary per-server settings
server_settings = {}

# Temporary XP storage
xp_data = {}


# =========================================================
# SERVER SETTINGS
# =========================================================

def get_settings(guild_id):

    if guild_id not in server_settings:
        server_settings[guild_id] = {
            "welcome_channel": None,
            "welcome_message": "Welcome {user} to {server}! 👋",

            "goodbye_channel": None,
            "goodbye_message": "{user} has left {server}. 👋",

            "autorole": None,

            "verify_role": None,

            "chat_channel": None,
        }

    return server_settings[guild_id]


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    print("================================")
    print(f"🤖 Logged in as: {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print("🛡️ SECURITY is online!")
    print("================================")

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game("!help | SECURITY")
    )


# =========================================================
# WELCOME
# =========================================================

@bot.event
async def on_member_join(member):

    settings = get_settings(member.guild.id)

    # -------------------------
    # AUTO ROLE
    # -------------------------

    role_id = settings["autorole"]

    if role_id:

        role = member.guild.get_role(role_id)

        if role:

            try:
                await member.add_roles(role)

            except discord.Forbidden:
                print(
                    f"❌ Cannot give role {role.name}"
                )

    # -------------------------
    # WELCOME MESSAGE
    # -------------------------

    channel_id = settings["welcome_channel"]

    if channel_id:

        channel = member.guild.get_channel(channel_id)

        if channel:

            message = settings["welcome_message"]

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


# =========================================================
# GOODBYE
# =========================================================

@bot.event
async def on_member_remove(member):

    settings = get_settings(member.guild.id)

    channel_id = settings["goodbye_channel"]

    if channel_id:

        channel = member.guild.get_channel(channel_id)

        if channel:

            message = settings["goodbye_message"]

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


# =========================================================
# HELP
# =========================================================

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="🛡️ SECURITY",
        description="Security & server management bot",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "`!ban @user`\n"
            "`!kick @user`\n"
            "`!timeout @user 10`\n"
            "`!warn @user reason`\n"
            "`!clear 10`"
        ),
        inline=False
    )

    embed.add_field(
        name="👋 Welcome",
        value=(
            "`!setwelcome #channel`\n"
            "`!setwelcomemessage message`"
        ),
        inline=False
    )

    embed.add_field(
        name="👋 Goodbye",
        value=(
            "`!setgoodbye #channel`\n"
            "`!setgoodbyemessage message`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎭 Auto Role",
        value="`!autorole @role`",
        inline=False
    )

    embed.add_field(
        name="📤 Send Message",
        value="`!send #channel message`",
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "`!ticket`\n"
            "`!close`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Cleanup",
        value=(
            "`!clear`\n"
            "`!deletechannels`\n"
            "`!deletecategories`\n"
            "`!wipe`"
        ),
        inline=False
    )

    embed.add_field(
        name="📈 Levels",
        value="`!level`",
        inline=False
    )

    embed.add_field(
        name="⚙️ Settings",
        value="`!settings`",
        inline=False
    )

    await ctx.send(embed=embed)


# =========================================================
# BAN
# =========================================================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    await member.ban(reason=reason)

    await ctx.send(
        f"🔨 {member.mention} was banned.\n"
        f"Reason: {reason}"
    )


# =========================================================
# KICK
# =========================================================

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    await member.kick(reason=reason)

    await ctx.send(
        f"👢 {member.mention} was kicked.\n"
        f"Reason: {reason}"
    )


# =========================================================
# TIMEOUT
# =========================================================

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(
    ctx,
    member: discord.Member,
    minutes: int = 10
):

    if minutes <= 0:
        await ctx.send("❌ Minutes must be greater than 0.")
        return

    if minutes > 40320:
        await ctx.send(
            "❌ Timeout cannot be longer than 28 days."
        )
        return

    duration = timedelta(minutes=minutes)

    await member.timeout(
        duration,
        reason=f"Timeout by {ctx.author}"
    )

    await ctx.send(
        f"⏱️ {member.mention} has been timed out "
        f"for **{minutes} minutes**."
    )


# =========================================================
# CLEAR MESSAGES
# =========================================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):

    if amount <= 0:
        await ctx.send("❌ Amount must be greater than 0.")
        return

    if amount > 100:
        amount = 100

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    message = await ctx.send(
        f"🧹 Deleted **{len(deleted) - 1}** messages."
    )

    await asyncio.sleep(3)

    try:
        await message.delete()
    except discord.HTTPException:
        pass


# =========================================================
# WELCOME SETUP
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setwelcome(
    ctx,
    channel: discord.TextChannel
):

    settings = get_settings(ctx.guild.id)

    settings["welcome_channel"] = channel.id

    await ctx.send(
        f"👋 Welcome channel set to {channel.mention}."
    )


@bot.command()
@commands.has_permissions(manage_guild=True)
async def setwelcomemessage(
    ctx,
    *,
    message
):

    settings = get_settings(ctx.guild.id)

    settings["welcome_message"] = message

    await ctx.send(
        "✅ Welcome message updated!"
    )


# =========================================================
# GOODBYE SETUP
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setgoodbye(
    ctx,
    channel: discord.TextChannel
):

    settings = get_settings(ctx.guild.id)

    settings["goodbye_channel"] = channel.id

    await ctx.send(
        f"👋 Goodbye channel set to {channel.mention}."
    )


@bot.command()
@commands.has_permissions(manage_guild=True)
async def setgoodbyemessage(
    ctx,
    *,
    message
):

    settings = get_settings(ctx.guild.id)

    settings["goodbye_message"] = message

    await ctx.send(
        "✅ Goodbye message updated!"
    )


# =========================================================
# AUTO ROLE
# =========================================================

@bot.command()
@commands.has_permissions(manage_roles=True)
async def autorole(
    ctx,
    role: discord.Role
):

    settings = get_settings(ctx.guild.id)

    settings["autorole"] = role.id

    await ctx.send(
        f"🎭 Auto role set to {role.mention}."
    )


# =========================================================
# SEND CUSTOM MESSAGE
# =========================================================
# Separate from welcome and goodbye.

@bot.command()
@commands.has_permissions(manage_messages=True)
async def send(
    ctx,
    channel: discord.TextChannel,
    *,
    message
):

    message = message.replace(
        "{server}",
        ctx.guild.name
    )

    message = message.replace(
        "{username}",
        ctx.author.name
    )

    await channel.send(message)

    await ctx.send(
        f"📤 Message sent to {channel.mention}."
    )


# =========================================================
# DELETE CHANNELS
# =========================================================

@bot.command()
@commands.has_permissions(manage_channels=True)
async def deletechannels(ctx):

    await ctx.send(
        "⚠️ **DELETE CHANNELS**\n\n"
        "This will delete the server's channels.\n"
        "Type `CONFIRM` within 15 seconds."
    )

    def check(message):

        return (
            message.author == ctx.author
            and message.channel == ctx.channel
            and message.content.upper() == "CONFIRM"
        )

    try:

        await bot.wait_for(
            "message",
            timeout=15,
            check=check
        )

    except asyncio.TimeoutError:

        await ctx.send("❌ Cancelled.")
        return

    for channel in list(ctx.guild.channels):

        try:
            await channel.delete(
                reason=f"Channel cleanup by {ctx.author}"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


# =========================================================
# DELETE CATEGORIES
# =========================================================

@bot.command()
@commands.has_permissions(manage_channels=True)
async def deletecategories(ctx):

    await ctx.send(
        "⚠️ **DELETE CATEGORIES**\n\n"
        "Type `CONFIRM` within 15 seconds."
    )

    def check(message):

        return (
            message.author == ctx.author
            and message.channel == ctx.channel
            and message.content.upper() == "CONFIRM"
        )

    try:

        await bot.wait_for(
            "message",
            timeout=15,
            check=check
        )

    except asyncio.TimeoutError:

        await ctx.send("❌ Cancelled.")
        return

    for category in list(ctx.guild.categories):

        try:
            await category.delete(
                reason=f"Category cleanup by {ctx.author}"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


# =========================================================
# WIPE SERVER
# =========================================================
#
# IMPORTANT:
#
# ❌ Does NOT delete the Discord server.
# ❌ Does NOT delete roles.
#
# ✅ Deletes channels.
# ✅ Deletes categories.
#
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def wipe(ctx):

    await ctx.send(
        "🚨 **WIPE SERVER** 🚨\n\n"
        "This will delete:\n"
        "🗑️ ALL CHANNELS\n"
        "🗑️ ALL CATEGORIES\n\n"
        "✅ ROLES WILL BE KEPT\n"
        "✅ THE DISCORD SERVER WILL BE KEPT\n\n"
        "Type `WIPE CONFIRM` within 15 seconds."
    )

    def check(message):

        return (
            message.author == ctx.author
            and message.channel == ctx.channel
            and message.content.upper() == "WIPE CONFIRM"
        )

    try:

        await bot.wait_for(
            "message",
            timeout=15,
            check=check
        )

    except asyncio.TimeoutError:

        await ctx.send("❌ Wipe cancelled.")
        return

    channels = list(ctx.guild.channels)

    for channel in channels:

        try:

            await channel.delete(
                reason=f"SECURITY wipe by {ctx.author}"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


# =========================================================
# TICKET
# =========================================================

@bot.command()
@commands.has_permissions(manage_channels=True)
async def ticket(ctx):

    guild = ctx.guild

    ticket_name = (
        f"ticket-{ctx.author.name.lower()}"
    )

    existing = discord.utils.get(
        guild.text_channels,
        name=ticket_name
    )

    if existing:

        await ctx.send(
            f"🎫 You already have {existing.mention}."
        )

        return

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        ctx.author:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True
            )
    }

    channel = await guild.create_text_channel(
        ticket_name,
        overwrites=overwrites
    )

    await channel.send(
        f"🎫 Welcome {ctx.author.mention}!\n\n"
        "A staff member will help you soon.\n"
        "Use `!close` to close this ticket."
    )


# =========================================================
# CLOSE TICKET
# =========================================================

@bot.command()
async def close(ctx):

    if not ctx.channel.name.startswith("ticket-"):

        await ctx.send(
            "❌ This isn't a ticket channel."
        )

        return

    await ctx.send(
        "🔒 Closing ticket..."
    )

    await asyncio.sleep(2)

    await ctx.channel.delete()


# =========================================================
# XP / LEVEL SYSTEM
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # -------------------------
    # XP
    # -------------------------

    if message.guild:

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

        user["xp"] += 5

        required_xp = user["level"] * 100

        if user["xp"] >= required_xp:

            user["xp"] -= required_xp
            user["level"] += 1

            await message.channel.send(
                f"🎉 {message.author.mention} reached "
                f"**Level {user['level']}!**"
            )

    # -------------------------
    # BOT CHAT
    # -------------------------

    if message.guild:

        settings = get_settings(
            message.guild.id
        )

        chat_channel = settings["chat_channel"]

        if chat_channel == message.channel.id:

            await message.channel.send(
                f"🤖 You said: **{message.content}**"
            )

    await bot.process_commands(message)


# =========================================================
# LEVEL COMMAND
# =========================================================

@bot.command()
async def level(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    guild_data = xp_data.get(
        ctx.guild.id,
        {}
    )

    user = guild_data.get(
        member.id,
        {
            "xp": 0,
            "level": 1
        }
    )

    await ctx.send(
        f"📈 **{member.display_name}**\n"
        f"Level: **{user['level']}**\n"
        f"XP: **{user['xp']}**"
    )


# =========================================================
# BOT CHAT CHANNEL
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setchat(
    ctx,
    channel: discord.TextChannel
):

    settings = get_settings(ctx.guild.id)

    settings["chat_channel"] = channel.id

    await ctx.send(
        f"💬 Bot chat enabled in {channel.mention}."
    )


# =========================================================
# SETTINGS
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def settings(ctx):

    data = get_settings(ctx.guild.id)

    welcome = (
        f"<#{data['welcome_channel']}>"
        if data["welcome_channel"]
        else "Not set"
    )

    goodbye = (
        f"<#{data['goodbye_channel']}>"
        if data["goodbye_channel"]
        else "Not set"
    )

    autorole = (
        f"<@&{data['autorole']}>"
        if data["autorole"]
        else "Not set"
    )

    chat = (
        f"<#{data['chat_channel']}>"
        if data["chat_channel"]
        else "Not set"
    )

    embed = discord.Embed(
        title="⚙️ SECURITY Settings",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome",
        value=welcome,
        inline=False
    )

    embed.add_field(
        name="👋 Goodbye",
        value=goodbye,
        inline=False
    )

    embed.add_field(
        name="🎭 Auto Role",
        value=autorole,
        inline=False
    )

    embed.add_field(
        name="💬 Bot Chat",
        value=chat,
        inline=False
    )

    await ctx.send(embed=embed)


# =========================================================
# ERROR HANDLING
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.send(
            "❌ You don't have permission "
            "to use that command."
        )
    elif isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "❌ You're missing a required argument."
        )

    elif isinstance(
        error,
        commands.MemberNotFound
    ):

        await ctx.send(
            "❌ I couldn't find that member."
        )

    elif isinstance(
        error,
        commands.RoleNotFound
    ):

        await ctx.send(
            "❌ I couldn't find that role."

        )
