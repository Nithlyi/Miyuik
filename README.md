# Discord Bot com Slash Commands

Este é um bot Discord criado com discord.py, utilizando slash commands e uma estrutura organizada.

## Estrutura do Projeto

```
.
├── main.py              # Arquivo principal do bot
├── requirements.txt     # Dependências do projeto
├── .env                # Arquivo de configuração (não versionado)
└── src/
    ├── cogs/           # Diretório para os cogs
    │   └── general.py  # Exemplo de cog com comandos básicos
    ├── cogs.py         # Gerenciador de cogs
    └── handlers.py     # Gerenciador de eventos
```

## Configuração

1. Clone este repositório
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
   ```
   DISCORD_TOKEN=seu_token_aqui
   ```
4. Execute o bot:
   ```bash
   python main.py
   ```

## Comandos Disponíveis

- `/ping` - Mostra a latência do bot
- `/info` - Mostra informações sobre o bot

## Adicionando Novos Comandos

Para adicionar novos comandos, crie um novo arquivo na pasta `src/cogs/` seguindo o padrão do arquivo `general.py`. O sistema carregará automaticamente todos os cogs na pasta.

## Requisitos

- Python 3.8 ou superior
- discord.py 2.3.2 ou superior 