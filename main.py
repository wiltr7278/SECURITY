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


# =========================================================
# BASIC CONFIG
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG_FILE = "config.json"

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Add DISCORD_TOKEN in Railway Variables."
    )


# =========================================================
# CONFIG SYSTEM
# =========================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except (json.JSONDecodeError, OSError):
        pass

    return {}


config = load_config()


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)
    except OSError as error:
        print(f"Config save error: {error}")


def get_guild_config(guild_id):
    guild_id = str(guild_id)

    if guild_id not in config:
        config[guild_id] = {}

    return config[guild_id]


# =========================================================
# MESSAGE FORMAT
# =========================================================

def format_message(text, member):
    return (
        text
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace("{count}", str(member.guild.member_count or 0))
    )


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# =========================================================
# BOT CLASS
# =========================================================

class SecurityBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        # Persistent buttons
        self.add_view(TicketCreateView())
        self.add_view(TicketCloseView())
        self.add_view(ShowcaseView())

        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands.")
        except Exception as error:
            print(f"Slash command sync error: {error}")


bot = SecurityBot()


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():
    print("================================")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")
    print("SECURITY is online.")
    print("================================")


# =========================================================
# EMBED HELPER
# =========================================================

async def send_embed(
    interaction,
    title,
    description,
    ephemeral=False
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple()
    )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                embed=embed,
                ephemeral=ephemeral
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                ephemeral=ephemeral
            )
    except discord.HTTPException:
        pass
# =========================================================
# WELCOME / BYE HELPERS
# =========================================================

def make_member_embed(
    member,
    title,
    message,
    image_url=None,
    style="avatar"
):
    embed = discord.Embed(
        title=title,
        description=format_message(message, member),
        color=discord.Color.blurple()
    )

    avatar_url = member.display_avatar.url

    # Avatar in thumbnail
    if style in ("avatar", "both"):
        embed.set_thumbnail(url=avatar_url)

    # Large image
    if style == "avatar":
        embed.set_image(url=avatar_url)

    elif style in ("custom", "both") and image_url:
        embed.set_image(url=image_url)

    elif style == "custom":
        embed.set_image(url=avatar_url)

    embed.set_footer(
        text=f"{member.guild.name} • SECURITY"
    )

    return embed


# =========================================================
# WELCOME
# =========================================================

@bot.event
async def on_member_join(member):

    settings = get_guild_config(member.guild.id)

    channel_id = settings.get("welcome_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)

    if not isinstance(channel, discord.TextChannel):
        return

    message = settings.get(
        "welcome_message",
        "Welcome {user} to **{server}**! 🎉"
    )

    image_url = settings.get("welcome_image")
    style = settings.get("welcome_style", "avatar")

    embed = make_member_embed(
        member,
        "👋 Welcome!",
        message,
        image_url,
        style
    )

    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


@bot.tree.command(
    name="welcome",
    description="Set the welcome channel."
)
@app_commands.describe(
    channel="Channel for welcome messages."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(interaction.guild.id)

    settings["welcome_channel"] = channel.id

    save_config()

    await send_embed(
        interaction,
        "✅ Welcome Channel",
        f"Welcome messages will be sent in {channel.mention}.",
        True
    )


@bot.tree.command(
    name="welcome-message",
    description="Customize the welcome message."
)
@app_commands.describe(
    message="Your welcome message."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_message(
    interaction: discord.Interaction,
    message: str
):
    settings = get_guild_config(interaction.guild.id)

    settings["welcome_message"] = message

    save_config()

    await send_embed(
        interaction,
        "✅ Welcome Message Updated",
        (
            f"{message}\n\n"
            "**Placeholders:**\n"
            "`{user}` ` {username}` `{server}` `{count}`"
        ),
        True
    )


@bot.tree.command(
    name="welcome-image",
    description="Set a custom welcome image."
)
@app_commands.describe(
    image="Upload your welcome image."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):
    if not image.content_type or not image.content_type.startswith("image/"):
        await send_embed(
            interaction,
            "❌ Invalid Image",
            "Please upload an image file.",
            True
        )
        return

    settings = get_guild_config(interaction.guild.id)

    settings["welcome_image"] = image.url

    save_config()

    await send_embed(
        interaction,
        "🖼️ Welcome Image Saved",
        "Your custom welcome image has been saved.",
        True
    )


@bot.tree.command(
    name="welcome-style",
    description="Choose the welcome image/avatar style."
)
@app_commands.describe(
    style="Choose how the welcome image looks."
)
@app_commands.choices(
    style=[
        app_commands.Choice(name="Member Avatar", value="avatar"),
        app_commands.Choice(name="Custom Image", value="custom"),
        app_commands.Choice(name="Custom Image + Avatar", value="both")
    ]
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):
    settings = get_guild_config(interaction.guild.id)

    settings["welcome_style"] = style.value

    save_config()

    await send_embed(
        interaction,
        "✅ Welcome Style Updated",
        f"Welcome style: **{style.name}**",
        True
    )


@bot.tree.command(
    name="testwelcome",
    description="Test the welcome message."
)
async def testwelcome(
    interaction: discord.Interaction
):
    settings = get_guild_config(interaction.guild.id)

    message = settings.get(
        "welcome_message",
        "Welcome {user} to **{server}**! 🎉"
    )

    image_url = settings.get("welcome_image")
    style = settings.get("welcome_style", "avatar")

    embed = make_member_embed(
        interaction.user,
        "👋 Welcome Test",
        message,
        image_url,
        style
    )

    await interaction.response.send_message(embed=embed)


# =========================================================
# BYE
# =========================================================

@bot.event
async def on_member_remove(member):

    settings = get_guild_config(member.guild.id)

    channel_id = settings.get("bye_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)

    if not isinstance(channel, discord.TextChannel):
        return

    message = settings.get(
        "bye_message",
        "Goodbye **{username}**! 👋"
    )

    image_url = settings.get("bye_image")
    style = settings.get("bye_style", "avatar")

    embed = make_member_embed(
        member,
        "🚪 Goodbye!",
        message,
        image_url,
        style
    )

    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


@bot.tree.command(
    name="bye",
    description="Set the goodbye channel."
)
@app_commands.describe(
    channel="Channel for goodbye messages."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(interaction.guild.id)

    settings["bye_channel"] = channel.id

    save_config()

    await send_embed(
        interaction,
        "✅ Bye Channel",
        f"Goodbye messages will be sent in {channel.mention}.",
        True
    )


@bot.tree.command(
    name="bye-message",
    description="Customize the goodbye message."
)
@app_commands.describe(
    message="Your goodbye message."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_message(
    interaction: discord.Interaction,
    message: str
):
    settings = get_guild_config(interaction.guild.id)

    settings["bye_message"] = message

    save_config()

    await send_embed(
        interaction,
        "✅ Bye Message Updated",
        (
            f"{message}\n\n"
            "**Placeholders:**\n"
            "`{user}` `{username}` `{server}` `{count}`"
        ),
        True
    )


@bot.tree.command(
    name="bye-image",
    description="Set a custom goodbye image."
)
@app_commands.describe(
    image="Upload your goodbye image."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):
    if not image.content_type or not image.content_type.startswith("image/"):
        await send_embed(
            interaction,
            "❌ Invalid Image",
            "Please upload an image file.",
            True
        )
        return

    settings = get_guild_config(interaction.guild.id)

    settings["bye_image"] = image.url

    save_config()

    await send_embed(
        interaction,
        "🖼️ Bye Image Saved",
        "Your custom goodbye image has been saved.",
        True
    )


@bot.tree.command(
    name="bye-style",
    description="Choose the goodbye image/avatar style."
)
@app_commands.describe(
    style="Choose how the goodbye image looks."
)
@app_commands.choices(
    style=[
        app_commands.Choice(name="Member Avatar", value="avatar"),
        app_commands.Choice(name="Custom Image", value="custom"),
        app_commands.Choice(name="Custom Image + Avatar", value="both")
    ]
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):
    settings = get_guild_config(interaction.guild.id)

    settings["bye_style"] = style.value

    save_config()

    await send_embed(
        interaction,
        "✅ Bye Style Updated",
        f"Goodbye style: **{style.name}**",
        True
    )


@bot.tree.command(
    name="testbye",
    description="Test the goodbye message."
)
async def testbye(
    interaction: discord.Interaction
):
    settings = get_guild_config(interaction.guild.id)

    message = settings.get(
        "bye_message",
        "Goodbye **{username}**! 👋"
    )

    image_url = settings.get("bye_image")
    style = settings.get("bye_style", "avatar")

    embed = make_member_embed(
        interaction.user,
        "🚪 Goodbye Test",
        message,
        image_url,
        style
    )

    await interaction.response.send_message(embed=embed)
# =========================================================
# VERIFY SYSTEM
# =========================================================

@bot.tree.command(
    name="verifysetup",
    description="Set the verification role."
)
@app_commands.describe(
    role="Role members receive when verified."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verifysetup(
    interaction: discord.Interaction,
    role: discord.Role
):
    guild = interaction.guild

    if role.is_default():
        await send_embed(
            interaction,
            "❌ Invalid Role",
            "You cannot use the @everyone role.",
            True
        )
        return

    if role.managed:
        await send_embed(
            interaction,
            "❌ Invalid Role",
            "You cannot use a managed/integration role.",
            True
        )
        return

    if guild.me and role >= guild.me.top_role:
        await send_embed(
            interaction,
            "❌ Role Hierarchy",
            "My highest role must be above the verification role.",
            True
        )
        return

    settings = get_guild_config(guild.id)

    settings["verify_role"] = role.id

    save_config()

    await send_embed(
        interaction,
        "✅ Verification Setup",
        f"Verified members receive {role.mention}.",
        True
    )


@bot.tree.command(
    name="verify-message",
    description="Customize the verification message."
)
@app_commands.describe(
    message="Text shown when someone uses verify."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verify_message(
    interaction: discord.Interaction,
    message: str
):
    settings = get_guild_config(interaction.guild.id)

    settings["verify_message"] = message

    save_config()

    await send_embed(
        interaction,
        "✅ Verify Message Updated",
        message,
        True
    )


@bot.tree.command(
    name="verify",
    description="Verify yourself."
)
async def verify(
    interaction: discord.Interaction
):
    guild = interaction.guild

    settings = get_guild_config(guild.id)

    role_id = settings.get("verify_role")

    if not role_id:
        await send_embed(
            interaction,
            "❌ Verification Not Setup",
            "An administrator needs to run `/verifysetup` first.",
            True
        )
        return

    role = guild.get_role(role_id)

    if role is None:
        await send_embed(
            interaction,
            "❌ Role Missing",
            "The configured verification role no longer exists.",
            True
        )
        return

    if role.is_default() or role.managed:
        await send_embed(
            interaction,
            "❌ Invalid Verification Role",
            "The configured role cannot be used.",
            True
        )
        return

    if guild.me and role >= guild.me.top_role:
        await send_embed(
            interaction,
            "❌ Role Hierarchy",
            "My bot role must be above the verification role.",
            True
        )
        return

    if role in interaction.user.roles:
        await send_embed(
            interaction,
            "✅ Already Verified",
            "You are already verified.",
            True
        )
        return

    try:
        await interaction.user.add_roles(
            role,
            reason="SECURITY verification"
        )

        message = settings.get(
            "verify_message",
            "You have been successfully verified! ✅"
        )

        await send_embed(
            interaction,
            "✅ Verified",
            format_message(message, interaction.user),
            True
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot give that role. Check my role hierarchy and Manage Roles permission.",
            True
        )

    except discord.HTTPException:
        await send_embed(
            interaction,
            "❌ Discord Error",
            "Discord rejected the role change.",
            True
        )
# =========================================================
# MODERATION
# =========================================================

@bot.tree.command(
    name="clear",
    description="Delete messages."
)
@app_commands.describe(
    amount="Number of messages to delete."
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
            "❌ I need Manage Messages permission.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord rejected the cleanup.",
            ephemeral=True
        )


@bot.tree.command(
    name="kick",
    description="Kick a member."
)
@app_commands.describe(
    member="Member to kick.",
    reason="Reason for the kick."
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    if member == interaction.user:
        await send_embed(
            interaction,
            "❌ Error",
            "You cannot kick yourself.",
            True
        )
        return

    if interaction.guild.me and member >= interaction.guild.me:
        await send_embed(
            interaction,
            "❌ Role Hierarchy",
            "My role must be above that member.",
            True
        )
        return

    try:
        await member.kick(reason=reason)

        await send_embed(
            interaction,
            "👢 Member Kicked",
            f"{member.mention} was kicked.\n**Reason:** {reason}"
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot kick that member.",
            True
        )


@bot.tree.command(
    name="ban",
    description="Ban a member."
)
@app_commands.describe(
    member="Member to ban.",
    reason="Reason for the ban."
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    if member == interaction.user:
        await send_embed(
            interaction,
            "❌ Error",
            "You cannot ban yourself.",
            True
        )
        return

    if interaction.guild.me and member >= interaction.guild.me:
        await send_embed(
            interaction,
            "❌ Role Hierarchy",
            "My role must be above that member.",
            True
        )
        return

    try:
        await member.ban(
            reason=reason,
            delete_message_seconds=0
        )

        await send_embed(
            interaction,
            "🔨 Member Banned",
            f"{member.mention} was banned.\n**Reason:** {reason}"
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot ban that member.",
            True
        )


@bot.tree.command(
    name="timeout",
    description="Timeout a member."
)
@app_commands.describe(
    member="Member to timeout.",
    minutes="Timeout duration in minutes."
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320]
):
    if member == interaction.user:
        await send_embed(
            interaction,
            "❌ Error",
            "You cannot timeout yourself.",
            True
        )
        return

    if interaction.guild.me and member >= interaction.guild.me:
        await send_embed(
            interaction,
            "❌ Role Hierarchy",
            "My role must be above that member.",
            True
        )
        return

    until = discord.utils.utcnow() + timedelta(
        minutes=minutes
    )

    try:
        await member.edit(
            timed_out_until=until,
            reason=f"Timeout by {interaction.user}"
        )

        await send_embed(
            interaction,
            "⏱️ Member Timed Out",
            f"{member.mention} was timed out for **{minutes} minutes**."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot timeout that member.",
            True
        )


@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout."
)
@app_commands.describe(
    member="Member to untimeout."
)
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member
):
    try:
        await member.edit(
            timed_out_until=None,
            reason=f"Timeout removed by {interaction.user}"
        )

        await send_embed(
            interaction,
            "✅ Timeout Removed",
            f"{member.mention} is no longer timed out."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot remove that timeout.",
            True
        )


@bot.tree.command(
    name="addrole",
    description="Give a role to a member."
)
@app_commands.describe(
    member="Member.",
    role="Role to give."
)
@app_commands.checks.has_permissions(manage_roles=True)
async def addrole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    if role.is_default() or role.managed:
        await send_embed(
            interaction,
            "❌ Invalid Role",
            "That role cannot be assigned.",
            True
        )
        return

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        await send_embed(
            interaction,
            "❌ Role Hierarchy",
            "My role must be above the role I'm assigning.",
            True
        )
        return

    try:
        await member.add_roles(role)

        await send_embed(
            interaction,
            "✅ Role Added",
            f"{role.mention} was added to {member.mention}."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot give that role.",
            True
        )


@bot.tree.command(
    name="removerole",
    description="Remove a role from a member."
)
@app_commands.describe(
    member="Member.",
    role="Role to remove."
)
@app_commands.checks.has_permissions(manage_roles=True)
async def removerole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    if role.is_default() or role.managed:
        await send_embed(
            interaction,
            "❌ Invalid Role",
            "That role cannot be removed.",
            True
        )
        return

    if interaction.guild.me and role >= interaction.guild.me.top_role:
        await send_embed(
            interaction,
            "❌ Role Hierarchy",
            "My role must be above the role I'm modifying.",
            True
        )
        return

    try:
        await member.remove_roles(role)

        await send_embed(
            interaction,
            "✅ Role Removed",
            f"{role.mention} was removed from {member.mention}."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot remove that role.",
            True
        )
# =========================================================
# CLEANER
# =========================================================

async def delete_messages_matching(
    channel,
    amount,
    check_function
):
    deleted = 0

    try:
        async for message in channel.history(
            limit=amount
        ):
            if check_function(message):
                try:
                    await message.delete()
                    deleted += 1
                except discord.HTTPException:
                    pass

    except discord.HTTPException:
        pass

    return deleted


@bot.tree.command(
    name="clearuser",
    description="Delete messages from a user."
)
@app_commands.describe(
    member="User whose messages should be deleted.",
    amount="Number of messages to check."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearuser(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    deleted = await delete_messages_matching(
        interaction.channel,
        amount,
        lambda m: m.author.id == member.id
    )

    await interaction.followup.send(
        f"🧹 Deleted **{deleted}** messages from {member.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearbots",
    description="Delete bot messages."
)
@app_commands.describe(
    amount="Number of messages to check."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearbots(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    deleted = await delete_messages_matching(
        interaction.channel,
        amount,
        lambda m: m.author.bot
    )

    await interaction.followup.send(
        f"🤖 Deleted **{deleted}** bot messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearlinks",
    description="Delete messages containing links."
)
@app_commands.describe(
    amount="Number of messages to check."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearlinks(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    url_pattern = re.compile(
        r"https?://\S+",
        re.IGNORECASE
    )

    deleted = await delete_messages_matching(
        interaction.channel,
        amount,
        lambda m: bool(url_pattern.search(m.content))
    )

    await interaction.followup.send(
        f"🔗 Deleted **{deleted}** messages containing links.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearinvites",
    description="Delete Discord invite links."
)
@app_commands.describe(
    amount="Number of messages to check."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearinvites(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(ephemeral=True)

    invite_pattern = re.compile(
        r"(discord\.gg/|discord\.com/invite/)",
        re.IGNORECASE
    )

    deleted = await delete_messages_matching(
        interaction.channel,
        amount,
        lambda m: bool(invite_pattern.search(m.content))
    )

    await interaction.followup.send(
        f"📨 Deleted **{deleted}** invite messages.",
        ephemeral=True
    )


@bot.tree.command(
    name="clearchannel",
    description="Delete and recreate the current channel."
)
@app_commands.checks.has_permissions(manage_channels=True)
async def clearchannel(
    interaction: discord.Interaction
):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "This command only works in text channels.",
            True
        )
        return

    try:
        new_channel = await channel.clone(
            reason=f"Channel cleared by {interaction.user}"
        )

        await channel.delete(
            reason=f"Channel cleared by {interaction.user}"
        )

        await new_channel.send(
            f"🧹 Channel cleared by {interaction.user.mention}."
        )

    except discord.Forbidden:
        if not interaction.response.is_done():
            await send_embed(
                interaction,
                "❌ Permission Error",
                "I need Manage Channels permission.",
                True
            )


@bot.tree.command(
    name="slowmode",
    description="Set channel slowmode."
)
@app_commands.describe(
    seconds="Slowmode from 0 to 21600 seconds."
)
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(
    interaction: discord.Interaction,
    seconds: app_commands.Range[int, 0, 21600]
):
    try:
        await interaction.channel.edit(
            slowmode_delay=seconds
        )

        await send_embed(
            interaction,
            "🐌 Slowmode Updated",
            f"Slowmode is now **{seconds} seconds**."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I need Manage Channels permission.",
            True
        )


@bot.tree.command(
    name="lock",
    description="Lock the current channel."
)
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(
    interaction: discord.Interaction
):
    channel = interaction.channel

    overwrite = channel.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = False

    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await send_embed(
            interaction,
            "🔒 Channel Locked",
            "Members can no longer send messages."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot change this channel.",
            True
        )


@bot.tree.command(
    name="unlock",
    description="Unlock the current channel."
)
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(
    interaction: discord.Interaction
):
    channel = interaction.channel

    overwrite = channel.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = None

    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await send_embed(
            interaction,
            "🔓 Channel Unlocked",
            "Members can send messages again."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot change this channel.",
            True
        )


# =========================================================
# WIPE CONFIRMATION
# =========================================================

class WipeView(discord.ui.View):

    def __init__(self, author_id):
        super().__init__(timeout=30)
        self.author_id = author_id

    @discord.ui.button(
        label="Confirm Wipe",
        emoji="💥",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Only the person who started the wipe can confirm it.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Administrator permission required.",
                ephemeral=True
            )
            return

        if guild.me is None:
            await interaction.response.send_message(
                "❌ I cannot find my server member.",
                ephemeral=True
            )
            return

        if not guild.me.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ I need Manage Channels permission.",
                ephemeral=True
            )
            return

        if not guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ I need Manage Roles permission.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="💥 **Wiping channels and removable roles...**",
            view=None
        )

        # Delete channels
        for channel in list(guild.channels):
            try:
                await channel.delete(
                    reason=f"Server wipe by {interaction.user}"
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

        # Delete removable roles
        for role in list(guild.roles):
            if role.is_default():
                continue

            if role.managed:
                continue

            if role >= guild.me.top_role:
                continue

            try:
                await role.delete(
                    reason=f"Server wipe by {interaction.user}"
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

    @discord.ui.button(
        label="Cancel",
        emoji="❌",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Only the person who started the wipe can cancel it.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Server wipe cancelled.",
            view=None
        )


@bot.tree.command(
    name="wipe",
    description="Wipe channels and removable roles."
)
@app_commands.checks.has_permissions(administrator=True)
async def wipe(
    interaction: discord.Interaction
):
    guild = interaction.guild

    if guild.me is None:
        await send_embed(
            interaction,
            "❌ Error",
            "I cannot find my server member.",
            True
        )
        return

    if not guild.me.guild_permissions.manage_channels:
        await send_embed(
            interaction,
            "❌ Missing Permission",
            "I need **Manage Channels**.",
            True
        )
        return

    if not guild.me.guild_permissions.manage_roles:
        await send_embed(
            interaction,
            "❌ Missing Permission",
            "I need **Manage Roles**.",
            True
        )
        return

    view = WipeView(interaction.user.id)

    await interaction.response.send_message(
        "⚠️ **SERVER WIPE WARNING**\n\n"
        "This will delete the server's channels/categories and removable roles.\n\n"
        "**The Discord server itself will NOT be deleted.**\n\n"
        "Press **Confirm Wipe** to continue.",
        view=view,
        ephemeral=True
    )
# =========================================================
# TICKET HELPERS
# =========================================================

def find_user_ticket(guild, user_id):
    topic_text = f"ticket_owner:{user_id}"

    for channel in guild.text_channels:
        if channel.topic == topic_text:
            return channel

    return None


# =========================================================
# CLOSE TICKET VIEW
# =========================================================

class TicketCloseView(discord.ui.View):

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
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )
            return

        if not channel.topic or not channel.topic.startswith(
            "ticket_owner:"
        ):
            await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )
            return

        owner_id_text = channel.topic.split(
            "ticket_owner:",
            1
        )[1]

        try:
            owner_id = int(owner_id_text)
        except ValueError:
            owner_id = None

        allowed = (
            interaction.user.id == owner_id
            or interaction.user.guild_permissions.administrator
            or interaction.user.guild_permissions.manage_channels
        )

        if not allowed:
            await interaction.response.send_message(
                "❌ You cannot close this ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Ticket closing in **5 seconds**..."
        )

        await asyncio.sleep(5)

        try:
            await channel.delete(
                reason=f"Ticket closed by {interaction.user}"
            )
        except (discord.Forbidden, discord.HTTPException):
            pass


# =========================================================
# CREATE TICKET VIEW
# =========================================================

class TicketCreateView(discord.ui.View):

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
        member = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "❌ This only works inside a server.",
                ephemeral=True
            )
            return

        existing = find_user_ticket(
            guild,
            member.id
        )

        if existing:
            await interaction.response.send_message(
                f"🎫 You already have a ticket: {existing.mention}",
                ephemeral=True
            )
            return

        settings = get_guild_config(guild.id)

        category_id = settings.get("ticket_category")
        staff_role_id = settings.get("ticket_staff_role")

        category = None

        if category_id:
            found = guild.get_channel(category_id)

            if isinstance(found, discord.CategoryChannel):
                category = found

        if category is None:
            await interaction.response.send_message(
                "❌ Tickets have not been configured correctly. "
                "An administrator should use `/ticket setup`.",
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
                attach_files=True,
                embed_links=True
            )
        }

        # Staff role
        if staff_role_id:
            staff_role = guild.get_role(
                staff_role_id
            )

            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )

        # Bot permissions
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )

        try:
            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{member.id}",
                category=category,
                topic=f"ticket_owner:{member.id}",
                overwrites=overwrites,
                reason=f"Ticket created by {member}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I cannot create tickets. Give me **Manage Channels**.",
                ephemeral=True
            )
            return

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Discord rejected the ticket creation.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Welcome {member.mention}!\n\n"
                "Please explain what you need help with.\n\n"
                "A staff member will help you soon.\n\n"
                "When finished, click **🔒 Close Ticket**."
            ),
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.set_footer(
            text=f"Opened by {member}"
        )

        try:
            await ticket_channel.send(
                content=member.mention,
                embed=embed,
                view=TicketCloseView()
            )

            await interaction.response.send_message(
                f"✅ Ticket created: {ticket_channel.mention}",
                ephemeral=True
            )

        except discord.HTTPException:
            try:
                await ticket_channel.delete(
                    reason="Ticket message failed"
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

            await interaction.response.send_message(
                "❌ The ticket could not be completed.",
                ephemeral=True
            )


# =========================================================
# TICKET COMMAND GROUP
# =========================================================

ticket_group = app_commands.Group(
    name="ticket",
    description="Ticket system commands."
)


@ticket_group.command(
    name="setup",
    description="Set up the ticket category and staff role."
)
@app_commands.describe(
    category="Category where tickets will be created.",
    staff_role="Optional staff role."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_setup(
    interaction: discord.Interaction,
    category: discord.CategoryChannel,
    staff_role: Optional[discord.Role] = None
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["ticket_category"] = category.id

    if staff_role:
        if staff_role.is_default() or staff_role.managed:
            await send_embed(
                interaction,
                "❌ Invalid Staff Role",
                "Choose a normal server role.",
                True
            )
            return

        settings["ticket_staff_role"] = staff_role.id
    else:
        settings.pop(
            "ticket_staff_role",
            None
        )

    save_config()

    staff_text = (
        staff_role.mention
        if staff_role
        else "No staff role"
    )

    await send_embed(
        interaction,
        "🎫 Ticket Setup Complete",
        (
            f"**Category:** {category.mention}\n"
            f"**Staff:** {staff_text}\n\n"
            "Now use `/ticket panel`."
        ),
        True
    )


@ticket_group.command(
    name="panel",
    description="Send the ticket panel."
)
@app_commands.describe(
    channel="Channel where the panel should be sent."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(
        interaction.guild.id
    )

    category_id = settings.get(
        "ticket_category"
    )

    category = interaction.guild.get_channel(
        category_id
    ) if category_id else None

    if not isinstance(
        category,
        discord.CategoryChannel
    ):
        await send_embed(
            interaction,
            "❌ Tickets Not Setup",
            "Use `/ticket setup` first.",
            True
        )
        return

    embed = discord.Embed(
        title="🎫 Support Center",
        description=(
            "Need help?\n\n"
            "Click **Create Ticket** below.\n\n"
            "Your ticket will be private and visible "
            "only to you, the bot, and the configured staff team."
        ),
        color=discord.Color.blurple()
    )

    try:
        await channel.send(
            embed=embed,
            view=TicketCreateView()
        )

        await send_embed(
            interaction,
            "✅ Ticket Panel Sent",
            f"Panel sent to {channel.mention}.",
            True
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot send messages in that channel.",
            True
        )


@ticket_group.command(
    name="close",
    description="Close the current ticket."
)
async def ticket_close(
    interaction: discord.Interaction
):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "This is not a ticket channel.",
            True
        )
        return

    if not channel.topic or not channel.topic.startswith(
        "ticket_owner:"
    ):
        await send_embed(
            interaction,
            "❌ Error",
            "This is not a ticket channel.",
            True
        )
        return

    owner_id_text = channel.topic.split(
        "ticket_owner:",
        1
    )[1]

    try:
        owner_id = int(owner_id_text)
    except ValueError:
        owner_id = None

    allowed = (
        interaction.user.id == owner_id
        or interaction.user.guild_permissions.administrator
        or interaction.user.guild_permissions.manage_channels
    )

    if not allowed:
        await send_embed(
            interaction,
            "❌ Not Allowed",
            "You cannot close this ticket.",
            True
        )
        return

    await interaction.response.send_message(
        "🔒 Ticket closing in **5 seconds**..."
    )

    await asyncio.sleep(5)

    try:
        await channel.delete(
            reason=f"Ticket closed by {interaction.user}"
        )
    except (discord.Forbidden, discord.HTTPException):
        pass


bot.tree.add_command(ticket_group)
# =========================================================
# LEVEL SYSTEM
# =========================================================

XP_COOLDOWN = {}


def get_level_data(guild_id, user_id):
    settings = get_guild_config(guild_id)

    levels = settings.setdefault(
        "levels",
        {}
    )

    user_id = str(user_id)

    if user_id not in levels:
        levels[user_id] = {
            "xp": 0,
            "level": 0
        }

    return levels[user_id]


def xp_needed(level):
    return 100 + (level * 50)


def add_xp(guild_id, user_id, amount):
    data = get_level_data(
        guild_id,
        user_id
    )

    data["xp"] += amount

    leveled_up = False

    while data["xp"] >= xp_needed(data["level"]):
        data["xp"] -= xp_needed(data["level"])
        data["level"] += 1
        leveled_up = True

    return data, leveled_up


def level_message(
    text,
    member,
    level
):
    return (
        text
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace("{level}", str(level))
    )


# =========================================================
# LEVEL MESSAGE LISTENER
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    # Ignore empty messages
    if not message.content.strip():
        return

    settings = get_guild_config(
        message.guild.id
    )

    if settings.get(
        "levels_enabled",
        True
    ):
        key = (
            message.guild.id,
            message.author.id
        )

        now = asyncio.get_running_loop().time()
        last = XP_COOLDOWN.get(key, 0)

        # 60-second XP cooldown
        if now - last >= 60:
            XP_COOLDOWN[key] = now

            amount = random.randint(15, 25)

            data, leveled_up = add_xp(
                message.guild.id,
                message.author.id,
                amount
            )

            save_config()

            if leveled_up:
                channel_id = settings.get(
                    "level_channel"
                )

                channel = (
                    message.guild.get_channel(channel_id)
                    if channel_id
                    else message.channel
                )

                if isinstance(
                    channel,
                    discord.TextChannel
                ):
                    text = settings.get(
                        "level_message",
                        "🎉 Congratulations {user}! "
                        "You reached **Level {level}**!"
                    )

                    embed = discord.Embed(
                        title="⭐ Level Up!",
                        description=level_message(
                            text,
                            message.author,
                            data["level"]
                        ),
                        color=discord.Color.gold()
                    )

                    embed.set_thumbnail(
                        url=message.author.display_avatar.url
                    )

                    try:
                        await channel.send(
                            embed=embed
                        )
                    except discord.HTTPException:
                        pass


# =========================================================
# RANK
# =========================================================

@bot.tree.command(
    name="rank",
    description="View your level and XP."
)
async def rank(
    interaction: discord.Interaction
):
    data = get_level_data(
        interaction.guild.id,
        interaction.user.id
    )

    needed = xp_needed(
        data["level"]
    )

    embed = discord.Embed(
        title="⭐ Your Rank",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="Level",
        value=f"**{data['level']}**",
        inline=True
    )

    embed.add_field(
        name="XP",
        value=f"**{data['xp']} / {needed}**",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# LEVEL
# =========================================================

@bot.tree.command(
    name="level",
    description="View another member's level."
)
@app_commands.describe(
    member="Member to check."
)
async def level(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user

    data = get_level_data(
        interaction.guild.id,
        member.id
    )

    needed = xp_needed(
        data["level"]
    )

    embed = discord.Embed(
        title="⭐ Member Level",
        description=member.mention,
        color=discord.Color.gold()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Level",
        value=f"**{data['level']}**",
        inline=True
    )

    embed.add_field(
        name="XP",
        value=f"**{data['xp']} / {needed}**",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# LEADERBOARD
# =========================================================

@bot.tree.command(
    name="leaderboard",
    description="Show the server XP leaderboard."
)
async def leaderboard(
    interaction: discord.Interaction
):
    settings = get_guild_config(
        interaction.guild.id
    )

    levels = settings.get(
        "levels",
        {}
    )

    ranking = []

    for user_id, data in levels.items():

        try:
            uid = int(user_id)
        except ValueError:
            continue

        member = interaction.guild.get_member(uid)

        if member:
            ranking.append(
                (
                    data.get("level", 0),
                    data.get("xp", 0),
                    member
                )
            )

    ranking.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )

    ranking = ranking[:10]

    if not ranking:
        await send_embed(
            interaction,
            "⭐ Leaderboard",
            "Nobody has earned XP yet."
        )
        return

    lines = []

    for index, (lvl, xp, member) in enumerate(
        ranking,
        start=1
    ):
        lines.append(
            f"**{index}.** {member.mention} — "
            f"Level **{lvl}** • {xp} XP"
        )

    await send_embed(
        interaction,
        "🏆 XP Leaderboard",
        "\n".join(lines)
    )


# =========================================================
# LEVEL SETTINGS
# =========================================================

@bot.tree.command(
    name="setlevelchannel",
    description="Set the level-up channel."
)
@app_commands.describe(
    channel="Channel for level-up messages."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setlevelchannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["level_channel"] = channel.id

    save_config()

    await send_embed(
        interaction,
        "✅ Level Channel",
        f"Level-ups will be announced in {channel.mention}.",
        True
    )


@bot.tree.command(
    name="setlevelmessage",
    description="Customize the level-up message."
)
@app_commands.describe(
    message="Use {user}, {username}, {server}, {level}."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setlevelmessage(
    interaction: discord.Interaction,
    message: str
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["level_message"] = message

    save_config()

    await send_embed(
        interaction,
        "✅ Level Message Updated",
        (
            f"{message}\n\n"
            "**Placeholders:** "
            "`{user}` `{username}` `{server}` `{level}`"
        ),
        True
    )


@bot.tree.command(
    name="togglelevels",
    description="Turn the XP system on or off."
)
@app_commands.describe(
    enabled="Enable or disable XP."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def togglelevels(
    interaction: discord.Interaction,
    enabled: bool
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["levels_enabled"] = enabled

    save_config()

    await send_embed(
        interaction,
        "⭐ Levels Updated",
        f"Levels are now **{'ON' if enabled else 'OFF'}**.",
        True
    )


@bot.tree.command(
    name="setlevel",
    description="Set a member's level."
)
@app_commands.describe(
    member="Member.",
    amount="New level."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setlevel(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 0, 100000]
):
    data = get_level_data(
        interaction.guild.id,
        member.id
    )

    data["level"] = amount
    data["xp"] = 0

    save_config()

    await send_embed(
        interaction,
        "⭐ Level Set",
        f"{member.mention} is now **Level {amount}**.",
        True
    )


@bot.tree.command(
    name="setxp",
    description="Set a member's XP."
)
@app_commands.describe(
    member="Member.",
    amount="New XP."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setxp(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 0, 1000000000]
):
    data = get_level_data(
        interaction.guild.id,
        member.id
    )

    data["xp"] = amount

    save_config()

    await send_embed(
        interaction,
        "⭐ XP Set",
        f"{member.mention} now has **{amount} XP**.",
        True
    )


@bot.tree.command(
    name="resetxp",
    description="Reset a member's XP and level."
)
@app_commands.describe(
    member="Member to reset."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def resetxp(
    interaction: discord.Interaction,
    member: discord.Member
):
    data = get_level_data(
        interaction.guild.id,
        member.id
    )

    data["xp"] = 0
    data["level"] = 0

    save_config()

    await send_embed(
        interaction,
        "♻️ XP Reset",
        f"{member.mention}'s XP and level were reset.",
        True
)
# =========================================================
# 🎬 TIKTOK SHOWCASE
# =========================================================

def is_tiktok_url(url):
    url = url.strip().lower()

    return (
        url.startswith("https://www.tiktok.com/")
        or url.startswith("https://tiktok.com/")
        or url.startswith("https://vm.tiktok.com/")
        or url.startswith("http://www.tiktok.com/")
        or url.startswith("http://tiktok.com/")
        or url.startswith("http://vm.tiktok.com/")
    )


class TikTokModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Submit TikTok"
        )

        self.link = discord.ui.TextInput(
            label="TikTok Video Link",
            placeholder="Example: https://vm.tiktok.com/*******",
            required=True,
            max_length=500
        )

        self.add_item(self.link)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        url = self.link.value.strip()

        if not is_tiktok_url(url):
            await interaction.response.send_message(
                "❌ That is not a valid TikTok link.\n\n"
                "Please paste a link like:\n"
                "`https://vm.tiktok.com/*******`",
                ephemeral=True
            )
            return

        settings = get_guild_config(
            interaction.guild.id
        )

        if not settings.get(
            "showcase_enabled",
            False
        ):
            await interaction.response.send_message(
                "❌ The TikTok showcase is currently disabled.",
                ephemeral=True
            )
            return

        channel_id = settings.get(
            "showcase_channel"
        )

        channel = (
            interaction.guild.get_channel(channel_id)
            if channel_id
            else None
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ The showcase channel is not configured.",
                ephemeral=True
            )
            return

        custom_text = settings.get(
            "showcase_message",
            "🎬 **New TikTok Submitted!**\n\n"
            "Thanks for sharing your video!"
        )

        embed = discord.Embed(
            title="🎬 TikTok Showcase",
            description=(
                f"{custom_text}\n\n"
                f"👤 **Creator:** {interaction.user.mention}\n"
                f"🔗 **TikTok:** [Watch Video]({url})"
            ),
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text=f"Submitted by {interaction.user}"
        )

        try:
            await channel.send(
                embed=embed
            )

            await interaction.response.send_message(
                f"✅ Your TikTok was submitted to {channel.mention}!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I cannot send messages in the showcase channel.",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Discord rejected the submission.",
                ephemeral=True
            )


class ShowcaseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Submit TikTok",
        emoji="🔗",
        style=discord.ButtonStyle.primary,
        custom_id="security_showcase_submit"
    )
    async def submit_tiktok(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        settings = get_guild_config(
            interaction.guild.id
        )

        if not settings.get(
            "showcase_enabled",
            False
        ):
            await interaction.response.send_message(
                "❌ The showcase is currently disabled.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            TikTokModal()
        )


# =========================================================
# SHOWCASE COMMAND GROUP
# =========================================================

showcase_group = app_commands.Group(
    name="showcase",
    description="TikTok edit/video showcase commands."
)


@showcase_group.command(
    name="setup",
    description="Set the TikTok showcase channel."
)
@app_commands.describe(
    channel="Channel where TikToks will be posted."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["showcase_channel"] = channel.id

    save_config()

    await send_embed(
        interaction,
        "🎬 Showcase Channel Set",
        f"TikTok submissions will be posted in {channel.mention}.",
        True
    )


@showcase_group.command(
    name="on",
    description="Turn the TikTok showcase on."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_on(
    interaction: discord.Interaction
):
    settings = get_guild_config(
        interaction.guild.id
    )

    if not settings.get("showcase_channel"):
        await send_embed(
            interaction,
            "❌ Setup Required",
            "Use `/showcase setup` first.",
            True
        )
        return

    settings["showcase_enabled"] = True

    save_config()

    await send_embed(
        interaction,
        "✅ Showcase Enabled",
        "Members can now submit TikTok videos.",
        True
    )


@showcase_group.command(
    name="off",
    description="Turn the TikTok showcase off."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_off(
    interaction: discord.Interaction
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["showcase_enabled"] = False

    save_config()

    await send_embed(
        interaction,
        "⛔ Showcase Disabled",
        "TikTok submissions are now disabled.",
        True
    )


@showcase_group.command(
    name="message",
    description="Customize the TikTok showcase text."
)
@app_commands.describe(
    text="Text shown with submitted TikToks."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_message(
    interaction: discord.Interaction,
    text: str
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["showcase_message"] = text

    save_config()

    await send_embed(
        interaction,
        "✅ Showcase Message Updated",
        text,
        True
    )


@showcase_group.command(
    name="panel",
    description="Send the TikTok submission panel."
)
@app_commands.describe(
    channel="Channel where the panel should be sent."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def showcase_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(
        interaction.guild.id
    )

    if not settings.get(
        "showcase_channel"
    ):
        await send_embed(
            interaction,
            "❌ Setup Required",
            "Use `/showcase setup` first.",
            True
        )
        return

    custom_text = settings.get(
        "showcase_message",
        "🎬 **SHOW YOUR EDITS!**\n"
        "Share your best TikTok with the community!"
    )

    embed = discord.Embed(
        title="🎬 TikTok Showcase",
        description=(
            f"{custom_text}\n\n"
            "**How to submit:**\n"
            "Click the button below and paste your TikTok link.\n\n"
            "**Example:**\n"
            "`https://vm.tiktok.com/*******`"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="TikTok Showcase • SECURITY"
    )

    try:
        await channel.send(
            embed=embed,
            view=ShowcaseView()
        )

        await send_embed(
            interaction,
            "✅ Showcase Panel Sent",
            f"Panel sent to {channel.mention}.",
            True
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot send messages in that channel.",
            True
        )


bot.tree.add_command(showcase_group)


# =========================================================
# 🛠️ UTILITY COMMANDS
# =========================================================

@bot.tree.command(
    name="ping",
    description="Check bot latency."
)
async def ping(
    interaction: discord.Interaction
):
    latency = round(
        bot.latency * 1000
    )

    await send_embed(
        interaction,
        "🏓 Pong!",
        f"Latency: **{latency}ms**"
    )


@bot.tree.command(
    name="serverinfo",
    description="Show server information."
)
async def serverinfo(
    interaction: discord.Interaction
):
    guild = interaction.guild

    embed = discord.Embed(
        title="🛡️ Server Information",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Name",
        value=guild.name,
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
    description="Show information about a member."
)
@app_commands.describe(
    member="Member to inspect."
)
async def userinfo(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user

    embed = discord.Embed(
        title="👤 User Information",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Username",
        value=member.name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Joined Server",
        value=(
            discord.utils.format_dt(
                member.joined_at,
                style="F"
            )
            if member.joined_at
            else "Unknown"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="avatar",
    description="Show a member's avatar."
)
@app_commands.describe(
    member="Member."
)
async def avatar(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user

    embed = discord.Embed(
        title=f"👤 {member.name}'s Avatar",
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="servericon",
    description="Show the server icon."
)
async def servericon(
    interaction: discord.Interaction
):
    if not interaction.guild.icon:
        await send_embed(
            interaction,
            "❌ No Server Icon",
            "This server doesn't have an icon."
        )
        return

    embed = discord.Embed(
        title=f"🖼️ {interaction.guild.name}",
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=interaction.guild.icon.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="botinfo",
    description="Show bot information."
)
async def botinfo(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="🛡️ SECURITY",
        description=(
            "Discord security, moderation and community bot."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Servers",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="Users",
        value=str(
            len(bot.users)
        ),
        inline=True
    )

    embed.add_field(
        name="Latency",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )

    if bot.user:
        embed.set_thumbnail(
            url=bot.user.display_avatar.url
        )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="say",
    description="Make the bot say something."
)
@app_commands.describe(
    message="Message to send."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def say(
    interaction: discord.Interaction,
    message: str
):
    await interaction.response.send_message(
        "✅ Sent.",
        ephemeral=True
    )

    try:
        await interaction.channel.send(
            message
        )
    except discord.HTTPException:
        pass


@bot.tree.command(
    name="announce",
    description="Send an announcement embed."
)
@app_commands.describe(
    title="Announcement title.",
    message="Announcement message."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def announce(
    interaction: discord.Interaction,
    title: str,
    message: str
):
    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"Announcement by {interaction.user}"
    )

    await interaction.response.send_message(
        "✅ Announcement sent.",
        ephemeral=True
    )

    try:
        await interaction.channel.send(
            embed=embed
        )
    except discord.HTTPException:
        pass


# =========================================================
# 📚 HELP
# =========================================================

@bot.tree.command(
    name="help",
    description="Show all SECURITY commands."
)
async def help_command(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="🛡️ SECURITY — Commands",
        description=(
            "Here are all available SECURITY commands.\n"
            "Use `/` and select the command you need."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome / Bye",
        value=(
            "`/welcome`\n"
            "`/welcome-message`\n"
            "`/welcome-image`\n"
            "`/welcome-style`\n"
            "`/testwelcome`\n"
            "`/bye`\n"
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
            "`/verify`"
        ),
        inline=True
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
            "`/removerole`"
        ),
        inline=True
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
            "`/unlock`\n"
            "`/wipe`"
        ),
        inline=True
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "`/ticket setup`\n"
            "`/ticket panel`\n"
            "`/ticket close`"
        ),
        inline=True
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
        inline=True
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
        inline=True
    )

    embed.add_field(
        name="🛠️ Utility",
        value=(
            "`/ping`\n"
            "`/serverinfo`\n"
            "`/userinfo`\n"
            "`/avatar`\n"
            "`/servericon`\n"
            "`/botinfo`\n"
            "`/say`\n"
            "`/announce`"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# GLOBAL COMMAND ERROR HANDLER
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
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
        app_commands.errors.CommandOnCooldown
    ):
        message = "⏳ This command is on cooldown."

    elif isinstance(
        error,
        app_commands.errors.CheckFailure
    ):
        message = "❌ You don't have permission to use this command."

    else:
        print(
            f"Command error: {type(error).__name__}: {error}"
        )

        message = (
            "❌ Something went wrong while running that command."
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


# =========================================================
# START BOT
# =========================================================

bot.run(TOKEN)    
