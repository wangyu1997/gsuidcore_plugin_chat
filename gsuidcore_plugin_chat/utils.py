import inspect
import re
import asyncio
import random
import base64
from httpx import AsyncClient
from gsuid_core.logger import logger
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO


bot_nickname: str = 'Paimon'
poke__reply: tuple = (
    "lsp你再戳？",
    "连个可爱美少女都要戳的肥宅真恶心啊。",
    "你再戳！",
    "？再戳试试？",
    "别戳了别戳了再戳就坏了555",
    "我爪巴爪巴，球球别再戳了",
    "你戳你🐎呢？！",
    f"请不要戳{bot_nickname} >_<",
    "放手啦，不给戳QAQ",
    f"喂(#`O′) 戳{bot_nickname}干嘛！",
    "戳坏了，赔钱！",
    "戳坏了",
    "嗯……不可以……啦……不要乱戳",
    "那...那里...那里不能戳...绝对...",
    "(。´・ω・)ん?",
    "有事恁叫我，别天天一个劲戳戳戳！",
    "欸很烦欸！你戳🔨呢",
    "再戳一下试试？",
    "正在关闭对您的所有服务...关闭成功",
    "啊呜，太舒服刚刚竟然睡着了。什么事？",
    "正在定位您的真实地址...定位成功。轰炸机已起飞",
)
hello_reply: tuple = (
    "你好！",
    "哦豁？！",
    "你好！Ov<",
    f"库库库，呼唤{bot_nickname}做什么呢",
    "我在呢！",
    "呼呼，叫俺干嘛",
)
nonsense: tuple = (
    "你好啊",
    "你好",
    "在吗",
    "在不在",
    "您好",
    "您好啊",
    "你好",
    "在",
)

LINE_CHAR_COUNT = 30 * 2
CHAR_SIZE = 30
TABLE_WIDTH = 4


async def rand_hello() -> str:
    """随机问候语"""
    return random.choice(hello_reply)


async def rand_poke() -> str:
    """随机戳一戳"""
    return random.choice(poke__reply)


async def request_img(img_url, client):
    response = await client.get(img_url)
    if response.status_code == 200:
        img_base64 = base64.b64encode(response.content)
        img_bytes = base64.b64decode(img_base64)
        return img_bytes
    return None

# 简单去除wx at有可能误杀
async def remove_at(msg: str):
    if ' ' not in msg and '@' in msg:
        msg = ''
    msg = re.sub(r"@.*? ", "", msg)
    return msg


async def line_break(line: str) -> str:
    """将一行文本按照指定宽度进行换行"""
    ret = ""
    width = 0
    for c in line:
        if len(c.encode("utf8")) == 3:  # 中文
            if LINE_CHAR_COUNT == width + 1:  # 剩余位置不够一个汉字
                width = 2
                ret += "\n" + c
            else:  # 中文宽度加2，注意换行边界
                width += 2
                ret += c
        elif c == "\n":
            width = 0
            ret += c
        elif c == "\t":
            space_c = TABLE_WIDTH - width % TABLE_WIDTH  # 已有长度对TABLE_WIDTH取余
            ret += " " * space_c
            width += space_c
        else:
            width += 1
            ret += c
        if width >= LINE_CHAR_COUNT:
            ret += "\n"
            width = 0
    return ret if ret.endswith("\n") else ret + "\n"


async def txt_to_img(text: str, font_size=30, font_path="hywh.ttf") -> bytes:
    """将文本转换为图片"""
    text = await line_break(text)
    d_font = ImageFont.truetype(font_path, font_size)
    lines = text.count("\n")
    image = Image.new(
        "L", (LINE_CHAR_COUNT * font_size // 2 +
              50, font_size * lines + 50), "white"
    )
    draw_table = ImageDraw.Draw(im=image)
    draw_table.text(
        xy=(25, 25), text=text, fill="#000000", font=d_font, spacing=4
    )
    new_img = image.convert("RGB")
    img_byte = BytesIO()
    new_img.save(img_byte, format="PNG")
    return img_byte.getvalue()


class Registry:
    def __init__(self, name=None, build_fn=None):
        self._name = name
        self._module_dict = dict()

        if build_fn is not None:
            self.build_fn = build_fn
        else:
            self.build_fn = build_from_cfg

    def __len__(self):
        return len(self._module_dict)

    def __contains__(self, key):
        return key in self._module_dict

    def __repr__(self):
        format_str = f'{self.__class__.__name__}(name={self._name}, ' \
                     f'items={self._module_dict})'
        return format_str

    def get(self, key: str):
        assert key in self._module_dict, f'{key} not find'
        return self._module_dict.get(key)

    def build(self, *args, **kwargs):
        return self.build_fn(*args, **kwargs, registry=self)

    def _register_module(self, module_cls, name=None):
        if not inspect.isclass(module_cls):
            raise TypeError(f'module must be a class, but got {type(module_cls)}')

        if name is None:
            name = module_cls.__name__

        if name in self._module_dict:
            raise KeyError(f'{name} is already registered in {self.name}')

        self._module_dict[name] = module_cls

    def register_module(self, name=None):
        def _register_module(cls):
            self._register_module(module_cls=cls, name=name)
            return cls

        return _register_module

    @property
    def name(self):
        return self._name

    @property
    def module_dict(self):
        return self._module_dict


def build_from_cfg(config, registry):
    if not config.name:
        raise RuntimeError(f'the name of the cfg for {registry.name} is needed!')

    if not isinstance(config.name, str):
        raise RuntimeError(f'the name of the cfg for {registry.name} should be str !')

    cls = registry.get(config.name)
    try:
        return cls(config)
    except Exception as e:
        raise type(e)(f'{cls.__name__}: {e}')



async def download_file(file_path, url):
    # 远程文件下载
    retry = 3
    async with AsyncClient(verify=False) as client:
        while retry:
            try:
                async with client.stream("GET", url) as res:
                    with open(file_path, "wb") as fb:
                        async for chunk in res.aiter_bytes():
                            fb.write(chunk)
                return file_path
            except Exception as e:
                retry -= 1
                if retry:
                    await asyncio.sleep(2)
                else:
                    logger.error(f"文件 {file_path} 下载失败！{e}")
