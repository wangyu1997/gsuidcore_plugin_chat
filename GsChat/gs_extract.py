import re
import uuid

from httpx import AsyncClient

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV
from .config import config
from .extract import EXTRACT, BiliBiliExtract
from .utils import send_img, send_file

extract_sv = SV('提取网页', pm=5, priority=9, enabled=True, black_list=[], area='ALL')

bili: BiliBiliExtract = EXTRACT.build(config.extract.bilibili)


@extract_sv.on_regex(
    (
        "b23.tv",
        "bili(22|23|33|2233).cn",
        ".bilibili.com",
        "^(av|cv)(\\d+)",
        "^BV([a-zA-Z0-9]{10})+",
        "[[QQ小程序]哔哩哔哩]",
        "QQ小程序&amp;#93;哔哩哔哩",
        "QQ小程序&#93;哔哩哔哩",
    ),
    block=True,
)
async def bilibili(bot: Bot, event: Event):
    await bili.handle_url(bot, event)


@extract_sv.on_regex(
    ("v.douyin.com",),
    block=True,
)
async def dy(bot: Bot, event: Event) -> None:
    msg: str = str(event.raw_text).strip()

    reg = r"(http:|https:)\/\/v.douyin.com\/[A-Za-z\d._?%&+\-=\/#]*"
    dou_url = re.search(reg, msg, re.I)[0]
    try:
        await general_extract(dou_url, bot)
    except Exception as e:
        logger.info(f'{type(e)}: {str(e)}')
        await bot.send("抖音解析出错啦")


@extract_sv.on_regex(
    ("vm.tiktok.com",),
    block=True,
)
async def tiktok(bot: Bot, event: Event) -> None:
    msg: str = str(event.raw_text).strip()
    reg = r"(http:|https:)\/\/vm.tiktok.com\/[A-Za-z\d._?%&+\-=\/#]*"
    dou_url = re.search(reg, msg, re.I)[0]
    try:
        await general_extract(dou_url, bot)
    except Exception as e:
        logger.info(f'{type(e)}: {str(e)}')
        await bot.send("Tiktok解析出错啦")


@extract_sv.on_regex(
    ("xiaohongshu.com",),
    block=True,
)
async def xhs(bot: Bot, event: Event) -> None:
    msg: str = str(event.raw_text).strip()
    reg = r"(http:|https:)\/\/(?:www\.)?xiaohongshu.com\/[A-Za-z\d._?%&+\-=\/#]*"
    dou_url = re.search(reg, msg, re.I)[0]
    try:
        await general_extract(dou_url, bot)
    except Exception as e:
        logger.info(f'{type(e)}: {str(e)}')
        await bot.send("小红书解析出错啦")


async def general_extract(link, bot):
    async with AsyncClient(timeout=None, verify=False) as client:
        url = "https://www.wouldmissyou.com/api/parse/"
        payload = {'link_text': link}
        resp = await client.post(url, data=payload)
        data = resp.json()['data']
        if data['code'] == 0:
            data = data['data']
            await bot.send(data['title'])
            if data['isVideo']:
                vedio_url = data['videoUrls']
                if isinstance(vedio_url, list):
                    vedio_url = vedio_url[0]
                filename = f'{str(uuid.uuid4())}.mp4'
                await send_file(vedio_url, bot, filename)
            else:
                pics = data['pics']
                if pics:
                    await send_img(pics, bot)
