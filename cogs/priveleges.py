# cogs/privileges.py
import discord
from discord import app_commands
from discord.ext import commands
import database
from utils import ranks as rank_utils # Import our new rank handler

# --- Configuration ---
SUGGESTION_CHANNEL_NAME = "suggestions"
PROPOSAL_CHANNEL_NAME = "contribution-board"

# Define the roles that have access to each privilege
INNER_DISCIPLE_RANKS = ["Inner Disciple", "Core Disciple", "Elite Disciple", "Elder", "Peak Master"]
ELDER_RANKS = ["Elder", "Peak Master"]
PROTEGE_TARGET_RANKS = ["Inner Disciple", "Core Disciple"]
PROTEGE_BONUS_POINTS = 300


class PrivilegesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="second", description="Boost a suggestion's visibility in #suggestions.")
    @app_commands.checks.has_any_role(*INNER_DISCIPLE_RANKS)
    async def second_suggestion(self, interaction: discord.Interaction):
        """Allows Inner Disciples and above to 'second' a suggestion."""
        channel = interaction.channel
        
        # Check if the command is used in a thread within the correct channel
        if not isinstance(channel, discord.Thread) or channel.parent.name != SUGGESTION_CHANNEL_NAME:
            await interaction.response.send_message(
                f"This command can only be used inside a suggestion thread within `#{SUGGESTION_CHANNEL_NAME}`.",
                ephemeral=True
            )
            return
            
        # Add a reaction to the thread's starting message to signify it's been "seconded"
        try:
            starting_message = await channel.fetch_message(channel.id)
            await starting_message.add_reaction("⭐") # Using a star to mark it
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} has seconded this suggestion, boosting its visibility!",
                allowed_mentions=discord.AllowedMentions.none()
            )
        except discord.NotFound:
            await interaction.response.send_message("Could not find the starting message of this thread.", ephemeral=True)
        except discord.Forbidden:
             await interaction.response.send_message("I don't have permission to add reactions here.", ephemeral=True)

    @app_commands.command(name="propose", description="Propose a new mission for the contribution board.")
    @app_commands.describe(title="The title of your proposed mission.", description="A detailed description of the mission.")
    @app_commands.checks.has_any_role(*ELDER_RANKS)
    async def propose_mission(self, interaction: discord.Interaction, title: str, description: str):
        """Allows Elders and above to formally propose missions."""
        proposal_channel = discord.utils.get(interaction.guild.text_channels, name=PROPOSAL_CHANNEL_NAME)
        if not proposal_channel:
            await interaction.response.send_message(
                f"Error: The `#{PROPOSAL_CHANNEL_NAME}` channel was not found. Please contact an admin.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📜 Mission Proposal: {title}",
            description=description,
            color=discord.Color.dark_gold()
        )
        embed.set_author(name=f"Proposed by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="This proposal is pending developer approval.")

        try:
            await proposal_channel.send(embed=embed)
            await interaction.response.send_message("Your mission proposal has been submitted for review! Thank you.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                f"Error: I don't have permissions to send messages in `#{PROPOSAL_CHANNEL_NAME}`.",
                ephemeral=True
            )

    @app_commands.command(name="protege", description="Recognize a rising talent as your Protégé.")
    @app_commands.describe(member="The Inner or Core Disciple you wish to recognize.")
    @app_commands.checks.has_any_role(*ELDER_RANKS)
    async def proclaim_protege(self, interaction: discord.Interaction, member: discord.Member):
        """Allows an Elder to grant a one-time point bonus to a disciple."""
        
        # --- Pre-computation Checks ---
        guild_id = interaction.guild.id
        elder = interaction.user
        
        # Check if the elder has already used this ability
        if database.has_proclaimed_protege(elder.id, guild_id):
            await interaction.response.send_message("You have already proclaimed a Protégé. This honor can only be bestowed once.", ephemeral=True)
            return
            
        if member.id == elder.id:
            await interaction.response.send_message("You cannot name yourself as your own Protégé.", ephemeral=True)
            return
        
        if member.bot:
            await interaction.response.send_message("You cannot name a bot as your Protégé.", ephemeral=True)
            return

        # Check if the target member has one of the required roles
        member_role_names = [role.name for role in member.roles]
        if not any(role_name in PROTEGE_TARGET_RANKS for role_name in member_role_names):
            await interaction.response.send_message(f"You can only name an `Inner Disciple` or `Core Disciple` as your Protégé.", ephemeral=True)
            return
        
        # --- Action ---
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Grant points and log the action
        reason = f"Proclaimed as Protégé by {elder.display_name}."
        database.add_points(member.id, guild_id, PROTEGE_BONUS_POINTS, reason)
        database.log_protege(elder.id, member.id, guild_id)

        # Announce it publicly
        embed = discord.Embed(
            title="📜 A Lineage Proclamation!",
            color=discord.Color.from_rgb(255, 215, 0), # Gold
            description=f"{elder.mention} has recognized a rising talent!\n\n"
                        f"**{member.mention}** is now their Protégé, a testament to their dedication and potential."
        )
        embed.add_field(name="Blessing of the Elder", value=f"As a sign of this bond, **{member.display_name}** has been granted **{PROTEGE_BONUS_POINTS} Contribution Points!**")
        embed.set_footer(text="May this new bond strengthen our community.")
        
        # We can re-use the proposal channel or make a new one like #lineage-announcements
        announcement_channel = discord.utils.get(interaction.guild.text_channels, name="rank-ups") or interaction.channel
        await announcement_channel.send(embed=embed)
        
        # Check for the Protégé's potential rank up
        await rank_utils.check_and_update_rank(interaction, member)

        await interaction.followup.send("You have successfully named your Protégé!", ephemeral=True)


    @second_suggestion.error
    @propose_mission.error
    @proclaim_protege.error
    async def privilege_error_handler(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(
                "You do not have the required rank to use this command.",
                ephemeral=True
            )
        else:
            print(f"An unhandled error occurred in PrivilegesCog: {error}")
            await interaction.response.send_message(
                "An unexpected error occurred. Please try again later.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(PrivilegesCog(bot))
