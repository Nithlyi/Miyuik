import discord
from discord import app_commands
from discord.ext import commands
import platform
import psutil
import time
from datetime import datetime

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="Mostra a latência do bot e informações do sistema")
    async def status(self, interaction: discord.Interaction):
        """Mostra a latência do bot e informações do sistema"""
        # Cria o embed
        embed = discord.Embed(
            title="🏓 Status do Bot",
            color=discord.Color.default(),  # Cor preta
            timestamp=datetime.now()
        )
        
        # Adiciona o avatar do bot
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        # Calcula a latência
        start_time = time.time()
        await interaction.response.defer()
        end_time = time.time()
        
        # Latência do bot
        bot_latency = round((end_time - start_time) * 1000)
        
        # Latência da API do Discord
        api_latency = round(self.bot.latency * 1000)
        
        # Informações do sistema
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Adiciona os campos ao embed
        embed.add_field(
            name="📊 Latência",
            value=f"```\nBot: {bot_latency}ms\nAPI: {api_latency}ms```",
            inline=False
        )
        
        embed.add_field(
            name="💻 Sistema",
            value=f"```\nCPU: {cpu_percent}%\nRAM: {memory_percent}%\nPython: {platform.python_version()}```",
            inline=False
        )
        
        embed.add_field(
            name="🤖 Bot",
            value=f"```\nServidores: {len(self.bot.guilds)}\nUsuários: {sum(g.member_count for g in self.bot.guilds)}```",
            inline=False
        )
        
        # Adiciona o footer
        embed.set_footer(
            text=f"Solicitado por {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Envia o embed
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot)) 