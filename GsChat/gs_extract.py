import re
import uuid
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from .extract import EXTRACT, BiliBiliExtract
from httpx import AsyncClient
from .config import config
from .utils import send_img, send_file


extract_sv = SV('提取网页', pm=5, priority=9, enabled=True, black_list=[], area='ALL')

bili: BiliBiliExtract = EXTRACT.build(config.extract.bilibili)


@extract_sv.on_regex(
    (
        "b23.tv",
        "bili(22|23|33|2233).cn",
        ".bilibili.com",
        "^(av|cv)(\d+)",
        "^BV([a-zA-Z0-9]{10})+",
        "\[\[QQ小程序\]哔哩哔哩\]",
        "QQ小程序&amp;#93;哔哩哔哩",
        "QQ小程序&#93;哔哩哔哩",
    ),
    block=True,
)
async def bilibili(bot: Bot, event: Event):
    text = str(event.raw_text).strip()

    async with AsyncClient(timeout=None) as client:
        try:
            if re.search(r"(b23.tv)|(bili(22|23|33|2233).cn)", text, re.I):
                # 提前处理短链接，避免解析到其他的
                text = await bili.b23_extract(text, client)

            group_id = event.group_id if event.user_type != 'direct' else None
            msg, url = await bili.bili_keyword(group_id, text, client)
            if msg:
                if isinstance(msg, str):
                    # 说明是错误信息
                    await bot.send(msg)
                else:
                    await _send_msg(msg, bot)

            # if url and url.startswith('http'):
            #     print(url)
            #     await general_extract(url, bot)

        except Exception as e:
            logger.info(f"{type(e)}: {str(e)}")


async def _send_msg(msg, bot) -> None:
    try:
        await bot.send("\n".join(msg[1:]))
        await send_img(msg[0], bot)
    except Exception as e:
        logger.info(f"{type(e)}: {str(e)}")


"""以下为抖音/TikTok类型代码/Type code for Douyin/TikTok"""
url_type_code_dict = {
    # 抖音/Douyin
    2: 'image',
    4: 'video',
    68: 'image',
    # TikTok
    0: 'video',
    51: 'video',
    55: 'video',
    58: 'video',
    61: 'video',
    150: 'image',
}


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


async def general_extract(link, bot):
    async with AsyncClient(timeout=None, verify=None) as client:
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
                print(vedio_url)
                await send_file(vedio_url, bot, filename)
            else:
                pics = data['pics']
                if pics:
                    await send_img(pics, bot)


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
    async with AsyncClient(timeout=None, verify=None) as client:
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
