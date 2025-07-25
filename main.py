import os
from pathlib import Path
from  dotenv import load_dotenv
from src.bot import bot, db
    
if __name__ == "__main__":
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path, override=True)
    TOKEN = os.getenv("TOKEN", "")
    print('Token:', TOKEN[:8], '...', TOKEN[-8:])
    bot.run(TOKEN)
    db.close()