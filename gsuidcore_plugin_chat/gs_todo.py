import copy
from .chat import CHAT, NormalChat
from .others import OTHER, Browser
from .todo import TODO, ToDoModel
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from gsuid_core.logger import logger
from .config import config
from yacs.config import CfgNode
from gsuid_core.aps import scheduler

todo_sv = SV(
    '提醒事项',
    pm=6,
    priority=9,
    enabled=True,
    black_list=[],
    area='ALL'
)


normal_cfg: CfgNode = copy.deepcopy(config.chat.Normal)
normal_cfg.defrost()
normal_cfg.person = ''
normal_cfg.freeze()
chatbot: NormalChat = CHAT.build(config.chat.Normal)

todo_model: ToDoModel = TODO.build(config.other.todo)
todo_model.set_chatgpt(chatbot.normal_chat)

@todo_sv.on_prefix(('提醒', '提醒我'), block=True,)
async def add_notice(bot: Bot, event: Event):
    await todo_model.add_todo(bot, event)


@todo_sv.on_prefix(('删除提醒', '完成提醒'), block=True,)
async def finish_notice(bot: Bot, event: Event):
    await todo_model.remove_todo(bot, event)


@todo_sv.on_fullmatch(('查看提醒'), block=True,)
async def change_notice(bot: Bot, event: Event):
    todo_model.check_all()
    await todo_model.send_pic(bot, event)


@todo_sv.on_fullmatch(('推送测试'), block=True,)
async def change_notice(bot: Bot, event: Event):
    todo_model.check_all()
    await todo_model.send_todo()


@scheduler.scheduled_job('cron', minute='*/10')
async def cron_job():
    todo_model.check_all()
    await todo_model.send_todo()
