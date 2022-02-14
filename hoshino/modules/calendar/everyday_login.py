from datetime import datetime
import pytz
import random

from hoshino import Service
from hoshino.typing import CQEvent
from hoshino.util import DailyNumberLimiter, load_config, load_localisation


config = load_config(__file__)
lang = config["LANG"]
L = load_localisation(__file__)[lang]


sv = Service("calendar-everyday-login", help_=L["HELP_EVERYDAY_LOGIN"], enable_on_default=False)
lmt = DailyNumberLimiter(1)


map_weekday = "一二三四五六日"


@sv.on_fullmatch(*L["CMD_EVERYDAY_LOGIN"], only_to_me=True)
async def everyday_login(bot, ev: CQEvent):
    uid = ev.user_id
    tz = pytz.timezone(config["TIMEZONE"])
    now = datetime.now(tz)
    dayinfo = (now.year, now.month, now.day, map_weekday[now.weekday()])
    if not lmt.check(uid):
        await bot.send(ev, L["INFO_REPEAT_LOGIN"].format(*dayinfo), at_sender=True)
        return
    lmt.increase(uid)
    datestr = f'{now.month}/{now.day}'
    kw = datestr if datestr in config["FESTIVAL"] else "DAILY"
    blessing = L["BLESSING_" + kw]
    flower = random.choice(config["FLOWER"][kw])
    flowernm = L["FLOWER_" + flower]
    flowerlang = L["FLOWER_LANGUAGE_" + flower]
    gift = random.choice(config["GIFT"][kw])
    giftnm = L["GIFT_" + gift]
    giftn = random.randint(1, 5)
    dailywork = random.choice(config["DAILY_WORK"][kw])
    desc = L["DAILY_WORK_" + dailywork]
    msg = L["INFO_EVERYDAY_LOGIN"].format(*dayinfo, blessing, flowernm, flowerlang, giftnm, giftn, desc)
    await bot.send(ev, msg, at_sender=True)
