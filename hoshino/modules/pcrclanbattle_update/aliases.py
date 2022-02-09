from enum import Enum


class ServerCode(Enum):
    SERVER_JP = 0
    SERVER_TW = 1
    SERVER_CN = 2


class RecordFlag(Enum):
    NORMAL   = 0
    TAIL     = 1
    LEFTOVER = 2
    LOST     = 3


class SubscribeFlag(Enum):
    NORMAL   = 0
    WHOLE    = 1
    CANCEL   = 2
    FINISHED = 3
    ONTREE   = 4
    LOCKED   = 5
