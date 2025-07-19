# Discord Bot

Este projeto é um bot simples para Discord que escuta mensagens em um canal específico e responde a comandos de moderadores. O bot possui dois comandos principais: `add` e `remove`, que permitem gerenciar uma lista de mensagens ou usuários.

## Estrutura do Projeto

```
discord-bot
├── src
│   ├── bot.py           # Ponto de entrada do bot
│   ├── commands
│   │   ├── add.py       # Implementação do comando add
│   │   └── remove.py    # Implementação do comando remove
│   └── utils
│       └── permissions.py # Funções utilitárias para verificar permissões
├── requirements.txt      # Dependências do projeto
└── README.md             # Documentação do projeto
```

## Instalação

1. Clone o repositório:
   ```
   git clone <URL_DO_REPOSITORIO>
   cd discord-bot
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

## Uso

1. Configure seu token do bot no arquivo `bot.py`.
2. Execute o bot:
   ```
   python src/bot.py
   ```

## Comandos

- `!add <mensagem>`: Adiciona uma mensagem ou usuário à lista. Apenas moderadores podem usar este comando.
- `!remove <mensagem>`: Remove uma mensagem ou usuário da lista. Apenas moderadores podem usar este comando.

## Contribuição

Sinta-se à vontade para contribuir com melhorias ou correções. Crie um fork do repositório, faça suas alterações e envie um pull request.