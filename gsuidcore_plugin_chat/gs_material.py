import random
import asyncio
from gsuid_core.gss import gss
from .material import MATERIAL
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from gsuid_core.logger import logger
from gsuid_core.segment import MessageSegment
from gsuid_core.aps import scheduler
from .config import config

material_sv = SV(
    '原神材料',
    pm=6,
    priority=10,
    enabled=True,
    black_list=[],
    area='ALL'
)


material_admin = SV(
    '原神材料管理',
    pm=1,
    priority=14,
    enabled=True,
    black_list=[],
    area='ALL'
)

material_model = MATERIAL.build(config.genshin.material)
hour, minute = config.genshin.material.push_time.split(':')

@material_sv.on_prefix(('计算', '原神计算'), block=True)
async def _(bot: Bot, event: Event):
    text = event.text.strip()
    msg = await material_model.generate_calc_msg(text, bot, event)
    if msg:
        await bot.send(
            MessageSegment.text(msg) if isinstance(
                msg, str) else MessageSegment.image(msg)
        )



@material_sv.on_command('材料', block=True)
async def material_full(bot: Bot, event: Event):
    name = event.text.strip()

    msg = await material_model.material_push(name=name)
    if msg:
        await bot.send(
            MessageSegment.text(msg) if isinstance(
                msg, str) else MessageSegment.image(msg)
        )
        

@material_sv.on_command('周本', block=True)
async def week_full(bot: Bot, event: Event):
    name = event.text.strip()
    msg = await material_model.week_push(name=name)
    if msg:
        await bot.send(
            MessageSegment.text(msg) if isinstance(
                msg, str) else MessageSegment.image(msg)
        )


@material_admin.on_keyword('订阅材料', block=True)
async def material_sub(bot: Bot, event: Event):
    bot_id = bot.bot_id
    msg = await material_model.subscribe(bot_id, event)
    await bot.send(msg)


@material_admin.on_fullmatch('推送材料提醒', block=True)
async def push_material(bot: Bot, event: Event):
    await daily_push()

@scheduler.scheduled_job('cron', hour=hour, minute=minute)
async def cron_material():
    await daily_push()


async def daily_push():
    msg, cfg = await material_model.daily_push()
    message = MessageSegment.text(msg) if isinstance(
                msg, str) else MessageSegment.image(msg)
    
    group_sub_list = cfg.get("群组", [])
    private_sub_list = cfg.get("私聊", [])
    for bot_id in group_sub_list:
        try:
            for BOT_ID in gss.active_bot:
                bot = gss.active_bot[BOT_ID]
                for group_id in group_sub_list[bot_id]:
                    await bot.target_send(
                        message, 'group', group_id, bot_id, '', ''
                    )
                    await asyncio.sleep(random.uniform(1, 3))
        except Exception as e:
            logger.exception(e)

    for bot_id in private_sub_list:
        try:
            for BOT_ID in gss.active_bot:
                bot = gss.active_bot[BOT_ID]
                for user_id in private_sub_list[bot_id]:
                    await bot.target_send(
                        message, 'direct', user_id, bot_id, '', ''
                    )
                    await asyncio.sleep(random.uniform(1, 3))
        except Exception as e:
            logger.exception(e)