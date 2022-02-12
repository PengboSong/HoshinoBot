from typing import Any, List

from hoshino import util
from nonebot import Message

from .exceptions import ParseError


lang = util.load_config(__file__)["LANG"]
L = util.load_localisation(__file__)[lang]   # Short of localisation


class ArgHolder(object):
    __slots__ = ('dtype', 'default', 'tips')

    def __init__(self, dtype: type = str, default: Any = None, tips: str = ''):
        self.dtype = dtype
        self.default = default
        self.tips = tips


class ParseResult(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class ParseArgs(object):
    def __init__(self, usagekw: str = '', argdict: dict = {}):
        self.usage = L["USAGE_PREFIX"] + usagekw + L["USAGE_SUFFIX"]
        self.argdict = argdict

    def add_arg(self, cmd: str, dtype: type = str, default: Any = None, tips: str = ''):
        self.argdict[cmd] = ArgHolder(dtype, default, tips)

    def parse(self, args: List[str], msg: Message) -> ParseResult:
        res = ParseResult()

        for arg in args:
            code = arg[0].upper()
            # Parameter starts with a one-letter code
            if code in self.argdict:
                holder = self.argdict[code]
                para = arg[1:]
            # Raw parameter
            elif '' in self.argdict:
                code = ''
                holder = self.argdict['']
                para = arg
            else:
                raise ParseError(L["UNKNOWN_HOLDER"], self.usage)

            try:
                if holder.dtype == str:
                    value = util.filt_message(holder.dtype(para))
                else:
                    value = holder.dtype(para)
            except ParseError as err:
                raise err.append(self.usage)
            except Exception:
                tip = L["STARTS_WITH"].format(
                    code) if code else '' + holder.tips or L["PARAMETER"]
                msg = L["CORRECT_PARAMETER_REQUIRED"].format(tip)
                raise ParseError(msg, self.usage)
            res.setdefault(code, value)

        # Check whether all required parameters get values
        for code, holder in self.argdict.items():
            if code not in res:
                if holder.default is None:
                    tip = L["STARTS_WITH"].format(code) if code else ''
                    tip += holder.tips or L["PARAMETER"]
                    raise ParseError(
                        L["MISSING_PARAMETER_REQUIRED"].format(tip))
                else:
                    res[code] = holder.default

        # Parse at target QQ number
        res['at'] = 0
        for seg in msg:
            if seg.type == 'at':
                res['at'] = int(seg.data['qq'])

        return res
