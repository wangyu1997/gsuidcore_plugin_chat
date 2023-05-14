import copy
from .chat import CHAT, NormalChat
from .image import IMAGEENGINE
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from gsuid_core.logger import logger
from .config import config
from yacs.config import CfgNode

image_sv = SV('图像搜索', pm=6, priority=10, enabled=True, black_list=[], area='ALL')


normal_cfg: CfgNode = copy.deepcopy(config.chat.Normal)
normal_cfg.defrost()
normal_cfg.person = ''
normal_cfg.freeze()
chatbot: NormalChat = CHAT.build(config.chat.Normal)

image_engine = IMAGEENGINE.build(config.image)

if chatbot._check_valid():
    logger.info(f'成功加载normal chat')
    align_prompt = image_engine.get_prompt()
    align_fn = lambda query, keywords: chatbot.normal_chat(
        align_prompt.replace('<QUERY>', query) + keywords
    )
else:
    del chatbot
    logger.info(f'加载normal chat失败')
    align_fn = lambda _, keywords: keywords


@image_sv.on_prefix('搜图', block=True)
async def _(bot: Bot, event: Event):
    keywords = event.text.strip()
    cur_engine = image_engine.current_engine
    if not keywords:
        return
    await bot.send(f'正在搜索关于[{keywords}]的图片, Engine: [{cur_engine}]...')
    imagebot = image_engine.get_singleton_bot(cur_engine)
    await imagebot.search(align_fn, bot, event)


@image_sv.on_prefix('转搜图', block=True)
async def _(bot: Bot, event: Event):
    keywords = event.text.strip()
    cur_engine = image_engine.current_engine
    if not keywords:
        return
    await bot.send(f'正在搜索关于[{keywords}]的图片, Engine: [{cur_engine}]...')
    imagebot = image_engine.get_singleton_bot(cur_engine)
    await imagebot.search(align_fn, bot, event, True)


@image_sv.on_prefix('切换搜图', block=True)
async def _(bot: Bot, event: Event):
    bot_name = event.text.strip().lower()

    if bot_name not in ['filckr', 'websearch']:
        bot.send(f"暂时不支持引擎 [{bot_name}] ")

    engine = image_engine.get_engine(bot_name)
    image_engine.change_engine(engine)
    await bot.send(f'已切换默认搜图引擎为: [{engine}]')


@image_sv.on_prefix('画图', block=True)
async def _(bot: Bot, event: Event):
    engine = image_engine.get_engine("bingai")
    imagebot = image_engine.get_singleton_bot(engine)
    await imagebot.search(align_fn, bot, event)


@image_sv.on_prefix('转画图', block=True)
async def _(bot: Bot, event: Event):
    engine = image_engine.get_engine("bingai")
    imagebot = image_engine.get_singleton_bot(engine)
    await imagebot.search(align_fn, bot, event, True)


@image_sv.on_fullmatch('查看搜图', block=True)
async def _(bot: Bot, _: Event):
    engine = image_engine.current_engine
    await bot.send(f'当前搜图引擎为: [{engine}]')
