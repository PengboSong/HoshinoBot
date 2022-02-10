from hoshino import util
from nonebot import NoneBot
from nonebot.typing import Context_T

from . import sv, cb_cmd
from .argtype import check_damage
from .parseargs import ArgHolder, ParseArgs, ParseResult
from .exceptions import ParseError

lang = util.load_config(__file__)["LANG"]
L = util.load_localisation(__file__)[lang]

@cb_cmd(L["CMD_UNION_RUN"],
    ParseArgs(usagekw=L["USAGE_UNION_RUN"], argdict={
        '': ArgHolder(dtype=check_damage, tips=L["TIP_BOSS_HP"]),
        'A': ArgHolder(dtype=check_damage, tips=L["TIP_DAMAGE"]),
        'B': ArgHolder(dtype=check_damage, tips=L["TIP_DAMAGE"]),
    }))
async def union_run(bot: NoneBot, ctx: Context_T, args: ParseResult):
    remain_HP = args['']
    if args.A + args.B < remain_HP:
        left_HP = remain_HP - args.A - args.B
        await bot.send(ctx, L["INFO_UNION_RUN_LESS_DAMAGE"].format(left_HP), at_sender=True)
    if (args.A >= remain_HP) and (args.B >= remain_HP):
        prior = 1 if args.A > args.B else 2
        time = (1 - remain_HP / max(args.A, args.B)) * 90 + 20
        await bot.send(ctx, L["INFO_UNION_RUN_MORE_DAMAGE"].format(prior, time), at_sender=True)
    elif args.A >= remain_HP:
        time = (1 - remain_HP / args.A) * 90 + 20
        await bot.send(ctx, L["INFO_UNION_RUN_MORE_DAMAGE"].format(1, time), at_sender=True)
    elif args.B >= remain_HP:
        time = (1 - remain_HP / args.B) * 90 + 20
        await bot.send(ctx, L["INFO_UNION_RUN_MORE_DAMAGE"].format(2, time), at_sender=True)
    else:
        damage1 = max(args.A, args.B)
        damage2 = min(args.A, args.B)
        prior = 1 if args.A > args.B else 2
        time = (1 - (remain_HP - damage1) / damage2) * 90 + 20
        await bot.send(ctx, L["INFO_UNION_RUN_SUCCESS"].format(prior, 3 - prior, time))
