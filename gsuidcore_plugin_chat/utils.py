import re
import json
import random
import httpx
import asyncio
import requests
from functools import partial

from .config import config, keyword_path, anime_thesaurus
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

reply_private: bool = config.ai_reply_private
bot_nickname: str = config.bot_nickname
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
    f"库库库，呼唤{config.bot_nickname}做什么呢",
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


async def normal_chat(text, session):
    if not session:
        session = []

    key = config.normal_chat_key

    prompt = [{'role': 'system', 'content': '你的名字叫Paimon，是来自提瓦特大陆的小助手，和你对话的是旅行者。'}]
    for (human, ai) in session:
        prompt.append({'role': 'user', 'content': human})
        prompt.append({'role': 'assistant', 'content': ai})

    prompt.append({'role': 'user', 'content': text})
    data = {
        "messages": prompt,
        "tokensLength": 0,
        "model": "gpt-3.5-turbo"
    }

    proxies = {}
    if config.chat_proxy:
        proxies = {
            'all://': f"http://{config.chat_proxy}"
        }

    url = f"https://api.aigcfun.com/api/v1/text?key={key}"

    headers = {
        'Content-Type': "application/json",
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
    }

    async with httpx.AsyncClient(proxies=proxies) as client:
        res = await client.post(url, data=json.dumps(data), headers=headers)
        res = res.json()
        return res["choices"][0]["text"].strip()


async def get_chat_result(text: str, session: None) -> str:
    """从字典中返回结果"""
    try:
        data = await normal_chat(text, session)
    except Exception as _:
        data = "请求失败，可能当前session对话达到上限，请使用[重置chat]重置会话，或尝试使用bing xx或openai xx来询问bing或者openai吧"

    return data

# 简单去除wx at有可能误杀


async def remove_at(msg: str):
    if ' ' not in msg and '@' in msg:
        msg = ''
    msg = re.sub(r"@.*? ", "", msg)
    return msg


async def add_word(word1: str, word2: str) -> str:
    """添加词条"""
    lis = []
    for key in anime_thesaurus:
        if key == word1:
            lis = anime_thesaurus[key]
            for word in lis:
                if word == word2:
                    return "寄"
    if lis == []:
        axis = {word1: [word2]}
    else:
        lis.append(word2)
        axis = {word1: lis}
    anime_thesaurus.update(axis)
    with open(keyword_path, "w", encoding="utf-8") as f:
        json.dump(anime_thesaurus, f, ensure_ascii=False, indent=4)


async def check_word(target: str) -> str:
    """查询关键词下词条"""
    for item in anime_thesaurus:
        if target == item:
            mes = f"下面是关键词 {target} 的全部响应\n\n"
            # 获取关键词
            lis = anime_thesaurus[item]
            n = 0
            for word in lis:
                n = n + 1
                mes = mes + str(n) + "、" + word + "\n"
            return mes
    return "寄"


async def check_all() -> str:
    """查询全部关键词"""
    mes = "下面是全部关键词\n\n"
    for c in anime_thesaurus:
        mes = mes + c + "\n"
    return mes


async def del_word(word1: str, word2: int):
    """删除关键词下具体回答"""
    axis = {}
    for key in anime_thesaurus:
        if key == word1:
            lis: list = anime_thesaurus[key]
            word2 = int(word2) - 1
            try:
                lis.pop(word2)
                axis = {word1: lis}
            except Exception:
                return "寄"
    if axis == {}:
        return "寄"
    anime_thesaurus.update(axis)
    with open(keyword_path, "w", encoding="utf8") as f:
        json.dump(anime_thesaurus, f, ensure_ascii=False, indent=4)


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
