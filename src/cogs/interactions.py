import discord
from discord.ext import commands
import json
import random

class Interactions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.combo_counter = {}

    from discord import app_commands

    @app_commands.command(name="hug", description="Abraçou")
    async def hug_command(self, interaction: discord.Interaction, member: discord.Member):
        await self.handle_interaction(interaction, member, "hug")

    @app_commands.command(name="kiss", description="Beijou")
    async def kiss_command(self, interaction: discord.Interaction, member: discord.Member):
        await self.handle_interaction(interaction, member, "kiss")

    @app_commands.command(name="cafune", description="Fez cafuné")
    async def cafune_command(self, interaction: discord.Interaction, member: discord.Member):
        await self.handle_interaction(interaction, member, "cafune")

    async def handle_interaction(self, interaction: discord.Interaction, member: discord.Member, interaction_type):
        # Define GIFs for each interaction type
        hugs_gifs = [
            "https://c.tenor.com/CR7WQmw-4v0AAAAd/tenor.gif",
            "https://c.tenor.com/FfSuovWnabYAAAAd/tenor.gif",
            "https://c.tenor.com/aUeJ871bGDUAAAAd/tenor.gif",
            "https://c.tenor.com/0QALoFNm07AAAAAd/tenor.gif",
            "https://c.tenor.com/RWD2XL_CxdcAAAAd/tenor.gif"
        ]
        kiss_gifs = [
            "https://c.tenor.com/mumjwctg3ssAAAAd/tenor.gif",
            "https://c.tenor.com/4go0vejtIncAAAAd/tenor.gif",
            "https://c.tenor.com/cQzRWAWrN6kAAAAd/tenor.gif",
            "https://c.tenor.com/06lz817csVgAAAAd/tenor.gif",
            "https://c.tenor.com/O1-IX-P5ugQAAAAd/tenor.gif",
            "https://c.tenor.com/YhGc7aQAI4oAAAAd/tenor.gif"
        ]
        cafune_gifs = [
            "https://c.tenor.com/9y-c-mXuJUoAAAAd/tenor.gif",
            "https://c.tenor.com/YroVxwiL2dcAAAAd/tenor.gif",
            "https://c.tenor.com/Ct6QxrXHZM0AAAAd/tenor.gif"
        ]
        gifs = {
            "hug": random.choice(hugs_gifs),
            "kiss": random.choice(kiss_gifs),
            "cafune": random.choice(cafune_gifs)
        }

        # Create embed
        embed = discord.Embed(
            description=f"{interaction.user.mention} sent a {interaction_type} to {member.mention}!",
            color=discord.Color.from_rgb(0, 0, 0)
        )
        embed.set_image(url=gifs[interaction_type])

        # Create a button
        retribute_button = discord.ui.Button(label="Retribuir", style=discord.ButtonStyle.primary, custom_id=f"retribute_{interaction_type}_{interaction.user.id}_{member.id}")
        view = discord.ui.View()
        view.add_item(retribute_button)

        await interaction.response.send_message(embed=embed, view=view)


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data["custom_id"]
            if custom_id.startswith("retribute_"):
                parts = custom_id.split("_")
                interaction_type = parts[1]
                original_user_id = int(parts[2])
                target_member_id = int(parts[3])

                original_user = self.bot.get_user(original_user_id)
                target_member = interaction.guild.get_member(target_member_id)

                # Check if the user clicking the button is the target member
                if interaction.user.id == target_member_id:
                    if original_user and target_member:
                        await self.handle_interaction(interaction, original_user, interaction_type)
                    else:
                        await interaction.response.send_message("Não foi possível encontrar os usuários.", ephemeral=True)
                else:
                    await interaction.response.send_message("Você não tem permissão para retribuir este gesto.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Interactions(bot))
