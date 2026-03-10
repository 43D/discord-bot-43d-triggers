from asyncio import Event, Task
from dataclasses import dataclass, field
from collections import deque

@dataclass
class JukeboxListMemory:
    guild_id: int
    channel_id: int | None = None
    queue: deque = field(default_factory=deque)
    audio_tasks: Task | None = None
    audio_skip_events: Event | None = None

    @staticmethod
    def from_guild(guild_id: int, channel_id: int | None):
        return JukeboxListMemory(guild_id=guild_id, channel_id=channel_id)

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

    def delete_audio_task(self):
        if self.audio_tasks is not None:
            self.audio_tasks.cancel()
            self.audio_tasks = None
            
    def delete_event(self):
        if self.audio_skip_events is not None:
            self.audio_skip_events = None