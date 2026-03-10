from dataclasses import dataclass
import os
import random
from typing import Literal
from src.entity.SoundEffectListMemory import SoundEffectListMemory
from src.entity.JukeboxListMemory import JukeboxListMemory

@dataclass
class AudioManager:
    sound_effects: dict[str, SoundEffectListMemory]
    jukebox: dict[str, JukeboxListMemory]
    audio_source: Literal["JUKEBOX", "SOUND_EFFECT"] = "SOUND_EFFECT"

    def get_manager(self, guild_id):
        if self.audio_source == "SOUND_EFFECT" and str(guild_id) not in self.sound_effects:
            self.sound_effects[str(guild_id)] = SoundEffectListMemory.from_guild(guild_id, [])
        elif self.audio_source == "JUKEBOX" and str(guild_id) not in self.jukebox:
            self.jukebox[str(guild_id)] = JukeboxListMemory.from_guild(guild_id, 0)

        return self.jukebox.get(str(guild_id)) if self.audio_source == "JUKEBOX" else self.sound_effects.get(str(guild_id))

    def delete_manager(self, guild_id):
        data = None
        if self.audio_source == "JUKEBOX" and str(guild_id) in self.jukebox:
            data = self.jukebox[str(guild_id)]
        elif self.audio_source == "SOUND_EFFECT" and str(guild_id) in self.sound_effects:
            data = self.sound_effects[str(guild_id)]
        if data:
            data.delete_event()
            data.delete_audio_task()

    def set_channel_id(self, guild_id: int, channel_id: int):
        if self.audio_source == "JUKEBOX":
            if str(guild_id) not in self.jukebox:
                self.jukebox[str(guild_id)] = JukeboxListMemory.from_guild(guild_id, channel_id)
            else:
                self.jukebox[str(guild_id)].channel_id = channel_id
        else:
            if str(guild_id) not in self.sound_effects:
                self.sound_effects[str(guild_id)] = SoundEffectListMemory.from_guild(guild_id, [])
            self.sound_effects[str(guild_id)].channel_id = channel_id

    def __add_to_ban_list(self, guild_id: int, song_path: str):
        if str(guild_id) not in self.sound_effects:
            self.sound_effects[str(guild_id)] = SoundEffectListMemory.from_guild(guild_id, [song_path])
        self.sound_effects[str(guild_id)].add_to_ban_list(song_path)

    def __calculate_ban_list_size(self, guild_id: int, len_audio_list: int) -> bool:
        if str(guild_id) not in self.sound_effects:
            return False
        return self.sound_effects[str(guild_id)].calculate_ban_list_size(len_audio_list)

    def __get_next_song_sound_effect(self, audio_list: list[str], guild_id: int) -> str:
        if str(guild_id) not in self.sound_effects:
            self.sound_effects[str(guild_id)] = SoundEffectListMemory.from_guild(guild_id, [])
        audio_list_final = [song for song in audio_list if not self.sound_effects[str(guild_id)].check_ban_list(song)]
        RANDOM_SEED = int(os.getenv("RANDOM_SEED", "43"))
        for _ in range(RANDOM_SEED):
            random.shuffle(audio_list_final)
        song = random.choice(audio_list_final)
        self.__add_to_ban_list(guild_id, song)
        self.__calculate_ban_list_size(guild_id, len(audio_list))
        return song

    def __get_next_song_jukebox(self, guild_id: int) -> str:
        return ""
    
    def get_next_song(self, audio_list: list[str], guild_id: int) -> str:
        if self.audio_source == "JUKEBOX":
            return self.__get_next_song_jukebox(guild_id)
        return self.__get_next_song_sound_effect(audio_list, guild_id)


    @staticmethod
    def mock():
        return AudioManager(sound_effects={}, jukebox={})


@dataclass
class AudioListManager:
    audio_manager: AudioManager
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

    def get_next_song(self, guild_id: int) -> str:
        return self.audio_manager.get_next_song(self.audio_list, guild_id)
    
    def get_manager_by_guild_id(self, guild_id: int):
        return self.audio_manager.get_manager(str(guild_id))

    def delete_manager_by_guild_id(self, guild_id: int):
        self.audio_manager.delete_manager(str(guild_id))

    def set_channel_id(self, guild_id: int, channel_id: int):
        self.audio_manager.set_channel_id(guild_id, channel_id)

    def set_sounds_ban_list(self, guild_id: int, ban_list: list[str]):
        if str(guild_id) not in self.audio_manager.sound_effects:
            self.audio_manager.sound_effects[str(guild_id)] = SoundEffectListMemory.from_guild(guild_id, [])
        self.audio_manager.sound_effects[str(guild_id)].audio_ban_list = ban_list

    @staticmethod
    def from_db(lista: list[tuple[int, int, int]]):
        entity = AudioListManager(audio_manager=AudioManager.mock(), audio_list=[])
        entity.update_audio_list()
        for guild_id, channel_id, _ in lista:
            try:
                int(guild_id)
                int(channel_id)
            except Exception:
                continue
            if str(guild_id) not in entity.audio_manager.sound_effects:
                entity.audio_manager.sound_effects[str(guild_id)] = SoundEffectListMemory.from_guild(guild_id, [])
            entity.audio_manager.sound_effects[str(guild_id)].channel_id = channel_id
            if str(guild_id) not in entity.audio_manager.jukebox:
                entity.audio_manager.jukebox[str(guild_id)] = JukeboxListMemory.from_guild(guild_id, channel_id)

        return entity