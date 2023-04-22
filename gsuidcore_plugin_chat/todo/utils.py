import re
import json
from datetime import datetime
from os import getcwd
from typing import Literal, Union
from gsuid_core.logger import logger
import jinja2

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
    browser=None
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
        ** pages,
    )


async def get_time(text: str, chatgpt_fn=None):
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M")
    try:
        prompt = f'现在时间是{time_str},' + \
            """帮我把下面提醒解析成时间，事件的格式(事件只包含待办事项，不包含时间信息和主语称呼)，请直接返回如下json {"time": "YYYY-MM-DD HH:mm"' , "thing":xxx,}:"""
        prompt += text
        data = await chatgpt_fn(prompt)
        try:
            data = json.loads(data)
        except:
            data = re.search('{.*}', data).group()
            data = json.loads(data)
        time = data['time']
        thing = data['thing']
        return time, thing, True
    except Exception as e:
        logger.info(f'chatgpt解析提醒失败 {e}')

    return None, None, False
