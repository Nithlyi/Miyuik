import discord
from discord import app_commands
from discord.ext import commands
from discord import ui
import json

class EmbedCreator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.embed_data = {}

    class EmbedModal(ui.Modal, title="Criar Embed"):
        def __init__(self, embed_data: dict):
            super().__init__()
            self.embed_data = embed_data

            # Título
            self.title_input = ui.TextInput(
                label="Título",
                placeholder="Digite o título do embed",
                default=embed_data.get("title", ""),
                required=False,
                max_length=256
            )
            self.add_item(self.title_input)

            # Descrição
            self.description_input = ui.TextInput(
                label="Descrição",
                placeholder="Digite a descrição do embed",
                default=embed_data.get("description", ""),
                required=False,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.description_input)

            # Cor
            self.color_input = ui.TextInput(
                label="Cor (hex)",
                placeholder="Ex: #FF0000 para vermelho",
                default=embed_data.get("color", "#000000"),
                required=False,
                max_length=7
            )
            self.add_item(self.color_input)

            # Imagem
            self.image_input = ui.TextInput(
                label="URL da Imagem/GIF",
                placeholder="Cole aqui a URL da imagem ou GIF",
                default=embed_data.get("image", ""),
                required=False
            )
            self.add_item(self.image_input)

            # Thumbnail
            self.thumbnail_input = ui.TextInput(
                label="URL da Thumbnail",
                placeholder="Cole aqui a URL da thumbnail",
                default=embed_data.get("thumbnail", ""),
                required=False
            )
            self.add_item(self.thumbnail_input)

        async def on_submit(self, interaction: discord.Interaction):
            # Atualiza os dados do embed
            self.embed_data["title"] = self.title_input.value
            self.embed_data["description"] = self.description_input.value
            self.embed_data["color"] = self.color_input.value
            self.embed_data["image"] = self.image_input.value
            self.embed_data["thumbnail"] = self.thumbnail_input.value

            # Cria o embed de preview
            embed = self.create_embed()
            await interaction.response.send_message("**Preview do Embed:**", embed=embed, view=EmbedCreator.EmbedView(self.embed_data))

        def create_embed(self) -> discord.Embed:
            embed = discord.Embed(
                title=self.title_input.value,
                description=self.description_input.value,
                color=int(self.color_input.value.replace("#", ""), 16) if self.color_input.value.startswith("#") else 0
            )
            
            # Adiciona imagem se fornecida
            if self.image_input.value:
                embed.set_image(url=self.image_input.value)
            
            # Adiciona thumbnail se fornecida
            if self.thumbnail_input.value:
                embed.set_thumbnail(url=self.thumbnail_input.value)
            
            return embed

    class EmbedView(ui.View):
        def __init__(self, embed_data: dict):
            super().__init__(timeout=None)
            self.embed_data = embed_data

        @discord.ui.button(label="Editar", style=discord.ButtonStyle.primary, emoji="✏️")
        async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(EmbedCreator.EmbedModal(self.embed_data))

        @discord.ui.button(label="Adicionar Campo", style=discord.ButtonStyle.success, emoji="➕")
        async def add_field_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = EmbedCreator.FieldModal(self.embed_data)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Enviar", style=discord.ButtonStyle.green, emoji="📨")
        async def send_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = self.create_embed()
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("Embed enviado com sucesso! ✅", ephemeral=True)

        @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
        async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.message.delete()
            await interaction.response.send_message("Criação do embed cancelada! ❌", ephemeral=True)

        def create_embed(self) -> discord.Embed:
            embed = discord.Embed(
                title=self.embed_data.get("title", ""),
                description=self.embed_data.get("description", ""),
                color=int(self.embed_data.get("color", "#000000").replace("#", ""), 16)
            )
            
            # Adiciona imagem se existir
            if self.embed_data.get("image"):
                embed.set_image(url=self.embed_data["image"])
            
            # Adiciona thumbnail se existir
            if self.embed_data.get("thumbnail"):
                embed.set_thumbnail(url=self.embed_data["thumbnail"])
            
            # Adiciona os campos
            for field in self.embed_data.get("fields", []):
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False)
                )
            
            return embed

    class FieldModal(ui.Modal, title="Adicionar Campo"):
        def __init__(self, embed_data: dict):
            super().__init__()
            self.embed_data = embed_data

            # Nome do campo
            self.name_input = ui.TextInput(
                label="Nome do Campo",
                placeholder="Digite o nome do campo",
                required=True,
                max_length=256
            )
            self.add_item(self.name_input)

            # Valor do campo
            self.value_input = ui.TextInput(
                label="Valor do Campo",
                placeholder="Digite o valor do campo",
                required=True,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.value_input)

            # Inline
            self.inline_input = ui.TextInput(
                label="Inline (true/false)",
                placeholder="Digite true ou false",
                default="false",
                required=True,
                max_length=5
            )
            self.add_item(self.inline_input)

        async def on_submit(self, interaction: discord.Interaction):
            # Adiciona o campo aos dados do embed
            if "fields" not in self.embed_data:
                self.embed_data["fields"] = []
            
            self.embed_data["fields"].append({
                "name": self.name_input.value,
                "value": self.value_input.value,
                "inline": self.inline_input.value.lower() == "true"
            })

            # Cria o embed de preview
            embed = self.create_embed()
            await interaction.response.send_message("**Preview do Embed:**", embed=embed, view=EmbedCreator.EmbedView(self.embed_data))

        def create_embed(self) -> discord.Embed:
            embed = discord.Embed(
                title=self.embed_data.get("title", ""),
                description=self.embed_data.get("description", ""),
                color=int(self.embed_data.get("color", "#000000").replace("#", ""), 16)
            )
            
            # Adiciona imagem se existir
            if self.embed_data.get("image"):
                embed.set_image(url=self.embed_data["image"])
            
            # Adiciona thumbnail se existir
            if self.embed_data.get("thumbnail"):
                embed.set_thumbnail(url=self.embed_data["thumbnail"])
            
            # Adiciona os campos
            for field in self.embed_data.get("fields", []):
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False)
                )
            
            return embed

    @app_commands.command(name="embed", description="Cria um embed personalizado com menu interativo")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def embed(self, interaction: discord.Interaction):
        # Inicializa os dados do embed
        self.embed_data = {
            "title": "",
            "description": "",
            "color": "#000000",
            "image": "",
            "thumbnail": "",
            "fields": []
        }

        # Cria o embed inicial
        embed = discord.Embed(
            title="Criador de Embed",
            description="Use os botões abaixo para criar seu embed personalizado!",
            color=discord.Color.default()  # Cor preta
        )
        embed.add_field(
            name="📝 Como usar",
            value="1. Clique em 'Editar' para definir título, descrição, cor e imagens\n"
                  "2. Use 'Adicionar Campo' para adicionar campos ao embed\n"
                  "3. Clique em 'Enviar' quando estiver pronto\n"
                  "4. Use 'Cancelar' para descartar o embed",
            inline=False
        )

        # Envia o menu inicial
        await interaction.response.send_message(embed=embed, view=self.EmbedView(self.embed_data))

async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedCreator(bot)) 