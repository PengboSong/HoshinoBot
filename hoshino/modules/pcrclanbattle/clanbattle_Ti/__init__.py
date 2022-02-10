# Princess Connect Re:Dive Clan Battle Management Module
# Refactor by pbsong
# Current Version: v2-pbsong-ver0.1

from .cmdcollections import *
from .union_run import union_run
from hoshino import Service, util
from hoshino.typing import *
from nonebot import on_command

from .parseargs import ArgParser
from .exceptions import ClanBattleError, DatabaseError


lang = util.load_config(__file__)["LANG"]
L = util.load_localisation(__file__)[lang]   # Short of localisation


sv = Service('clanbattle', help_=L["MODULE_NAME"] +
             L["VERSION"], bundle='PCR Clan Battle')

_registry: Dict[str, Tuple[Callable, ArgParser]] = {}


@sv.on_message('group')
async def _clanbattle_bus(bot, ctx):
    # Check prefix
    start = ''
    for m in ctx['message']:
        if m.type == 'text':
            start = m.data.get('text', '').lstrip()
            break
    if not start or start[0] not in '!！':
        return

    # find cmd
    plain_text = ctx['message'].extract_plain_text()
    if len(plain_text) <= 1:
        return
    cmd, *args = plain_text[1:].split()
    cmd = util.normalize_str(cmd)
    if cmd in _registry:
        func, parser = _registry[cmd]
        try:
            sv.logger.info(
                f'Message {ctx["message_id"]} is a clanbattle command, start to process by {func.__name__}.')
            args = parser.parse(args, ctx['message'])
            await func(bot, ctx, args)
            sv.logger.info(
                f'Message {ctx["message_id"]} is a clanbattle command, handled by {func.__name__}.')
        except DatabaseError as err:
            await bot.send(ctx, L["DATABASE_ERROR"].format(err.message) + L["SORRY"], at_sender=True)
        except ClanBattleError as err:
            await bot.send(ctx, err.message, at_sender=True)
        except Exception as err:
            sv.logger.exception(err)
            sv.logger.error(
                f'{type(err)} occured when {func.__name__} handling message {ctx["message_id"]}.')
            await bot.send(ctx, L["UNEXPECTED_ERROR"].format(err.message) + L["SORRY"], at_sender=True)


def cb_cmd(name, parser: ArgParser) -> Callable:
    if isinstance(name, str):
        name = (name, )
    if not isinstance(name, Iterable):
        raise ValueError('`name` of cb_cmd must be `str` or `Iterable[str]`')
    names = map(lambda x: util.normalize_str(x), name)

    def deco(func) -> Callable:
        for n in names:
            if n in _registry:
                sv.logger.warning(
                    f'Name clash found in {func.__name__} and {_registry[n].__name__}.')
            else:
                _registry[n] = (func, parser)
        return func
    return deco


QUICK_START = f'''
============================================
- {L["MOUDLE_NAME"]}{L["VERSION"]} {L["QUICK_START"]} -
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
'''.rstrip()


@on_command(L["CMD_HELP"], aliases=L["CMD_HELP_ALIAS"], only_to_me=False)
async def cb_help(session: CommandSession):
    await session.send(QUICK_START, at_sender=True)
    doc1 = MessageSegment.share(url='https://github.com/PengboSong/HoshinoBot/hoshino/modules/pcrclanbattle_update/README.md',
                                title=L["MODULE_NAME"] + L["VERSION"],
                                content=L["MANUAL"])
    await session.send(doc1)
    doc2 = MessageSegment.share(url='https://github.com/Ice-Cirno/HoshinoBot/wiki/%E4%BC%9A%E6%88%98%E7%AE%A1%E7%90%86v2',
                                title=L["MODULE_NAME"] +
                                    L["OPEN_SOURCE_VERSION"],
                                content=L["MANUAL"])
    await session.send(doc2)
