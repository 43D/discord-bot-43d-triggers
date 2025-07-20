import os
from  dotenv import load_dotenv
from src.bot import bot, db
    
if __name__ == "__main__":
    load_dotenv()
    bot.run(os.getenv("TOKEN", ""))
    db.close()