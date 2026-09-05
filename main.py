# =========================
#        START PART 1
# =========================

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


# =========================
#       BOT SETTINGS
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG_FILE = "config.json"

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Add it to Railway Variables."
    )


# =========================
#       CONFIG SYSTEM
# =========================

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


# =========================
#      MESSAGE SYSTEM
# =========================

def format_message(text, member):
    return (
        text
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace(
            "{count}",
            str(member.guild.member_count or 0)
        )
    )


# =========================
#       TIKTOK SYSTEM
# =========================

def extract_tiktok_link(text):
    if not text:
        return None

    pattern = (
        r"https?://"
        r"(?:www\.|vm\.|vt\.|m\.)?"
        r"tiktok\.com/"
        r"[^\s<>()]+"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    return match.group(0).rstrip(
        ".,!?)]}"
    )


# =========================
#         INTENTS
# =========================

intents = discord.Intents.default()

intents.members = True
intents.message_content = True


# =========================
#      VERIFY SYSTEM
# =========================

async def verify_member(member: discord.Member):

    settings = get_guild_config(
        member.guild.id
    )

    role_id = settings.get(
        "verify_role"
    )

    if not role_id:
        return (
            False,
            "❌ Verification has not been configured yet."
        )

    try:
        role_id = int(role_id)

    except (TypeError, ValueError):
        return (
            False,
            "❌ The saved verification role is invalid."
        )

    role = member.guild.get_role(role_id)

    if role is None:
        return (
            False,
            "❌ The verification role no longer exists."
        )

    if role.is_default():
        return (
            False,
            "❌ You cannot use @everyone."
        )

    if role.managed:
        return (
            False,
            "❌ That role is managed and cannot be assigned."
        )

    if role in member.roles:
        return (
            True,
            "✅ You are already verified."
        )

    bot_member = member.guild.me

    if bot_member is None:
        return (
            False,
            "❌ I could not find the bot in this server."
        )

    if not bot_member.guild_permissions.manage_roles:
        return (
            False,
            "❌ I need the Manage Roles permission."
        )

    if role >= bot_member.top_role:
        return (
            False,
            "❌ Move my bot role above the verification role."
        )

    try:
        await member.add_roles(
            role,
            reason="SECURITY verification"
        )

        return (
            True,
            f"✅ You are now verified! "
            f"You received {role.mention}."
        )

    except discord.Forbidden:
        return (
            False,
            "❌ I cannot give you that role. "
            "Make sure my bot role is above it."
        )

    except discord.HTTPException:
        return (
            False,
            "❌ Discord rejected the role assignment."
        )


# =========================
#       VERIFY BUTTON
# =========================

class VerifyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        emoji="🛡️",
        style=discord.ButtonStyle.success,
        custom_id="security_verify_button"
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True
            )
            return

        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ I couldn't identify you as a server member.",
                ephemeral=True
            )
            return

        success, message = await verify_member(
            member
        )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


# =========================
#      VERIFY PANEL
# =========================

def create_verify_panel(guild):

    settings = get_guild_config(
        guild.id
    )

    message = settings.get(
        "verify_message",
        "Click the button below to verify yourself "
        "and access the server."
    )

    embed = discord.Embed(
        title="🛡️ Server Verification",
        description=message,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"{guild.name} • SECURITY"
    )

    return embed


# =========================
#         END PART 1
# =========================
# =========================
#        START PART 2
# =========================

class SecurityBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        self.add_view(VerifyView())

        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands.")
        except Exception as error:
            print(f"Sync error: {error}")


bot = SecurityBot()


# =========================
#      VERIFY COMMANDS
# =========================

@bot.tree.command(
    name="verifysetup",
    description="Set the verification role."
)
@app_commands.checks.has_permissions(administrator=True)
async def verifysetup(
    interaction: discord.Interaction,
    role: discord.Role
):
    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ That role cannot be used.",
            ephemeral=True
        )
        return

    bot_member = interaction.guild.me

    if not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ I need Manage Roles permission.",
            ephemeral=True
        )
        return

    if role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ Move my bot role above the verification role.",
            ephemeral=True
        )
        return

    settings = get_guild_config(
        interaction.guild.id
    )

    settings["verify_role"] = role.id
    save_config()

    await interaction.response.send_message(
        f"✅ Verification role set to {role.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify-message",
    description="Set the verification message."
)
@app_commands.checks.has_permissions(administrator=True)
async def verify_message(
    interaction: discord.Interaction,
    text: str
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["verify_message"] = text
    save_config()

    await interaction.response.send_message(
        "✅ Verification message updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="verify-panel",
    description="Send the verification panel."
)
@app_commands.checks.has_permissions(administrator=True)
async def verify_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(
        interaction.guild.id
    )

    if not settings.get("verify_role"):
        await interaction.response.send_message(
            "❌ Run `/verifysetup @role` first.",
            ephemeral=True
        )
        return

    try:
        await channel.send(
            embed=create_verify_panel(
                interaction.guild
            ),
            view=VerifyView()
        )

        await interaction.response.send_message(
            f"✅ Verification panel sent to {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot send messages in that channel.",
            ephemeral=True
        )


@bot.tree.command(
    name="verify",
    description="Manually verify a member."
)
@app_commands.checks.has_permissions(manage_roles=True)
async def verify(
    interaction: discord.Interaction,
    member: discord.Member
):
    success, message = await verify_member(
        member
    )

    await interaction.response.send_message(
        message,
        ephemeral=True
    )


# =========================
#     WELCOME / BYE HELPERS
# =========================

def make_member_embed(
    member,
    title,
    message,
    image_url=None,
    style="avatar"
):
    embed = discord.Embed(
        title=title,
        description=format_message(
            message,
            member
        ),
        color=discord.Color.blurple()
    )

    avatar_url = member.display_avatar.url

    if style in ("avatar", "both"):
        embed.set_thumbnail(
            url=avatar_url
        )

    if style == "avatar":
        embed.set_image(
            url=avatar_url
        )

    elif style in ("custom", "both") and image_url:
        embed.set_image(
            url=image_url
        )

    embed.set_footer(
        text=f"{member.guild.name} • SECURITY"
    )

    return embed


# =========================
#     WELCOME COMMANDS
# =========================

@bot.tree.command(
    name="welcome",
    description="Set the welcome channel."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["welcome_channel"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"✅ Welcome channel set to {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="welcome-message",
    description="Set the welcome message."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_message(
    interaction: discord.Interaction,
    text: str
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["welcome_message"] = text
    save_config()

    await interaction.response.send_message(
        "✅ Welcome message updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="welcome-image",
    description="Set the welcome image."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["welcome_image"] = image.url
    save_config()

    await interaction.response.send_message(
        "✅ Welcome image updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="welcome-style",
    description="Set the welcome style."
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.choices(
    style=[
        app_commands.Choice(
            name="Avatar",
            value="avatar"
        ),
        app_commands.Choice(
            name="Custom",
            value="custom"
        ),
        app_commands.Choice(
            name="Both",
            value="both"
        )
    ]
)
async def welcome_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["welcome_style"] = style.value
    save_config()

    await interaction.response.send_message(
        f"✅ Welcome style: **{style.name}**",
        ephemeral=True
    )


@bot.tree.command(
    name="testwelcome",
    description="Test the welcome message."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def testwelcome(
    interaction: discord.Interaction
):
    settings = get_guild_config(
        interaction.guild.id
    )

    message = settings.get(
        "welcome_message",
        "Welcome {user} to **{server}**! 🎉"
    )

    image = settings.get(
        "welcome_image"
    )

    style = settings.get(
        "welcome_style",
        "avatar"
    )

    embed = make_member_embed(
        interaction.user,
        "Welcome! 🎉",
        message,
        image,
        style
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#       BYE COMMANDS
# =========================

@bot.tree.command(
    name="bye",
    description="Set the goodbye channel."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["bye_channel"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"✅ Goodbye channel set to {channel.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-message",
    description="Set the goodbye message."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_message(
    interaction: discord.Interaction,
    text: str
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["bye_message"] = text
    save_config()

    await interaction.response.send_message(
        "✅ Goodbye message updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-image",
    description="Set the goodbye image."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def bye_image(
    interaction: discord.Interaction,
    image: discord.Attachment
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["bye_image"] = image.url
    save_config()

    await interaction.response.send_message(
        "✅ Goodbye image updated.",
        ephemeral=True
    )


@bot.tree.command(
    name="bye-style",
    description="Set the goodbye style."
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.choices(
    style=[
        app_commands.Choice(
            name="Avatar",
            value="avatar"
        ),
        app_commands.Choice(
            name="Custom",
            value="custom"
        ),
        app_commands.Choice(
            name="Both",
            value="both"
        )
    ]
)
async def bye_style(
    interaction: discord.Interaction,
    style: app_commands.Choice[str]
):
    settings = get_guild_config(
        interaction.guild.id
    )

    settings["bye_style"] = style.value
    save_config()

    await interaction.response.send_message(
        f"✅ Goodbye style: **{style.name}**",
        ephemeral=True
    )


@bot.tree.command(
    name="testbye",
    description="Test the goodbye message."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def testbye(
    interaction: discord.Interaction
):
    settings = get_guild_config(
        interaction.guild.id
    )

    message = settings.get(
        "bye_message",
        "Goodbye {user}. 👋"
    )

    image = settings.get(
        "bye_image"
    )

    style = settings.get(
        "bye_style",
        "avatar"
    )

    embed = make_member_embed(
        interaction.user,
        "Goodbye! 👋",
        message,
        image,
        style
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#         END PART 2
# =========================
# =========================
#        START PART 3
# =========================

@bot.tree.command(
    name="kick",
    description="Kick a member."
)
@app_commands.checks.has_permissions(
    kick_members=True
)
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
            "❌ You cannot kick someone with an equal or higher role.",
            ephemeral=True
        )
        return

    if member.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ My bot role is not high enough.",
            ephemeral=True
        )
        return

    try:
        await member.kick(reason=reason)

        await interaction.response.send_message(
            f"👢 Kicked {member.mention}.\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to kick this member.",
            ephemeral=True
        )


@bot.tree.command(
    name="ban",
    description="Ban a member."
)
@app_commands.checks.has_permissions(
    ban_members=True
)
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
            "❌ You cannot ban someone with an equal or higher role.",
            ephemeral=True
        )
        return

    if member.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ My bot role is not high enough.",
            ephemeral=True
        )
        return

    try:
        await member.ban(reason=reason)

        await interaction.response.send_message(
            f"🔨 Banned {member.mention}.\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to ban this member.",
            ephemeral=True
        )


@bot.tree.command(
    name="timeout",
    description="Timeout a member."
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320]
):
    if member == interaction.user:
        await interaction.response.send_message(
            "❌ You cannot timeout yourself.",
            ephemeral=True
        )
        return

    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "❌ You cannot timeout someone with an equal or higher role.",
            ephemeral=True
        )
        return

    if member.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ My bot role is not high enough.",
            ephemeral=True
        )
        return

    until = (
        discord.utils.utcnow()
        + timedelta(minutes=minutes)
    )

    try:
        await member.edit(
            timed_out_until=until,
            reason=f"Timeout by {interaction.user}"
        )

        await interaction.response.send_message(
            f"⏳ {member.mention} was timed out "
            f"for **{minutes} minutes**."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to timeout this member.",
            ephemeral=True
        )


@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout."
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member
):
    try:
        await member.edit(
            timed_out_until=None,
            reason=f"Untimeout by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Removed timeout from {member.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to remove this timeout.",
            ephemeral=True
        )


@bot.tree.command(
    name="addrole",
    description="Give a role to a member."
)
@app_commands.checks.has_permissions(
    manage_roles=True
)
async def addrole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    bot_member = interaction.guild.me

    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ That role cannot be assigned.",
            ephemeral=True
        )
        return

    if role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ My bot role must be above that role.",
            ephemeral=True
        )
        return

    try:
        await member.add_roles(
            role,
            reason=f"Role added by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Added {role.mention} to {member.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot assign that role.",
            ephemeral=True
        )


@bot.tree.command(
    name="removerole",
    description="Remove a role from a member."
)
@app_commands.checks.has_permissions(
    manage_roles=True
)
async def removerole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    bot_member = interaction.guild.me

    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ That role cannot be removed.",
            ephemeral=True
        )
        return

    if role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ My bot role must be above that role.",
            ephemeral=True
        )
        return

    try:
        await member.remove_roles(
            role,
            reason=f"Role removed by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Removed {role.mention} from {member.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot remove that role.",
            ephemeral=True
        )


# =========================
#         END PART 3
# =========================
# =========================
#        START PART 4
# =========================

async def delete_matching_messages(
    channel,
    checker,
    amount
):
    deleted = 0

    async for message in channel.history(
        limit=None
    ):
        if deleted >= amount:
            break

        if checker(message):
            try:
                await message.delete()
                deleted += 1
            except discord.HTTPException:
                pass

    return deleted


# =========================
#       CLEAR USER
# =========================

@bot.tree.command(
    name="clearuser",
    description="Delete messages from a user."
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearuser(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 1, 500]
):
    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await delete_matching_messages(
        interaction.channel,
        lambda message:
            message.author.id == member.id,
        amount
    )

    await interaction.followup.send(
        f"🧹 Deleted **{deleted}** messages "
        f"from {member.mention}.",
        ephemeral=True
    )


# =========================
#       CLEAR BOTS
# =========================

@bot.tree.command(
    name="clearbots",
    description="Delete bot messages."
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearbots(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 500]
):
    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await delete_matching_messages(
        interaction.channel,
        lambda message:
            message.author.bot,
        amount
    )

    await interaction.followup.send(
        f"🤖 Deleted **{deleted}** bot messages.",
        ephemeral=True
    )


# =========================
#       CLEAR LINKS
# =========================

@bot.tree.command(
    name="clearlinks",
    description="Delete messages containing links."
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearlinks(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 500]
):
    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await delete_matching_messages(
        interaction.channel,
        lambda message:
            bool(
                re.search(
                    r"https?://",
                    message.content
                )
            ),
        amount
    )

    await interaction.followup.send(
        f"🔗 Deleted **{deleted}** link messages.",
        ephemeral=True
    )


# =========================
#      CLEAR INVITES
# =========================

@bot.tree.command(
    name="clearinvites",
    description="Delete Discord invite messages."
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clearinvites(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 500]
):
    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await delete_matching_messages(
        interaction.channel,
        lambda message:
            bool(
                re.search(
                    r"(discord\.gg/|discord\.com/invite/)",
                    message.content,
                    re.IGNORECASE
                )
            ),
        amount
    )

    await interaction.followup.send(
        f"📨 Deleted **{deleted}** invite messages.",
        ephemeral=True
    )


# =========================
#       CLEAR CHANNEL
# =========================

@bot.tree.command(
    name="clearchannel",
    description="Clear the current channel."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def clearchannel(
    interaction: discord.Interaction
):
    channel = interaction.channel

    await interaction.response.send_message(
        "🧹 Clearing this channel...",
        ephemeral=True
    )

    try:
        new_channel = await channel.clone(
            reason=f"Channel cleared by {interaction.user}"
        )

        await new_channel.edit(
            position=channel.position
        )

        await channel.delete(
            reason=f"Channel cleared by {interaction.user}"
        )

        await new_channel.send(
            "🧹 **Channel cleared!**"
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to manage this channel.",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Discord rejected the channel operation.",
            ephemeral=True
        )


# =========================
#        SLOWMODE
# =========================

@bot.tree.command(
    name="slowmode",
    description="Set channel slowmode."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def slowmode(
    interaction: discord.Interaction,
    seconds: app_commands.Range[int, 0, 21600]
):
    try:
        await interaction.channel.edit(
            slowmode_delay=seconds
        )

        await interaction.response.send_message(
            f"🐌 Slowmode set to **{seconds} seconds**."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to edit this channel.",
            ephemeral=True
        )


# =========================
#           LOCK
# =========================

@bot.tree.command(
    name="lock",
    description="Lock the current channel."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def lock(
    interaction: discord.Interaction
):
    overwrite = (
        interaction.channel.overwrites_for(
            interaction.guild.default_role
        )
    )

    overwrite.send_messages = False

    try:
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await interaction.response.send_message(
            "🔒 Channel locked."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to lock this channel.",
            ephemeral=True
        )


# =========================
#          UNLOCK
# =========================

@bot.tree.command(
    name="unlock",
    description="Unlock the current channel."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def unlock(
    interaction: discord.Interaction
):
    overwrite = (
        interaction.channel.overwrites_for(
            interaction.guild.default_role
        )
    )

    overwrite.send_messages = None

    try:
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await interaction.response.send_message(
            "🔓 Channel unlocked."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to unlock this channel.",
            ephemeral=True
        )


# =========================
#         END PART 4
# =========================
# =========================
#        START PART 5
# =========================


# =========================
#        WIPE SYSTEM
# =========================

class WipeView(discord.ui.View):

    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id

    @discord.ui.button(
        label="Confirm Wipe",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You cannot use this button.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        bot_member = guild.me

        await interaction.response.edit_message(
            content="🧨 **Wiping the server...**",
            view=None
        )

        # Delete channels and categories
        if bot_member.guild_permissions.manage_channels:

            for channel in list(guild.channels):
                try:
                    await channel.delete(
                        reason=f"Server wipe by {interaction.user}"
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    pass

        # Delete removable roles
        if bot_member.guild_permissions.manage_roles:

            for role in list(guild.roles):

                if role.is_default():
                    continue

                if role.managed:
                    continue

                if role >= bot_member.top_role:
                    continue

                try:
                    await role.delete(
                        reason=f"Server wipe by {interaction.user}"
                    )
                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    pass

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You cannot use this button.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Server wipe cancelled.",
            view=None
        )


@bot.tree.command(
    name="wipe",
    description="Wipe removable channels and roles."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def wipe(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="⚠️ SERVER WIPE",
        description=(
            "This will delete:\n"
            "• All removable channels\n"
            "• All removable categories\n"
            "• All removable roles\n\n"
            "⚠️ **The Discord server itself will NOT be deleted.**\n"
            "⚠️ This action cannot be undone."
        ),
        color=discord.Color.red()
    )

    await interaction.response.send_message(
        embed=embed,
        view=WipeView(interaction.user.id),
        ephemeral=True
    )


# =========================
#          PING
# =========================

@bot.tree.command(
    name="ping",
    description="Check SECURITY's latency."
)
async def ping(
    interaction: discord.Interaction
):

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 **Pong!** `{latency}ms`"
    )


# =========================
#       SERVER INFO
# =========================

@bot.tree.command(
    name="serverinfo",
    description="Show server information."
)
async def serverinfo(
    interaction: discord.Interaction
):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👑 Owner",
        value=(
            guild.owner.mention
            if guild.owner
            else "Unknown"
        ),
        inline=True
    )

    embed.add_field(
        name="👥 Members",
        value=str(
            guild.member_count
        ),
        inline=True
    )

    embed.add_field(
        name="💬 Channels",
        value=str(
            len(guild.channels)
        ),
        inline=True
    )

    embed.add_field(
        name="🎭 Roles",
        value=str(
            len(guild.roles)
        ),
        inline=True
    )

    embed.add_field(
        name="🆔 Server ID",
        value=str(
            guild.id
        ),
        inline=True
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#         USER INFO
# =========================

@bot.tree.command(
    name="userinfo",
    description="Show information about a user."
)
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
        name="User ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Top Role",
        value=member.top_role.mention,
        inline=True
    )

    if member.joined_at:
        embed.add_field(
            name="Joined Server",
            value=discord.utils.format_dt(
                member.joined_at,
                "R"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#           AVATAR
# =========================

@bot.tree.command(
    name="avatar",
    description="Show a user's avatar."
)
async def avatar(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
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


# =========================
#        SERVER ICON
# =========================

@bot.tree.command(
    name="servericon",
    description="Show the server icon."
)
async def servericon(
    interaction: discord.Interaction
):

    if not interaction.guild.icon:
        await interaction.response.send_message(
            "❌ This server doesn't have an icon."
        )
        return

    embed = discord.Embed(
        title="🖼️ Server Icon",
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=interaction.guild.icon.url
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#          BOT INFO
# =========================

@bot.tree.command(
    name="botinfo",
    description="Show SECURITY information."
)
async def botinfo(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🛡️ SECURITY",
        description=(
            "Security, moderation and "
            "server management bot."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Servers",
        value=str(
            len(bot.guilds)
        ),
        inline=True
    )

    embed.add_field(
        name="Commands",
        value=str(
            len(bot.tree.get_commands())
        ),
        inline=True
    )

    embed.add_field(
        name="Library",
        value="discord.py",
        inline=True
    )

    embed.set_thumbnail(
        url=bot.user.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#           SAY
# =========================

@bot.tree.command(
    name="say",
    description="Make SECURITY send a message."
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def say(
    interaction: discord.Interaction,
    message: str
):

    await interaction.response.send_message(
        "✅ Message sent.",
        ephemeral=True
    )

    await interaction.channel.send(
        message
    )


# =========================
#        ANNOUNCE
# =========================

@bot.tree.command(
    name="announce",
    description="Send an announcement."
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def announce(
    interaction: discord.Interaction,
    message: str
):

    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        "✅ Announcement sent.",
        ephemeral=True
    )

    await interaction.channel.send(
        embed=embed
    )


# =========================
#         END PART 5
# =========================
# =========================
#        START PART 6
# =========================

# =========================
#        LEVEL SYSTEM
# =========================

def get_level_data(guild_id):
    settings = get_guild_config(guild_id)

    if "levels" not in settings:
        settings["levels"] = {
            "enabled": True,
            "channel": None,
            "message": "🎉 {user} reached **Level {level}**!"
        }

    if "xp" not in settings:
        settings["xp"] = {}

    return settings


def get_user_xp(guild_id, user_id):
    settings = get_level_data(guild_id)

    user_id = str(user_id)

    if user_id not in settings["xp"]:
        settings["xp"][user_id] = {
            "xp": 0,
            "level": 0
        }

    return settings["xp"][user_id]


def calculate_level(xp):
    return int((xp / 100) ** 0.5)


def level_required(level):
    return level * level * 100


def add_xp(guild_id, user_id, amount):
    settings = get_level_data(guild_id)

    data = get_user_xp(
        guild_id,
        user_id
    )

    old_level = data["level"]

    data["xp"] += amount

    new_level = calculate_level(
        data["xp"]
    )

    data["level"] = new_level

    save_config()

    return (
        data,
        old_level,
        new_level
    )


# =========================
#          RANK
# =========================

@bot.tree.command(
    name="rank",
    description="Show your level and XP."
)
async def rank(
    interaction: discord.Interaction
):

    data = get_user_xp(
        interaction.guild.id,
        interaction.user.id
    )

    xp = data["xp"]
    level = data["level"]

    current_level_xp = (
        level_required(level)
    )

    next_level_xp = (
        level_required(level + 1)
    )

    progress = (
        xp - current_level_xp
    )

    needed = (
        next_level_xp - current_level_xp
    )

    embed = discord.Embed(
        title=f"🏆 {interaction.user.display_name}'s Rank",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="⭐ Level",
        value=str(level),
        inline=True
    )

    embed.add_field(
        name="✨ XP",
        value=f"{xp:,}",
        inline=True
    )

    embed.add_field(
        name="📈 Progress",
        value=f"{progress:,} / {needed:,} XP",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#         LEVEL
# =========================

@bot.tree.command(
    name="level",
    description="Show another member's level."
)
async def level(
    interaction: discord.Interaction,
    member: discord.Member
):

    data = get_user_xp(
        interaction.guild.id,
        member.id
    )

    embed = discord.Embed(
        title=f"🏆 {member.display_name}'s Level",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="⭐ Level",
        value=str(data["level"]),
        inline=True
    )

    embed.add_field(
        name="✨ XP",
        value=f"{data['xp']:,}",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#       LEADERBOARD
# =========================

@bot.tree.command(
    name="leaderboard",
    description="Show the server XP leaderboard."
)
async def leaderboard(
    interaction: discord.Interaction
):

    settings = get_level_data(
        interaction.guild.id
    )

    xp_data = settings["xp"]

    if not xp_data:
        await interaction.response.send_message(
            "📊 There are no XP records yet."
        )
        return

    sorted_users = sorted(
        xp_data.items(),
        key=lambda item: item[1]["xp"],
        reverse=True
    )

    lines = []

    for position, (user_id, data) in enumerate(
        sorted_users[:10],
        start=1
    ):

        member = interaction.guild.get_member(
            int(user_id)
        )

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        lines.append(
            f"**{position}.** {name} — "
            f"Level {data['level']} • "
            f"{data['xp']:,} XP"
        )

    embed = discord.Embed(
        title="🏆 XP Leaderboard",
        description="\n".join(lines),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
#     LEVEL CHANNEL
# =========================

@bot.tree.command(
    name="setlevelchannel",
    description="Set the level-up channel."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setlevelchannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    settings = get_level_data(
        interaction.guild.id
    )

    settings["levels"]["channel"] = channel.id

    save_config()

    await interaction.response.send_message(
        f"✅ Level-up channel set to {channel.mention}.",
        ephemeral=True
    )


# =========================
#     LEVEL MESSAGE
# =========================

@bot.tree.command(
    name="setlevelmessage",
    description="Set the level-up message."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setlevelmessage(
    interaction: discord.Interaction,
    text: str
):

    settings = get_level_data(
        interaction.guild.id
    )

    settings["levels"]["message"] = text

    save_config()

    await interaction.response.send_message(
        "✅ Level-up message updated.",
        ephemeral=True
    )


# =========================
#       TOGGLE LEVELS
# =========================

@bot.tree.command(
    name="togglelevels",
    description="Enable or disable the level system."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def togglelevels(
    interaction: discord.Interaction,
    enabled: bool
):

    settings = get_level_data(
        interaction.guild.id
    )

    settings["levels"]["enabled"] = enabled

    save_config()

    status = (
        "enabled 🟢"
        if enabled
        else "disabled 🔴"
    )

    await interaction.response.send_message(
        f"✅ Level system is now **{status}**.",
        ephemeral=True
    )


# =========================
#        SET LEVEL
# =========================

@bot.tree.command(
    name="setlevel",
    description="Set a member's level."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setlevel(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 0, 1000]
):

    data = get_user_xp(
        interaction.guild.id,
        member.id
    )

    data["level"] = amount
    data["xp"] = level_required(
        amount
    )

    save_config()

    await interaction.response.send_message(
        f"✅ Set {member.mention}'s level to **{amount}**.",
        ephemeral=True
    )


# =========================
#          SET XP
# =========================

@bot.tree.command(
    name="setxp",
    description="Set a member's XP."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setxp(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 0, 100000000]
):

    data = get_user_xp(
        interaction.guild.id,
        member.id
    )

    data["xp"] = amount
    data["level"] = calculate_level(
        amount
    )

    save_config()

    await interaction.response.send_message(
        f"✅ Set {member.mention}'s XP to **{amount:,}**.",
        ephemeral=True
    )


# =========================
#         RESET XP
# =========================

@bot.tree.command(
    name="resetxp",
    description="Reset a member's XP."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def resetxp(
    interaction: discord.Interaction,
    member: discord.Member
):

    settings = get_level_data(
        interaction.guild.id
    )

    user_id = str(member.id)

    settings["xp"].pop(
        user_id,
        None
    )

    save_config()

    await interaction.response.send_message(
        f"♻️ Reset {member.mention}'s XP and level.",
        ephemeral=True
    )


# =========================
#         END PART 6
# =========================
# =========================
#        START PART 7
# =========================

# =========================
#       TICKET HELPERS
# =========================

def get_ticket_settings(guild_id):
    settings = get_guild_config(guild_id)

    if "tickets" not in settings:
        settings["tickets"] = {
            "category": None,
            "staff_role": None
        }

    return settings


def get_user_ticket(guild, user):
    settings = get_ticket_settings(guild.id)

    category_id = settings["tickets"].get(
        "category"
    )

    if not category_id:
        return None

    category = guild.get_channel(
        int(category_id)
    )

    if category is None:
        return None

    for channel in category.channels:
        if channel.topic == f"ticket:{user.id}":
            return channel

    return None


# =========================
#      CREATE TICKET
# =========================

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

        if guild is None:
            await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True
            )
            return

        settings = get_ticket_settings(
            guild.id
        )

        category_id = settings["tickets"].get(
            "category"
        )

        if not category_id:
            await interaction.response.send_message(
                "❌ Tickets have not been configured.",
                ephemeral=True
            )
            return

        category = guild.get_channel(
            int(category_id)
        )

        if not isinstance(
            category,
            discord.CategoryChannel
        ):
            await interaction.response.send_message(
                "❌ The ticket category is invalid.",
                ephemeral=True
            )
            return

        existing = get_user_ticket(
            guild,
            interaction.user
        )

        if existing:
            await interaction.response.send_message(
                f"❌ You already have a ticket: {existing.mention}",
                ephemeral=True
            )
            return

        staff_role = None

        staff_role_id = settings["tickets"].get(
            "staff_role"
        )

        if staff_role_id:
            staff_role = guild.get_role(
                int(staff_role_id)
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
                )
        }

        if staff_role:
            overwrites[staff_role] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True
                )
            )

        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                category=category,
                overwrites=overwrites,
                topic=f"ticket:{interaction.user.id}",
                reason=f"Ticket created by {interaction.user}"
            )

            await channel.send(
                f"🎫 Welcome {interaction.user.mention}!\n\n"
                "Please describe your issue and our staff "
                "will help you shortly.",
                view=TicketCloseView()
            )

            await interaction.response.send_message(
                f"✅ Ticket created: {channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to create ticket channels.",
                ephemeral=True
            )


# =========================
#       CLOSE TICKET
# =========================

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

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )
            return

        if not channel.topic:
            await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )
            return

        if not channel.topic.startswith(
            "ticket:"
        ):
            await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Closing ticket..."
        )

        await asyncio.sleep(2)

        try:
            await channel.delete(
                reason=f"Ticket closed by {interaction.user}"
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to delete this ticket.",
                ephemeral=True
            )


# =========================
#        TICKET GROUP
# =========================

ticket_group = app_commands.Group(
    name="ticket",
    description="Ticket system commands."
)

bot.tree.add_command(
    ticket_group
)


# =========================
#       TICKET SETUP
# =========================

@ticket_group.command(
    name="setup",
    description="Configure the ticket system."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def ticket_setup(
    interaction: discord.Interaction,
    category: discord.CategoryChannel,
    staff_role: Optional[discord.Role] = None
):

    settings = get_ticket_settings(
        interaction.guild.id
    )

    settings["tickets"]["category"] = (
        category.id
    )

    settings["tickets"]["staff_role"] = (
        staff_role.id
        if staff_role
        else None
    )

    save_config()

    if staff_role:
        staff_text = staff_role.mention
    else:
        staff_text = "Not set"

    await interaction.response.send_message(
        "✅ **Ticket system configured!**\n\n"
        f"📁 Category: {category.mention}\n"
        f"👮 Staff role: {staff_text}",
        ephemeral=True
    )


# =========================
#       TICKET PANEL
# =========================

@ticket_group.command(
    name="panel",
    description="Send the ticket panel."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def ticket_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    settings = get_ticket_settings(
        interaction.guild.id
    )

    if not settings["tickets"].get(
        "category"
    ):
        await interaction.response.send_message(
            "❌ Run `/ticket setup` first.",
            ephemeral=True
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
        text=f"{interaction.guild.name} • SECURITY"
    )

    try:
        await channel.send(
            embed=embed,
            view=TicketCreateView()
        )

        await interaction.response.send_message(
            f"✅ Ticket panel sent to {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot send messages in that channel.",
            ephemeral=True
        )


# =========================
#        TICKET CLOSE
# =========================

@ticket_group.command(
    name="close",
    description="Close the current ticket."
)
async def ticket_close(
    interaction: discord.Interaction
):

    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )
        return

    if not channel.topic or not channel.topic.startswith(
        "ticket:"
    ):
        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔒 Closing ticket..."
    )

    await asyncio.sleep(2)

    try:
        await channel.delete(
            reason=f"Ticket closed by {interaction.user}"
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to delete this ticket.",
            ephemeral=True
        )


# =========================
#         END PART 7
# =========================
# =========================
#        START PART 8
# =========================

# =========================
#      SHOWCASE SYSTEM
# =========================

def get_showcase_settings(guild_id):
    settings = get_guild_config(guild_id)

    if "showcase" not in settings:
        settings["showcase"] = {
            "enabled": False,
            "showcase_channel": None,
            "judge_channel": None,
            "judge_role": None,
            "message": (
                "🎬 Submit your TikTok below!"
            )
        }

    return settings


# =========================
#       TIKTOK MODAL
# =========================

class TikTokModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Submit a TikTok"
        )

        self.link = discord.ui.TextInput(
            label="TikTok URL",
            placeholder="https://www.tiktok.com/@user/video/...",
            required=True,
            max_length=500
        )

        self.add_item(self.link)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True
            )
            return

        settings = get_showcase_settings(
            guild.id
        )

        if not settings["showcase"].get(
            "enabled",
            False
        ):
            await interaction.response.send_message(
                "❌ TikTok showcase is currently disabled.",
                ephemeral=True
            )
            return

        url = extract_tiktok_link(
            self.link.value
        )

        if not url:
            await interaction.response.send_message(
                "❌ Please enter a valid TikTok link.",
                ephemeral=True
            )
            return

        judge_channel_id = settings["showcase"].get(
            "judge_channel"
        )

        judge_role_id = settings["showcase"].get(
            "judge_role"
        )

        if not judge_channel_id:
            await interaction.response.send_message(
                "❌ The judge channel has not been configured.",
                ephemeral=True
            )
            return

        judge_channel = guild.get_channel(
            int(judge_channel_id)
        )

        if not isinstance(
            judge_channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ The judge channel is invalid.",
                ephemeral=True
            )
            return

        mention = ""

        if judge_role_id:
            role = guild.get_role(
                int(judge_role_id)
            )

            if role:
                mention = role.mention

        embed = discord.Embed(
            title="🎬 New TikTok Submission",
            description=(
                f"👤 **User:** {interaction.user.mention}\n\n"
                f"🔗 **TikTok:** {url}"
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text=f"Submitted in {guild.name}"
        )

        try:
            await judge_channel.send(
                content=mention,
                embed=embed
            )

            await interaction.response.send_message(
                "✅ Your TikTok was submitted!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I cannot send messages in the judge channel.",
                ephemeral=True
            )


# =========================
#      SHOWCASE BUTTON
# =========================

class ShowcaseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Submit TikTok",
        emoji="🎬",
        style=discord.ButtonStyle.primary,
        custom_id="security_showcase_submit"
    )
    async def submit_tiktok(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            TikTokModal()
        )


# =========================
#      SHOWCASE GROUP
# =========================

showcase_group = app_commands.Group(
    name="showcase",
    description="TikTok showcase commands."
)

bot.tree.add_command(
    showcase_group
)


# =========================
#      SHOWCASE SETUP
# =========================

@showcase_group.command(
    name="setup",
    description="Configure TikTok showcase."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_setup(
    interaction: discord.Interaction,
    showcase_channel: discord.TextChannel,
    judge_channel: discord.TextChannel,
    judge_role: discord.Role
):

    settings = get_showcase_settings(
        interaction.guild.id
    )

    settings["showcase"]["showcase_channel"] = (
        showcase_channel.id
    )

    settings["showcase"]["judge_channel"] = (
        judge_channel.id
    )

    settings["showcase"]["judge_role"] = (
        judge_role.id
    )

    save_config()

    await interaction.response.send_message(
        "✅ **TikTok showcase configured!**\n\n"
        f"🎬 Showcase: {showcase_channel.mention}\n"
        f"⚖️ Judge channel: {judge_channel.mention}\n"
        f"👮 Judge role: {judge_role.mention}",
        ephemeral=True
    )


# =========================
#       SHOWCASE ON
# =========================

@showcase_group.command(
    name="on",
    description="Enable TikTok showcase."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_on(
    interaction: discord.Interaction
):

    settings = get_showcase_settings(
        interaction.guild.id
    )

    if not settings["showcase"].get(
        "showcase_channel"
    ):
        await interaction.response.send_message(
            "❌ Run `/showcase setup` first.",
            ephemeral=True
        )
        return

    settings["showcase"]["enabled"] = True

    save_config()

    await interaction.response.send_message(
        "🟢 TikTok showcase is now **ON**.",
        ephemeral=True
    )


# =========================
#       SHOWCASE OFF
# =========================

@showcase_group.command(
    name="off",
    description="Disable TikTok showcase."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_off(
    interaction: discord.Interaction
):

    settings = get_showcase_settings(
        interaction.guild.id
    )

    settings["showcase"]["enabled"] = False

    save_config()

    await interaction.response.send_message(
        "🔴 TikTok showcase is now **OFF**.",
        ephemeral=True
    )


# =========================
#     SHOWCASE MESSAGE
# =========================

@showcase_group.command(
    name="message",
    description="Set the showcase panel message."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_message(
    interaction: discord.Interaction,
    text: str
):

    settings = get_showcase_settings(
        interaction.guild.id
    )

    settings["showcase"]["message"] = text

    save_config()

    await interaction.response.send_message(
        "✅ Showcase message updated.",
        ephemeral=True
    )


# =========================
#      SHOWCASE PANEL
# =========================

@showcase_group.command(
    name="panel",
    description="Send the TikTok submission panel."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def showcase_panel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    settings = get_showcase_settings(
        interaction.guild.id
    )

    if not settings["showcase"].get(
        "showcase_channel"
    ):
        await interaction.response.send_message(
            "❌ Run `/showcase setup` first.",
            ephemeral=True
        )
        return

    message = settings["showcase"].get(
        "message",
        "🎬 Submit your TikTok below!"
    )

    embed = discord.Embed(
        title="🎬 TikTok Showcase",
        description=message,
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="How it works",
        value=(
            "Click **Submit TikTok** and send "
            "your TikTok link.\n\n"
            "Your submission will be privately "
            "forwarded to the judges."
        ),
        inline=False
    )

    embed.set_footer(
        text=f"{interaction.guild.name} • SECURITY"
    )

    try:
        await channel.send(
            embed=embed,
            view=ShowcaseView()
        )

        await interaction.response.send_message(
            f"✅ Showcase panel sent to {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I cannot send messages in that channel.",
            ephemeral=True
        )


# =========================
#        HELP COMMAND
# =========================

@bot.tree.command(
    name="help",
    description="Show SECURITY commands."
)
async def help_command(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🛡️ SECURITY Commands",
        description="Here are the main SECURITY commands.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🛡️ Verification",
        value=(
            "`/verifysetup`\n"
            "`/verify-message`\n"
            "`/verify-panel`\n"
            "`/verify`"
        ),
        inline=False
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
        name="🔨 Moderation",
        value=(
            "`/kick` `/ban` `/timeout`\n"
            "`/untimeout` `/addrole` `/removerole`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Cleaner",
        value=(
            "`/clearuser` `/clearbots`\n"
            "`/clearlinks` `/clearinvites`\n"
            "`/clearchannel` `/slowmode`\n"
            "`/lock` `/unlock`"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 Levels",
        value=(
            "`/rank` `/level` `/leaderboard`\n"
            "`/setlevelchannel` `/setlevelmessage`\n"
            "`/togglelevels` `/setlevel`\n"
            "`/setxp` `/resetxp`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "`/ticket setup`\n"
            "`/ticket panel`\n"
            "`/ticket close`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎬 TikTok",
        value=(
            "`/showcase setup`\n"
            "`/showcase on` `/showcase off`\n"
            "`/showcase message`\n"
            "`/showcase panel`"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Utility",
        value=(
            "`/ping` `/serverinfo` `/userinfo`\n"
            "`/avatar` `/servericon` `/botinfo`\n"
            "`/say` `/announce` `/wipe`"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================
#       ONE ON MESSAGE
# =========================

@bot.event
async def on_message(
    message: discord.Message
):

    if message.author.bot:
        return

    if message.guild is None:
        return

    # =====================
    #       LEVELS
    # =====================

    settings = get_level_data(
        message.guild.id
    )

    levels_enabled = settings["levels"].get(
        "enabled",
        True
    )

    if levels_enabled:

        # Small random XP reward
        xp_amount = random.randint(
            10,
            20
        )

        data, old_level, new_level = add_xp(
            message.guild.id,
            message.author.id,
            xp_amount
        )

        if new_level > old_level:

            level_channel_id = settings["levels"].get(
                "channel"
            )

            if level_channel_id:
                level_channel = message.guild.get_channel(
                    int(level_channel_id)
                )
            else:
                level_channel = message.channel

            if isinstance(
                level_channel,
                discord.TextChannel
            ):

                level_message = settings["levels"].get(
                    "message",
                    "🎉 {user} reached **Level {level}**!"
                )

                level_message = (
                    level_message
                    .replace(
                        "{user}",
                        message.author.mention
                    )
                    .replace(
                        "{username}",
                        message.author.name
                    )
                    .replace(
                        "{server}",
                        message.guild.name
                    )
                    .replace(
                        "{level}",
                        str(new_level)
                    )
                    .replace(
                        "{count}",
                        str(
                            message.guild.member_count or 0
                        )
                    )
                )

                try:
                    await level_channel.send(
                        level_message
                    )
                except discord.HTTPException:
                    pass

    # =====================
    #      TIKTOK LINKS
    # =====================

    showcase = get_showcase_settings(
        message.guild.id
    )

    showcase_data = showcase["showcase"]

    if showcase_data.get(
        "enabled",
        False
    ):

        url = extract_tiktok_link(
            message.content
        )

        showcase_channel_id = (
            showcase_data.get(
                "showcase_channel"
            )
        )

        judge_channel_id = (
            showcase_data.get(
                "judge_channel"
            )
        )

        judge_role_id = (
            showcase_data.get(
                "judge_role"
            )
        )

        if (
            url
            and showcase_channel_id
            and judge_channel_id
            and message.channel.id
            == int(showcase_channel_id)
        ):

            judge_channel = message.guild.get_channel(
                int(judge_channel_id)
            )

            if isinstance(
                judge_channel,
                discord.TextChannel
            ):

                role_mention = ""

                if judge_role_id:
                    role = message.guild.get_role(
                        int(judge_role_id)
                    )

                    if role:
                        role_mention = role.mention

                embed = discord.Embed(
                    title="🎬 New TikTok Submission",
                    description=(
                        f"👤 **Submitted by:** "
                        f"{message.author.mention}\n\n"
                        f"🔗 **TikTok:** {url}"
                    ),
                    color=discord.Color.blurple()
                )

                embed.set_footer(
                    text=f"Submitted in {message.guild.name}"
                )

                try:
                    await judge_channel.send(
                        content=role_mention,
                        embed=embed
                    )
                except discord.HTTPException:
                    pass

    await bot.process_commands(
        message
    )


# =========================
#        ONE ON READY
# =========================

@bot.event
async def on_ready():

    print(
        f"✅ SECURITY is online as "
        f"{bot.user}."
    )

    print(
        f"🌐 Connected to "
        f"{len(bot.guilds)} server(s)."
    )


# =========================
#   REGISTER PERSISTENT VIEWS
# =========================

bot.add_view(
    TicketCreateView()
)

bot.add_view(
    TicketCloseView()
)

bot.add_view(
    ShowcaseView()
)


# =========================
#        START BOT
# =========================

bot.run(TOKEN)

# =========================
#         END PART 8
# =========================
