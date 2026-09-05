PART 1 — CORE BOT

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Add your bot token as DISCORD_TOKEN."
    )

CONFIG_FILE = "config.json"
LEVEL_FILE = "levels.json"


def load_data(filename):
    if not os.path.exists(filename):
        return {}

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


config = load_data(CONFIG_FILE)
levels = load_data(LEVEL_FILE)


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True


class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced.")


bot = SecurityBot()


def get_guild_config(guild_id):
    guild_id = str(guild_id)

    if guild_id not in config:
        config[guild_id] = {}

    return config[guild_id]


@bot.event
async def on_ready():
    print("--------------------------------")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("SECURITY is ONLINE!")
    print("--------------------------------")
PART 2 — WELCOME SYSTEM ONLY 👋

# ==============================
# WELCOME SYSTEM
# ==============================

@bot.tree.command(
    name="welcome",
    description="Set the welcome channel."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    data = get_guild_config(interaction.guild.id)

    data["welcome_channel"] = channel.id
    save_data(CONFIG_FILE, config)

    await interaction.response.send_message(
        f"✅ Welcome messages will now be sent in {channel.mention}.",
        ephemeral=True
    )


@bot.event
async def on_member_join(member: discord.Member):
    data = get_guild_config(member.guild.id)

    channel_id = data.get("welcome_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(int(channel_id))

    if channel is None:
        return

    embed = discord.Embed(
        title=f"👋 Welcome to {member.guild.name}!",
        description=(
            f"Hey {member.mention}! 🎉\n\n"
            f"Welcome to **{member.guild.name}**!\n\n"
            "📖 Read the rules\n"
            "✅ Verify yourself\n"
            "💬 Enjoy the community!"
        ),
        color=discord.Color.blurple()
    )

    # PERSON'S DISCORD AVATAR
    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="👤 Member",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="📊 Member Count",
        value=str(member.guild.member_count),
        inline=True
    )

    embed.set_footer(
        text=f"Welcome, {member.name}!"
    )

    try:
        await channel.send(
            content=f"👋 Welcome {member.mention}!",
            embed=embed
        )
    except discord.Forbidden:
        print("Welcome error: I cannot send messages in the welcome channel.")
    except discord.HTTPException as error:
        print(f"Welcome Discord error: {error}")
PART 3 — BYE SYSTEM ONLY 👋

# ==============================
# BYE SYSTEM
# ==============================

@bot.tree.command(
    name="bye",
    description="Set the goodbye channel."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    data = get_guild_config(interaction.guild.id)

    data["bye_channel"] = channel.id
    save_data(CONFIG_FILE, config)

    await interaction.response.send_message(
        f"✅ Goodbye messages will now be sent in {channel.mention}.",
        ephemeral=True
    )


@bot.event
async def on_member_remove(member: discord.Member):
    data = get_guild_config(member.guild.id)

    channel_id = data.get("bye_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(int(channel_id))

    if channel is None:
        return

    embed = discord.Embed(
        title="👋 Goodbye!",
        description=(
            f"**{member.name}** has left **{member.guild.name}**.\n\n"
            "We hope to see you again! ❤️"
        ),
        color=discord.Color.red()
    )

    # PERSON'S AVATAR
    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="📊 Members Remaining",
        value=str(member.guild.member_count),
        inline=True
    )

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        print("Bye error: I cannot send messages in the goodbye channel.")
    except discord.HTTPException as error:
        print(f"Bye Discord error: {error}")
PART 4 — VERIFICATION ONLY ✅

# ==============================
# VERIFICATION SYSTEM
# ==============================

@bot.tree.command(
    name="verifysetup",
    description="Set the verification role."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verifysetup(
    interaction: discord.Interaction,
    role: discord.Role
):
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

    bot_member = interaction.guild.me

    if bot_member is None:
        await interaction.response.send_message(
            "❌ I couldn't find my bot member.",
            ephemeral=True
        )
        return

    if role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ Move my bot role ABOVE the verification role.",
            ephemeral=True
        )
        return

    data = get_guild_config(interaction.guild.id)

    data["verify_role"] = role.id
    save_data(CONFIG_FILE, config)

    await interaction.response.send_message(
        f"✅ Verification role set to {role.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify",
    description="Verify yourself."
)
async def verify(interaction: discord.Interaction):
    data = get_guild_config(interaction.guild.id)

    role_id = data.get("verify_role")

    if not role_id:
        await interaction.response.send_message(
            "❌ Verification has not been configured.\n"
            "An administrator must use `/verifysetup` first.",
            ephemeral=True
        )
        return

    role = interaction.guild.get_role(int(role_id))

    if role is None:
        await interaction.response.send_message(
            "❌ The verification role no longer exists.\n"
            "An administrator must run `/verifysetup` again.",
            ephemeral=True
        )
        return

    if role in interaction.user.roles:
        await interaction.response.send_message(
            "✅ You are already verified!",
            ephemeral=True
        )
        return

    bot_member = interaction.guild.me

    if bot_member is None or role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ I cannot give you this role.\n"
            "Move my bot role above the verification role.",
            ephemeral=True
        )
        return

    try:
        await interaction.user.add_roles(
            role,
            reason="Security bot verification"
        )

        await interaction.response.send_message(
            "✅ **Verified successfully!**\n"
            "You can now access the server.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Discord denied the role change.\n"
            "Check my Manage Roles permission and role position.",
            ephemeral=True
        )

    except discord.HTTPException as error:
        print(f"Verification error: {error}")

        await interaction.response.send_message(
            "❌ Discord returned an error while verifying you.",
            ephemeral=True
        )
PART 5 — MODERATION + ROLES

# ==============================
# MODERATION
# ==============================

@bot.tree.command(
    name="clear",
    description="Delete messages."
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
            "❌ I don't have permission to delete messages.",
            ephemeral=True
        )


@bot.tree.command(
    name="kick",
    description="Kick a member."
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot kick yourself.",
            ephemeral=True
        )
        return

    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "❌ You cannot kick an equal or higher role.",
            ephemeral=True
        )
        return

    try:
        await member.kick(reason=reason)

        await interaction.response.send_message(
            f"👢 **{member}** was kicked.\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot kick that member.",
            ephemeral=True
        )


@bot.tree.command(
    name="ban",
    description="Ban a member."
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot ban yourself.",
            ephemeral=True
        )
        return

    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "❌ You cannot ban an equal or higher role.",
            ephemeral=True
        )
        return

    try:
        await member.ban(reason=reason)

        await interaction.response.send_message(
            f"🔨 **{member}** was banned.\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot ban that member.",
            ephemeral=True
        )


# ==============================
# ROLE COMMANDS
# ==============================

@bot.tree.command(
    name="addrole",
    description="Give a role to a member."
)
@app_commands.checks.has_permissions(manage_roles=True)
async def addrole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    bot_member = interaction.guild.me

    if bot_member is None or role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ My bot role must be above that role.",
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


@bot.tree.command(
    name="removerole",
    description="Remove a role from a member."
)
@app_commands.checks.has_permissions(manage_roles=True)
async def removerole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    bot_member = interaction.guild.me

    if bot_member is None or role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ My bot role must be above that role.",
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


@bot.tree.command(
    name="say",
    description="Make the bot send a message."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def say(
    interaction: discord.Interaction,
    message: str
):
    await interaction.response.send_message(
        "✅ Message sent.",
        ephemeral=True
    )

    try:
        await interaction.channel.send(message)
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I cannot send messages here.",
            ephemeral=True
        )
PART 6 — LEVELING + HELP + ERRORS

# ==============================
# LEVELING
# ==============================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.guild is not None:
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        if guild_id not in levels:
            levels[guild_id] = {}

        if user_id not in levels[guild_id]:
            levels[guild_id][user_id] = {
                "xp": 0,
                "level": 1
            }

        user = levels[guild_id][user_id]

        user["xp"] += random.randint(5, 15)

        required_xp = user["level"] * 100

        if user["xp"] >= required_xp:
            user["xp"] -= required_xp
            user["level"] += 1

            try:
                await message.channel.send(
                    f"🎉 {message.author.mention} reached "
                    f"**Level {user['level']}**!"
                )
            except discord.HTTPException:
                pass

        save_data(LEVEL_FILE, levels)

    await bot.process_commands(message)


@bot.tree.command(
    name="level",
    description="Check your level."
)
async def level(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)

    user = levels.get(guild_id, {}).get(
        user_id,
        {
            "xp": 0,
            "level": 1
        }
    )

    embed = discord.Embed(
        title="⭐ Your Level",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="👤 User",
        value=interaction.user.mention,
        inline=False
    )

    embed.add_field(
        name="🏆 Level",
        value=str(user["level"]),
        inline=True
    )

    embed.add_field(
        name="✨ XP",
        value=str(user["xp"]),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ==============================
# SERVER INFO
# ==============================

@bot.tree.command(
    name="serverinfo",
    description="Show server information."
)
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color.blurple()
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

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

    await interaction.response.send_message(
        embed=embed
    )


# ==============================
# HELP
# ==============================

@bot.tree.command(
    name="help",
    description="Show all bot commands."
)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ SECURITY — HELP",
        description="Available commands:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome",
        value="`/welcome`",
        inline=True
    )

    embed.add_field(
        name="👋 Goodbye",
        value="`/bye`",
        inline=True
    )

    embed.add_field(
        name="✅ Verification",
        value="`/verifysetup`\n`/verify`",
        inline=True
    )

    embed.add_field(
        name="🛡️ Moderation",
        value="`/clear`\n`/kick`\n`/ban`",
        inline=True
    )

    embed.add_field(
        name="🎭 Roles",
        value="`/addrole`\n`/removerole`",
        inline=True
    )

    embed.add_field(
        name="⭐ Other",
        value="`/level`\n`/say`\n`/serverinfo`\n`/help`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ==============================
# ERROR HANDLER
# ==============================

@bot.tree.error
async def command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        message = (
            "❌ You don't have permission "
            "to use this command."
        )

    else:
        print(f"Command error: {error}")
        message = (
            "❌ Something went wrong while "
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


# ==============================
# START BOT
# ==============================

bot.run(TOKEN)        
