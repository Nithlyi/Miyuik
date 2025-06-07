import discord
from discord.ext import commands
from discord import app_commands
import re
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict

class Protection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "data/protection_config.json"
        self.load_config()
        
        # Anti-spam tracking
        self.message_history = defaultdict(list)
        self.user_warnings = defaultdict(int)
        
        # Anti-raid tracking
        self.join_history = defaultdict(list)
        self.raid_detected = False
        
        # Load invite regex
        self.invite_regex = re.compile(r'(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com/invite)/[a-zA-Z0-9]+')

    def load_config(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "anti_spam": {
                    "enabled": True,
                    "max_messages": 5,
                    "time_window": 5,
                    "punishment": "mute",
                    "punishment_duration": 300
                },
                "anti_raid": {
                    "enabled": True,
                    "max_joins": 5,
                    "time_window": 10,
                    "punishment": "ban"
                },
                "anti_invite": {
                    "enabled": True,
                    "punishment": "delete",
                    "whitelist": []
                }
            }
            self.save_config()

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Anti-spam check
        if self.config["anti_spam"]["enabled"]:
            await self.check_spam(message)

        # Anti-invite check
        if self.config["anti_invite"]["enabled"]:
            await self.check_invite(message)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if self.config["anti_raid"]["enabled"]:
            await self.check_raid(member)

    async def check_spam(self, message: discord.Message):
        current_time = datetime.utcnow()
        user_id = message.author.id
        guild_id = message.guild.id

        # Clean old messages
        self.message_history[guild_id] = [
            msg for msg in self.message_history[guild_id]
            if current_time - msg["time"] < timedelta(seconds=self.config["anti_spam"]["time_window"])
        ]

        # Add new message
        self.message_history[guild_id].append({
            "user_id": user_id,
            "time": current_time
        })

        # Check for spam
        user_messages = [
            msg for msg in self.message_history[guild_id]
            if msg["user_id"] == user_id
        ]

        if len(user_messages) > self.config["anti_spam"]["max_messages"]:
            self.user_warnings[user_id] += 1
            
            if self.config["anti_spam"]["punishment"] == "mute":
                try:
                    await message.author.timeout(
                        datetime.utcnow() + timedelta(seconds=self.config["anti_spam"]["punishment_duration"]),
                        reason="Anti-spam: Muitas mensagens em pouco tempo"
                    )
                    await message.channel.send(
                        f"{message.author.mention} foi silenciado por spam.",
                        delete_after=5
                    )
                except discord.Forbidden:
                    await message.channel.send(
                        "Não tenho permissão para silenciar usuários!",
                        delete_after=5
                    )
            elif self.config["anti_spam"]["punishment"] == "kick":
                try:
                    await message.author.kick(reason="Anti-spam: Muitas mensagens em pouco tempo")
                    await message.channel.send(
                        f"{message.author.mention} foi expulso por spam.",
                        delete_after=5
                    )
                except discord.Forbidden:
                    await message.channel.send(
                        "Não tenho permissão para expulsar usuários!",
                        delete_after=5
                    )

            # Delete spam messages
            try:
                await message.delete()
            except discord.Forbidden:
                pass

    async def check_raid(self, member: discord.Member):
        current_time = datetime.utcnow()
        guild_id = member.guild.id

        # Clean old joins
        self.join_history[guild_id] = [
            join for join in self.join_history[guild_id]
            if current_time - join["time"] < timedelta(seconds=self.config["anti_raid"]["time_window"])
        ]

        # Add new join
        self.join_history[guild_id].append({
            "user_id": member.id,
            "time": current_time
        })

        # Check for raid
        if len(self.join_history[guild_id]) > self.config["anti_raid"]["max_joins"]:
            self.raid_detected = True
            
            if self.config["anti_raid"]["punishment"] == "ban":
                try:
                    await member.ban(reason="Anti-raid: Muitos joins em pouco tempo")
                except discord.Forbidden:
                    pass

            # Notify admins
            for channel in member.guild.text_channels:
                if channel.permissions_for(member.guild.me).send_messages:
                    try:
                        embed = discord.Embed(
                            title="⚠️ Alerta de Raid Detectado!",
                            description="Muitos usuários entraram em pouco tempo!",
                            color=discord.Color.red(),
                            timestamp=current_time
                        )
                        embed.add_field(
                            name="Ações Tomadas",
                            value="• Usuários suspeitos foram banidos\n• Sistema de verificação ativado",
                            inline=False
                        )
                        await channel.send(embed=embed)
                        break
                    except discord.Forbidden:
                        continue

    async def check_invite(self, message: discord.Message):
        if not message.guild:
            return

        # Check if user has permission to post invites
        if message.author.guild_permissions.manage_guild:
            return

        # Check if invite is in whitelist
        if message.guild.id in self.config["anti_invite"]["whitelist"]:
            return

        if self.invite_regex.search(message.content):
            if self.config["anti_invite"]["punishment"] == "delete":
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention}, convites não são permitidos aqui!",
                        delete_after=5
                    )
                except discord.Forbidden:
                    pass
            elif self.config["anti_invite"]["punishment"] == "mute":
                try:
                    await message.author.timeout(
                        datetime.utcnow() + timedelta(minutes=30),
                        reason="Anti-invite: Postou convite"
                    )
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention} foi silenciado por postar convite!",
                        delete_after=5
                    )
                except discord.Forbidden:
                    pass

    @app_commands.command(name="protection", description="Configura o sistema de proteção")
    @app_commands.checks.has_permissions(administrator=True)
    async def protection(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛡️ Sistema de Proteção",
            description="Configure as proteções do servidor",
            color=discord.Color.default()
        )

        # Anti-spam status
        spam_status = "✅ Ativado" if self.config["anti_spam"]["enabled"] else "❌ Desativado"
        embed.add_field(
            name="Anti-spam",
            value=f"Status: {spam_status}\n"
                  f"Máximo de mensagens: {self.config['anti_spam']['max_messages']}\n"
                  f"Janela de tempo: {self.config['anti_spam']['time_window']}s\n"
                  f"Punição: {self.config['anti_spam']['punishment']}",
            inline=False
        )

        # Anti-raid status
        raid_status = "✅ Ativado" if self.config["anti_raid"]["enabled"] else "❌ Desativado"
        embed.add_field(
            name="Anti-raid",
            value=f"Status: {raid_status}\n"
                  f"Máximo de joins: {self.config['anti_raid']['max_joins']}\n"
                  f"Janela de tempo: {self.config['anti_raid']['time_window']}s\n"
                  f"Punição: {self.config['anti_raid']['punishment']}",
            inline=False
        )

        # Anti-invite status
        invite_status = "✅ Ativado" if self.config["anti_invite"]["enabled"] else "❌ Desativado"
        embed.add_field(
            name="Anti-invite",
            value=f"Status: {invite_status}\n"
                  f"Punição: {self.config['anti_invite']['punishment']}",
            inline=False
        )

        view = ProtectionView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ProtectionView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Anti-spam", style=discord.ButtonStyle.primary, row=0)
    async def anti_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AntiSpamModal(self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Anti-raid", style=discord.ButtonStyle.primary, row=0)
    async def anti_raid(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AntiRaidModal(self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Anti-invite", style=discord.ButtonStyle.primary, row=0)
    async def anti_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AntiInviteModal(self.cog)
        await interaction.response.send_modal(modal)

class AntiSpamModal(discord.ui.Modal, title="Configurar Anti-spam"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

        self.enabled = discord.ui.TextInput(
            label="Ativado (true/false)",
            placeholder="true ou false",
            required=True
        )
        self.add_item(self.enabled)

        self.max_messages = discord.ui.TextInput(
            label="Máximo de mensagens",
            placeholder="Ex: 5",
            required=True
        )
        self.add_item(self.max_messages)

        self.time_window = discord.ui.TextInput(
            label="Janela de tempo (segundos)",
            placeholder="Ex: 5",
            required=True
        )
        self.add_item(self.time_window)

        self.punishment = discord.ui.TextInput(
            label="Punição (mute/kick)",
            placeholder="mute ou kick",
            required=True
        )
        self.add_item(self.punishment)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.cog.config["anti_spam"]["enabled"] = self.enabled.value.lower() == "true"
            self.cog.config["anti_spam"]["max_messages"] = int(self.max_messages.value)
            self.cog.config["anti_spam"]["time_window"] = int(self.time_window.value)
            self.cog.config["anti_spam"]["punishment"] = self.punishment.value.lower()
            
            self.cog.save_config()
            
            await interaction.response.send_message("Configurações do anti-spam atualizadas!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Valores inválidos! Verifique os números e tente novamente.", ephemeral=True)

class AntiRaidModal(discord.ui.Modal, title="Configurar Anti-raid"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

        self.enabled = discord.ui.TextInput(
            label="Ativado (true/false)",
            placeholder="true ou false",
            required=True
        )
        self.add_item(self.enabled)

        self.max_joins = discord.ui.TextInput(
            label="Máximo de joins",
            placeholder="Ex: 5",
            required=True
        )
        self.add_item(self.max_joins)

        self.time_window = discord.ui.TextInput(
            label="Janela de tempo (segundos)",
            placeholder="Ex: 10",
            required=True
        )
        self.add_item(self.time_window)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.cog.config["anti_raid"]["enabled"] = self.enabled.value.lower() == "true"
            self.cog.config["anti_raid"]["max_joins"] = int(self.max_joins.value)
            self.cog.config["anti_raid"]["time_window"] = int(self.time_window.value)
            
            self.cog.save_config()
            
            await interaction.response.send_message("Configurações do anti-raid atualizadas!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Valores inválidos! Verifique os números e tente novamente.", ephemeral=True)

class AntiInviteModal(discord.ui.Modal, title="Configurar Anti-invite"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

        self.enabled = discord.ui.TextInput(
            label="Ativado (true/false)",
            placeholder="true ou false",
            required=True
        )
        self.add_item(self.enabled)

        self.punishment = discord.ui.TextInput(
            label="Punição (delete/mute)",
            placeholder="delete ou mute",
            required=True
        )
        self.add_item(self.punishment)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.cog.config["anti_invite"]["enabled"] = self.enabled.value.lower() == "true"
            self.cog.config["anti_invite"]["punishment"] = self.punishment.value.lower()
            
            self.cog.save_config()
            
            await interaction.response.send_message("Configurações do anti-invite atualizadas!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Valores inválidos! Verifique os valores e tente novamente.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Protection(bot)) 