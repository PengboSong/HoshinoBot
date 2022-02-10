# Princess Connect Re:Dive Clan Battle Management Module
# Refactor by Titanium
# Current Version: v2-Ti-ver0.1-alpha

from hoshino import Service, util
from hoshino.typing import *
from nonebot import on_command

from .parseargs import ParseArgs
from .exceptions import ClanBattleError, DatabaseError


lang = util.load_config(__file__)["LANG"]
L = util.load_localisation(__file__)[lang]   # Short of localisation


sv = Service('clanbattle-Ti', help_=L["MODULE_NAME"] + L["VERSION"], visible=True)

_registry: Dict[str, Tuple[Callable, ParseArgs]] = {}


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
            await bot.send(ctx, L["UNEXPECTED_ERROR"].format(err) + L["SORRY"], at_sender=True)


def cb_cmd(name, parser: ParseArgs) -> Callable:
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


# Import commands
from .cmdcollections import *
from .union_run import union_run
from .help_doc import help_doc
