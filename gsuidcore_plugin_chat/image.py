import httpx
import asyncio
import random

from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from gsuid_core.logger import logger

from .utils import *
from .config import config


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


@image_sv.on_keyword(('图片', '照片'), block=True,)
async def reserve_openai(bot: Bot, event: Event):
    if not API_KEY:
        await bot.send('请配置key之后再来搜索图片哦.', at_sender=True)
        return

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
        async with httpx.AsyncClient(verify=False, timeout=None) as client:
            results = await client.get(ENDPOINT, params=params)
            results = results.json()
            total_num = len(results['photos']['photo'])

            sample_num = total_num if total_num <= 3 else 3

            await bot.send(f"好的，共搜索到 [{total_num}] 张关于 [{keyword}] 的图片，为您随机发送{sample_num}张.")

            values = random.sample(results['photos']['photo'], sample_num)

            for value in values:
                url = f"https://live.staticflickr.com/{value['server']}/{value['id']}_{value['secret']}_b.jpg"
                img_bytes = await request_img(url, client)
                if img_bytes:
                    await bot.send(img_bytes)
    except Exception as e:
        logger.info(f'图片发送失败: {e}')


@image_sv.on_prefix(('搜索'), block=True,)
async def reserve_openai(bot: Bot, event: Event):
    web_search_key = config.rapid_api_key
    if not web_search_key:
        await bot.send('请配置key之后再来搜索图片哦.', at_sender=True)
        return

    text = event.text.strip()
    if not text:
        await bot.send('没有提取到有效的词条。', at_sender=True)
        return
    prompt = [
        {'role': 'user', 'content': f'帮我把下面文本用一个简短的英文实体名词概括，可以是多个单词，直接返回短语即可: {text}'}]

    image_url = "https://contextualwebsearch-websearch-v1.p.rapidapi.com/api/Search/ImageSearchAPI"

    image_headers = {
        "X-RapidAPI-Key": f"{web_search_key}",
        "X-RapidAPI-Host": "contextualwebsearch-websearch-v1.p.rapidapi.com"
    }

    async with httpx.AsyncClient(verify=False, timeout=None) as client:
        try:

            res = await request_chat(prompt, client)
            query_text = res.replace('.', '')
            await bot.send(f'已根据查询文本 [{text}] 建立新的搜索词: [{query_text}]', at_sender=True)
            querystring = {"q": query_text, "pageNumber": "1",
                           "pageSize": "50", "autoCorrect": "true"}
            query_res = await client.get(image_url, headers=image_headers, params=querystring)
            query_res = query_res.json()
            total_num = query_res['totalCount']
            urls = [i['url'] for i in query_res['value']]
            thumbnails = [i['thumbnail'] for i in query_res['value']]
            sample_num = len(urls) if len(urls) <= 5 else 5
            await bot.send(f"好的，共搜索到 [{total_num}] 张关于 [{text}] 的图片，为您随机发送{sample_num}张. \n网络图片，可能存在资源不存在的情况，望谅解！", at_sender=True)
            urls = random.sample(urls, sample_num)
            thumbnails = random.sample(thumbnails, sample_num)

            async def get_img(url, thumbnail):
                try:
                    img_bytes = await request_img(url, client)
                    if img_bytes:
                        await bot.send(img_bytes)
                except Exception as e:
                    try:
                        img_bytes = await request_img(thumbnail, client)
                        if img_bytes:
                            await bot.send(img_bytes)
                    except Exception as f:
                        logger.info(f'图片发送失败: {e} {f}')

            tasks = []
            for url, thumbnail in zip(urls, thumbnails):
                tasks.append(asyncio.ensure_future(get_img(url, thumbnail)))
            await asyncio.gather(*tasks)
        except Exception as e:
            await bot.send(f'今日查询次数已使用完毕 {e}', at_sender=True)
