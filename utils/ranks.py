# utils/ranks.py
import discord
import database

# --- Configuration ---
# The ranks are ordered from highest point requirement to lowest.
# This is crucial for the logic to work correctly.
# The bot will find the first rank the user qualifies for and assign that one.
RANKS = [
    {"points": 10000, "name": "Peak Master"},
    {"points": 4000,  "name": "Elder"},
    {"points": 1500,  "name": "Elite Disciple"},
    {"points": 500,   "name": "Core Disciple"},
    {"points": 150,   "name": "Inner Disciple"},
    {"points": 0,     "name": "Outer Disciple"},
]

# The channel where rank-up announcements will be posted.
RANK_UP_CHANNEL_NAME = "rank-ups"


async def check_and_update_rank(interaction: discord.Interaction, member: discord.Member):
    """
    Checks a member's total points and updates their rank roles accordingly.
    - Removes old rank roles.
    - Adds the new, correct rank role.
    - Announces the promotion in a dedicated channel.
    """
    if member.bot:
        return

    guild = interaction.guild
    total_points = database.get_user_points(member.id, guild.id)

    # Determine the correct rank for the user based on their points
    correct_rank_name = None
    for rank in RANKS:
        if total_points >= rank["points"]:
            correct_rank_name = rank["name"]
            break

    if not correct_rank_name:
        # This should theoretically not happen if the ranks are configured correctly
        print(f"Error: Could not determine a rank for {member.display_name} with {total_points} points.")
        return

    # Get the discord.Role object for the correct rank
    correct_role = discord.utils.get(guild.roles, name=correct_rank_name)
    if not correct_role:
        print(f"Error: The role '{correct_rank_name}' was not found in the server.")
        return

    # Get all possible rank roles from the server to check against
    all_rank_role_names = [r["name"] for r in RANKS]
    member_rank_roles = [role for role in member.roles if role.name in all_rank_role_names]

    # Check if the user already has the correct role and no others
    has_correct_role = correct_role in member_rank_roles
    has_incorrect_roles = len(member_rank_roles) > 1 or not has_correct_role

    if has_correct_role and not has_incorrect_roles:
        # User is already set up correctly, no changes needed.
        return

    # --- Time to update roles ---
    try:
        # Remove any old rank roles
        roles_to_remove = [role for role in member_rank_roles if role.id != correct_role.id]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Rank update")

        # Add the new, correct role if they don't have it
        if not has_correct_role:
            await member.add_roles(correct_role, reason="Rank promotion")
            print(f"Promoted {member.display_name} to {correct_rank_name}")
            
            # Announce the promotion
            announcement_channel = discord.utils.get(guild.text_channels, name=RANK_UP_CHANNEL_NAME)
            if announcement_channel:
                embed = discord.Embed(
                    title="🎉 Rank Promotion! 🎉",
                    color=correct_role.color,
                    description=f"Congratulations {member.mention}, you have ascended to the rank of **{correct_rank_name}**!"
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"Total Contribution Points: {total_points}")
                await announcement_channel.send(embed=embed)
            else:
                print(f"Warning: Announcement channel '#{RANK_UP_CHANNEL_NAME}' not found.")

    except discord.Forbidden:
        print(f"Error: Bot lacks permissions to manage roles for {member.display_name}. Ensure the bot's role is above the rank roles.")
    except Exception as e:
        print(f"An unexpected error occurred during rank update for {member.display_name}: {e}")
