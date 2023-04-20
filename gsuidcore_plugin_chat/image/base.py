import copy
import httpx
import asyncio
import random
from abc import ABCMeta, abstractmethod
from gsuid_core.data_store import get_res_path
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger
from ..utils import request_img

class BaseImage(metaclass=ABCMeta):
  def __init__(self, config=None):
    super(BaseImage, self).__init__()
    self.config = copy.deepcopy(config)
    self.keys = []
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
      align_flag = True
      try:
        align_words = await align_fn(self.query, keywords)
        if '抱歉' in align_words:
          align_flag = False
      except:
        align_flag = False
        
      if align_flag:
        await bot.send(f'已根据查询文本 [{keywords}] 建立新的搜索词: [{align_words}]', at_sender=True)
        keywords = align_words
      
    self.send_urls = []
    await self._search(keywords.lower(), bot)
    if self.send_urls:
      await self.send_imgs(bot)


  @abstractmethod
  async def _search(self, keywords, bot: Bot):
    pass
    
    
  async def send_imgs(self, bot: Bot):
    urls = self.send_urls
    tasks = []
    for url in urls:
        tasks.append(asyncio.ensure_future(self._send_img(url, bot)))
    await asyncio.gather(*tasks)


  async def _send_img(self, url:str, bot: Bot):
    async with httpx.AsyncClient(verify=False, timeout=None) as client:
      try:
          img_bytes = await request_img(url, client)
          if img_bytes:
              await bot.send(img_bytes)
      except Exception as e:
          logger.info(f'{type(e)}: 图片发送失败: {e}')


  @abstractmethod
  def init_data(self):
    """初始化cookie或者key"""
    pass
  
  
  def _get_random_key(self):
    return random.choice(self.keys) 
  
  
  # 检查cookie或key的函数
  def _check_valid(self):
    return self.keys