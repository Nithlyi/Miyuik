import os
import sys
import time
import psutil
import logging
import subprocess
from datetime import datetime
import discord
from discord.ext import commands, tasks

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_monitor.log'),
        logging.StreamHandler()
    ]
)

class BotMonitor:
    def __init__(self):
        self.bot_process = None
        self.last_restart = None
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_cooldown = 300  # 5 minutos
        self.check_interval = 60  # 1 minuto

    def start_bot(self):
        """Inicia o bot em um processo separado"""
        try:
            # Verifica se já existe um processo do bot rodando
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'python' in proc.info['name'].lower() and 'main.py' in ' '.join(proc.info['cmdline']):
                    logging.warning("Bot já está em execução!")
                    return False

            # Inicia o bot em um novo processo
            self.bot_process = subprocess.Popen(
                [sys.executable, 'main.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logging.info(f"Bot iniciado com PID: {self.bot_process.pid}")
            self.last_restart = datetime.now()
            self.restart_count += 1
            return True

        except Exception as e:
            logging.error(f"Erro ao iniciar o bot: {str(e)}")
            return False

    def stop_bot(self):
        """Para o processo do bot"""
        try:
            if self.bot_process:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=5)
                logging.info("Bot parado com sucesso")
            return True
        except Exception as e:
            logging.error(f"Erro ao parar o bot: {str(e)}")
            return False

    def check_bot_status(self):
        """Verifica se o bot está rodando e reinicia se necessário"""
        try:
            # Verifica se o processo ainda está rodando
            if self.bot_process and self.bot_process.poll() is not None:
                logging.warning("Bot parou de responder!")
                
                # Verifica o cooldown de reinicialização
                if self.last_restart:
                    time_since_last_restart = (datetime.now() - self.last_restart).total_seconds()
                    if time_since_last_restart < self.restart_cooldown:
                        logging.warning(f"Aguardando cooldown de reinicialização... ({int(self.restart_cooldown - time_since_last_restart)}s restantes)")
                        return

                # Verifica o limite de reinicializações
                if self.restart_count >= self.max_restarts:
                    logging.error("Limite de reinicializações atingido! Verifique os logs para mais detalhes.")
                    return

                # Tenta reiniciar o bot
                logging.info("Tentando reiniciar o bot...")
                self.stop_bot()
                time.sleep(5)  # Aguarda 5 segundos antes de reiniciar
                self.start_bot()

        except Exception as e:
            logging.error(f"Erro ao verificar status do bot: {str(e)}")

    def start_monitoring(self):
        """Inicia o monitoramento do bot"""
        logging.info("Iniciando sistema de monitoramento...")
        
        # Inicia o bot pela primeira vez
        if not self.start_bot():
            logging.error("Falha ao iniciar o bot!")
            return

        # Loop principal de monitoramento
        while True:
            try:
                self.check_bot_status()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logging.info("Monitoramento interrompido pelo usuário")
                self.stop_bot()
                break
            except Exception as e:
                logging.error(f"Erro no loop de monitoramento: {str(e)}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = BotMonitor()
    monitor.start_monitoring() 