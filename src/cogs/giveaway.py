import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
from datetime import datetime, timedelta
import asyncio

class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.giveaways_file = "data/giveaways.json"
        self.load_giveaways()
        self.check_giveaways.start()

    def load_giveaways(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if os.path.exists(self.giveaways_file):
            with open(self.giveaways_file, "r") as f:
                self.giveaways = json.load(f)
        else:
            self.giveaways = {}
            self.save_giveaways()

    def save_giveaways(self):
        with open(self.giveaways_file, "w") as f:
            json.dump(self.giveaways, f, indent=4)

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        """Verifica sorteios expirados a cada 30 segundos"""
        current_time = datetime.utcnow().timestamp()
        ended_giveaways = []

        for giveaway_id, giveaway in self.giveaways.items():
            if current_time >= giveaway["end_time"]:
                await self.end_giveaway(giveaway_id, giveaway)
                ended_giveaways.append(giveaway_id)

        # Remove sorteios finalizados
        for giveaway_id in ended_giveaways:
            del self.giveaways[giveaway_id]
        if ended_giveaways:
            self.save_giveaways()

    async def end_giveaway(self, giveaway_id: str, giveaway: dict):
        """Finaliza um sorteio e seleciona os vencedores"""
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if not channel:
                return

            message = await channel.fetch_message(giveaway["message_id"])
            if not message:
                return

            # Pega todos os usuários que reagiram
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            if not reaction:
                return

            users = []
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)

            if not users:
                embed = discord.Embed(
                    title="🎉 Sorteio Finalizado",
                    description=f"Ninguém participou do sorteio!\n\n"
                              f"**Prêmio:** {giveaway['prize']}\n"
                              f"**Host:** <@{giveaway['host_id']}>",
                    color=discord.Color.red()
                )
                await message.edit(embed=embed)
                return

            # Seleciona os vencedores
            winners = random.sample(users, min(giveaway["winners"], len(users)))
            winners_mention = ", ".join([winner.mention for winner in winners])

            embed = discord.Embed(
                title="🎉 Sorteio Finalizado",
                description=f"**Prêmio:** {giveaway['prize']}\n"
                          f"**Vencedores:** {winners_mention}\n"
                          f"**Host:** <@{giveaway['host_id']}>",
                color=discord.Color.green()
            )
            await message.edit(embed=embed)

            # Notifica os vencedores
            for winner in winners:
                try:
                    await winner.send(
                        f"🎉 Parabéns! Você ganhou **{giveaway['prize']}** no servidor {channel.guild.name}!"
                    )
                except discord.Forbidden:
                    pass

        except Exception as e:
            print(f"Erro ao finalizar sorteio {giveaway_id}: {str(e)}")

    @app_commands.command(name="giveaway", description="Cria um novo sorteio")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def giveaway(self, interaction: discord.Interaction):
        """Comando principal de sorteio"""
        modal = GiveawayModal(self)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="reroll", description="Refaz o sorteio de um prêmio")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def reroll(self, interaction: discord.Interaction, message_id: str):
        """Refaz o sorteio de um prêmio"""
        try:
            message = await interaction.channel.fetch_message(int(message_id))
            if not message:
                await interaction.response.send_message("Mensagem não encontrada!", ephemeral=True)
                return

            # Verifica se é uma mensagem de sorteio
            if not message.embeds or not message.embeds[0].title == "🎉 Sorteio Finalizado":
                await interaction.response.send_message("Esta mensagem não é um sorteio finalizado!", ephemeral=True)
                return

            # Pega todos os usuários que reagiram
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            if not reaction:
                await interaction.response.send_message("Nenhuma reação encontrada!", ephemeral=True)
                return

            users = []
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)

            if not users:
                await interaction.response.send_message("Ninguém participou do sorteio!", ephemeral=True)
                return

            # Seleciona um novo vencedor
            winner = random.choice(users)

            embed = message.embeds[0]
            embed.description = embed.description.replace(
                "**Vencedores:**", f"**Vencedor (Reroll):** {winner.mention}"
            )
            await message.edit(embed=embed)

            # Notifica o novo vencedor
            try:
                await winner.send(
                    f"🎉 Parabéns! Você ganhou o reroll de **{embed.description.split('**')[1]}** no servidor {interaction.guild.name}!"
                )
            except discord.Forbidden:
                pass

            await interaction.response.send_message(f"Novo vencedor selecionado: {winner.mention}", ephemeral=True)

        except ValueError:
            await interaction.response.send_message("ID de mensagem inválido!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Erro ao refazer sorteio: {str(e)}", ephemeral=True)

class GiveawayModal(discord.ui.Modal, title="Criar Sorteio"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

        self.prize = discord.ui.TextInput(
            label="Prêmio",
            placeholder="Digite o prêmio do sorteio",
            required=True
        )
        self.add_item(self.prize)

        self.winners = discord.ui.TextInput(
            label="Número de Vencedores",
            placeholder="Digite o número de vencedores (1-10)",
            required=True
        )
        self.add_item(self.winners)

        self.duration = discord.ui.TextInput(
            label="Duração",
            placeholder="Ex: 1h, 30m, 1d",
            required=True
        )
        self.add_item(self.duration)

        self.description = discord.ui.TextInput(
            label="Descrição",
            placeholder="Digite uma descrição para o sorteio",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar número de vencedores
            winners = int(self.winners.value)
            if winners < 1 or winners > 10:
                await interaction.response.send_message(
                    "O número de vencedores deve estar entre 1 e 10!",
                    ephemeral=True
                )
                return

            # Converter duração para segundos
            time_units = {
                's': 1,
                'm': 60,
                'h': 3600,
                'd': 86400
            }
            
            duration = self.duration.value
            time_value = int(duration[:-1])
            time_unit = duration[-1].lower()
            
            if time_unit not in time_units:
                await interaction.response.send_message(
                    "Formato de duração inválido! Use: 30s, 5m, 1h, 1d",
                    ephemeral=True
                )
                return
            
            duration_seconds = time_value * time_units[time_unit]
            end_time = datetime.utcnow().timestamp() + duration_seconds

            # Criar embed do sorteio
            embed = discord.Embed(
                title="🎉 Novo Sorteio!",
                description=f"**Prêmio:** {self.prize.value}\n"
                          f"**Vencedores:** {winners}\n"
                          f"**Host:** {interaction.user.mention}\n\n"
                          f"{self.description.value}\n\n"
                          f"Termina: <t:{int(end_time)}:R>",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"ID: {interaction.id}")

            # Enviar mensagem do sorteio
            message = await interaction.channel.send(embed=embed)
            await message.add_reaction("🎉")

            # Salvar sorteio
            self.cog.giveaways[str(interaction.id)] = {
                "channel_id": interaction.channel.id,
                "message_id": message.id,
                "prize": self.prize.value,
                "winners": winners,
                "end_time": end_time,
                "host_id": interaction.user.id
            }
            self.cog.save_giveaways()

            await interaction.response.send_message(
                f"Sorteio criado com sucesso! ID: {interaction.id}",
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                "Valores inválidos! Verifique os números e tente novamente.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Erro ao criar sorteio: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot)) 