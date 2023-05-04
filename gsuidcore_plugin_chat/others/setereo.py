import os
import copy
import random
import asyncio
import threading
from .build import OTHER
from pathlib import Path
from ..utils import download_file
from gsuid_core.logger import logger
from gsuid_core.data_store import get_res_path


@OTHER.register_module()
class Setereo:
    def __init__(self, config=None):
        self.config = copy.deepcopy(config)
        self.data_path = get_res_path('GsChat') / 'setereo'
        self.download_url = config.data_url
        self.datas = []
        self.initial()

    def initial(self):
        threading.Thread(
            target=lambda: asyncio.run(self.init_data()), daemon=True
        ).start()

    async def init_data(self):
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.data_file: Path = self.data_path / self.config.data
        if not os.path.exists(self.data_file):
            logger.warning(f'setereo 数据文件[{self.data_file.name}]不存在，已切换到默认配置')
            self.data_file: Path = self.data_path / self.config.default
            if not os.path.exists(self.data_file):
                logger.info(f'setereo 正在下载配置文件...')
                await download_file(self.data_file, self.download_url)

        self.datas = open(self.data_file, 'r').readlines()

    async def get_setereo(self, name: str):
        msg = random.choice(self.datas).format(target_name=name)
        msg = msg.replace('\\n', '\n').replace('\\t', '\t')
        return msg
