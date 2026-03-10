from asyncio import Event, Task, wait_for, TimeoutError
from dataclasses import dataclass
import os
import random


@dataclass
class SoundEffectListMemory:
    guild_id: int
    audio_ban_list: list[str]
    audio_tasks: Task | None = None
    audio_skip_events: Event | None = None
    channel_id: int | None = None

    @staticmethod
    def from_guild(guild_id: int, audio_ban_list: list[str]):
        return SoundEffectListMemory(guild_id=guild_id, audio_ban_list=audio_ban_list)
    
    @staticmethod
    def mock():
        return SoundEffectListMemory(guild_id=0, audio_ban_list=[])

    def add_to_ban_list(self, song_path: str):
        self.audio_ban_list.append(song_path)

    def check_ban_list(self, song_path: str) -> bool:
        return song_path in self.audio_ban_list
    
    def calculate_ban_list_size(self, audio_list_size: int) -> bool:
        BAN_LIST_MAX_INT = min(int(os.getenv("BAN_LIST_MAX", "75")), 100)
        BAN_LIST_FREE_UP_INT = max(1, min(int(os.getenv("BAN_LIST_FREE_UP", "15")), BAN_LIST_MAX_INT))
        BAN_LIST_MAX_FLOAT = BAN_LIST_MAX_INT / 100
        BAN_LIST_FREE_UP_FLOAT = BAN_LIST_FREE_UP_INT / 100
        if int(audio_list_size * BAN_LIST_MAX_FLOAT) <= len(self.audio_ban_list):
            stuff_to_remove = int(audio_list_size * BAN_LIST_FREE_UP_FLOAT)
            RANDOM_SEED = int(os.getenv("RANDOM_SEED", "43"))
            for _ in range(RANDOM_SEED):
                random.shuffle(self.audio_ban_list)
            self.audio_ban_list = self.audio_ban_list[stuff_to_remove:]
            return True
        return False
    
    def update_audio_task(self, task: Task):
        if self.audio_tasks is not None:
            self.audio_tasks.cancel()
        self.audio_tasks = task

    def audio_event_is_set(self) -> bool:
        if self.audio_skip_events is None:
            self.audio_skip_events = Event()
        return self.audio_skip_events.is_set()

    def audio_event_clear(self):
        if self.audio_skip_events is None:
            self.audio_skip_events = Event()
        self.audio_skip_events.clear()
        
    def audio_event_set(self):
        if self.audio_skip_events is None:
            self.audio_skip_events = Event()
        self.audio_skip_events.set()

    async def await_event(self):
        MINIMUS_DELAYS = int(os.getenv("MINIMUS_DELAYS", "60"))
        MAXIMUS_DELAYS = int(os.getenv("MAXIMUS_DELAYS", "660"))
        delay = random.randint(MINIMUS_DELAYS, MAXIMUS_DELAYS)
        print(f"[Guild {self.guild_id}] Áudio terminou, reiniciando em {delay}s...")
        if not self.audio_skip_events:
            self.audio_skip_events = Event()
        try:
            await wait_for(self.audio_skip_events.wait(), timeout=delay)
            print(f"[Guild {self.guild_id}] /next-audio solicitado — avançando para o próximo áudio")
            self.audio_skip_events.clear()
        except TimeoutError:
            pass

    def delete_audio_task(self):
        if self.audio_tasks is not None:
            self.audio_tasks.cancel()
            self.audio_tasks = None
            
    def delete_event(self):
        if self.audio_skip_events is not None:
            self.audio_skip_events = None