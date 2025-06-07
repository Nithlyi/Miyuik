import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
import asyncio

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Bane um usuário do servidor")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(
        user="O usuário que será banido",
        reason="O motivo do banimento"
    )
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Nenhum motivo fornecido"):
        # Verifica se o usuário tem cargo superior
        if user.top_role >= interaction.user.top_role:
            embed = discord.Embed(
                title="❌ Erro",
                description="Você não pode banir alguém com cargo igual ou superior ao seu!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # Cria o embed de banimento
            embed = discord.Embed(
                title="🔨 Usuário Banido",
                description=f"**Usuário:** {user.mention}\n**Motivo:** {reason}\n**Banido por:** {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"ID do Usuário: {user.id}")
            
            # Executa o banimento
            await user.ban(reason=f"{reason} | Banido por {interaction.user}")
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erro",
                description="Não tenho permissão para banir este usuário!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="kick", description="Expulsa um usuário do servidor")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(
        user="O usuário que será expulso",
        reason="O motivo da expulsão"
    )
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Nenhum motivo fornecido"):
        # Verifica se o usuário tem cargo superior
        if user.top_role >= interaction.user.top_role:
            embed = discord.Embed(
                title="❌ Erro",
                description="Você não pode expulsar alguém com cargo igual ou superior ao seu!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # Cria o embed de expulsão
            embed = discord.Embed(
                title="👢 Usuário Expulso",
                description=f"**Usuário:** {user.mention}\n**Motivo:** {reason}\n**Expulso por:** {interaction.user.mention}",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"ID do Usuário: {user.id}")
            
            # Executa a expulsão
            await user.kick(reason=f"{reason} | Expulso por {interaction.user}")
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erro",
                description="Não tenho permissão para expulsar este usuário!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="tempmute", description="Silencia um usuário temporariamente")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        user="O usuário que será silenciado",
        duration="Duração do silenciamento (ex: 1h, 30m, 1d)",
        reason="O motivo do silenciamento"
    )
    async def tempmute(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "Nenhum motivo fornecido"):
        # Verifica se o usuário tem cargo superior
        if user.top_role >= interaction.user.top_role:
            embed = discord.Embed(
                title="❌ Erro",
                description="Você não pode silenciar alguém com cargo igual ou superior ao seu!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Converte a duração para segundos
        time_units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        
        try:
            time_value = int(duration[:-1])
            time_unit = duration[-1].lower()
            
            if time_unit not in time_units:
                raise ValueError
                
            duration_seconds = time_value * time_units[time_unit]
            
            # Verifica se a duração não excede o limite do Discord (28 dias)
            if duration_seconds > 2419200:
                embed = discord.Embed(
                    title="❌ Erro",
                    description="A duração máxima do silenciamento é 28 dias!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # Aplica o timeout
            await user.timeout(datetime.utcnow() + timedelta(seconds=duration_seconds), reason=reason)
            
            # Cria o embed de silenciamento
            embed = discord.Embed(
                title="🔇 Usuário Silenciado",
                description=f"**Usuário:** {user.mention}\n**Duração:** {duration}\n**Motivo:** {reason}\n**Silenciado por:** {interaction.user.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"ID do Usuário: {user.id}")
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            embed = discord.Embed(
                title="❌ Erro",
                description="Formato de duração inválido! Use: 30s, 5m, 1h, 1d",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erro",
                description="Não tenho permissão para silenciar este usuário!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="lock", description="Bloqueia um canal para que apenas administradores possam enviar mensagens")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Bloqueia um canal para que apenas administradores possam enviar mensagens"""
        channel = channel or interaction.channel
        
        try:
            # Configurar permissões para @everyone
            await channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
                reason=f"Canal bloqueado por {interaction.user}"
            )
            
            embed = discord.Embed(
                title="🔒 Canal Bloqueado",
                description=f"O canal {channel.mention} foi bloqueado com sucesso!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Bloqueado por",
                value=interaction.user.mention,
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para gerenciar canais!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao bloquear canal: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="unlock", description="Desbloqueia um canal permitindo que todos enviem mensagens")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Desbloqueia um canal permitindo que todos enviem mensagens"""
        channel = channel or interaction.channel
        
        try:
            # Restaurar permissões para @everyone
            await channel.set_permissions(
                interaction.guild.default_role,
                send_messages=True,
                reason=f"Canal desbloqueado por {interaction.user}"
            )
            
            embed = discord.Embed(
                title="🔓 Canal Desbloqueado",
                description=f"O canal {channel.mention} foi desbloqueado com sucesso!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Desbloqueado por",
                value=interaction.user.mention,
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para gerenciar canais!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao desbloquear canal: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="slowmode", description="Define o modo lento de um canal")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: int,
        channel: Optional[discord.TextChannel] = None
    ):
        """Define o modo lento de um canal"""
        channel = channel or interaction.channel
        
        if seconds < 0 or seconds > 21600:  # Discord limita a 6 horas (21600 segundos)
            await interaction.response.send_message(
                "❌ O tempo deve estar entre 0 e 21600 segundos (6 horas)!",
                ephemeral=True
            )
            return
        
        try:
            await channel.edit(slowmode_delay=seconds)
            
            embed = discord.Embed(
                title="⏱️ Modo Lento Configurado",
                description=f"O modo lento do canal {channel.mention} foi configurado!",
                color=discord.Color.blue()
            )
            
            if seconds == 0:
                embed.description = f"O modo lento do canal {channel.mention} foi desativado!"
            else:
                minutes, remaining_seconds = divmod(seconds, 60)
                hours, remaining_minutes = divmod(minutes, 60)
                
                time_str = ""
                if hours > 0:
                    time_str += f"{hours}h "
                if remaining_minutes > 0:
                    time_str += f"{remaining_minutes}m "
                if remaining_seconds > 0:
                    time_str += f"{remaining_seconds}s"
                
                embed.add_field(
                    name="Tempo de espera",
                    value=time_str.strip(),
                    inline=True
                )
            
            embed.add_field(
                name="Configurado por",
                value=interaction.user.mention,
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para gerenciar canais!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao configurar modo lento: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="clear", description="Limpa um número específico de mensagens no canal")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        """Limpa um número específico de mensagens no canal"""
        if amount <= 0 or amount > 100:
            await interaction.response.send_message(
                "❌ A quantidade deve estar entre 1 e 100 mensagens!",
                ephemeral=True
            )
            return

        try:
            # Defer a resposta para evitar timeout
            await interaction.response.defer(ephemeral=True)
            
            # Deletar as mensagens
            deleted = await interaction.channel.purge(limit=amount)
            
            embed = discord.Embed(
                title="🧹 Mensagens Limpas",
                description=f"Foram deletadas {len(deleted)} mensagens com sucesso!",
                color=discord.Color.default()
            )
            embed.add_field(
                name="Canal",
                value=interaction.channel.mention,
                inline=True
            )
            embed.add_field(
                name="Deletado por",
                value=interaction.user.mention,
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não tenho permissão para gerenciar mensagens!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao limpar mensagens: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="lockdown", description="Trava ou destrava todos os canais de texto do servidor")
    @app_commands.describe(
        action="Ação a ser realizada (lock/unlock)",
        reason="Motivo do lockdown (opcional)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Travar", value="lock"),
        app_commands.Choice(name="Destravar", value="unlock")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(
        self,
        interaction: discord.Interaction,
        action: str,
        reason: Optional[str] = None
    ):
        """Trava ou destrava todos os canais de texto do servidor"""
        await interaction.response.defer()

        # Verifica se o bot tem permissões necessárias
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Eu não tenho permissão para gerenciar canais!")
            return

        # Obtém todos os canais de texto do servidor
        text_channels = [c for c in interaction.guild.text_channels]
        
        # Prepara a mensagem de status
        status_message = await interaction.followup.send(
            f"🔄 {'Travando' if action == 'lock' else 'Destravando'} canais...\n"
            f"Progresso: 0/{len(text_channels)}"
        )

        # Contador de canais processados
        processed = 0
        failed = 0

        # Processa cada canal
        for channel in text_channels:
            try:
                # Atualiza as permissões do canal
                overwrite = channel.overwrites_for(interaction.guild.default_role)
                overwrite.send_messages = False if action == "lock" else None
                await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
                processed += 1
            except discord.Forbidden:
                failed += 1
            except Exception as e:
                failed += 1
                print(f"Erro ao processar canal {channel.name}: {str(e)}")

            # Atualiza a mensagem de status a cada 5 canais
            if processed % 5 == 0 or processed == len(text_channels):
                await status_message.edit(content=(
                    f"🔄 {'Travando' if action == 'lock' else 'Destravando'} canais...\n"
                    f"Progresso: {processed}/{len(text_channels)}\n"
                    f"Falhas: {failed}"
                ))

        # Mensagem final
        result_message = (
            f"✅ {'Lockdown' if action == 'lock' else 'Unlock'} concluído!\n"
            f"• Canais processados: {processed}\n"
            f"• Falhas: {failed}\n"
        )
        if reason:
            result_message += f"• Motivo: {reason}"

        await status_message.edit(content=result_message)

    @ban.error
    @kick.error
    @tempmute.error
    @lockdown.error
    async def moderation_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Erro",
                description="Você não tem permissão para usar este comando!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot)) 