from typing import Set
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from src.cogs import load_cogs
from src.handlers import setup_handlers

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do bot
class Bot(commands.Bot):
    def __init__(self):
        # Configura as intents do bot
        intents = discord.Intents.default()
        intents.message_content = True  # Permite o bot de ler o conteúdo das mensagens
        intents.members = True          # Permite o bot de receber eventos de membros do servidor
        super().__init__(command_prefix="!", intents=intents)
        # Define os IDs dos donos do bot
        self.owner_ids: Set[int] = {1243889655087370270}  # Substitua pelo seu ID

    # Executado quando o bot está pronto
    async def setup_hook(self):
        print("Carregando cogs...")
        await load_cogs(self)  # Carrega todos os cogs
        print("Cogs carregados com sucesso!")

        print("Configurando handlers...")
        setup_handlers(self)  # Configura os handlers
        print("Handlers configurados com sucesso!")

        print("Sincronizando comandos com o Discord...")
        try:
            synced = await self.tree.sync()  # Sincroniza os comandos com o Discord
            print(f"Sincronizados {len(synced)} comandos")
        except Exception as e:
            print(f"Erro ao sincronizar comandos: {e}")
        print("Setup completo!")

    # Evento chamado quando o bot está online
    async def on_ready(self):
        print(f"Bot pronto! Logado como {self.user}")
        print(f"ID do Bot: {self.user.id}")
        print("------")
        try:
            synced = await self.tree.sync()  # Sincroniza os comandos com o Discord
            print(f"Sincronizados {len(synced)} comandos")
        except Exception as e:
            print(f"Erro ao sincronizar comandos em on_ready: {e}")


# Função principal
def main():
    bot = Bot()
    try:
        bot.run(os.getenv("DISCORD_TOKEN"))  # Inicia o bot com o token do Discord
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")


# Garante que a função main() seja executada quando o script for executado
if __name__ == "__main__":
    main()