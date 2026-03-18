from dataclasses import dataclass, field
from typing import Any

@dataclass
class LinkedIds:
    myanimelist: int | None = None
    anidb: int | None = None
    anilist: int | None = None
    kitsu: int | None = None

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "LinkedIds":
        data = data or {}
        return LinkedIds(
            myanimelist=data.get("myanimelist"),
            anidb=data.get("anidb"),
            anilist=data.get("anilist"),
            kitsu=data.get("kitsu"),
        )

@dataclass
class CreditPerson:
    id: int
    names: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CreditPerson":
        return CreditPerson(
            id=int(data.get("id", 0)),
            names=list(data.get("names", []) or []),
        )

@dataclass
class AudioAMQ:
    annId: int
    annSongId: int
    amqSongId: int
    animeENName: str
    animeJPName: str
    animeAltName: str | None
    animeVintage: str
    linked_ids: LinkedIds
    animeType: str
    animeCategory: str
    songType: str
    songName: str
    songArtist: str
    songComposer: str
    songArranger: str
    songDifficulty: float
    songCategory: str
    songLength: float
    isDub: bool
    isRebroadcast: bool
    HQ: str
    MQ: str
    audio: str
    artists: list[CreditPerson] = field(default_factory=list)
    composers: list[CreditPerson] = field(default_factory=list)
    arrangers: list[CreditPerson] = field(default_factory=list)

    @staticmethod
    def _parse_people(items: Any) -> list[CreditPerson]:
        if not isinstance(items, list):
            return []
        return [CreditPerson.from_dict(item) for item in items if isinstance(item, dict)]

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AudioAMQ":
        return AudioAMQ(
            annId=int(data.get("annId", 0)),
            annSongId=int(data.get("annSongId", 0)),
            amqSongId=int(data.get("amqSongId", 0)),
            animeENName=str(data.get("animeENName", "")),
            animeJPName=str(data.get("animeJPName", "")),
            animeAltName=data.get("animeAltName"),
            animeVintage=str(data.get("animeVintage", "")),
            linked_ids=LinkedIds.from_dict(data.get("linked_ids")),
            animeType=str(data.get("animeType", "")),
            animeCategory=str(data.get("animeCategory", "")),
            songType=str(data.get("songType", "")),
            songName=str(data.get("songName", "")),
            songArtist=str(data.get("songArtist", "")),
            songComposer=str(data.get("songComposer", "")),
            songArranger=str(data.get("songArranger", "")),
            songDifficulty=float(data.get("songDifficulty", 0.0)),
            songCategory=str(data.get("songCategory", "")),
            songLength=float(data.get("songLength", 0.0)),
            isDub=bool(data.get("isDub", False)),
            isRebroadcast=bool(data.get("isRebroadcast", False)),
            HQ=str(data.get("HQ", "")),
            MQ=str(data.get("MQ", "")),
            audio=str(data.get("audio", "")),
            artists=AudioAMQ._parse_people(data.get("artists")),
            composers=AudioAMQ._parse_people(data.get("composers")),
            arrangers=AudioAMQ._parse_people(data.get("arrangers")),
        )
