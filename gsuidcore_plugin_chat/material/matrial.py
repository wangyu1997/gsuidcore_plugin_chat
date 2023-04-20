import copy
from .build import MATERIAL
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger
from typing import Dict, Union
from .utils import *
import asyncio
import threading


@MATERIAL.register_module()
class MaterialModel:
    def __init__(self, config=None):
        super(MaterialModel, self).__init__()
        self.config = copy.deepcopy(config)
        self.UID_HINT = "你还没有绑定过uid哦!\n请使用[绑定uid123456]命令绑定!"
        self.dl_cfg = {}
        self.item_alias = {}
        threading.Thread(target=lambda: asyncio.run(
            self.initail_data(config)), daemon=True).start()

    async def get_uid(self, bot: Bot, event: Event):
        user_id = event.user_id
        bot_id = event.bot_id
        uid = await _get_uid(user_id, bot_id)
        if uid is None:
            return await bot.send(self.UID_HINT)

        return uid

    async def initail_data(self, config):
        self.dl_cfg, self.item_alias = await startup(config)

    async def material_push(self, name: str):
        # 获取不包含触发关键词的消息文本
        arg = name

        # 识别周几，也可以是纯数字
        weekday, timedelta = 0, 0
        week_keys = ["一", "四", "1", "4", "二",
                     "五", "2", "5", "三", "六", "3", "6"]
        for idx, s in enumerate(week_keys):
            if s in arg:
                weekday = idx // 4 + 1
                arg = arg.replace(f"周{s}", "").replace(s, "").strip()
                break
        for idx, s in enumerate(["今", "明", "后"]):
            if s in arg:
                timedelta = idx
                arg = arg.replace(f"{s}天", "").replace(f"{s}日", "").strip()

        # 处理正常指令
        if any(x in arg for x in ["天赋", "角色"]):
            target = "avatar"
        elif any(x in arg for x in ["武器"]):
            target = "weapon"
        elif not arg:
            # 只发送了命令触发词，返回每日总图
            target = "all"
        else:
            # 发送了无法被识别为类型的内容，忽略
            return

        # 获取每日材料图片
        msg = await generate_daily_msg(target, weekday, timedelta)
        return msg
      
      
    async def week_push(self, name:str):
      # 获取不包含触发关键词的消息文本
      arg, target = name, ""
      # 处理输入
      for boss_alias in WEEKLY_BOSS:
          if arg in boss_alias:
              target = boss_alias[0]
              break
      if not arg:
          # 只发送了命令触发词，返回周本总图
          target = "all"
      elif not target:
          # 发送了无法被识别为周本名的内容，忽略
          return
      # 获取周本材料图片
      msg = await generate_weekly_msg(target)
      return msg
    
    
    async def subscribe(self, bot_id: str, event: Event):
        text = event.text
        user_id = event.user_id
        is_delete = "删除" in text or "关闭" in text
        is_group = event.user_type != 'direct'
        action = f"{'d' if is_delete else 'a'}{'g' if is_group else 'p'}"
        action_id = event.group_id if is_group else user_id

        return await sub_helper(action, action_id, bot_id)


    async def daily_push(self):
        cfg = await sub_helper()
        assert isinstance(cfg, Dict)

        msg = await generate_daily_msg("update")
        return msg, cfg




    async def generate_calc_msg(self, name: str, bot: Bot, event: Event) -> Union[bytes, str]:
        """原神计算器材料图片生成入口"""
        # 提取待升级物品 ID 及真实名称
        target_input = name.split(" ", 1)[0]
        target_id, target_name = await get_target(target_input.strip())
        if not target_id:
            return f"无法识别的名称「{target_input}」"
        others = name.lstrip(target_input).strip()

        uid = await self.get_uid(bot, event)
        if not uid:
            return
        # 提取升级范围
        target = await get_upgrade_target(target_id, others, uid)
        if target.get("error"):
            return target["error"]

        # 请求米游社计算器
        logger.info(f"{target_id}: {target}")
        calculate, success = await request_cal(uid, target)
        if success:
            # 下载计算器素材图片
            for key in calculate.keys():
                consume_tasks = [
                    download(
                        i["icon_url"],
                        "mihoyo",
                        f"{i[self.dl_cfg['item']['file']]}.{self.dl_cfg['item']['fmt']}",
                    )
                    for i in calculate[key]
                ]
                logger.info(f"正在下载计算器 {key} 消耗材料的 {len(consume_tasks)} 张图片")
                await asyncio.gather(*consume_tasks)
                consume_tasks.clear()

            # 绘制计算器材料图片
            return await draw_calculator(target_name, target, calculate)
        return None

    async def check_files(self):
        pass
