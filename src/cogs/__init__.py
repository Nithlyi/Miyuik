"""
Moderation commands module
""" 

import os
from discord.ext import commands

async def load_cogs(bot: commands.Bot):
    """Load all cogs from the cogs directory and its subdirectories"""
    for root, dirs, files in os.walk("./src/cogs"):
        for filename in files:
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    # Convert path to module path
                    relative_path = os.path.relpath(os.path.join(root, filename[:-3]), ".")
                    module_path = relative_path.replace("/", ".").replace("\\", ".")
                    print(f"Attempting to load cog: {module_path}")
                    await bot.load_extension(module_path)
                    print(f"Loaded cog: {module_path}")
                except commands.ExtensionNotFound as e:
                    print(f"Failed to load cog {module_path}: Extension not found. {e}")
                except Exception as e:
                    print(f"Failed to load cog {module_path}: An unexpected error occurred during loading.")
                    import traceback
                    traceback.print_exc()