import re
import json
from datetime import datetime

from gsuid_core.logger import logger


async def get_time(text: str, chatgpt_fn=None):
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M")
    try:
        prompt = (
            f"现在时间是{time_str},"
            + """帮我把下面提醒解析成时间，事件的格式(事件只包含待办事项，不包含时间信息和主语称呼)，请直接返回如下json {"time": "YYYY-MM-DD HH:mm"' , "thing":xxx,}:"""
        )
        prompt += text
        data = await chatgpt_fn(prompt)
        try:
            data = json.loads(data)
        except Exception:
            data = re.search("{.*}", data).group()
            data = json.loads(data)
        time = data["time"]
        thing = data["thing"]
        return time, thing, True
    except Exception as e:
        logger.info(f"chatgpt解析提醒失败 {e}")

    return None, None, False
