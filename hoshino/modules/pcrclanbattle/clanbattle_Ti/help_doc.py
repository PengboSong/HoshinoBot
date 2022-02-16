import re

from hoshino import util
from hoshino.typing import CQEvent, MessageSegment
from nonebot import NoneBot

from . import sv


lang = util.load_config(__file__)["LANG"]
L = util.load_localisation(__file__)[lang]


# Map words
map_numbers = dict(zip('12345一二三四五壹贰叁肆伍', [i % 5 + 1 for i in range(15)]))
map_letters = dict(zip('ABCDEabcde', [i % 5 + 1 for i in range(10)]))

# Regex
reg_reference = re.compile(r'^[抄查]?(?P<tier>(?P<num>[1-5一二三四五壹贰叁肆伍])阶段|(?P<letter>[A-Ea-e])面)?作业$')


QUICK_START = f'''
===============================
- {L["MODULE_NAME"]}{L["VERSION_TI_SHORT"]}版 {L["QUICK_START"]} -
===============================
【必读事项】
{L["CAUTIONS"]}
【查看进度】
{L["USAGE_SHOW_PROGRESS"]}
【推进系统进度】
{L["USAGE_CHANGE_PROGRESS"]}
【预约普通刀】
{L["USAGE_SUBSCRIBE"]}
【预约整刀+自动锁定】
{L["USAGE_SUBSCRIBE_WHOLE"]}
【取消预约】
{L["USAGE_UNSUBSCRIBE"]}
【交换预约】
{L["USAGE_SWAP_SUBSCRIBES"]}
【查看公会预约】
{L["USAGE_LIST_SUBSCRIBES"]}
【查看我的预约】
{L["USAGE_LIST_USER_SUBSCRIBES"]}
【锁定 & 解锁】
{L["USAGE_LOCK_BOSS"]}
{L["USAGE_LOCK_BOSS_AHEAD"]}
{L["USAGE_UNLOCK_BOSS"]}
【计算合刀】
{L["USAGE_UNION_RUN"]}
'''.rstrip()


@sv.on_rex(reg_reference)
async def cb_clanbattle_reference(bot: NoneBot, ev: CQEvent):
    res = ev["match"]
    tier = 0
    if res.group("tier"):
        if num := res.group("num"):
            tier = map_numbers[num]
        if letter := res.group("letter"):
            tier = map_letters[letter]
    link = "LINK_CLAN_BATTLE_REFERENCE"
    title = "INFO_CLAN_BATTLE_REFERENCE_TITLE"
    content = "INFO_CLAN_BATTLE_REFERENCE_CONTENT"
    if (tier > 0) and (tier <= 5):
        link = f"LINK_CLAN_BATTLE_REFERENCE_TIER_{tier}"
        title = f"INFO_CLAN_BATTLE_REFERENCE_TIER_{tier}_TITLE"
        content = f"INFO_CLAN_BATTLE_REFERENCE_TIER_{tier}_CONTENT"
        
    await bot.send(ev, L[content], at_sender=True)
    msg = MessageSegment.share(url=L[link],
                            title=L[title],
                            content=L[content])
    await bot.send(ev, msg)


@sv.on_fullmatch(*L["CMD_CLAN_BATTLE_RANK"], only_to_me=False)
async def cb_clanbattle_rank(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, L["INFO_CLAN_BATTLE_RANK_CONTENT"], at_sender=True)
    msg = MessageSegment.share(url=L["LINK_CLAN_BATTLE_RANK"],
                               title=L["INFO_CLAN_BATTLE_RANK_TITLE"],
                               content=L["INFO_CLAN_BATTLE_RANK_CONTENT"])
    await bot.send(ev, msg)


@sv.on_fullmatch(*L["CMD_HELP"], only_to_me=False)
async def cb_help_doc(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, QUICK_START, at_sender=True)
    msg = MessageSegment.share(url=L["LINK_HELP_DOC"],
                               title=L["INFO_HELP_DOC_TITLE"],
                               content=L["INFO_HELP_DOC_CONTENT"])
    await bot.send(ev, msg)

