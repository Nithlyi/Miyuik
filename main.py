import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import webserver

print("Loading environment variables...")
load_dotenv()
print("Environment variables loaded.")

print("Creating bot instance...")
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
print("Bot instance created.")
bot.owner_ids = {1243889655087370270}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    webserver.start_web_server()
    await bot.load_extension('src.cogs.general')
    await bot.load_extension('src.cogs.moderation')
    await bot.load_extension('src.cogs.utility')
    await bot.load_extension('src.cogs.giveaway')
    await bot.load_extension('src.cogs.tickets')
    await bot.load_extension('src.cogs.welcome')
    await bot.load_extension('src.cogs.autorole')
    await bot.load_extension('src.cogs.levels')
    await bot.load_extension('src.cogs.protection')
    await bot.load_extension('src.cogs.backup')
    await bot.load_extension('src.cogs.git')
    await bot.load_extension('src.cogs.embed_creator')
    await bot.load_extension('src.cogs.moderation_panel')
    await bot.load_extension('src.cogs.support')
    await bot.load_extension('src.cogs.history')
    await bot.load_extension('src.cogs.interactions')

    print(f"Total Cogs Loaded: {len(bot.cogs)}")
    print(f"Total Commands Loaded: {len(bot.commands)}")

    try:
        synced = await bot.tree.sync()
        print(f"Comandos Globais Sincronizados (Inicialização): {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos na inicialização: {e}")

print("Running the bot...")
try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except Exception as e:
    print(f"Erro ao rodar o bot: {e}")
print("Bot finished running.")
