import asyncio

import time

from revChatGPT.V3 import Chatbot as openaiChatbot

from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from revChatGPT.V3 import Chatbot
from gsuid_core.logger import logger

from .utils import *

openai_chat_dict: dict = {}   
openai_api_key: list = config.openai_api_key
openai_max_tokens: int = config.openai_max_tokens
apikey_allow = bool(openai_api_key)

if config.bing_or_openai_proxy:
    os.environ["all_proxy"] = config.bing_or_openai_proxy
    logger.info(f"已设置代理, 值为:{config.bing_or_openai_proxy}")
else:
    logger.warning("未检测到代理，国内用户可能无法使用bing或openai功能")


openai = SV(
    'OPENAI',
    pm=6, 
    priority=13,
    enabled=True,
    black_list=[],
    area='ALL'
)

@openai.on_fullmatch('重置openai', block=True,)
async def reserve_openai(bot:Bot, event:Event):
    await openai_new_chat(bot,event)
    await bot.send("openai会话已重置")


@openai.on_prefix('openai', block=True,)
async def openai_handle(bot:Bot, event:Event):
    if not reply_private and event.user_type == 'direct':
        return          
    
    uid = event.user_id
    msg = event.text.strip()

    if not apikey_allow:
        await bot.send("openai_api_key未设置, 无法访问")
        return

    if (
      (not msg)
      or msg.isspace()
    ):
      await bot.send(await rand_poke())
      return
    if msg in nonsense:
      await bot.send(await rand_hello())
      return
        
    if uid not in openai_chat_dict: 
        await openai_new_chat(bot,event)
        await bot.send("openai新会话已创建")

    if openai_chat_dict[uid]["isRunning"]:  
        await bot.send("当前会话正在运行中, 请稍后再发起请求")
        return
    openai_chat_dict[uid]["isRunning"] = True  
    chatbot: Chatbot = openai_chat_dict[uid]["chatbot"]  
    try:
        loop = asyncio.get_event_loop()     # 调用ask会阻塞asyncio
        data = await loop.run_in_executor(None, chatbot.ask, msg)
        openai_chat_dict[uid]["sessions_number"]+=1 
    except Exception as e: 
        openai_chat_dict[uid]["isRunning"] = False
        await bot.send( f'askError: {str(e)}多次askError请尝试发送"重置openai"')
        return
    openai_chat_dict[uid]["isRunning"] = False  # 将当前会话状态设置为未运行
    sessions_number = openai_chat_dict[uid]["sessions_number"]  # 获取当前会话的会话数
    data += f"\n\n当前会话: {sessions_number}   字数异常请发送\"重置openai\"" 
    try:
        await bot.send(data)
    except Exception as e:
        try:
            await bot.send(f"文本消息被风控了,错误信息:{str(e)}, 这里咱尝试把文字写在图片上发送了")
            await bot.send(await txt_to_img(data))
        except Exception as eeee:
            await bot.send(f"消息全被风控了, 这是捕获的异常: \n{str(eeee)}")


async def openai_new_chat(bot:Bot,event: Event) -> None:
    current_time = int(time.time())  
    user_id: str = str(event.user_id)
    if user_id in openai_chat_dict:
        last_time = openai_chat_dict[user_id]["last_time"]
        if (current_time - last_time < config.openai_cd_time) and (
            event.user_id not in config.superusers
        ): 
            await bot.send(
                f"非报错情况下每个会话需要{config.openai_cd_time}秒才能新建哦, 当前还需要{config.openai_cd_time - (current_time - last_time)}秒"
            )
            return
    bot = openaiChatbot(
        api_key=random.choice(openai_api_key),
        max_tokens=openai_max_tokens,
    ) 
    openai_chat_dict[user_id] = {"chatbot": bot, "last_time": current_time, "sessions_number":0, "isRunning": False}

