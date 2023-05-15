import re
import urllib.parse
import json
import copy
from time import localtime, strftime
from typing import Dict, List, Optional, Tuple, Union
from httpx import AsyncClient
from .build import EXTRACT


@EXTRACT.register_module()
class BiliBiliExtract:
    def __init__(self, config=None):
        self.config = copy.deepcopy(config)
        self.analysis_stat: Dict[int, str] = {}
        self.analysis_display_image = self.config.display_image
        self.analysis_display_image_list = self.config.display_image_list

    async def bili_keyword(
        self, group_id: Optional[int], text: str, client: AsyncClient
    ) -> Union[List[Union[List[str], str]], str]:
        try:
            # 提取url
            url, page, time_location = self.extract(text)
            # 如果是小程序就去搜索标题
            if not url:
                if title := re.search(r'"desc":("[^"哔哩]+")', text):
                    vurl = await self.search_bili_by_title(title[1], client)
                    if vurl:
                        url, page, time_location = self.extract(vurl)

            # 获取视频详细信息
            msg, vurl = "", ""
            if "view?" in url:
                msg, vurl = await self.video_detail(
                    url, page=page, time_location=time_location, client=client
                )
            elif "bangumi" in url:
                msg, vurl = await self.bangumi_detail(url, time_location, client)
            elif "xlive" in url:
                msg, vurl = await self.live_detail(url, client)
            elif "article" in url:
                msg, vurl = await self.article_detail(url, page, client)
            elif "dynamic" in url:
                msg, vurl = await self.dynamic_detail(url, client)

            # 避免多个机器人解析重复推送
            if group_id:
                if (
                    group_id in self.analysis_stat
                    and self.analysis_stat[group_id] == vurl
                ):
                    return ""
                self.analysis_stat[group_id] = vurl
        except Exception as e:
            msg = "bili_keyword Error: {}".format(type(e))
            vurl = None
        return msg, vurl

    async def b23_extract(self, text: str, client: AsyncClient) -> str:
        b23 = re.compile(r"b23.tv/(\w+)|(bili(22|23|33|2233).cn)/(\w+)", re.I).search(
            text.replace("\\", "")
        )
        url = f"https://{b23[0]}"

        resp = await client.get(url)
        return resp.url

    def extract(self, text: str) -> Tuple[str, Optional[str], Optional[str]]:
        try:
            url = ""
            # 视频分p
            page = re.compile(r"([?&]|&amp;)p=\d+").search(text)
            # 视频播放定位时间
            time = re.compile(r"([?&]|&amp;)t=\d+").search(text)
            # 主站视频 av 号
            aid = re.compile(r"av\d+", re.I).search(text)
            # 主站视频 bv 号
            bvid = re.compile(r"BV([A-Za-z0-9]{10})+", re.I).search(text)
            # 番剧视频页
            epid = re.compile(r"ep\d+", re.I).search(text)
            # 番剧剧集ssid(season_id)
            ssid = re.compile(r"ss\d+", re.I).search(text)
            # 番剧详细页
            mdid = re.compile(r"md\d+", re.I).search(text)
            # 直播间
            room_id = re.compile(r"live.bilibili.com/(blanc/|h5/)?(\d+)", re.I).search(
                text
            )
            # 文章
            cvid = re.compile(
                r"(/read/(cv|mobile|native)(/|\?id=)?|^cv)(\d+)", re.I
            ).search(text)
            # 动态
            dynamic_id_type2 = re.compile(
                r"(t|m).bilibili.com/(\d+)\?(.*?)(&|&amp;)type=2", re.I
            ).search(text)
            # 动态
            dynamic_id = re.compile(r"(t|m).bilibili.com/(\d+)", re.I).search(text)
            if bvid:
                url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid[0]}"
            elif aid:
                url = f"https://api.bilibili.com/x/web-interface/view?aid={aid[0][2:]}"
            elif epid:
                url = f"https://bangumi.bilibili.com/view/web_api/season?ep_id={epid[0][2:]}"
            elif ssid:
                url = f"https://bangumi.bilibili.com/view/web_api/season?season_id={ssid[0][2:]}"
            elif mdid:
                url = f"https://bangumi.bilibili.com/view/web_api/season?media_id={mdid[0][2:]}"
            elif room_id:
                url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id[2]}"
            elif cvid:
                page = cvid[4]
                url = f"https://api.bilibili.com/x/article/viewinfo?id={page}&mobi_app=pc&from=web"
            elif dynamic_id_type2:
                url = f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?rid={dynamic_id_type2[2]}&type=2"
            elif dynamic_id:
                url = f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?dynamic_id={dynamic_id[2]}"
            return url, page, time
        except Exception:
            return "", None, None

    async def search_bili_by_title(self, title: str, client: AsyncClient) -> str:
        mainsite_url = "https://www.bilibili.com"
        search_url = f"https://api.bilibili.com/x/web-interface/wbi/search/all/v2?keyword={urllib.parse.quote(title)}"

        # set headers
        resp = await client.get(mainsite_url)
        assert resp.status == 200

        resp = await client.get(search_url)
        result = (await resp.json())["data"]["result"]

        for i in result:
            if i.get("result_type") != "video":
                continue
            # 只返回第一个结果
            return i["data"][0].get("arcurl")

    # 处理超过一万的数字
    def handle_num(self, num: int) -> str:
        if num > 10000:
            num = f"{num / 10000:.2f}万"
        return num

    async def video_detail(
        self, url: str, client: AsyncClient, **kwargs
    ) -> Tuple[List[str], str]:
        try:
            resp = await client.get(url)
            res = resp.json().get("data")
            if not res:
                return "解析到视频被删了/稿件不可见或审核中/权限不足", url
            vurl = f"https://www.bilibili.com/video/av{res['aid']}"
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
                    vurl += f"?p={p}"
                    part = res["pages"][p - 1]["part"]
                    if part != res["title"]:
                        title += f"小标题：{part}\n"
            if time_location := kwargs.get("time_location"):
                time_location = time_location[0].replace("&amp;", "&")[3:]
                if page:
                    vurl += f"&t={time_location}"
                else:
                    vurl += f"?t={time_location}"
            pubdate = strftime("%Y-%m-%d %H:%M:%S", localtime(res["pubdate"]))
            tname = f"类型：{res['tname']} | UP：{res['owner']['name']} | 日期：{pubdate}\n"
            stat = f"播放：{self.handle_num(res['stat']['view'])} | 弹幕：{self.handle_num(res['stat']['danmaku'])} | 收藏：{self.handle_num(res['stat']['favorite'])}\n"
            stat += f"点赞：{self.handle_num(res['stat']['like'])} | 硬币：{self.handle_num(res['stat']['coin'])} | 评论：{self.handle_num(res['stat']['reply'])}\n"
            desc = f"简介：{res['desc']}"
            desc_list = desc.split("\n")
            desc = "".join(i + "\n" for i in desc_list if i)
            desc_list = desc.split("\n")
            if len(desc_list) > 4:
                desc = desc_list[0] + "\n" + desc_list[1] + "\n" + desc_list[2] + "……"
            msg = [cover, title, tname, stat, desc, vurl]
            return msg, vurl
        except Exception as e:
            msg = "视频解析出错--Error: {}".format(type(e))
            return msg, None

    async def bangumi_detail(
        self, url: str, time_location: str, client: AsyncClient
    ) -> Tuple[List[str], str]:
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
                vurl = f"https://www.bilibili.com/bangumi/play/ss{res['season_id']}"
            elif "media_id" in url:
                vurl = f"https://www.bilibili.com/bangumi/media/md{res['media_id']}"
            else:
                epid = re.compile(r"ep_id=\d+").search(url)[0][len("ep_id=") :]
                for i in res["episodes"]:
                    if str(i["ep_id"]) == epid:
                        index_title = f"标题：{i['index_title']}\n"
                        break
                vurl = f"https://www.bilibili.com/bangumi/play/ep{epid}"
            if time_location:
                time_location = time_location[0].replace("&amp;", "&")[3:]
                vurl += f"?t={time_location}"
            msg = [cover, title, index_title, desc, style, evaluate, f"{vurl}\n"]
            return msg, vurl
        except Exception as e:
            msg = "番剧解析出错--Error: {}".format(type(e))
            msg += f"\n{url}"
            return msg, None

    async def live_detail(self, url: str, client: AsyncClient) -> Tuple[List[str], str]:
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
            vurl = f"https://live.bilibili.com/{room_id}\n"
            if lock_status:
                lock_time = res["room_info"]["lock_time"]
                lock_time = strftime("%Y-%m-%d %H:%M:%S", localtime(lock_time))
                title = f"[已封禁]直播间封禁至：{lock_time}\n"
            elif live_status == 1:
                title = f"[直播中]标题：{title}\n"
            elif live_status == 2:
                title = f"[轮播中]标题：{title}\n"
            else:
                title = f"[未开播]标题：{title}\n"
            up = f"主播：{uname}  当前分区：{parent_area_name}-{area_name}\n"
            watch = f"观看：{watched_show}  直播时的人气上一次刷新值：{self.handle_num(online)}\n"
            if tags:
                tags = f"标签：{tags}\n"
            if live_status:
                player = f"独立播放器：https://www.bilibili.com/blackboard/live/live-activity-player.html?enterTheRoom=0&cid={room_id}"
            else:
                player = ""
            msg = [cover, title, up, watch, tags, player, vurl]
            return msg, vurl
        except Exception as e:
            msg = "直播间解析出错--Error: {}".format(type(e))
            return msg, None

    async def article_detail(
        self, url: str, cvid: str, client: AsyncClient
    ) -> Tuple[List[Union[List[str], str]], str]:
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
            vurl = f"https://www.bilibili.com/read/cv{cvid}"
            title = f"标题：{res['title']}\n"
            up = f"作者：{res['author_name']} (https://space.bilibili.com/{res['mid']})\n"
            view = f"阅读数：{self.handle_num(res['stats']['view'])} "
            favorite = f"收藏数：{self.handle_num(res['stats']['favorite'])} "
            coin = f"硬币数：{self.handle_num(res['stats']['coin'])}"
            share = f"分享数：{self.handle_num(res['stats']['share'])} "
            like = f"点赞数：{self.handle_num(res['stats']['like'])} "
            dislike = f"不喜欢数：{self.handle_num(res['stats']['dislike'])}"
            desc = view + favorite + coin + "\n" + share + like + dislike + "\n"
            msg = [images, title, up, desc, vurl]
            return msg, vurl
        except Exception as e:
            msg = "专栏解析出错--Error: {}".format(type(e))
            return msg, None

    async def dynamic_detail(
        self, url: str, client: AsyncClient
    ) -> Tuple[List[Union[List[str], str]], str]:
        try:
            resp = await client.get(url)
            res = resp.json()["data"].get("card")
            if not res:
                return None, None
            card = json.loads(res["card"])
            dynamic_id = res["desc"]["dynamic_id"]
            vurl = f"https://t.bilibili.com/{dynamic_id}\n"
            if not (item := card.get("item")):
                return "动态不存在文字内容", vurl
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
                jorigin = json.loads(origin)
                short_link = jorigin.get("short_link")
                if short_link:
                    content += f"\n动态包含转发视频{short_link}"
                else:
                    content += f"\n动态包含转发其他动态"
            msg = [images, content, f"\n动态链接：{vurl}"]
            return msg, vurl
        except Exception as e:
            msg = "动态解析出错--Error: {}".format(type(e))
            return msg, None
