import re
from urllib.parse import quote

from httpx import AsyncClient

from gsuid_core.logger import logger

b23_pattern = r"(b23.tv)|(bili(22|23|33|2233).cn)"
b23_redirect_pattern = r"b23.tv/(\w+)|(bili(22|23|33|2233).cn)/(\w+)"
page_pattern = r"([?&]|&amp;)p=\d+"
time_pattern = r"([?&]|&amp;)t=\d+"
av_pattern = r"av\d+"
bv_pattern = r"BV([A-Za-z0-9]{10})+"
ep_pattern = r"ep\d+"
ss_pattern = r"ss\d+"
md_pattern = r"md\d+"
live_pattern = r"live.bilibili.com/(blanc/|h5/)?(\d+)"
cv_pattern = r"(/read/(cv|mobile|native)(/|\?id=)?|^cv)(\d+)"
dy_type_pattern = r"(t|m).bilibili.com/(\d+)\?(.*?)(&|&amp;)type=2"
dy_id_pattern = r"(t|m).bilibili.com/(\d+)"

bv_url = "https://api.bilibili.com/x/web-interface/view?bvid={param}"
av_url = "https://api.bilibili.com/x/web-interface/view?aid={param}"
ep_url = "https://bangumi.bilibili.com/view/web_api/season?ep_id={param}"
ss_url = "https://bangumi.bilibili.com/view/web_api/season?season_id={param}"
md_url = "https://bangumi.bilibili.com/view/web_api/season?media_id={param}"
live_url = "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={param}"
cv_url = "https://api.bilibili.com/x/article/viewinfo?id={param}&mobi_app=pc&from=web"
dy_type_url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?rid={param}&type=2"
dy_id_url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?dynamic_id={param}"
search_url = "https://api.bilibili.com/x/web-interface/wbi/search/all/v2?keyword={param}"
bilibili_url = "https://www.bilibili.com"


# 处理超过一万的数字
def handle_num(num: int) -> str:
    if num > 10000:
        num = f"{num / 10000:.2f}万"
    return num


async def get_b23_redirection(text: str, client: AsyncClient) -> str:
    # 获取b23链接的重定向
    b23 = re.compile(b23_redirect_pattern, re.I).search(
        text.replace("\\", "")
    )
    url = f"https://{b23[0]}"
    resp = await client.get(url)
    return resp.headers.get('location', url)


async def search_bili_by_title(title: str, client: AsyncClient) -> str:
    # set headers
    resp = await client.get(bilibili_url)
    assert resp.status_code == 200

    resp = await client.get(search_url.format(quote(title)))
    result = (await resp.json())["data"]["result"]

    for i in result:
        if i.get("result_type") != "video":
            continue
        # 只返回第一个结果
        return i["data"][0].get("arcurl")


def extract_bili_info(text: str):
    try:
        url = ""
        page = re.compile(page_pattern).search(text)
        time = re.compile(time_pattern).search(text)
        aid = re.compile(av_pattern, re.I).search(text)
        bv_id = re.compile(bv_pattern, re.I).search(text)
        ep_id = re.compile(ep_pattern, re.I).search(text)
        ssid = re.compile(ss_pattern, re.I).search(text)
        mdid = re.compile(md_pattern, re.I).search(text)
        room_id = re.compile(live_pattern, re.I).search(text)
        cv_id = re.compile(cv_pattern, re.I).search(text)
        dynamic_id_type2 = re.compile(dy_type_pattern, re.I).search(text)
        dynamic_id = re.compile(dy_id_pattern, re.I).search(text)

        if bv_id:
            url = bv_url.format(param=bv_id[0])
        elif aid:
            url = av_url.format(param=aid[0][2:])
        elif ep_id:
            url = ep_url.format(param=ep_id[0][2:])
        elif ssid:
            url = ss_url.format(param=ssid[0][2:])
        elif mdid:
            url = md_url.format(param=mdid[0][2:])
        elif room_id:
            url = live_url.format(param=room_id[2])
        elif cv_id:
            page = cv_id[4]
            url = cv_url.format(param=page)
        elif dynamic_id_type2:
            url = dy_type_url.format(param=dynamic_id_type2[2])
        elif dynamic_id:
            url = dy_id_url.format(param=dynamic_id[2])
        return url, page, time
    except Exception as e:
        logger.info(f'{type(e)}: bilibili解析失败 - {str(e)}')
        return "", None, None
