import asyncio
import yt_dlp
from copy import deepcopy
from src.entity.YouTube.YouTubeEntity import YouTubeMetadata, YouTubeMetadataLazy

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "youtube_include_dash_manifest": False,
    "youtube_include_hls_manifest": False,
    "ignoreerrors":True,
    "quiet":True,
    "no_warnings":True
}

async def search_ytdlp_async(query, playlist=False):
    opts = deepcopy(YDL_OPTS)
    opts["noplaylist"] = not playlist
    if playlist:
        opts.update({
            "noplaylist": False,
            "lazy_playlist": True,
            "extract_flat": "in_playlist",
            "ignoreerrors": True
        })

    def extract(query):
        with yt_dlp.YoutubeDL(opts) as ydl: # type: ignore
            return ydl.extract_info(query, download=False)
        
    loop = asyncio.get_running_loop()
    res =  await loop.run_in_executor(None, lambda: extract(query))
    entries = res.get("entries", [])
    if not playlist:
        return [YouTubeMetadata.from_dict(s) for s in entries]
    return [YouTubeMetadataLazy.from_dict(s) for s in entries]
