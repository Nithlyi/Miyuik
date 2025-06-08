# c:\Users\Miko\Downloads\Miy\src\cogs\support.py
import discord
from discord.ext import commands
import discord.ui # Importar ui explicitamente para clareza

# Defina os IDs dos cargos que terão permissão para ver e gerenciar tickets
# Substitua com os IDs reais dos seus cargos de moderação/administração
MOD_ROLES = [] 
ADMIN_ROLES = []

# View para confirmar o fechamento do ticket
class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180) # Timeout de 3 minutos

    @discord.ui.button(label="Sim", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Envia uma resposta efêmera confirmando que vai fechar
        await interaction.response.send_message("Fechando ticket...", ephemeral=True)
        
        # Não edita a mensagem efêmera de confirmação, apenas deleta o canal.
        # O timeout da view fará com que a mensagem efêmera e seus botões desapareçam naturalmente.
        
        # Excluir o canal do ticket (o canal onde esta mensagem está)
        await interaction.channel.delete()

    @discord.ui.button(label="Não", style=discord.ButtonStyle.red)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fechamento cancelado.", ephemeral=True)
        # Remove todos os botões da mensagem de confirmação e edita o texto
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(content="Fechamento do ticket cancelado.", view=self)

# View para ações dentro do canal do ticket (como fechar)
class TicketActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Esta view deve persistir na mensagem do ticket

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Envia uma mensagem pedindo confirmação para fechar o ticket
        await interaction.response.send_message("Tem certeza que deseja fechar este ticket?", view=ConfirmCloseView(), ephemeral=True)


# View para a mensagem principal de suporte com os botões de criação de ticket
class SupportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Denúncia", style=discord.ButtonStyle.red, custom_id="support_denuncia")
    async def denuncia_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "denuncia")

    @discord.ui.button(label="Dúvidas", style=discord.ButtonStyle.blurple, custom_id="support_duvidas")
    async def duvidas_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "duvidas")

    @discord.ui.button(label="Solicitar recompensa", style=discord.ButtonStyle.green, custom_id="support_recompensa")
    async def recompensa_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "recompensa")

    @discord.ui.button(label="Reportar erros", style=discord.ButtonStyle.grey, custom_id="support_erros")
    async def erros_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "erros")

    @discord.ui.button(label="Apelar punições", style=discord.ButtonStyle.red, custom_id="support_apelacao")
    async def apelacao_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "apelacao")

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        # Aqui virá a lógica para criar o canal do ticket
        # e enviar a mensagem inicial com o embed
        await interaction.response.send_message(f"Criando ticket de {ticket_type}...", ephemeral=True)
        
        guild = interaction.guild
        member = interaction.user

        # Definir permissões para o novo canal
        # Permite que o criador do ticket, o bot e os cargos de moderação/administração vejam o canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), # Ninguém mais vê
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True), # Criador vê e envia msg
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) # Bot vê e envia msg
        }
        
        # Adicionar permissões para cargos de moderação/administração
        for role_id in MOD_ROLES + ADMIN_ROLES:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # Criar o canal de texto
        category = discord.utils.get(guild.categories, name="Tickets") # Substitua "Tickets" pelo nome da sua categoria de tickets, se tiver
        if not category:
             category = await guild.create_category("Tickets") # Cria a categoria se não existir
             
        # Nome do canal do ticket (ex: ticket-denuncia-miko)
        channel_name = f"ticket-{ticket_type}-{member.name}".lower().replace(" ", "-")

        ticket_channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            category=category
        )

        # Enviar mensagem inicial no ticket com a TicketActionsView
        embed = discord.Embed(
            title=f"Ticket de {ticket_type.capitalize()}",
            description=f"Olá {member.mention}, bem-vindo(a) ao seu ticket de {ticket_type}. Descreva seu problema ou solicitação aqui.\nUm membro da equipe de suporte logo estará com você.",
            color=discord.Color.blue() # Cor padrão, pode ser customizada
        )
        await ticket_channel.send(content=f"{member.mention}", embed=embed, view=TicketActionsView()) # Adiciona a view aqui
        
        await interaction.followup.send(f"Seu ticket de {ticket_type} foi criado em {ticket_channel.mention}", ephemeral=True)


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Adiciona as views persistentes ao bot
        self.bot.add_view(SupportView())
        # Não é necessário adicionar TicketActionsView ou ConfirmCloseView aqui
        # porque elas são efêmeras ou criadas dinamicamente no ticket.

    @commands.command(name="setup_support")
    @commands.has_permissions(administrator=True) # Apenas administradores podem usar este comando
    async def setup_support_command(self, ctx):
        """Envia a mensagem de configuração do sistema de suporte."""
        embed = discord.Embed(
            title="<a:emoji_25:1378082547929710693>    **Suporte & Atendimento**   <a:emoji_25:1378082547929710693>",
            description=(
                "> Neste canal, você pode tirar suas dúvidas ou entrar em contato com a nossa equipe staff para resolver algum problema ou para uma  solicitação.\n\n"
                "> Pedimos que, por favor, leia atentamente as opções a seguir para não acabar abrindo algum ticket errado e acabar causando uma demora no seu atendimento \n\n"
                "> <:emoji_33:1381070775490052156>   Denúncia e/ou reporte;\n"
                "> <:emoji_33:1381070775490052156>   Tirar dúvidas;\n"
                "> <:emoji_33:1381070775490052156>   Fazer parcerias;\n"
                "> <:emoji_33:1381070775490052156>   Solicitar recompensas (ex: cargos, calls..) \n"
                "> <:emoji_33:1381070775490052156>   Reportar erros do servidor;\n"
                "> <:emoji_33:1381070775490052156>   Apelar punições que considera erradas <:emoji_33:1381070775490052156>   ou  precipitadas."
            ),
            color=0x420000
        )
        # Certifique-se de que esta mensagem inicial use a SupportView
        await ctx.send(embed=embed, view=SupportView())

async def setup(bot):
    await bot.add_cog(Support(bot))

class SupportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Denúncia", style=discord.ButtonStyle.red, custom_id="support_denuncia")
    async def denuncia_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "denuncia")

    @discord.ui.button(label="Dúvidas", style=discord.ButtonStyle.blurple, custom_id="support_duvidas")
    async def duvidas_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "duvidas")

    @discord.ui.button(label="Solicitar recompensa", style=discord.ButtonStyle.green, custom_id="support_recompensa")
    async def recompensa_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "recompensa")

    @discord.ui.button(label="Reportar erros", style=discord.ButtonStyle.grey, custom_id="support_erros")
    async def erros_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "erros")

    @discord.ui.button(label="Apelar punições", style=discord.ButtonStyle.red, custom_id="support_apelacao")
    async def apelacao_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "apelacao")

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        # Aqui virá a lógica para criar o canal do ticket
        # e enviar a mensagem inicial com o embed
        await interaction.response.send_message(f"Criando ticket de {ticket_type}...", ephemeral=True)
        
        guild = interaction.guild
        member = interaction.user

        # Definir permissões para o novo canal
        # Permite que o criador do ticket, o bot e os cargos de moderação/administração vejam o canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), # Ninguém mais vê
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True), # Criador vê e envia msg
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) # Bot vê e envia msg
        }
        
        # Adicionar permissões para cargos de moderação/administração
        for role_id in MOD_ROLES + ADMIN_ROLES:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # Criar o canal de texto
        category = discord.utils.get(guild.categories, name="Tickets") # Substitua "Tickets" pelo nome da sua categoria de tickets, se tiver
        if not category:
             category = await guild.create_category("Tickets") # Cria a categoria se não existir
             
        # Nome do canal do ticket (ex: ticket-denuncia-miko)
        channel_name = f"ticket-{ticket_type}-{member.name}".lower().replace(" ", "-")

        ticket_channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            category=category
        )

        # Enviar mensagem inicial no ticket com a TicketActionsView
        embed = discord.Embed(
            title=f"Ticket de {ticket_type.capitalize()}",
            description=f"Olá {member.mention}, bem-vindo(a) ao seu ticket de {ticket_type}. Descreva seu problema ou solicitação aqui.\nUm membro da equipe de suporte logo estará com você.",
            color=discord.Color.blue() # Cor padrão, pode ser customizada
        )
        # Envia UMA mensagem contendo o embed, a menção e a view
        await ticket_channel.send(content=f"{member.mention}", embed=embed, view=TicketActionsView())
        
        await interaction.followup.send(f"Seu ticket de {ticket_type} foi criado em {ticket_channel.mention}", ephemeral=True)


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Adiciona a view ao bot para que ela persista após reinícios
        self.bot.add_view(SupportView())

    @commands.command(name="setup_support")
    @commands.has_permissions(administrator=True) # Apenas administradores podem usar este comando
    async def setup_support_command(self, ctx):
        """Envia a mensagem de configuração do sistema de suporte."""
        embed = discord.Embed(
            title="<a:emoji_25:1378082547929710693>    **Suporte & Atendimento**   <a:emoji_25:1378082547929710693>",
            description=(
                "> Neste canal, você pode tirar suas dúvidas ou entrar em contato com a nossa equipe staff para resolver algum problema ou para uma  solicitação.\n\n"
                "> Pedimos que, por favor, leia atentamente as opções a seguir para não acabar abrindo algum ticket errado e acabar causando uma demora no seu atendimento \n\n"
                "> <:emoji_33:1381070775490052156>   Denúncia e/ou reporte;\n"
                "> <:emoji_33:1381070775490052156>   Tirar dúvidas;\n"
                "> <:emoji_33:1381070775490052156>   Fazer parcerias;\n"
                "> <:emoji_33:1381070775490052156>   Solicitar recompensas (ex: cargos, calls..) \n"
                "> <:emoji_33:1381070775490052156>   Reportar erros do servidor;\n"
                "> <:emoji_33:1381070775490052156>   Apelar punições que considera erradas <:emoji_33:1381070775490052156>   ou  precipitadas."
            ),
            color=0x420000
        )
        embed.set_image(url="https://media.discordapp.net/attachments/1362206488063377672/1381026673855561839/66b51d261d62299e29383da00b413c75.jpg?ex=684604d1&is=6844b351&hm=ebdfed4e81586c0a7e6a11de724b9e24cbb3277a59c4ad7e6b668c4aa8decc60&=&format=webp&width=661&height=113")
        await ctx.send(embed=embed, view=SupportView())

async def setup(bot):
    await bot.add_cog(Support(bot))