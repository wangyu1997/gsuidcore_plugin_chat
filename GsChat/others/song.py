import copy

import httpx

from gsuid_core.logger import logger
from .build import OTHER


@OTHER.register_module()
class Song:
    def __init__(self, config=None):
        self.config = copy.deepcopy(config)
        self.api = config.api

    async def init_data(self):
        pass

    async def get_song(self, song_name):
        return await self.get_song_id(song_name)

    async def get_song_id(self, singer: str):
        params = {
            "keywords": "",
        }
        url = f"{self.api}/search"
        params["keywords"] = singer

        try:
            async with httpx.AsyncClient(timeout=None, verify=False) as client:
                res = await client.get(url, params=params)
                res = res.json()
                for song in res["result"]["songs"]:
                    song_id = song["id"]
                    song_url = f"{self.api}/song/url?id={song_id}"
                    song_res = await client.get(song_url)
                    song_res = song_res.json()["data"]
                    if len(song_res) == 0:
                        continue
                    song_res = song_res[0]
                    if "url" in song_res and song_res["url"]:
                        return {
                            "name": song["name"],
                            "artist": song["artists"][0]["name"],
                            "album": song["album"]["name"],
                            "img_url": song["artists"][0]["img1v1Url"],
                            "song_url": song_res["url"],
                        }
        except Exception as e:
            logger.error(f"{type(e)}: get song failed {str(e)}")
            return None
