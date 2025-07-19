# Discord Bot

Este projeto é um bot simples para Discord que escuta mensagens em um canal específico e responde com marcações. O bot possui 3 comandos: `add`, `remove` e `list`, que permitem gerenciar uma lista de triggers.

## Estrutura do Projeto

```
discord-bot
├── src
│   ├── bot.py           # Ponto de entrada do bot
│   └── database
│       └── db.py       # Banco de dados SQLite para armazenar regras
├── .env                # Variáveis de ambiente
├── main.py             # Inicialização do bot
└── pyproject.toml      # Configurações do projeto
```

## Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/43D/discord-bot-43d-triggers.git
   cd discord-bot
   ```

2. Instale as dependências:
   ```
   uv sync
   ```
   caso não tenha astral-uv instalado:
   ```
   pip install -r requirements.txt
   ```

## Uso

1. Configure seu token do bot no arquivo `.env` (renomei `.env-example` se necessário).
2. Execute o bot:
   ```
   uv run python main.py
   ```
   caso não tenha astral-uv instalado:
   ```
   python main.py
   ```

## Comandos

- `/add <canal> <regex> <cargo>`: Adiciona um observador para um canal específico. O comando aceita o ID do canal, uma expressão regular e o ID do cargo a ser mencionado quando a mensagem corresponder à regex.
- `/remove <id>`: Remove uma observador existente pelo ID.
- `/list`: Lista todos os observadores configurados no servidor.