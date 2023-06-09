from contextlib import redirect_stdout

from yacs.config import CfgNode
from gsuid_core.logger import logger
from gsuid_core.data_store import get_res_path

meta_config = CfgNode()
# -----------------------------------------------------------------------------
# chat setting
# -----------------------------------------------------------------------------
meta_config.chat = CfgNode()
meta_config.chat.name = "ChatEngine"
meta_config.chat.default = "chat"
meta_config.chat.group = True

# -----------------------------------------------------------------------------
# Bing setting
# -----------------------------------------------------------------------------
meta_config.chat.Bing = CfgNode()
meta_config.chat.Bing.show_create = True
meta_config.chat.Bing.name = "BingChat"
meta_config.chat.Bing.cd_time = 120
meta_config.chat.Bing.style = "creative"
meta_config.chat.Bing.proxy = ""

# -----------------------------------------------------------------------------
# Normal Chat setting
# -----------------------------------------------------------------------------
meta_config.chat.Normal = CfgNode()
meta_config.chat.Normal.show_create = False
meta_config.chat.Normal.name = "NormalChat"
meta_config.chat.Normal.api_url = (
    "https://api.aigcfun.com/api/v1/text?key=<KEY>"
)
meta_config.chat.Normal.api_keys = []
meta_config.chat.Normal.cd_time = 120
meta_config.chat.Normal.model = "gpt-3.5-turbo"
meta_config.chat.Normal.proxy = ""
meta_config.chat.Normal.token_length = 0
meta_config.chat.Normal.person = "miao"
meta_config.chat.Normal.nickname = "Paimon"
meta_config.chat.Normal.data_url = "https://raw.githubusercontent.com/wangyu1997/file_upload/main/miao.json"
meta_config.chat.Normal.default = "miao"

# -----------------------------------------------------------------------------
# Openai setting
# -----------------------------------------------------------------------------
meta_config.chat.Openai = CfgNode()
meta_config.chat.Openai.show_create = True
meta_config.chat.Openai.name = "OpenaiChat"
meta_config.chat.Openai.cd_time = 120
meta_config.chat.Openai.max_tokens = 1000
meta_config.chat.Openai.cd_time = 120
meta_config.chat.Openai.proxy = ""
meta_config.chat.Openai.api_keys = []

# -----------------------------------------------------------------------------
# POE setting
# -----------------------------------------------------------------------------
meta_config.chat.Poe = CfgNode()
meta_config.chat.Poe.show_create = True
meta_config.chat.Poe.name = "POEChat"
meta_config.chat.Poe.cd_time = 120
meta_config.chat.Poe.proxy = ""
meta_config.chat.Poe.model = "capybara"
meta_config.chat.Poe.api_keys = [""]

# -----------------------------------------------------------------------------
# image setting
# -----------------------------------------------------------------------------
meta_config.image = CfgNode()
meta_config.image.name = "ImageEngine"
meta_config.image.default = "filckr"
meta_config.image.align_prompt = (
    "帮我生成一个适配<QUERY>的英文搜索文本，直接返回文本，不需要额外的文字："
)

# -----------------------------------------------------------------------------
#  filckr setting
# -----------------------------------------------------------------------------
meta_config.image.FilckrImg = CfgNode()
meta_config.image.FilckrImg.name = "FilckrImg"
meta_config.image.FilckrImg.query = "filckr"
meta_config.image.FilckrImg.cnt = 5
meta_config.image.FilckrImg.api_keys = []
meta_config.image.FilckrImg.api_url = (
    "https://www.flickr.com/services/rest"
)
meta_config.image.FilckrImg.method = "flickr.photos.search"

# -----------------------------------------------------------------------------
#  websearch setting
# -----------------------------------------------------------------------------
meta_config.image.WebSearchImg = CfgNode()
meta_config.image.WebSearchImg.name = "WebSearchImg"
meta_config.image.WebSearchImg.query = "web image search"
meta_config.image.WebSearchImg.cnt = 6
meta_config.image.WebSearchImg.api_keys = []
meta_config.image.WebSearchImg.api_url = "https://contextualwebsearch-websearch-v1.p.rapidapi.com/api/Search/ImageSearchAPI"

# -----------------------------------------------------------------------------
#  bingai setting
# -----------------------------------------------------------------------------
meta_config.image.BingImg = CfgNode()
meta_config.image.BingImg.name = "BingImg"
meta_config.image.BingImg.query = "Bing AI"

# -----------------------------------------------------------------------------
#  genshin setting
# -----------------------------------------------------------------------------
meta_config.genshin = CfgNode()

# -----------------------------------------------------------------------------
#  material setting
# -----------------------------------------------------------------------------
meta_config.genshin.material = CfgNode()
meta_config.genshin.material.name = "MaterialModel"
meta_config.genshin.material.skip_three = False
meta_config.genshin.material.push_time = "4:10"

# -----------------------------------------------------------------------------
#  other setting
# -----------------------------------------------------------------------------
meta_config.other = CfgNode()

# -----------------------------------------------------------------------------
#  browser setting
# -----------------------------------------------------------------------------
meta_config.other.browser = CfgNode()
meta_config.other.browser.name = "Browser"

# -----------------------------------------------------------------------------
#  setereo setting
# -----------------------------------------------------------------------------
meta_config.other.setereo = CfgNode()
meta_config.other.setereo.name = "Setereo"
meta_config.other.setereo.default = "default.data"
meta_config.other.setereo.data_url = "https://raw.githubusercontent.com/wangyu1997/file_upload/main/stereo.data"
meta_config.other.setereo.data = "default.data"

# -----------------------------------------------------------------------------
#  song setting
# -----------------------------------------------------------------------------
meta_config.other.song = CfgNode()
meta_config.other.song.name = "Song"
meta_config.other.song.api = (
    "https://netease-cloud-music-api-git-master-wangyu1997.vercel.app"
)

# -----------------------------------------------------------------------------
#  todo setting
# -----------------------------------------------------------------------------
meta_config.other.todo = CfgNode()
meta_config.other.todo.name = "ToDoModel"
meta_config.other.todo.push_time = 30

# -----------------------------------------------------------------------------
#  billing setting
# -----------------------------------------------------------------------------
meta_config.other.billing = CfgNode()
meta_config.other.billing.name = "BillingModel"

# -----------------------------------------------------------------------------
#  extract setting
# -----------------------------------------------------------------------------
meta_config.extract = CfgNode()

# -----------------------------------------------------------------------------
#  bilibili setting
# -----------------------------------------------------------------------------
meta_config.extract.bilibili = CfgNode()
meta_config.extract.bilibili.name = "BiliBiliExtract"
meta_config.extract.bilibili.display_image = True
meta_config.extract.bilibili.display_image_list = True


def get_config():
    m_config = meta_config.clone()
    config_path = get_res_path("GsChat") / "config.yaml"

    if config_path.exists():
        m_config.defrost()
        m_config.merge_from_file(config_path)
        m_config.freeze()
        logger.info("加载用户配置文件")

    with open(config_path, "w") as f:
        logger.info("覆盖用户配置文件")
        with redirect_stdout(f):
            print(m_config.dump(allow_unicode=True))

    return m_config


config = get_config()
