import copy
import time
import random
from abc import ABCMeta, abstractmethod

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger
from gsuid_core.data_store import get_res_path

from ..utils import txt_to_img


class BaseChat(metaclass=ABCMeta):
    def __init__(self, config=None):
        super(BaseChat, self).__init__()
        self.config = copy.deepcopy(config)
        self.chat_dict = {}
        self.cookies = []
        self.keys = []
        self.show = self.config.show_create
        self.cd_time = config.cd_time
        self.res_path = get_res_path("GsChat")

    async def reset(self, user_id, bot: Bot, event: Event):
        """重置bot"""
        # 返回False则等待cd
        if not self._check_valid():
            await bot.send("请先配置Cookie或API-Key再尝试使用.")

        if not await self.wait_cd(user_id, bot, event):
            return

        return await self.create(user_id, bot, event)

    async def create(self, user_id, bot: Bot, event: Event) -> bool:
        """创建新的bot"""
        if not self._check_valid():
            await bot.send("请先配置Cookie或API-Key再尝试使用.")
            return False

        try:
            await self._create(user_id)
            return True
        except Exception as e:
            logger.info(f"{type(e)}: create bot fail {e}")
            return False

    async def ask(self, user_id, bot: Bot, event: Event):
        if not self._check_valid():
            await bot.send("请先配置Cookie或API-Key再尝试使用.")

        if user_id not in self.chat_dict:
            res = await self.create(user_id, bot, event)
            if res:
                if self.show:
                    await bot.send(f"{self.config.name} 对话已创建")
            else:
                return

        if (
            user_id in self.chat_dict
            and self.chat_dict[user_id]["isRunning"]
        ):
            await bot.send("我正在努力回答您的问题，请再稍等一下下...", at_sender=True)
            return

        self.chat_dict[user_id]["isRunning"] = True

        message = await self._ask(user_id, bot, event)

        if not message:
            return

        message = message.strip()
        try:
            await bot.send(message, at_sender=True)
        except Exception as e:
            try:
                await bot.send(
                    f"文本消息被风控了,错误信息:{str(e)}, 这里咱尝试把文字写在图片上发送了",
                    at_sender=True,
                )
                await bot.send(
                    await txt_to_img(message), at_sender=True
                )
            except Exception as ex:
                await bot.send(
                    f"消息全被风控了, 这是捕获的异常: \n{str(ex)}", at_sender=True
                )

    @abstractmethod
    async def _create(self, user_id):
        pass

    @abstractmethod
    async def _ask(self, user_id, bot: Bot, event: Event):
        pass

    @abstractmethod
    def init_data(self):
        """初始化cookie或者key"""
        pass

    @abstractmethod
    def get_style(self, user_id):
        """初始化cookie或者key"""
        pass

    async def wait_cd(self, user_id, bot: Bot, event: Event):
        current_time = int(time.time())
        is_super = event.user_pm == 1

        if user_id in self.chat_dict:
            last_time: int = self.chat_dict[user_id]["last_time"]
            if (current_time - last_time < self.cd_time) and (
                not is_super
            ):
                await bot.send(
                    f"非报错情况下每个会话需要{self.cd_time}秒才能新建哦, 当前还需要{self.cd_time - (current_time - last_time)}秒",
                    at_sender=True,
                )
                return False

        return True

    def _get_random_key(self):
        return random.choice(
            self.cookies if self.cookies else self.keys
        )

    # 检查cookie或key的函数
    def _check_valid(self):
        return self.cookies or self.keys
