import re 

import time
from pathlib import Path

from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from .utils import *

regular_sv = SV(
    '普通聊天',
    pm=3,  
    priority=17,
    enabled=True,
    black_list=[],
    area='ALL'
)

chat_dict: dict = {}   


@regular_sv.on_fullmatch('重置chat', block=True,)
async def reserve_openai(bot:Bot, event:Event):
    new_chat(bot,event)
    await bot.send("chat会话已重置,最多维持5段对话")
    
    

# TODO at_me 功能
# @regular_sv.on_command(('tome'), block=True)
# async def at_test(bot:Bot, event:Event):
#     # new_chat(bot,event)
    
#     logger.info(event.at_list)
#     logger.info(event.at)

#     logger.info(event.text)
    
#     await space_handle(bot,event)
    
    
#     msg = re.sub(r"@.*? ", "", event.text)
#     logger.info(bot,event)


#     await bot.send("at test")



@regular_sv.on_prefix(('chat'), block=True,)
async def regular_reply(bot:Bot,event:Event):
  """普通回复"""
  if not reply_private and event.user_type == 'direct':
    return  
  uid = event.user_id
  msg = event.text
   
  # 去掉带中括号的内容(去除cq码)
  msg = re.sub(r"\[.*?\]", "", msg)
  if uid not in chat_dict:  
    new_chat(bot,event)
    await bot.send("chat新会话已创建,最多维持5段对话")
  
  if chat_dict[uid]["isRunning"]:  
    
      await bot.send("当前会话正在运行中, 请稍后再发起请求")
      return
  chat_dict[uid]["isRunning"] = True 
  chat_dict[uid]['session'] = chat_dict[uid]['session'][:5]
  session =  chat_dict[uid]['session']
  result = await get_chat_result(msg, session)
  chat_dict[uid]["sessions_number"]+=1 
  if result is None:
      data = f"抱歉，{bot_nickname}暂时不知道怎么回答你呢, 试试使用openai或者bing吧~"
  else:
    chat_dict[uid]['session'].append((msg,result))
    data = result
  chat_dict[uid]["isRunning"] = False 
  sessions_number = chat_dict[uid]["sessions_number"]  
  data += f"\n\n当前会话: {sessions_number}  字数异常请发送\"重置chat\"" 
  await bot.send(data)

    
# 空消息处理
# async def space_handle(bot:Bot,event:Event):
#     """戳一戳回复, 私聊会报错, 暂时摸不着头脑"""
#     probability = random.random()
#     # 33%概率回复莲宝的藏话
#     # if probability > 11:
#         # 发送语音需要配置ffmpeg, 这里try一下, 不行就随机回复poke__reply的内容
#         # try:
#     logger.info(Path(audio_path) / random.choice(audio_list))
#     await bot.send(Path(audio_path) / random.choice(audio_list))
#     #     except Exception:
#     #         await matcher.send(await utils.rand_poke())
#     # elif probability > 0.66:
#     #     # 33% 概率戳回去
#     #     await matcher.send(Message(f"[CQ:poke,qq={event.user_id}]"))
#     # # probability在0.33和0.66之间的概率回复poke__reply的内容
#     # else:
#     #     await matcher.send(await utils.rand_poke())

    
def new_chat(_:Bot,event: Event) -> None:
    current_time = int(time.time())  
    user_id: str = str(event.user_id)
    chat_dict[user_id] = {"session": [], "last_time": current_time, "sessions_number":0, "isRunning": False}


