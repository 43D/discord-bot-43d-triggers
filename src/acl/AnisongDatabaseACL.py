import json
import os
from typing import Literal
import requests
from copy import deepcopy
from src.entity.AnnSongDB.AudioAMQ import AudioAMQ

class AnisongDatabaseACL:
    def __init__(self):
        self.__url_base = os.getenv("ANISONG_DATABASE_URL_BASE", "https://anisongdb.com/api/")
        self.__url_song_id = self.__url_base + "ann_song_ids_request"
        self.__url_anime_id = self.__url_base + "ann_ids_request"
        self.__url_search_name = self.__url_base + "search_request"
        self.__url_mal_id = self.__url_base + "mal_ids_request"
        self.__url_artist_id = self.__url_base + "artist_ids_request"
        self.__url_composer_id = self.__url_base + "composer_ids_request"   

    def __post_request(self, url: str, data: str) -> requests.Response:
        response = requests.post(url, data)
        response.raise_for_status()
        return response
    
    def get_song_id(self, ann_song_id: int) -> list[AudioAMQ]:
        payload = json.dumps({ "ann_song_ids": [ ann_song_id ] })
        response = self.__post_request(self.__url_song_id, payload)
        res = response.json() if response.status_code == 200 else []
        if isinstance(res, dict): return []
        return [AudioAMQ.from_dict(r) for r in res]
    
    def get_song_by_id_ann(self, ann_id: int) -> list[AudioAMQ]:
        payload = json.dumps({ "ann_ids": [ ann_id ] })
        response = self.__post_request(self.__url_anime_id, payload)
        res = response.json() if response.status_code == 200 else []
        if isinstance(res, dict): return []
        return [AudioAMQ.from_dict(r) for r in res] if len(res) > 0 else []
    
    def search_songs(self, name: str, type_search: Literal["song", "anime", "artist", "composer", "all"] = "all") -> list[AudioAMQ]:
        payload_dict:  dict[str, bool | dict[str, str | bool]]  = {
            "and_logic": False,
            "ignore_duplicate": False,
            "opening_filter": True,
            "ending_filter": True,
            "insert_filter": True,
            "normal_broadcast": True,
            "dub": True,
            "rebroadcast": True,
            "standard": True,
            "instrumental": True,
            "chanting": True,
            "character": True
        }

        payload_search = { "search": name, "partial_match": True }

        if type_search == "song" or type_search == "all":
            payload_dict["song_name_search_filter"] = deepcopy(payload_search)

        if type_search == "anime" or type_search == "all":
            payload_dict["anime_search_filter"] = deepcopy(payload_search)

        if type_search == "artist" or type_search == "all":
            payload_dict["artist_search_filter"] = deepcopy(payload_search)
            payload_dict["artist_search_filter"].update({"group_granularity": 0, "max_other_artist": 99 })

        if type_search == "composer" or type_search == "all":
            payload_dict["composer_search_filter"] = deepcopy(payload_search)
            payload_dict["composer_search_filter"].update({ "arrangement": True })

        payload = json.dumps(payload_dict)
        response = self.__post_request(self.__url_search_name, payload)
        res = response.json() if response.status_code == 200 else []
        if isinstance(res, dict): return []
        return [AudioAMQ.from_dict(r) for r in res] if len(res) > 0 else []
    
    def get_song_by_id_myanimelist(self, mal_id: int) -> list[AudioAMQ]:
        payload = json.dumps({ "mal_ids": [ mal_id ] })
        response = self.__post_request(self.__url_mal_id, payload)
        res = response.json() if response.status_code == 200 else []
        if isinstance(res, dict): return []
        return [AudioAMQ.from_dict(r) for r in res] if len(res) > 0 else []
    
    def get_song_by_artist_id(self, artist_id: int) -> list[AudioAMQ]:
        payload = json.dumps({ "artist_ids": [ artist_id ] })
        response = self.__post_request(self.__url_artist_id, payload)
        res = response.json() if response.status_code == 200 else []
        if isinstance(res, dict): return []
        return [AudioAMQ.from_dict(r) for r in res] if len(res) > 0 else []
    
    def get_song_by_composer_id(self, composer_id: int) -> list[AudioAMQ]:
        payload = json.dumps({ "composer_ids": [ composer_id ] })
        response = self.__post_request(self.__url_composer_id, payload)
        res = response.json() if response.status_code == 200 else []
        if isinstance(res, dict): return []
        return [AudioAMQ.from_dict(r) for r in res] if len(res) > 0 else []