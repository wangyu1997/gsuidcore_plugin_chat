import copy
import json
from pathlib import Path
from datetime import datetime

from gsuid_core.logger import logger
from gsuid_core.data_store import get_res_path

from .build import BILLING
from ..utils import BaseBrowser, template_to_pic


class BillingItem:
    def __init__(
        self, name: str, date=None, money=0.0, payer="", customers=[]
    ):
        self.format_str = "%Y-%m-%d %H:%M"
        self.name = name
        self.money = money
        self.date = self.time_parse(date)
        self.payer = payer
        self.customers = customers

    def time_parse(self, _time):
        if _time is None:
            _time = datetime.now()
        if isinstance(_time, datetime):
            return _time
        return datetime.strptime(_time, self.format_str)

    @property
    def day(self):
        return datetime.strftime(self.date, "%Y-%m-%d")

    @property
    def time(self):
        return datetime.strftime(self.date, "%H:%M")

    @classmethod
    def get_from_json(cls, json_data):
        return cls(
            json_data["name"],
            json_data["date"],
            json_data["money"],
            json_data["payer"],
            json_data["customers"].split(","),
        )

    def to_dict(self):
        return {
            "name": self.name,
            "date": datetime.strftime(self.date, self.format_str),
            "money": self.money,
            "payer": self.payer,
            "customers": ",".join(self.customers),
        }


@BILLING.register_module()
class BillingModel:
    def __init__(self, config=None):
        self.config = copy.deepcopy(config)
        self.write_file: Path = get_res_path("GsChat") / "billing.json"
        self.data = {}
        self.name_map = {}
        self.browser = BaseBrowser()
        self.init_data()

    def init_data(self):
        if not self.write_file.exists():
            with self.write_file.open(mode="w") as f:
                f.write("{}")
        datas = json.loads(open(self.write_file, "r").read())
        for group_id in datas:
            if group_id not in self.data:
                self.data[group_id] = []
            for item in datas[group_id]["data"]:
                billing_item = BillingItem.get_from_json(item)
                self.data[group_id].append(billing_item)
            self.name_map[group_id] = datas[group_id]["name_map"]

    async def set_alias(self, group_id, wx_id, text):
        print(self.name_map)
        if group_id not in self.name_map:
            self.name_map[group_id] = {}
        self.name_map[group_id][wx_id] = text
        await self.write_back(group_id)

    async def write_back(self, group_id):
        datas = json.loads(open(self.write_file, "r").read())
        data_json = []
        for item in self.data[group_id]:
            data_json.append(item.to_dict())
        if group_id not in datas:
            datas[group_id] = {}
        datas[group_id]["data"] = data_json
        if group_id not in self.name_map:
            self.name_map[group_id] = {}
        datas[group_id]["name_map"] = self.name_map[group_id]

        with self.write_file.open(mode="w") as f:
            f.write(json.dumps(datas, ensure_ascii=False, indent=4))

    def alias(self, group_id, username):
        if (
            group_id not in self.name_map
            or username not in self.name_map[group_id]
        ):
            return username

        return self.name_map[group_id][username]

    async def renew(self, group_id):
        self.data[group_id] = []
        await self.write_back(group_id)

    async def add_new(self, group_id, name, money, payer, customers):
        bill = BillingItem(
            name, money=money, payer=payer, customers=customers
        )
        self.data[group_id].append(bill)
        await self.write_back(group_id)
        return f"名称: {bill.name}\n时间: {bill.time}\n金额: {bill.money}\n支出者: {self.alias(group_id, bill.payer)}\n均摊者: {','.join([self.alias(group_id, i) for i in bill.customers])}\n"

    async def discard(self, group_id):
        if len(self.data[group_id]) == 0:
            return None
        bill = self.data[group_id][-1]
        self.data[group_id] = self.data[group_id][:-1]
        await self.write_back(group_id)
        return f"名称: {bill.name}\n时间: {bill.time}\n金额: {bill.money}\n支出者: {self.alias(group_id, bill.payer)}\n均摊者: {','.join([self.alias(group_id, i) for i in bill.customers])}\n"

    async def output_bill(self, group_id):
        if group_id not in self.data:
            return None
        billings = self.data[group_id]
        output_dict = {}
        for bill in billings:
            if bill.day not in output_dict:
                output_dict[bill.day] = []
            output_dict[bill.day].append(bill)

        res = "开销账单\n\n"
        sorted_day = sorted(output_dict)
        for day in sorted_day:
            billings = output_dict[day]
            res += f"{day}\n" + "-" * 30 + "\n"
            for idx, bill in enumerate(
                sorted(billings, key=lambda x: x.time)
            ):
                res += f"名称: {bill.name}\n时间: {bill.time}\n金额: {bill.money}\n支出者: {self.alias(group_id, bill.payer)}\n均摊者: {','.join([self.alias(group_id, i) for i in bill.customers])}\n"
                if idx < len(billings) - 1:
                    res += "\n"
            res += "-" * 30 + "\n"
        img = await self.text_to_img(res)
        return img

    async def checkout(self, group_id):
        res = "结算开销\n\n"
        user_pay = {}
        if group_id in self.data:
            for bill in self.data[group_id]:
                for user in bill.customers:
                    if user not in user_pay:
                        user_pay[user] = {}
                    if bill.payer not in user_pay[user]:
                        user_pay[user][bill.payer] = 0
                    user_pay[user][bill.payer] += bill.money / (
                        len(bill.customers) + 1
                    )

        for customer in user_pay:
            data = user_pay[customer]
            for payer in data:
                if payer in user_pay and customer in user_pay[payer]:
                    if user_pay[payer][customer] >= data[payer]:
                        user_pay[payer][customer] -= data[payer]
                        user_pay[customer][payer] = 0
                    else:
                        user_pay[customer][payer] -= user_pay[payer][
                            customer
                        ]
                        user_pay[payer][customer] = 0

        for customer in user_pay:
            data = user_pay[customer]
            payer_text = ""
            for payer in data:
                if data[payer] > 0:
                    payer_text += (
                        f"收款人: {self.alias(group_id, payer)} \n"
                    )
                    payer_text += f"收款金额: {data[payer]:.2f} \n\n"
            if payer_text:
                res += (
                    f"转账人: {self.alias(group_id, customer)}\n\n"
                    + payer_text
                    + "-" * 30
                    + "\n"
                )

        img = await self.text_to_img(res)
        return img

    async def today_bill(self, group_id):
        if group_id not in self.data:
            return None
        billings = self.data[group_id]
        output_dict = {}
        for bill in billings:
            if bill.day not in output_dict:
                output_dict[bill.day] = []
            output_dict[bill.day].append(bill)

        res = "开销账单\n\n"
        sorted_day = sorted(output_dict)
        today = datetime.now()
        today = datetime.strftime(today, "%Y-%m-%d")
        if today in sorted_day:
            billings = output_dict[today]
            res += f"{today}\n" + "-" * 30 + "\n"
            for idx, bill in enumerate(
                sorted(billings, key=lambda x: x.time)
            ):
                res += f"名称: {bill.name}\n时间: {bill.time}\n金额: {bill.money}\n支出者: {self.alias(group_id, bill.payer)}\n均摊者: {','.join([self.alias(group_id, i) for i in bill.customers])}\n"
                if idx < len(billings) - 1:
                    res += "\n"
            res += "-" * 30 + "\n"
        img = await self.text_to_img(res)
        return img

    async def my_bill(self, group_id, username):
        if group_id not in self.data:
            return None
        billings = self.data[group_id]
        output_dict = {}
        for bill in billings:
            if bill.day not in output_dict:
                output_dict[bill.day] = []
            output_dict[bill.day].append(bill)

        sorted_day = sorted(output_dict)
        nickname = self.alias(group_id, username)
        res = f"{nickname}的支出\n\n"
        for day in sorted_day:
            billings = output_dict[day]
            day_res = ""
            for idx, bill in enumerate(
                sorted(billings, key=lambda x: x.time)
            ):
                if bill.payer == username:
                    day_res += f"名称: {bill.name}\n时间: {bill.time}\n金额: {bill.money}\n均摊者: {','.join([self.alias(group_id, i) for i in bill.customers])}\n"
                    if idx < len(billings) - 1:
                        day_res += "\n"
            if day_res:
                res += f"{day}\n" + "-" * 30 + "\n" + day_res
                res += "-" * 30 + "\n"

        res += f"\n\n{nickname}的均摊\n\n"
        for day in sorted_day:
            billings = output_dict[day]
            day_res = ""
            for idx, bill in enumerate(
                sorted(billings, key=lambda x: x.time)
            ):
                if bill.payer in bill.customers:
                    day_res += f"名称: {bill.name}\n时间: {bill.time}\n金额: {bill.money}\n支出者: {self.alias(group_id, bill.payer)}\n均摊者: {','.join([self.alias(group_id, i) for i in bill.customers])}\n"
                    if idx < len(billings) - 1:
                        day_res += "\n"
            if day_res:
                res += f"{day}\n" + "-" * 30 + "\n" + day_res
                res += "-" * 30 + "\n"
        img = await self.text_to_img(res)
        return img

    async def text_to_img(self, text):
        browser = await self.browser.get_browser()
        try:
            content_width = 300
            content_height = 13 * len(text.split("\n"))
            text = text.replace("\n", "<br/>")
            # estimated title_height + date_height + list_token_height
            img_width = content_width / 0.618
            img_height = content_height / 0.618
            template_path = str(Path(__file__).parent / "templates")
            img = await template_to_pic(
                template_path=template_path,
                template_name="template.html",
                templates={
                    "text": text,
                },
                browser=browser,
                pages={
                    "viewport": {
                        "width": int(img_width),
                        "height": int(img_height),
                    },
                    "base_url": f"file://{template_path}",
                },
            )
            return img
        except Exception as e:
            logger.error(f"render notice error {str(e)}")
            return None
