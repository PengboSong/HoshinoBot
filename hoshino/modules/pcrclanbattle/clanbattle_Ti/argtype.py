import re
from typing import Union

from hoshino import util

from .aliases import ServerCode, SubscribeFlag
from .exceptions import ParseError


lang = util.load_config(__file__)["LANG"]
L = util.load_localisation(__file__)[lang]   # Short of localisation


# Map words
call_numbers = '⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿'
map_numbers = dict(zip('12345一二三四五壹贰叁肆伍', [i % 5 + 1 for i in range(15)]))


# Regex
reg_dint = re.compile(r'^(\+?[0-9]*\.?[0-9]+)([kKwWmM]?)$')
reg_bcode = re.compile(r'^[b|B|老]?([1-5一二三四五壹贰叁肆伍])王?$', re.IGNORECASE)
reg_rcode = re.compile(r'^[1-9][0-9]{0,2}$')
reg_server_jp = re.compile(r'^JP|日服?$', re.IGNORECASE)
reg_server_tw = re.compile(r'^TW|台服?$', re.IGNORECASE)
reg_server_cn = re.compile(r'^CN|[B国]服?$', re.IGNORECASE)


def convert_unit(num: Union[int, float], unit: str = '') -> int:
    value = round(num)
    if unit:
        if unit in 'kK':
            value = round(num * 1000)
        elif unit in 'wW':
            value = round(num * 10000)
        elif unit in 'mM':
            value = round(num * 1000000)
    return value


def check_damage(para: str) -> int:
    para = util.normalize_str(para).strip()
    if res := reg_dint.match(para):
        v = convert_unit(float(res.group(1)), res.group(2))
        if v > 1000000000:
            raise ParseError(L["DAMAGE_OVERFLOW"])
        return v
    else:
        raise ParseError(L["INVALID_DAMAGE_FORMAT"])


def check_boss(para: str) -> int:
    para = util.normalize_str(para).strip()
    if res := reg_bcode.match(para):
        return map_numbers[res.group(1)]
    else:
        raise ParseError(L["INVALID_BOSS_CODE"])


def check_round(para: str) -> int:
    para = util.normalize_str(para).strip()
    if reg_rcode.match(para):
        return int(para)
    else:
        raise ParseError(L["INVALID_ROUND_CODE"])


def check_server_code(para: str) -> int:
    para = util.normalize_str(para).strip()
    if reg_server_jp.match(para):
        return ServerCode.SERVER_JP.value
    elif reg_server_tw.match(para):
        return ServerCode.SERVER_TW.value
    elif reg_server_cn.match(para):
        return ServerCode.SERVER_CN.value
    else:
        raise ParseError(L["INVALID_SERVER_CODE"])


def check_server_name(code: int) -> str:
    if code == ServerCode.SERVER_JP.value:
        return "JP"
    elif code == ServerCode.SERVER_TW.value:
        return "TW"
    elif code == ServerCode.SERVER_CN.value:
        return "CN"
    else:
        return "UNKNOWN"


def check_subscribe_flag(flag: int) -> str:
    if flag == SubscribeFlag.NORMAL.value:
        return L["SUBSCRIBE_FLAG_NORMAL"]
    elif flag == SubscribeFlag.WHOLE.value:
        return L["SUBSCRIBE_FLAG_WHOLE"]
    elif flag == SubscribeFlag.CANCEL.value:
        return L["SUBSCRIBE_FLAG_CANCEL"]
    elif flag == SubscribeFlag.FINISHED.value:
        return L["SUBSCRIBE_FLAG_FINISHED"]
    elif flag == SubscribeFlag.LOCKED.value:
        return L["SUBSCRIBE_FLAG_LOCKED"]
    elif flag == SubscribeFlag.ONTREE.value:
        return L["SUBSCRIBE_FLAG_ONTREE"]
    else:
        return L["SUBSCRIBE_FLAG_UNKNOWN"]


def int2callnum(x: int) -> str:
    if 0 <= x <= 50:
        return call_numbers[x]
    else:
        raise ValueError("Input x should be in range 0 <= x <= 50.")


def serial2text(x: int) -> str:
    text = ''
    for digit in str(x):
        text += int2callnum(int(digit))
    return text
