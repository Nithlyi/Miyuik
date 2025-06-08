import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Set
import asyncio

# Define the leveladmin command group globally
#leveladmin = app_commands.Group(name="leveladmin", description="Comandos administrativos para o sistema de níveis")

class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.levels_file = "data/levels.json"
        self.levels_data: Dict[str, Any] = {} # Use type hinting
        self.xp_per_message = 15
        self.cooldown_seconds = 60
        self.user_message_cooldowns: Dict[str, float] = {} # {user_id: last_message_timestamp}
        self.disabled_channels: Set[int] = set()  # Store channel IDs where XP is disabled
        self.role_buffs: Dict[str, Dict[str, float]] = {}  # Store active role buffs {role_id: {"multiplier": float, "expires_at": float}}
        self.save_interval = 60

        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

        # Load levels data, disabled channels, and role buffs
        self.load_levels_data()

        # Start the background task to save levels data
        self.save_task = self.bot.loop.create_task(self.save_levels_loop())

    def cog_unload(self):
        # Cancel the save task when the cog is unloaded
        self.save_task.cancel()

    async def save_levels_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(self.save_interval)
            await self.save_levels_data()

    def load_levels_data(self):
        if os.path.exists(self.levels_file):
            with open(self.levels_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    self.levels_data = data.get("users", {})
                    self.disabled_channels = set(data.get("disabled_channels", []))
                    self.role_buffs = data.get("role_buffs", {})

                    # Ensure all users in loaded data have a 'buff' key, default to None
                    for user_data in self.levels_data.values():
                        user_data.setdefault("buff", None)

                except json.JSONDecodeError:
                    self.levels_data = {}
                    self.disabled_channels = set()
                    self.role_buffs = {}
        else:
            self.levels_data = {}
            self.disabled_channels = set()
            self.role_buffs = {}

    async def save_levels_data(self):
        # Before saving, remove 'buff': None entries from users and expired role buffs to keep the file cleaner
        users_to_save = {k: v for k, v in self.levels_data.items() if v.get("buff") is not None or v.get("xp") > 0}

        current_time = time.time()
        active_role_buffs = {k: v for k, v in self.role_buffs.items() if v.get("expires_at", 0) > current_time}

        data_to_save = {
            "users": users_to_save,
            "disabled_channels": list(self.disabled_channels),
            "role_buffs": active_role_buffs,
        }
        try:
            with open(self.levels_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving levels data: {e}")

    def get_user_xp(self, user_id: int) -> int:
        return self.levels_data.get(str(user_id), {}).get("xp", 0)

    def get_user_level(self, user_id: int) -> int:
        xp = self.get_user_xp(user_id)
        # Simple leveling formula: level = floor(0.1 * sqrt(xp))
        # Ensure result is non-negative
        return max(0, int(0.1 * (xp ** 0.5)))

    def get_xp_for_next_level(self, level: int) -> int:
        # Inverse of the leveling formula to find XP needed for the next level
        # xp = (level / 0.1)^2 = (level * 10)^2
        next_level = level + 1
        return (next_level * 10) ** 2

    # --- Listeners ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages, messages in DMs, or messages in disabled channels
        if message.author.bot or not message.guild or message.channel.id in self.disabled_channels:
            return

        user_id = str(message.author.id)
        current_time = time.time()

        # Check cooldown
        if user_id in self.user_message_cooldowns and current_time - self.user_message_cooldowns[user_id] < self.cooldown_seconds:
            return  # User is on cooldown

        # Update cooldown for the user
        self.user_message_cooldowns[user_id] = current_time

        # Ensure user exists in data with default values if not
        if user_id not in self.levels_data:
            self.levels_data[user_id] = {"xp": 0, "level": 0, "buff": None}

        # --- Buff Logic ---
        effective_multiplier = 1.0

        # Check personal buff
        user_buff = self.levels_data[user_id].get("buff")
        if user_buff:
            if current_time < user_buff.get("expires_at", 0):
                effective_multiplier = max(effective_multiplier, user_buff.get("multiplier", 1.0))
            else:
                # Buff has expired, remove it
                self.levels_data[user_id]["buff"] = None
                print(f"Buff de XP pessoal expirado para {message.author.display_name}.")  # Log for debugging
                # Consider sending a message to the user informing them their buff expired

        # Check role buffs
        # Clean up expired role buffs first
        expired_role_ids = [role_id for role_id, buff_data in self.role_buffs.items() if buff_data.get("expires_at", 0) < current_time]
        for role_id in expired_role_ids:
            del self.role_buffs[role_id]
            print(f"Buff de XP para o cargo {role_id} expirado e removido.")  # Log for debugging
            # Consider logging this event or sending a message to admins

        # Check if the user has any role with an active buff
        if message.author.roles:
            for role in message.author.roles:
                role_buff = self.role_buffs.get(str(role.id))
                if role_buff and current_time < role_buff.get("expires_at", 0):
                    effective_multiplier = max(effective_multiplier, role_buff.get("multiplier", 1.0))

        # Calculate XP to add based on the effective multiplier
        xp_to_add = int(self.xp_per_message * effective_multiplier)
        if effective_multiplier > 1.0:
            print(f"Aplicando multiplicador de XP ({effective_multiplier}x) para {message.author.display_name}. XP a adicionar: {xp_to_add}")  # Log for debugging when buff is applied

        # Add XP
        current_level = self.get_user_level(int(user_id))
        self.levels_data[user_id]["xp"] += xp_to_add
        new_level = self.get_user_level(int(user_id))

        # Level up message
        if new_level > current_level:
            self.levels_data[user_id]["level"] = new_level
            try:
                await message.channel.send(f"🎉 Parabéns, {message.author.mention}! Você alcançou o Nível {new_level}! 🎉", delete_after=10)
            except discord.errors.NotFound:
                pass  # Message might have been deleted before the bot could send the response

        # Save data (consider saving less frequently for performance on very active servers)
        # Saving is handled by the background task `save_levels_loop` now.

    # --- Admin Level Config Group ---
    levelconfig = app_commands.Group(name="levelconfig", description="Comandos de configuração do sistema de níveis")

    @levelconfig.command(name="setxppermessage", description="Define a quantidade de XP ganha por mensagem enviada")
    @app_commands.describe(amount="A quantidade de XP para cada mensagem")
    @app_commands.checks.has_permissions(administrator=True)
    async def setxppermessage(self, interaction: discord.Interaction, amount: int):
        if amount < 0:
            await interaction.response.send_message("A quantidade de XP por mensagem não pode ser negativa.", ephemeral=True)
            return

        self.xp_per_message = amount
        # Since xp_per_message is a setting, we should save it.
        # For now, it's only in memory. A more robust solution would save settings to the data file.
        # await self.save_levels_data() # Need to add settings to save data

        await interaction.response.send_message(f"✅ Quantidade de XP por mensagem definida para {amount}.", ephemeral=True)

    @levelconfig.command(name="addrolebuff", description="Aplica um buff de ganho de XP a um cargo")
    @app_commands.describe(role="Cargo para aplicar o buff", multiplier="Multiplicador de XP (ex: 2 para dobro)", duration_minutes="Duração do buff em minutos")
    @app_commands.checks.has_permissions(administrator=True)
    async def addrolebuff(self, interaction: discord.Interaction, role: discord.Role, multiplier: float, duration_minutes: int):
        if multiplier <= 0:
            await interaction.response.send_message("O multiplicador deve ser maior que zero.", ephemeral=True)
            return
        if duration_minutes <= 0:
            await interaction.response.send_message("A duração deve ser maior que zero minutos.", ephemeral=True)
            return

        role_id = str(role.id)
        current_time = time.time()
        expires_at = current_time + (duration_minutes * 60)

        self.role_buffs[role_id] = {
            "multiplier": multiplier,
            "expires_at": expires_at,
        }

        expiry_datetime = datetime.fromtimestamp(expires_at)
        await interaction.response.send_message(
            f"✨ Buff de XP ({multiplier}x por {duration_minutes} minutos) aplicado ao cargo {role.name}. Expira em {expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')}. ✨",
            ephemeral=True,
        )

    @levelconfig.command(name="removerolebuff", description="Remove um buff de XP de um cargo")
    @app_commands.describe(role="Cargo para remover o buff")
    @app_commands.checks.has_permissions(administrator=True)
    async def removerolebuff(self, interaction: discord.Interaction, role: discord.Role):
        role_id = str(role.id)

        if role_id in self.role_buffs:
            del self.role_buffs[role_id]
            await interaction.response.send_message(f"✅ Buff de XP removido do cargo {role.name}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ O cargo {role.name} não possui um buff de XP ativo.", ephemeral=True)

    @levelconfig.command(name="listbuffs", description="Lista todos os buffs de XP ativos (cargos e membros)")
    @app_commands.checks.has_permissions(administrator=True)
    async def listbuffs(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✨ Buffs de XP Ativos ✨",
            color=0x9932CC  # Purple
        )
        current_time = time.time()
        found_buffs = False

        # List Role Buffs
        role_buffs_text = ""
        for role_id, buff_data in self.role_buffs.items():
            expires_at = buff_data.get("expires_at", 0)
            if expires_at > current_time:
                found_buffs = True
                try:
                    # Fetch role name (requires bot to be in guild where role exists)
                    guild = interaction.guild
                    role = guild.get_role(int(role_id)) if guild else None
                    role_name = role.name if role else f"Unknown Role ({role_id})"

                    expiry_datetime = datetime.fromtimestamp(expires_at)
                    role_buffs_text += f"**{role_name}**: {buff_data.get("multiplier", 1.0)}x (Expira em {expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')})\n"
                except Exception as e:
                     print(f"Error fetching role for buff listing: {e}") # Log error but continue
                     role_buffs_text += f"**Unknown Role ({role_id})**: {buff_data.get("multiplier", 1.0)}x (Expira em {datetime.fromtimestamp(expires_at).strftime('%Y-%m-%d %H:%M:%S')})\n"

        if role_buffs_text:
            embed.add_field(name="👥 Buffs de Cargo", value=role_buffs_text, inline=False)

        # List User Buffs
        user_buffs_text = ""
        for user_id, user_data in self.levels_data.items():
            user_buff = user_data.get("buff")
            if user_buff:
                 expires_at = user_buff.get("expires_at", 0)
                 if expires_at > current_time:
                    found_buffs = True
                    try:
                        # Fetch user (requires user to be in bot's cache or guild)
                        user = self.bot.get_user(int(user_id))
                        user_name = user.display_name if user else f"Unknown User ({user_id})"

                        expiry_datetime = datetime.fromtimestamp(expires_at)
                        user_buffs_text += f"**{user_name}**: {user_buff.get("multiplier", 1.0)}x (Expira em {expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')})\n"
                    except Exception as e:
                        print(f"Error fetching user for buff listing: {e}") # Log error but continue
                        user_buffs_text += f"**Unknown User ({user_id})**: {user_buff.get("multiplier", 1.0)}x (Expira em {datetime.fromtimestamp(expires_at).strftime('%Y-%m-%d %H:%M:%S')})\n"

        if user_buffs_text:
            embed.add_field(name="👤 Buffs de Membro", value=user_buffs_text, inline=False)

        if not found_buffs:
            embed.description = "Nenhum buff de XP ativo no momento."

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @levelconfig.command(name="togglelevelupmessage", description="Ativa/desativa mensagens de level up em um canal")
    @app_commands.describe(channel="Canal para alternar o estado das mensagens de level up")
    @app_commands.checks.has_permissions(administrator=True)
    async def togglelevelupmessage(self, interaction: discord.Interaction, channel: discord.TextChannel):
        channel_id = channel.id

        if channel_id in self.disabled_channels:
            self.disabled_channels.remove(channel_id)
            await interaction.response.send_message(f"✅ Mensagens de level up ativadas no canal {channel.mention}.", ephemeral=True)
        else:
            self.disabled_channels.add(channel_id)
            await interaction.response.send_message(f"❌ Mensagens de level up desativadas no canal {channel.mention}.", ephemeral=True)

        # Note: self.disabled_channels is saved by the background task.

    # --- User Commands ---
    @app_commands.command(name="level", description="Mostra seu nível e XP atual")
    @app_commands.describe(member="Membro para verificar o nível (opcional)")
    async def level(self, interaction: discord.Interaction, member: discord.Member = None):
        user = member if member else interaction.user
        user_id = str(user.id)

        if user_id not in self.levels_data or "xp" not in self.levels_data[user_id]:
            if user == interaction.user:
                await interaction.response.send_message("Você ainda não ganhou nenhum XP. Comece a conversar para subir de nível!", ephemeral=True)
            else:
                await interaction.response.send_message(f"{user.display_name} ainda não ganhou nenhum XP.", ephemeral=True)
            return

        xp = self.get_user_xp(int(user_id))
        level = self.get_user_level(int(user_id))
        xp_for_current_level_start = self.get_xp_for_next_level(level - 1) if level > 0 else 0
        xp_needed_for_next_level = self.get_xp_for_next_level(level)
        xp_in_current_level = xp - xp_for_current_level_start
        total_xp_for_level = xp_needed_for_next_level - xp_for_current_level_start

        # Calculate progress percentage
        if total_xp_for_level > 0:
            progress_percentage = (xp_in_current_level / total_xp_for_level) * 100
        else:
            progress_percentage = 100  # Avoid division by zero, if already at a very high level or formula issue

        # Create progress bar
        bar_length = 15  # Slightly shorter bar
        filled_length = int(bar_length * progress_percentage // 100)
        bar = '⬛' * filled_length + '⬜' * (bar_length - filled_length)  # Using black and white squares

        embed = discord.Embed(
            title=f"✨ Progresso de Nível de {user.display_name} ✨",  # Aesthetic title
            color=0x8B0000  # Dark Red color
        )

        if user.display_avatar:
            embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="🌟 Nível Atual", value=level, inline=True)  # Aesthetic field name
        embed.add_field(name="✨ XP Total", value=xp, inline=True)  # Aesthetic field name
        embed.add_field(name="📈 Progresso para o Próximo Nível", value=f"{bar}\n{xp_in_current_level}/{total_xp_for_level} XP ({progress_percentage:.2f}%)", inline=False)  # Added progress bar to the value

        embed.set_footer(text="Continue conversando para subir de nível!", icon_url=self.bot.user.display_avatar.url)  # Add footer with bot avatar

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Mostra o ranking de níveis do servidor")
    @app_commands.guild_only()  # This command only makes sense in a guild
    async def leaderboard(self, interaction: discord.Interaction, limit: int = 10):
        if not self.levels_data:
            await interaction.response.send_message("Ainda não há dados de nível para exibir no ranking.", ephemeral=True)
            return

        # Get users with XP and sort them by XP in descending order
        sorted_users = sorted(
            [(user_id, data["xp"]) for user_id, data in self.levels_data.items() if data["xp"] > 0],
            key=lambda item: item[1],
            reverse=True,
        )

        if not sorted_users:
            await interaction.response.send_message("Ainda n��o há usuários com XP para exibir no ranking.", ephemeral=True)
            return

        # Limit the number of users to display
        top_users = sorted_users[:limit]

        embed = discord.Embed(
            title="🏆 Ranking de Níveis do Servidor 🏆",  # Título Estético
            color=0x420000,  # Vermelho Escuro
        )

        # Adiciona um campo para cada usuário no ranking
        for rank, (user_id, xp) in enumerate(top_users, 1):
            user = self.bot.get_user(int(user_id))

            if user:
                level = self.get_user_level(int(user_id))
                # Pega o avatar do usuário (se disponível)
                avatar = user.display_avatar.url if user.display_avatar else None

                # Cria a descrição do campo com emoji, nome, nível e XP
                description = f"**Nível:** {level}\n**XP:** {xp}"

                # Adiciona o campo ao embed
                embed.add_field(
                    name=f"#{rank} - {user.display_name}",  # Título do campo: Posição - Nome
                    value=description,  # Descrição: Nível e XP
                    inline=False,  # Garante que cada usuário fique em uma linha separada
                )
                if rank == 1 and user.display_avatar:  # apenas no primeiro lugar
                    embed.set_thumbnail(url=user.display_avatar.url)

            else:
                # Se o usuário não for encontrado
                embed.add_field(
                    name=f"#{rank} - Usuário Desconhecido",
                    value=f"ID: {user_id}\nXP: {xp}",
                    inline=False,
                )

        embed.set_footer(text=f"Exibindo os Top {len(top_users)}", icon_url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    level_rewards = {
        5: "Cargo VIP",
        10: "Acesso a um canal especial",
        15: "Permissão para usar comandos personalizados",
    }

    @app_commands.command(name="levelrewards", description="Mostra as recompensas para cada nível")
    async def levelrewards(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏆 Recompensas de Nível 🏆",
            color=0x00FF00,  # Verde
        )

        for level, reward in self.level_rewards.items():
            embed.add_field(name=f"Nível {level}", value=reward, inline=False)

        embed.set_footer(text="Continue subindo de nível para desbloquear recompensas!", icon_url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="addxp", description="Adiciona XP a um membro")
    @app_commands.describe(member="Membro para adicionar XP", xp="Quantidade de XP para adicionar")
    @app_commands.checks.has_permissions(administrator=True)
    async def addxp(self, interaction: discord.Interaction, member: discord.Member, xp: int):
        user_id = str(member.id)
        if user_id not in self.levels_data:
            self.levels_data[user_id] = {"xp": 0, "level": 0}

        self.levels_data[user_id]["xp"] += xp
        self.levels_data[user_id]["level"] = self.get_user_level(member.id)  # Recalculate level

        await interaction.response.send_message(f"✅ Adicionado {xp} XP a {member.display_name}. Nível atual: {self.get_user_level(member.id)} ✅", ephemeral=True)

    @app_commands.command(name="removexp", description="Remove XP de um membro")
    @app_commands.describe(member="Membro para remover XP", xp="Quantidade de XP para remover")
    @app_commands.checks.has_permissions(administrator=True)
    async def removexp(self, interaction: discord.Interaction, member: discord.Member, xp: int):
        user_id = str(member.id)
        if user_id not in self.levels_data:
            self.levels_data[user_id] = {"xp": 0, "level": 0}

        self.levels_data[user_id]["xp"] -= xp
        if self.levels_data[user_id]["xp"] < 0:
            self.levels_data[user_id]["xp"] = 0  # Impede XP negativo

        self.levels_data[user_id]["level"] = self.get_user_level(member.id)  # Recalculate level

        await interaction.response.send_message(f"✅ Removido {xp} XP de {member.display_name}. Nível atual: {self.get_user_level(member.id)} ✅", ephemeral=True)

    @app_commands.command(name="applybuff", description="Aplica um buff de ganho de XP a um membro")
    @app_commands.describe(member="Membro para aplicar o buff", multiplier="Multiplicador de XP (ex: 2 para dobro)", duration_minutes="Duração do buff em minutos")
    @app_commands.checks.has_permissions(administrator=True)
    async def applybuff(self, interaction: discord.Interaction, member: discord.Member, multiplier: float, duration_minutes: int):
        if multiplier <= 0:
            await interaction.response.send_message("O multiplicador deve ser maior que zero.", ephemeral=True)
            return
        if duration_minutes <= 0:
            await interaction.response.send_message("A duração deve ser maior que zero minutos.", ephemeral=True)
            return

        user_id = str(member.id)
        current_time = time.time()
        expires_at = current_time + (duration_minutes * 60)

        # Store buff information
        # Ensure user data exists
        if user_id not in self.levels_data:
            self.levels_data[user_id] = {"xp": 0, "level": 0, "buff": None}

        self.levels_data[user_id]["buff"] = {
            "multiplier": multiplier,
            "expires_at": expires_at,
        }

        # Confirm to the admin
        expiry_datetime = datetime.fromtimestamp(expires_at)
        await interaction.response.send_message(
            f"✨ Buff de XP ({multiplier}x por {duration_minutes} minutos) aplicado a {member.display_name}. Expira em {expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')}. ✨",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))