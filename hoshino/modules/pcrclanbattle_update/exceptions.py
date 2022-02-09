class ClanBattleError(Exception):
    """Exceptions caught by work loop"""

    def __init__(self, *msgs):
        self._msg = '\n'.join(msgs)

    def __str__(self):
        return self._msg

    @property
    def message(self):
        return str(self)

    def append(self, msg: str):
        self._msg += '\n' + msg.strip()
        return self


class ParseError(ClanBattleError):
    """Invalid passed argument"""
    pass


class NotFoundError(ClanBattleError):
    """Target object (clan, member, record) can not be found"""
    pass


class AlreadyExistError(ClanBattleError):
    pass


class PermissionDeniedError(ClanBattleError):
    """DO NOT have sufficient permissions to do opertions"""
    pass


class DatabaseError(ClanBattleError):
    """Low-level database operation failed"""
    pass
