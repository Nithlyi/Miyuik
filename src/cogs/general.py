import discord
from discord.ext import commands
from discord import app_commands
import platform
import time
from datetime import datetime

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
        self.afk_users = {} # Dictionary to store AFK users: {user_id: {"status": "...", "time": timestamp}}

    @app_commands.command(name="sync", description="Atualiza os comandos slash do bot")
    async def sync(self, interaction: discord.Interaction):
        try:
            # Verifica se o usuário é o dono do bot
            if interaction.user.id not in self.bot.owner_ids: # Using owner_ids list is safer
                embed = discord.Embed(
                    title="❌ Erro",
                    description="Apenas o dono do bot pode usar este comando!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)

            # Sincroniza os comandos globalmente
            synced = await self.bot.tree.sync()

            # Sincroniza os comandos no servidor atual
            guild_synced = []
            if interaction.guild: # Only sync to guild if command is used in a guild
                 guild_synced = await self.bot.tree.sync(guild=interaction.guild)

            embed = discord.Embed(
                title="🔄 Comandos Atualizados",
                description=f"**Comandos Globais:** {len(synced)}\n**Comandos do Servidor:** {len(guild_synced)}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Erro",
                description=f"Ocorreu um erro ao sincronizar os comandos:\n```{str(e)}```",
                color=discord.Color.red()
            )
            # Always use followup.send after defer, even if defer might have failed internally
            await interaction.followup.send(embed=error_embed, ephemeral=True)


    @app_commands.command(name="ping", description="Mostra a latência do bot")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! Latência: {latency}ms")

    @app_commands.command(name="info", description="Mostra informações detalhadas sobre o bot")
    async def info(self, interaction: discord.Interaction):
        # Calcula o tempo de atividade
        uptime = int(time.time() - self.start_time)
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60

        # Cria o embed principal
        embed = discord.Embed(
            title="Informações do Bot",
            description="Um bot Discord criado com discord.py",
            color=discord.Color.default()  # Cor preta
        )

        # Adiciona o avatar do bot
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # Informações do Bot
        embed.add_field(
            name="📊 Estatísticas",
            value=f"**Servidores:** {len(self.bot.guilds)}\n"
                  f"**Usuários:** {sum(g.member_count for g in self.bot.guilds)}\n"
                  f"**Comandos:** {len(self.bot.tree.get_commands())}",
            inline=True
        )

        # Informações Técnicas
        embed.add_field(
            name="⚙️ Tecnologias",
            value=f"**Python:** {platform.python_version()}\n"
                  f"**Discord.py:** {discord.__version__}\n"
                  f"**Sistema:** {platform.system()} {platform.release()}",
            inline=True
        )

        # Tempo de Atividade
        embed.add_field(
            name="⏰ Tempo de Atividade",
            value=f"**Dias:** {days}\n"
                  f"**Horas:** {hours}\n"
                  f"**Minutos:** {minutes}\n"
                  f"**Segundos:** {seconds}",
            inline=True
        )

        # Lista de Servidores
        server_list = "\n".join([f"• {g.name} ({g.member_count} membros)" for g in sorted(self.bot.guilds, key=lambda x: x.member_count, reverse=True)[:5]])
        embed.add_field(
            name="Servidores",
            value=server_list if server_list else "Nenhum servidor",
            inline=False
        )

        # Créditos
        embed.add_field(
            name="Desenvolvedor",
            value="Bot criado por lonelyyi.",
            inline=False
        )

        # Footer com ID do bot
        embed.set_footer(text=f"ID do Bot: {self.bot.user.id}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite", description="Gera um convite para o bot")
    async def invite(self, interaction: discord.Interaction):
        """Gera um convite para o bot"""
        if interaction.user.id not in self.bot.owner_ids: # Using owner_ids list is safer
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando!",
                ephemeral=True
            )
            return

        try:
            # Gerar link de convite com permissões necessárias
            invite_url = discord.utils.oauth_url(
                self.bot.user.id,
                permissions=discord.Permissions(
                    administrator=True  # Permissões administrativas para todas as funcionalidades
                )
            )

            embed = discord.Embed(
                title="📨 Convite do Bot",
                description="Use o link abaixo para adicionar o bot ao seu servidor:",
                color=discord.Color.default()
            )
            embed.add_field(
                name="Link de Convite",
                value=f"[Clique aqui]({invite_url})",
                inline=False
            )
            embed.add_field(
                name="Permissões",
                value="O bot requer permissões administrativas para funcionar corretamente.",
                inline=False
            )
            embed.set_footer(text=f"Solicitado por {interaction.user.name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao gerar convite: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="afk", description="Define seu status AFK")
    @app_commands.describe(status="Sua mensagem de status (opcional)")
    async def afk(self, interaction: discord.Interaction, status: str = "Estou AFK."):
        user_id = interaction.user.id
        if user_id in self.afk_users:
            await interaction.response.send_message("Você já está AFK!", ephemeral=True)
            return

        self.afk_users[user_id] = {"status": status, "time": datetime.now().timestamp()}
        await interaction.response.send_message(f"Você está agora AFK. Status: **{status}**", ephemeral=False) # Send publicly

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = message.author.id
        if user_id in self.afk_users:
            del self.afk_users[user_id]
            # Use a temporary embed for the welcome back message if preferred,
            # but a simple ephemeral message is often less intrusive.
            # For now, keep the simple message.
            try: # Add try-except for the delete_after
                 await message.channel.send(f"Bem-vindo de volta, {message.author.mention}! Seu status AFK foi removido.", delete_after=10)
            except discord.errors.NotFound:
                 pass # Message might have been deleted before the bot could delete the response


        for mention in message.mentions:
            # Check if the mentioned user is AFK and is not the author of the message
            if mention.id in self.afk_users and mention.id != message.author.id:
                afk_status = self.afk_users[mention.id]["status"]
                afk_time = datetime.fromtimestamp(self.afk_users[mention.id]["time"])
                time_diff = datetime.now() - afk_time

                # Format time difference nicely
                seconds = time_diff.total_seconds()
                if seconds < 60:
                    time_ago = f"{int(seconds)}s atrás"
                elif seconds < 3600:
                    time_ago = f"{int(seconds//60)}m atrás"
                elif seconds < 86400:
                    time_ago = f"{int(seconds//3600)}h {int((seconds%3600)//60)}m atrás"
                else:
                    time_ago = f"{int(seconds//86400)}d {int((seconds%86400)//3600)}h atrás"

                # Create and send the embed
                embed = discord.Embed(
                    title=f"📌 {mention.display_name} está AFK",
                    description=f"**Status:** {afk_status}\n**Desde:** {time_ago}",
                    color=discord.Color.orange() # Using orange color
                )
                # Set the mentioned user's avatar as the thumbnail
                if mention.display_avatar:
                    embed.set_thumbnail(url=mention.display_avatar.url)

                await message.channel.send(embed=embed)


async def setup(bot: commands.Bot):
    # Ensure bot.owner_ids is set up in main.py, otherwise this might cause issues
    # For now, assuming it's a list or set of IDs
    if not hasattr(bot, 'owner_ids'):
        print("Warning: bot.owner_ids not found. Sync and Invite commands might not work as intended.")
        # Attempt to load owner_ids from environment or a config if not set
        # For now, default to an empty list or a known single ID if available
        # Assuming you've added your ID to main.py already
        # bot.owner_ids = [] # Or load from config/env

    await bot.add_cog(General(bot))
