import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "data/welcome_config.json"
        self.load_config()

    def load_config(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {}
            self.save_config()

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Evento quando um membro entra no servidor"""
        guild_id = str(member.guild.id)
        if guild_id in self.config and "welcome" in self.config[guild_id]:
            welcome_config = self.config[guild_id]["welcome"]
            
            if not welcome_config["enabled"]:
                return

            channel = member.guild.get_channel(welcome_config["channel_id"])
            if not channel:
                return

            # Substituir variáveis na mensagem
            message = welcome_config["message"]
            message = message.replace("{user}", member.mention)
            message = message.replace("{server}", member.guild.name)
            message = message.replace("{count}", str(member.guild.member_count))
            message = message.replace("{username}", str(member))
            message = message.replace("{mention}", member.mention)

            if welcome_config["use_embed"]:
                embed = discord.Embed(
                    title=welcome_config["embed_title"],
                    description=message,
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                if welcome_config["embed_thumbnail"]:
                    embed.set_thumbnail(url=member.display_avatar.url)
                
                if welcome_config["embed_image"]:
                    embed.set_image(url=welcome_config["embed_image"])
                
                if welcome_config["embed_footer"]:
                    embed.set_footer(text=welcome_config["embed_footer"])
                
                await channel.send(embed=embed)
            else:
                await channel.send(message)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Evento quando um membro sai do servidor"""
        guild_id = str(member.guild.id)
        if guild_id in self.config and "leave" in self.config[guild_id]:
            leave_config = self.config[guild_id]["leave"]
            
            if not leave_config["enabled"]:
                return

            channel = member.guild.get_channel(leave_config["channel_id"])
            if not channel:
                return

            # Substituir variáveis na mensagem
            message = leave_config["message"]
            message = message.replace("{user}", member.mention)
            message = message.replace("{server}", member.guild.name)
            message = message.replace("{count}", str(member.guild.member_count))
            message = message.replace("{username}", str(member))
            message = message.replace("{mention}", member.mention)

            if leave_config["use_embed"]:
                embed = discord.Embed(
                    title=leave_config["embed_title"],
                    description=message,
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                
                if leave_config["embed_thumbnail"]:
                    embed.set_thumbnail(url=member.display_avatar.url)
                
                if leave_config["embed_image"]:
                    embed.set_image(url=leave_config["embed_image"])
                
                if leave_config["embed_footer"]:
                    embed.set_footer(text=leave_config["embed_footer"])
                
                await channel.send(embed=embed)
            else:
                await channel.send(message)

    @app_commands.command(name="setwelcome", description="Configura a mensagem de boas-vindas")
    @app_commands.checks.has_permissions(administrator=True)
    async def setwelcome(self, interaction: discord.Interaction):
        """Comando para configurar mensagem de boas-vindas"""
        view = WelcomeSetupView(self)
        await interaction.response.send_message(
            "Configure a mensagem de boas-vindas:",
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="setleave", description="Configura a mensagem de despedida")
    @app_commands.checks.has_permissions(administrator=True)
    async def setleave(self, interaction: discord.Interaction):
        """Comando para configurar mensagem de despedida"""
        modal = LeaveModal(self)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="welcomeconfig", description="Mostra a configuração atual de boas-vindas")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcomeconfig(self, interaction: discord.Interaction):
        """Comando para ver configuração de boas-vindas"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config or "welcome" not in self.config[guild_id]:
            await interaction.response.send_message(
                "Nenhuma configuração de boas-vindas encontrada! Use `/setwelcome` para configurar.",
                ephemeral=True
            )
            return

        welcome_config = self.config[guild_id]["welcome"]
        channel = interaction.guild.get_channel(welcome_config["channel_id"])

        embed = discord.Embed(
            title="⚙️ Configuração de Boas-vindas",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Status",
            value="✅ Ativado" if welcome_config["enabled"] else "❌ Desativado",
            inline=False
        )

        embed.add_field(
            name="Canal",
            value=channel.mention if channel else "Canal não encontrado",
            inline=False
        )

        embed.add_field(
            name="Mensagem",
            value=welcome_config["message"],
            inline=False
        )

        if welcome_config["use_embed"]:
            embed.add_field(
                name="Configuração do Embed",
                value=f"**Título:** {welcome_config['embed_title']}\n"
                      f"**Thumbnail:** {'Sim' if welcome_config['embed_thumbnail'] else 'Não'}\n"
                      f"**Imagem:** {'Sim' if welcome_config['embed_image'] else 'Não'}\n"
                      f"**Rodapé:** {welcome_config['embed_footer']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaveconfig", description="Mostra a configuração atual de despedidas")
    @app_commands.checks.has_permissions(administrator=True)
    async def leaveconfig(self, interaction: discord.Interaction):
        """Comando para ver configuração de despedidas"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config or "leave" not in self.config[guild_id]:
            await interaction.response.send_message(
                "Nenhuma configuração de despedida encontrada! Use `/setleave` para configurar.",
                ephemeral=True
            )
            return

        leave_config = self.config[guild_id]["leave"]
        channel = interaction.guild.get_channel(leave_config["channel_id"])

        embed = discord.Embed(
            title="⚙️ Configuração de Despedidas",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Status",
            value="✅ Ativado" if leave_config["enabled"] else "❌ Desativado",
            inline=False
        )

        embed.add_field(
            name="Canal",
            value=channel.mention if channel else "Canal não encontrado",
            inline=False
        )

        embed.add_field(
            name="Mensagem",
            value=leave_config["message"],
            inline=False
        )

        if leave_config["use_embed"]:
            embed.add_field(
                name="Configuração do Embed",
                value=f"**Título:** {leave_config['embed_title']}\n"
                      f"**Thumbnail:** {'Sim' if leave_config['embed_thumbnail'] else 'Não'}\n"
                      f"**Imagem:** {'Sim' if leave_config['embed_image'] else 'Não'}\n"
                      f"**Rodapé:** {leave_config['embed_footer']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class WelcomeSetupView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = None
        self.message = None
        self.use_embed = False
        self.embed_title = None
        self.embed_image = None
        self.embed_footer = None

    @discord.ui.button(label="1. Configurar Canal", style=discord.ButtonStyle.primary, row=0)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ChannelModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="2. Configurar Mensagem", style=discord.ButtonStyle.primary, row=0)
    async def set_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.channel_id:
            await interaction.response.send_message(
                "Configure o canal primeiro!",
                ephemeral=True
            )
            return
        
        modal = MessageModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="3. Configurar Embed", style=discord.ButtonStyle.primary, row=0)
    async def set_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.message:
            await interaction.response.send_message(
                "Configure a mensagem primeiro!",
                ephemeral=True
            )
            return
        
        modal = EmbedModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="4. Salvar Configuração", style=discord.ButtonStyle.success, row=1)
    async def save_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.channel_id or not self.message:
            await interaction.response.send_message(
                "Configure o canal e a mensagem primeiro!",
                ephemeral=True
            )
            return

        try:
            # Salvar configuração
            guild_id = str(interaction.guild.id)
            if guild_id not in self.cog.config:
                self.cog.config[guild_id] = {}

            self.cog.config[guild_id]["welcome"] = {
                "enabled": True,
                "channel_id": self.channel_id,
                "message": self.message,
                "use_embed": self.use_embed,
                "embed_title": self.embed_title if self.use_embed else "",
                "embed_thumbnail": True if self.use_embed else False,
                "embed_image": self.embed_image if self.use_embed and self.embed_image else "",
                "embed_footer": self.embed_footer if self.use_embed and self.embed_footer else ""
            }

            self.cog.save_config()

            embed = discord.Embed(
                title="✅ Configuração Salva",
                description="Configuração de boas-vindas atualizada com sucesso!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Canal",
                value=f"<#{self.channel_id}>",
                inline=False
            )
            embed.add_field(
                name="Mensagem",
                value=self.message,
                inline=False
            )
            if self.use_embed:
                embed.add_field(
                    name="Configuração do Embed",
                    value=f"**Título:** {self.embed_title}\n"
                          f"**Imagem:** {'Sim' if self.embed_image else 'Não'}\n"
                          f"**Rodapé:** {self.embed_footer or 'Não'}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"Erro ao salvar configuração: {str(e)}",
                ephemeral=True
            )

class ChannelModal(discord.ui.Modal, title="Configurar Canal"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.channel = discord.ui.TextInput(
            label="ID do Canal",
            placeholder="Digite o ID do canal",
            required=True
        )
        self.add_item(self.channel)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel.value)
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                await interaction.response.send_message(
                    "Canal não encontrado! Verifique o ID.",
                    ephemeral=True
                )
                return

            self.view.channel_id = channel_id
            await interaction.response.send_message(
                f"Canal configurado: {channel.mention}",
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                "ID de canal inválido!",
                ephemeral=True
            )

class MessageModal(discord.ui.Modal, title="Configurar Mensagem"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.message = discord.ui.TextInput(
            label="Mensagem",
            placeholder="Digite a mensagem de boas-vindas\nVariáveis: {user}, {server}, {count}, {username}, {mention}",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.message = self.message.value
        await interaction.response.send_message(
            "Mensagem configurada com sucesso!",
            ephemeral=True
        )

class EmbedModal(discord.ui.Modal, title="Configurar Embed"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.use_embed = discord.ui.TextInput(
            label="Usar Embed (true/false)",
            placeholder="true ou false",
            required=True
        )
        self.add_item(self.use_embed)

        self.embed_title = discord.ui.TextInput(
            label="Título do Embed",
            placeholder="Digite o título do embed",
            required=False
        )
        self.add_item(self.embed_title)

        self.embed_image = discord.ui.TextInput(
            label="URL da Imagem do Embed",
            placeholder="Digite a URL da imagem (opcional)",
            required=False
        )
        self.add_item(self.embed_image)

        self.embed_footer = discord.ui.TextInput(
            label="Rodapé do Embed",
            placeholder="Digite o texto do rodapé (opcional)",
            required=False
        )
        self.add_item(self.embed_footer)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.view.use_embed = self.use_embed.value.lower() == "true"
            
            if self.view.use_embed:
                if not self.embed_title.value:
                    await interaction.response.send_message(
                        "O título do embed é obrigatório quando usar embed!",
                        ephemeral=True
                    )
                    return
                
                self.view.embed_title = self.embed_title.value
                self.view.embed_image = self.embed_image.value
                self.view.embed_footer = self.embed_footer.value

            await interaction.response.send_message(
                "Configuração do embed atualizada com sucesso!",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"Erro ao configurar embed: {str(e)}",
                ephemeral=True
            )

class LeaveModal(discord.ui.Modal, title="Configurar Despedida"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

        self.channel = discord.ui.TextInput(
            label="ID do Canal",
            placeholder="Digite o ID do canal",
            required=True
        )
        self.add_item(self.channel)

        self.message = discord.ui.TextInput(
            label="Mensagem",
            placeholder="Digite a mensagem de despedida\nVariáveis: {user}, {server}, {count}, {username}, {mention}",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.message)

        self.use_embed = discord.ui.TextInput(
            label="Usar Embed (true/false)",
            placeholder="true ou false",
            required=True
        )
        self.add_item(self.use_embed)

        self.embed_title = discord.ui.TextInput(
            label="Título do Embed",
            placeholder="Digite o título do embed",
            required=False
        )
        self.add_item(self.embed_title)

        self.embed_image = discord.ui.TextInput(
            label="URL da Imagem do Embed",
            placeholder="Digite a URL da imagem (opcional)",
            required=False
        )
        self.add_item(self.embed_image)

        self.embed_footer = discord.ui.TextInput(
            label="Rodapé do Embed",
            placeholder="Digite o texto do rodapé (opcional)",
            required=False
        )
        self.add_item(self.embed_footer)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar canal
            channel_id = int(self.channel.value)
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                await interaction.response.send_message(
                    "Canal não encontrado! Verifique o ID.",
                    ephemeral=True
                )
                return

            # Validar uso de embed
            use_embed = self.use_embed.value.lower() == "true"
            if use_embed and not self.embed_title.value:
                await interaction.response.send_message(
                    "O título do embed é obrigatório quando usar embed!",
                    ephemeral=True
                )
                return

            # Salvar configuração
            guild_id = str(interaction.guild.id)
            if guild_id not in self.cog.config:
                self.cog.config[guild_id] = {}

            self.cog.config[guild_id]["leave"] = {
                "enabled": True,
                "channel_id": channel_id,
                "message": self.message.value,
                "use_embed": use_embed,
                "embed_title": self.embed_title.value if use_embed else "",
                "embed_thumbnail": True if use_embed else False,
                "embed_image": self.embed_image.value if use_embed and self.embed_image.value else "",
                "embed_footer": self.embed_footer.value if use_embed and self.embed_footer.value else ""
            }

            self.cog.save_config()

            await interaction.response.send_message(
                "Configuração de despedida atualizada com sucesso!",
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                "ID de canal inválido!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Erro ao configurar: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot)) 