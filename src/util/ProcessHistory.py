import os
import sqlite3
from typing import Literal
import discord
from src.database.db import RegrasDB

class ProcessHistory:
    def __init__(self, db: RegrasDB):
        self._db = db
        
    def _create_db(self, guild_id):
        os.makedirs("amilton_db", exist_ok=True)
        db_path = f"amilton_db/{guild_id}.db"
        self._conn = sqlite3.connect(db_path)
        self._cursor = self._conn.cursor()
        self._cursor.execute("""CREATE TABLE IF NOT EXISTS mensagens (
            id TEXT PRIMARY KEY,
            conteudo TEXT
        )""")
        self._conn.commit()

    def _save_msg(self, id, msg):
        self._cursor.execute("INSERT OR REPLACE INTO mensagens (id, conteudo) VALUES (?, ?)", (id, msg))
        self._conn.commit()
            
    async def processar_historico(self, guild: discord.Guild | None):
        if not guild:
            print("Guild is None, cannot process history.")
            return
        id_guild = guild.id if guild else 0
        self._create_db(id_guild)
        
        def get_channel_status(canais: list[tuple[int, Literal[0, 1]]], channel_id: int) -> Literal[0, 1, 2]:
            for canal in canais:
                if canal[0] == channel_id:
                    return canal[1]
            return 2
        
        modus_op: Literal["ALL", "WHITE", "DENY"] = self._db.get_configs_by_tag(id_guild, "amilton_mode") # type: ignore
        canais = self._db.get_amilton_channels_by_guild(id_guild)
        for channel in guild.text_channels:
            try:
                channel_status = get_channel_status(canais, channel.id)
                if (modus_op == "ALL") or (modus_op == "WHITE" and channel_status == 0) or (modus_op == "DENY" and channel_status != 1):
                    async for message in channel.history(limit=None, oldest_first=True):
                        if message.author.bot: continue
                        msg = message.content.strip()
                        if not msg or len(msg) < 1:
                            continue
                        id = message.id
                        self._save_msg(id, msg)
            except Exception as e:
                print(f"Erro ao processar {channel.name}: {e}")
                
        self._cursor.close()
        self._conn.close()
        