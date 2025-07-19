import os
from  dotenv import load_dotenv
from src.bot import bot, db

def main():
    bot.run(os.getenv("TOKEN", ""))
    db.close()
    
if __name__ == "__main__":
    load_dotenv()
    main()
