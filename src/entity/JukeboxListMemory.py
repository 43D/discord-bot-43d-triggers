from asyncio import Event, Task, wait_for
from dataclasses import dataclass, field
from collections import deque
from src.entity.YouTube.YouTubeEntity import YouTubeMetadata, YouTubeMetadataLazy

@dataclass
class JukeboxListMemory:
    guild_id: int
    channel_id: int | None = None
    channel_id_msg: int | None = None
    queue: deque[YouTubeMetadata | YouTubeMetadataLazy] = field(default_factory=deque)
    current_song: YouTubeMetadata | YouTubeMetadataLazy = field(default_factory=YouTubeMetadataLazy)
    audio_tasks: Task | None = None
    audio_player_events: Event | None = None
    audio_skip_events: Event | None = None

    @staticmethod
    def from_guild(guild_id: int, channel_id: int | None):
        return JukeboxListMemory(guild_id=guild_id, channel_id=channel_id)

    def update_audio_task(self, task: Task):
        if self.audio_tasks is not None:
            print("Cancelando tarefa de áudio existente")
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

    def delete_audio_task(self):
        if self.audio_tasks is not None:
            print("Cancelando tarefa de áudio")
            self.audio_tasks.cancel()
            self.audio_tasks = None
            
    def delete_event(self):
        if self.audio_skip_events is not None:
            self.audio_skip_events = None
            
    def delete_player_event(self):
        if self.audio_player_events is not None:
            self.audio_player_events = None

    def audio_is_play(self) -> bool:
        if self.audio_player_events is None:
            self.audio_player_events = Event()
        return self.audio_player_events.is_set()

    def audio_player_ending(self):
        if self.audio_player_events is None:
            self.audio_player_events = Event()
        self.audio_player_events.set()

    async def audio_player_await(self, timeout: float):
        if self.audio_player_events is None:
            self.audio_player_events = Event()
        await wait_for(self.audio_player_events.wait(), timeout=timeout + 10.0)
        self.audio_player_clear()

    def audio_player_clear(self):
        if self.audio_player_events is None:
            self.audio_player_events = Event()
        self.audio_player_events.clear()
        
    def check_empty(self) -> bool:
        return len(self.queue) == 0 and self.audio_tasks is None
    
    def add_song_to_queue(self, song_entries: YouTubeMetadata | YouTubeMetadataLazy):
        self.queue.append(song_entries)
        print(len(self.queue))

    def get_next_song(self) -> YouTubeMetadata | YouTubeMetadataLazy | None:
        if len(self.queue) == 0:
            return None
        data = self.queue.popleft()
        if data: self.current_song = data
        return data

    def song_is_currently_playing(self, url: str) -> bool:
        return self.current_song.id == url
    
    def song_is_in_queue(self, url: str) -> bool:
        return any(song.id == url for song in self.queue)

    def finish(self):
        self.queue.clear()
        self.delete_audio_task()
        self.delete_event()
        self.delete_player_event()