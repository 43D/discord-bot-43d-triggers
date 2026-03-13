from dataclasses import dataclass
import os
import random
from typing import Literal
from src.entity.SoundEffectListMemory import SoundEffectListMemory
from src.entity.JukeboxListMemory import JukeboxListMemory

@dataclass
class AudioManager:
    sound_effects: SoundEffectListMemory
    jukebox: JukeboxListMemory
    audio_source: Literal["JUKEBOX", "SOUND_EFFECT"] = "SOUND_EFFECT"
    guild_id: int = 0

    def get_manager(self):
        if self.audio_source == "SOUND_EFFECT":
            return self.sound_effects
        return self.jukebox

    def delete_manager(self):
        data = self.jukebox if self.audio_source == "JUKEBOX" else self.sound_effects
        data.delete_event()
        data.delete_audio_task()

    def set_channel_id(self, channel_id: int):
        self.jukebox.channel_id = channel_id
        self.sound_effects.channel_id = channel_id

    def __add_to_ban_list(self, song_path: str):
        self.sound_effects.add_to_ban_list(song_path)

    def __calculate_ban_list_size(self, len_audio_list: int) -> bool:
        return self.sound_effects.calculate_ban_list_size(len_audio_list)

    def __get_next_song_sound_effect(self, audio_list: list[str]) -> str:
        audio_list_final = [song for song in audio_list if not self.sound_effects.check_ban_list(song)]
        RANDOM_SEED = int(os.getenv("RANDOM_SEED", "43"))
        for _ in range(RANDOM_SEED):
            random.shuffle(audio_list_final)
        song = random.choice(audio_list_final)
        self.__add_to_ban_list(song)
        self.__calculate_ban_list_size(len(audio_list))
        return song

    def __get_next_song_jukebox(self) -> str:
        return ""
    
    def get_next_song(self, audio_list: list[str], guild_id: int) -> str:
        if self.audio_source == "JUKEBOX":
            return self.__get_next_song_jukebox()
        return self.__get_next_song_sound_effect(audio_list)

    def set_audio_source(self, audio_source: Literal["JUKEBOX", "SOUND_EFFECT"]):
        self.audio_source = audio_source

    def check_audio_jukebox_empty(self) -> bool:
        return self.jukebox.check_empty()

    @staticmethod
    def from_db(guild_id: int, channel_id: int, audio_ban_list: list[str], audio_source: Literal["JUKEBOX", "SOUND_EFFECT"] = "SOUND_EFFECT"):
        manager = AudioManager(
            sound_effects=SoundEffectListMemory.from_guild(guild_id, audio_ban_list),
            jukebox=JukeboxListMemory.from_guild(guild_id, channel_id),
            guild_id=guild_id,
            audio_source=audio_source
        )
        manager.set_channel_id(channel_id)
        return manager

@dataclass
class AudioListManager:
    audio_manager: dict[str, AudioManager]
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

    def get_by_guild_id(self, guild_id: int):
        if not str(guild_id) in self.audio_manager:
            self.audio_manager[str(guild_id)] = AudioManager.from_db(guild_id, 0, [])
        return self.audio_manager[str(guild_id)]

    def get_next_song(self, guild_id: int) -> str:
        m = self.get_by_guild_id(guild_id)
        return m.get_next_song(self.audio_list, guild_id)
    
    def get_manager_by_guild_id(self, guild_id: int):
        m = self.get_by_guild_id(guild_id)
        return m.get_manager()

    def delete_manager_by_guild_id(self, guild_id: int):
        self.get_by_guild_id(guild_id).delete_manager()

    def set_channel_id(self, guild_id: int, channel_id: int):
        self.get_by_guild_id(guild_id).set_channel_id(channel_id)

    def set_sounds_ban_list(self, guild_id: int, ban_list: list[str]):
        self.get_by_guild_id(guild_id).sound_effects.audio_ban_list = ban_list

    def set_audio_source(self, guild_id: int, audio_source: Literal["JUKEBOX", "SOUND_EFFECT"]):
        m = self.get_by_guild_id(guild_id)
        print(f"[Guild {guild_id}] Alterando fonte de áudio para: {audio_source}")
        m.set_audio_source(audio_source)

    @staticmethod
    def from_db(lista: list[tuple[int, int, int]]):
        entity = AudioListManager(audio_manager={}, audio_list=[])
        entity.update_audio_list()
        for guild_id, channel_id, _ in lista:
            try:
                int(guild_id)
                int(channel_id)
            except Exception:
                continue
            entity.audio_manager[str(guild_id)] = AudioManager.from_db(guild_id, channel_id, [])
        return entity