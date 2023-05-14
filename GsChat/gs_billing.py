import copy
from .billing import BILLING, BillingModel
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.segment import MessageSegment
from gsuid_core.models import Event
from gsuid_core.logger import logger
from .config import config

bill_sv = SV("账单事项", pm=6, priority=9, enabled=True, black_list=[], area="GROUP")
bill_admin_sv = SV("账单管理员", pm=1, priority=9, enabled=True, black_list=[], area="GROUP")


bill_model: BillingModel = BILLING.build(config.other.billing)


@bill_sv.on_fullmatch(
    ("查看账单"),
    block=True,
)
async def get_billing(bot: Bot, event: Event):
    group_id = event.group_id
    res = await bill_model.output_bill(group_id)
    if not res:
        await bot.send("当前群组还没有账单,请输入创建账单初始化.")
    else:
        await bot.send(MessageSegment.image(res))


@bill_sv.on_fullmatch(
    ("今日账单"),
    block=True,
)
async def today_billing(bot: Bot, event: Event):
    group_id = event.group_id
    res = await bill_model.today_bill(group_id)
    if not res:
        await bot.send("当前群组还没有账单,请输入创建账单初始化.")
    else:
        await bot.send(MessageSegment.image(res))


@bill_sv.on_fullmatch(
    ("清算", "结算账单"),
    block=True,
)
async def get_billing(bot: Bot, event: Event):
    group_id = event.group_id
    res = await bill_model.checkout(group_id)
    if not res:
        await bot.send("当前群组还没有账单,请输入创建账单初始化.")
    else:
        await bot.send(MessageSegment.image(res))


@bill_sv.on_fullmatch(
    ("我的账单"),
    block=True,
)
async def my_billing(bot: Bot, event: Event):
    group_id = event.group_id
    user_id = event.user_id
    res = await bill_model.my_bill(group_id, user_id)
    if not res:
        await bot.send("当前群组还没有账单,请输入创建账单初始化.")
    else:
        await bot.send(MessageSegment.image(res))


@bill_sv.on_fullmatch(
    ("创建账单", "重置账单"),
    block=True,
)
async def new_billing(bot: Bot, event: Event):
    group_id = event.group_id
    await bill_model.renew(group_id)
    await bot.send("当前群聊账单创建成功")


@bill_admin_sv.on_fullmatch(
    ("撤销账单"),
    block=True,
)
async def new_billing(bot: Bot, event: Event):
    group_id = event.group_id

    res = await bill_model.discard(group_id)
    if not res:
        await bot.send("撤销上一笔开销失败，可能当前群聊没有开销记录")
    else:
        await bot.send("成功撤销上一笔账单\n账单详情:\n" + res)


@bill_sv.on_keyword(
    ("账单"),
    block=True,
)
async def new_billing(bot: Bot, event: Event):
    group_id = event.group_id
    at_list = event.at_list
    user_id = event.user_id
    text = event.raw_text
    try:
        text = text.split("账单")[1].strip()
    except:
        return
    if not at_list:
        await bot.send("请at需要平摊费用的好友")
    else:
        name, money = text.split(" ")
        try:
            money = float(money.strip())
            res = await bill_model.add_new(group_id, name, money, user_id, at_list)
            await bot.send("当前群聊账单创建成功\n新增开销:\n" + res)
        except Exception as e:
            await bot.send("金额必须为小数")


@bill_sv.on_prefix(
    ("设置昵称", "昵称"),
    block=True,
)
async def my_billing(bot: Bot, event: Event):
    group_id = event.group_id
    if event.at_list:
        user_id = event.at_list[0]
    else:
        user_id = event.user_id
    alias = event.text.strip()
    await bill_model.set_alias(group_id, user_id, alias)
    await bot.target_send(
        f"成功设置您的昵称为: {alias}",
        "group",
        group_id,
        True,
        user_id,
    )
