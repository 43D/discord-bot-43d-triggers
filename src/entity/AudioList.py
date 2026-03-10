from asyncio import Event, Task
import asyncio
from dataclasses import dataclass
import os
import random

@dataclass
class AudioListMemory:
    guild_id: int
    audio_ban_list: list[str]
    audio_tasks: Task | None = None
    audio_skip_events: Event | None = None
    channel_id: int | None = None

    @staticmethod
    def from_guild(guild_id: int, audio_ban_list: list[str]):
        return AudioListMemory(guild_id=guild_id, audio_ban_list=audio_ban_list)
    
    @staticmethod
    def mock():
        return AudioListMemory(guild_id=0, audio_ban_list=[])

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

    def delete_audio_task(self):
        if self.audio_tasks is not None:
            self.audio_tasks.cancel()
            self.audio_tasks = None

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
            await asyncio.wait_for(self.audio_skip_events.wait(), timeout=delay)
            print(f"[Guild {self.guild_id}] /next-audio solicitado — avançando para o próximo áudio")
            self.audio_skip_events.clear()
        except asyncio.TimeoutError:
            pass

    def delete_event(self):
        if self.audio_skip_events is not None:
            self.audio_skip_events = None

@dataclass
class AudioListManager:
    audio_guild_manager: dict[str, AudioListMemory]
    audio_list: list[str]

    def update_audio_list(self):
        base_path = os.path.join(
            os.path.dirname(__file__).replace('/src', '').replace('\\src', '').replace('/entity', '').replace('\\entity', ''), 
            'sounds'
        )
        audio_list = []
        if not os.path.exists(base_path):
            return
        for file in os.listdir(base_path):
            if file.endswith('.ogg') or file.endswith('.mp3'):
                filepath = os.path.join(base_path, file)
                audio_list.append(filepath)
        random.shuffle(audio_list)
        self.audio_list = audio_list

    def __add_to_ban_list(self, guild_id: int, song_path: str):
        if str(guild_id) not in self.audio_guild_manager:
            self.audio_guild_manager[str(guild_id)] = AudioListMemory.from_guild(guild_id, [song_path])
        self.audio_guild_manager[str(guild_id)].add_to_ban_list(song_path)

    def __calculate_ban_list_size(self, guild_id: int) -> bool:
        if str(guild_id) not in self.audio_guild_manager:
            return False
        return self.audio_guild_manager[str(guild_id)].calculate_ban_list_size(len(self.audio_list))

    def get_next_song(self, guild_id: int) -> str:
        if str(guild_id) not in self.audio_guild_manager:
            self.audio_guild_manager[str(guild_id)] = AudioListMemory.from_guild(guild_id, [])
        audio_list_final = [song for song in self.audio_list if not self.audio_guild_manager[str(guild_id)].check_ban_list(song)]
        RANDOM_SEED = int(os.getenv("RANDOM_SEED", "43"))
        for _ in range(RANDOM_SEED):
            random.shuffle(audio_list_final)
        song = random.choice(audio_list_final)
        self.__add_to_ban_list(guild_id, song)
        self.__calculate_ban_list_size(guild_id)
        return song
    
    def get_manager_by_guild_id(self, guild_id: int) -> AudioListMemory:
        if str(guild_id) not in self.audio_guild_manager:
            self.audio_guild_manager[str(guild_id)] = AudioListMemory.from_guild(guild_id, [])
        return self.audio_guild_manager[str(guild_id)]

    def delete_manager_by_guild_id(self, guild_id: int):
        if str(guild_id) not in self.audio_guild_manager:
            return
        
        self.audio_guild_manager[str(guild_id)].delete_event()
        self.audio_guild_manager[str(guild_id)].delete_audio_task()

    def set_channel_id(self, guild_id: int, channel_id: int):
        if str(guild_id) not in self.audio_guild_manager:
            self.audio_guild_manager[str(guild_id)] = AudioListMemory.from_guild(guild_id, [])
        self.audio_guild_manager[str(guild_id)].channel_id = channel_id

    def set_channel_ban_list(self, guild_id: int, ban_list: list[str]):
        if str(guild_id) not in self.audio_guild_manager:
            self.audio_guild_manager[str(guild_id)] = AudioListMemory.from_guild(guild_id, [])
        self.audio_guild_manager[str(guild_id)].audio_ban_list = ban_list

    @staticmethod
    def from_db(lista: list[tuple[int, int, int]]):
        entity = AudioListManager(audio_guild_manager={}, audio_list=[])
        entity.update_audio_list()

        for guild_id, channel_id, _ in lista:
            try:
                gid = int(guild_id)
                cid = int(channel_id)
            except Exception:
                continue
            if str(guild_id) not in entity.audio_guild_manager:
                entity.audio_guild_manager[str(guild_id)] = AudioListMemory.from_guild(guild_id, [])
            entity.audio_guild_manager[str(guild_id)].channel_id = channel_id

        return entity