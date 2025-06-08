import discord
from discord.ext import commands
from discord import app_commands
import sqlite3  # Import SQLite
import time
from datetime import datetime
from typing import Dict, Any, Set
import asyncio

class History(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_file = "data/moderation.db"  # Define o arquivo do banco de dados
        self.conn = sqlite3.connect(self.db_file) # Conecta ao banco
        self.cursor = self.conn.cursor() # Cria um cursor
        self.create_table() # Chama a função para criar a tabela
    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS moderation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                timestamp INTEGER
            )
        """)
        self.conn.commit()
    def log_action(self, user_id: int, moderator_id: int, action: str, reason: str):
        timestamp = int(time.time())
        self.cursor.execute("INSERT INTO moderation_log (user_id, moderator_id, action, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
                            (user_id, moderator_id, action, reason, timestamp))
        self.conn.commit()

    @app_commands.command(name="history", description="Mostra o histórico de moderação de um usuário")
    @app_commands.describe(member="Membro para ver o histórico")
    async def history(self, interaction: discord.Interaction, member: discord.Member):
        user_id = member.id

        # Busca o histórico do usuário no banco de dados
        self.cursor.execute("SELECT * FROM moderation_log WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        history_data = self.cursor.fetchall()

        if not history_data:
            await interaction.response.send_message(f"Não há histórico de moderação para {member.display_name}.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Histórico de Moderação de {member.display_name}",
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)

        for entry in history_data:
            action_id, user_id, moderator_id, action, reason, timestamp = entry
            moderator = self.bot.get_user(moderator_id)
            moderator_name = moderator.display_name if moderator else "Desconhecido"
            timestamp_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

            embed.add_field(
                name=f"#{action_id} - {action.capitalize()} em {timestamp_str}",
                value=f"**Moderador:** {moderator_name}\n**Razão:** {reason}",
                inline=False
            )

        embed.set_footer(text=f"Histórico de moderação de {member.display_name}", icon_url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(History(bot))