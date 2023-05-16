import asyncio
import time
from functools import partial

from poe import Client

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from .base import BaseChat
from .build import CHAT


@CHAT.register_module()
class POEChat(BaseChat):
    def __init__(self, config=None):
        super(POEChat, self).__init__(config)
        self.proxy = ""
        self.chatbot = None
        self.model = config.model

    async def get_new_bot(self):
        api_key = self._get_random_key()
        chat_bot = Client(api_key)
        self.chatbot = chat_bot

    async def _create(self, user_id):
        current_time = int(time.time())
        if not self.chatbot:
            await self.get_new_bot()
        self.chat_dict[user_id] = {
            "last_time": current_time,
            "model": self.model,
            "sessions_number": 0,
            "isRunning": False}

    def non_stream_ask(self, user_id, msg):
        chatbot = self.chatbot
        model = self.chat_dict[user_id]["model"]
        chunk = None
        for chunk in chatbot.send_message(model, msg):
            pass
        return chunk['text']

    async def _ask(self, user_id, bot: Bot, event: Event):
        msg = event.text.strip()
        try:
            loop = asyncio.get_event_loop()
            partial_func = partial(self.non_stream_ask, user_id, msg)
            data = await loop.run_in_executor(None, partial_func)
            self.chat_dict[user_id]["sessions_number"] += 1
        except Exception as e:
            self.chat_dict[user_id]["isRunning"] = False
            await self.get_new_bot()
            await bot.send(f'askError: {str(e)}多次askError 对话已自动重置"', at_sender=True)
            return
        self.chat_dict[user_id]["isRunning"] = False  # 将当前会话状态设置为未运行
        sessions_number = self.chat_dict[user_id]["sessions_number"]
        data += f"\n\n当前会话: {sessions_number}   字数异常请发送\"重置对话\""

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
        if user_id not in self.chat_dict:
            res = await self.create(user_id, bot, event)
            if res:
                if self.config.show_create:
                    await bot.send(f'{self.config.name} 对话已创建')
            else:
                return
        self.chat_dict[user_id]['model'] = style
