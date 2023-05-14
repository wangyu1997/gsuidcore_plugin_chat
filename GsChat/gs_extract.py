import re
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import Message
from .extract import EXTRACT, BiliBiliExtract
from httpx import AsyncClient
from .config import config
from .utils import send_img

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
async def add_notice(bot: Bot, event: Event):
    text = str(event.text).strip()

    async with AsyncClient(timeout=None) as client:
        try:
            if re.search(r"(b23.tv)|(bili(22|23|33|2233).cn)", text, re.I):
                # 提前处理短链接，避免解析到其他的
                text = await bili.b23_extract(text, client)

            group_id = event.group_id if event.user_type != 'direct' else None
            msg = await bili.bili_keyword(group_id, text, client)
            if msg:
                if isinstance(msg, str):
                    # 说明是错误信息
                    await bot.send(msg)
                else:
                    await _send_msg(msg, bot)

        except Exception as e:
            logger.info(f"{type(e)}: {str(e)}")


async def _send_msg(msg, bot) -> None:
    try:
        await bot.send("\n".join(msg[1:]))
        await send_img(msg[0], bot)
    except Exception as e:
        logger.info(f"{type(e)}: {str(e)}")
