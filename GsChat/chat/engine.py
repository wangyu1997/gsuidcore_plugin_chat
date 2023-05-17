import copy

from yacs.config import CfgNode
from gsuid_core.models import Event

from .build import CHAT, CHATENGINE


@CHATENGINE.register_module()
class ChatEngine:
    def __init__(self, config: CfgNode = None):
        self.name_map = {
            "bing": "Bing",
            "chat": "Normal",
            "openai": "Openai",
            "poe": "Poe",
        }  # nickname->engine name
        self.bots = {}  # 维护不同engine对应的bot singleton
        self.bot_user_map = {}
        self.default_engine = self.name_map[config.default]
        self.config = copy.deepcopy(config)

    def get_bot_info(self, event: Event):
        chat_type = event.user_type
        is_private = bool(chat_type == "direct")
        group_chat = True

        # 处理非私聊的情况
        if not is_private:
            group_id = event.group_id
            if group_id not in self.bot_user_map:
                self.bot_user_map[group_id] = {
                    "group": self.config.group,
                    "engine": self.default_engine,
                }
            group_chat = self.bot_user_map[group_id]["group"]
            if group_chat:
                return (
                    group_id,
                    True,
                    self.bot_user_map[group_id]["engine"],
                )

        if is_private or (not group_chat):
            user_id = event.user_id
            if user_id not in self.bot_user_map:
                self.bot_user_map[user_id] = {
                    "group": False,
                    "engine": self.default_engine,
                }
            return user_id, False, self.bot_user_map[user_id]["engine"]

    def change_engine(self, event: Event, new_engine: str):
        chat_type = event.user_type
        is_private = bool(chat_type == "direct")
        group_chat = True

        if not is_private:
            group_id = event.group_id
            group_chat = self.bot_user_map[group_id]["group"]
            if group_chat:
                self.bot_user_map[group_id]["engine"] = new_engine

        if is_private or (not group_chat):
            user_id = event.user_id
            self.bot_user_map[user_id]["engine"] = new_engine

    def change_mode(self, group_id):
        group = not self.bot_user_map[group_id]["group"]
        self.bot_user_map[group_id]["group"] = group
        return group

    async def get_singleton_bot(self, engine):
        if engine in self.bots:
            return self.bots[engine]

        chat_config = self.config[engine]
        assert isinstance(chat_config, CfgNode)

        bot = CHAT.build(chat_config)
        self.bots[engine] = bot

        await bot.init_data()

        return bot

    def get_engine(self, bot_name):
        return self.name_map[bot_name.lower()]
