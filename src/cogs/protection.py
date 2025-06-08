import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Set, List, Tuple # Importando Tuple
import re
import sqlite3
import Levenshtein
from discord.ui import Button, View
from discord import ButtonStyle

class Protection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.protection_config_file = "data/protection_config.json"
        self.protection_config: Dict[str, Any] = {}
        self.load_protection_config()
        # Modificado para armazenar (membro, timestamp)
        self.recent_joins: Dict[int, List[Tuple[discord.Member, int]]] = {}  # Guild ID: List of (Member, Join Timestamp)
        self.raid_mode_active: Dict[int, bool] = {}  # Track raid mode status per guild
        self.load_raid_mode_status()
        self.db_file = "data/moderation.db"
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.create_table()

        self.task = self.check_raids
        # Define o loop para rodar a cada 60 segundos
        # Não é necessário chamar change_interval aqui, o decorator já define.
        # self.check_raids.change_interval(seconds=60)


    @tasks.loop(seconds=60)
    async def check_raids(self):
        # print("Executando verificação de raids...") # Pode manter ou remover este print
        current_time = int(time.time())
        # Define a janela de tempo recente (últimos 60 segundos, correspondendo ao loop interval)
        recent_window = 60

        # Crie uma cópia das chaves para iterar de forma segura
        guild_ids_to_process = list(self.recent_joins.keys())

        for guild_id in guild_ids_to_process:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                # Remove a entrada se o guild não for encontrado ou se o bot saiu
                if guild_id in self.recent_joins:
                    del self.recent_joins[guild_id]
                continue

            config = self.protection_config.get(str(guild_id), {})
            raid_mode_active = self.raid_mode_active.get(guild_id, False)
            threshold = config.get("raid_threshold", 5)
            log_channel_id = config.get("log_channel")
            log_channel = guild.get_channel(log_channel_id) if log_channel_id else None

            # Filtra membros que entraram na janela de tempo recente
            # Mantenha apenas membros que entraram na janela atual para processamento
            members_to_check_in_this_window = [(member, ts) for member, ts in self.recent_joins.get(guild_id, []) if current_time - ts <= recent_window]

            if raid_mode_active and len(members_to_check_in_this_window) >= threshold:
                print(f"Potencial raid detectado no servidor {guild.name} ({guild_id}). {len(members_to_check_in_this_window)} membros juntaram recentemente.")

                suspect_members = []
                for member, join_timestamp in members_to_check_in_this_window:
                    suspect_level = 0
                    # Aplicar verificações configuradas
                    if config.get("check_username", True):
                         suspect_level += self.analyze_username(member.name)

                    if config.get("check_account_age", True):
                         # Adiciona ponto se a conta for muito nova (ex: menos de 1 dia)
                         account_creation_time = int(member.created_at.timestamp())
                         if current_time - account_creation_time <= 86400: # 86400 segundos = 1 dia
                             suspect_level += 5 # Peso ajustável para idade da conta

                    if config.get("check_avatar", True):
                         # Adiciona ponto se o membro não tem avatar customizado (usa o avatar padrão)
                         if member.avatar is None or (member.avatar and "embed/avatars/" in str(member.avatar.url)):
                              suspect_level += 3 # Peso ajustável para avatar padrão


                    if config.get("check_similarity", True):
                         # Verifica similaridade com OUTROS membros que entraram RECENTEMENTE nesta janela
                         recent_peers = [m for m, ts in members_to_check_in_this_window if m.id != member.id]
                         for peer_member in recent_peers:
                            name_sim = self.similarity(member.name, peer_member.name)
                            if name_sim > 0.8: # Limite de similaridade ajustável
                                suspect_level += 5 # Peso ajustável para similaridade de nome
                            if member.display_avatar and peer_member.display_avatar and member.display_avatar.url == peer_member.display_avatar.url:
                                suspect_level += 7 # Peso ajustável para similaridade de avatar


                    # Se o suspect_level total exceder o threshold configurado
                    if suspect_level >= threshold: # Usando o threshold como exemplo de limite de suspeição individual
                        suspect_members.append((member, suspect_level))

                if suspect_members:
                    action_taken = False
                    for member, level in suspect_members:
                         try:
                              # Exemplo de ação: Kickar o membro suspeito
                              reason = f"Potencial membro de raid (Suspect Level: {level})"
                              # Verifique se o membro ainda está no servidor antes de tentar kickar
                              if guild.get_member(member.id):
                                  await guild.kick(member, reason=reason)
                                  self.log_action(member.id, self.bot.user.id, "kick", reason, member.name)
                                  print(f"Kickado membro {member.name} ({member.id}) no servidor {guild.name} por ser suspeito de raid.")
                                  if log_channel:
                                       await log_channel.send(f"🛡️ | Membro {member.mention} (`{member.name}#{member.discriminator}`) foi kickado por suspeita de raid (Suspect Level: {level}).")
                                  action_taken = True
                              else:
                                  print(f"Membro {member.name} ({member.id}) já saiu do servidor {guild.name}.")

                         except Exception as e:
                              print(f"Não foi possível kickar membro {member.name} ({member.id}) no servidor {guild.name}: {e}")
                              if log_channel:
                                   await log_channel.send(f"⚠️ | Não foi possível kickar membro {member.mention} (`{member.name}#{member.discriminator}`) no servidor {guild.name} por suspeita de raid: {e}")

                    if action_taken and log_channel:
                        # Opcional: Enviar uma mensagem geral de alerta após tomar ações
                        await log_channel.send(f"🚨 | Múltiplos membros suspeitos de raid foram detectados e ações foram tomadas no servidor {guild.name}.")

            # Limpar a lista de membros recentes, removendo APENAS os que saíram da janela de tempo
            # Mantenha na lista apenas os membros que AINDA estão dentro da janela de tempo recente para a próxima verificação
            if guild_id in self.recent_joins:
                 self.recent_joins[guild_id] = [(member, ts) for member, ts in self.recent_joins[guild_id] if current_time - ts <= recent_window]
                 # Opcional: remove a chave do dicionário se a lista ficar vazia
                 if not self.recent_joins[guild_id]:
                     del self.recent_joins[guild_id]


    @check_raids.before_loop
    async def before_check_raids(self):
        await self.bot.wait_until_ready()
        print("Tarefa check_raids esperando o bot ficar pronto...")

    # Adiciona o listener on_member_join
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = member.guild.id
        join_time = int(time.time())
        # Adiciona o membro e o timestamp de entrada
        self.recent_joins.setdefault(guild_id, []).append((member, join_time))
        print(f"Membro {member.name} ({member.id}) juntou-se ao servidor {member.guild.name} ({guild_id}). Adicionado à lista de recentes com timestamp {join_time}.")


    def load_raid_mode_status(self):
        for guild in self.bot.guilds:
            self.raid_mode_active[guild.id] = False

    def load_protection_config(self):
        if os.path.exists(self.protection_config_file):
            with open(self.protection_config_file, "r", encoding="utf-8") as f:
                try:
                    self.protection_config = json.load(f)
                except json.JSONDecodeError:
                    self.protection_config = {}
        else:
            self.protection_config = {}

    def save_protection_config(self):
        try:
            with open(self.protection_config_file, "w", encoding="utf-8") as f:
                json.dump(self.protection_config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao salvar a configuração de proteção: {e}")

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS moderation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                username TEXT,
                timestamp INTEGER
            )
        """)
        self.conn.commit()

    def log_action(self, user_id: int, moderator_id: int, action: str, reason: str, username: str):
        timestamp = int(time.time())
        self.cursor.execute("INSERT INTO moderation_log (user_id, moderator_id, action, reason, username, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                            (user_id, moderator_id, action, reason, username, timestamp))
        self.conn.commit()

    def analyze_username(self, username: str) -> int:
        suspect_level = 0

        # Critério 1: Nomes de usuário com muitos números
        num_digits = sum(c.isdigit() for c in username)
        if num_digits > len(username) / 2:
            suspect_level += 2

        # Critério 2: Nomes de usuário com muitos caracteres aleatórios
        # O import re deve estar no topo do arquivo
        # import re
        non_alphanumeric_count = len(re.findall(r'[^a-zA-Z0-9]', username))
        if non_alphanumeric_count > len(username) / 3:
            suspect_level += 3

        # Critério 3: Nomes de usuário curtos demais (comum em contas de raid)
        if len(username) < 3:
            suspect_level += 1

        # Critério 4: Lista negra de palavras
        blacklist = ["raid", "bot", "free", "nitro"]
        for word in blacklist:
            if word in username.lower():
                suspect_level += 4

        # Critério 5: Muitos caracteres Unicode
        unicode_count = 0
        for char in username:
            if ord(char) > 127:  # Basicamente, se não for ASCII
                unicode_count += 1
        if unicode_count > len(username) / 4:
            suspect_level += 2

        return suspect_level

    def similarity(self, s1, s2):
        if not isinstance(s1, str) or not isinstance(s2, str):
            return 0.0
        longer = s1 if len(s1) > len(s2) else s2
        shorter = s1 if len(s1) < len(s2) else s2
        if len(shorter) == 0:
            return 0.0

        longer_length = len(longer)
        distance = Levenshtein.distance(longer, shorter)
        return (longer_length - distance) / longer_length

    async def assess_similarity(self, member: discord.Member) -> int:
        suspect_level = 0
        # Verifica similaridade com outros membros recém chegados
        # Esta lógica agora compara o membro atual com TODOS na lista recent_joins do guild
        # Se a intenção for comparar apenas com outros da janela de tempo atual,
        # essa função precisaria receber a lista members_to_check_in_this_window
        # da função check_raids. Mantendo a lógica original por enquanto, mas com a ressalva.
        for other_member, other_ts in self.recent_joins.get(member.guild.id, []):
            if member.id != other_member.id:
                name_sim = self.similarity(member.name, other_member.name)
                if name_sim > 0.8:
                    suspect_level += 5
                if member.display_avatar and other_member.display_avatar and member.display_avatar.url == other_member.display_avatar.url:
                    suspect_level += 7
        return suspect_level

    @app_commands.command(name="raidmode", description="Configurações avançadas de anti-raid")
    @app_commands.checks.has_permissions(administrator=True)
    async def raidmode(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        config = self.protection_config.setdefault(str(guild_id), {})

        # Load settings from config, default to True if not set
        check_username = config.get("check_username", True)
        check_account_age = config.get("check_account_age", True)
        check_avatar = config.get("check_avatar", True)
        check_similarity = config.get("check_similarity", True)
        raid_mode_active = config.get("raid_mode_active", False)
        threshold = config.get("raid_threshold", 5)

        # Build the embed
        embed = discord.Embed(title="Configurações do Modo Anti-Raid", color=discord.Color.from_rgb(66, 0, 0))
        embed.add_field(name="Modo Anti-Raid", value="Ativado" if raid_mode_active else "Desativado", inline=False)
        embed.add_field(name="Threshold", value=str(threshold), inline=False)
        embed.add_field(name="Análise de Nome de Usuário", value="Ativada" if check_username else "Desativada", inline=False)
        embed.add_field(name="Análise da Idade da Conta", value="Ativada" if check_account_age else "Desativada", inline=False)
        embed.add_field(name="Análise de Avatar", value="Ativada" if check_avatar else "Desativada", inline=False)
        embed.add_field(name="Análise de Similaridade", value="Ativada" if check_similarity else "Desativada", inline=False)

        # Create the buttons
        username_button = Button(style=ButtonStyle.secondary, label="Nome de Usuário", emoji="👤", custom_id="username_check")
        account_age_button = Button(style=ButtonStyle.secondary, label="Idade da Conta", emoji="🗓️", custom_id="account_age_check")
        avatar_button = Button(style=ButtonStyle.secondary, label="Avatar", emoji="🖼️", custom_id="avatar_check")
        similarity_button = Button(style=ButtonStyle.secondary, label="Similaridade", emoji="🤝", custom_id="similarity_check")
        raid_mode_button = Button(style=ButtonStyle.primary, label="Modo Anti-Raid", emoji="🛡️", custom_id="raid_mode")
        threshold_button = Button(style=ButtonStyle.secondary, label="Threshold", emoji="⚙️", custom_id="threshold_adjust")

        # Update button colors based on current settings
        if check_username: username_button.style = ButtonStyle.success
        if check_account_age: account_age_button.style = ButtonStyle.success
        if check_avatar: avatar_button.style = ButtonStyle.success
        if check_similarity: similarity_button.style = ButtonStyle.success
        if raid_mode_active: raid_mode_button.style = ButtonStyle.success

        # Create the view and add the buttons
        view = View()
        view.add_item(username_button)
        view.add_item(account_age_button)
        view.add_item(avatar_button)
        view.add_item(similarity_button)
        view.add_item(raid_mode_button)
        view.add_item(threshold_button)

        await interaction.response.send_message(embed=embed, view=view)

    async def update_raidmode_embed(self, interaction: discord.Interaction, guild_id: int):
        config = self.protection_config.setdefault(str(guild_id), {})
        threshold = config.get("raid_threshold", 5)
        check_username = config.get("check_username", True)
        check_account_age = config.get("check_account_age", True)
        check_avatar = config.get("check_avatar", True)
        check_similarity = config.get("check_similarity", True)
        raid_mode_active = config.get("raid_mode_active", False)

        embed = discord.Embed(title="Configurações do Modo Anti-Raid", color=discord.Color.from_rgb(66, 0, 0))
        embed.add_field(name="Modo Anti-Raid", value="Ativado" if raid_mode_active else "Desativado", inline=False)
        embed.add_field(name="Threshold", value=str(threshold), inline=False)
        embed.add_field(name="Análise de Nome de Usuário", value="Ativada" if check_username else "Desativada", inline=False)
        embed.add_field(name="Análise da Idade da Conta", value="Ativada" if check_account_age else "Desativada", inline=False)
        embed.add_field(name="Análise de Avatar", value="Ativada" if check_avatar else "Desativada", inline=False)
        embed.add_field(name="Análise de Similaridade", value="Ativada" if check_similarity else "Desativada", inline=False)

        # Create the buttons
        username_button = Button(style=ButtonStyle.secondary, label="Nome de Usuário", emoji="👤", custom_id="username_check")
        account_age_button = Button(style=ButtonStyle.secondary, label="Idade da Conta", emoji="🗓️", custom_id="account_age_check")
        avatar_button = Button(style=ButtonStyle.secondary, label="Avatar", emoji="🖼️", custom_id="avatar_check")
        similarity_button = Button(style=ButtonStyle.secondary, label="Similaridade", emoji="🤝", custom_id="similarity_check")
        raid_mode_button = Button(style=ButtonStyle.primary, label="Modo Anti-Raid", emoji="🛡️", custom_id="raid_mode")
        threshold_button = Button(style=ButtonStyle.secondary, label="Threshold", emoji="⚙️", custom_id="threshold_adjust")

        # Update button colors based on current settings
        if check_username: username_button.style = ButtonStyle.success
        else: username_button.style = ButtonStyle.secondary
        if check_account_age: account_age_button.style = ButtonStyle.success
        else: account_age_button.style = ButtonStyle.secondary
        if check_avatar: avatar_button.style = ButtonStyle.success
        else: avatar_button.style = ButtonStyle.secondary
        if check_similarity: similarity_button.style = ButtonStyle.success
        else: similarity_button.style = ButtonStyle.secondary
        if raid_mode_active: raid_mode_button.style = ButtonStyle.success
        else: raid_mode_button.style = ButtonStyle.primary

        # Create the view and add the buttons
        view = View()
        view.add_item(username_button)
        view.add_item(account_age_button)
        view.add_item(avatar_button)
        view.add_item(similarity_button)
        view.add_item(raid_mode_button)
        view.add_item(threshold_button)

        # Use followup.edit_message para editar a mensagem original
        # Verifique se interaction.message existe antes de tentar acessar o id
        if interaction.message:
             await interaction.followup.edit_message(interaction.message.id, embed=embed, view=view)
        else:
             # Se por algum motivo interaction.message não estiver disponível (improvável para componente interaction)             
             print("Erro: interaction.message não disponível para editar a mensagem.")
             # Opcional: enviar uma nova mensagem em vez de editar
             # await interaction.followup.send_message(embed=embed, view=view)



    @app_commands.describe(channel="Canal para logs")
    @app_commands.checks.has_permissions(administrator=True)
    async def setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id
        self.protection_config.setdefault(str(guild_id), {})["log_channel"] = channel.id
        self.save_protection_config()
        await interaction.response.send_message(f"Canal de log definido para {channel.mention}.")

    # Adiciona o listener on_member_join
    async def on_member_join(self, member: discord.Member):
        guild_id = member.guild.id
        join_time = int(time.time())
        # Adiciona o membro e o timestamp de entrada
        self.recent_joins.setdefault(guild_id, []).append((member, join_time))
        print(f"Membro {member.name} ({member.id}) juntou-se ao servidor {member.guild.name} ({guild_id}). Adicionado à lista de recentes com timestamp {join_time}.")


async def setup(bot: commands.Bot):
    cog = Protection(bot)
    await bot.add_cog(cog)

    @commands.Cog.listener()
    async def on_ready():
        cog.task.start()

    bot.add_listener(on_ready)

