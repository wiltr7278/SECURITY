import os
import random
import asyncio
from datetime import timedelta

import discord
from discord.ext import commands

PREFIX = "!"

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
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
            "ticket_category": None,
        }

    return settings[guild_id]


@bot.event
async def on_ready():
    print(f"✅ SECURITY is online as {bot.user}")
    print(f"📊 Servers: {len(bot.guilds)}")

    await bot.change_presence(
        activity=discord.Game(
            name="!help | SECURITY"
        )
    )


@bot.event
async def on_member_join(member):
    data = get_settings(member.guild.id)

    # Auto role
    role_id = data["autorole"]

    if role_id:
        role = member.guild.get_role(role_id)

        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

    # Welcome
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


@bot.command()
@commands.has_permissions(manage_guild=True)
async def setwelcome(
    ctx,
    channel: discord.TextChannel
):
    data = get_settings(ctx.guild.id)

    data["welcome_channel"] = channel.id

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
    data = get_settings(ctx.guild.id)

    data["welcome_message"] = message

    await ctx.send(
        "✅ Welcome message updated."
    )


@bot.command()
@commands.has_permissions(manage_guild=True)
async def setgoodbye(
    ctx,
    channel: discord.TextChannel
):
    data = get_settings(ctx.guild.id)

    data["goodbye_channel"] = channel.id

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
    data = get_settings(ctx.guild.id)

    data["goodbye_message"] = message

    await ctx.send(
        "✅ Goodbye message updated."
    )# =========================================================
# VERIFICATION
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def verifysetup(
    ctx,
    role: discord.Role,
    channel: discord.TextChannel
):
    data = get_settings(ctx.guild.id)

    data["verify_role"] = role.id
    data["verify_channel"] = channel.id

    await channel.send(
        "✅ **Verification**\n\n"
        "Click the button below to verify yourself.",
        view=VerifyView(role.id)
    )

    await ctx.send(
        f"✅ Verification setup in {channel.mention}."
    )


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


# =========================================================
# TICKETS
# =========================================================

@bot.command()
async def ticket(ctx):

    guild = ctx.guild

    category = discord.utils.get(
        guild.categories,
        name="🎫 Tickets"
    )

    if category is None:
        category = await guild.create_category(
            "🎫 Tickets"
        )

    channel = await guild.create_text_channel(
        f"ticket-{ctx.author.name}",
        category=category
    )

    await channel.set_permissions(
        ctx.author,
        read_messages=True,
        send_messages=True
    )

    await channel.send(
        f"🎫 Welcome {ctx.author.mention}!\n\n"
        "A staff member will help you soon.\n"
        "Use `!close` to close this ticket."
    )

    await ctx.send(
        f"🎫 Ticket created: {channel.mention}"
    )


@bot.command()
async def close(ctx):

    if not ctx.channel.name.startswith(
        "ticket-"
    ):
        await ctx.send(
            "❌ This is not a ticket channel."
        )
        return

    await ctx.send(
        "🔒 Closing ticket in 3 seconds..."
    )

    await asyncio.sleep(3)

    await ctx.channel.delete()
    # =========================================================
# MODERATION
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
        f"🔨 {member.mention} has been banned.\n"
        f"Reason: `{reason}`"
    )

    await send_log(
        ctx.guild,
        f"🔨 **Ban**\n"
        f"{member} was banned by {ctx.author}.\n"
        f"Reason: {reason}"
    )


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
        f"👢 {member.mention} has been kicked.\n"
        f"Reason: `{reason}`"
    )

    await send_log(
        ctx.guild,
        f"👢 **Kick**\n"
        f"{member} was kicked by {ctx.author}.\n"
        f"Reason: {reason}"
    )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(
    ctx,
    member: discord.Member,
    minutes: int = 10
):
    await member.timeout(
        timedelta(minutes=minutes)
    )

    await ctx.send(
        f"⏱️ {member.mention} timed out "
        f"for `{minutes}` minutes."
    )

    await send_log(
        ctx.guild,
        f"⏱️ **Timeout**\n"
        f"{member} was timed out by {ctx.author}."
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):
    await ctx.send(
        f"⚠️ {member.mention} has been warned.\n"
        f"Reason: `{reason}`"
    )

    await send_log(
        ctx.guild,
        f"⚠️ **Warning**\n"
        f"{member} was warned by {ctx.author}.\n"
        f"Reason: {reason}"
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(
    ctx,
    amount: int = 10
):
    if amount < 1:
        await ctx.send(
            "❌ Amount must be at least 1."
        )
        return

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    message = await ctx.send(
        f"🧹 Deleted `{len(deleted) - 1}` messages."
    )

    await asyncio.sleep(3)

    try:
        await message.delete()
    except:
        pass


# =========================================================
# AUTO ROLE
# =========================================================

@bot.command()
@commands.has_permissions(manage_roles=True)
async def autorole(
    ctx,
    role: discord.Role
):
    data = get_settings(ctx.guild.id)

    data["autorole"] = role.id

    await ctx.send(
        f"🎚️ Auto-role set to {role.mention}."
    )# =========================================================
# AI / CHAT CHANNEL
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setai(
    ctx,
    channel: discord.TextChannel
):
    data = get_settings(ctx.guild.id)

    data["ai_channel"] = channel.id

    await ctx.send(
        f"🤖 AI channel set to {channel.mention}."
    )


@bot.command()
async def ai(
    ctx,
    *,
    message
):
    data = get_settings(ctx.guild.id)

    if data["ai_channel"]:
        if ctx.channel.id != data["ai_channel"]:
            await ctx.send(
                "❌ AI chat is only available "
                "in the configured AI channel."
            )
            return

    text = message.lower()

    if "hello" in text or "hi" in text:
        response = (
            f"👋 Hello {ctx.author.mention}!"
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
            "I'm your SECURITY bot chat assistant."
        )

    await ctx.send(response)


# =========================================================
# SAY
# =========================================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(
    ctx,
    *,
    message
):
    try:
        await ctx.message.delete()
    except:
        pass

    await ctx.send(message)


# =========================================================
# LEVELING / XP
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

    gained = random.randint(5, 15)

    user["xp"] += gained

    needed = user["level"] * 100

    if user["xp"] >= needed:

        user["xp"] -= needed
        user["level"] += 1

        await message.channel.send(
            f"🎉 {message.author.mention} "
            f"leveled up to "
            f"**Level {user['level']}**!"
        )

    await bot.process_commands(message)


@bot.command()
async def level(ctx):

    guild_id = ctx.guild.id
    user_id = ctx.author.id

    user = xp_data.get(
        guild_id,
        {}
    ).get(
        user_id,
        {
            "xp": 0,
            "level": 1
        }
    )

    await ctx.send(
        f"📊 {ctx.author.mention}\n"
        f"Level: **{user['level']}**\n"
        f"XP: **{user['xp']}**"
    )


@bot.command()
async def rank(
    ctx,
    member: discord.Member = None
):
    member = member or ctx.author

    user = xp_data.get(
        ctx.guild.id,
        {}
    ).get(
        member.id,
        {
            "xp": 0,
            "level": 1
        }
    )

    await ctx.send(
        f"📊 **{member.display_name}'s Rank**\n"
        f"Level: **{user['level']}**\n"
        f"XP: **{user['xp']}**"
    )# =========================================================
# SERVER SETUP
# =========================================================

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild

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

    await ctx.send(embed=embed)


@bot.command(name="settings")
async def settings_command(ctx):
    data = get_settings(ctx.guild.id)

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
        value=channel(data["welcome_channel"]),
        inline=False
    )

    embed.add_field(
        name="👋 Goodbye",
        value=channel(data["goodbye_channel"]),
        inline=False
    )

    embed.add_field(
        name="🤖 AI",
        value=channel(data["ai_channel"]),
        inline=False
    )

    embed.add_field(
        name="📜 Logs",
        value=channel(data["log_channel"]),
        inline=False
    )

    embed.add_field(
        name="🎚️ Auto Role",
        value=role(data["autorole"]),
        inline=False
    )

    await ctx.send(embed=embed)


# =========================================================
# GIVEAWAYS
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def giveaway(
    ctx,
    seconds: int,
    *,
    prize
):
    if seconds < 5:
        await ctx.send(
            "❌ Giveaway must last at least 5 seconds."
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

    message = await ctx.send(embed=embed)

    await message.add_reaction("🎉")

    await asyncio.sleep(seconds)

    try:
        message = await ctx.channel.fetch_message(
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
            await ctx.send(
                "🎉 Giveaway ended, but nobody entered."
            )
            return

        winner = random.choice(users)

        await ctx.send(
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

@bot.command()
async def suggest(
    ctx,
    *,
    suggestion
):
    embed = discord.Embed(
        title="📝 New Suggestion",
        description=suggestion,
        color=discord.Color.blurple()
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )

    message = await ctx.send(
        embed=embed
    )

    await message.add_reaction("✅")
    await message.add_reaction("❌")

    try:
        await ctx.message.delete()
    except:
        pass


# =========================================================
# LOGGING
# =========================================================

async def send_log(
    guild,
    message
):
    data = get_settings(guild.id)

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


@bot.command()
@commands.has_permissions(manage_guild=True)
async def setlog(
    ctx,
    channel: discord.TextChannel
):
    data = get_settings(ctx.guild.id)

    data["log_channel"] = channel.id

    await ctx.send(
        f"📜 Logging channel set to {channel.mention}."
    )# =========================================================
# HELP
# =========================================================

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="🛡️ SECURITY Commands",
        description="Use `!` before commands.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome / Goodbye",
        value=(
            "`!setwelcome #channel`\n"
            "`!setwelcomemessage <message>`\n"
            "`!setgoodbye #channel`\n"
            "`!setgoodbyemessage <message>`"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ Verification",
        value="`!verifysetup @role #channel`",
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets",
        value="`!ticket` • `!close`",
        inline=False
    )

    embed.add_field(
        name="🤖 AI / Chat",
        value="`!setai #channel` • `!ai <message>`",
        inline=False
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
        name="🎚️ Auto Role",
        value="`!autorole @role`",
        inline=False
    )

    embed.add_field(
        name="📊 Leveling",
        value="`!level` • `!rank @user`",
        inline=False
    )

    embed.add_field(
        name="📢 Say",
        value="`!say <message>`",
        inline=False
    )

    embed.add_field(
        name="🔧 Server",
        value="`!serverinfo` • `!settings`",
        inline=False
    )

    embed.add_field(
        name="🎉 Giveaway",
        value="`!giveaway <seconds> <prize>`",
        inline=False
    )

    embed.add_field(
        name="📝 Suggestions",
        value="`!suggest <suggestion>`",
        inline=False
    )

    embed.add_field(
        name="📜 Logging",
        value="`!setlog #channel`",
        inline=False
    )

    embed.add_field(
        name="🧹 Cleanup",
        value=(
            "`!deletechannels`\n"
            "`!deletecategories`\n"
            "`!wipe`"
        ),
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# CLEANUP
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def deletechannels(ctx):

    await ctx.send(
        "🧹 Deleting all channels..."
    )

    for channel in list(
        ctx.guild.channels
    ):
        try:
            await channel.delete()
        except:
            pass


@bot.command()
@commands.has_permissions(administrator=True)
async def deletecategories(ctx):

    await ctx.send(
        "🧹 Deleting all categories..."
    )

    for category in list(
        ctx.guild.categories
    ):
        try:
            await category.delete()
        except:
            pass


@bot.command()
@commands.has_permissions(administrator=True)
async def wipe(ctx):

    await ctx.send(
        "⚠️ **SERVER WIPE STARTING**\n"
        "All channels and categories will be deleted.\n"
        "Roles and the server itself will remain."
    )

    await asyncio.sleep(3)

    for channel in list(
        ctx.guild.channels
    ):
        try:
            await channel.delete()
        except:
            pass

    try:
        channel = await ctx.guild.create_text_channel(
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
# ERROR HANDLER
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

    elif isinstance(
        error,
        commands.ChannelNotFound
    ):
        await ctx.send(
            "❌ I couldn't find that channel."
        )

    elif isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    elif isinstance(
        error,
        commands.BadArgument
    ):
        await ctx.send(
            "❌ Invalid argument."
        )

    else:
        print(
            f"Command error: {error}"
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
