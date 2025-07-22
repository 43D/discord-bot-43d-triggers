import random
import re
import discord
from src.database.db import MessagesDB, RegrasDB

class ProcessOsaka:
    def __init__(self, msDB: MessagesDB, db: RegrasDB):
        self._db = db
        self._msDB = msDB
        
    def _gerar_frase(self, frases, max_palavras=25):
        def contem_link(palavra):
            return palavra.startswith("http://") or palavra.startswith("https://")

        palavras_total = 0
        nova_frase = []
        links_encontrados = 0

        while palavras_total < max_palavras:
            frase = random.choice(frases)
            palavras = frase.split()

            if not palavras:
                continue

            # Decide se vai pegar um bloco sequencial ou palavras soltas
            if random.random() < 0.7 and len(palavras) >= 1:
                inicio = random.randint(0, len(palavras) - 1)
                tamanho_bloco = random.randint(1, min(6, len(palavras) - inicio))
                bloco = palavras[inicio:inicio + tamanho_bloco]
            else:
                max_amostragem = min(len(palavras), 3)
                if max_amostragem == 0:
                    continue
                tamanho_bloco = random.randint(1, max_amostragem)
                bloco = random.sample(palavras, tamanho_bloco)

            # Filtra links e conta quantos já foram adicionados
            bloco_filtrado = []
            for palavra in bloco:
                if contem_link(palavra):
                    if links_encontrados < 2:
                        bloco_filtrado.append(palavra)
                        links_encontrados += 1
                    # Ignora links excedentes
                else:
                    bloco_filtrado.append(palavra)

            if palavras_total + len(bloco_filtrado) > max_palavras:
                break

            nova_frase.extend(bloco_filtrado)
            palavras_total += len(bloco_filtrado)

        # Se houve links removidos, adiciona nova frase sem links
        while palavras_total < max_palavras:
            frase_extra = random.choice(frases)
            palavras_extra = frase_extra.split()
            palavras_sem_links = [p for p in palavras_extra if not contem_link(p)]

            if not palavras_sem_links:
                continue

            tamanho_extra = min(max_palavras - palavras_total, len(palavras_sem_links))
            nova_frase.extend(palavras_sem_links[:tamanho_extra])
            palavras_total += tamanho_extra

        return ' '.join(nova_frase) + '.'

    def _rng_msg(self, guild_id, id_chat, is_mentioned):
        def random_rate(rate: float):
            chance = random.randint(1, 10000)
            return (float(chance) / 100) <= rate
        
        rate = self._db.get_configs_by_tag(guild_id, "osaka_rate") if not is_mentioned else "100"
        rate_up = float(rate) if rate else 0.0
        modus_op = self._db.get_configs_by_tag(guild_id, "osaka_mode")
        canais = self._db.get_osaka_channels_by_guild(guild_id)
        if modus_op == "DENY":
            if id_chat in [c[0] for c in canais if c[1] == 1]:
                return False
        elif modus_op == "WHITE":
            if id_chat not in [c[0] for c in canais if c[1] == 0]:
                return False
        return random_rate(rate_up) if rate else False
    
    async def process(self, message: discord.Message, is_mentioned: bool):
        print("osakaBot processando mensagem...")
        guild_id = message.guild.id if message.guild else 0
        channel_id = message.channel.id
        if not self._rng_msg(guild_id, channel_id, is_mentioned):
            return 
        
        all_msg = self._msDB.get_all_messages(guild_id, message)
        if not all_msg or len(all_msg) < 1:
            return
        
        all_msg_strs: list[str] = [msg[0] for msg in all_msg]
        msg_final = self._gerar_frase(all_msg_strs)
        await message.channel.send(msg_final)