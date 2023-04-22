from typing import List
import pandas as pd
from pandas import DataFrame, read_csv, concat
from datetime import datetime
from re import match
from pathlib import Path
from pandas.errors import EmptyDataError

class NoticeItem:
    def __init__(self, name: str, start_date, end_date):
        self.format_str = "%Y-%m-%d %H:%M"
        self._name = name
        self._start_date = self.time_parse(start_date)
        self._end_date = self.time_parse(end_date)

    @property
    def name(self):
        return self._name

    @property
    def start_date(self):
        return self._start_date

    @property
    def end_date(self):
        return self._end_date

    @property
    def priority(self):
        return self._priority

    @property
    def time_left(self):
        end = datetime.strptime(self.end_date, self.format_str)
        today = datetime.today()
        time_diff = (end - today)
        days = time_diff.days
        hours = time_diff.total_seconds() // 3600
        minutes = (time_diff.total_seconds() % 3600) // 60
        total_minutes = time_diff.total_seconds() // 60
        return f"{days}天{hours}时{minutes}分", total_minutes

    @property
    def percentage(self):
        start = datetime.strptime(self.start_date, self.format_str)
        end = datetime.strptime(self.end_date, self.format_str)
        today = datetime.today()
        time_len = (end - start)
        time_spent = (today - start)
        return int(time_spent / time_len * 100)

    def time_parse(self, _time):
        if _time is None:
            _time = datetime.today()
        elif isinstance(_time, datetime):
            _time = _time.strftime(self.format_str)
        else:
            try:
                _time = datetime.strptime(_time, self.format_str)
            except ValueError:
                raise ValueError("Time parsing failed.")
        return _time

    def __lt__(self, other):
        if not isinstance(other, NoticeItem):
            raise ValueError("{other} is not a NoticeItem.")
        if self.end_date != other.end_date:
            return self.end_date < other.end_date
        elif self.priority != other.priority:
            return self.start_date < other.start_date
        else:
            return self.name < other.name

    def __eq__(self, other):
        if not isinstance(other, NoticeItem):
            raise ValueError("{other} is not a NoticeItem.")
        if (self.name == other.name and
                self.start_date == other.start_date and
                self.end_date == other.end_date):
            return True
        else:
            return False

    def __str__(self):
        return self._name + ',' + self._start_date + ',' + self._end_date

    def to_dict(self):
        return {'name': self._name,
                'start_date': self._start_date,
                'end_date': self._end_date}


class TodoList:
    def __init__(self, user: str, path: str):
        self._list = list()
        self._user = user
        self._path = path
        self._format_str = "%Y-%m-%d %H:%M"
        try:
            df = read_csv(self.path + '/' + user + ".csv")
        except FileNotFoundError or EmptyDataError:
            df = None
        if df is not None:
            for index, row in df.iterrows():
                token = NoticeItem(row['name'], row['start_date'],
                                  row['end_date'], self.format_str)
                self._list.append(token)

    @property
    def size(self):
        return len(self._list)

    @property
    def path(self):
        return self._path

    @property
    def format_str(self):
        return self._format_str

    def add_data(self, token: NoticeItem) -> bool:
        if token in self._list:
            return False
        else:
            self._list.append(token)
            self.write_data()
            return True

    def remove_data(self, name: str) -> int:
        list_len = len(self._list)
        self._list = [token for token in self._list if not match(name, token.name)]
        if list_len > len(self._list):
            self.write_data()
        return list_len - len(self._list)

    def change_data(self, name: str, slot: str, content: str):
        count = 0
        for token in self._list:
            if match(name, token.name) is not None:
                setattr(token, slot, content)
                count += 1
        self.write_data()
        return count

    def write_data(self):
        self._list.sort()
        if len(self._list) == 0:
            df = pd.DataFrame(columns=['name', 'start_date', 'end_date'])
            df.to_csv(self.path + '/' + self._user + '.csv', index=False)

        else:
            df = DataFrame()
            for token in self._list:
                tmp = DataFrame([token.to_dict()])
                df = concat([df, tmp], axis=0, ignore_index=True)
            df.to_csv(self.path + '/' + self._user + '.csv', index=False)

    async def get_img(self):
        list_by_date: List[(str, int, List[NoticeItem])] = list()
        now_date = ""
        date_count = 0
        now_date_token: List[NoticeItem] = list()
        for token in self._list:
            if token.end_date != now_date:
                date_count += 1
                now_date = token.end_date
                now_date_token:List[NoticeItem] = list()
                list_by_date.append((now_date, token.time_left[0], now_date_token))
            now_date_token.append(token)

        content_width = 500
        content_height = 76.4 + \
                         34 * date_count + \
                         64 * len(self._list)
        # estimated title_height + date_height + list_token_height
        img_width = content_width / 0.618
        img_height = content_height / 0.618
        template_path = str(Path(__file__).parent / "templates")
        img = await template_to_pic(template_path=template_path,
                                    template_name="template.html",
                                    templates={
                                        "list_by_date": list_by_date,
                                    },
                                    pages={
                                        "viewport": {"width": int(img_width), "height": int(img_height)},
                                        "base_url": f"file://{template_path}"
                                    },
                                    )
        return img
