import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os

class ModerationPanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.warns_file = "data/warns.json"
        self.load_warns()

    def load_warns(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if os.path.exists(self.warns_file):
            with open(self.warns_file, "r") as f:
                self.warns = json.load(f)
        else:
            self.warns = {}
            self.save_warns()

    def save_warns(self):
        with open(self.warns_file, "w") as f:
            json.dump(self.warns, f, indent=4)

    class ModerationView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="Banir", style=discord.ButtonStyle.danger, emoji="🔨")
        async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = ModerationPanel.BanModal(self.cog)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Expulsar", style=discord.ButtonStyle.danger, emoji="👢")
        async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = ModerationPanel.KickModal(self.cog)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Silenciar", style=discord.ButtonStyle.primary, emoji="🔇")
        async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = ModerationPanel.MuteModal(self.cog)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Avisar", style=discord.ButtonStyle.secondary, emoji="⚠️")
        async def warn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = ModerationPanel.WarnModal(self.cog)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Limpar", style=discord.ButtonStyle.secondary, emoji="🧹")
        async def clear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = ModerationPanel.ClearModal(self.cog)
            await interaction.response.send_modal(modal)

    class BanModal(discord.ui.Modal, title="Banir Usuário"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog

            self.user_input = discord.ui.TextInput(
                label="ID do Usuário",
                placeholder="Digite o ID do usuário",
                required=True
            )
            self.add_item(self.user_input)

            self.reason_input = discord.ui.TextInput(
                label="Motivo",
                placeholder="Digite o motivo do banimento",
                required=True,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.reason_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                user_id = int(self.user_input.value)
                user = await self.cog.bot.fetch_user(user_id)
                
                if user.top_role >= interaction.user.top_role:
                    await interaction.response.send_message("Você não pode banir alguém com cargo igual ou superior ao seu!", ephemeral=True)
                    return

                await interaction.guild.ban(user, reason=f"{self.reason_input.value} | Banido por {interaction.user}")
                
                embed = discord.Embed(
                    title="🔨 Usuário Banido",
                    description=f"**Usuário:** {user.mention}\n**Motivo:** {self.reason_input.value}\n**Banido por:** {interaction.user.mention}",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"ID do Usuário: {user.id}")
                
                await interaction.response.send_message(embed=embed)
                
            except ValueError:
                await interaction.response.send_message("ID de usuário inválido!", ephemeral=True)
            except discord.NotFound:
                await interaction.response.send_message("Usuário não encontrado!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Não tenho permissão para banir este usuário!", ephemeral=True)

    class KickModal(discord.ui.Modal, title="Expulsar Usuário"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog

            self.user_input = discord.ui.TextInput(
                label="ID do Usuário",
                placeholder="Digite o ID do usuário",
                required=True
            )
            self.add_item(self.user_input)

            self.reason_input = discord.ui.TextInput(
                label="Motivo",
                placeholder="Digite o motivo da expulsão",
                required=True,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.reason_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                user_id = int(self.user_input.value)
                member = await interaction.guild.fetch_member(user_id)
                
                if member.top_role >= interaction.user.top_role:
                    await interaction.response.send_message("Você não pode expulsar alguém com cargo igual ou superior ao seu!", ephemeral=True)
                    return

                await member.kick(reason=f"{self.reason_input.value} | Expulso por {interaction.user}")
                
                embed = discord.Embed(
                    title="👢 Usuário Expulso",
                    description=f"**Usuário:** {member.mention}\n**Motivo:** {self.reason_input.value}\n**Expulso por:** {interaction.user.mention}",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"ID do Usuário: {member.id}")
                
                await interaction.response.send_message(embed=embed)
                
            except ValueError:
                await interaction.response.send_message("ID de usuário inválido!", ephemeral=True)
            except discord.NotFound:
                await interaction.response.send_message("Usuário não encontrado!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Não tenho permissão para expulsar este usuário!", ephemeral=True)

    class MuteModal(discord.ui.Modal, title="Silenciar Usuário"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog

            self.user_input = discord.ui.TextInput(
                label="ID do Usuário",
                placeholder="Digite o ID do usuário",
                required=True
            )
            self.add_item(self.user_input)

            self.duration_input = discord.ui.TextInput(
                label="Duração",
                placeholder="Ex: 1h, 30m, 1d",
                required=True
            )
            self.add_item(self.duration_input)

            self.reason_input = discord.ui.TextInput(
                label="Motivo",
                placeholder="Digite o motivo do silenciamento",
                required=True,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.reason_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                user_id = int(self.user_input.value)
                member = await interaction.guild.fetch_member(user_id)
                
                if member.top_role >= interaction.user.top_role:
                    await interaction.response.send_message("Você não pode silenciar alguém com cargo igual ou superior ao seu!", ephemeral=True)
                    return

                # Converte duração para segundos
                time_units = {
                    's': 1,
                    'm': 60,
                    'h': 3600,
                    'd': 86400
                }
                
                duration = self.duration_input.value
                time_value = int(duration[:-1])
                time_unit = duration[-1].lower()
                
                if time_unit not in time_units:
                    await interaction.response.send_message("Formato de duração inválido! Use: 30s, 5m, 1h, 1d", ephemeral=True)
                    return
                
                duration_seconds = time_value * time_units[time_unit]
                
                if duration_seconds > 2419200:  # 28 dias
                    await interaction.response.send_message("A duração máxima do silenciamento é 28 dias!", ephemeral=True)
                    return
                
                await member.timeout(datetime.utcnow() + timedelta(seconds=duration_seconds), reason=self.reason_input.value)
                
                embed = discord.Embed(
                    title="🔇 Usuário Silenciado",
                    description=f"**Usuário:** {member.mention}\n**Duração:** {duration}\n**Motivo:** {self.reason_input.value}\n**Silenciado por:** {interaction.user.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"ID do Usuário: {member.id}")
                
                await interaction.response.send_message(embed=embed)
                
            except ValueError:
                await interaction.response.send_message("ID de usuário inválido!", ephemeral=True)
            except discord.NotFound:
                await interaction.response.send_message("Usuário não encontrado!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Não tenho permissão para silenciar este usuário!", ephemeral=True)

    class WarnModal(discord.ui.Modal, title="Avisar Usuário"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog

            self.user_input = discord.ui.TextInput(
                label="ID do Usuário",
                placeholder="Digite o ID do usuário",
                required=True
            )
            self.add_item(self.user_input)

            self.reason_input = discord.ui.TextInput(
                label="Motivo",
                placeholder="Digite o motivo do aviso",
                required=True,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.reason_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                user_id = int(self.user_input.value)
                member = await interaction.guild.fetch_member(user_id)
                
                # Adiciona o aviso
                if str(member.id) not in self.cog.warns:
                    self.cog.warns[str(member.id)] = []
                
                self.cog.warns[str(member.id)].append({
                    "reason": self.reason_input.value,
                    "moderator": str(interaction.user.id),
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                self.cog.save_warns()
                
                embed = discord.Embed(
                    title="⚠️ Usuário Avisado",
                    description=f"**Usuário:** {member.mention}\n**Motivo:** {self.reason_input.value}\n**Avisado por:** {interaction.user.mention}",
                    color=discord.Color.yellow(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"ID do Usuário: {member.id}")
                
                await interaction.response.send_message(embed=embed)
                
            except ValueError:
                await interaction.response.send_message("ID de usuário inválido!", ephemeral=True)
            except discord.NotFound:
                await interaction.response.send_message("Usuário não encontrado!", ephemeral=True)

    class ClearModal(discord.ui.Modal, title="Limpar Mensagens"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog

            self.amount_input = discord.ui.TextInput(
                label="Quantidade",
                placeholder="Digite a quantidade de mensagens (1-100)",
                required=True
            )
            self.add_item(self.amount_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                amount = int(self.amount_input.value)
                if amount < 1 or amount > 100:
                    await interaction.response.send_message("A quantidade deve estar entre 1 e 100!", ephemeral=True)
                    return

                deleted = await interaction.channel.purge(limit=amount)
                
                embed = discord.Embed(
                    title="🧹 Mensagens Limpas",
                    description=f"**Quantidade:** {len(deleted)} mensagens\n**Canal:** {interaction.channel.mention}\n**Limpo por:** {interaction.user.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except ValueError:
                await interaction.response.send_message("Quantidade inválida!", ephemeral=True)

    @app_commands.command(name="modpanel", description="Abre o painel de moderação")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def modpanel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Painel de Moderação",
            description="Use os botões abaixo para moderar o servidor",
            color=discord.Color.default()
        )
        embed.add_field(
            name="Comandos Disponíveis",
            value="🔨 **Banir** - Bane um usuário do servidor\n"
                  "👢 **Expulsar** - Expulsa um usuário do servidor\n"
                  "🔇 **Silenciar** - Silencia um usuário temporariamente\n"
                  "⚠️ **Avisar** - Dá um aviso a um usuário\n"
                  "🧹 **Limpar** - Limpa mensagens do canal",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=self.ModerationView(self))

    @app_commands.command(name="warns", description="Mostra os avisos de um usuário")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warns(self, interaction: discord.Interaction, user: discord.Member):
        if str(user.id) not in self.warns or not self.warns[str(user.id)]:
            await interaction.response.send_message(f"{user.mention} não possui avisos!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"⚠️ Avisos de {user.name}",
            color=discord.Color.yellow(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        for i, warn in enumerate(self.warns[str(user.id)], 1):
            moderator = await self.bot.fetch_user(int(warn["moderator"]))
            timestamp = datetime.fromisoformat(warn["timestamp"])
            
            embed.add_field(
                name=f"Aviso #{i}",
                value=f"**Motivo:** {warn['reason']}\n"
                      f"**Moderador:** {moderator.mention}\n"
                      f"**Data:** <t:{int(timestamp.timestamp())}:R>",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clearwarns", description="Limpa os avisos de um usuário")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clearwarns(self, interaction: discord.Interaction, user: discord.Member):
        if str(user.id) not in self.warns:
            await interaction.response.send_message(f"{user.mention} não possui avisos!", ephemeral=True)
            return

        del self.warns[str(user.id)]
        self.save_warns()

        embed = discord.Embed(
            title="✅ Avisos Limpos",
            description=f"Todos os avisos de {user.mention} foram removidos!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationPanel(bot)) 