import re

from httpx import AsyncClient


async def get_b23_redirection(text: str, client: AsyncClient) -> str:
    # 获取b23链接的重定向
    b23 = re.compile(r"b23.tv/(\w+)|(bili(22|23|33|2233).cn)/(\w+)", re.I).search(
        text.replace("\\", "")
    )
    url = f"https://{b23[0]}"
    resp = await client.get(url)
    return resp.headers.get('location', url)
