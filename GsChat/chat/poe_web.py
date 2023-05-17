import time
import asyncio
from functools import partial

from poe import Client
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger

from .build import CHAT
from .base import BaseChat
from ..utils import to_async, map_str_to_unique_string


@CHAT.register_module()
class POEChat(BaseChat):
    def __init__(self, config=None):
        super(POEChat, self).__init__(config)
        self.proxy = None
        self.chatbot = None
        self.model = config.model
        self.default_bots = [
            "capybara",
            "a2",
            "chinchilla",
            "hutia",
            "nutria",
        ]

    async def get_new_bot(self, user_id=None):
        api_key = self._get_random_key()
        chat_bot = await to_async(
            Client, token=api_key, proxy=self.proxy
        )
        self.chatbot = chat_bot
        # 在获取新的bot的时候，如果是自定义的bot，则创建
        if user_id and user_id in self.chat_dict:
            if (
                self.chat_dict[user_id]["model"]
                not in self.default_bots
            ):
                await self.create_user_bot(user_id)

    async def _create(self, user_id):
        current_time = int(time.time())
        if not self.chatbot:
            await self.get_new_bot(user_id)

        if user_id in self.chat_dict:
            model = self.chat_dict[user_id]["model"]
            # 忽略公告bot的清除
            if model not in self.default_bots:
                await to_async(
                    self.chatbot.send_chat_break, chatbot=model
                )

        self.chat_dict[user_id] = {
            "last_time": current_time,
            "model": self.model,
            "sessions_number": 0,
            "isRunning": False,
        }

    def non_stream_ask(self, user_id, msg):
        chatbot = self.chatbot
        model = self.chat_dict[user_id]["model"]
        chunk = None
        for chunk in chatbot.send_message(model, msg):
            pass
        return chunk["text"]

    async def _ask(self, user_id, bot: Bot, event: Event):
        msg = event.text.strip()
        try:
            loop = asyncio.get_event_loop()
            partial_func = partial(self.non_stream_ask, user_id, msg)
            data = await loop.run_in_executor(None, partial_func)
            self.chat_dict[user_id]["sessions_number"] += 1
        except Exception as e:
            self.chat_dict[user_id]["isRunning"] = False
            await self.get_new_bot(user_id)
            await bot.send(
                f'askError: {str(e)}多次askError 对话已自动重置"', at_sender=True
            )
            return
        self.chat_dict[user_id]["isRunning"] = False  # 将当前会话状态设置为未运行
        sessions_number = self.chat_dict[user_id]["sessions_number"]
        data += f'\n\n当前会话: {sessions_number}   字数异常请发送"重置对话"'

        return data

    async def init_data(self):
        config = self.config
        if config.proxy:
            self.proxy = config.proxy
            logger.info(f"POE已设置代理, 值为:{config.proxy}")
        else:
            logger.warning("未检测到代理，国内用户可能无法使用poe功能")
        self.keys = config.api_keys

    async def switch_style(self, user_id, style, bot, event):
        """
        开关风格
        :param style:
        :param user_id:
        :return:
        """
        try:
            if user_id not in self.chat_dict:
                res = await self.create(user_id, bot, event)
                if res:
                    if self.config.show_create:
                        await bot.send(f"{self.config.name} 对话已创建")
                else:
                    return
            if style == "custom":
                bot_id = await self.create_user_bot(user_id)
                style = "a2"
                self.chat_dict[user_id]["model"] = bot_id
            else:
                self.chat_dict[user_id]["model"] = style
            return True, style
        except Exception as e:
            await self.get_new_bot(user_id)
            return False, f"创建Poe对话失败, {str(e)}"

    async def create_user_bot(self, user_id):
        bot_id = str(user_id)
        bot_id = map_str_to_unique_string(bot_id)
        bot_id = str(user_id)[:5] + bot_id[5:]
        if bot_id not in self.chatbot.bot_names:
            await to_async(
                self.chatbot.create_bot,
                handle=bot_id,
                prompt="",
                base_model="a2",
            )
        return bot_id
