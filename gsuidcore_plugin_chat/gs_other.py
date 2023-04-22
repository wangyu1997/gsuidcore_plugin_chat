from .others import OTHER
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from .config import config


other_sv = SV(
    '其他相关',
    pm=6,  
    priority=1400,
    enabled=True,
    black_list=[],
    area='ALL'
)


browser = OTHER.build(config.other.browser)
setereo = OTHER.build(config.other.setereo)


@other_sv.on_prefix(('网页截图','截图'), block=True,)
async def reserve_openai(bot:Bot, event:Event):
    text = event.text.strip()
    if not text:
        return 
    await bot.send(await browser.screenshot(text))
   
   
@other_sv.on_prefix(('发病'), block=True,)
async def reserve_openai(bot:Bot, event:Event):
    text = event.text.strip()
    if not text:
        return
    await bot.send(await setereo.get_setereo(text))
    
   
   