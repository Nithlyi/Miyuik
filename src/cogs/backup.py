import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import aiohttp
import asyncio
from datetime import datetime
import zipfile
import io

class Backup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backup_dir = "data/backups"
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    async def create_backup(self, guild: discord.Guild) -> dict:
        """Cria um backup completo do servidor"""
        backup = {
            "name": guild.name,
            "icon_url": str(guild.icon.url) if guild.icon else None,
            "banner_url": str(guild.banner.url) if guild.banner else None,
            "verification_level": str(guild.verification_level),
            "explicit_content_filter": str(guild.explicit_content_filter),
            "default_notifications": str(guild.default_notifications),
            "roles": [],
            "channels": [],
            "emojis": [],
            "created_at": datetime.utcnow().isoformat()
        }

        # Backup de cargos
        for role in guild.roles:
            if role.name != "@everyone":
                role_data = {
                    "name": role.name,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "position": role.position,
                    "mentionable": role.mentionable,
                    "permissions": role.permissions.value
                }
                backup["roles"].append(role_data)

        # Backup de canais
        for category in guild.categories:
            category_data = {
                "name": category.name,
                "position": category.position,
                "type": "category",
                "overwrites": self._get_overwrites(category.overwrites)
            }
            backup["channels"].append(category_data)

            for channel in category.channels:
                channel_data = {
                    "name": channel.name,
                    "type": str(channel.type),
                    "position": channel.position,
                    "overwrites": self._get_overwrites(channel.overwrites),
                    "parent": category.name
                }

                if isinstance(channel, discord.TextChannel):
                    channel_data.update({
                        "topic": channel.topic,
                        "nsfw": channel.nsfw,
                        "slowmode_delay": channel.slowmode_delay
                    })
                elif isinstance(channel, discord.VoiceChannel):
                    channel_data.update({
                        "bitrate": channel.bitrate,
                        "user_limit": channel.user_limit
                    })

                backup["channels"].append(channel_data)

        # Backup de emojis
        for emoji in guild.emojis:
            emoji_data = {
                "name": emoji.name,
                "url": str(emoji.url)
            }
            backup["emojis"].append(emoji_data)

        return backup

    def _get_overwrites(self, overwrites):
        """Converte overwrites para um formato serializável"""
        overwrite_data = []
        for target, overwrite in overwrites.items():
            allow, deny = overwrite.pair()
            overwrite_data.append({
                "id": target.id,
                "type": "role" if isinstance(target, discord.Role) else "member",
                "allow": allow.value,
                "deny": deny.value
            })
        return overwrite_data

    async def save_backup(self, guild: discord.Guild) -> str:
        """Salva o backup em um arquivo"""
        backup = await self.create_backup(guild)
        
        # Criar nome do arquivo
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{guild.id}_{timestamp}.json"
        filepath = os.path.join(self.backup_dir, filename)

        # Salvar backup
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=4, ensure_ascii=False)

        return filename

    async def load_backup(self, guild: discord.Guild, filename: str):
        """Carrega e aplica um backup"""
        filepath = os.path.join(self.backup_dir, filename)
        
        with open(filepath, "r", encoding="utf-8") as f:
            backup = json.load(f)

        # Atualizar configurações básicas
        await guild.edit(
            name=backup["name"],
            verification_level=discord.VerificationLevel[backup["verification_level"]],
            explicit_content_filter=discord.ContentFilter[backup["explicit_content_filter"]],
            default_notifications=discord.NotificationLevel[backup["default_notifications"]]
        )

        # Baixar e atualizar ícone
        if backup["icon_url"]:
            async with aiohttp.ClientSession() as session:
                async with session.get(backup["icon_url"]) as resp:
                    if resp.status == 200:
                        icon_data = await resp.read()
                        await guild.edit(icon=icon_data)

        # Baixar e atualizar banner
        if backup["banner_url"]:
            async with aiohttp.ClientSession() as session:
                async with session.get(backup["banner_url"]) as resp:
                    if resp.status == 200:
                        banner_data = await resp.read()
                        await guild.edit(banner=banner_data)

        # Criar cargos
        role_mapping = {}
        for role_data in sorted(backup["roles"], key=lambda x: x["position"], reverse=True):
            role = await guild.create_role(
                name=role_data["name"],
                color=discord.Color(role_data["color"]),
                hoist=role_data["hoist"],
                mentionable=role_data["mentionable"],
                permissions=discord.Permissions(role_data["permissions"])
            )
            role_mapping[role_data["name"]] = role

        # Criar categorias
        category_mapping = {}
        for channel_data in backup["channels"]:
            if channel_data["type"] == "category":
                category = await guild.create_category(
                    name=channel_data["name"],
                    position=channel_data["position"],
                    overwrites=self._convert_overwrites(channel_data["overwrites"], role_mapping)
                )
                category_mapping[channel_data["name"]] = category

        # Criar canais
        for channel_data in backup["channels"]:
            if channel_data["type"] != "category":
                parent = category_mapping.get(channel_data["parent"])
                
                if channel_data["type"] == "text":
                    channel = await guild.create_text_channel(
                        name=channel_data["name"],
                        category=parent,
                        position=channel_data["position"],
                        topic=channel_data.get("topic"),
                        nsfw=channel_data.get("nsfw", False),
                        slowmode_delay=channel_data.get("slowmode_delay", 0),
                        overwrites=self._convert_overwrites(channel_data["overwrites"], role_mapping)
                    )
                elif channel_data["type"] == "voice":
                    channel = await guild.create_voice_channel(
                        name=channel_data["name"],
                        category=parent,
                        position=channel_data["position"],
                        bitrate=channel_data.get("bitrate", 64000),
                        user_limit=channel_data.get("user_limit", 0),
                        overwrites=self._convert_overwrites(channel_data["overwrites"], role_mapping)
                    )

        # Baixar e adicionar emojis
        for emoji_data in backup["emojis"]:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(emoji_data["url"]) as resp:
                        if resp.status == 200:
                            emoji_data = await resp.read()
                            await guild.create_custom_emoji(
                                name=emoji_data["name"],
                                image=emoji_data
                            )
            except discord.HTTPException:
                continue

    def _convert_overwrites(self, overwrites, role_mapping):
        """Converte overwrites do backup para o formato do Discord.py"""
        converted = {}
        for overwrite in overwrites:
            if overwrite["type"] == "role":
                role = role_mapping.get(overwrite["id"])
                if role:
                    converted[role] = discord.PermissionOverwrite(
                        allow=discord.Permissions(overwrite["allow"]),
                        deny=discord.Permissions(overwrite["deny"])
                    )
        return converted

    @app_commands.command(name="backup", description="Gerencia backups do servidor")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup(self, interaction: discord.Interaction):
        """Comando principal de backup"""
        # Verificar se o usuário tem permissão
        if interaction.user.id not in [1243889655087370270, 1332644814344425593]:
            await interaction.response.send_message(
                "Você não tem permissão para usar este comando!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💾 Sistema de Backup",
            description="Gerencie os backups do servidor",
            color=discord.Color.default()
        )

        # Listar backups existentes
        backups = [f for f in os.listdir(self.backup_dir) if f.endswith(".json")]
        if backups:
            backup_list = "\n".join([f"• {backup}" for backup in sorted(backups, reverse=True)[:5]])
            embed.add_field(
                name="Backups Recentes",
                value=backup_list,
                inline=False
            )
        else:
            embed.add_field(
                name="Backups",
                value="Nenhum backup encontrado",
                inline=False
            )

        view = BackupView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class BackupView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Criar Backup", style=discord.ButtonStyle.primary, row=0)
    async def create_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            filename = await self.cog.save_backup(interaction.guild)
            
            embed = discord.Embed(
                title="✅ Backup Criado",
                description=f"Backup salvo como: `{filename}`",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro ao Criar Backup",
                description=f"Erro: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Restaurar Backup", style=discord.ButtonStyle.primary, row=0)
    async def restore_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        backups = [f for f in os.listdir(self.cog.backup_dir) if f.endswith(".json")]
        if not backups:
            await interaction.response.send_message("Nenhum backup disponível para restaurar!", ephemeral=True)
            return

        view = RestoreView(self.cog, backups)
        await interaction.response.send_message("Selecione o backup para restaurar:", view=view, ephemeral=True)

    @discord.ui.button(label="Baixar Backup", style=discord.ButtonStyle.primary, row=0)
    async def download_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        backups = [f for f in os.listdir(self.cog.backup_dir) if f.endswith(".json")]
        if not backups:
            await interaction.response.send_message("Nenhum backup disponível para baixar!", ephemeral=True)
            return

        view = DownloadView(self.cog, backups)
        await interaction.response.send_message("Selecione o backup para baixar:", view=view, ephemeral=True)

class RestoreView(discord.ui.View):
    def __init__(self, cog, backups):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(RestoreSelect(backups))

class RestoreSelect(discord.ui.Select):
    def __init__(self, backups):
        options = [
            discord.SelectOption(
                label=backup,
                description=f"Backup de {backup.split('_')[1]}"
            )
            for backup in sorted(backups, reverse=True)
        ]
        super().__init__(
            placeholder="Selecione um backup",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            await self.view.cog.load_backup(interaction.guild, self.values[0])
            
            embed = discord.Embed(
                title="✅ Backup Restaurado",
                description=f"Backup `{self.values[0]}` foi restaurado com sucesso!",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro ao Restaurar Backup",
                description=f"Erro: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class DownloadView(discord.ui.View):
    def __init__(self, cog, backups):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(DownloadSelect(backups))

class DownloadSelect(discord.ui.Select):
    def __init__(self, backups):
        options = [
            discord.SelectOption(
                label=backup,
                description=f"Backup de {backup.split('_')[1]}"
            )
            for backup in sorted(backups, reverse=True)
        ]
        super().__init__(
            placeholder="Selecione um backup",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            filepath = os.path.join(self.view.cog.backup_dir, self.values[0])
            
            # Criar arquivo ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.write(filepath, self.values[0])
            
            zip_buffer.seek(0)
            
            # Enviar arquivo
            await interaction.followup.send(
                f"Aqui está seu backup:",
                file=discord.File(zip_buffer, f"{self.values[0]}.zip"),
                ephemeral=True
            )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro ao Baixar Backup",
                description=f"Erro: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot)) 