import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional
import asyncio

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tickets_file = "data/tickets.json"
        self.tickets = self.load_tickets()

    def load_tickets(self):
        """Carrega as configurações de tickets do arquivo JSON"""
        if not os.path.exists("data"):
            os.makedirs("data")
            
        if os.path.exists(self.tickets_file):
            with open(self.tickets_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_tickets(self):
        """Salva as configurações de tickets no arquivo JSON"""
        with open(self.tickets_file, "w", encoding="utf-8") as f:
            json.dump(self.tickets, f, indent=4)

    @app_commands.command(name="setup_tickets", description="Configura o sistema de tickets")
    @app_commands.describe(
        channel="Canal onde o painel de tickets será enviado",
        category="Categoria onde os tickets serão criados",
        support_role="Role que terá acesso aos tickets"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_tickets(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        category: discord.CategoryChannel,
        support_role: discord.Role
    ):
        """Configura o sistema de tickets"""
        await interaction.response.defer()

        # Verifica permissões do bot
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Eu não tenho permissão para gerenciar canais!")
            return

        # Cria o embed do painel
        embed = discord.Embed(
            title="🎫 Sistema de Tickets",
            description="Clique no botão abaixo para abrir um ticket de suporte",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Suporte • Tickets")

        # Cria o botão
        button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Abrir Ticket",
            emoji="🎫",
            custom_id="create_ticket"
        )

        # Cria a view
        view = discord.ui.View()
        view.add_item(button)

        # Envia a mensagem
        message = await channel.send(embed=embed, view=view)

        # Salva a configuração
        guild_id = str(interaction.guild.id)
        self.tickets[guild_id] = {
            "panel_message_id": message.id,
            "channel_id": channel.id,
            "category_id": category.id,
            "support_role_id": support_role.id
        }
        self.save_tickets()

        await interaction.followup.send(
            f"✅ Sistema de tickets configurado com sucesso!\n"
            f"• Painel enviado em {channel.mention}\n"
            f"• Categoria: {category.name}\n"
            f"• Role de suporte: {support_role.mention}"
        )

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Manipula todas as interações com os botões"""
        if not interaction.type == discord.InteractionType.component:
            return

        try:
            custom_id = interaction.data.get("custom_id")
            if not custom_id:
                return

            if custom_id == "create_ticket":
                await self.create_ticket(interaction)
            elif custom_id == "close_ticket":
                await self.close_ticket(interaction)
            elif custom_id == "confirm_close":
                await self.confirm_close_ticket(interaction)
            elif custom_id == "cancel_close":
                await interaction.message.delete()
        except Exception as e:
            print(f"Erro ao processar interação: {str(e)}")
            await interaction.response.send_message("❌ Ocorreu um erro ao processar sua interação.", ephemeral=True)

    async def create_ticket(self, interaction: discord.Interaction):
        """Cria um novo ticket"""
        guild_id = str(interaction.guild.id)
        if guild_id not in self.tickets:
            await interaction.response.send_message("❌ Sistema de tickets não configurado!", ephemeral=True)
            return

        # Verifica se o usuário já tem um ticket aberto
        for channel in interaction.guild.channels:
            if channel.name.startswith(f"ticket-{interaction.user.id}"):
                await interaction.response.send_message("❌ Você já tem um ticket aberto!", ephemeral=True)
                return

        # Obtém as configurações
        config = self.tickets[guild_id]
        category = interaction.guild.get_channel(config["category_id"])
        support_role = interaction.guild.get_role(config["support_role_id"])

        # Cria o canal do ticket
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites
        )

        # Cria o embed do ticket
        embed = discord.Embed(
            title="🎫 Ticket de Suporte",
            description=f"Ticket criado por {interaction.user.mention}\n\n"
                       f"Por favor, descreva seu problema em detalhes para que possamos ajudá-lo.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Suporte • Tickets")

        # Cria os botões
        close_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Fechar Ticket",
            emoji="🔒",
            custom_id="close_ticket"
        )

        view = discord.ui.View()
        view.add_item(close_button)

        # Envia a mensagem inicial
        await channel.send(
            content=f"{interaction.user.mention} {support_role.mention}",
            embed=embed,
            view=view
        )

        await interaction.response.send_message(
            f"✅ Seu ticket foi criado em {channel.mention}!",
            ephemeral=True
        )

    async def close_ticket(self, interaction: discord.Interaction):
        """Fecha um ticket"""
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ Este comando só pode ser usado em canais de ticket!", ephemeral=True)
            return

        # Verifica permissões
        guild_id = str(interaction.guild.id)
        if guild_id not in self.tickets:
            await interaction.response.send_message("❌ Sistema de tickets não configurado!", ephemeral=True)
            return

        config = self.tickets[guild_id]
        support_role = interaction.guild.get_role(config["support_role_id"])

        if not (interaction.user.guild_permissions.administrator or support_role in interaction.user.roles):
            await interaction.response.send_message("❌ Você não tem permissão para fechar tickets!", ephemeral=True)
            return

        # Confirma o fechamento
        confirm_embed = discord.Embed(
            title="🔒 Fechar Ticket",
            description="Tem certeza que deseja fechar este ticket?",
            color=discord.Color.red()
        )

        confirm_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Confirmar",
            emoji="✅",
            custom_id="confirm_close"
        )

        cancel_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Cancelar",
            emoji="❌",
            custom_id="cancel_close"
        )

        view = discord.ui.View()
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)

    async def confirm_close_ticket(self, interaction: discord.Interaction):
        """Confirma o fechamento do ticket"""
        # Obtém o ID do usuário do ticket do nome do canal (formato ticket-tipo-user_id)
        user_id = None
        try:
            parts = interaction.channel.name.split("-")
            # Verifica se o nome do canal tem o formato esperado e tenta obter o ID do usuário
            if len(parts) > 2 and parts[-1].isdigit():
                 user_id = int(parts[-1]) # O ID do usuário é a última parte
        except (ValueError, IndexError):
             # Ignora se o nome do canal não estiver no formato esperado ou a conversão falhar
             pass

        # Cria o embed de fechamento
        close_embed = discord.Embed(
            title="🔒 Ticket Fechado",
            description=f"Este ticket foi fechado por {interaction.user.mention}",
            color=discord.Color.red()
        )
        # Adiciona o campo de usuário do ticket ao embed se o ID foi obtido com sucesso
        if user_id:
             close_embed.add_field(name="Usuário do Ticket", value=f"<@{user_id}>", inline=True)

        # Envia a mensagem de fechamento
        await interaction.channel.send(embed=close_embed)

        # Espera 5 segundos antes de deletar o canal
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @setup_tickets.error
    async def tickets_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Ocorreu um erro: {str(error)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot)) 