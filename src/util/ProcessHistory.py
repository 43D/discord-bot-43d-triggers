import asyncio
import os
import sqlite3
from typing import Literal
import discord
from src.database.db import RegrasDB

class ProcessHistory:
    def __init__(self, db: RegrasDB):
        self._db = db
        
    def _create_db(self, guild_id):
        os.makedirs("osaka_db", exist_ok=True)
        db_path = f"osaka_db/{guild_id}.db"
        self._conn = sqlite3.connect(db_path)
        self._cursor = self._conn.cursor()
        self._cursor.execute("""CREATE TABLE IF NOT EXISTS mensagens (
            id TEXT PRIMARY KEY,
            conteudo TEXT
        )""")
        self._conn.commit()
        self._cursor.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
            channel_id TEXT PRIMARY KEY,
            last_msg_id TEXT
        )""")
        self._conn.commit()
    def _get_last_msg_id(self, channel_id: int) -> str | None:
        self._cursor.execute("SELECT last_msg_id FROM checkpoints WHERE channel_id = ?", (str(channel_id),))
        result = self._cursor.fetchone()
        return result[0] if result else None

    def _save_last_msg_id(self, channel_id: int, msg_id: int):
        self._cursor.execute("INSERT OR REPLACE INTO checkpoints (channel_id, last_msg_id) VALUES (?, ?)", (str(channel_id), str(msg_id)))
        self._conn.commit()

    def _save_msg(self, id, msg):
        self._cursor.execute("INSERT OR REPLACE INTO mensagens (id, conteudo) VALUES (?, ?)", (id, msg))
        self._conn.commit()
    
    async def fetch_full_history(self, channel: discord.TextChannel, after_obj: discord.Object | None):
        last_id = None
        while True:
            kwargs = {
                "limit": 1000,
                "oldest_first": True
            }
            if after_obj:
                kwargs["after"] = after_obj
            if last_id:
                kwargs["after"] = discord.Object(id=last_id)
            try:
                messages = [msg async for msg in channel.history(**kwargs)]
            except discord.HTTPException as e:
                if e.status == 429:
                    print("Rate limit atingido. Aguardando 5 segundos...")
                    await asyncio.sleep(15)
                else: raise

            if not messages:
                break

            for message in messages:
                if message.author.bot:
                    continue
                msg = message.content.strip()
                if not msg or len(msg) < 1:
                    continue
                self._save_msg(message.id, msg)
                self._save_last_msg_id(channel.id, message.id)
                last_id = message.id
            print("sleep de 100ms:", self._id_guild)  
            await asyncio.sleep(1)  # 1 chamadas a cada 1000ms
                
    async def processar_historico(self, guild: discord.Guild | None):
        if not guild:
            print("Guild is None, cannot process history.")
            return
        id_guild = guild.id if guild else 0
        self._id_guild = id_guild
        self._create_db(id_guild)
        
        def get_channel_status(canais: list[tuple[int, Literal[0, 1]]], channel_id: int) -> Literal[0, 1, 2]:
            for canal in canais:
                if canal[0] == channel_id:
                    return canal[1]
            return 2
        
        modus_op: Literal["ALL", "WHITE", "DENY"] = self._db.get_configs_by_tag(id_guild, "osaka_mode") # type: ignore
        canais = self._db.get_osaka_channels_by_guild(id_guild)
        for channel in guild.text_channels:
            try:
                channel_status = get_channel_status(canais, channel.id)
                await asyncio.sleep(10)
                if (modus_op == "ALL") or (modus_op == "WHITE" and channel_status == 0) or (modus_op == "DENY" and channel_status != 1):
                    last_msg_id = self._get_last_msg_id(channel.id)
                    after_obj = discord.Object(id=int(last_msg_id)) if last_msg_id else None
                    await self.fetch_full_history(channel, after_obj)
            except Exception as e:
                print(f"Erro ao processar {channel.name}: {e}")
                
        self._conn.close()
        