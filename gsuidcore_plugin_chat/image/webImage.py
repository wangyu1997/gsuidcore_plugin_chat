from .base import BaseImage
from .base import BaseImage
import httpx
import random
from .build import IMAGE
from gsuid_core.bot import Bot


@IMAGE.register_module()
class WebSearchImg(BaseImage):
  def __init__(self, config=None):
    super(WebSearchImg, self).__init__(config)
    

  async def _search(self, keywords, bot: Bot):
    headers = self.headers
    headers['X-RapidAPI-Key'] = self._get_random_key()
    params = self.params
    params['q'] = keywords
    cnt = self.cnt

    async with httpx.AsyncClient(verify=False, timeout=None) as client:
        try:
            query_res = await client.get(self.api_url, headers=headers, params=params)
            query_res = query_res.json()
            total_num = query_res['totalCount']
            urls = [i['url'] for i in query_res['value']]
            sample_num = len(urls) if len(urls) <= cnt else cnt
            await bot.send(f"好的，共搜索到 [{total_num}] 张关于 [{keywords}] 的图片，为您随机发送{sample_num}张. \n网络图片，可能存在资源不存在的情况，望谅解！", at_sender=True)
            self.send_urls = random.sample(urls, sample_num)
        except Exception as e:
            await bot.send(f'今日查询次数已使用完毕 {e}', at_sender=True)

  
  def init_data(self):
      config = self.config
      self.api_url = config.api_url
      self.keys = config.api_keys
      self.cnt = config.cnt
      self.headers = {
        "X-RapidAPI-Key": "",
        "X-RapidAPI-Host": "contextualwebsearch-websearch-v1.p.rapidapi.com"
      }
      self.params = {
        "q": "", 
        "pageNumber": "1",
        "pageSize": "50", 
        "autoCorrect": "true"
      }


  
  
  