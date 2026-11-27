import os
from pathlib import Path
from  dotenv import load_dotenv
    
if __name__ == "__main__":
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path, override=True)
    from src.bot import bot, DB

    TOKEN = os.getenv("TOKEN", "")
    print('Token:', TOKEN[:8], '...', TOKEN[-8:])
    bot.run(TOKEN)
    DB.close()