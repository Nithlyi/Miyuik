from discord.ext import commands

def setup_handlers(bot: commands.Bot):
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Comando não encontrado!")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("Você não tem permissão para usar este comando!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Faltam argumentos necessários para este comando!")
        else:
            await ctx.send(f"Ocorreu um erro: {str(error)}")

    @bot.event
    async def on_ready():
        print(f"Bot está online como {bot.user.name}")
        print("------") 