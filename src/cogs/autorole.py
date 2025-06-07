import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional, List

class Autorole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles_file = "data/reaction_roles.json"
        self.reaction_roles = self.load_reaction_roles()

    def load_reaction_roles(self):
        """Carrega as configurações de reaction roles do arquivo JSON"""
        if not os.path.exists("data"):
            os.makedirs("data")
            
        if os.path.exists(self.reaction_roles_file):
            with open(self.reaction_roles_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_reaction_roles(self):
        """Salva as configurações de reaction roles no arquivo JSON"""
        with open(self.reaction_roles_file, "w", encoding="utf-8") as f:
            json.dump(self.reaction_roles, f, indent=4)

    @app_commands.command(name="setup_autorole", description="Configura um sistema de reaction roles")
    @app_commands.describe(
        channel="Canal onde a mensagem será enviada",
        title="Título da mensagem",
        description="Descrição da mensagem",
        roles="Lista de roles (formato: emoji=@role, emoji=@role, ...)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_autorole(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str,
        roles: str
    ):
        """Configura um sistema de reaction roles"""
        await interaction.response.defer()

        # Verifica se o bot tem permissões necessárias
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.followup.send("❌ Eu não tenho permissão para gerenciar roles!")
            return

        # Processa a string de roles
        role_pairs = []
        for pair in roles.split(","):
            try:
                emoji, role_mention = pair.strip().split("=")
                emoji = emoji.strip()
                role_id = int(role_mention.strip("<@&>"))
                role = interaction.guild.get_role(role_id)
                if role:
                    role_pairs.append((emoji, role))
            except:
                continue

        if not role_pairs:
            await interaction.followup.send("❌ Nenhum role válido encontrado!")
            return

        # Cria o embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        
        # Adiciona os roles ao embed
        roles_text = "\n".join([f"{emoji} - {role.mention}" for emoji, role in role_pairs])
        embed.add_field(name="Roles Disponíveis", value=roles_text, inline=False)
        
        # Envia a mensagem
        message = await channel.send(embed=embed)
        
        # Adiciona as reações
        for emoji, _ in role_pairs:
            try:
                await message.add_reaction(emoji)
            except:
                continue

        # Salva a configuração
        guild_id = str(interaction.guild.id)
        if guild_id not in self.reaction_roles:
            self.reaction_roles[guild_id] = {}

        self.reaction_roles[guild_id][str(message.id)] = {
            "channel_id": channel.id,
            "roles": {emoji: role.id for emoji, role in role_pairs}
        }
        self.save_reaction_roles()

        await interaction.followup.send(
            f"✅ Sistema de reaction roles configurado com sucesso!\n"
            f"• Mensagem enviada em {channel.mention}\n"
            f"• {len(role_pairs)} roles configurados"
        )

    @app_commands.command(name="remove_autorole", description="Remove um sistema de reaction roles")
    @app_commands.describe(
        message_id="ID da mensagem de reaction roles"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_autorole(
        self,
        interaction: discord.Interaction,
        message_id: str
    ):
        """Remove um sistema de reaction roles"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.reaction_roles or message_id not in self.reaction_roles[guild_id]:
            await interaction.response.send_message("❌ Sistema de reaction roles não encontrado!", ephemeral=True)
            return

        # Remove a configuração
        del self.reaction_roles[guild_id][message_id]
        self.save_reaction_roles()

        await interaction.response.send_message("✅ Sistema de reaction roles removido com sucesso!")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Manipula a adição de reações"""
        if payload.user_id == self.bot.user.id:
            return

        guild_id = str(payload.guild_id)
        if guild_id not in self.reaction_roles:
            return

        message_id = str(payload.message_id)
        if message_id not in self.reaction_roles[guild_id]:
            return

        # Obtém o emoji
        emoji = str(payload.emoji)
        if emoji not in self.reaction_roles[guild_id][message_id]["roles"]:
            return

        # Obtém o guild e o membro
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member:
            return

        # Obtém o role
        role_id = self.reaction_roles[guild_id][message_id]["roles"][emoji]
        role = guild.get_role(role_id)
        if not role:
            return

        # Adiciona o role
        try:
            await member.add_roles(role)
        except:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Manipula a remoção de reações"""
        if payload.user_id == self.bot.user.id:
            return

        guild_id = str(payload.guild_id)
        if guild_id not in self.reaction_roles:
            return

        message_id = str(payload.message_id)
        if message_id not in self.reaction_roles[guild_id]:
            return

        # Obtém o emoji
        emoji = str(payload.emoji)
        if emoji not in self.reaction_roles[guild_id][message_id]["roles"]:
            return

        # Obtém o guild e o membro
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member:
            return

        # Obtém o role
        role_id = self.reaction_roles[guild_id][message_id]["roles"][emoji]
        role = guild.get_role(role_id)
        if not role:
            return

        # Remove o role
        try:
            await member.remove_roles(role)
        except:
            pass

    @setup_autorole.error
    @remove_autorole.error
    async def autorole_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Ocorreu um erro: {str(error)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Autorole(bot)) 