import random
import discord
from src.database.db import MessagesDB, RegrasDB

class ProcessOsaka:
    def __init__(self, msDB: MessagesDB, db: RegrasDB):
        self._db = db
        self._msDB = msDB
        
    def _rng_msg(self, guild_id, id_chat):
        def random_rate(rate: float):
            chance = random.randint(1, 10000)
            return (float(chance) / 100) <= rate
        rate = self._db.get_configs_by_tag(guild_id, "osaka_rate")
        modus_op = self._db.get_configs_by_tag(guild_id, "osaka_mode")
        canais = self._db.get_osaka_channels_by_guild(guild_id)
        if modus_op == "DENY":
            if id_chat in [c[0] for c in canais if c[1] == 1]:
                return False
        elif modus_op == "WHITE":
            if id_chat not in [c[0] for c in canais if c[1] == 0]:
                return False
        return random_rate(rate) if rate else False
    
    async def process(self, message: discord.Message):
        guild_id = message.guild.id if message.guild else 0
        channel_id = message.channel.id
        if not self._rng_msg(guild_id, channel_id):
            return 
        
        all_msg = self._msDB.get_all_messages(guild_id)
        if not all_msg or len(all_msg) < 1:
            return
        
        all_msg_strs: list[str] = [msg[0] for msg in all_msg]
        # codigo da Osaka