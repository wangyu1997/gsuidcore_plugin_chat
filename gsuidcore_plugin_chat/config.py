import os
import json
from pathlib import Path
from typing import Optional, Sequence
from pydantic import BaseSettings

module_path: Path = Path(__file__).parent
data_path: Path= module_path /'data'
config_path = data_path /'config.json'
keyword_path: Path = data_path / "resource/json/data.json"
anime_thesaurus: dict = json.load(open(keyword_path, "r", encoding="utf-8"))
audio_path: Path = data_path / "resource/audio"
audio_list: list = os.listdir(audio_path)

class Config(BaseSettings):
    bot_nickname: str = "我"
    smart_reply_path: Path = Path(f"{data_path}/cookies")
    ai_reply_private: bool = False
    openai_api_key: Optional[Sequence[str]]
    openai_max_tokens: int = 1000
    openai_cd_time: int = 600
    newbing_cd_time: int = 600
    newbing_style: str = "creative"
    bing_or_openai_proxy: str = ""
    superusers: Optional[Sequence[str]] = []
    

config_json = json.loads(open(config_path,'r').read())
config = Config.parse_obj(config_json)
