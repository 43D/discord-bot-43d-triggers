from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class VoiceLogData:
    guild_id: int
    song_name: str
    song_path: str
    duration: float
    next_in: float
    channel_id_log: int

    @staticmethod
    def create_config(
        guild_id: int,
        song_name: str,
        song_path: str,
        duration: float,
        next_in: float,
        channel_id_log: int
    ) -> VoiceLogData:
        return VoiceLogData(
            guild_id=guild_id,
            song_name=song_name,
            song_path=song_path,
            duration=duration,
            next_in=next_in,
            channel_id_log=channel_id_log
        )