# bot.py
import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
import database

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Set up intents
intents = discord.Intents.default()
intents.members = True # REQUIRED for the /giverole command to see role members

class CelestialBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # This is called when the bot is preparing to start
        print("Running setup hook...")
        
        # Initialize the database
        database.initialize_database()
        
        # Load the commands from the cogs
        await self.load_extension("cogs.points")
        await self.load_extension("cogs.privileges") # Load the new cog
        print("Cogs loaded.")

        # Sync slash commands with Discord.
        # This can take a minute, but only needs to run when commands change.
        await self.tree.sync()
        print("Command tree synced.")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

bot = CelestialBot()

# A simple health check for Railway deployment
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())