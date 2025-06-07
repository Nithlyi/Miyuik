import discord
from discord import app_commands
from discord.ext import commands
import platform
import time

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="sync", description="Atualiza os comandos slash do bot")
    async def sync(self, interaction: discord.Interaction):
        try:
            # Verifica se o usuário é o dono do bot
            if interaction.user.id != self.bot.owner_id:
                embed = discord.Embed(
                    title="❌ Erro",
                    description="Apenas o dono do bot pode usar este comando!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Responde imediatamente para evitar timeout
            await interaction.response.defer(ephemeral=True)

            # Sincroniza os comandos globalmente
            synced = await self.bot.tree.sync()
            
            # Sincroniza os comandos no servidor atual
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
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)

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
        if interaction.user.id != 1243889655087370270:
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

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot)) 