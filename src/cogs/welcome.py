import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# Modal para configurar o ID do canal
class ChannelModal(discord.ui.Modal, title="Configurar Canal"):
    channel_input = discord.ui.TextInput(label="ID do Canal", placeholder="Digite o ID do canal de boas-vindas", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_input.value)
            self.stop()
            await interaction.response.send_message(f"✅ Canal configurado para: {channel_id}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ ID do canal inválido. Use apenas números.", ephemeral=True)

# Modal para configurar o Embed
class EmbedModal(discord.ui.Modal, title="Configurar Embed"):
    title_input = discord.ui.TextInput(label="Título do Embed", placeholder="Digite o título", required=False)
    description_input = discord.ui.TextInput(label="Descrição do Embed", style=discord.TextStyle.paragraph, placeholder="Digite a descrição (use {member} para mencionar o membro)", required=False)
    color_input = discord.ui.TextInput(label="Cor do Embed (hex)", placeholder="Digite o código hexadecimal da cor (ex: #FFFFFF)", required=False)
    thumbnail_input = discord.ui.TextInput(label="URL da Imagem", placeholder="Digite o URL da imagem grande", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_message("Embed configurado!", ephemeral=True)



# View para o comando /setwelcome
class WelcomeSetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None) # Removido o timeout
        self.bot = bot
        self.channel_id = None
        self.embed_title = None
        self.embed_description = None
        self.embed_color = None

    @discord.ui.button(label="Configurar Canal", style=discord.ButtonStyle.primary, custom_id="set_channel")
    async def set_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ChannelModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.channel_input.value:
            self.channel_id = int(modal.channel_input.value)
            button.label = f"Canal: {self.channel_id}"
            self.channel = self.bot.get_channel(self.channel_id)
            await interaction.followup.send(view=self, ephemeral=True)

    @discord.ui.button(label="Configurar Embed", style=discord.ButtonStyle.secondary, custom_id="set_embed")
    async def set_embed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EmbedModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.embed_title = modal.title_input.value
        self.embed_description = modal.description_input.value
        self.embed_color = modal.color_input.value
        self.embed_thumbnail = modal.thumbnail_input.value

    @discord.ui.button(label="Testar Embed", style=discord.ButtonStyle.blurple, custom_id="test_embed")
    async def test_embed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.channel_id:
            await interaction.response.send_message("❌ Por favor, configure o canal primeiro.", ephemeral=True)
            return

        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("❌ Canal de boas-vindas não encontrado.", ephemeral=True)
            return

        embed = discord.Embed(
            title=self.embed_title or "Bem-vindo!",
            description=self.embed_description or f"Bem-vindo(a) ao servidor!",
            color=discord.Color.from_str(self.embed_color or '#FFFFFF')
        )
        if self.embed_thumbnail:
            embed.set_image(url=self.embed_thumbnail)

        test_description = self.embed_description.replace("{member}", f"<@1234567890>") if self.embed_description else f"Bem-vindo(a) ao servidor!"
        embed.description = test_description

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message("✅ Embed de boas-vindas enviado para o canal de teste!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ocorreu um erro ao enviar o embed: {e}", ephemeral=True)


    @discord.ui.button(label="Salvar Configuração", style=discord.ButtonStyle.success, custom_id="save_config")
    async def save_config_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.channel_id:
            await interaction.response.send_message("❌ Por favor, configure o canal primeiro.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        config_data = {
            "channel_id": self.channel_id,
            "embed_title": self.embed_title,
            "embed_description": self.embed_description,
            "embed_color": self.embed_color,
            "embed_thumbnail": self.embed_thumbnail
        }

        with open('data/welcome_config.json', 'w') as f:
            json.dump({guild_id: config_data}, f)

        await interaction.response.send_message("✅ Configuração salva com sucesso!", ephemeral=True)


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setwelcome", description="Configura a mensagem de boas-vindas")
    @app_commands.checks.has_permissions(administrator=True)
    async def setwelcome(self, interaction: discord.Interaction):
        """Configura a mensagem de boas-vindas"""
        view = WelcomeSetupView(self.bot)
        await interaction.response.send_message("Clique nos botões para configurar a mensagem de boas-vindas:", view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Envia a mensagem de boas-vindas quando um membro entra no servidor"""
        print(f"on_member_join triggered for {member.name} ({member.id}) in {member.guild.name} ({member.guild.id})")
        guild_id = str(member.guild.id)
        try:
            with open('data/welcome_config.json', 'r') as f:
                welcome_config = json.load(f)

            if guild_id in welcome_config:
                channel_id = int(welcome_config[guild_id]['channel_id'])
                channel = self.bot.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(
                        title=welcome_config[guild_id].get('embed_title', 'Bem-vindo!'),
                        description=welcome_config[guild_id].get('embed_description', f'Bem-vindo(a) {member.mention} ao servidor!'),
                        color=discord.Color.from_str(welcome_config[guild_id].get('embed_color', '#FFFFFF'))
                    )
                    image_url = welcome_config[guild_id].get('embed_thumbnail')
                    if image_url:
                        embed.set_image(url=image_url)
                    description = welcome_config[guild_id].get('embed_description', f'Bem-vindo(a) {member.mention} ao servidor!').replace("{member}", member.mention)
                    embed.description = description
                    print(f"channel_id: {channel_id}")
                    print(f"channel: {channel}")
                    # await channel.send(member.mention)
                    await channel.send(embed=embed)
        except FileNotFoundError:
            print("Arquivo de configuração não encontrado.")
        except Exception as e:
            print(f"Ocorreu um erro: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
