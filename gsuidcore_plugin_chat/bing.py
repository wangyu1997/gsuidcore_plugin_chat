import re
import time
from EdgeGPT import Chatbot as bingChatbot
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event
from gsuid_core.logger import logger
from revChatGPT.V3 import Chatbot


from .utils import *
from .config import config

bing = SV(
    'NEWBING',
    pm=6, 
    priority=14,
    enabled=True,
    black_list=[],
    area='ALL'
)


bing_chat_dict: dict= {}       
bing_cookies_files = []
bing_cookies_files: list = [
    file
    for file in config.smart_reply_path.rglob("*.json")
    if file.stem.startswith("cookie")
]

try:
    bing_cookies: list = [
        json.load(open(file, "r", encoding="utf-8")) for file in bing_cookies_files
    ]
    logger.info(f"bing_cookies读取, 初始化成功, 共{len(bing_cookies)}个cookies")
except Exception as e:
    logger.info(f"读取bing cookies失败 error信息: {str(e)}")
    bing_cookies: list = []


cookie_allow = bool(bing_cookies)

@bing.on_fullmatch('重置bing', block=True,)
async def reserve_bing(bot: Bot, event: Event) -> None:    
    style = config.newbing_style
    await newbing_new_chat(bot, event=event, style=style)
    await bot.send(f"newbing会话已重置, 当前对话模式为[{style}].")

@bing.on_prefix('切换bing', block=True,)
async def reserve_bing(bot: Bot, event: Event) -> None:
    text = event.text.strip()
    
    style = config.newbing_style
    
    if text == '准确':
        style = 'precise'
    elif text == "平衡":
        style = 'balanced'
    else:
        style = "creative"
        
    await newbing_new_chat(bot, event=event, style=style)
    await bot.send(f"newbing会话已重置, 当前对话模式为[{style}].")


async def pretreatment(bot:Bot, event:Event):  
    uid = event.user_id  
      
    if not cookie_allow:
        await bot.send("cookie未设置, 无法访问")
        return
    
    if uid not in bing_chat_dict:
        await newbing_new_chat(bot, event)
        await bot.send("newbing新会话已创建")
        return
      
    if bing_chat_dict[uid]["isRunning"]:
        await bot.send("当前会话正在运行中, 请稍后再发起请求")
        return
    bing_chat_dict[uid]["isRunning"] = True

@bing.on_prefix('bing', block=True,)   
async def bing_handle(bot:Bot, event:Event): 
    uid = event.user_id  
    msg = event.text.strip() 
    
    if not reply_private and event.user_type == 'direct':
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
  
    await pretreatment(bot=bot, event=event)     

    chatbot: Chatbot = bing_chat_dict[uid]["chatbot"]  
    style: str = bing_chat_dict[uid]["model"] 
    try:  
        data = await chatbot.ask(prompt=msg, conversation_style=style)
    except Exception as e: 
        bing_chat_dict[uid]["isRunning"] = False
        await bot.send(f'askError: {str(e)}多次askError请尝试"重置bing"')
        return
      
    bing_chat_dict[uid]["isRunning"] = False  # 将当前会话状态设置为未运行
    if (
        data["item"]["result"]["value"] != "Success"
    ):  # 如果返回的结果不是Success, 则返回错误信息, 并且删除当前会话
        await bot.send(
            "返回Error: " + data["item"]["result"]["value"] + "请重试"
        )
        del bing_chat_dict[uid]
        return

    throttling = data["item"]["throttling"]  # 获取当前会话的限制信息
    # 获取当前会话的最大对话数
    max_conversation = throttling["maxNumUserMessagesInConversation"]
    # 获取当前会话的当前对话数
    current_conversation = throttling["numUserMessagesInConversation"]
    if len(data["item"]["messages"]) < 2:  # 如果返回的消息数量小于2, 则说明会话已经中断, 则删除当前会话
        await bot.send("该对话已中断, 可能是被bing掐了, 正帮你重新创建会话")
        await newbing_new_chat(bot,event)
        return
    # 如果返回的消息中没有text, 则说明提问了敏感问题, 则删除当前会话
    if "text" not in data["item"]["messages"][1]:
        await bot.send(
            data["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"],
            
        )
        return
    rep_message = await bing_string_handle(
        data["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"]
    )  # 获取bing的回复, 并且稍微处理一下
    try:  # 尝试发送回复
        await bot.send(
            f"{rep_message}\n\n当前{current_conversation} 共 {max_conversation}",
            
        )
        if max_conversation <= current_conversation:
            await bot.send("达到对话上限, 正帮你重置会话")
            try:
                await newbing_new_chat(bot,event)
            except Exception:
                return
    except Exception as e:  # 如果发送失败, 则尝试把文字写在图片上发送
        try:
            await bot.send(f"文本消息被风控了,错误信息:{str(e)}, 这里咱尝试把文字写在图片上发送了")
            await bot.send(await txt_to_img(data))
        except Exception as eeee:  # 如果还是失败, 我也没辙了, 只能返回异常信息了
            await bot.send(f"消息全被风控了, 这是捕获的异常: \n{str(eeee)}")


async def newbing_new_chat(bot:Bot,event: Event, style=config.newbing_style) -> None:
    current_time: int = int(time.time())
    user_id: str = str(event.user_id)
    if user_id in bing_chat_dict:
        last_time: int = bing_chat_dict[user_id]["last_time"]
        if (current_time - last_time < config.newbing_cd_time) and (
            event.user_id not in config.superusers
        ):  # 如果当前时间减去上一次时间小于CD时间, 直接返回
            await bot.send(
                f"非报错情况下每个会话需要{config.newbing_cd_time}秒才能新建哦, 当前还需要{config.newbing_cd_time - (current_time - last_time)}秒"
            )
            return 
          
    bot = bingChatbot(cookies=random.choice(bing_cookies))  # 随机选择一个cookies创建一个Chatbot
    bing_chat_dict[user_id] = {"chatbot": bot, "last_time": current_time, "model": style, "isRunning": False}



async def bing_string_handle(input_string: str) -> str:
    """处理一下bing返回的字符串"""
    input_string = re.sub(r"\[\^(\d+)\^\]", "", input_string)
    regex = r"\[\d+\]:"
    matches = re.findall(regex, input_string)
    if not matches:
        return input_string
    positions = [
        (match.start(), match.end()) for match in re.finditer(regex, input_string)
    ]
    end = input_string.find("\n", positions[-1][1])
    target = input_string[end:] + "\n\n" + input_string[:end]
    while target[0] == "\n":
        target = target[1:]
    return target
