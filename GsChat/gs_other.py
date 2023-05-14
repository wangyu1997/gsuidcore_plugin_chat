from .others import OTHER
import httpx
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from .config import config


other_sv = SV("其他相关", pm=6, priority=1400, enabled=True, black_list=[], area="ALL")


browser = OTHER.build(config.other.browser)
setereo = OTHER.build(config.other.setereo)
song = OTHER.build(config.other.song)


@other_sv.on_regex(
    (
        '[a-zA-z]+://[^\s]*',
        'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)',
    ),
    block=True,
)
async def screenshot_handle(bot: Bot, event: Event):
    print(event.command)
    text = event.command
    if not text:
        return
    await bot.send(await browser.screenshot(text))


@other_sv.on_prefix(
    ("发病"),
    block=True,
)
async def setereo_handle(bot: Bot, event: Event):
    text = event.text.strip()
    if not text:
        return
    await bot.send(await setereo.get_setereo(text))


@other_sv.on_prefix(
    ("点歌"),
    block=True,
)
async def setereo_handle(bot: Bot, event: Event):
    text = event.text.strip()
    if not text:
        return
    res = await song.get_song(text)
    if res:
        name = res["name"]
        artist = res["artist"]
        album = res["album"]
        img_url = res["img_url"]
        song_url = res["song_url"]
        await bot.send(f"即将为您播放歌曲 [{name}]\n\n专辑: {album}\n歌手: {artist}\n\n正在下载中，请稍后")
        try:
            # if img_url:
            #     async with httpx.AsyncClient() as client:
            #         img_bytes = await request_img(img_url, client)
            #         await bot.send(MessageSegment.image(img_bytes))

            async with httpx.AsyncClient() as client:
                response = await client.get(song_url)
                await bot.send(
                    MessageSegment.file(
                        content=response.content, file_name=f"{name}.mp3"
                    )
                )
        except Exception as e:
            logger.error(f"{type(e)}: 歌曲下载失败 {str(e)}")
            await bot.send("很抱歉，歌曲下载失败，请稍后重试。")
    else:
        await bot.send("对不起，由于版权原因，我并没有搜索到该歌曲。")
