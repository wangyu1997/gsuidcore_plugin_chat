import random
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from .utils import *
from .config import setreo_path


data = open(setreo_path, 'r').readlines()


setreo_sv = SV(
    'NEWBING',
    pm=6,
    priority=13,
    enabled=True,
    black_list=[],
    area='ALL'
)


@setreo_sv.on_prefix(('发病'), block=True)
async def _(bot: Bot, event: Event):
    target_str = event.text.strip()
    if not target_str:
        return
    msg = random.choice(data).format(target_name=target_str)
    msg = msg.replace('\\n', '\n').replace('\\t', '\t')
    await bot.send(msg)
