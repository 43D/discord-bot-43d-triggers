import io
import random
import aiohttp
import discord
from src.database.db import RegrasDB

class ProcessMensage:
    def __init__(self, db: RegrasDB):
        self._db = db
    
    def _rng_service(self, guild_id: int, drop_rate: float, win_rate: float):
        def random_rate(rate: float):
            chance = random.randint(1, 10000)
            return (float(chance) / 100) <= rate
        
        if not random_rate(drop_rate): return
        imgs = self._db.get_url_by_guild(guild_id)
        real_imgs = [img[2] for img in imgs if img[3] == 'REAL']
        fake_imgs = [img[2] for img in imgs if img[3] == 'FAKE']
        real = random_rate(win_rate)
        link: str = random.choice(real_imgs) if real else random.choice(fake_imgs)
        return link
    
    def _get_win_rate_by_user_id(self, guild_id: int, user_id: int, random_user_enable: bool, random_taxa: float) -> tuple[None, None] |tuple[float, float]:
        users = self._db.get_users_by_guild(guild_id)
        for _, user_id, _, _, win_rate, checking, deny in users:
            if user_id == user_id:
                if deny == 1:
                    return (None, None)
                return win_rate, checking
        if random_user_enable:
            return random_taxa, 50.0 
        return (None, None)
    
    async def _send_msg(self, url: str, message: discord.Message):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    img_bytes = await resp.read()
                    file = discord.File(io.BytesIO(img_bytes))
                    await message.reply(file=file)
                else:
                    await message.reply(f" --  {url}")
    
    async def process(self, message: discord.Message, skip: bool, bot_user_id: int, is_mentioned: bool):
        if skip: return
        if is_mentioned and not message.reference: return
        
        guild = message.guild
        guild_id = guild.id if guild else 0
        chanel_id = message.channel.id
        message_author_id = message.author.id
        isBotMessage = message.author.id == bot_user_id
        if isBotMessage: return
        regras = self._db.get_config_by_guild(guild_id)
        if not regras: return
        if not regras[1]: return
        random_user_enable = regras[2] == 1
        all_channel_enable = regras[4] == 1
        random_taxa: float = regras[3]
        
        if is_mentioned:
            message_id_reply = message.reference.message_id if message.reference else 0
            message_id_reply = message_id_reply if message_id_reply else 0
            replied_message = await message.channel.fetch_message(message_id_reply)
            replied_author_id = replied_message.author.id
            if replied_author_id == bot_user_id: return
            _, checking = self._get_win_rate_by_user_id(guild_id, replied_author_id, random_user_enable, random_taxa)
            if not checking: checking = 50.0
            url = self._rng_service(guild_id, 100, checking)
            if not url: return
            await self._send_msg(url, replied_message)
            return
    
        if not all_channel_enable:
            channels = self._db.get_channels_by_guild(guild_id)
            if not any(channel[0] == chanel_id and channel[1] == 1 for channel in channels):
                return
            
        wrate, checking = self._get_win_rate_by_user_id(guild_id, message_author_id, random_user_enable, random_taxa)
        if not wrate or not checking: return
        url = self._rng_service(guild_id, wrate, checking)
        if not url: return
        await self._send_msg(url, message)