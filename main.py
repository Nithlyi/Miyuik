import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from src.cogs import load_cogs
from src.handlers import setup_handlers

# Load environment variables
load_dotenv()

# Bot configuration
class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Necessário para comandos de moderação
        super().__init__(command_prefix="!", intents=intents)
        self.owner_id = 1243889655087370270  # ID do dono do bot
        
    async def setup_hook(self):
        print("Loading cogs...")
        # Load all cogs
        await load_cogs(self)
        print("Cogs loaded successfully!")
        
        print("Setting up handlers...")
        # Setup handlers
        setup_handlers(self)
        print("Handlers setup complete!")
        
        print("Syncing commands with Discord...")
        try:
            # Sync commands with Discord
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Error syncing commands: {str(e)}")
        print("Setup complete!")
        
    async def on_ready(self):
        print(f"Bot is ready! Logged in as {self.user}")
        print(f"Bot ID: {self.user.id}")
        print("------")

def main():
    bot = Bot()
    try:
        bot.run(os.getenv("DISCORD_TOKEN"))
    except Exception as e:
        print(f"Error starting bot: {str(e)}")

if __name__ == "__main__":
    main() 