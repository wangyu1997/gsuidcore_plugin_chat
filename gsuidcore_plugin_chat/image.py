import base64
import random
import requests
from functools import partial

from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from .utils import *

image_sv = SV(
    '图片查询',
    pm=6,  
    priority=15,
    enabled=True,
    black_list=[],
    area='ALL'
)



ENDPOINT = 'https://www.flickr.com/services/rest/'
METHOD = 'flickr.photos.search'
API_KEY = config.flickr_api


@image_sv.on_keyword(('图片','照片'), block=True,)
async def reserve_openai(bot:Bot, event:Event):
    text = event.text
    if "张" not in text:
      return
    
    keyword = text.split("张")[1].split("的")[0]
    
    params = {
      'method': METHOD,
      'api_key': API_KEY,
      'text': keyword.replace(' ', ''),
      'per_page': 500,
      'page': 1,
      'format': 'json',
      'nojsoncallback': 1
    }
    try:
      loop = asyncio.get_event_loop()      
      results = requests.get(ENDPOINT, params=params).json()
      data = await loop.run_in_executor(None, partial(requests.get, ENDPOINT, params))
      data = data.json()
      total_num = len(results['photos']['photo'])
      
      sample_num = total_num if total_num<=3 else 3
        
      await bot.send(f"好的，共搜索到 [{total_num}] 张关于 [{keyword}] 的图片，为您随机发送{sample_num}张.")

      values = random.sample(results['photos']['photo'], sample_num)

      for value in values:
        url = f"https://live.staticflickr.com/{value['server']}/{value['id']}_{value['secret']}_b.jpg"
        response = await loop.run_in_executor(None, requests.get, url)
        img_base64 = base64.b64encode(response.content)
        img_bytes = base64.b64decode(img_base64)
        await bot.send(img_bytes)
    except e:
      return
  
    