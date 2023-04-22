import json
import copy
import asyncio
import random
from pathlib import Path
from datetime import datetime, timedelta
from .build import TODO
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.data_store import get_res_path
from gsuid_core.segment import MessageSegment
from gsuid_core.gss import gss
from gsuid_core.logger import logger
from .utils import get_time, template_to_pic
from typing import Optional, Literal, Tuple
from ..utils import BaseBrowser


class NoticeItem:
    def __init__(self, name: str, start_date, end_date, group):
        self.format_str = "%Y-%m-%d %H:%M"
        self.name = name
        self.group = group
        self.start_date = self.time_parse(start_date)
        self.end_date = self.time_parse(end_date)
        self.check_done()

    @property
    def time_left(self):
        today = datetime.today()
        time_diff = (self.end_date - today)
        days = time_diff.days
        hours = int(time_diff.seconds // 3600)
        minutes = int((time_diff.seconds % 3600) // 60)
        return days, hours, minutes

    @property
    def percentage(self):
        today = datetime.today()
        time_len = (self.end_date - self.start_date)
        time_spent = (today - self.start_date)
        return int(time_spent / time_len * 100)

    def time_parse(self, _time):
        if _time is None:
            _time = datetime.today()
        if isinstance(_time, datetime):
            return _time
        return datetime.strptime(_time, self.format_str)

    def update_name(self, new_value):
        self.name = new_value

    def update_end(self, new_value):
        self.end_date = new_value

    def check_push(self, max_minutes):
        today = datetime.today()
        self.done = today >= self.end_date
        today = datetime.today()
        time_diff = (self.end_date - today)
        minutes = time_diff.seconds // 60
        if not self.done and minutes <= max_minutes:
            return True
        return False

    def check_done(self):
        today = datetime.today()
        self.done = today >= self.end_date + timedelta(minutes=1)
        return self.done

    def __eq__(self, other):
        if not isinstance(other, NoticeItem):
            raise ValueError("{other} is not a NoticeItem.")
        if (self.name == other.name and self.group == other.group and
                self.start_date == other.start_date and
                self.end_date == other.end_date):
            return True
        else:
            return False

    def to_dict(self):
        return {
            'name': self.name,
            'start_time': datetime.strftime(self.start_date, self.format_str),
            'end_time': datetime.strftime(self.end_date, self.format_str),
            'group': self.group
        }

    def __str__(self):
        return f"name: {self.name}, start: {datetime.strftime(self.start_date, self.format_str)}" \
            + f"end: {datetime.strftime(self.end_date, self.format_str)}, left: {self.time_left}"


@TODO.register_module()
class ToDoModel:
    def __init__(self, config=None):
        self.config = copy.deepcopy(config)
        self.write_file: Path = get_res_path('GsChat')/'todo.json'
        self.user_map = {}
        self.user2bot = {}
        self.chatgpt_fn = None
        self.push_time = config.push_time
        if self.push_time < 0:
            self.push_time = 0
        self.browser = BaseBrowser()
        self.init_data()

    def init_data(self):
        if not self.write_file.exists():
            with self.write_file.open(mode='w') as f:
                f.write("{}")
        datas = json.loads(open(self.write_file, 'r').read())
        for bot_id in datas:
            if bot_id not in self.user_map:
                self.user_map[bot_id] = {}
            for user_id in datas[bot_id]:
                if user_id not in self.user_map[bot_id]:
                    self.user_map[bot_id][user_id] = []
                for item in datas[bot_id][user_id]:
                    name = item['name']
                    start_date = item['start_time']
                    end_date = item['end_time']
                    group = bool(item['group'])
                    notice = NoticeItem(name, start_date, end_date, group)
                    self.user_map[bot_id][user_id].append(notice)

        self.check_all()

    def check_all(self):
        res = {}
        for bot_id in self.user_map:
            if bot_id not in res:
                res[bot_id] = {}
            for user_id in self.user_map[bot_id]:
                if user_id not in res[bot_id]:
                    res[bot_id][user_id] = []
                notices = self.user_map[bot_id][user_id]
                notice_copy = copy.deepcopy(notices)
                for notice in notice_copy:
                    notice.check_done()
                    if not notice.done:
                        res[bot_id][user_id].append(notice.to_dict())
                    else:
                        self.user_map[bot_id][user_id].remove(notice)
                if not self.user_map[bot_id][user_id]:
                    del res[bot_id][user_id]

        with self.write_file.open(mode='w') as f:
            f.write(json.dumps(res, ensure_ascii=False, indent=4))

        return self.user_map

    def set_chatgpt(self, chatgpt_fn):
        self.chatgpt_fn = chatgpt_fn

    async def add_todo(self, bot: Bot, event: Event):
        text = event.text.strip()
        bot_id = bot.bot_id
        is_group = event.user_type != 'direct'
        user_id = event.group_id if is_group else event.user_id

        exceed_time, name, status = await get_time(text, self.chatgpt_fn)

        if not status:
            await bot.send(f'提醒解析失败，请调整输入后尝试.')
            return

        notice = NoticeItem(name, datetime.today(), exceed_time, is_group)
        if notice.done:
            await bot.send(f"当前提醒[{name}]时间已经过了，添加失败")
            return

        number = await self.add_to_list(user_id, bot_id, notice)
        self.check_all()
        if number:
            await bot.send(f"已将[{name}]加入清单，ddl为{exceed_time}。\n当前共{number}项待办。")
            img = await self.get_list_img(user_id, bot_id)
            await bot.send(img)
        else:
            await bot.send(f"[{name}]已在清单中。")

    async def remove_todo(self, bot: Bot, event: Event):
        name = event.text.strip()
        bot_id = bot.bot_id
        is_group = event.user_type != 'direct'
        user_id = event.group_id if is_group else event.user_id
        status, number = await self.remove_from_list(user_id, bot_id, name)
        self.check_all()
        if not status:
            await bot.send(f"不存在名为[{name}]的提醒。")
        else:
            img = await self.get_list_img(user_id)
            await bot.send(f"已删除[{name}]，剩余待办{number}项。")
            await bot.send(img)

    async def send_pic(self, bot: Bot, event: Event):
        user_id = event.user_id if event.user_type == 'direct' else event.group_id
        bot_id = bot.bot_id
        self.check_all()
        img = await self.get_list_img(user_id, bot_id)
        await bot.send(MessageSegment.image(img))

    async def send_todo(self):
        for bot_id in self.user_map:
            try:
                for BOT_ID in gss.active_bot:
                    bot = gss.active_bot[BOT_ID]
                    for user_id in self.user_map[bot_id]:
                        if self.user_map[bot_id][user_id]:
                            user_type = 'group' if self.user_map[bot_id][user_id][0].group else 'direct'
                            send_flag = False
                            for notice in self.user_map[bot_id][user_id]:
                                if notice.check_push(self.push_time):
                                    send_flag = True
                                    break
                            if send_flag:
                                user_notices = await self.get_list_img(user_id, bot_id)
                                await bot.target_send(
                                    user_notices, user_type, user_id, bot_id, '', ''
                                )
                                await asyncio.sleep(random.uniform(1, 3))
            except Exception as e:
                logger.exception(e)

    async def get_list(self, user_id, bot_id):
        if bot_id not in self.user_map or \
                user_id not in self.user_map[bot_id]:
            if bot_id not in self.user_map:
                self.user_map[bot_id] = {}
            self.user_map[bot_id][user_id] = []

        return self.user_map[bot_id][user_id]

    async def add_to_list(self, user_id, bot_id, notice):
        user_list = await self.get_list(user_id, bot_id)

        for item in user_list:
            if notice.name == item.name:
                return 0

        user_list.append(notice)
        return len(user_list)

    async def remove_from_list(self, user_id, bot_id, name):
        user_list = await self.get_list(user_id, bot_id)

        user_copy = copy.deepcopy(user_list)
        remove = False
        for notice in user_copy:
            if notice.name == name:
                user_list.remove(notice)
                remove = True

        return remove, len(user_list)

    async def get_list_img(self, user_id, bot_id):
        list_by_date = {}
        user_list = await self.get_list(user_id, bot_id)
        for notice in user_list:
            date = notice.end_date.strftime("%m-%d")
            time = notice.end_date.strftime("%H:%M")
            days, hours, minutes = notice.time_left
            ddl = f'{days}d{hours}h{minutes}m'
            if date not in list_by_date:
                list_by_date[date] = []
            list_by_date[date].append(
                (time, ddl, notice.name, notice.percentage))

        if not list_by_date:
            return '您目前没有待办任务哦'

        result = '任务清单\n'
        sorted_dates = sorted(list_by_date)
        render_list = []
        date_count = len(sorted_dates)
        total_datas = 0
        for date in sorted_dates:
            render_list.append((date, list_by_date[date]))
            total_datas += len(list_by_date[date])

        browser = await self.browser.get_browser()

        try:
            content_width = 500
            content_height = 76.4 + \
                34 * date_count + \
                64 * total_datas
            # estimated title_height + date_height + list_token_height
            img_width = content_width / 0.618
            img_height = content_height / 0.618
            template_path = str(Path(__file__).parent / "templates")
            img = await template_to_pic(template_path=template_path,
                                        template_name="template.html",
                                        templates={
                                            "list_by_date": render_list,
                                        },
                                        browser=browser,
                                        pages={
                                            "viewport": {"width": int(img_width), "height": int(img_height)},
                                            "base_url": f"file://{template_path}"
                                        }
                                        )
            return img
        except Exception as e:
            logger.error(f'render notice error {str(e)}')
            return None
