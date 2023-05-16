import copy
import random
from abc import ABCMeta, abstractmethod

from gsuid_core.bot import Bot
from gsuid_core.data_store import get_res_path
from gsuid_core.models import Event
from ..utils import send_img


class BaseImage(metaclass=ABCMeta):
    def __init__(self, config=None):
        super(BaseImage, self).__init__()
        self.config = copy.deepcopy(config)
        self.keys = []
        self.Us = []
        self.query = config.query
        self.res_path = get_res_path('GsChat')
        self.send_urls = []
        self.init_data()

    async def search(self, align_fn, bot: Bot, event: Event, convert=False):
        """重置bot"""
        # 返回False则等待cd
        if not self._check_valid():
            await bot.send(f'请先配置Cookie或API-Key再尝试使用.')

        keywords = event.text.strip()

        if convert:
            try:
                align_words = await align_fn(self.query, keywords)
                if '抱歉' not in align_words:
                    await bot.send(
                        f'已根据查询文本 [{keywords}] 建立新的搜索词: [{align_words}]', at_sender=True
                    )
                    keywords = align_words
            except:
                pass

        self.send_urls = []
        await self._search(keywords.lower(), bot)
        if self.send_urls:
            await send_img(self.send_urls, bot)

    @abstractmethod
    async def _search(self, keywords, bot: Bot):
        pass

    @abstractmethod
    def init_data(self):
        """初始化cookie或者key"""
        pass

    def _get_random_key(self):
        return random.choice(self.keys if self.keys else self.Us)

    # 检查cookie或key的函数
    def _check_valid(self):
        return self.keys or self.Us
