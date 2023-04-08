import re

import time

from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from .utils import *

regular_sv = SV(
    '普通聊天',
    pm=6,
    priority=22,
    enabled=True,
    black_list=[],
    area='ALL'
)


at_sv = SV(
    'at聊天',
    pm=6,
    priority=2000,
    enabled=True,
    black_list=[],
    area='ALL'
)

chat_dict: dict = {}
key = config.normal_chat_key


@regular_sv.on_fullmatch('重置chat', block=True,)
async def reserve_chat(bot: Bot, event: Event):
    new_chat(bot, event)
    await bot.send("chat会话已重置", at_sender=True)


# TODO at_me 功能
@at_sv.on_command('', block=True, to_me=True)
async def at_test(bot: Bot, event: Event):

    msg = event.text.strip()

    if event.bot_id == 'ntchat':
        # 粗暴
        if ' ' not in msg and "@" in msg:
            msg = ''
        else:
            msg = re.sub(r"@.*? ", "", msg)

    if (
        (not msg)
        or msg.isspace()
    ):
        await bot.send(await rand_poke(), at_sender=True)
        return
    if msg in nonsense:
        await bot.send(await rand_hello(), at_sender=True)
        return

    await regular_reply(bot, event)


@regular_sv.on_prefix(('chat'), block=True,)
async def _(bot: Bot, event: Event):
    await regular_reply(bot, event)


async def regular_reply(bot: Bot, event: Event):
    """普通回复"""

    if not key:
        await bot.send('请配置key之后再来和我聊天哦.', at_sender=True)
        return

    uid = event.user_id
    msg = event.text

    if uid not in chat_dict:
        new_chat(bot, event)
        await bot.send("chat新会话已创建", at_sender=True)

    if chat_dict[uid]["isRunning"]:
        await bot.send("当前会话正在运行中, 请稍后再发起请求", at_sender=True)
        return
    chat_dict[uid]["isRunning"] = True
    session = chat_dict[uid]['session']
    result = await get_chat_result(msg, session)
    chat_dict[uid]["sessions_number"] += 1
    if result is None:
        data = f"抱歉，{bot_nickname}暂时不知道怎么回答你呢, 试试使用openai或者bing吧~"
        await reserve_chat(bot, event)
    else:
        chat_dict[uid]['session'].append((msg, result))
        data = result
        if '作为一个' in data or '很抱歉' in data:
            data += f"\n\n您也可以尝试使用[bing xx]指令从NewBing查询更多实时的信息哦。"
    chat_dict[uid]["isRunning"] = False
    sessions_number = chat_dict[uid]["sessions_number"]
    data += f"\n\n当前会话: {sessions_number}  字数异常请发送\"重置chat\""
    await bot.send(data, at_sender=True)


def new_chat(_: Bot, event: Event) -> None:
    current_time = int(time.time())
    user_id: str = str(event.user_id)
    chat_dict[user_id] = {"session": [], "last_time": current_time,
                          "sessions_number": 0, "isRunning": False}
