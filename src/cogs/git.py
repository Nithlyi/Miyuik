import discord
from discord.ext import commands
from discord import app_commands
import subprocess
import os
from typing import Optional
import asyncio
import json

class Git(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_file = "data/github.json"
        self.github_config = self.load_github_config()

    def load_github_config(self):
        """Carrega as configurações do GitHub do arquivo JSON"""
        if not os.path.exists("data"):
            os.makedirs("data")
            
        if os.path.exists(self.github_file):
            with open(self.github_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_github_config(self):
        """Salva as configurações do GitHub no arquivo JSON"""
        with open(self.github_file, "w", encoding="utf-8") as f:
            json.dump(self.github_config, f, indent=4)

    @app_commands.command(name="git_init", description="Inicializa um repositório Git")
    @app_commands.describe(
        path="Caminho do diretório (opcional, usa o diretório atual se não especificado)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def git_init(
        self,
        interaction: discord.Interaction,
        path: Optional[str] = None
    ):
        """Inicializa um repositório Git"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Executa git init
            result = subprocess.run(
                ["git", "init"],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await interaction.followup.send(
                    f"✅ Repositório Git inicializado com sucesso em `{work_dir}`!"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao inicializar repositório: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="git_status", description="Mostra o status do repositório Git")
    @app_commands.describe(
        path="Caminho do diretório (opcional, usa o diretório atual se não especificado)"
    )
    async def git_status(
        self,
        interaction: discord.Interaction,
        path: Optional[str] = None
    ):
        """Mostra o status do repositório Git"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Executa git status
            result = subprocess.run(
                ["git", "status"],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Cria um embed com o status
                embed = discord.Embed(
                    title="📊 Status do Git",
                    description=f"```\n{result.stdout}\n```",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ Erro ao verificar status: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="git_add", description="Adiciona arquivos ao stage")
    @app_commands.describe(
        files="Arquivos para adicionar (use . para todos)",
        path="Caminho do diretório (opcional)"
    )
    async def git_add(
        self,
        interaction: discord.Interaction,
        files: str,
        path: Optional[str] = None
    ):
        """Adiciona arquivos ao stage"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Executa git add
            result = subprocess.run(
                ["git", "add", files],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await interaction.followup.send(
                    f"✅ Arquivos adicionados com sucesso: `{files}`"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao adicionar arquivos: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="git_commit", description="Faz commit das alterações")
    @app_commands.describe(
        message="Mensagem do commit",
        path="Caminho do diretório (opcional)"
    )
    async def git_commit(
        self,
        interaction: discord.Interaction,
        message: str,
        path: Optional[str] = None
    ):
        """Faz commit das alterações"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Executa git commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await interaction.followup.send(
                    f"✅ Commit realizado com sucesso!\n"
                    f"Mensagem: `{message}`"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao fazer commit: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="git_push", description="Envia alterações para o repositório remoto")
    @app_commands.describe(
        remote="Nome do repositório remoto (padrão: origin)",
        branch="Nome da branch (padrão: main)",
        path="Caminho do diretório (opcional)"
    )
    async def git_push(
        self,
        interaction: discord.Interaction,
        remote: Optional[str] = "origin",
        branch: Optional[str] = "main",
        path: Optional[str] = None
    ):
        """Envia alterações para o repositório remoto"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Executa git push
            result = subprocess.run(
                ["git", "push", remote, branch],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await interaction.followup.send(
                    f"✅ Alterações enviadas com sucesso para `{remote}/{branch}`!"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao enviar alterações: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="git_pull", description="Atualiza o repositório local")
    @app_commands.describe(
        remote="Nome do repositório remoto (padrão: origin)",
        branch="Nome da branch (padrão: main)",
        path="Caminho do diretório (opcional)"
    )
    async def git_pull(
        self,
        interaction: discord.Interaction,
        remote: Optional[str] = "origin",
        branch: Optional[str] = "main",
        path: Optional[str] = None
    ):
        """Atualiza o repositório local"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Executa git pull
            result = subprocess.run(
                ["git", "pull", remote, branch],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await interaction.followup.send(
                    f"✅ Repositório atualizado com sucesso de `{remote}/{branch}`!"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao atualizar repositório: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="git_log", description="Mostra o histórico de commits")
    @app_commands.describe(
        limit="Número máximo de commits para mostrar (padrão: 5)",
        path="Caminho do diretório (opcional)"
    )
    async def git_log(
        self,
        interaction: discord.Interaction,
        limit: Optional[int] = 5,
        path: Optional[str] = None
    ):
        """Mostra o histórico de commits"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Executa git log
            result = subprocess.run(
                ["git", "log", f"-n{limit}", "--pretty=format:%h - %s (%cr) <%an>"],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Cria um embed com o log
                embed = discord.Embed(
                    title="📜 Histórico de Commits",
                    description=f"```\n{result.stdout}\n```",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ Erro ao obter histórico: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="github_setup", description="Configura um repositório para o GitHub")
    @app_commands.describe(
        username="Seu nome de usuário do GitHub",
        repo="Nome do repositório",
        token="Token de acesso pessoal do GitHub (opcional)",
        path="Caminho do diretório (opcional)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def github_setup(
        self,
        interaction: discord.Interaction,
        username: str,
        repo: str,
        path: Optional[str] = None,
        token: Optional[str] = None
    ):
        """Configura um repositório para o GitHub"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Salva o token se fornecido
            if token:
                guild_id = str(interaction.guild.id)
                if guild_id not in self.github_config:
                    self.github_config[guild_id] = {}
                self.github_config[guild_id][repo] = {
                    "username": username,
                    "token": token
                }
                self.save_github_config()

            # Configura o remote
            remote_url = f"https://github.com/{username}/{repo}.git"
            result = subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await interaction.followup.send(
                    f"✅ Repositório configurado com sucesso!\n"
                    f"• Usuário: `{username}`\n"
                    f"• Repositório: `{repo}`\n"
                    f"• URL: {remote_url}"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao configurar repositório: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="github_create", description="Cria um novo repositório no GitHub")
    @app_commands.describe(
        name="Nome do repositório",
        description="Descrição do repositório (opcional)",
        private="Se o repositório deve ser privado (padrão: false)",
        token="Token de acesso pessoal do GitHub"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def github_create(
        self,
        interaction: discord.Interaction,
        name: str,
        token: str,
        description: Optional[str] = None,
        private: Optional[bool] = False
    ):
        """Cria um novo repositório no GitHub"""
        await interaction.response.defer()

        try:
            # Prepara os dados para a API do GitHub
            data = {
                "name": name,
                "description": description or "",
                "private": private
            }

            # Cria o repositório usando a API do GitHub
            import requests
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            response = requests.post(
                "https://api.github.com/user/repos",
                json=data,
                headers=headers
            )

            if response.status_code == 201:
                repo_data = response.json()
                await interaction.followup.send(
                    f"✅ Repositório criado com sucesso!\n"
                    f"• Nome: `{name}`\n"
                    f"• URL: {repo_data['html_url']}\n"
                    f"• Privado: {'Sim' if private else 'Não'}"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao criar repositório: {response.json().get('message', 'Erro desconhecido')}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="github_token", description="Configura ou atualiza o token do GitHub")
    @app_commands.describe(
        token="Token de acesso pessoal do GitHub",
        repo="Nome do repositório (opcional, se não especificado, configura para todos)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def github_token(
        self,
        interaction: discord.Interaction,
        token: str,
        repo: Optional[str] = None
    ):
        """Configura ou atualiza o token do GitHub"""
        await interaction.response.defer()

        try:
            guild_id = str(interaction.guild.id)
            if guild_id not in self.github_config:
                self.github_config[guild_id] = {}

            if repo:
                if repo not in self.github_config[guild_id]:
                    self.github_config[guild_id][repo] = {}
                self.github_config[guild_id][repo]["token"] = token
            else:
                # Atualiza o token para todos os repositórios
                for repo_config in self.github_config[guild_id].values():
                    repo_config["token"] = token

            self.save_github_config()

            await interaction.followup.send(
                f"✅ Token do GitHub {'atualizado' if repo else 'configurado'} com sucesso!"
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="github_push", description="Envia alterações para o GitHub")
    @app_commands.describe(
        repo="Nome do repositório",
        branch="Nome da branch (padrão: main)",
        path="Caminho do diretório (opcional)"
    )
    async def github_push(
        self,
        interaction: discord.Interaction,
        repo: str,
        branch: Optional[str] = "main",
        path: Optional[str] = None
    ):
        """Envia alterações para o GitHub"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Obtém o token do GitHub
            guild_id = str(interaction.guild.id)
            if guild_id not in self.github_config or repo not in self.github_config[guild_id]:
                await interaction.followup.send("❌ Repositório não configurado! Use /github_setup primeiro.")
                return

            token = self.github_config[guild_id][repo].get("token")
            if not token:
                await interaction.followup.send("❌ Token do GitHub não configurado! Use /github_token primeiro.")
                return

            # Configura o token no git
            subprocess.run(
                ["git", "config", "credential.helper", "store"],
                cwd=work_dir,
                capture_output=True
            )

            # Executa git push com o token
            result = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=work_dir,
                env={"GIT_ASKPASS": "echo", "GIT_USERNAME": self.github_config[guild_id][repo]["username"], "GIT_PASSWORD": token},
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await interaction.followup.send(
                    f"✅ Alterações enviadas com sucesso para o GitHub!\n"
                    f"• Repositório: `{repo}`\n"
                    f"• Branch: `{branch}`"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao enviar alterações: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="git_remote_remove", description="Remove um remote do Git")
    @app_commands.describe(
        remote="Nome do remote (padrão: origin)",
        path="Caminho do diretório (opcional)"
    )
    async def git_remote_remove(
        self,
        interaction: discord.Interaction,
        remote: Optional[str] = "origin",
        path: Optional[str] = None
    ):
        """Remove um remote do Git"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            # Remove o remote
            result = subprocess.run(
                ["git", "remote", "remove", remote],
                cwd=work_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await interaction.followup.send(
                    f"✅ Remote `{remote}` removido com sucesso!"
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao remover remote: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @app_commands.command(name="git_branch", description="Verifica ou configura a branch atual")
    @app_commands.describe(
        branch="Nome da branch para configurar (opcional)",
        path="Caminho do diretório (opcional)"
    )
    async def git_branch(
        self,
        interaction: discord.Interaction,
        branch: Optional[str] = None,
        path: Optional[str] = None
    ):
        """Verifica ou configura a branch atual"""
        await interaction.response.defer()

        try:
            # Define o diretório de trabalho
            work_dir = path if path else os.getcwd()
            
            if branch:
                # Cria e muda para a nova branch
                result = subprocess.run(
                    ["git", "checkout", "-b", branch],
                    cwd=work_dir,
                    capture_output=True,
                    text=True
                )
            else:
                # Apenas verifica a branch atual
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=work_dir,
                    capture_output=True,
                    text=True
                )

            if result.returncode == 0:
                if branch:
                    await interaction.followup.send(
                        f"✅ Branch `{branch}` criada e selecionada com sucesso!"
                    )
                else:
                    current_branch = result.stdout.strip()
                    await interaction.followup.send(
                        f"📌 Branch atual: `{current_branch}`"
                    )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao gerenciar branch: {result.stderr}"
                )

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}")

    @git_init.error
    @git_status.error
    @git_add.error
    @git_commit.error
    @git_push.error
    @git_pull.error
    @git_log.error
    async def git_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Ocorreu um erro: {str(error)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Git(bot)) 