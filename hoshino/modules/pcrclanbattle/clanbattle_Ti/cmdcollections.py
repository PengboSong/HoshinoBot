from datetime import datetime, timedelta
from time import sleep
from typing import Iterable, List

from aiocqhttp.exceptions import ActionFailed
from hoshino import util, priv
from matplotlib import pyplot as plt
from nonebot import NoneBot
from nonebot import MessageSegment as ms
from nonebot.typing import Context_T

from . import cb_cmd
from .aliases import RecordFlag, SubscribeFlag
from .argtype import check_damage, check_round, check_boss, check_server_code, check_server_name, check_subscribe_flag, int2callnum, serial2text
from .manager import ClanBattleManager
from .parseargs import ArgHolder, ParseArgs, ParseResult
from .exceptions import AlreadyExistError, ClanBattleError, DatabaseError, NotFoundError, PermissionDeniedError


config = util.load_config(__file__)
lang = config["LANG"]
L = util.load_localisation(__file__)[lang]   # Short of localisation

plt.style.use(config["MATPLOTLIB_STYLE"])
plt.rcParams['font.family'] = config["MATPLOTLIB_FONTS"]


def _check_clan(bm: ClanBattleManager):
    """Check whether manager is bound with at least one clan"""
    clan = bm.fetch_clan(1)
    if not clan:
        raise NotFoundError(L["ERROR_CLAN_NOT_FOUND"].format(
            L["USAGE_ADD_CLAN"]) + L["USAGE_SUFFIX"])
    return clan


def _check_member(bm: ClanBattleManager, userid: int, alt: int, tip: str = ''):
    """Check whether the given member exists"""
    member = bm.fetch_member(userid=userid, alt=alt)
    if not member:
        raise NotFoundError(tip or L["ERROR_MEMBER_NOT_FOUND"].format(
            L["USAGE_ADD_MEMBER"]) + L["USAGE_SUFFIX"])
    return member


def _check_admin(ctx: Context_T, tip: str = ''):
    """Check whether member has ADMIN permission"""
    if not priv.check_priv(ctx, priv.ADMIN):
        raise PermissionDeniedError(L["ERROR_PERMISSION_DENIED"] + tip)


@cb_cmd(L["CMD_ADD_CLAN"],
        ParseArgs(usagekw=L["USAGE_ADD_CLAN"], argdict={
            'N': ArgHolder(dtype=str, tips=L["TIP_CLAN"]),
            'S': ArgHolder(dtype=check_server_code, tips=L["TIP_SERVER_CODE"])
        }))
async def add_clan(bot: NoneBot, ctx: Context_T, args: ParseResult):
    _check_admin(ctx)
    bm = ClanBattleManager(ctx["group_id"])
    if bm.check_clan(1):
        bm.modify_clan(clanid=1, name=args.N, server=args.S)
        await bot.send(ctx, L["INFO_MODIFY_CLAN"].format(args.N, args.S), at_sender=True)
    else:
        bm.add_clan(clanid=1, name=args.N, server=args.S)
        await bot.send(ctx, L["INFO_ADD_CLAN"].format(args.N, args.S), at_sender=True)


@cb_cmd(L["CMD_LIST_CLAN"],
        ParseArgs(usagekw=L["USAGE_LIST_CLAN"]))
async def list_clan(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    clans = bm.list_clans()
    if len(clans) != 0:
        msg = ['', L["INFO_CLAN_TITLE"]]
        for clan in clans:
            msg.append(L["INFO_CLAN_CONTENT"].format(
                clan["clanid"], clan["name"], check_server_name(clan["server"])))
        await bot.send(ctx, '\n'.join(msg), at_sender=True)
    else:
        raise NotFoundError(L["ERROR_CLAN_NOT_FOUND"].format(
            L["USAGE_ADD_CLAN"]) + L["USAGE_SUFFIX"])


@cb_cmd(L["CMD_ADD_MEMBER"],
        ParseArgs(usagekw=L["USAGE_ADD_MEMBER"], argdict={
            '': ArgHolder(dtype=str, default='', tips=L["TIP_NICKNAME"]),
            '@': ArgHolder(dtype=int, default=0, tips=L["TIP_QQ_NUMBER"])}))
async def add_member(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    clan = _check_clan(bm)
    uid = args['@'] or args.at or ctx['user_id']
    name = args['']
    if uid != ctx['user_id']:
        _check_admin(ctx, tip=L["TIP_ADD_OTHER_MEMBER"])
        # Check whether member is in this group chat
        try:
            await bot.get_group_member_info(self_id=ctx['self_id'], group_id=bm.groupid, user_id=uid)
        except:
            raise NotFoundError(L["ERROR_MEMBER_NOT_IN_GROUP"].format(uid))
    if not name:
        m = await bot.get_group_member_info(self_id=ctx['self_id'], group_id=bm.groupid, user_id=uid)
        name = util.filt_message(m['card']) or util.filt_message(
            m['nickname']) or str(m['user_id'])

    if (member := bm.fetch_member(userid=uid, alt=bm.groupid)):
        bm.modify_member(uid, member['alt'], name, clan["clanid"])
        await bot.send(ctx, L["INFO_MODIFY_MEMBER"].format(ms.at(uid), name))
    else:
        bm.add_member(uid, bm.groupid, name, clan["clanid"])
        await bot.send(ctx, L["INFO_ADD_MEMBER"].format(ms.at(uid), name, clan["name"]))


@cb_cmd(L["CMD_LIST_MEMBER"],
        ParseArgs(usagekw=L["USAGE_LIST_MEMBER"]))
async def list_member(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    _check_clan(bm)
    members = bm.list_members(clanid=1)
    if (members_count := len(members)):
        msg = ['', L["INFO_MEMBER_TITLE"].format(members_count)]
        for idx, member in enumerate(members):
            msg.append(f"{1 + idx:>2d}/30 | {serial2text(member['userid']):<12} | {member['name']}")
        await bot.send(ctx, '\n'.join(msg), at_sender=True)
    else:
        raise NotFoundError(L["ERROR_EMPTY_CLAN"].format(
            L["USAGE_ADD_MEMBER"]) + L["USAGE_SUFFIX"])


@cb_cmd(L["CMD_REMOVE_MEMBER"],
        ParseArgs(usagekw=L["USAGE_REMOVE_MEMBER"],
                  argdict={'@': ArgHolder(dtype=int, default=0, tips=L["TIP_QQ_NUMBER"])}))
async def remove_member(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    uid = args['@'] or args.at or ctx['user_id']
    member = _check_member(bm, uid, bm.groupid, tip=L["MEMBER_NOT_FOUND"])
    if uid != ctx['user_id']:
        _check_admin(ctx, tip=L["TIP_REMOVE_OTHER_MEMBER"])
    bm.remove_member(uid, member['alt'])
    await bot.send(ctx, L["INFO_REMOVE_MEMBER"].format(member["name"]), at_sender=True)


@cb_cmd(L["CMD_CLEAR_MEMBERS"],
        ParseArgs(usagekw=L["USAGE_CLEAR_MEMBERS"]))
async def clear_member(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    clan = _check_clan(bm)
    _check_admin(ctx)
    if bm.clear_members(clan["clanid"]) != 0:
        await bot.send(ctx, L["INFO_CLEAR_MEMBERS"].format(clan["name"]))
    else:
        await bot.send(ctx, L["INFO_EMPTY_CLAN"].format(clan["name"]))


@cb_cmd(L["CMD_BATCH_ADD_MEMBER"],
        ParseArgs(usagekw=L["USAGE_BATCH_ADD_MEMBER"]))
async def batch_add_member(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    _check_clan(bm)
    _check_admin(ctx)
    try:
        mlist = await bot.get_group_member_list(self_id=ctx['self_id'], group_id=bm.groupid)
    except ActionFailed:
        raise ClanBattleError(
            L["ERROR_GET_MEMBER_LIST_FAILED"].format(L["USAGE_ADD_MEMBER"]))
    if len(mlist) > config["BATCH_ADD_MEMBER_LIMIT"]:
        raise ClanBattleError(
            L["ERROR_MEMBER_LIST_TOO_LONG"].format(BATCH_ADD_MEMBER_LIMIT))

    self_id = ctx['self_id']
    succ, fail = 0, 0
    for m in mlist:
        if m['user_id'] != self_id:
            try:
                bm.add_member(userid=m['user_id'], alt=bm.groupid, name=m['card']
                              or m['nickname'] or str(m['user_id']), clanid=1)
                succ += 1
            except DatabaseError:
                fail += 1
    await bot.send(ctx, L["INFO_BATCH_ADD_MEMBER"].format(succ, fail, L["USAGE_LIST_MEMBER"]), at_sender=True)


def _gen_progress_text(clan_name: str, tier: int, rcode: int, bcode: int, hp: int, total_hp: int, score_rate: float) -> str:
    return L["INFO_PROGRESS_TEMPLATE"].format(clan_name, int2callnum(tier), serial2text(rcode), int2callnum(bcode), '%.1f' % score_rate, hp, total_hp)


def _gen_record_text(rid: int, member_name: str, rcode: int, bcode: int, damage: int) -> str:
    return L["INFO_RECORD_TEMPLATE"].format(rid, member_name, serial2text(rcode), int2callnum(bcode), damage)


def _gen_namelist_text(bm: ClanBattleManager, subscribe_list: Iterable, do_at: bool = False) -> List[str]:
    msg = []
    for subscribe in subscribe_list:
        uid = subscribe["userid"]
        member = str(ms.at(uid)) if do_at else bm.fetch_member(
            uid, bm.groupid)["name"]
        msg.append(L["INFO_SUBSCRIBE_QUEUE_CONTENT"].format(
            subscribe["sid"], member, serial2text(subscribe["round"]), int2callnum(
                subscribe["boss"]),
            check_subscribe_flag(subscribe["flag"]), subscribe["msg"]))
    return msg


@cb_cmd(L["CMD_SUBSCRIBE"],
        ParseArgs(usagekw=L["USAGE_SUBSCRIBE"], argdict={
            'R': ArgHolder(dtype=check_round, default=0, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, default=0, tips=L["TIP_BOSS"]),
            'M': ArgHolder(dtype=str, default='', tips=L["TIP_MESSAGE"])
        }))
async def subscribe(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    uid = ctx["user_id"]
    clan = _check_clan(bm)
    cid = clan["clanid"]
    dhours = bm.UTC_delta(clan["server"])
    _check_member(bm=bm, userid=uid, alt=bm.groupid)
    # Check current progress
    current_round, current_boss, _ = bm.check_progress(cid, now)
    target_round, target_boss = bm.filter_round_boss(args.R, args.B, current_round, current_boss)
    rtext = serial2text(target_round)
    btext = int2callnum(target_boss)
    if (target_round * 5 + target_boss) <= (current_round * 5 + current_boss):
        raise ClanBattleError(
            L["ERROR_LATE_SUBSCRIBE"].format(rtext, btext))
    # Check whether target boss is locked
    if bm.check_boss_locked(cid, now, target_round, target_boss):
        raise AlreadyExistError(
            L["ERROR_TARGET_BOSS_LOCKED"].format(rtext, btext))
    # Check whether user has already subscribed the same boss
    if len(bm.list_subscribes_by_detail(uid, bm.groupid, now, target_round, target_boss)) != 0:
        raise AlreadyExistError(
            L["ERROR_DUPLICATED_SUBSCRIBE"].format(rtext, btext))
    msg = ['']
    # Check whether target boss subscribe number has reached limit
    if len(bm.list_subscribes_by_boss(cid, now, target_round, target_boss)) < config["BOSS_SUBSCRIBE_LIMIT"]:
        sid = bm.add_subscribe(uid, bm.groupid, now, target_round,
                         target_boss, SubscribeFlag.NORMAL.value, args.M)
        msg.append(L["INFO_SUBSCRIBE"].format(rtext, btext, sid))
    else:
        msg.append(L["INFO_SUBSCRIBE_REACH_LIMIT"].format(
            rtext, btext))
    msg.append(L["INFO_SUBSCRIBE_QUEUE_TITLE"])
    msg.extend(_gen_namelist_text(bm=bm,
                                  subscribe_list=bm.list_subscribes_active(clanid=cid, time=now, hourdelta=dhours)))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


@cb_cmd(L["CMD_SUBSCRIBE_WHOLE"],
        ParseArgs(usagekw=L["USAGE_SUBSCRIBE_WHOLE"], argdict={
            'R': ArgHolder(dtype=check_round, default=0, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, default=0, tips=L["TIP_BOSS"]),
            'M': ArgHolder(dtype=str, default='', tips=L["TIP_MESSAGE"])
        }))
async def subscribe_whole(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    dhours = bm.UTC_delta(clan["server"])
    uid = ctx["user_id"]
    _check_member(bm=bm, userid=uid, alt=bm.groupid)
    # Check current progress
    current_round, current_boss, _ = bm.check_progress(cid, now)
    target_round, target_boss = bm.filter_round_boss(args.R, args.B, current_round, current_boss)
    rtext = serial2text(target_round)
    btext = int2callnum(target_boss)
    if (target_round * 5 + target_boss) <= (current_round * 5 + current_boss):
        raise ClanBattleError(
            L["ERROR_LATE_SUBSCRIBE"].format(rtext, btext))
    # Check whether target boss is locked
    if bm.check_boss_locked(cid, now, target_round, target_boss):
        raise AlreadyExistError(
            L["ERROR_TARGET_BOSS_LOCKED"].format(rtext, btext))
    # Check whether user has already subscribed the same boss
    if len(bm.list_subscribes_by_detail(uid, bm.groupid, now, target_round, target_boss)) != 0:
        raise AlreadyExistError(
            L["ERROR_DUPLICATED_SUBSCRIBE"].format(rtext, btext))
    msg = ['']
    # Check whether target boss subscribe number has reached limit
    # For whole run, the limit should be 1
    if len(bm.list_subscribes_by_boss(cid, now, target_round, target_boss)) == 0:
        bm.add_subscribe(userid=uid, alt=bm.groupid, time=now,
                         rcode=target_round, bcode=target_boss,
                         flag=SubscribeFlag.WHOLE.value, msg=args.M)
        # Auto lock boss
        sid = bm.add_subscribe(userid=uid, alt=bm.groupid, time=now,
                         rcode=target_round, bcode=target_boss,
                         flag=SubscribeFlag.LOCKED.value, msg=args.M)
        msg.append(L["INFO_SUBSCRIBE"].format(rtext, btext, sid))
        msg.append(L["INFO_LOCK_BOSS"].format(
            rtext, btext, ms.at(uid)))
    else:
        msg.append(L["INFO_SUBSCRIBE_REACH_LIMIT"].format(
            rtext, btext))
    msg.append(L["INFO_SUBSCRIBE_QUEUE_TITLE"])
    msg.extend(_gen_namelist_text(bm=bm,
                                  subscribe_list=bm.list_subscribes_active(clanid=cid, time=now, hourdelta=dhours)))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


@cb_cmd(L["CMD_UNSUBSCRIBE"],
        ParseArgs(usagekw=L["USAGE_UNSUBSCRIBE"],
                  argdict={'S': ArgHolder(dtype=int, tips=L["TIP_SUBSCRIBE_ID"])}))
async def unsubscribe(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    dhours = bm.UTC_delta(clan["server"])
    subscribe = bm.fetch_subscribe(sid=args.S, clanid=cid, time=now)
    if not subscribe:
        raise NotFoundError(L["ERROR_SUBSCRIBE_NOT_FOUND"].format(args.S))
    if subscribe["userid"] != ctx["user_id"]:
        _check_admin(ctx, tip=L["TIP_UNSUBSCRIBE_OTHER_MEMBER"])
    # Check whether subscribe flag is whole
    if subscribe["flag"] == SubscribeFlag.WHOLE.value:
        # Auto unlock boss
        for locked in bm.list_subscribes_locked(cid, now, subscribe["round"], subscribe["boss"]):
            locked = bm.change_subscribe_flag(locked, SubscribeFlag.CANCEL.value)
            bm.modify_subscribe(**locked)
    subscribe = bm.change_subscribe_flag(subscribe, SubscribeFlag.CANCEL.value)
    bm.modify_subscribe(**subscribe)
    #bm.remove_subscribe(sid=args.S, clanid=clanid, time=now)
    msg = ['', L["INFO_UNSUBSCRIBE"].format(serial2text(
        subscribe["rcode"]), int2callnum(subscribe["bcode"]))]
    msg.append(L["INFO_SUBSCRIBE_QUEUE_TITLE"])
    msg.extend(_gen_namelist_text(bm=bm,
                                  subscribe_list=bm.list_subscribes_active(clanid=cid, time=now, hourdelta=dhours)))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


async def auto_unsubscribe(bot: NoneBot, ctx: Context_T, bm: ClanBattleManager, userid: int, alt: int, rcode: int, bcode: int):
    now = datetime.now()
    subscribes = bm.list_subscribes_by_detail(userid, alt, now, rcode, bcode)
    if len(subscribes) == 0:
        return
    subscribe = bm.change_subscribe_flag(subscribes[0], SubscribeFlag.FINISHED.value)
    bm.modify_subscribe(**subscribe)
    await bot.send(ctx, L["INFO_AUTO_UNSUBSCRIBE"].format(ms.at(userid), serial2text(rcode), int2callnum(bcode)))


async def call_subscribe(bot: NoneBot, ctx: Context_T, rcode: int, bcode: int):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    subscribes = bm.list_subscribes_by_boss(cid, now, rcode, bcode)
    ontrees = bm.list_subscribes_ontree(cid, now, rcode, bcode)
    msg = []
    if len(subscribes) > 0:
        msg.append(L["INFO_CALL_SUBSCRIBES"].format(
            serial2text(rcode), int2callnum(bcode)))
        msg.extend(_gen_namelist_text(bm, subscribes, do_at=True))
    if len(ontrees) > 0:
        msg.append('='*12)
        msg.append(L["INFO_OFF_TREE"])
        msg.extend(_gen_namelist_text(bm, ontrees, do_at=True))
        for ontree in ontrees:
            ontree = bm.change_subscribe_flag(ontree, SubscribeFlag.FINISHED.value)
            bm.modify_subscribe(**ontree)
    if len(msg) != 0:
        await bot.send(ctx, '\n'.join(msg), at_sender=False)


@cb_cmd(L["CMD_SWAP_SUBSCRIBES"],
        ParseArgs(usagekw=L["USAGE_SWAP_SUBSCRIBES"], argdict={
            'S': ArgHolder(dtype=int, tips=L["TIP_SUBSCRIBE_ID"]),
            'R': ArgHolder(dtype=check_round, tips=L["TIP_ROUND"])
        }))
async def swap_subscribes(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    dhours = bm.UTC_delta(clan["server"])
    subscribe = bm.fetch_subscribe(sid=args.S, clanid=cid, time=now)
    if not subscribe:
        raise NotFoundError(L["ERROR_SUBSCRIBE_NOT_FOUND"].format(args.S))
    rcode = subscribe["round"]
    bcode = subscribe["boss"]
    btext = int2callnum(bcode)
    if rcode >= args.R:
        raise ClanBattleError(L["ERROR_SWAP_SUBSCRIBES_FORWARD_ONLY"].format(serial2text(rcode + 1), btext))
    if ctx["user_id"] != subscribe["userid"]:
        _check_admin(ctx, tip=L["TIP_SWAP_OTHER_MEMBER"])
    subscribe = bm.change_subscribe_round(subscribe, args.R)
    # Find locked subscribe
    locked = None
    if bm.check_boss_locked(clanid=cid, time=now, rcode=rcode, bcode=bcode):
        locked = bm.list_subscribes_locked(clanid=cid, time=now, rcode=rcode, bcode=bcode)[0]
        locked = bm.change_subscribe_round(locked, args.R)

    # Find target subscribe
    target_subscribe = None
    target_subscribes = bm.list_subscribes_by_boss(clanid=cid, time=now, rcode=args.R, bcode=bcode)
    if len(target_subscribes) != 0:
        target_subscribe = bm.change_subscribe_round(target_subscribes[0], rcode)
    
    # Find target locked subscribe
    target_locked = None
    if bm.check_boss_locked(clanid=cid, time=now, rcode=args.R, bcode=bcode):
        target_locked = bm.list_subscribes_locked(clanid=cid, time=now, rcode=args.R, bcode=bcode)[0]
        target_locked = bm.change_subscribe_round(target_locked, rcode)

    # Modify subscribe
    bm.modify_subscribe(**subscribe)
    if locked:
        bm.modify_subscribe(**locked)
    if target_subscribe:
        bm.modify_subscribe(**target_subscribe)
    if target_locked:
        bm.modify_subscribe(**target_locked)
    msg = ['', L["INFO_SWAP_SUBSCRIBES_SUCCESS"].format(serial2text(args.R), btext)]
    msg.append(L["INFO_SUBSCRIBE_QUEUE_TITLE"])
    msg.extend(_gen_namelist_text(bm=bm,
                                  subscribe_list=bm.list_subscribes_active(cid, now, dhours)))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


@cb_cmd(L["CMD_CLEAR_SUBSCRIBES"],
        ParseArgs(usagekw=L["USAGE_CLEAR_SUBSCRIBES"], argdict={
            'R': ArgHolder(dtype=check_round, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, tips=L["TIP_BOSS"])}))
async def clear_subscribes(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    _check_admin(ctx, tip=L["TIP_CLEAR_SUBSCRIBES"])
    rtext = serial2text(args.R)
    btext = int2callnum(args.B)
    subscribes = bm.list_subscribes_by_boss(
        clan["clanid"], now, args.R, args.B)
    if len(subscribes) > 0:
        for subscribe in subscribes:
            subscribe = bm.change_subscribe_flag(subscribe, SubscribeFlag.CANCEL.value)
            bm.modify_subscribe(**subscribe)
        await bot.send(ctx, L["INFO_CLEAR_SUBSCRIBES"].format(rtext, btext))
    else:
        raise NotFoundError(
            L["ERROR_SUBSCRIBE_QUEUE_EMPTY"].format(rtext, btext))


@cb_cmd(L["CMD_LIST_SUBSCRIBES"],
        ParseArgs(usagekw=L["USAGE_LIST_SUBSCRIBES"]))
async def list_subscribes(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    dhours = bm.UTC_delta(clan["server"])
    subscribes = bm.list_subscribes_active(clanid=clan["clanid"], time=now, hourdelta=dhours)
    msg = ['', L["INFO_LIST_SUBSCRIBES"].format(clan["name"], len(subscribes))]
    msg.append(L["INFO_SUBSCRIBE_QUEUE_TITLE"])
    msg.extend(_gen_namelist_text(bm, subscribes))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


@cb_cmd(L["CMD_LIST_USER_SUBSCRIBES"],
        ParseArgs(usagekw=L["USAGE_LIST_USER_SUBSCRIBES"]))
async def list_user_subscribes(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    dhours = bm.UTC_delta(clan["server"])
    uid = ctx["user_id"]
    member = _check_member(bm=bm, userid=uid, alt=bm.groupid)
    subscribes = bm.list_subscribes_user_active(userid=uid, alt=member["alt"], time=now, hourdelta=dhours)
    msg = ['', L["INFO_LIST_SUBSCRIBES"].format(clan["name"], len(subscribes))]
    msg.append(L["INFO_SUBSCRIBE_QUEUE_TITLE"])
    msg.extend(_gen_namelist_text(bm, subscribes))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


@cb_cmd(L["CMD_LIST_SUBSCRIBE_TREE"],
        ParseArgs(usagekw=L["USAGE_LIST_SUBSCRIBE_TREE"]))
async def list_subscribe_tree(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    subscribes = bm.list_subscribes(clan["clanid"], now)
    msg = ['', L["INFO_LIST_SUBSCRIBES"].format(clan["name"], len(subscribes))]
    msg.append(L["INFO_SUBSCRIBE_QUEUE_TITLE"])
    msg.extend(_gen_namelist_text(bm, subscribes))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


@cb_cmd(L["CMD_ON_TREE"],
        ParseArgs(usagekw=L["USAGE_ON_TREE"]))
async def on_tree(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    uid = ctx["user_id"]
    clan = _check_clan(bm)
    cid = clan["clanid"]
    _check_member(bm, uid, bm.groupid)
    current_round, current_boss, _ = bm.check_progress(cid, now)
    ontrees = bm.list_subscribes_ontree(cid, now, current_round, current_boss)
    for ontree in ontrees:
        if ontree["userid"] == uid:
            raise AlreadyExistError(L["ERROR_ALREADY_ON_TREE"])
    bm.add_subscribe(userid=uid, alt=bm.groupid, time=now,
                     rcode=current_round, bcode=current_boss,
                     flag=SubscribeFlag.ONTREE.value, msg='')
    ontrees = bm.list_subscribes_ontree(cid, now, current_round, current_boss)
    msg = ['', L["INFO_ON_TREE"]]
    msg.append(L["INFO_LIST_TREE"].format(clan["name"], len(ontrees)))
    msg.extend(_gen_namelist_text(bm, ontrees))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


@cb_cmd(L["CMD_LIST_TREE"],
        ParseArgs(usagekw=L["USAGE_LIST_TREE"]))
async def list_tree(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    current_round, current_boss, _ = bm.check_progress(cid, now)
    ontrees = bm.list_subscribes_ontree(cid, now, current_round, current_boss)
    msg = ['', L["INFO_LIST_TREE"].format(clan["name"], len(ontrees))]
    msg.extend(_gen_namelist_text(bm, ontrees))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


@cb_cmd(L["CMD_LOCK_BOSS"],
        ParseArgs(usagekw=L["USAGE_LOCK_BOSS"]))
async def lock_boss(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    current_round, current_boss, _ = bm.check_progress(cid, now)
    rtext = serial2text(current_round)
    btext = int2callnum(current_boss)
    if bm.check_boss_locked(cid, now, current_round, current_boss):
        locked = bm.list_subscribes_locked(
            cid, now, current_round, current_boss)[0]
        await bot.send(ctx, L["ERROR_ALREADY_LOCKED"].format(rtext, btext, ms.at(locked["userid"])), at_sender=True)
    else:
        uid = ctx["user_id"]
        bm.add_subscribe(userid=uid, alt=bm.groupid, time=now,
                         rcode=current_round, bcode=current_boss,
                         flag=SubscribeFlag.LOCKED.value, msg='')
        await bot.send(ctx, L["INFO_LOCK_BOSS"].format(rtext, btext, ms.at(uid)), at_sender=True)


@cb_cmd(L["CMD_UNLOCK_BOSS"],
        ParseArgs(usagekw=L["USAGE_UNLOCK_BOSS"]))
async def unlock_boss(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    current_round, current_boss, _ = bm.check_progress(cid, now)
    rtext = serial2text(current_round)
    btext = int2callnum(current_boss)
    if bm.check_boss_locked(cid, now, current_round, current_boss):
        locked = bm.list_subscribes_locked(
            cid, now, current_round, current_boss)[0]
        userid = locked["userid"]
        if userid != ctx["user_id"]:
            _check_admin(ctx, tip=L["TIP_UNLOCK_BOSS"].format(
                rtext, btext, ms.at(userid)))
        locked = bm.change_subscribe_flag(locked, SubscribeFlag.FINISHED.value)
        bm.modify_subscribe(**locked)
        await bot.send(ctx, L["INFO_UNLOCK_BOSS"].format(rtext, btext), at_sender=True)
    else:
        await bot.send(ctx, L["ERROR_BOSS_UNLOCKED"].format(rtext, btext), at_sender=True)


@cb_cmd(L["CMD_LOCK_BOSS_AHEAD"],
        ParseArgs(usagekw=L["USAGE_LOCK_BOSS_AHEAD"], argdict={
            'R': ArgHolder(dtype=check_round, default=0, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, default=0, tips=L["TIP_BOSS"])}))
async def lock_boss_ahead(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    # Check current progress
    current_round, current_boss, _ = bm.check_progress(cid, now)
    target_round, target_boss = bm.filter_round_boss(args.R, args.B, current_round, current_boss)
    rtext = serial2text(target_round)
    btext = int2callnum(target_boss)
    if (target_round * 5 + target_boss) <= (current_round * 5 + current_boss):
        raise ClanBattleError(
            L["ERROR_LATE_SUBSCRIBE"].format(rtext, btext))
    if bm.check_boss_locked(cid, now, target_round, target_boss):
        locked = bm.list_subscribes_locked(cid, now, target_round, target_boss)[0]
        await bot.send(ctx, L["ERROR_ALREADY_LOCKED"].format(rtext, btext, ms.at(locked["userid"])), at_sender=True)
    else:
        uid = ctx["user_id"]
        subscribes = bm.list_subscribes_by_boss(cid, now, target_round, target_boss)
        if len(subscribes) != 0 and subscribes[0]["userid"] == uid:
            bm.add_subscribe(userid=uid, alt=bm.groupid, time=now,
                            rcode=target_round, bcode=target_boss,
                            flag=SubscribeFlag.LOCKED.value, msg='')
            await bot.send(ctx, L["INFO_LOCK_BOSS"].format(rtext, btext, ms.at(uid)), at_sender=True)
        else:
            await bot.send(ctx, L["ERROR_SUBSCRIBE_REQUIRED"].format(rtext, btext), at_sender=True)


@cb_cmd(L["CMD_LIST_LOCKED"],
        ParseArgs(usagekw=L["USAGE_LIST_LOCKED"]))
async def list_locked(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    locked = bm.list_subscribes_locked(clanid=clan["clanid"], time=now)
    msg = ['', L["INFO_LIST_SUBSCRIBES"].format(clan["name"], len(locked))]
    msg.append(L["INFO_SUBSCRIBE_QUEUE_TITLE"])
    msg.extend(_gen_namelist_text(bm, locked))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


async def auto_unlock_boss(bot: NoneBot, ctx: Context_T, bm: ClanBattleManager, rcode: int, bcode: int):
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    if bm.check_boss_locked(cid, now, rcode, bcode):
        locked = bm.list_subscribes_locked(
            cid, now, rcode, bcode)[0]
        uid = locked["userid"]
        if uid != ctx["user_id"]:
            await bot.send(ctx, L["INFO_CLASH"].format(ms.at(uid)), at_sender=True)
        else:
            locked = bm.change_subscribe_flag(locked, SubscribeFlag.FINISHED.value)
            bm.modify_subscribe(**locked)
            await bot.send(ctx, L["INFO_AUTO_UNLOCK"], at_sender=True)


@cb_cmd(L["CMD_SHOW_PROGRESS"],
        ParseArgs(usagekw=L["USAGE_SHOW_PROGRESS"]))
async def show_progress(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    server = clan["server"]
    current_round, current_boss, remain_hp = bm.check_progress(cid, now)
    total_hp, score_rate = bm.get_boss_info(
        current_round, current_boss, server)
    tier = bm.current_tier(current_round, server)
    msg = ['', _gen_progress_text(
        clan["name"], tier, current_round, current_boss, remain_hp, total_hp, score_rate)]
    if bm.check_boss_locked(cid, now, current_round, current_boss):
        locked = bm.list_subscribes_locked(
            cid, now, current_round, current_boss)[0]
        msg.append(L["INFO_BOSS_LOCKED"].format(ms.at(locked["userid"])))
    else:
        msg.append(L["INFO_BOSS_UNLOCKED"])
    await bot.send(ctx, '\n'.join(msg), at_sender=True)


async def process_run(bot: NoneBot, ctx: Context_T, args: ParseResult):
    """Handle submitted battle record"""
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now() - timedelta(days=args.get('dayoffset', 0))
    clan = _check_clan(bm)
    member = _check_member(bm, args.userid, args.alt)
    cid = clan["clanid"]
    server = clan["server"]
    uid = member["userid"]
    gid = member["alt"]

    current_round, current_boss, remain_hp = bm.check_progress(clanid=cid, time=now)
    rcode = args.round or current_round
    bcode = args.boss or current_boss
    damage = args.damage if args.flag != RecordFlag.TAIL.value else (
        args.damage or remain_hp)
    flag = args.flag

    if (flag == RecordFlag.TAIL.value) and ((args.round != 0) or (args.boss != 0)) and (damage == 0):
        # Late tail damage is required
        raise NotFoundError(L["ERROR_LATE_TAIL_MISSING_DAMAGE"])

    msg = ['']
    run_list = bm.list_run_by_user_day(
        userid=uid, alt=gid, time=now, hourdelta=bm.UTC_delta(server))
    # If the previous run is tail, this run must be leftover
    if len(run_list) > 0 and run_list[-1]["flag"] == RecordFlag.TAIL.value:
        flag = RecordFlag.LEFTOVER.value
        msg.append(L["INFO_RETAG_LEFTOVER"])

    if (rcode != current_round) or (bcode != current_boss):
        msg.append(L["INFO_MISMATCH_PROGRESS"])
    else:   # Damage correction
        eps = 30000
        if damage > remain_hp + eps:
            damage = remain_hp
            msg.append(L["INFO_DAMAGE_CORRECTION"].format(damage))
            if flag == RecordFlag.NORMAL.value:
                flag = RecordFlag.TAIL.value
                msg.append(L["INFO_RETAG_TAIL"])
        elif flag == RecordFlag.TAIL.value:
            if damage < remain_hp - eps:
                msg.append(L["INFO_TAIL_LESS_DAMAGE"])
            elif damage < remain_hp:
                if damage % 1000 == 0:
                    damage = remain_hp
                    msg.append(L["INFO_TAIL_DAMAGE_CORRECTION"].format(damage))
                else:
                    msg.append(L["INFO_LESS_DAMAGE"])

    rid = bm.add_run(userid=uid, alt=gid,
                     time=now, rcode=rcode, bcode=bcode, damage=damage, flag=flag)
    after_round, after_boss, after_hp = bm.check_progress(clanid=cid, time=now)
    total_hp, score_rate = bm.get_boss_info(
        after_round, after_boss, server)
    tier = bm.current_tier(after_round, server)
    msg.append(_gen_record_text(
        rid=rid, member_name=member["name"], rcode=rcode, bcode=bcode, damage=damage))
    msg.append(_gen_progress_text(clan_name=clan["name"], tier=tier, rcode=after_round,
               bcode=after_boss, hp=after_hp, total_hp=total_hp, score_rate=score_rate))
    await bot.send(ctx, '\n'.join(msg), at_sender=True)

    # If current progress changes, check subscribe list and call
    if (after_round != current_round) or (after_boss != current_boss):
        await call_subscribe(bot, ctx, after_round, after_boss)

    await auto_unlock_boss(bot, ctx, bm, current_round, current_boss)
    await auto_unsubscribe(bot, ctx, bm, uid, bm.groupid, current_round, current_boss)


@cb_cmd(L["CMD_ADD_RUN"],
        ParseArgs(usagekw=L["USAGE_ADD_RUN"], argdict={
            '': ArgHolder(dtype=check_damage, tips=L["TIP_DAMAGE"]),
            '@': ArgHolder(dtype=int, default=0, tips=L["TIP_QQ_NUMBER"]),
            'R': ArgHolder(dtype=check_round, default=0, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, default=0, tips=L["TIP_BOSS"]),
            'D': ArgHolder(dtype=int, default=0, tips=L["TIP_DATE_DELTA"])}))
async def add_run(bot: NoneBot, ctx: Context_T, args: ParseResult):
    await process_run(bot, ctx, args=ParseResult({
        "round": args.R, "boss": args.B, "damage": args.get(''),
        "userid": args['@'] or args.at or ctx["user_id"],
        "alt": ctx["group_id"],
        "flag": RecordFlag.NORMAL.value,
        "dayoffset": args.get('D', 0)}))


@cb_cmd(L["CMD_ADD_RUN_TAIL"],
        ParseArgs(usagekw=L["USAGE_ADD_RUN_TAIL"], argdict={
            '': ArgHolder(dtype=check_damage, default=0, tips=L["TIP_DAMAGE"]),
            '@': ArgHolder(dtype=int, default=0, tips=L["TIP_QQ_NUMBER"]),
            'R': ArgHolder(dtype=check_round, default=0, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, default=0, tips=L["TIP_BOSS"])}))
async def add_run_tail(bot: NoneBot, ctx: Context_T, args: ParseResult):
    await process_run(bot, ctx, args=ParseResult({
        "round": args.R, "boss": args.B, "damage": args.get(''),
        "userid": args['@'] or args.at or ctx["user_id"],
        "alt": ctx["group_id"],
        "flag": RecordFlag.TAIL.value}))


@cb_cmd(L["CMD_ADD_RUN_LEFTOVER"],
        ParseArgs(usagekw=L["USAGE_ADD_RUN_LEFTOVER"], argdict={
            '': ArgHolder(dtype=check_damage, tips=L["TIP_DAMAGE"]),
            '@': ArgHolder(dtype=int, default=0, tips=L["TIP_QQ_NUMBER"]),
            'R': ArgHolder(dtype=check_round, default=0, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, default=0, tips=L["TIP_BOSS"])}))
async def add_run_leftover(bot: NoneBot, ctx: Context_T, args: ParseResult):
    await process_run(bot, ctx, args=ParseResult({
        "round": args.R, "boss": args.B, "damage": args.get(''),
        "userid": args['@'] or args.at or ctx["user_id"],
        "alt": ctx["group_id"],
        "flag": RecordFlag.LEFTOVER.value}))


@cb_cmd(L["CMD_ADD_RUN_LOST"],
        ParseArgs(usagekw=L["USAGE_ADD_RUN_LOST"], argdict={
            '@': ArgHolder(dtype=int, default=0, tips=L["TIP_QQ_NUMBER"]),
            'R': ArgHolder(dtype=check_round, default=0, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, default=0, tips=L["TIP_BOSS"])}))
async def add_run_lost(bot: NoneBot, ctx: Context_T, args: ParseResult):
    await process_run(bot, ctx, args=ParseResult({
        "round": args.R, "boss": args.B, "damage": 0,
        "userid": args['@'] or args.at or ctx["user_id"],
        "alt": ctx["group_id"],
        "flag": RecordFlag.LOST.value}))


@cb_cmd(L["CMD_REMOVE_RUN"],
        ParseArgs(usagekw=L["USAGE_REMOVE_RUN"],
                  argdict={'R': ArgHolder(dtype=int, tips=L["TIP_RECORD_ID"])}))
async def remove_run(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]

    record = bm.fetch_run(rid=args.R, clanid=cid, time=now)
    if not record:
        raise NotFoundError(L["ERROR_RECORD_NOT_FOUND"].format(args.R))
    uid = record["userid"]
    if uid != ctx["user_id"]:
        _check_admin(ctx, tip=L["TIP_UNSUBSCRIBE_OTHERS"])
    bm.remove_run(rid=args.R, clanid=cid, time=now)
    await bot.send(ctx, L["INFO_REMOVE_RUN"].format(ms.at(uid), clan["name"], args.R), at_sender=True)


@cb_cmd(L["CMD_CHANGE_PROGRESS"],
        ParseArgs(usagekw=L["USAGE_CHANGE_PROGRESS"], argdict={
            '': ArgHolder(dtype=check_damage, default=1000000000, tips=L["TIP_BOSS_HP"]),
            'R': ArgHolder(dtype=check_round, default=0, tips=L["TIP_ROUND"]),
            'B': ArgHolder(dtype=check_boss, default=0, tips=L["TIP_BOSS"])}))
async def change_progress(bot: NoneBot, ctx: Context_T, args: ParseResult):
    bm = ClanBattleManager(ctx["group_id"])
    now = datetime.now()
    clan = _check_clan(bm)
    cid = clan["clanid"]
    server = clan["server"]
    uid = ctx["self_id"]
    admin = _check_member(bm, uid, bm.groupid, tip=L["TIP_ADD_BOT"])
    current_round, current_boss, remain_hp = bm.check_progress(cid, now)
    target_round, target_boss = bm.filter_round_boss(args.R, args.B, current_round, current_boss)
    if (current_round * 5 + current_boss) > (target_round * 5 + target_boss):
        total_hp, _ = bm.get_boss_info(current_round, current_boss, server)
        raise AlreadyExistError(L["ERROR_CHANGE_PROGRESS_BACKWARD"].format(clan["name"], current_round, current_boss, remain_hp, total_hp))
    while (current_round * 5 + current_boss) < (target_round * 5 + target_boss):
        await process_run(bot, ctx, args=ParseResult({
            "round": current_round, "boss": current_boss, "damage": remain_hp,
            "userid": uid, "alt": bm.groupid,
            "flag": RecordFlag.NORMAL.value
        }))
        sleep(1)   # Wait 1 second
        current_round, current_boss, remain_hp = bm.check_progress(cid, now)
    target_hp = max(0, min(args.get(''), remain_hp))
    total_hp, _ = bm.get_boss_info(current_round, current_boss, server)
    damage = abs(remain_hp - target_hp)
    if damage != 0:
        await process_run(bot, ctx, args=ParseResult({
            "round": current_round, "boss": current_boss, "damage": damage,
            "userid": uid, "alt": bm.groupid,
            "flag": RecordFlag.NORMAL.value
        }))
    await bot.send(ctx, L["INFO_CHANGE_PROGRESS"].format(clan["name"], current_round, current_boss, target_hp, total_hp), at_sender=True)
