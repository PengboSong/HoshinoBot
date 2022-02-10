from hoshino import util
from nonebot import NoneBot
from nonebot.typing import Context_T

from . import cb_cmd
from .parseargs import ParseArgs, ParseResult


lang = util.load_config(__file__)["LANG"]
L = util.load_localisation(__file__)[lang]


QUICK_START = f'''
============================================
- {L["MODULE_NAME"]}{L["VERSION"]} {L["QUICK_START"]} -
============================================
【必读事项】
{L["CAUTIONS"]}
【公会注册】
{L["USAGE_ADD_CLAN"]}
【注册成员】
{L["USAGE_ADD_MEMBER"]}
【报刀】
{L["USAGE_ADD_RUN"]}
{L["USAGE_ADD_RUN_TAIL"]}
{L["USAGE_ADD_RUN_LEFTOVER"]}
{L["USAGE_ADD_RUN_LOST"]}
【删刀】
{L["USAGE_REMOVE_RUN"]}
【预约Boss】
{L["USAGE_SUBSCRIBE"]}
{L["USAGE_UNSUBSCRIBE"]}
【锁定Boss】
{L["USAGE_LOCK_BOSS"]}
{L["USAGE_UNLOCK_BOSS"]}
{L["USAGE_LOCK_BOSS_AHEAD"]}
'''.strip()


@cb_cmd(L["CMD_HELP"],
        ParseArgs(usagekw=L["USAGE_HELP"]))
async def help_doc(bot: NoneBot, ctx: Context_T, args: ParseResult):
    await bot.send(ctx, QUICK_START, at_sender=True)
