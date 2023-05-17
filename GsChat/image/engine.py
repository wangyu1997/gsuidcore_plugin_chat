import copy

from yacs.config import CfgNode

from .build import IMAGE, IMAGEENGINE


@IMAGEENGINE.register_module()
class ImageEngine:
    def __init__(self, config: CfgNode = None):
        self.name_map = {
            "filckr": "FilckrImg",
            "websearch": "WebSearchImg",
            "bingai": "BingImg",
        }
        self.bots = {}
        self.current_engine = self.name_map[config.default]
        self.config = copy.deepcopy(config)

    def change_engine(self, new_engine: str):
        self.current_engine = new_engine

    def get_singleton_bot(self, engine):
        if engine in self.bots:
            return self.bots[engine]

        image_config = self.config[engine]
        assert isinstance(image_config, CfgNode)
        bot = IMAGE.build(image_config)
        self.bots[engine] = bot

        return bot

    def get_engine(self, bot_name):
        return self.name_map[bot_name.lower()]

    def get_prompt(self):
        return self.config.align_prompt
