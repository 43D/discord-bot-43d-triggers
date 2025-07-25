import asyncio
from collections import deque
import discord
from src.util.ProcessHistory import ProcessHistory
from src.database.db import RegrasDB

class ProcessadorHistoricoManager:
    def __init__(self, db: RegrasDB, max_concurrent=4):
        self._db = db
        self._processar_historico = ProcessHistory(self._db)
        self.queue = deque()
        self.active_tasks = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.lock = asyncio.Lock()

    async def adicionar_guild(self, guild: discord.Guild | None):
        if not guild:
            print("Guild is None, cannot process history.")
            return
        async with self.lock:
            guild_id = guild.id

            # Se já está na fila ou sendo processado, cancela e remove
            if guild_id in self.active_tasks:
                task = self.active_tasks[guild_id]
                task.cancel()
                del self.active_tasks[guild_id]

            # Adiciona no final da fila
            self.queue.append(guild)

            # Inicia o processamento se possível
            asyncio.create_task(self._processar_fila())

    async def _processar_fila(self):
        async with self.lock:
            while self.queue and len(self.active_tasks) < self.semaphore._value:
                guild = self.queue.popleft()
                guild_id = guild.id

                # Cria e registra a tarefa
                task = asyncio.create_task(self._executar(guild))
                self.active_tasks[guild_id] = task

    async def _executar(self, guild: discord.Guild):
        guild_id = guild.id
        try:
            async with self.semaphore:
                print(f"Iniciando processamento para guild {guild_id}")
                await self._processar_historico.processar_historico(guild)
                print(f"Finalizado processamento para guild {guild_id}")
        except asyncio.CancelledError:
            print(f"Processamento cancelado para guild {guild_id}")
        finally:
            async with self.lock:
                self.active_tasks.pop(guild_id, None)
                # Tenta continuar a fila
                asyncio.create_task(self._processar_fila())