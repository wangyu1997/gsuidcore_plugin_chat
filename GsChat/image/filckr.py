import random

import httpx

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from .base import BaseImage
from .build import IMAGE


@IMAGE.register_module()
class FilckrImg(BaseImage):
    def __init__(self, config=None):
        super(FilckrImg, self).__init__(config)

    async def _search(self, keywords, bot: Bot):
        params = self.params
        params['api_key'] = self._get_random_key()
        params['text'] = keywords
        cnt = self.cnt

        try:
            async with httpx.AsyncClient(verify=False, timeout=None) as client:
                results = await client.get(self.api_url, params=params)
                results = results.json()
                total_num = len(results['photos']['photo'])
                sample_num = total_num if total_num <= cnt else cnt
                await bot.send(f"好的，共搜索到 [{total_num}] 张关于 [{keywords}] 的图片，为您随机发送{sample_num}张.")
                values = random.sample(results['photos']['photo'], sample_num)
                for value in values:
                    url = f"https://live.staticflickr.com/{value['server']}/{value['id']}_{value['secret']}_b.jpg"
                    self.send_urls.append(url)
        except Exception as e:
            logger.info(f'{type(e)}: 图片发送失败: {e}')

    def init_data(self):
        config = self.config
        self.api_url = config.api_url
        self.keys = config.api_keys
        self.method = config.method
        self.cnt = config.cnt
        self.params = {
            'method': self.method,
            'api_key': '',
            'text': '',
            'per_page': 500,
            'page': 1,
            'format': 'json',
            'nojsoncallback': 1
        }
