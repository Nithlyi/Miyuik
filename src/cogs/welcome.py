import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.welcome_config = {}
        self.load_config()

    def load_config(self):
        """Carrega a configuração de boas-vindas"""
        if os.path.exists("welcome_config.json"):
            with open("welcome_config.json", "r") as f:
                self.welcome_config = json.load(f)

    def save_config(self):
        """Salva a configuração de boas-vindas"""
        with open("welcome_config.json", "w") as f:
            json.dump(self.welcome_config, f, indent=4)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Evento quando um membro entra no servidor"""
        guild_id = str(member.guild.id)
        if guild_id in self.welcome_config:
            config = self.welcome_config[guild_id]
            
            if not config["enabled"]:
                return

            channel = member.guild.get_channel(config["channel_id"])
            if not channel:
                return

            # Substituir variáveis na mensagem
            message = config["message"]
            message = message.replace("{user}", member.mention)
            message = message.replace("{server}", member.guild.name)
            message = message.replace("{count}", str(member.guild.member_count))
            message = message.replace("{username}", str(member))
            message = message.replace("{mention}", member.mention)

            if config["use_embed"]:
                embed = discord.Embed(
                    title=config["embed_title"],
                    description=message,
                    color=discord.Color(config["embed_color"]),
                    timestamp=datetime.utcnow()
                )
                
                if config["embed_thumbnail"]:
                    embed.set_thumbnail(url=member.display_avatar.url)
                
                if config["embed_image"]:
                    embed.set_image(url=config["embed_image"])
                
                if config["embed_footer"]:
                    embed.set_footer(text=config["embed_footer"])
                
                await channel.send(embed=embed)
            else:
                await channel.send(message)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Evento quando um membro sai do servidor"""
        guild_id = str(member.guild.id)
        if guild_id in self.welcome_config and "leave" in self.welcome_config[guild_id]:
            leave_config = self.welcome_config[guild_id]["leave"]
            
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
        """Configura a mensagem de boas-vindas"""
        # Inicializa a configuração do servidor se não existir
        guild_id = str(interaction.guild.id)
        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {
                "enabled": True,
                "channel_id": None,
                "message": "Bem-vindo {user} ao {server}!",
                "use_embed": True,
                "embed_title": "👋 Boas-vindas!",
                "embed_thumbnail": True,
                "embed_image": None,
                "embed_footer": None,
                "embed_color": discord.Color.blue()
            }

        # Cria a view de configuração
        view = WelcomeSetupView(self)
        await interaction.response.send_message(
            "**Configuração de Boas-vindas**\n"
            "Use os botões abaixo para configurar a mensagem de boas-vindas:",
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="setleave", description="Configura a mensagem de despedida")
    @app_commands.checks.has_permissions(administrator=True)
    async def setleave(self, interaction: discord.Interaction):
        """Configura a mensagem de despedida"""
        # Inicializa a configuração do servidor se não existir
        guild_id = str(interaction.guild.id)
        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {}
        
        if "leave" not in self.welcome_config[guild_id]:
            self.welcome_config[guild_id]["leave"] = {
                "enabled": True,
                "channel_id": None,
                "message": "{user} saiu do servidor {server}!",
                "use_embed": True,
                "embed_title": "👋 Até logo!",
                "embed_thumbnail": True,
                "embed_image": None,
                "embed_footer": None
            }

        # Cria o modal de configuração
        modal = LeaveModal(self)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="welcomeconfig", description="Mostra a configuração atual de boas-vindas")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcomeconfig(self, interaction: discord.Interaction):
        """Mostra a configuração atual de boas-vindas"""
        guild_id = str(interaction.guild.id)
        if guild_id not in self.welcome_config:
            await interaction.response.send_message(
                "❌ Nenhuma configuração de boas-vindas encontrada! Use /setwelcome para configurar.",
                ephemeral=True
            )
            return

        config = self.welcome_config[guild_id]
        channel = interaction.guild.get_channel(config["channel_id"]) if config["channel_id"] else None

        embed = discord.Embed(
            title="⚙️ Configuração de Boas-vindas",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Status",
            value="✅ Ativado" if config["enabled"] else "❌ Desativado",
            inline=True
        )

        embed.add_field(
            name="Canal",
            value=channel.mention if channel else "❌ Não configurado",
            inline=True
        )

        embed.add_field(
            name="Mensagem",
            value=config["message"],
            inline=False
        )

        if config["use_embed"]:
            embed.add_field(
                name="Configuração do Embed",
                value=f"**Título:** {config['embed_title']}\n"
                      f"**Cor:** {config['embed_color']}\n"
                      f"**Thumbnail:** {'✅' if config['embed_thumbnail'] else '❌'}\n"
                      f"**Imagem:** {config['embed_image'] or '❌'}\n"
                      f"**Rodapé:** {config['embed_footer'] or '❌'}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaveconfig", description="Mostra a configuração atual de despedidas")
    @app_commands.checks.has_permissions(administrator=True)
    async def leaveconfig(self, interaction: discord.Interaction):
        """Mostra a configuração atual de despedidas"""
        guild_id = str(interaction.guild.id)
        if guild_id not in self.welcome_config or "leave" not in self.welcome_config[guild_id]:
            await interaction.response.send_message(
                "❌ Nenhuma configuração de despedida encontrada! Use /setleave para configurar.",
                ephemeral=True
            )
            return

        config = self.welcome_config[guild_id]["leave"]
        channel = interaction.guild.get_channel(config["channel_id"]) if config["channel_id"] else None

        embed = discord.Embed(
            title="⚙️ Configuração de Despedidas",
            color=discord.Color.red()
        )

        embed.add_field(
            name="Status",
            value="✅ Ativado" if config["enabled"] else "❌ Desativado",
            inline=True
        )

        embed.add_field(
            name="Canal",
            value=channel.mention if channel else "❌ Não configurado",
            inline=True
        )

        embed.add_field(
            name="Mensagem",
            value=config["message"],
            inline=False
        )

        if config["use_embed"]:
            embed.add_field(
                name="Configuração do Embed",
                value=f"**Título:** {config['embed_title']}\n"
                      f"**Thumbnail:** {'✅' if config['embed_thumbnail'] else '❌'}\n"
                      f"**Imagem:** {config['embed_image'] or '❌'}\n"
                      f"**Rodapé:** {config['embed_footer'] or '❌'}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class WelcomeSetupView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.config = {
            "channel_id": None,
            "message": None,
            "use_embed": True,
            "embed_title": None,
            "embed_thumbnail": True,
            "embed_image": None,
            "embed_footer": None,
            "embed_color": discord.Color.blue()
        }

    @discord.ui.button(label="1. Configurar Canal", style=discord.ButtonStyle.primary, row=0)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configura o canal de boas-vindas"""
        modal = ChannelModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="2. Configurar Mensagem", style=discord.ButtonStyle.primary, row=0)
    async def set_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configura a mensagem de boas-vindas"""
        modal = MessageModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="3. Configurar Embed", style=discord.ButtonStyle.primary, row=0)
    async def set_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configura as opções do embed"""
        modal = EmbedModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="4. Escolher Cor", style=discord.ButtonStyle.primary, row=1)
    async def set_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abre o menu de seleção de cor"""
        view = ColorSelectView(self)
        await interaction.response.send_message(
            "Escolha uma cor para o embed:",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="5. Preview", style=discord.ButtonStyle.secondary, row=1)
    async def preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mostra uma prévia do embed"""
        if not self.config["message"]:
            await interaction.response.send_message(
                "❌ Você precisa configurar a mensagem primeiro!",
                ephemeral=True
            )
            return

        if self.config["use_embed"] and not self.config["embed_title"]:
            await interaction.response.send_message(
                "❌ Você precisa configurar o título do embed primeiro!",
                ephemeral=True
            )
            return

        # Cria o embed de preview
        embed = discord.Embed(
            title=self.config["embed_title"],
            description=self.config["message"].replace("{user}", interaction.user.mention)
                                             .replace("{server}", interaction.guild.name)
                                             .replace("{count}", str(interaction.guild.member_count))
                                             .replace("{username}", str(interaction.user))
                                             .replace("{mention}", interaction.user.mention),
            color=self.config["embed_color"],
            timestamp=datetime.utcnow()
        )

        if self.config["embed_thumbnail"]:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

        if self.config["embed_image"]:
            embed.set_image(url=self.config["embed_image"])

        if self.config["embed_footer"]:
            embed.set_footer(text=self.config["embed_footer"])

        # Cria uma view com botões para atualizar o preview
        view = PreviewView(self, embed)
        await interaction.response.send_message(
            "**Preview do Embed de Boas-vindas**",
            embed=embed,
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="6. Salvar Configuração", style=discord.ButtonStyle.success, row=2)
    async def save_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Salva a configuração de boas-vindas"""
        if not self.config["channel_id"]:
            await interaction.response.send_message(
                "❌ Você precisa configurar o canal primeiro!",
                ephemeral=True
            )
            return

        if not self.config["message"]:
            await interaction.response.send_message(
                "❌ Você precisa configurar a mensagem primeiro!",
                ephemeral=True
            )
            return

        if self.config["use_embed"] and not self.config["embed_title"]:
            await interaction.response.send_message(
                "❌ Você precisa configurar o título do embed primeiro!",
                ephemeral=True
            )
            return

        # Salva a configuração
        guild_id = str(interaction.guild.id)
        if guild_id not in self.cog.welcome_config:
            self.cog.welcome_config[guild_id] = {}
        
        self.cog.welcome_config[guild_id]["welcome"] = {
            "enabled": True,
            "channel_id": self.config["channel_id"],
            "message": self.config["message"],
            "use_embed": self.config["use_embed"],
            "embed_title": self.config["embed_title"],
            "embed_thumbnail": self.config["embed_thumbnail"],
            "embed_image": self.config["embed_image"],
            "embed_footer": self.config["embed_footer"],
            "embed_color": self.config["embed_color"].value
        }

        self.cog.save_config()

        embed = discord.Embed(
            title="✅ Configuração Salva",
            description="A configuração de boas-vindas foi salva com sucesso!",
            color=discord.Color.green()
        )

        channel = interaction.guild.get_channel(self.config["channel_id"])
        embed.add_field(
            name="Canal",
            value=channel.mention if channel else "❌ Canal não encontrado",
            inline=True
        )

        embed.add_field(
            name="Mensagem",
            value=self.config["message"],
            inline=False
        )

        if self.config["use_embed"]:
            embed.add_field(
                name="Configuração do Embed",
                value=f"**Título:** {self.config['embed_title']}\n"
                      f"**Cor:** {self.config['embed_color']}\n"
                      f"**Thumbnail:** {'✅' if self.config['embed_thumbnail'] else '❌'}\n"
                      f"**Imagem:** {self.config['embed_image'] or '❌'}\n"
                      f"**Rodapé:** {self.config['embed_footer'] or '❌'}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class ChannelModal(discord.ui.Modal, title="Configurar Canal"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.channel_input = discord.ui.TextInput(
            label="ID do Canal",
            placeholder="Digite o ID do canal de boas-vindas",
            required=True
        )
        self.add_item(self.channel_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_input.value)
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message(
                    "❌ Canal não encontrado! Verifique o ID e tente novamente.",
                    ephemeral=True
                )
                return

            self.view.config["channel_id"] = channel_id
            await interaction.response.send_message(
                f"✅ Canal configurado: {channel.mention}",
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                "❌ ID do canal inválido! Digite apenas números.",
                ephemeral=True
            )

class MessageModal(discord.ui.Modal, title="Configurar Mensagem"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.message_input = discord.ui.TextInput(
            label="Mensagem",
            placeholder="Digite a mensagem de boas-vindas (use {user} para mencionar o usuário)",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.config["message"] = self.message_input.value
        await interaction.response.send_message(
            "✅ Mensagem configurada com sucesso!",
            ephemeral=True
        )

class EmbedModal(discord.ui.Modal, title="Configurar Embed"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        
        self.title_input = discord.ui.TextInput(
            label="Título do Embed",
            placeholder="Digite o título do embed",
            required=True
        )
        
        self.thumbnail_input = discord.ui.TextInput(
            label="Usar Thumbnail",
            placeholder="Digite 'sim' ou 'não'",
            required=True
        )
        
        self.image_input = discord.ui.TextInput(
            label="URL da Imagem",
            placeholder="Digite a URL da imagem (opcional)",
            required=False
        )
        
        self.footer_input = discord.ui.TextInput(
            label="Texto do Rodapé",
            placeholder="Digite o texto do rodapé (opcional)",
            required=False
        )
        
        self.add_item(self.title_input)
        self.add_item(self.thumbnail_input)
        self.add_item(self.image_input)
        self.add_item(self.footer_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.config["embed_title"] = self.title_input.value
        self.view.config["embed_thumbnail"] = self.thumbnail_input.value.lower() == "sim"
        self.view.config["embed_image"] = self.image_input.value or None
        self.view.config["embed_footer"] = self.footer_input.value or None

        await interaction.response.send_message(
            "✅ Configuração do embed salva com sucesso!",
            ephemeral=True
        )

class LeaveModal(discord.ui.Modal, title="Configurar Despedida"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        
        self.channel_input = discord.ui.TextInput(
            label="ID do Canal",
            placeholder="Digite o ID do canal de despedidas",
            required=True
        )
        
        self.message_input = discord.ui.TextInput(
            label="Mensagem",
            placeholder="Digite a mensagem de despedida (use {user} para mencionar o usuário)",
            required=True,
            style=discord.TextStyle.paragraph
        )
        
        self.title_input = discord.ui.TextInput(
            label="Título do Embed",
            placeholder="Digite o título do embed",
            required=True
        )
        
        self.thumbnail_input = discord.ui.TextInput(
            label="Usar Thumbnail",
            placeholder="Digite 'sim' ou 'não'",
            required=True
        )
        
        self.image_input = discord.ui.TextInput(
            label="URL da Imagem",
            placeholder="Digite a URL da imagem (opcional)",
            required=False
        )
        
        self.footer_input = discord.ui.TextInput(
            label="Texto do Rodapé",
            placeholder="Digite o texto do rodapé (opcional)",
            required=False
        )
        
        self.add_item(self.channel_input)
        self.add_item(self.message_input)
        self.add_item(self.title_input)
        self.add_item(self.thumbnail_input)
        self.add_item(self.image_input)
        self.add_item(self.footer_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_input.value)
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message(
                    "❌ Canal não encontrado! Verifique o ID e tente novamente.",
                    ephemeral=True
                )
                return

            # Salva a configuração
            guild_id = str(interaction.guild.id)
            self.cog.welcome_config[guild_id]["leave"] = {
                "enabled": True,
                "channel_id": channel_id,
                "message": self.message_input.value,
                "use_embed": True,
                "embed_title": self.title_input.value,
                "embed_thumbnail": self.thumbnail_input.value.lower() == "sim",
                "embed_image": self.image_input.value or None,
                "embed_footer": self.footer_input.value or None
            }
            self.cog.save_config()

            # Mostra a configuração salva
            embed = discord.Embed(
                title="✅ Configuração Salva!",
                description="Sua mensagem de despedida foi configurada com sucesso!",
                color=discord.Color.green()
            )

            embed.add_field(
                name="Canal",
                value=channel.mention,
                inline=True
            )

            embed.add_field(
                name="Mensagem",
                value=self.message_input.value,
                inline=False
            )

            embed.add_field(
                name="Configuração do Embed",
                value=f"**Título:** {self.title_input.value}\n"
                      f"**Thumbnail:** {'✅' if self.thumbnail_input.value.lower() == 'sim' else '❌'}\n"
                      f"**Imagem:** {self.image_input.value or '❌'}\n"
                      f"**Rodapé:** {self.footer_input.value or '❌'}",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except ValueError:
            await interaction.response.send_message(
                "❌ ID do canal inválido! Digite apenas números.",
                ephemeral=True
            )

class ColorSelectView(discord.ui.View):
    def __init__(self, welcome_view):
        super().__init__(timeout=60)
        self.welcome_view = welcome_view
        self.add_color_buttons()

    def add_color_buttons(self):
        colors = [
            ("Azul", discord.Color.blue(), discord.ButtonStyle.primary),
            ("Vermelho", discord.Color.red(), discord.ButtonStyle.danger),
            ("Verde", discord.Color.green(), discord.ButtonStyle.success),
            ("Amarelo", discord.Color.gold(), discord.ButtonStyle.secondary),
            ("Roxo", discord.Color.purple(), discord.ButtonStyle.primary),
            ("Laranja", discord.Color.orange(), discord.ButtonStyle.secondary),
            ("Rosa", discord.Color.pink(), discord.ButtonStyle.primary),
            ("Preto", discord.Color.default(), discord.ButtonStyle.secondary),
            ("Branco", discord.Color.light_grey(), discord.ButtonStyle.secondary)
        ]

        for label, color, style in colors:
            button = discord.ui.Button(
                label=label,
                style=style,
                custom_id=f"color_{color.value}"
            )
            button.callback = self.color_callback
            self.add_item(button)

    async def color_callback(self, interaction: discord.Interaction):
        color_value = int(interaction.data["custom_id"].split("_")[1])
        self.welcome_view.config["embed_color"] = discord.Color(color_value)
        button = interaction.component
        await interaction.response.send_message(
            f"✅ Cor do embed alterada para {button.label}!",
            ephemeral=True
        )

class PreviewView(discord.ui.View):
    def __init__(self, welcome_view, embed):
        super().__init__(timeout=300)
        self.welcome_view = welcome_view
        self.embed = embed

    @discord.ui.button(label="Atualizar Preview", style=discord.ButtonStyle.primary)
    async def update_preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Atualiza o preview do embed"""
        if not self.welcome_view.config["message"]:
            await interaction.response.send_message(
                "❌ Você precisa configurar a mensagem primeiro!",
                ephemeral=True
            )
            return

        if self.welcome_view.config["use_embed"] and not self.welcome_view.config["embed_title"]:
            await interaction.response.send_message(
                "❌ Você precisa configurar o título do embed primeiro!",
                ephemeral=True
            )
            return

        # Atualiza o embed
        self.embed.title = self.welcome_view.config["embed_title"]
        self.embed.description = self.welcome_view.config["message"].replace("{user}", interaction.user.mention) \
            .replace("{server}", interaction.guild.name) \
            .replace("{count}", str(interaction.guild.member_count)) \
            .replace("{username}", str(interaction.user)) \
            .replace("{mention}", interaction.user.mention)
        self.embed.color = self.welcome_view.config["embed_color"]

        if self.welcome_view.config["embed_thumbnail"]:
            self.embed.set_thumbnail(url=interaction.user.display_avatar.url)
        else:
            self.embed.set_thumbnail(url=None)

        if self.welcome_view.config["embed_image"]:
            self.embed.set_image(url=self.welcome_view.config["embed_image"])
        else:
            self.embed.set_image(url=None)

        if self.welcome_view.config["embed_footer"]:
            self.embed.set_footer(text=self.welcome_view.config["embed_footer"])
        else:
            self.embed.set_footer(text=None)

        try:
            await interaction.message.edit(embed=self.embed, view=self)
            await interaction.response.send_message("✅ Preview atualizado!", ephemeral=True)
        except discord.NotFound:
            # Se a mensagem não existir mais, cria uma nova
            await interaction.response.send_message(
                "**Preview do Embed de Boas-vindas**",
                embed=self.embed,
                view=self,
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot)) 