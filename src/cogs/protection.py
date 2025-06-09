# c:\Users\Miko\Downloads\Miy\src\cogs\protection.py
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
import Levenshtein # Certifique-se de ter a biblioteca 'python-Levenshtein' instalada (pip install python-Levenshtein)
from discord.ui import Button, View
from discord import ButtonStyle

# Define a janela de tempo maior para manter membros recentes (em segundos, ex: 5 minutos)
RECENT_JOINS_WINDOW = 300 # 5 minutos
# Define a janela de tempo para detecção de pico (em segundos, ex: 60 segundos)
SPIKE_DETECTION_WINDOW = 60

class Protection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.protection_config_file = "data/protection_config.json"
        self.protection_config: Dict[str, Any] = {}
        self.load_protection_config()
        # Armazena (membro.id, timestamp) para evitar problemas de pickle/serialização
        self.recent_joins: Dict[int, List[Tuple[int, int]]] = {}  # Guild ID: List of (Member ID, Join Timestamp)
        self.raid_mode_active: Dict[int, bool] = {}  # Track raid mode status per guild
        self.db_file = "data/moderation.db"
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.create_table()

        # Inicializa o estado do raid mode para os guilds atuais
        # O estado será gerenciado dinamicamente por guild join/leave e comandos
        for guild in self.bot.guilds:
             self.raid_mode_active.setdefault(guild.id, False)


    @tasks.loop(seconds=SPIKE_DETECTION_WINDOW) # Loop roda a cada SPIKE_DETECTION_WINDOW segundos
    async def check_raids(self):
        # print("Executando verificação de raids...")
        current_time = int(time.time())

        # Crie uma cópia das chaves para iterar de forma segura
        guild_ids_to_process = list(self.recent_joins.keys())

        for guild_id in guild_ids_to_process:
            guild = self.bot.get_guild(guild_id)
            # Remove a entrada se o guild não for encontrado ou se o bot saiu
            if not guild:
                if guild_id in self.recent_joins:
                    del self.recent_joins[guild_id]
                if guild_id in self.raid_mode_active:
                    del self.raid_mode_active[guild_id]
                continue

            config = self.protection_config.get(str(guild_id), {})
            raid_mode_active = self.raid_mode_active.get(guild_id, False)
            threshold = config.get("raid_threshold", 5)
            log_channel_id = config.get("log_channel")
            log_channel = guild.get_channel(log_channel_id) if log_channel_id else None

            # FILTRA: Mantenha na lista self.recent_joins apenas membros que entraram DENTRO da janela RECENT_JOINS_WINDOW
            # Limpa a lista antes de contar para a detecção de pico
            if guild_id in self.recent_joins:
                 self.recent_joins[guild_id] = [(member_id, ts) for member_id, ts in self.recent_joins[guild_id] if current_time - ts <= RECENT_JOINS_WINDOW]

            # CONTA: Conta quantos membros na lista filtrada entraram DENTRO da janela SPIKE_DETECTION_WINDOW
            recent_joins_in_spike_window = [(member_id, ts) for member_id, ts in self.recent_joins.get(guild_id, []) if current_time - ts <= SPIKE_DETECTION_WINDOW]
            num_recent_joins = len(recent_joins_in_spike_window)

            # Lógica de detecção de pico e processamento
            if raid_mode_active and num_recent_joins >= threshold:
                print(f"Potencial pico de junções detectado no servidor {guild.name} ({guild_id}). {num_recent_joins} membros juntaram nos últimos {SPIKE_DETECTION_WINDOW} segundos.")

                suspect_members_info = [] # Armazena (Member object, suspect_level)
                members_to_analyze = [] # Lista para buscar os objetos Member

                # Coleta os IDs dos membros que entraram na janela de pico para análise
                for member_id, ts in recent_joins_in_spike_window:
                    member = guild.get_member(member_id)
                    if member:
                        members_to_analyze.append(member)

                if members_to_analyze:
                    # Realiza a análise e coleta suspeitos
                    for member in members_to_analyze:
                        suspect_level = 0
                        # Aplicar verificações configuradas
                        if config.get("check_username", True):
                             suspect_level += self.analyze_username(member.name)

                        if config.get("check_account_age", True):
                             account_creation_time = int(member.created_at.timestamp())
                             if current_time - account_creation_time <= 86400: # 86400 segundos = 1 dia
                                 suspect_level += 5 # Peso ajustável

                        if config.get("check_avatar", True):
                             if member.avatar is None or (member.avatar and "embed/avatars/" in str(member.avatar.url)):
                                  suspect_level += 3 # Peso ajustável

                        if config.get("check_similarity", True):
                            # Verifica similaridade com OUTROS membros que entraram NESTA JANELA DE PICO
                            # Cria um conjunto de nomes e avatares para verificar duplicados/similares eficientemente
                            recent_peers_data = [(m.name, str(m.display_avatar.url) if m.display_avatar else None) for m in members_to_analyze if m.id != member.id]
                            member_avatar_url = str(member.display_avatar.url) if member.display_avatar else None

                            for peer_name, peer_avatar_url in recent_peers_data:
                                # Verifica similaridade de nome
                                if self.similarity(member.name, peer_name) > 0.8: # Limite de similaridade ajustável
                                    suspect_level += 5 # Peso ajustável

                                # Verifica similaridade de avatar (exata)
                                if member_avatar_url and peer_avatar_url and member_avatar_url == peer_avatar_url:
                                    suspect_level += 7 # Peso ajustável
                                    break # Assume que um avatar duplicado já é um forte indicador, pode parar de verificar outros peers para avatar


                        # Se o suspect_level total exceder o threshold configurado para ações
                        # Pode usar um threshold diferente para a ação do que para a detecção do pico
                        action_threshold = config.get("action_threshold", threshold) # Usando o mesmo threshold por padrão, mas pode ser separado
                        if suspect_level >= action_threshold:
                            suspect_members_info.append((member, suspect_level))

                    if suspect_members_info:
                        action_taken = False
                        for member, level in suspect_members_info:
                             try:
                                  reason = f"Potencial membro de raid (Suspect Level: {level})"
                                  # Verifique se o membro ainda está no servidor antes de tentar kickar
                                  if guild.get_member(member.id):
                                      await guild.kick(member, reason=reason)
                                      # Use self.bot.user.id como moderator_id para ações automáticas
                                      self.log_action(member.id, self.bot.user.id, "kick", reason, f"{member.name}#{member.discriminator}")
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
                            await log_channel.send(f"🚨 | Múltiplos membros suspeitos de raid foram detectados e ações foram tomadas no servidor {guild.name}.")

            # Opcional: Limpa completamente a lista de joins recentes de um guild se ela ficar vazia
            if guild_id in self.recent_joins and not self.recent_joins[guild_id]:
                 del self.recent_joins[guild_id]


    @check_raids.before_loop
    async def before_check_raids(self):
        await self.bot.wait_until_ready()
        print("Tarefa check_raids esperando o bot ficar pronto...")
        # Inicializa o raid mode para todos os guilds após o bot estar pronto
        for guild in self.bot.guilds:
             self.raid_mode_active.setdefault(guild.id, False)


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = member.guild.id
        join_time = int(time.time())
        # Armazena o ID do membro e o timestamp de entrada
        self.recent_joins.setdefault(guild_id, []).append((member.id, join_time))
        # Remove entradas antigas imediatamente ao adicionar uma nova, mantendo apenas dentro da janela maior
        self.recent_joins[guild_id] = [(mid, ts) for mid, ts in self.recent_joins[guild_id] if join_time - ts <= RECENT_JOINS_WINDOW]
        print(f"Membro {member.name} ({member.id}) juntou-se ao servidor {member.guild.name} ({guild_id}). Adicionado à lista de recentes com timestamp {join_time}.")


    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        # Inicializa o estado do raid mode para o novo guild
        self.raid_mode_active.setdefault(guild.id, False)
        print(f"Bot juntou-se ao servidor {guild.name} ({guild.id}). Inicializando estado de proteção.")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        # Limpa os dados do guild que o bot saiu
        if guild.id in self.recent_joins:
            del self.recent_joins[guild.id]
        if guild.id in self.raid_mode_active:
            del self.raid_mode_active[guild.id]
        print(f"Bot saiu do servidor {guild.name} ({guild.id}). Limpando dados de proteção.")


    def load_protection_config(self):
        if os.path.exists(self.protection_config_file):
            with open(self.protection_config_file, "r", encoding="utf-8") as f:
                try:
                    self.protection_config = json.load(f)
                except json.JSONDecodeError:
                    print(f"Erro ao decodificar JSON em {self.protection_config_file}. O arquivo pode estar corrompido. Usando configuração vazia.")
                    self.protection_config = {}
        else:
            self.protection_config = {}
            print(f"Arquivo de configuração {self.protection_config_file} não encontrado. Usando configuração vazia.")


    def save_protection_config(self):
        try:
            # Certifica-se de que o diretório 'data' existe antes de salvar
            os.makedirs(os.path.dirname(self.protection_config_file), exist_ok=True)
            with open(self.protection_config_file, "w", encoding="utf-8") as f:
                # Converte chaves de int para str para salvar em JSON, se necessário (embora o código já use str(guild_id))
                # Garante que apenas dados serializáveis estão sendo salvos
                serializable_config = {k: v for k, v in self.protection_config.items()}
                json.dump(serializable_config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao salvar a configuração de proteção em {self.protection_config_file}: {e}")

    def create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS moderation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    action TEXT,
                    reason TEXT,
                    username TEXT, -- Armazena o nome de usuário na hora da ação
                    timestamp INTEGER,
                    guild_id INTEGER -- Adiciona coluna para o ID do guild
                )
            """)
            self.conn.commit()
        except Exception as e:
            print(f"Erro ao criar tabela moderation_log: {e}")


    def log_action(self, user_id: int, moderator_id: int, action: str, reason: str, username: str, guild_id: int):
        timestamp = int(time.time())
        try:
            self.cursor.execute("INSERT INTO moderation_log (user_id, moderator_id, action, reason, username, timestamp, guild_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (user_id, moderator_id, action, reason, username, timestamp, guild_id))
            self.conn.commit()
        except Exception as e:
            print(f"Erro ao logar ação de moderação: {e}")

    def analyze_username(self, username: str) -> int:
        suspect_level = 0

        if not isinstance(username, str):
             return 0 # Retorna 0 se não for uma string válida

        # Critério 1: Nomes de usuário com muitos números
        num_digits = sum(c.isdigit() for c in username)
        if len(username) > 0 and num_digits / len(username) > 0.5:
            suspect_level += 2

        # Critério 2: Nomes de usuário com muitos caracteres não alfanuméricos
        non_alphanumeric_count = len(re.findall(r'[^a-zA-Z0-9]', username))
        if len(username) > 0 and non_alphanumeric_count / len(username) > 0.33:
            suspect_level += 3

        # Critério 3: Nomes de usuário curtos demais
        if 0 < len(username) < 3:
            suspect_level += 1

        # Critério 4: Lista negra de palavras
        blacklist = ["raid", "bot", "free", "nitro", "hack"] # Adicione palavras relevantes
        for word in blacklist:
            if word in username.lower():
                suspect_level += 4
                break # Não precisa verificar outras palavras da blacklist se uma já foi encontrada

        # Critério 5: Muitos caracteres Unicode (não ASCII)
        unicode_count = 0
        for char in username:
            if ord(char) > 127:
                unicode_count += 1
        if len(username) > 0 and unicode_count / len(username) > 0.25:
            suspect_level += 2

        return suspect_level

    def similarity(self, s1, s2):
        if not isinstance(s1, str) or not isinstance(s2, str) or not s1 or not s2:
            return 0.0
        longer = s1 if len(s1) > len(s2) else s2
        shorter = s1 if len(s1) < len(s2) else s2
        # Já tratamos o caso de string vazia acima, mas esta verificação é redundante
        # if len(shorter) == 0:
        #     return 0.0

        longer_length = len(longer)
        # Adiciona um try-except caso Levenshtein falhe por algum motivo inesperado
        try:
            distance = Levenshtein.distance(longer, shorter)
            return (longer_length - distance) / longer_length
        except Exception as e:
            print(f"Erro ao calcular similaridade entre '{s1}' e '{s2}': {e}")
            return 0.0 # Retorna 0 em caso de erro

    # A função assess_similarity original não é usada diretamente na check_raids corrigida,
    # pois a lógica de similaridade foi integrada para comparar apenas membros na janela de pico atual.
    # Mantendo-a caso seja usada em outro lugar ou para referência, mas pode ser removida se não for mais necessária.
    # async def assess_similarity(self, member: discord.Member) -> int:
    #     suspect_level = 0
    #     for other_member_id, other_ts in self.recent_joins.get(member.guild.id, []):
    #         other_member = member.guild.get_member(other_member_id)
    #         if other_member and member.id != other_member_id:
    #             name_sim = self.similarity(member.name, other_member.name)
    #             if name_sim > 0.8:
    #                 suspect_level += 5
    #             if member.display_avatar and other_member.display_avatar and str(member.display_avatar.url) == str(other_member.display_avatar.url):
    #                  suspect_level += 7
    #     return suspect_level


    @app_commands.command(name="raidmode", description="Configurações avançadas de anti-raid")
    @app_commands.checks.has_permissions(administrator=True)
    async def raidmode(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Este comando só pode ser usado em um servidor.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        config = self.protection_config.setdefault(str(guild_id), {})

        # Load settings from config, default to True for checks, False for raid_mode_active, 5 for threshold
        check_username = config.get("check_username", True)
        check_account_age = config.get("check_account_age", True)
        check_avatar = config.get("check_avatar", True)
        check_similarity = config.get("check_similarity", True)
        raid_mode_active = self.raid_mode_active.get(guild_id, False) # Usa o estado atual do dicionário in-memory
        threshold = config.get("raid_threshold", 5)
        action_threshold = config.get("action_threshold", threshold)

        # Build the embed
        embed = discord.Embed(title="Configurações do Modo Anti-Raid", color=discord.Color.from_rgb(66, 0, 0))
        embed.add_field(name="Modo Anti-Raid", value="Ativado" if raid_mode_active else "Desativado", inline=False)
        embed.add_field(name="Threshold de Detecção (Pico de Joins)", value=str(threshold), inline=False)
        embed.add_field(name="Threshold de Ação (Nível de Suspeição)", value=str(action_threshold), inline=False)
        embed.add_field(name="Janela de Detecção (Segundos)", value=str(SPIKE_DETECTION_WINDOW), inline=False)
        embed.add_field(name="Janela de Joins Recentes (Segundos)", value=str(RECENT_JOINS_WINDOW), inline=False)
        embed.add_field(name="Análise de Nome de Usuário", value="Ativada" if check_username else "Desativada", inline=True)
        embed.add_field(name="Análise da Idade da Conta", value="Ativada" if check_account_age else "Desativada", inline=True)
        embed.add_field(name="Análise de Avatar", value="Ativada" if check_avatar else "Desativada", inline=True)
        embed.add_field(name="Análise de Similaridade", value="Ativada" if check_similarity else "Desativada", inline=True)


        # Create the buttons
        # Use custom_id prefixes to distinguish button types and actions
        username_button = Button(style=ButtonStyle.success if check_username else ButtonStyle.secondary, label="Nome", emoji="👤", custom_id=f"protection:toggle:check_username")
        account_age_button = Button(style=ButtonStyle.success if check_account_age else ButtonStyle.secondary, label="Idade", emoji="🗓️", custom_id=f"protection:toggle:check_account_age")
        avatar_button = Button(style=ButtonStyle.success if check_avatar else ButtonStyle.secondary, label="Avatar", emoji="🖼️", custom_id=f"protection:toggle:check_avatar")
        similarity_button = Button(style=ButtonStyle.success if check_similarity else ButtonStyle.secondary, label="Similaridade", emoji="🤝", custom_id=f"protection:toggle:check_similarity")
        raid_mode_button = Button(style=ButtonStyle.success if raid_mode_active else ButtonStyle.danger, label="Modo Anti-Raid", emoji="🛡️", custom_id=f"protection:toggle:raid_mode_active")
        threshold_button = Button(style=ButtonStyle.secondary, label="Thresholds", emoji="⚙️", custom_id=f"protection:adjust:thresholds")


        # Create the view and add the buttons
        view = View(timeout=180) # Adiciona um timeout para a view
        view.add_item(username_button)
        view.add_item(account_age_button)
        view.add_item(avatar_button)
        view.add_item(similarity_button)
        view.add_item(raid_mode_button)
        view.add_item(threshold_button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True) # Use ephemeral=True para que apenas o admin veja

    # Adiciona o listener para interações com botões
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        if not custom_id or not custom_id.startswith("protection:"):
            return # Não é um botão desta cog

        # Garante que a interação veio de um admin
        if not interaction.user.guild_permissions.administrator:
             await interaction.response.send_message("Você não tem permissão para usar este botão.", ephemeral=True)
             return

        parts = custom_id.split(":")
        action_type = parts[1] # 'toggle' or 'adjust'
        setting_key = parts[2] # The setting name or 'thresholds'

        guild_id = interaction.guild.id
        config = self.protection_config.setdefault(str(guild_id), {})

        if action_type == "toggle":
            if setting_key == "raid_mode_active":
                 # Toggle o estado in-memory diretamente
                 self.raid_mode_active[guild_id] = not self.raid_mode_active.get(guild_id, False)
                 current_state = self.raid_mode_active[guild_id]
                 await interaction.response.send_message(f"Modo Anti-Raid {'ativado' if current_state else 'desativado'}.", ephemeral=True)
            elif setting_key in ["check_username", "check_account_age", "check_avatar", "check_similarity"]:
                 # Toggle settings in config
                 config[setting_key] = not config.get(setting_key, True) # Default is True for these checks
                 self.save_protection_config()
                 current_state = config[setting_key]
                 await interaction.response.send_message(f"{setting_key.replace('check_', '').replace('_', ' ').title()} {'ativada' if current_state else 'desativada'}.", ephemeral=True)
            else:
                 await interaction.response.send_message("Opção desconhecida.", ephemeral=True)
                 return # Para não tentar atualizar o embed com um estado inválido


        elif action_type == "adjust":
            if setting_key == "thresholds":
                # Lógica para ajustar thresholds via Modal
                class ThresholdModal(discord.ui.Modal, title="Ajustar Thresholds Anti-Raid"):
                    threshold_input = discord.ui.TextInput(
                        label="Threshold de Detecção (Pico de Joins)",
                        placeholder=str(config.get("raid_threshold", 5)),
                        required=True,
                        max_length=4
                    )
                    action_threshold_input = discord.ui.TextInput(
                        label="Threshold de Ação (Nível de Suspeição)",
                        placeholder=str(config.get("action_threshold", config.get("raid_threshold", 5))),
                        required=True,
                        max_length=4
                    )

                    async def on_submit(self, modal_interaction: discord.Interaction):
                         try:
                              new_threshold = int(self.threshold_input.value)
                              new_action_threshold = int(self.action_threshold_input.value)

                              if new_threshold <= 0 or new_action_threshold <= 0:
                                   await modal_interaction.response.send_message("Os thresholds devem ser números positivos.", ephemeral=True)
                                   return

                              config["raid_threshold"] = new_threshold
                              config["action_threshold"] = new_action_threshold
                              self.save_protection_config()
                              await modal_interaction.response.send_message("Thresholds atualizados com sucesso.", ephemeral=True)
                         except ValueError:
                              await modal_interaction.response.send_message("Por favor, insira apenas números inteiros para os thresholds.", ephemeral=True)
                         except Exception as e:
                              print(f"Erro ao salvar thresholds: {e}")
                              await modal_interaction.response.send_message(f"Ocorreu um erro ao salvar os thresholds: {e}", ephemeral=True)


                await interaction.response.send_modal(ThresholdModal())
                # Após o modal ser submetido, a edição do embed acontecerá no on_submit do modal
                # Não chame update_raidmode_embed aqui imediatamente após enviar o modal
                return # Sai da função on_interaction para não editar o embed agora

        # Atualiza o embed após a ação (exceto para modals que lidam com sua própria resposta/edição)
        # Edita a mensagem original (o embed com os botões)
        await self.update_raidmode_embed(interaction, guild_id)


    async def update_raidmode_embed(self, interaction: discord.Interaction, guild_id: int):
        # Busca a configuração mais recente após a alteração
        config = self.protection_config.setdefault(str(guild_id), {})

        # Load settings from config and in-memory state
        check_username = config.get("check_username", True)
        check_account_age = config.get("check_account_age", True)
        check_avatar = config.get("check_avatar", True)
        check_similarity = config.get("check_similarity", True)
        raid_mode_active = self.raid_mode_active.get(guild_id, False) # Usa o estado in-memory
        threshold = config.get("raid_threshold", 5)
        action_threshold = config.get("action_threshold", threshold)


        embed = discord.Embed(title="Configurações do Modo Anti-Raid", color=discord.Color.from_rgb(66, 0, 0))
        embed.add_field(name="Modo Anti-Raid", value="Ativado" if raid_mode_active else "Desativado", inline=False)
        embed.add_field(name="Threshold de Detecção (Pico de Joins)", value=str(threshold), inline=False)
        embed.add_field(name="Threshold de Ação (Nível de Suspeição)", value=str(action_threshold), inline=False)
        embed.add_field(name="Janela de Detecção (Segundos)", value=str(SPIKE_DETECTION_WINDOW), inline=False)
        embed.add_field(name="Janela de Joins Recentes (Segundos)", value=str(RECENT_JOINS_WINDOW), inline=False)
        embed.add_field(name="Análise de Nome de Usuário", value="Ativada" if check_username else "Desativada", inline=True)
        embed.add_field(name="Análise da Idade da Conta", value="Ativada" if check_account_age else "Desativada", inline=True)
        embed.add_field(name="Análise de Avatar", value="Ativada" if check_avatar else "Desativada", inline=True)
        embed.add_field(name="Análise de Similaridade", value="Ativada" if check_similarity else "Desativada", inline=True)

        # Create the buttons with updated styles
        username_button = Button(style=ButtonStyle.success if check_username else ButtonStyle.secondary, label="Nome", emoji="👤", custom_id=f"protection:toggle:check_username")
        account_age_button = Button(style=ButtonStyle.success if check_account_age else ButtonStyle.secondary, label="Idade", emoji="🗓️", custom_id=f"protection:toggle:check_account_age")
        avatar_button = Button(style=ButtonStyle.success if check_avatar else ButtonStyle.secondary, label="Avatar", emoji="🖼️", custom_id=f"protection:toggle:check_avatar")
        similarity_button = Button(style=ButtonStyle.success if check_similarity else ButtonStyle.secondary, label="Similaridade", emoji="🤝", custom_id=f"protection:toggle:check_similarity")
        raid_mode_button = Button(style=ButtonStyle.success if raid_mode_active else ButtonStyle.danger, label="Modo Anti-Raid", emoji="🛡️", custom_id=f"protection:toggle:raid_mode_active")
        threshold_button = Button(style=ButtonStyle.secondary, label="Thresholds", emoji="⚙️", custom_id=f"protection:adjust:thresholds")

        # Create the view and add the buttons
        view = View(timeout=180) # Mantém o mesmo timeout
        view.add_item(username_button)
        view.add_item(account_age_button)
        view.add_item(avatar_button)
        view.add_item(similarity_button)
        view.add_item(raid_mode_button)
        view.add_item(threshold_button)

        # Edita a mensagem original que contém os botões
        # Use interaction.edit_original_response() para editar a mensagem que iniciou a interação do componente
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except discord.errors.NotFound:
             print("Erro: Mensagem original não encontrada para edição.")
        except Exception as e:
             print(f"Erro ao editar a mensagem original: {e}")


    @app_commands.command(name="setlogchannel", description="Define o canal para logs de moderação e proteção anti-raid.")
    @app_commands.describe(channel="Canal para logs")
    @app_commands.checks.has_permissions(administrator=True)
    async def setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.guild:
            await interaction.response.send_message("Este comando só pode ser usado em um servidor.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        self.protection_config.setdefault(str(guild_id), {})["log_channel"] = channel.id
        self.save_protection_config()
        await interaction.response.send_message(f"Canal de log definido para {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot):
    cog = Protection(bot)
    await bot.add_cog(cog)

    # Inicia a tarefa de checagem de raids apenas UMA VEZ, após o bot estar pronto.
    # O listener on_ready dentro da classe já cuida disso com o decorator @check_raids.before_loop.
    # Remover a re-definição e adição do listener on_ready aqui.
    # @commands.Cog.listener()
    # async def on_ready():
    #     cog.task.start()
    # bot.add_listener(on_ready)
