import re
import copy
import json
from typing import Dict, Optional
from time import strftime, localtime

from httpx import AsyncClient
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger

from .build import EXTRACT
from ..utils import send_img
from .utils import (
    handle_num,
    b23_pattern,
    extract_bili_info,
    get_b23_redirection,
    search_bili_by_title,
)


@EXTRACT.register_module()
class BiliBiliExtract:
    def __init__(self, config=None):
        self.config = copy.deepcopy(config)
        self.analysis_stat: Dict[int, str] = {}
        self.analysis_display_image = self.config.display_image
        self.analysis_display_image_list = (
            self.config.display_image_list
        )

    async def handle_url(self, bot: Bot, event: Event):
        text = str(event.raw_text).strip()
        async with AsyncClient(timeout=None, verify=False) as client:
            try:
                if re.search(b23_pattern, text, re.I):
                    # 提前处理短链接，避免解析到其他的
                    text = await get_b23_redirection(text, client)

                group_id = (
                    event.group_id
                    if event.user_type != "direct"
                    else None
                )
                msg, url = await self.bili_keyword(
                    group_id, text, client
                )
                if msg:
                    if isinstance(msg, str):
                        # 说明是错误信息
                        await bot.send(msg)
                    else:
                        await self._send_msg(msg, bot)
            except Exception as e:
                logger.info(f"{type(e)}: {str(e)}")

    @staticmethod
    async def _send_msg(msg, bot) -> None:
        try:
            await bot.send("\n".join(msg[1:]))
            await send_img(msg[0], bot)
        except Exception as e:
            logger.info(f"{type(e)}: {str(e)}")

    async def bili_keyword(
        self, group_id: Optional[int], text: str, client: AsyncClient
    ):
        try:
            # 提取url
            url, page, time_location = extract_bili_info(text)
            # 如果是小程序就去搜索标题
            if not url:
                if title := re.search(r'"desc":("[^"哔哩]+")', text):
                    video_url = await search_bili_by_title(
                        title[1], client
                    )
                    if video_url:
                        url, page, time_location = extract_bili_info(
                            video_url
                        )

            # 获取视频详细信息
            msg, video_url = "", ""
            if "view?" in url:
                msg, video_url = await self.video_detail(
                    url,
                    page=page,
                    time_location=time_location,
                    client=client,
                )
            elif "bangumi" in url:
                msg, video_url = await self.bangumi_detail(
                    url, time_location, client
                )
            elif "xlive" in url:
                msg, video_url = await self.live_detail(url, client)
            elif "article" in url:
                msg, video_url = await self.article_detail(
                    url, page, client
                )
            elif "dynamic" in url:
                msg, video_url = await self.dynamic_detail(url, client)

            # 避免多个机器人解析重复推送
            if group_id:
                if (
                    group_id in self.analysis_stat
                    and self.analysis_stat[group_id] == video_url
                ):
                    return ""
                self.analysis_stat[group_id] = video_url
        except Exception as e:
            print(e)
            msg = "bili_keyword Error: {}".format(type(e))
            video_url = None
        return msg, video_url

    async def video_detail(
        self, url: str, client: AsyncClient, **kwargs
    ):
        try:
            resp = await client.get(url)
            res = resp.json().get("data")
            if not res:
                return "解析到视频被删了/稿件不可见或审核中/权限不足", url
            video_url = f"https://www.bilibili.com/video/av{res['aid']}"
            title = f"\n标题：{res['title']}\n"
            cover = (
                res["pic"]
                if self.analysis_display_image
                or "video" in self.analysis_display_image_list
                else ""
            )
            if page := kwargs.get("page"):
                page = page[0].replace("&amp;", "&")
                p = int(page[3:])
                if p <= len(res["pages"]):
                    video_url += f"?p={p}"
                    part = res["pages"][p - 1]["part"]
                    if part != res["title"]:
                        title += f"小标题：{part}\n"
            if time_location := kwargs.get("time_location"):
                time_location = time_location[0].replace("&amp;", "&")[
                    3:
                ]
                if page:
                    video_url += f"&t={time_location}"
                else:
                    video_url += f"?t={time_location}"
            pubdate = strftime(
                "%Y-%m-%d %H:%M:%S", localtime(res["pubdate"])
            )
            tname = f"类型：{res['tname']} | UP：{res['owner']['name']} | 日期：{pubdate}\n"
            stat = f"播放：{handle_num(res['stat']['view'])} | 弹幕：{handle_num(res['stat']['danmaku'])} | 收藏：{handle_num(res['stat']['favorite'])}\n"
            stat += f"点赞：{handle_num(res['stat']['like'])} | 硬币：{handle_num(res['stat']['coin'])} | 评论：{handle_num(res['stat']['reply'])}\n"
            desc = f"简介：{res['desc']}"
            desc_list = desc.split("\n")
            desc = "".join(i + "\n" for i in desc_list if i)
            desc_list = desc.split("\n")
            if len(desc_list) > 4:
                desc = (
                    desc_list[0]
                    + "\n"
                    + desc_list[1]
                    + "\n"
                    + desc_list[2]
                    + "……"
                )
            msg = [cover, title, tname, stat, desc, video_url]
            return msg, video_url
        except Exception as e:
            msg = "视频解析出错--Error: {}".format(type(e))
            return msg, None

    async def bangumi_detail(
        self, url: str, time_location: str, client: AsyncClient
    ):
        try:
            resp = await client.get(url)
            res = resp.json().get("result")
            if not res:
                return None, None
            cover = (
                res["cover"]
                if self.analysis_display_image
                or "bangumi" in self.analysis_display_image_list
                else ""
            )
            title = f"番剧：{res['title']}\n"
            desc = f"{res['newest_ep']['desc']}\n"
            index_title = ""
            style = "".join(f"{i}," for i in res["style"])
            style = f"类型：{style[:-1]}\n"
            evaluate = f"简介：{res['evaluate']}\n"
            if "season_id" in url:
                video_url = f"https://www.bilibili.com/bangumi/play/ss{res['season_id']}"
            elif "media_id" in url:
                video_url = f"https://www.bilibili.com/bangumi/media/md{res['media_id']}"
            else:
                epid = re.compile(r"ep_id=\d+").search(url)[0][
                    len("ep_id=") :
                ]
                for i in res["episodes"]:
                    if str(i["ep_id"]) == epid:
                        index_title = f"标题：{i['index_title']}\n"
                        break
                video_url = (
                    f"https://www.bilibili.com/bangumi/play/ep{epid}"
                )
            if time_location:
                time_location = time_location[0].replace("&amp;", "&")[
                    3:
                ]
                video_url += f"?t={time_location}"
            msg = [
                cover,
                title,
                index_title,
                desc,
                style,
                evaluate,
                f"{video_url}\n",
            ]
            return msg, video_url
        except Exception as e:
            msg = "番剧解析出错--Error: {}".format(type(e))
            msg += f"\n{url}"
            return msg, None

    async def live_detail(self, url: str, client: AsyncClient):
        try:
            resp = await client.get(url)
            res = resp.json()
            if res["code"] != 0:
                return None, None
            res = res["data"]
            uname = res["anchor_info"]["base_info"]["uname"]
            room_id = res["room_info"]["room_id"]
            title = res["room_info"]["title"]
            cover = (
                res["room_info"]["cover"]
                if self.analysis_display_image
                or "live" in self.analysis_display_image_list
                else ""
            )
            live_status = res["room_info"]["live_status"]
            lock_status = res["room_info"]["lock_status"]
            parent_area_name = res["room_info"]["parent_area_name"]
            area_name = res["room_info"]["area_name"]
            online = res["room_info"]["online"]
            tags = res["room_info"]["tags"]
            watched_show = res["watched_show"]["text_large"]
            video_url = f"https://live.bilibili.com/{room_id}\n"
            if lock_status:
                lock_time = res["room_info"]["lock_time"]
                lock_time = strftime(
                    "%Y-%m-%d %H:%M:%S", localtime(lock_time)
                )
                title = f"[已封禁]直播间封禁至：{lock_time}\n"
            elif live_status == 1:
                title = f"[直播中]标题：{title}\n"
            elif live_status == 2:
                title = f"[轮播中]标题：{title}\n"
            else:
                title = f"[未开播]标题：{title}\n"
            up = f"主播：{uname}  当前分区：{parent_area_name}-{area_name}\n"
            watch = f"观看：{watched_show}  直播时的人气上一次刷新值：{handle_num(online)}\n"
            if tags:
                tags = f"标签：{tags}\n"
            if live_status:
                player = f"独立播放器：https://www.bilibili.com/blackboard/live/live-activity-player.html?enterTheRoom=0&cid={room_id}"
            else:
                player = ""
            msg = [cover, title, up, watch, tags, player, video_url]
            return msg, video_url
        except Exception as e:
            msg = "直播间解析出错--Error: {}".format(type(e))
            return msg, None

    async def article_detail(
        self, url: str, cv_id: str, client: AsyncClient
    ):
        try:
            resp = await client.get(url)
            res = resp.json().get("data")
            if not res:
                return None, None
            images = (
                res["origin_image_urls"]
                if self.analysis_display_image
                or "article" in self.analysis_display_image_list
                else []
            )
            video_url = f"https://www.bilibili.com/read/cv{cv_id}"
            title = f"标题：{res['title']}\n"
            up = f"作者：{res['author_name']} (https://space.bilibili.com/{res['mid']})\n"
            view = f"阅读数：{handle_num(res['stats']['view'])} "
            favorite = f"收藏数：{handle_num(res['stats']['favorite'])} "
            coin = f"硬币数：{handle_num(res['stats']['coin'])}"
            share = f"分享数：{handle_num(res['stats']['share'])} "
            like = f"点赞数：{handle_num(res['stats']['like'])} "
            dislike = f"不喜欢数：{handle_num(res['stats']['dislike'])}"
            desc = (
                view
                + favorite
                + coin
                + "\n"
                + share
                + like
                + dislike
                + "\n"
            )
            msg = [images, title, up, desc, video_url]
            return msg, video_url
        except Exception as e:
            msg = "专栏解析出错--Error: {}".format(type(e))
            return msg, None

    async def dynamic_detail(self, url: str, client: AsyncClient):
        try:
            resp = await client.get(url)
            res = resp.json()["data"].get("card")
            if not res:
                return None, None
            card = json.loads(res["card"])
            dynamic_id = res["desc"]["dynamic_id"]
            video_url = f"https://t.bilibili.com/{dynamic_id}\n"
            if not (item := card.get("item")):
                return "动态不存在文字内容", video_url
            if not (content := item.get("description")):
                content = item.get("content")
            content = content.replace("\r", "\n")
            if len(content) > 250:
                content = content[:250] + "......"
            images = (
                [i.get("img_src") for i in item.get("pictures", [])]
                if self.analysis_display_image
                or "dynamic" in self.analysis_display_image_list
                else []
            )
            if not images:
                pics = item.get("pictures_count")
                if pics:
                    content += f"\nPS：动态中包含{pics}张图片"
            if origin := card.get("origin"):
                j_origin = json.loads(origin)
                short_link = j_origin.get("short_link")
                if short_link:
                    content += f"\n动态包含转发视频{short_link}"
                else:
                    content += "\n动态包含转发其他动态"
            msg = [images, content, f"\n动态链接：{video_url}"]
            return msg, video_url
        except Exception as e:
            msg = "动态解析出错--Error: {}".format(type(e))
            return msg, None
