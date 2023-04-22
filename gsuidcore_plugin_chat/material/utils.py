from .config import (
    AMBR,
    WEEKLY_BOSS,
)
import json
from httpx import HTTPError, AsyncClient
import asyncio
from time import time
from io import BytesIO
from re import findall
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Tuple, Union, Literal, Optional
from gsuid_core.plugins.GenshinUID.GenshinUID.utils.database import get_sqla
from gsuid_core.plugins.GenshinUID.GenshinUID.utils.mys_api import mys_api
from gsuid_core.logger import logger
from PIL import Image
from .config import MYS_API
from re import match
from math import ceil
from io import BytesIO
from pathlib import Path
from copy import deepcopy
from typing import Dict, List, Union
from PIL import Image, ImageDraw, ImageFont
from gsuid_core.logger import logger
from gsuid_core.data_store import get_res_path

CONFIG_DIR = get_res_path('GsChat')/'materials'
GSUID_DIR = get_res_path("GenshinUID")
DL_MIRROR = 'https://api.ambr.top/assets/UI/'
SKIP_THREE = True
_WEEKLY_BOSS = WEEKLY_BOSS[:-1]
ITEM_ALIAS = {}
DL_CFG = {}

RESAMPLING = getattr(Image, "Resampling", Image).LANCZOS


async def _get_uid(user_id: str, bot_id: str):
    sqla = get_sqla(bot_id)
    uid = await sqla.get_bind_uid(user_id)

    return uid


async def _mys_request(
    url: str,
    method: str,
    uid: str,
    data: Dict
) -> Dict:

    ck = await mys_api.get_ck(uid, 'RANDOM')
    HEADER = {
        "host": "api-takumi.mihoyo.com",
        "origin": "https://webstatic.mihoyo.com",
        "referer": "https://webstatic.mihoyo.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": (
            "Mozilla/5.0 (Linux; Android 12; SM-G977N Build/SP1A.210812.016; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
            "Chrome/107.0.5304.105 Mobile Safari/537.36 miHoYoBBS/2.40.1"
        ),
        "x-requested-with": "com.mihoyo.hyperion",
    }
    HEADER['Cookie'] = ck

    data = await mys_api._mys_request(
        url=url,
        method=method,
        header=HEADER,
        params=data if method == 'GET' else None,
        data=data if method == 'POST' else None,
    )
    return data['data'], data['retcode'] == 0


async def request_cal(uid: str, data: Dict):
    request_url = MYS_API['计算']
    result, success = await _mys_request(request_url, 'POST', uid, data)
    return result, success


async def request_skill(uid: str, data: Dict):
    request_url = MYS_API['技能']
    result, success = await _mys_request(request_url, 'GET', uid, data)
    return result, success


async def sub_helper(
    mode: Literal["r", "ag", "ap", "dg", "dp"] = "r", id: Union[str, int] = "", bot_id: Union[str, int] = ""
) -> Union[Dict, str]:
    cfg_file = CONFIG_DIR / "sub.json"
    sub_cfg = json.loads(cfg_file.read_text(encoding="UTF-8"))

    # 读取订阅配置
    if mode == "r":
        return sub_cfg

    # 添加及删除订阅配置
    write_key = {"g": "群组", "p": "私聊"}[mode[1]]
    if bot_id not in sub_cfg[write_key]:
        sub_cfg[write_key][bot_id] = []

    if mode[0] == "a":
        # 添加群组订阅或私聊订阅
        if id in list(sub_cfg[write_key][bot_id]):
            return f"已经添加过当前{write_key}的原神每日材料订阅辣！"
        sub_cfg[write_key][bot_id].append(id)
    else:
        # 删除群组订阅或私聊订阅
        if id not in list(sub_cfg[write_key][bot_id]):
            return f"还没有添加过当前{write_key}的原神每日材料订阅哦.."
        sub_cfg[write_key][bot_id].remove(id)

    # 更新写入
    cfg_file.write_text(
        json.dumps(sub_cfg, ensure_ascii=False, indent=2), encoding="UTF-8"
    )
    return f"已{'启用' if mode[0] == 'a' else '禁用'}当前{write_key}的原神每日材料订阅。"


def get_weekday(delta: int = 0) -> int:
    """周几整数获取，delta 为向后推迟几天"""

    today = datetime.now()  # 添加时区信息
    _delta = (delta - 1) if today.hour < 4 else delta
    return (today + timedelta(days=_delta)).weekday() + 1


async def generate_daily_msg(
    material: Literal["avatar", "weapon", "all", "update"],
    weekday: int = 0,
    delta: int = 0,
) -> Union[Path, str]:
    """原神每日材料图片生成入口"""

    # 时间判断
    weekday = weekday or get_weekday(delta)
    if weekday == 7:
        return "今天所有天赋培养、武器突破材料都可以获取哦~"
    day = weekday % 3 or 3

    # 存在图片缓存且非更新任务时使用缓存
    cache_pic = CONFIG_DIR / "cache" / f"daily.{day}.{material}.jpg"
    if material != "update" and cache_pic.exists():
        logger.info(f"使用缓存的原神材料图片 {cache_pic.name}")
        return cache_pic

    # 根据每日材料配置重新生成图片
    config = json.loads(
        (CONFIG_DIR / "config.json").read_text(encoding="UTF-8"))
    need_types = [material] if material in [
        "avatar", "weapon"] else ["avatar", "weapon"]
    # 按需绘制素材图片
    try:
        return await draw_materials(config, need_types, day)
    except Exception as e:
        logger.opt(exception=e).error("原神每日材料图片生成出错")
        return f"[{e.__class__.__name__}] 原神每日材料生成失败"


async def generate_weekly_msg(boss: str) -> Union[Path, str]:
    """原神周本材料图片生成入口"""

    assert boss in ["all", *[b[0] for b in WEEKLY_BOSS]]
    # 存在图片缓存且非更新任务时使用缓存
    cache_pic = CONFIG_DIR / f"cache/weekly.{boss}.jpg"
    if cache_pic.exists():
        logger.info(f"使用缓存的原神材料图片 {cache_pic.name}")
        return cache_pic

    # 根据每日材料配置重新生成图片
    config = json.loads(
        (CONFIG_DIR / "config.json").read_text(encoding="UTF-8"))
    need_types = [boss] if boss != "all" else [b[0] for b in _WEEKLY_BOSS]
    if not config["weekly"].get("？？？") and boss == "？？？":
        return "当前暂无未上线的周本"
    elif config["weekly"].get("？？？") and boss == "all":
        need_types.append("？？？")
    # 按需绘制素材图片
    try:
        return await draw_materials(config, need_types)
    except Exception as e:
        logger.opt(exception=e).error("原神周本材料图片生成出错")
        return f"[{e.__class__.__name__}] 原神周本材料生成失败"


async def get_target(alias: str) -> Tuple[int, str]:
    """升级目标 ID 及真实名称提取"""

    alias = alias.lower()
    for item_id, item_alias in ITEM_ALIAS.items():
        if alias in item_alias:
            return int(item_id), item_alias[0]
    return 0, alias


async def get_upgrade_target(target_id: int, msg: str, uid: str) -> Dict:
    """计算器升级范围提取"""
    lvl_regex = r"([0-9]{1,2})([-\s]([0-9]{1,2}))?"
    t_lvl_regex = r"(10|[1-9])(-(10|[1-9]))?"

    # 武器升级识别
    if target_id < 10000000:
        level_target = findall(lvl_regex, msg)
        if not level_target:
            _lvl_from, _lvl_to = 1, 90
        else:
            _target = level_target[0]
            _lvl_from, _lvl_to = (
                (int(_target[0]), int(_target[-1]))
                if _target[-1]
                else (1, int(_target[0]))
            )
        return (
            {"error": "武器等级超出限制~"}
            if _lvl_to > 90
            else {
                "weapon": {
                    "id": target_id,
                    "level_current": _lvl_from,
                    "level_target": _lvl_to,
                },
            }
        )

    # 角色升级识别
    # 角色等级，支持 90、70-90、70 90 三种格式
    level_input = (
        msg.split("天赋")[0].strip() if "天赋" in msg else msg.split(
            " ", 1)[0].strip()
    )
    level_targets = findall(lvl_regex, level_input)
    if not level_targets:
        # 消息直接以天赋开头视为不升级角色等级
        _lvl_from, _lvl_to = 90 if msg.startswith("天赋") else 1, 90
    elif len(level_targets) > 1:
        return {"error": f"无法识别的等级「{level_input}」"}
    else:
        _target = level_targets[0]
        _lvl_from, _lvl_to = (
            (int(_target[0]), int(_target[-1])
             ) if _target[-1] else (1, int(_target[0]))
        )
    if _lvl_to > 90:
        return {"error": "伙伴等级超出限制~"}
    msg = msg.lstrip(level_input).strip()
    # 天赋等级，支持 8、888、81010、8 8 8、1-8、1-8 1-10 10 等
    if msg.startswith("天赋"):
        msg = msg.lstrip("天赋").strip()
    skill_targets = findall(t_lvl_regex, msg)
    if not skill_targets:
        _skill_target = [[1, 8]] * 3
    else:
        _skill_target = [
            [int(_matched[0]), int(_matched[-1])]
            if _matched[-1]
            else [1, int(_matched[0])]
            for _matched in skill_targets
        ]
    if len(_skill_target) > 3:
        return {"error": f"怎么会有 {len(_skill_target)} 个技能的角色呢？"}
    if any(_s[1] > 10 for _s in _skill_target):
        return {"error": "天赋等级超出限制~"}

    # 获取角色技能数据
    skill_list, success = await request_skill(uid, {"avatar_id": target_id})
    if not success:
        return skill_list
    skill_ids = [
        skill["group_id"] for skill in skill_list["list"] if skill["max_level"] == 10
    ]

    return {
        "avatar_id": target_id,
        "avatar_level_current": _lvl_from,
        "avatar_level_target": _lvl_to,
        # "element_attr_id": 4,
        "skill_list": [
            {
                "id": skill_ids[idx],
                "level_current": skill_target[0],
                "level_target": skill_target[1],
            }
            for idx, skill_target in enumerate(_skill_target)
        ]

    }


async def query_ambr(
    type: Literal["每日采集", "升级材料", "角色列表", "武器列表", "材料列表"], retry: int = 3
) -> Dict:
    """安柏计划数据接口请求"""

    async with AsyncClient() as client:
        while retry:
            try:
                res = await client.get(AMBR[type], timeout=10.0)
                return res.json()["data"]
            except (HTTPError, json.decoder.JSONDecodeError, KeyError) as e:
                retry -= 1
                if retry:
                    await asyncio.sleep(2)
                else:
                    logger.opt(exception=e).error(f"安柏计划 {type} 接口请求出错")
    return {}


def _init_picture_dir(env_key: str, config_dir: Path) -> Tuple[str, str, Path]:
    """根据本地文件决定后续下载文件路径及命名"""
    if "item" in env_key:
        env_value = None
    elif "avatar" in env_key:
        env_value = GSUID_DIR / "resource/chars"
    else:
        env_value = GSUID_DIR / "resource/weapon"

    if not env_value:
        sub_dirs = {
            "gsmaterial_avatar": "avatar",
            "gsmaterial_weapon": "weapon",
            "gsmaterial_item": "item",
        }
        return "name", "png", config_dir / sub_dirs[env_key]
    env_value = Path(env_value)
    if not env_value.exists():
        raise ValueError(f".env 文件中 {env_key} 填写的路径不存在！")
    elif env_value.is_file():
        pic_name = "id" if str(env_value.name[0]).isdigit() else "name"
        pic_fmt = env_value.name.split(".")[-1]
        pic_dir = env_value.parent
        return pic_name, pic_fmt, pic_dir
    elif env_value.is_dir():
        pic_name, pic_fmt = "name", "png"
        for already_have in env_value.iterdir():
            pic_name = "id" if str(already_have.name[0]).isdigit() else "name"
            pic_fmt = already_have.name.split(".")[-1]
            break
        return pic_name, pic_fmt, env_value
    raise ValueError(f".env 文件中 {env_key} 填写的值异常！应填写图片文件或文件夹路径")


async def download(
    url: str, type: str = "draw", rename: str = "", retry: int = 3
) -> Optional[Path]:
    """
    资源下载。图片资源使用 Pillow 保存
    * ``param url: str`` 下载链接
    * ``param type: str = "draw"`` 下载类型，根据类型决定保存的文件夹
    * ``param rename: str = ""`` 下载资源重命名，需要包含文件后缀
    * ``param retry: int = 3`` 下载失败重试次数
    - ``return: Optional[Path]`` 本地文件路径，出错时返回空
    """

    # 下载链接及保存路径处理
    if type == "draw":
        # 插件绘图素材，通过阿里云 CDN 下载
        f = CONFIG_DIR / "draw" / url
        url = f"https://cdn.monsterx.cn/bot/gsmaterial/{url}"
    elif type == "mihoyo":
        # 通过米游社下载的文件，主要为米游社计算器材料图标
        f = DL_CFG["item"]["dir"] / rename
    else:
        # 可通过镜像下载的文件，主要为角色头像、武器图标、天赋及武器突破材料图标
        f = DL_CFG[type]["dir"] / rename
        url = DL_MIRROR + url

    # 跳过下载本地已存在的文件
    if f.exists():
        # 测试角色图像为白色问号，该图片 st_size = 5105，小于 6KB 均视为无效图片
        if not (f.name.lower().endswith("png") and f.stat().st_size < 6144):
            return f

    # 远程文件下载
    async with AsyncClient(verify=False) as client:
        while retry:
            try:
                if type == "draw":
                    # 通过阿里云 CDN 下载，可能有字体文件等
                    async with client.stream("GET", url) as res:
                        with open(f, "wb") as fb:
                            async for chunk in res.aiter_bytes():
                                fb.write(chunk)
                else:
                    logger.info(f"正在下载文件 {f.name}\n>>>>> {url}")
                    headers = (
                        {
                            "host": "uploadstatic.mihoyo.com",
                            "referer": "https://webstatic.mihoyo.com/",
                            "sec-fetch-dest": "image",
                            "sec-fetch-mode": "no-cors",
                            "sec-fetch-site": "same-site",
                            "user-agent": (
                                "Mozilla/5.0 (Linux; Android 12; SM-G977N Build/SP1A.210812.016; wv) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
                                "Chrome/107.0.5304.105 Mobile Safari/537.36 miHoYoBBS/2.40.1"
                            ),
                            "x-requested-with": "com.mihoyo.hyperion",
                        }
                        if type == "mihoyo"
                        else {
                            "referer": "https://ambr.top/",
                            "user-agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
                                "like Gecko) Chrome/104.0.5112.81 Safari/537.36 Edg/104.0.1293.47"
                            ),
                        }
                    )
                    res = await client.get(url, headers=headers, timeout=20.0)
                    userImage = Image.open(BytesIO(res.content))
                    userImage.save(f, quality=100)
                return f
            except Exception as e:
                retry -= 1
                if retry:
                    await asyncio.sleep(2)
                else:
                    logger.opt(exception=e).error(f"文件 {f.name} 下载失败！")


async def check_files():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "draw").mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "cache").mkdir(parents=True, exist_ok=True)

    _avatar, _avatar_fmt, _avatar_dir = _init_picture_dir(
        "gsmaterial_avatar", CONFIG_DIR)
    _weapon, _weapon_fmt, _weapon_dir = _init_picture_dir(
        "gsmaterial_weapon", CONFIG_DIR)
    _item, _item_fmt, _item_dir = _init_picture_dir(
        "gsmaterial_item", CONFIG_DIR)
    _avatar_dir.mkdir(parents=True, exist_ok=True)
    _weapon_dir.mkdir(parents=True, exist_ok=True)
    _item_dir.mkdir(parents=True, exist_ok=True)

    DL_CFG = {
        "avatar": {"dir": _avatar_dir, "file": _avatar, "fmt": _avatar_fmt},
        "weapon": {"dir": _weapon_dir, "file": _weapon, "fmt": _weapon_fmt},
        "item": {"dir": _item_dir, "file": _item, "fmt": _item_fmt},
    }

    # 配置文件初始化
    if not (CONFIG_DIR / "sub.json").exists():
        (CONFIG_DIR / "sub.json").write_text(
            json.dumps({"群组": {}, "私聊": {}}, ensure_ascii=False, indent=2), encoding="UTF-8"
        )

    return DL_CFG


async def update_config(config):
    """材料配置更新"""
    global ITEM_ALIAS, DL_CFG, SKIP_THREE
    SKIP_THREE = config.skip_three
    DL_CFG = await check_files()

    async with AsyncClient(verify=False) as client:
        ITEM_ALIAS = await client.get(
            "https://cdn.monsterx.cn/bot/gsmaterial/item-alias.json")
        ITEM_ALIAS = ITEM_ALIAS.json()
        (CONFIG_DIR / "item-alias.json").write_text(
            json.dumps(ITEM_ALIAS, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # 启动资源下载
    init_tasks = [
        download(file, "draw")
        for file in [
            "SmileySans-Oblique.ttf",
            "bg5.140.png",
            "bg4.140.png",
            "bg3.140.png",
        ]
    ]

    await asyncio.gather(*init_tasks)
    init_tasks.clear()

    logger.info("原神材料配置更新开始...")

    # 获取安柏计划数据
    logger.debug("安柏计划数据接口请求...")
    domain_res = await query_ambr("每日采集")
    update_res = await query_ambr("升级材料")
    avatar_res = await query_ambr("角色列表")
    weapon_res = await query_ambr("武器列表")
    material_res = await query_ambr("材料列表")
    if any(
        not x for x in [domain_res, avatar_res, weapon_res, update_res, material_res]
    ):
        logger.info("安柏计划数据不全！更新任务被跳过")
        return DL_CFG, ITEM_ALIAS

    config = {"avatar": {}, "weapon": {},
              "weekly": {}, "skip_3": SKIP_THREE, "time": 0}

    # 生成最新每日材料配置
    logger.debug("每日材料配置更新 & 对应图片下载...")
    for weekday, domains in domain_res.items():
        if weekday not in ["monday", "tuesday", "wednesday"]:
            # 跳过材料重复的日期
            continue
        day_num = {"monday": "1", "tuesday": "2", "wednesday": "3"}[weekday]
        config["avatar"][day_num], config["weapon"][day_num] = {}, {}
        # 按区域重新排序秘境
        # 约 3.2 版本起，安柏计划上游蒙德武器秘境返回的城市 ID 异常，手动纠正为 1
        config_order = sorted(
            domains,
            key=lambda x: (
                1
                if domains[x]["name"] in ["炼武秘境：水光之城", "炼武秘境：深没之谷", "炼武秘境：渴水的废都"]
                else domains[x]["city"]
            ),
        )
        # 遍历秘境填充对应的角色/武器数据
        for domain_key in config_order:
            if "精通秘境" in domains[domain_key]["name"]:
                item_type, trans = "avatar", avatar_res["items"]
            else:  # "炼武秘境" in domains[domain_key]["name"]
                item_type, trans = "weapon", weapon_res["items"]
            material_id = str(domains[domain_key]["reward"][-1])
            material_name = material_res["items"][material_id]["name"]
            use_this = [
                id_str
                for id_str in update_res[item_type]
                if material_id in update_res[item_type][id_str]["items"]
                and id_str.isdigit()  # 排除旅行者 "10000005-anemo" 等
            ]
            # 以 "5琴10000003,5优菈10000051,...,[rank][name][id]" 形式写入配置
            config[item_type][day_num][f"{material_name}-{material_id}"] = ",".join(
                f"{trans[i]['rank']}{trans[i]['name']}{i}" for i in use_this
            )
            # 下载图片
            domain_tasks = [
                download(
                    f"UI_ItemIcon_{material_id}.png",
                    "item",
                    "{}.{}".format(
                        material_id
                        if DL_CFG["item"]["file"] == "id"
                        else material_name
                        if material_name != "？？？"
                        else material_id,
                        DL_CFG["item"]["fmt"],
                    ),
                ),
                *[
                    download(
                        f"{trans[i]['icon']}.png",
                        item_type,
                        # 特殊物品图片重命名为 config 中写入格式（L454）
                        "{}.{}".format(
                            (
                                i
                                if DL_CFG[item_type]["file"] == "id"
                                else trans[i]["name"]
                                if trans[i]["name"] != "？？？"
                                else i
                            )
                            or f"{trans[i]['rank']}{trans[i]['name']}{i}",
                            DL_CFG[item_type]["fmt"],
                        ),
                    )
                    for i in use_this
                ],
            ]
            await asyncio.gather(*domain_tasks)
            domain_tasks.clear()

    # 获取最新周本材料
    logger.debug("周本材料配置更新 & 对应图片下载...")
    weekly_material, weekly_tasks = [], []
    for material_id, material in material_res["items"].items():
        # 筛选周本材料
        if (
            material["rank"] != 5
            or material["type"] != "characterLevelUpMaterial"
            or int(material_id)
            in [
                104104,  # 璀璨原钻
                104114,  # 燃愿玛瑙
                104124,  # 涤净青金
                104134,  # 生长碧翡
                104144,  # 最胜紫晶
                104154,  # 自在松石
                104164,  # 哀叙冰玉
                104174,  # 坚牢黄玉
            ]
        ):
            # 包含计算器素材，但不在此处下载，后续计算时从米游社下载
            continue
        weekly_material.append(material_id)
        if material["icon"]:
            weekly_tasks.append(
                download(
                    f"{material['icon']}.png",
                    "item",
                    "{}.{}".format(
                        material_id
                        if DL_CFG["item"]["file"] == "id"
                        else material["name"]
                        if material["name"] != "？？？"
                        else material_id,
                        DL_CFG["item"]["fmt"],
                    ),
                )
            )

    # 下载最新周本材料图片
    await asyncio.gather(*weekly_tasks)
    weekly_tasks.clear()

    # 固定已知周本的各个材料键名顺序
    config["weekly"] = {
        boss_info[0]: {
            f"{material_res['items'][material_id]['name']}-{material_id}": ""
            for material_id in weekly_material[boss_idx * 3: boss_idx * 3 + 3]
        }
        for boss_idx, boss_info in enumerate(_WEEKLY_BOSS)
    }
    # 未实装周本材料视为 BOSS "？？？" 的产物
    if len(weekly_material) > len(_WEEKLY_BOSS * 3):
        config["weekly"]["？？？"] = {
            f"{material_res['items'][material_id]['name']}-{material_id}": ""
            for material_id in weekly_material[len(_WEEKLY_BOSS * 3):]
        }

    # 从升级材料中查找使用某周本材料的角色
    for avatar_id, avatar in update_res["avatar"].items():
        # 排除旅行者
        if not str(avatar_id).isdigit():
            continue
        # 将角色升级材料按消耗数量重新排序，周本材料 ID 将排在最后一位
        material_id = list(
            {k: v for k, v in sorted(
                avatar["items"].items(), key=lambda i: i[1])}
        )[-1]
        material_name = material_res["items"][material_id]["name"]
        # 确定 config["weekly"] 写入键名，第一层键名为周本 BOSS 名，第二层为 [name]-[id] 材料名
        _boss_idx = weekly_material.index(material_id) // 3
        _boss_name = (
            _WEEKLY_BOSS[_boss_idx][0] if _boss_idx < len(
                _WEEKLY_BOSS) else "？？？"
        )
        _material_name = f"{material_res['items'][material_id]['name']}-{material_id}"
        # 以 "5琴10000003,5迪卢克10000016,...,[rank][name][id]" 形式写入配置
        config["weekly"][_boss_name][_material_name] += "{}{}{}{}".format(
            "," if config["weekly"][_boss_name][_material_name] else "",
            avatar_res["items"][avatar_id]["rank"],
            avatar_res["items"][avatar_id]["name"],
            avatar_id,
        )

    # 判断是否需要更新缓存
    config_file, redraw_daily, redraw_weekly = CONFIG_DIR / "config.json", True, True
    if config_file.exists():
        old_config: Dict = json.loads(config_file.read_text(encoding="UTF-8"))
        redraw_daily = any(
            old_config.get(key) != config[key] for key in ["avatar", "weapon"]
        )
        redraw_weekly = old_config.get("weekly") != config["weekly"]
        # 跳过三星物品环境变量改变，强制重绘每日材料图片
        if old_config.get("skip_3", True) != config["skip_3"]:
            redraw_daily = True
    # 更新每日材料图片缓存
    if redraw_daily:
        logger.debug("每日材料图片缓存生成...")
        daily_draw_tasks = [
            draw_materials(config, ["avatar", "weapon"], day) for day in [1, 2, 3]
        ]
        await asyncio.gather(*daily_draw_tasks)
        daily_draw_tasks.clear()
    # 更新周本材料图片缓存
    if redraw_weekly:
        logger.debug("周本材料图片缓存生成...")
        bosses_names = WEEKLY_BOSS if config["weekly"].get(
            "？？？") else _WEEKLY_BOSS
        bosses_key = [b[0] for b in bosses_names]
        await draw_materials(config, bosses_key)
    # 清理未上线周本过期的图片缓存
    if not config["weekly"].get("？？？"):
        beta_weekly_pic = CONFIG_DIR / "cache/weekly.？？？.jpg"
        beta_weekly_pic.unlink(missing_ok=True)

    # 补充时间戳
    config["time"] = int(time())
    config_file.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="UTF-8"
    )
    logger.info("原神材料配置更新完成！")

    return DL_CFG, ITEM_ALIAS


def font(size: int) -> ImageFont.FreeTypeFont:
    """Pillow 绘制字体设置"""

    return ImageFont.truetype(
        str(CONFIG_DIR / "draw" / "SmileySans-Oblique.ttf"), size=size  # HYWH-65W
    )


async def circle_corner(mark_img: Image.Image, radius: int = 30) -> Image.Image:
    """图片圆角处理"""

    mark_img = mark_img.convert("RGBA")
    scale, radius = 5, radius * 5
    mark_img = mark_img.resize(
        (mark_img.size[0] * scale, mark_img.size[1] * scale), RESAMPLING
    )
    w, h = mark_img.size
    circle = Image.new("L", (radius * 2, radius * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)
    alpha = Image.new("L", mark_img.size, 255)
    alpha.paste(circle.crop((0, 0, radius, radius)), (0, 0))
    alpha.paste(circle.crop((radius, 0, radius * 2, radius)), (w - radius, 0))
    alpha.paste(
        circle.crop((radius, radius, radius * 2, radius * 2)),
        (w - radius, h - radius),
    )
    alpha.paste(circle.crop((0, radius, radius, radius * 2)), (0, h - radius))
    mark_img.putalpha(alpha)
    return mark_img.resize((int(w / scale), int(h / scale)), RESAMPLING)


async def draw_materials(config: Dict, needs: List[str], day: int = 0) -> Path:
    """原神秘境材料图片绘制"""

    cache_dir = CONFIG_DIR / "cache"
    is_weekly, img_and_path = day == 0, []
    rank_bg = {
        "3": Image.open(CONFIG_DIR / "draw/bg3.140.png"),
        "4": Image.open(CONFIG_DIR / "draw/bg4.140.png"),
        "5": Image.open(CONFIG_DIR / "draw/bg5.140.png"),
    }
    for need in needs:
        raw_config = config["weekly" if is_weekly else need][
            need if is_weekly else str(day)
        ]
        draw_config = {  # 剔除 3 星武器
            key: ",".join(s for s in value.split(
                ",") if not SKIP_THREE or s[0] != "3")
            for key, value in dict(raw_config).items()
            if value
        }

        # 计算待绘制图片的宽度
        title = (
            need
            if is_weekly
            else {1: "周一/周四 {}材料", 2: "周二/周五 {}材料", 3: "周三/周六 {}材料"}[day].format(
                "天赋培养" if need == "avatar" else "武器突破"
            )
        )
        title_bbox = font(50).getbbox(title)
        total_width = max(
            title_bbox[-2] + 50,
            max(
                [(font(40).getlength(_key.split("-")[0]) + 150)
                 for _key in draw_config]
            ),
            max([len(draw_config[_key].split(",")[:6])
                for _key in draw_config])
            * (170 + 10)
            + 10,
        )

        # 计算待绘制图片的高度，每行绘制 6 个角色或武器
        line_cnt = sum(
            ceil(len(draw_config[_key].split(",")) / 6) for _key in draw_config
        )
        total_height = 150 + len(draw_config) * 90 + line_cnt * (160 + 40 + 20)

        # 开始绘制！
        img = Image.new("RGBA", (int(total_width), total_height), "#FBFBFB")
        drawer = ImageDraw.Draw(img)

        # 绘制标题
        drawer.text(
            (int((total_width - title_bbox[-2]) / 2),
             int((150 - title_bbox[-1]) / 2)),
            title,
            fill="black",
            font=font(50),
            stroke_fill="grey",
            stroke_width=2,
        )

        # 绘制每个分组
        startH = 150
        for key in draw_config:
            # 绘制分组所属材料的图片
            key_name, key_id = key.split("-")
            try:
                _key_icon = deepcopy(rank_bg["4" if need == "avatar" else "5"])
                _key_icon_path = DL_CFG["item"]["dir"] / "{}.{}".format(
                    key_id
                    if DL_CFG["item"]["file"] == "id"
                    else key_name
                    if key_name != "？？？"
                    else key_id,
                    DL_CFG["item"]["fmt"],
                )
                _key_icon_img = Image.open(
                    _key_icon_path).resize((140, 140), RESAMPLING)
                _key_icon.paste(_key_icon_img, (0, 0), _key_icon_img)
                _key_icon = (await circle_corner(_key_icon, radius=30)).resize(
                    (80, 80), RESAMPLING
                )
                img.paste(_key_icon, (25, startH), _key_icon)
            except:  # noqa: E722
                pass
            # 绘制分组所属材料的名称
            ImageDraw.Draw(img).text(
                (125, startH + int((80 - font(40).getbbox("高")[-1]) / 2)),
                key_name,
                font=font(40),
                fill="#333",
            )

            # 绘制当前分组的所有角色/武器
            startH += 90
            draw_X, draw_Y, cnt = 10, startH, 0
            draw_order = sorted(
                draw_config[key].split(","), key=lambda x: x[0], reverse=True
            )
            for item in draw_order:
                if match(r"^[0-9][\u3000-\u9fff]+[0-9]{5,}$", item):
                    # 5雷电将军10000052,5八重神子10000058,...
                    _split = -5 if need == "weapon" else -8
                    rank, name, this_id = item[0], item[1:_split], item[_split:]
                else:
                    rank = 0
                    name = this_id = item
                # 角色/武器图片
                try:
                    _dl_cfg_key = "avatar" if need not in [
                        "avatar", "weapon"] else need
                    _icon = (
                        deepcopy(rank_bg[str(rank)])
                        if rank
                        else Image.new("RGBA", (140, 140), "#818486")
                    )
                    _icon_path = DL_CFG[_dl_cfg_key]["dir"] / "{}.{}".format(
                        this_id if DL_CFG[_dl_cfg_key]["file"] == "id" else name,
                        DL_CFG[_dl_cfg_key]["fmt"],
                    )
                    _icon_img = Image.open(_icon_path).resize(
                        (140, 140), RESAMPLING)
                    _icon.paste(_icon_img, (0, 0), _icon_img)
                    _icon = (await circle_corner(_icon, radius=10)).resize(
                        (150, 150), RESAMPLING  # 140
                    )
                    img.paste(_icon, (draw_X + 10, draw_Y + 10), _icon)
                except:  # noqa: E722
                    pass
                # 角色/武器名称
                name_bbox = font(30).getbbox(name)
                ImageDraw.Draw(img).text(
                    (
                        int(draw_X + (170 - name_bbox[-2]) / 2),
                        int(draw_Y + 160 + (40 - name_bbox[-1]) / 2),
                    ),
                    name,
                    font=font(30),
                    fill="#333",
                )
                # 按照 6 个角色/武器一行绘制
                draw_X += 170 + 10
                cnt += 1
                if cnt == 6:
                    draw_X, cnt = 10, 0
                    draw_Y += 160 + 40 + 20

            # 一组角色/武器绘制完毕
            startH += (160 + 40 + 20) * \
                ceil(len(draw_config[key].split(",")) / 6)

        # 全部绘制完毕，保存图片
        cache_file = cache_dir / (
            f"weekly.{need}.jpg" if is_weekly else f"daily.{day}.{need}.jpg"
        )
        img.convert("RGB").save(cache_file)
        logger.debug(
            f"{'周本' if is_weekly else '每日'}材料图片生成完毕 {cache_file.name}")
        img_and_path.append([img, cache_file])

    # 仅有一张图片时直接返回
    if len(img_and_path) == 1:
        return img_and_path[0][1]

    # 存在多张图片时横向合并
    width = sum([i[0].size[0] for i in img_and_path]) + \
        (len(img_and_path) - 1) * 25
    _weight, height = 0, max([i[0].size[1] for i in img_and_path])
    merge = Image.new("RGBA", (width, height), "#FBFBFB")
    for i in img_and_path:
        merge.paste(i[0], (_weight, 0), i[0])
        _weight += i[0].size[0] + 25
    merge_file = cache_dir / \
        ("weekly.all.jpg" if is_weekly else f"daily.{day}.all.jpg")
    merge.convert("RGB").save(merge_file)
    logger.info(f"{'周本' if is_weekly else '每日'}材料图片合并完毕 {merge_file.name}")
    return merge_file


async def draw_calculator(name: str, target: Dict, calculate: Dict) -> Union[bytes, str]:
    """原神计算器材料图片绘制"""
    height = sum(80 + ceil(len(v) / 2) * 70 + 20 for _,
                 v in calculate.items() if v) + 20
    img = Image.new("RGBA", (800, height), "#FEFEFE")
    drawer = ImageDraw.Draw(img)

    icon_bg = Image.new("RGBA", (100, 100))
    ImageDraw.Draw(icon_bg).rounded_rectangle(
        (0, 0, 100, 100), radius=10, fill="#a58d83", width=0
    )
    icon_bg = icon_bg.resize((50, 50), RESAMPLING)

    draw_X, draw_Y = 20, 20
    for key, consume in calculate.items():
        if not consume:
            continue

        # 背景纯色
        block_height = 80 + ceil(len(consume) / 2) * 70
        drawer.rectangle(
            ((20, draw_Y), (800 - 20 - 1, draw_Y + block_height)),
            fill="#f1ede4",
            width=0,
        )

        # 标题
        if key == "avatar_consume":
            title_left, title_right = (
                f"{name}·角色消耗",
                f"Lv.{target['avatar_level_current']} >>> Lv.{target['avatar_level_target']}",
            )
        elif key == "avatar_skill_consume":
            title_left, title_right = f"{name}·天赋消耗", "   ".join(
                f"Lv.{_skill['level_current']}>{_skill['level_target']}"
                for _skill in target["skill_list"]
                if _skill["level_current"] != _skill["level_target"]
            )
        elif key == "weapon_consume":
            title_left, title_right = (
                f"{name}·升级消耗",
                f"Lv.{target['weapon']['level_current']} >>> Lv.{target['weapon']['level_target']}",
            )
        else:
            raise ValueError("材料计算器无法计算圣遗物消耗")
        # 左侧标题
        drawer.text(
            (draw_X + 40, int(draw_Y + (80 - font(40).getbbox("高")[-1]) / 2)),
            title_left,
            fill="#8b7770",
            font=font(40),
        )
        # 右侧标题字体大小自适应
        _size = 40 - len(title_right.split("   ")) * 3
        _text_width, _text_height = font(_size).getbbox(title_right)[-2:]
        drawer.text(
            (800 - 70 - _text_width, int(draw_Y + (80 - _text_height) / 2)),
            title_right,
            fill="#8b7770",
            font=font(_size),
        )

        # 材料
        is_left, _draw_X, _draw_Y = True, draw_X + 30, draw_Y + 80 + 10
        for cost in consume:
            # 图标背景
            img.paste(icon_bg, (_draw_X, _draw_Y), icon_bg)
            # 图标
            _icon_path = DL_CFG["item"]["dir"] / "{}.{}".format(
                cost["id"] if DL_CFG["item"]["file"] == "id" else cost["name"],
                DL_CFG["item"]["fmt"],
            )
            _icon_img = Image.open(_icon_path).resize((50, 50), RESAMPLING)
            img.paste(_icon_img, (_draw_X, _draw_Y), _icon_img)
            # 名称 × 数量
            cost_str = f"{cost['name']} × {cost['num']}"
            drawer.text(
                (_draw_X + 65, _draw_Y +
                 int((50 - font(30).getbbox(cost_str)[-1]) / 2)),
                cost_str,
                fill="#967b68",
                font=font(30),
            )
            if is_left:
                _draw_X += 370
            else:
                _draw_X = draw_X + 30
                _draw_Y += 70
            is_left = not is_left

        draw_Y += block_height + 20

    buf = BytesIO()
    img.save(buf, format="PNG", quality=100)
    return buf.getvalue()


async def startup(config):
    logger.info('[资源文件下载] 正在检查与下载缺失的资源文件，可能需要较长时间，请稍等')
    return await update_config(config)
