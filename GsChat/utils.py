import re
import hmac
import base64
import asyncio
import hashlib
import inspect
from os import getcwd
from io import BytesIO
from functools import partial
from contextlib import suppress, asynccontextmanager
from typing import Union, Literal, Optional, AsyncGenerator

import jinja2
from httpx import AsyncClient
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from PIL import Image, ImageDraw, ImageFont
from gsuid_core.segment import MessageSegment
from playwright.async_api import (
    Page,
    Error,
    Browser,
    Playwright,
    async_playwright,
)

LINE_CHAR_COUNT = 30 * 2
CHAR_SIZE = 30
TABLE_WIDTH = 4


async def request_img(img_url, client):
    response = await client.get(img_url)
    if response.status_code == 200:
        img_base64 = base64.b64encode(response.content)
        img_bytes = base64.b64decode(img_base64)
        return img_bytes
    return None


# 简单去除wx at有可能误杀
async def remove_at(msg: str):
    if " " not in msg and "@" in msg:
        msg = ""
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
            space_c = (
                TABLE_WIDTH - width % TABLE_WIDTH
            )  # 已有长度对TABLE_WIDTH取余
            ret += " " * space_c
            width += space_c
        else:
            width += 1
            ret += c
        if width >= LINE_CHAR_COUNT:
            ret += "\n"
            width = 0
    return ret if ret.endswith("\n") else ret + "\n"


async def txt_to_img(
    text: str, font_size=30, font_path="hywh.ttf"
) -> bytes:
    """将文本转换为图片"""
    text = await line_break(text)
    text = "\n".join([text] * 10)
    d_font = ImageFont.truetype(font_path, font_size)
    lines = len(text.split("\n"))
    image = Image.new(
        "L",
        (
            LINE_CHAR_COUNT * font_size // 2 + 50,
            font_size * lines + 300,
        ),
        "white",
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
        format_str = (
            f"{self.__class__.__name__}(name={self._name}, "
            f"items={self._module_dict})"
        )
        return format_str

    def get(self, key: str):
        assert key in self._module_dict, f"{key} not find"
        return self._module_dict.get(key)

    def build(self, *args, **kwargs):
        return self.build_fn(*args, **kwargs, registry=self)

    def _register_module(self, module_cls, name=None):
        if not inspect.isclass(module_cls):
            raise TypeError(
                f"module must be a class, but got {type(module_cls)}"
            )

        if name is None:
            name = module_cls.__name__

        if name in self._module_dict:
            raise KeyError(
                f"{name} is already registered in {self.name}"
            )

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
        raise RuntimeError(
            f"the name of the cfg for {registry.name} is needed!"
        )

    if not isinstance(config.name, str):
        raise RuntimeError(
            f"the name of the cfg for {registry.name} should be str !"
        )

    cls = registry.get(config.name)
    try:
        return cls(config)
    except Exception as e:
        raise type(e)(f"{cls.__name__}: {e}")


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


class BaseBrowser:
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def init_browser(self, **kwargs) -> Browser:
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self.launch_browser(**kwargs)
        except NotImplementedError:
            logger.warning("Playwright", "初始化失败，请关闭FASTAPI_RELOAD")
        except Error:
            await self.install_browser()
            self._browser = await self.launch_browser(**kwargs)
        return self._browser

    async def launch_browser(self, **kwargs) -> Browser:
        assert (
            self._playwright is not None
        ), "Playwright is not initialized"
        return await self._playwright.chromium.launch(**kwargs)

    async def get_browser(self, **kwargs) -> Browser:
        return self._browser or await self.init_browser(**kwargs)

    async def install_browser(self):
        import os
        import sys

        from playwright.__main__ import main

        logger.info("Playwright", "正在安装 chromium")
        sys.argv = ["", "install", "chromium"]
        with suppress(SystemExit):
            logger.info("Playwright", "正在安装依赖")
            os.system("playwright install-deps")
            main()

    @asynccontextmanager
    async def get_new_page(
        self, **kwargs
    ) -> AsyncGenerator[Page, None]:
        assert self._browser, "playwright尚未初始化"
        page = await self._browser.new_page(**kwargs)
        try:
            yield page
        finally:
            await page.close()


async def html_to_pic(
    html: str,
    wait: int = 0,
    template_path: str = f"file://{getcwd()}",
    type: Literal["jpeg", "png"] = "png",
    quality: Union[int, None] = None,
    browser=None,
    **kwargs,
) -> bytes:
    """html转图片

    Args:
        html (str): html文本
        wait (int, optional): 等待时间. Defaults to 0.
        template_path (str, optional): 模板路径 如 "file:///path/to/template/"
        type (Literal["jpeg", "png"]): 图片类型, 默认 png
        quality (int, optional): 图片质量 0-100 当为`png`时无效
        **kwargs: 传入 page 的参数

    Returns:
        bytes: 图片, 可直接发送
    """
    if "file:" not in template_path:
        raise Exception("template_path 应该为 file:///path/to/template")
    async with await browser.new_page(**kwargs) as page:
        await page.goto(template_path)
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(wait)
        img_raw = await page.screenshot(
            full_page=True,
            type=type,
            quality=quality,
        )
    return img_raw


async def template_to_pic(
    template_path: str,
    template_name: str,
    templates: dict,
    pages: dict = {
        "viewport": {"width": 500, "height": 10},
        "base_url": f"file://{getcwd()}",
    },
    wait: int = 0,
    type: Literal["jpeg", "png"] = "png",
    quality: Union[int, None] = None,
    browser=None,
) -> bytes:
    """使用jinja2模板引擎通过html生成图片
    Args:
        template_path (str): 模板路径
        template_name (str): 模板名
        templates (dict): 模板内参数 如: {"name": "abc"}
        pages (dict): 网页参数 Defaults to
            {"base_url": f"file://{getcwd()}", "viewport": {"width": 500, "height": 10}}
        wait (int, optional): 网页载入等待时间. Defaults to 0.
        type (Literal["jpeg", "png"]): 图片类型, 默认 png
        quality (int, optional): 图片质量 0-100 当为`png`时无效

    Returns:
        bytes: 图片 可直接发送
    """

    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_path),
        enable_async=True,
    )
    template = template_env.get_template(template_name)

    return await html_to_pic(
        template_path=f"file://{template_path}",
        html=await template.render_async(**templates),
        wait=wait,
        type=type,
        quality=quality,
        browser=browser,
        **pages,
    )


async def _send_img(url: str, bot: Bot):
    async with AsyncClient(verify=False, timeout=None) as client:
        try:
            img_bytes = await request_img(url, client)
            if img_bytes:
                await bot.send(img_bytes)
        except Exception as e:
            logger.info(f"{type(e)}: 图片发送失败: {e}")


async def send_img(urls, bot: Bot):
    if isinstance(urls, str):
        urls = [urls]
    elif not isinstance(urls, list):
        return

    bot_id = bot.bot_id
    if bot_id == "onebot_v12":
        messages = []
        for url in urls:
            messages.append(MessageSegment.image(url))
        await bot.send(messages)
    else:
        tasks = []
        for url in urls:
            tasks.append(asyncio.ensure_future(_send_img(url, bot)))
        await asyncio.gather(*tasks)


async def send_file(url, bot: Bot, filename=None):
    bot_id = bot.bot_id
    if bot_id == "onebot_v12":
        await bot.send(
            MessageSegment.file(content=url, file_name=filename)
        )
    else:
        async with AsyncClient(verify=False, timeout=None) as client:
            try:
                response = await client.get(url)
                if response:
                    await bot.send(
                        MessageSegment.file(
                            content=response.content,
                            file_name=filename,
                        )
                    )
            except Exception as e:
                logger.info(f"{type(e)}: 文件发送失败: {e}")


async def to_async(func, **kwargs):
    loop = asyncio.get_event_loop()
    print(kwargs)
    partial_func = partial(func, **kwargs)
    data = await loop.run_in_executor(None, partial_func)
    return data


def map_str_to_unique_string(s, key="HASH_KEY"):
    hashed = hmac.new(key.encode(), s.encode(), hashlib.sha256).digest()
    unique_string = "".join(format(x, "02x") for x in hashed)[:15]
    unique_string = unique_string[: max(4, len(unique_string))]
    return unique_string
