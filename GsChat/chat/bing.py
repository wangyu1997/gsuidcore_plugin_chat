import json
import re
import time

from EdgeGPT import Chatbot as bingChatbot

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from .base import BaseChat
from .build import CHAT


@CHAT.register_module()
class BingChat(BaseChat):
    def __init__(self, config=None):
        super(BingChat, self).__init__(config)
        self.style = self.config.style

    async def _create(self, user_id):
        current_time: int = int(time.time())
        chat_bot = bingChatbot(cookies=self._get_random_key())
        self.chat_dict[user_id] = {
            "chatbot": chat_bot, "last_time": current_time, "model": self.style, "isRunning": False}

    async def _ask(self, user_id, bot: Bot, event: Event):
        msg = event.text.strip()

        chatbot = self.chat_dict[user_id]["chatbot"]
        style: str = self.chat_dict[user_id]["model"]

        try:
            data = await chatbot.ask(prompt=msg, conversation_style=style)
        except Exception as e:
            self.chat_dict[user_id]["isRunning"] = False
            await bot.send(f'askError: {str(e)}多次askError请尝试"重置对话"', at_sender=True)
            return

        self.chat_dict[user_id]["isRunning"] = False
        if (
            data["item"]["result"]["value"] != "Success"
        ):
            await bot.send(
                "返回Error: " + data["item"]["result"]["value"] + "请重试", at_sender=True
            )
            del self.chat_dict[user_id]
            return

        throttling = data["item"]["throttling"]
        max_conversation = throttling["maxNumUserMessagesInConversation"]
        current_conversation = throttling["numUserMessagesInConversation"]
        if len(data["item"]["messages"]) < 2:
            await bot.send("该对话已中断, 可能是被bing掐了, 正帮你重新创建会话", at_sender=True)
            await self.create(user_id, bot, event)
            return

        if "text" not in data["item"]["messages"][1]:
            await bot.send(
                data["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"],
                at_sender=True
            )
            return

        rep_message = await self.bing_string_handle(
            data["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"]
        )

        if max_conversation <= current_conversation:
            await bot.send("达到对话上限, 正帮你重置会话", at_sender=True)
            try:
                await self.create(user_id, bot, event)
            except Exception:
                return None
        message = f"{rep_message}\n\n当前{current_conversation} 共 {max_conversation}"
        return message

    async def init_data(self):
        cookie_path = self.res_path / 'bing_cookies'
        cookie_path.mkdir(parents=True, exist_ok=True)
        cookies_files: list = [
            file for file in cookie_path.rglob("*.json") if file.stem.startswith("cookie")
        ]

        try:
            self.cookies = [
                json.load(open(file, "r", encoding="utf-8")) for file in cookies_files
            ]
            logger.info(f"bing_cookies读取, 初始化成功, 共{len(self.cookies)}个cookies")
        except Exception as e:
            logger.info(f"读取bing cookies失败 error信息: {str(e)}")

    async def bing_string_handle(self, input_string: str) -> str:
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

    async def switch_style(self, user_id, style):
        """
        开关风格
        :param style:
        :param user_id:
        :return:
        """
        print(self.chat_dict)
        if user_id in self.chat_dict:
            self.chat_dict[user_id]['model'] = style
            return True
        return False
