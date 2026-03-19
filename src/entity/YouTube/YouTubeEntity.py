from dataclasses import dataclass, field
from typing import Any

@dataclass
class HttpHeaders:
    user_agent: str = ""
    accept: str = ""
    accept_language: str = ""
    sec_fetch_mode: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "HttpHeaders":
        data = data or {}

        known = {
            "User-Agent",
            "Accept",
            "Accept-Language",
            "Sec-Fetch-Mode",
        }

        extra_headers = {
            str(k): str(v)
            for k, v in data.items()
            if isinstance(k, str) and k not in known
        }

        return HttpHeaders(
            user_agent=str(data.get("User-Agent", "")),
            accept=str(data.get("Accept", "")),
            accept_language=str(data.get("Accept-Language", "")),
            sec_fetch_mode=str(data.get("Sec-Fetch-Mode", "")),
            extra=extra_headers,
        )
    
@dataclass
class Thumbnail:
    url: str = ""
    height: int = 0
    width: int = 0
    preference: int = 0

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "Thumbnail":
        data = data or {}
        return Thumbnail(
            url=str(data.get("url", "")),
            height=int(data.get("height", 0) or 0),
            width=int(data.get("width", 0) or 0),
            preference=int(data.get("preference", 0) or 0)
        )

@dataclass
class YouTubeMetadata:
    id: str
    title: str
    thumbnail: str
    duration: int
    webpage_url: str
    playable_in_embed: bool
    album: str
    artists: list[str] = field(default_factory=list)
    track: str = ""
    release_year: int = 0
    channel: str = ""
    channel_follower_count: int = 0
    creators: list[str] = field(default_factory=list)
    uploader: str = ""
    url: str = ""
    http_headers: HttpHeaders = field(default_factory=HttpHeaders)
    thumbnails: list[Thumbnail] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "YouTubeMetadata":
        thumbs = data.get("thumbnails", [])
        return YouTubeMetadata(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            thumbnail=str(data.get("thumbnail", "")),
            duration=int(data.get("duration", 0) or 0),
            webpage_url=str(data.get("webpage_url", "")),
            playable_in_embed=bool(data.get("playable_in_embed", False)),
            album=str(data.get("album", "")),
            artists=[str(a) for a in (data.get("artists", []) or []) if a is not None],
            track=str(data.get("track", "")),
            release_year=int(data.get("release_year", 0) or 0),
            channel=str(data.get("channel", "")),
            channel_follower_count=int(data.get("channel_follower_count", 0) or 0),
            creators=[str(c) for c in (data.get("creators", []) or []) if c is not None],
            uploader=str(data.get("uploader", "")),
            url=str(data.get("url", "")),
            http_headers=HttpHeaders.from_dict(data.get("http_headers")),
            thumbnails=[Thumbnail.from_dict(t) for t in thumbs if isinstance(t, dict)]
        )
    
@dataclass
class YouTubeMetadataLazy:
    id: str = ""
    url: str = ""
    title: str = ""
    duration: int = 0
    channel: str = ""
    uploader: str = ""
    thumbnails: list[Thumbnail] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "YouTubeMetadataLazy":
        thumbs = data.get("thumbnails", [])
        return YouTubeMetadataLazy(
            id=str(data.get("id", "")),
            url=str(data.get("url", "")),
            title=str(data.get("title", "")),
            duration=int(data.get("duration", 0) or 0),
            channel=str(data.get("channel", "")),
            uploader=str(data.get("uploader", "")),
            thumbnails=[Thumbnail.from_dict(t) for t in thumbs if isinstance(t, dict)],
        )
    