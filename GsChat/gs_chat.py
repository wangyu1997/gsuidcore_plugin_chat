from .chat import BaseChat, CHATENGINE
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from .utils import rand_poke, rand_hello, nonsense
from .config import config

chat_sv = SV(
    '聊天',
    pm=6,
    priority=10,
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

# admin 一键切换所有模式 查看模式和engine
chat_engine = CHATENGINE.build(config.chat)

@chat_sv.on_prefix(('bing','chat','openai','Bing','Chat','Openai'), block=True,)
async def chat_handle(bot: Bot, event: Event):
  bot_name = event.command
  new_engine_name = chat_engine.get_engine(bot_name=bot_name)
  await handle_msg(bot, event, new_engine_name)
  
  
@at_sv.on_command('', block=True, to_me=True)
async def at_test(bot: Bot, event: Event):
    await handle_msg(bot, event)
  

@chat_sv.on_prefix(('切换引擎','ce'), block=True,)
async def change_engine(bot: Bot, event: Event):
  bot_name = event.text.strip().lower()
  
  if bot_name not in ['bing','chat','openai']:
    bot.send(f"暂时不支持引擎 [{bot_name}] ")
  
  new_engine_name = chat_engine.get_engine(bot_name=bot_name)
  _, group, _  = chat_engine.get_bot_info(event)
  chat_engine.change_engine(event, new_engine_name)
  
  await bot.send(f'已切换当前[{"群聊" if group else "私聊"}] 引擎为: [{new_engine_name}]')

@chat_sv.on_fullmatch(('切换模式','cm'), block=True,)
async def mode_handle(bot: Bot, event: Event):
  chat_type = event.user_type
  is_private = bool(chat_type == 'direct')

  # 不支持私聊
  if is_private:
    await bot.send(f'私人聊天无法切换模式哦, 在群组中使用该命令。')
    return
    
  _,_, engine = chat_engine.get_bot_info(event)
  group = chat_engine.change_mode(event.group_id)
  _,_, engine = chat_engine.get_bot_info(event)

  await bot.send(f'切换成功\n当前模式为: [{"群聊" if group else "私人"}模式]\n当前引擎为: [{engine}]')


@chat_sv.on_fullmatch(('重置对话','reset'), block=True,)
async def reserve_handle(bot: Bot, event: Event):
    user_id, group, engine_name = chat_engine.get_bot_info(event)
    chatbot:BaseChat = await chat_engine.get_singleton_bot(engine_name)
    if await chatbot.reset(user_id, bot, event):
      await bot.send(f'已重置当前[{"群聊" if group else "私聊"}] 引擎为: [{engine_name}]')
      
      
@chat_sv.on_fullmatch('查看引擎', block=True)
async def _(bot: Bot, event: Event):
  _,group, engine_name = chat_engine.get_bot_info(event)
  await bot.send(f'当前[{"群聊" if group else "私聊"}] 引擎为: [{engine_name}]')


async def handle_msg(bot:Bot, event: Event, engine_name: str = None):
  msg = event.text.strip()
  
  if event.bot_id == 'ntchat':
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
    
  user_id, _, engine  = chat_engine.get_bot_info(event)
  
  if not engine_name:
    engine_name = engine
    
  chat_bot:BaseChat = await chat_engine.get_singleton_bot(engine_name)
    
  await chat_bot.ask(user_id, bot, event)
  


# @bing.on_prefix('切换bing', block=True,)
# async def reserve_bing(bot: Bot, event: Event) -> None:
#     text = event.text.strip()

#     style = config.newbing_style

#     if text == '准确':
#         style = 'precise'
#     elif text == "平衡":
#         style = 'balanced'
#     else:
#         style = "creative"

#     await newbing_new_chat(bot, event=event, style=style)
#     await bot.send(f"newbing会话已重置, 当前对话模式为[{style}].", at_sender=True)

