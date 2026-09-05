import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import asyncio
from typing import Optional

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing from Railway Variables.")

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
        print(f"Could not save config: {e}")


def guild_config(guild_id: int):
    gid = str(guild_id)

    if gid not in config:
        config[gid] = {}

    return config[gid]


def format_message(template: str, member: discord.Member):
    return (
        template
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace(
            "{count}",
            str(member.guild.member_count or 0)
        )
    )


intents = discord.Intents.default()
intents.members = True
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


@bot.event
async def on_ready():
    print("--------------------------------")
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("--------------------------------")


async def send_embed(
    interaction: discord.Interaction,
    title: str,
    description: str,
    ephemeral: bool = False
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple()
    )

    try:
        await interaction.response.send_message(
            embed=embed,
            ephemeral=ephemeral
        )
    except discord.InteractionResponded:
        await interaction.followup.send(
            embed=embed,
            ephemeral=ephemeral
        )
def build_member_embed(
    member: discord.Member,
    title: str,
    description: str,
    image_name: str
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    image_path = image_name

    if os.path.exists(image_path):
        embed.set_image(url=f"attachment://{image_name}")

    embed.set_footer(
        text=f"{member.guild.name} • Member #{member.guild.member_count or 0}"
    )

    return embed


async def send_member_message(
    channel: discord.TextChannel,
    member: discord.Member,
    template: str,
    title: str,
    image_name: str
):
    description = format_message(template, member)

    embed = build_member_embed(
        member,
        title,
        description,
        image_name
    )

    if os.path.exists(image_name):
        file = discord.File(image_name, filename=image_name)

        await channel.send(
            embed=embed,
            file=file
        )
    else:
        await channel.send(embed=embed)


@bot.event
async def on_member_join(member: discord.Member):
    settings = guild_config(member.guild.id)

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

    try:
        await send_member_message(
            channel,
            member,
            message,
            "👋 Welcome!",
            "welcome.png"
        )
    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"Welcome error: {e}")


@bot.event
async def on_member_remove(member: discord.Member):
    settings = guild_config(member.guild.id)

    channel_id = settings.get("bye_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)

    if not isinstance(channel, discord.TextChannel):
        return

    message = settings.get(
        "bye_message",
        "Goodbye {username}! 👋"
    )

    try:
        await send_member_message(
            channel,
            member,
            message,
            "👋 Goodbye!",
            "bye.png"
        )
    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"Bye error: {e}")


@bot.tree.command(
    name="welcome",
    description="Set the welcome channel."
)
@app_commands.describe(channel="The channel for welcome messages.")
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = guild_config(interaction.guild.id)

    settings["welcome_channel"] = channel.id
    save_config()

    await send_embed(
        interaction,
        "✅ Welcome Channel",
        f"Welcome messages will now be sent in {channel.mention}.",
        True
    )


@bot.tree.command(
    name="welcome-message",
    description="Customize the welcome message."
)
@app_commands.describe(message="Your welcome message.")
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_message(
    interaction: discord.Interaction,
    message: app_commands.Range[str, 1, 1000]
):
    settings = guild_config(interaction.guild.id)

    settings["welcome_message"] = message
    save_config()

    await send_embed(
        interaction,
        "✅ Welcome Message Updated",
        "Your welcome message has been saved.",
        True
    )


@bot.tree.command(
    name="bye",
    description="Set the goodbye channel."
)
@app_commands.describe(channel="The channel for goodbye messages.")
@app_commands.checks.has_permissions(manage_guild=True)
async def bye(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = guild_config(interaction.guild.id)

    settings["bye_channel"] = channel.id
    save_config()

    await send_embed(
        interaction,
        "✅ Bye Channel",
        f"Goodbye messages will now be sent in {channel.mention}.",
        True
    )


@bot.tree.command(
    name="bye-message",
    description="Customize the goodbye message."
)
@app_commands.describe(message="Your goodbye message.")
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_message(
    interaction: discord.Interaction,
    message: app_commands.Range[str, 1, 1000]
):
    settings = guild_config(interaction.guild.id)

    settings["bye_message"] = message
    save_config()

    await send_embed(
        interaction,
        "✅ Goodbye Message Updated",
        "Your goodbye message has been saved.",
        True
    )


@bot.tree.command(
    name="testwelcome",
    description="Test the welcome message."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def testwelcome(interaction: discord.Interaction):
    settings = guild_config(interaction.guild.id)

    channel_id = settings.get("welcome_channel")

    if not channel_id:
        await send_embed(
            interaction,
            "❌ Not Configured",
            "Use `/welcome` first.",
            True
        )
        return

    channel = interaction.guild.get_channel(channel_id)

    if not isinstance(channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Invalid Channel",
            "The configured welcome channel no longer exists.",
            True
        )
        return

    message = settings.get(
        "welcome_message",
        "Welcome {user} to **{server}**! 🎉"
    )

    try:
        await send_member_message(
            channel,
            interaction.user,
            message,
            "👋 Welcome!",
            "welcome.png"
        )

        await send_embed(
            interaction,
            "✅ Test Sent",
            f"Check {channel.mention}.",
            True
        )
    except (discord.Forbidden, discord.HTTPException):
        await send_embed(
            interaction,
            "❌ Error",
            "I can't send messages in that channel.",
            True
        )


@bot.tree.command(
    name="testbye",
    description="Test the goodbye message."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def testbye(interaction: discord.Interaction):
    settings = guild_config(interaction.guild.id)

    channel_id = settings.get("bye_channel")

    if not channel_id:
        await send_embed(
            interaction,
            "❌ Not Configured",
            "Use `/bye` first.",
            True
        )
        return

    channel = interaction.guild.get_channel(channel_id)

    if not isinstance(channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Invalid Channel",
            "The configured goodbye channel no longer exists.",
            True
        )
        return

    message = settings.get(
        "bye_message",
        "Goodbye {username}! 👋"
    )

    try:
        await send_member_message(
            channel,
            interaction.user,
            message,
            "👋 Goodbye!",
            "bye.png"
        )

        await send_embed(
            interaction,
            "✅ Test Sent",
            f"Check {channel.mention}.",
            True
        )
    except (discord.Forbidden, discord.HTTPException):
        await send_embed(
            interaction,
            "❌ Error",
            "I can't send messages in that channel.",
            True
    )
@bot.tree.command(
    name="verifysetup",
    description="Set the role given when someone verifies."
)
@app_commands.describe(role="The role verified members receive.")
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
            "You cannot use a managed integration/bot role.",
            True
        )
        return

    if role >= guild.me.top_role:
        await send_embed(
            interaction,
            "❌ Role Too High",
            "Move my bot role above the verification role.",
            True
        )
        return

    settings = guild_config(guild.id)

    settings["verify_role"] = role.id
    save_config()

    await send_embed(
        interaction,
        "✅ Verification Setup",
        f"Verified members will receive {role.mention}.",
        True
    )


@bot.tree.command(
    name="verify-message",
    description="Customize the verification message."
)
@app_commands.describe(message="Your verification message.")
@app_commands.checks.has_permissions(manage_guild=True)
async def verify_message(
    interaction: discord.Interaction,
    message: app_commands.Range[str, 1, 1000]
):
    settings = guild_config(interaction.guild.id)

    settings["verify_message"] = message
    save_config()

    await send_embed(
        interaction,
        "✅ Verify Message Updated",
        "Your verification message has been saved.",
        True
    )


@bot.tree.command(
    name="verify",
    description="Verify yourself and receive the verification role."
)
async def verify(interaction: discord.Interaction):
    guild = interaction.guild
    settings = guild_config(guild.id)

    role_id = settings.get("verify_role")

    if not role_id:
        await send_embed(
            interaction,
            "❌ Verification Not Setup",
            "An administrator needs to use `/verifysetup` first.",
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

    member = interaction.user

    if role in member.roles:
        await send_embed(
            interaction,
            "ℹ️ Already Verified",
            "You already have the verification role.",
            True
        )
        return

    if role >= guild.me.top_role:
        await send_embed(
            interaction,
            "❌ Bot Role Too Low",
            "Move my bot role above the verification role.",
            True
        )
        return

    try:
        await member.add_roles(
            role,
            reason="Security verification"
        )

        message = settings.get(
            "verify_message",
            "You are now verified! ✅"
        )

        message = format_message(
            message,
            member
        )

        await send_embed(
            interaction,
            "✅ Verified",
            message,
            True
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Permission Error",
            "I cannot give that role. Move my bot role above it.",
            True
        )

    except discord.HTTPException:
        await send_embed(
            interaction,
            "❌ Discord Error",
            "Discord rejected the role change. Try again.",
            True
        )
@bot.tree.command(
    name="clear",
    description="Delete messages from the current channel."
)
@app_commands.describe(amount="Number of messages to delete.")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    if not isinstance(interaction.channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "This command can only be used in a text channel.",
            True
        )
        return

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
            "❌ I need **Manage Messages** permission.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord could not delete the messages.",
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
    reason: Optional[str] = "No reason provided"
):
    if member == interaction.user:
        await send_embed(
            interaction,
            "❌ Error",
            "You cannot kick yourself.",
            True
        )
        return

    if member.top_role >= interaction.user.top_role:
        await send_embed(
            interaction,
            "❌ Error",
            "You cannot kick someone with an equal or higher role.",
            True
        )
        return

    try:
        await member.kick(reason=reason)

        await send_embed(
            interaction,
            "👢 Member Kicked",
            f"{member} was kicked.\n**Reason:** {reason}"
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Error",
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
    reason: Optional[str] = "No reason provided"
):
    if member == interaction.user:
        await send_embed(
            interaction,
            "❌ Error",
            "You cannot ban yourself.",
            True
        )
        return

    if member.top_role >= interaction.user.top_role:
        await send_embed(
            interaction,
            "❌ Error",
            "You cannot ban someone with an equal or higher role.",
            True
        )
        return

    try:
        await member.ban(reason=reason)

        await send_embed(
            interaction,
            "🔨 Member Banned",
            f"{member} was banned.\n**Reason:** {reason}"
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Error",
            "I cannot ban that member.",
            True
        )


@bot.tree.command(
    name="timeout",
    description="Timeout a member."
)
@app_commands.describe(
    member="Member to timeout.",
    minutes="Timeout length in minutes."
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320]
):
    if member.top_role >= interaction.user.top_role:
        await send_embed(
            interaction,
            "❌ Error",
            "You cannot timeout someone with an equal or higher role.",
            True
        )
        return

    try:
        until = discord.utils.utcnow() + discord.timedelta(
            minutes=minutes
        )
    except AttributeError:
        from datetime import timedelta
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
            "❌ Error",
            "I cannot timeout that member.",
            True
        )


@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout."
)
@app_commands.describe(member="Member to untimeout.")
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
            "❌ Error",
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
            "That role cannot be manually assigned.",
            True
        )
        return

    if role >= interaction.guild.me.top_role:
        await send_embed(
            interaction,
            "❌ Role Too High",
            "My bot role must be above that role.",
            True
        )
        return

    try:
        await member.add_roles(role)

        await send_embed(
            interaction,
            "✅ Role Added",
            f"Added {role.mention} to {member.mention}."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Error",
            "I cannot add that role.",
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
            "That role cannot be manually removed.",
            True
        )
        return

    if role >= interaction.guild.me.top_role:
        await send_embed(
            interaction,
            "❌ Role Too High",
            "My bot role must be above that role.",
            True
        )
        return

    try:
        await member.remove_roles(role)

        await send_embed(
            interaction,
            "✅ Role Removed",
            f"Removed {role.mention} from {member.mention}."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Error",
            "I cannot remove that role.",
            True
        )
@bot.tree.command(
    name="clearuser",
    description="Delete recent messages from one member."
)
@app_commands.describe(
    member="Member whose messages should be removed.",
    amount="Maximum number of messages to check."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearuser(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 1, 100]
):
    if not isinstance(interaction.channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "Use this in a text channel.",
            True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        messages = []

        async for message in interaction.channel.history(
            limit=amount
        ):
            if message.author.id == member.id:
                messages.append(message)

        if messages:
            await interaction.channel.delete_messages(messages)

        await interaction.followup.send(
            f"🧹 Deleted **{len(messages)}** messages from {member.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need Manage Messages permission.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord could not delete those messages.",
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
            "This only works in a text channel.",
            True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        new_channel = await channel.clone(
            reason=f"Channel cleared by {interaction.user}"
        )

        await new_channel.edit(
            position=channel.position,
            category=channel.category
        )

        await channel.delete(
            reason=f"Channel cleared by {interaction.user}"
        )

        await new_channel.send(
            "🧹 **Channel cleaned.**"
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need Manage Channels permission.",
            ephemeral=True
        )


@bot.tree.command(
    name="clearbots",
    description="Delete recent messages sent by bots."
)
@app_commands.describe(
    amount="Number of recent messages to check."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearbots(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    if not isinstance(interaction.channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "Use this in a text channel.",
            True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        messages = []

        async for message in interaction.channel.history(
            limit=amount
        ):
            if message.author.bot:
                messages.append(message)

        if messages:
            await interaction.channel.delete_messages(messages)

        await interaction.followup.send(
            f"🤖 Deleted **{len(messages)}** bot messages.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need Manage Messages permission.",
            ephemeral=True
        )


@bot.tree.command(
    name="clearlinks",
    description="Delete recent messages containing links."
)
@app_commands.describe(
    amount="Number of recent messages to check."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearlinks(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    if not isinstance(interaction.channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "Use this in a text channel.",
            True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        messages = []

        async for message in interaction.channel.history(
            limit=amount
        ):
            if "http://" in message.content.lower() or "https://" in message.content.lower():
                messages.append(message)

        if messages:
            await interaction.channel.delete_messages(messages)

        await interaction.followup.send(
            f"🔗 Deleted **{len(messages)}** messages containing links.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need Manage Messages permission.",
            ephemeral=True
        )


@bot.tree.command(
    name="clearinvites",
    description="Delete recent Discord invite messages."
)
@app_commands.describe(
    amount="Number of recent messages to check."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clearinvites(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):
    if not isinstance(interaction.channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "Use this in a text channel.",
            True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        messages = []

        async for message in interaction.channel.history(
            limit=amount
        ):
            content = message.content.lower()

            if (
                "discord.gg/" in content
                or "discord.com/invite/" in content
            ):
                messages.append(message)

        if messages:
            await interaction.channel.delete_messages(messages)

        await interaction.followup.send(
            f"🚫 Deleted **{len(messages)}** Discord invite messages.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need Manage Messages permission.",
            ephemeral=True
        )


@bot.tree.command(
    name="slowmode",
    description="Set channel slowmode."
)
@app_commands.describe(
    seconds="Slowmode seconds, from 0 to 21600."
)
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(
    interaction: discord.Interaction,
    seconds: app_commands.Range[int, 0, 21600]
):
    if not isinstance(interaction.channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "Use this in a text channel.",
            True
        )
        return

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
            "❌ Error",
            "I need Manage Channels permission.",
            True
        )


@bot.tree.command(
    name="lock",
    description="Lock the current channel."
)
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "Use this in a text channel.",
            True
        )
        return

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
            "Members can no longer send messages here."
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Error",
            "I need Manage Channels permission.",
            True
        )


@bot.tree.command(
    name="unlock",
    description="Unlock the current channel."
)
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "Use this in a text channel.",
            True
        )
        return

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
            "❌ Error",
            "I need Manage Channels permission.",
            True
        )


class WipeView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=30)
        self.author_id = author_id

    @discord.ui.button(
        label="CONFIRM WIPE",
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

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Administrator permission is required.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild

        deleted_channels = 0
        deleted_roles = 0

        me = guild.me

        if me is None:
            await interaction.followup.send(
                "❌ I could not identify my bot member.",
                ephemeral=True
            )
            return

        if not me.guild_permissions.manage_channels:
            await interaction.followup.send(
                "❌ I need **Manage Channels** permission.",
                ephemeral=True
            )
            return

        if not me.guild_permissions.manage_roles:
            await interaction.followup.send(
                "❌ I need **Manage Roles** permission.",
                ephemeral=True
            )
            return

        # Delete channels/categories.
        for channel in list(guild.channels):
            try:
                await channel.delete(
                    reason=f"Server wipe by {interaction.user}"
                )
                deleted_channels += 1
            except (discord.Forbidden, discord.HTTPException):
                pass

        # Delete removable roles.
        for role in list(guild.roles):
            if role.is_default():
                continue

            if role.managed:
                continue

            if role >= me.top_role:
                continue

            try:
                await role.delete(
                    reason=f"Server wipe by {interaction.user}"
                )
                deleted_roles += 1
            except (discord.Forbidden, discord.HTTPException):
                pass

        try:
            await interaction.followup.send(
                "💀 **SERVER WIPE COMPLETE**\n\n"
                f"🗑️ Channels removed: **{deleted_channels}**\n"
                f"🎭 Roles removed: **{deleted_roles}**\n\n"
                "The Discord server itself was **NOT deleted**.",
                ephemeral=True
            )
        except discord.HTTPException:
            pass

    @discord.ui.button(
        label="CANCEL",
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

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="❌ **Server wipe cancelled.**",
            view=self
        )

        self.stop()


@bot.tree.command(
    name="wipe",
    description="Wipe channels and removable roles from this server."
)
@app_commands.checks.has_permissions(administrator=True)
async def wipe(interaction: discord.Interaction):
    warning = discord.Embed(
        title="⚠️ SERVER WIPE WARNING",
        description=(
            "**THIS WILL DELETE:**\n"
            "🗑️ Channels\n"
            "🗂️ Categories\n"
            "🎭 Removable roles\n\n"
            "**THIS WILL NOT DELETE:**\n"
            "❌ The Discord server itself\n"
            "❌ @everyone\n"
            "❌ Managed roles\n"
            "❌ Roles above the bot\n\n"
            "**This action cannot be easily undone.**"
        ),
        color=discord.Color.red()
    )

    await interaction.response.send_message(
        embed=warning,
        view=WipeView(interaction.user.id),
        ephemeral=True
        )
@bot.tree.command(
    name="ping",
    description="Check the bot latency."
)
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)

    await send_embed(
        interaction,
        "🏓 Pong!",
        f"Bot latency: **{latency}ms**"
    )


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

    embed.add_field(
        name="👥 Members",
        value=str(guild.member_count or 0),
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

    embed.add_field(
        name="🆔 Server ID",
        value=str(guild.id),
        inline=False
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="userinfo",
    description="Show information about a member."
)
@app_commands.describe(member="Member to inspect.")
async def userinfo(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user

    embed = discord.Embed(
        title=f"👤 {member}",
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
        name="Top Role",
        value=member.top_role.mention,
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="avatar",
    description="Show a member's avatar."
)
@app_commands.describe(member="Member whose avatar you want.")
async def avatar(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):
    member = member or interaction.user

    embed = discord.Embed(
        title=f"🖼️ {member.name}'s Avatar",
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
async def servericon(interaction: discord.Interaction):
    guild = interaction.guild

    if not guild.icon:
        await send_embed(
            interaction,
            "❌ No Icon",
            "This server does not have an icon.",
            True
        )
        return

    embed = discord.Embed(
        title=f"🖼️ {guild.name} Icon",
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=guild.icon.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="botinfo",
    description="Show bot information."
)
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ SECURITY",
        description="Security and moderation Discord bot.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Commands",
        value=str(len(bot.tree.get_commands())),
        inline=True
    )

    embed.add_field(
        name="Servers",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="discord.py",
        value=discord.__version__,
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
    description="Make the bot send a message."
)
@app_commands.describe(message="Message to send.")
@app_commands.checks.has_permissions(manage_messages=True)
async def say(
    interaction: discord.Interaction,
    message: app_commands.Range[str, 1, 2000]
):
    if not isinstance(interaction.channel, discord.TextChannel):
        await send_embed(
            interaction,
            "❌ Error",
            "Use this in a text channel.",
            True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        await interaction.channel.send(message)

        await interaction.followup.send(
            "✅ Message sent.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I cannot send messages here.",
            ephemeral=True
        )


@bot.tree.command(
    name="announce",
    description="Send an announcement embed."
)
@app_commands.describe(message="Announcement text.")
@app_commands.checks.has_permissions(manage_guild=True)
async def announce(
    interaction: discord.Interaction,
    message: app_commands.Range[str, 1, 2000]
):
    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"Announcement by {interaction.user}"
    )

    try:
        await interaction.channel.send(
            embed=embed
        )

        await send_embed(
            interaction,
            "✅ Announcement Sent",
            "The announcement was sent.",
            True
        )

    except discord.Forbidden:
        await send_embed(
            interaction,
            "❌ Error",
            "I cannot send messages in this channel.",
            True
        )


@bot.tree.command(
    name="help",
    description="Show SECURITY commands."
)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ SECURITY — Help",
        description="Main bot commands:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👋 Welcome / Bye",
        value=(
            "`/welcome`\n"
            "`/welcome-message`\n"
            "`/bye`\n"
            "`/bye-message`\n"
            "`/testwelcome`\n"
            "`/testbye`"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ Verify",
        value=(
            "`/verifysetup`\n"
            "`/verify-message`\n"
            "`/verify`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Cleaner",
        value=(
            "`/clear`\n"
            "`/clearuser`\n"
            "`/clearchannel`\n"
            "`/clearbots`\n"
            "`/clearlinks`\n"
            "`/clearinvites`\n"
            "`/slowmode`\n"
            "`/lock`\n"
            "`/unlock`\n"
            "`/wipe`"
        ),
        inline=False
    )

    embed.add_field(
        name="🔨 Moderation",
        value=(
            "`/kick`\n"
            "`/ban`\n"
            "`/timeout`\n"
            "`/untimeout`\n"
            "`/addrole`\n"
            "`/removerole`"
        ),
        inline=False
    )

    embed.add_field(
        name="🔧 Utility",
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


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.errors.MissingPermissions):
        message = "❌ You don't have permission to use this command."

    elif isinstance(error, app_commands.errors.CheckFailure):
        message = "❌ You don't have permission to use this command."

    else:
        print(f"Command error: {repr(error)}")
        message = "❌ Something went wrong while running that command."

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


bot.run(TOKEN)    
