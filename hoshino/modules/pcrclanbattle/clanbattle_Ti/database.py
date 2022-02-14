import os
import sqlite3
from typing import Dict, List, Tuple, Optional

from hoshino import logger, util
from hoshino.modules.pcrclanbattle.clanbattle.cmdv2 import subscribe

from .exceptions import DatabaseError


config = util.load_config(__file__)
lang = config["LANG"]
L = util.load_localisation(__file__)[lang]   # Short of localisation


class PCRsqlite(object):
    """Basic class for clan battle data management based on Sqlite3"""
    def __init__(self, table, columns, fields):
        self._dbpath = config["DB_PATH"]
        os.makedirs(os.path.dirname(self._dbpath), exist_ok=True)
        self._table = table
        self._columns = columns
        self._fields = fields

        # Initialize database table
        sql = f"CREATE TABLE IF NOT EXISTS {self._table} ({self._fields})"
        with self._connect() as conn:
            conn.execute(sql)

    def _connect(self):
        # PARSE_DECLTYPES and PARSE_COLNAMES are used to handle datetime
        return sqlite3.connect(
            self._dbpath,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )


class ClanDB(PCRsqlite):
    """Database class for clan management"""
    def __init__(self):
        """Create a database table with basic clan information.
        
        The table is built with the following columns:
        Columns   Description        Type   NotNull   PK
        groupid   QQ group chat ID   INT    True      True
        clanid    PCR clan ID        INT    True      True
        name      PCR clan name      TEXT   True      False
        server    PCR server code    INT    True      False
        """
        super().__init__(
            table="claninfo",
            columns="groupid, clanid, name, server",
            fields='''
groupid INT  NOT NULL,
clanid  INT  NOT NULL,
name    TEXT NOT NULL,
server  INT  NOT NULL,
PRIMARY KEY (groupid, clanid)''')
    
    @staticmethod
    def pack_claninfo(record : Tuple) -> Dict:
        if record:
            gid, cid, nm, scode = record
            return {"groupid": gid, "clanid": cid, "name": nm, "server": scode}
        else:
            return {}
    
    @staticmethod
    def unpack_claninfo(claninfo : Dict) -> Tuple:
        if claninfo:
            return (claninfo["groupid"], claninfo["clanid"], claninfo["name"], claninfo["server"])
        else:
            return ()
    
    def add(self, claninfo: Dict):
        sql = f"INSERT INTO {self._table} ({self._columns}) VALUES (?, ?, ?, ?)"
        with self._connect() as conn:
            try:
                conn.execute(sql, self.unpack_claninfo(claninfo))
            except sqlite3.DatabaseError as err:
                logger.error("[ClanDB.add Failed] " + str(err))
                raise DatabaseError(L["ADD_CLAN_FAILED"])
    
    def remove(self, groupid : int, clanid : int):
        sql = f"DELETE FROM {self._table} WHERE groupid=? AND clanid=?"
        with self._connect() as conn:
            try:
                conn.execute(sql, (groupid, clanid))
            except sqlite3.DatabaseError as err:
                logger.error("[ClanDB.remove Failed] " + str(err))
                raise DatabaseError(L["REMOVE_CLAN_FAILED"])
    
    def modify(self, claninfo: Dict):
        sql = f"UPDATE {self._table} SET name=?, server=? WHERE groupid=? AND clanid=?"
        with self._connect() as conn:
            try:
                paras = self.unpack_claninfo(claninfo)
                conn.execute(sql, (*paras[2:], *paras[:2]))
            except sqlite3.DatabaseError as err:
                logger.error("[ClanDB.modify Failed] " + str(err))
                raise DatabaseError(L["MODIFY_CLAN_FAILED"])
    
    def find_one(self, groupid : int, clanid : int) -> Dict:
        sql = f"SELECT {self._columns} FROM {self._table} WHERE groupid=? AND clanid=?"
        with self._connect() as conn:
            try:
                record = conn.execute(sql, (groupid, clanid)).fetchone()
                return self.pack_claninfo(record)
            except sqlite3.DatabaseError as err:
                logger.error("[ClanDB.find_one Failed] " + str(err))
                raise DatabaseError(L["SEARCH_CLAN_FAILED"])
    
    def find_all(self) -> List[Dict]:
        sql = f"SELECT {self._columns} FROM {self._table}"
        with self._connect() as conn:
            try:
                records = conn.execute(sql).fetchall()
                return [self.pack_claninfo(record) for record in records]
            except sqlite3.DatabaseError as err:
                logger.error("[ClanDB.find_all Failed] " + str(err))
                raise DatabaseError(L["SEARCH_CLAN_FAILED"])
    
    def find_by_groupid(self, groupid : int) -> List[Dict]:
        """Search all clans belong to the given group chat"""
        sql = f"SELECT {self._columns} FROM {self._table} WHERE groupid=?"
        with self._connect() as conn:
            try:
                records = conn.execute(sql, (groupid,)).fetchall()
                return [self.pack_claninfo(record) for record in records]
            except sqlite3.DatabaseError as err:
                logger.error("[ClanDB.find_by_groupid Failed] " + str(err))
                raise DatabaseError(L["SEARCH_CLAN_FAILED"])


class MemberDB(PCRsqlite):
    """Database class for clan members management"""
    def __init__(self):
        """Create a database table with clan members information.
        
        The table is built with the following columns:
        Columns   Description          Type   NotNull   PK
        userid    QQ user number       INT    True      True
        alt       User group chat ID   INT    True      True
        name      QQ user nickname     TEXT   True      False
        groupid   QQ group chat ID     INT    True      False
        clanid    PCR clan ID          INT    True      False
        """
        super().__init__(
            table="clanmember",
            columns="userid, alt, name, groupid, clanid",
            fields='''
userid  INT  NOT NULL,
alt     INT  NOT NULL,
name    TEXT NOT NULL,
groupid INT  NOT NULL,
clanid  INT  NOT NULL,
PRIMARY KEY (userid, alt)''')
    
    @staticmethod
    def pack_memberinfo(record : Tuple) -> Dict:
        if record:
            uid, alt, nm, gid, cid = record
            return {"userid": uid, "alt": alt, "name": nm, "groupid": gid, "clanid": cid}
        else:
            return {}
    
    @staticmethod
    def unpack_memberinfo(memberinfo : Dict) -> Tuple:
        if memberinfo:
            return (memberinfo["userid"], memberinfo["alt"], memberinfo["name"], memberinfo["groupid"], memberinfo["clanid"])
        else:
            return ()

    @staticmethod
    def gen_condition_sql(userid : Optional[int] = None, groupid : Optional[int] = None, clanid : Optional[int] = None) -> Tuple[str, Tuple]:
        """Generate condition SQL statement after WHERE and corresponding parameter set"""
        condition_sql, condition_paras = [], []
        if userid is not None:
            condition_sql.append("userid=?")
            condition_paras.append(userid)
        if groupid is not None:
            condition_sql.append("groupid=?")
            condition_paras.append(groupid)
        if clanid is not None:
            condition_sql.append("clanid=?")
            condition_paras.append(clanid)
        return " AND ".join(condition_sql), tuple(condition_paras)

    
    def add(self, memberinfo: Dict):
        sql = f"INSERT INTO {self._table} ({self._columns}) VALUES (?, ?, ?, ?, ?)"
        with self._connect() as conn:
            try:
                conn.execute(sql, self.unpack_memberinfo(memberinfo))
            except sqlite3.DatabaseError as err:
                logger.error("[MemberDB.add Failed] " + str(err))
                raise DatabaseError(L["ADD_MEMBER_FAILED"])
    
    def remove(self, userid : int, alt : int):
        sql = f"DELETE FROM {self._table} WHERE userid=? AND alt=?"
        with self._connect() as conn:
            try:
                conn.execute(sql, (userid, alt))
            except sqlite3.DatabaseError as err:
                logger.error("[MemberDB.remove Failed] " + str(err))
                raise DatabaseError(L["REMOVE_MEMBER_FAILED"])
    
    def modify(self, memberinfo: Dict):
        sql = f"UPDATE {self._table} SET name=?, groupid=?, clanid=? WHERE userid=? AND alt=?"
        with self._connect() as conn:
            try:
                paras = self.unpack_memberinfo(memberinfo)
                conn.execute(sql, (*paras[2:], *paras[:2]))
            except sqlite3.DatabaseError as err:
                logger.error("[MemberDB.modify Failed] " + str(err))
                raise DatabaseError(L["MODIFY_MEMBER_FAILED"])
    
    def find_one(self, userid : int, alt : int):
        sql = f"SELECT {self._columns} FROM {self._table} WHERE userid=? AND alt=?"
        with self._connect() as conn:
            try:
                record = conn.execute(sql, (userid, alt)).fetchone()
                return self.pack_memberinfo(record)
            except sqlite3.DatabaseError as err:
                logger.error("[MemberDB.find_one Failed] " + str(err))
                raise DatabaseError(L["SEARCH_MEMBER_FAILED"])
    
    def find_all(self) -> List:
        sql = f"SELECT {self._columns} FROM {self._table}"
        with self._connect() as conn:
            try:
                records = conn.execute(sql).fetchall()
                return [self.pack_memberinfo(record) for record in records]
            except sqlite3.DatabaseError as err:
                logger.error("[MemberDB.find_all Failed] " + str(err))
                raise DatabaseError(L["SEARCH_MEMBER_FAILED"])
    
    def find_by(self, userid : Optional[int] = None, groupid : Optional[int] = None, clanid : Optional[int] = None) -> List:
        """Search all members that match the given condition"""
        sql, paras = self.gen_condition_sql(userid, groupid, clanid)
        if len(paras) != 0:
            sql = f"SELECT {self._columns} FROM {self._table} WHERE {sql}"
            with self._connect() as conn:
                try:
                    records = conn.execute(sql, paras).fetchall()
                    return [self.pack_memberinfo(record) for record in records]
                except sqlite3.DatabaseError as err:
                    logger.error("[MemberDB.find_by Failed] " + str(err))
                    raise DatabaseError(L["SEARCH_MEMBER_FAILED"])
        else:
            return self.find_all()
    
    def remove_by(self, userid : Optional[int] = None, groupid : Optional[int] = None, clanid : Optional[int] = None) -> int:
        """Remove all members that match the given condition"""
        sql, paras = self.gen_condition_sql(userid, groupid, clanid)
        if len(paras) != 0:
            sql = f"DELETE FROM {self._table} WHERE {sql}"
            with self._connect() as conn:
                try:
                    cursor = conn.execute(sql, paras)
                    return cursor.rowcount
                except sqlite3.DatabaseError as err:
                    logger.error("[MemberDB.remove_by Failed] " + str(err))
                    raise DatabaseError(L["REMOVE_MEMBER_FAILED"])
        else:
            raise DatabaseError(L["WRONG_FILTER_MEMBER_CONDITION"])


class ClanBattleDB(PCRsqlite):
    """Database class for clan battle records management"""
    def __init__(self, tablename):
        """Create a database table with clan battle data.
        
        The table is built with the following columns:
        Columns   Description              Type        NotNull   PK
        rid       Record ID for each run   INTEGER     True      True
        userid    QQ user number           INT         True      False
        alt       User group chat ID       INT         True      False
        time      Record submit time       TIMESTAMP   True      False
        round     Record round number      INT         True      False
        boss      Record boss number       INT         True      False
        damage    Record damage            INT         True      False
        flag      Record type (0=normal,   INT         True      False
                  1=tail,2=leftover,
                  3=lost)
        """
        super().__init__(
            table=tablename,
            columns="rid, userid, alt, time, round, boss, damage, flag",
            fields='''
rid     INTEGER   PRIMARY KEY AUTOINCREMENT,
userid  INT       NOT NULL,
alt     INT       NOT NULL,
time    TIMESTAMP NOT NULL,
round   INT       NOT NULL,
boss    INT       NOT NULL,
damage  INT       NOT NULL,
flag    INT       NOT NULL''')
    
    @staticmethod
    def set_table_name(groupid : int, clanid : int, year : int, month : int) -> str:
        """Determine the standard table name by group ID, clan ID and clan date"""
        return f'clanbattle_{groupid}_{clanid}_{year:04d}{month:02d}'
    
    @staticmethod
    def pack_battleinfo(record : Tuple) -> Dict:
        if record:
            rid, uid, alt, t, r, b, d, flag = record
            return {"rid": rid, "userid": uid, "alt": alt, "time": t, "round": r, "boss": b, "damage": d, "flag": flag}
        else:
            return {}
    
    @staticmethod
    def unpack_battleinfo(battleinfo : Dict) -> Tuple:
        if (binfo := battleinfo):
            rid = binfo["rid"] if "rid" in binfo else 0
            return (rid, binfo["userid"], binfo["alt"], binfo["time"], binfo["round"], binfo["boss"], binfo["damage"], binfo["flag"])
        else:
            return ()

    @staticmethod
    def gen_condition_sql(userid : Optional[int] = None, alt : Optional[int] = None) -> Tuple[str, Tuple]:
        """Generate condition SQL statement after WHERE and corresponding parameter set"""
        condition_sql, condition_paras = [], []
        if userid is not None:
            condition_sql.append("userid=?")
            condition_paras.append(userid)
        if alt is not None:
            condition_sql.append("alt=?")
            condition_paras.append(alt)
        return " AND ".join(condition_sql), tuple(condition_paras)

    
    def add(self, battleinfo : Dict) -> int:
        sql = f"INSERT INTO {self._table} ({self._columns}) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)"
        with self._connect() as conn:
            try:
                cursor = conn.execute(sql, self.unpack_battleinfo(battleinfo)[1:])
                return cursor.lastrowid
            except sqlite3.DatabaseError as err:
                logger.error("[ClanBattleDB.add Failed] " + str(err))
                raise DatabaseError(L["ADD_RECORD_FAILED"])
    
    def remove(self, rid : int):
        sql = f"DELETE FROM {self._table} WHERE rid=?"
        with self._connect() as conn:
            try:
                conn.execute(sql, (rid,))
            except sqlite3.DatabaseError as err:
                logger.error("[ClanBattleDB.remove Failed] " + str(err))
                raise DatabaseError(L["REMOVE_RECORD_FAILED"])
    
    def modify(self, battleinfo: Dict):
        sql = f"UPDATE {self._table} SET userid=?, alt=?, time=?, round=?, boss=?, damage=?, flag=? WHERE rid=?"
        with self._connect() as conn:
            try:
                paras = self.unpack_battleinfo(battleinfo)
                conn.execute(sql, (*paras[1:], paras[0]))
            except sqlite3.DatabaseError as err:
                logger.error("[ClanBattleDB.modify Failed] " + str(err))
                raise DatabaseError(L["MODIFY_RECORD_FAILED"])
    
    def find_one(self, rid : int):
        sql = f"SELECT {self._columns} FROM {self._table} WHERE rid=?"
        with self._connect() as conn:
            try:
                record = conn.execute(sql, (rid,)).fetchone()
                return self.pack_battleinfo(record)
            except sqlite3.DatabaseError as err:
                logger.error("[ClanBattleDB.find_one Failed] " + str(err))
                raise DatabaseError(L["SEARCH_RECORD_FAILED"])
    
    def find_all(self) -> List:
        sql = f"SELECT {self._columns} FROM {self._table} ORDER BY round, boss, rid"
        with self._connect() as conn:
            try:
                records = conn.execute(sql).fetchall()
                return [self.pack_battleinfo(record) for record in records]
            except sqlite3.DatabaseError as err:
                logger.error("[ClanBattleDB.find_all Failed] " + str(err))
                raise DatabaseError(L["SEARCH_RECORD_FAILED"])
    
    def find_by(self, userid : Optional[int] = None, alt : Optional[int] = None, order_by_user: bool = False) -> List:
        """Search all records that match the given condition"""
        sql, paras = self.gen_condition_sql(userid, alt)
        order = "userid, alt, round, boss, rid" if order_by_user else "round, boss, rid"
        if len(paras) != 0:
            sql = f"SELECT {self._columns} FROM {self._table} WHERE {sql} ORDER BY {order}"
            with self._connect() as conn:
                try:
                    records = conn.execute(sql, paras).fetchall()
                    return [self.pack_battleinfo(record) for record in records]
                except sqlite3.DatabaseError as err:
                    logger.error("[ClanBattleDB.find_by Failed] " + str(err))
                    raise DatabaseError(L["SEARCH_RECORD_FAILED"])
        else:
            return self.find_all()

class SubscribeDB(PCRsqlite):
    """Database class for clan battle subscribe management"""
    def __init__(self, tablename):
        """Create a database table with clan battle subscribe data
        
        The table is built with the following columns:
        Columns   Description              Type        NotNull   PK
        sid       Subscribe ID             INTEGER     True      True
        userid    QQ user number           INT         True      False
        alt       User group chat ID       INT         True      False
        time      Subscribe submit time    TIMESTAMP   True      False
        round     Subscribe round number   INT         True      False
        boss      Subscribe boss number    INT         True      False
        flag      Subscribe type           INT         True      False
                  (0=normal, 1=whole,
                  2=cancel, 3=finished,
                  4=ontree, 5=locked)
        msg       Additional message       TEXT        True      False
        """
        super().__init__(
            table=tablename,
            columns="sid, userid, alt, time, round, boss, flag, msg",
            fields='''
sid     INTEGER   PRIMARY KEY AUTOINCREMENT,
userid  INT       NOT NULL,
alt     INT       NOT NULL,
time    TIMESTAMP NOT NULL,
round   INT       NOT NULL,
boss    INT       NOT NULL,
flag    INT       NOT NULL,
msg     TEXT      NOT NULL''')

    @staticmethod
    def set_table_name(groupid : int, clanid : int, year : int, month : int) -> str:
        """Determine the standard table name by group ID, clan ID and clan date"""
        return f'subscribe_{groupid}_{clanid}_{year:04d}{month:02d}'

    @staticmethod
    def pack_subscribeinfo(record : Tuple) -> Dict:
        if record:
            sid, uid, alt, t, r, b, flag, msg = record
            return {"sid": sid, "userid": uid, "alt": alt, "time": t, "round": r, "boss": b, "flag": flag, "msg": msg}
        else:
            return {}
    
    @staticmethod
    def unpack_subscribeinfo(subscribeinfo : Dict) -> Tuple:
        if (sinfo := subscribeinfo):
            sid = sinfo["sid"] if "sid" in sinfo else 0
            return (sid, sinfo["userid"], sinfo["alt"], sinfo["time"], sinfo["round"], sinfo["boss"], sinfo["flag"], sinfo["msg"])
        else:
            return ()
    
    @staticmethod
    def gen_condition_sql(userid : Optional[int] = None, alt : Optional[int] = None, round_ : Optional[int] = None, boss : Optional[int] = None, flag : Optional[int] = None) -> Tuple[str, Tuple]:
        """Generate condition SQL statement after WHERE and corresponding parameter set"""
        condition_sql, condition_paras = [], []
        if userid is not None:
            condition_sql.append("userid=?")
            condition_paras.append(userid)
        if alt is not None:
            condition_sql.append("alt=?")
            condition_paras.append(alt)
        if round_ is not None:
            condition_sql.append("round=?")
            condition_paras.append(round_)
        if boss is not None:
            condition_sql.append("boss=?")
            condition_paras.append(boss)
        if flag is not None:
            condition_sql.append("flag=?")
            condition_paras.append(flag)
        return " AND ".join(condition_sql), tuple(condition_paras)

    def add(self, subscribeinfo: Dict) -> int:
        sql = f"INSERT INTO {self._table} ({self._columns}) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)"
        with self._connect() as conn:
            try:
                cursor = conn.execute(sql, self.unpack_subscribeinfo(subscribeinfo)[1:])
                return cursor.lastrowid
            except sqlite3.DatabaseError as err:
                logger.error("[SubscribeDB.add Failed] " + str(err))
                raise DatabaseError(L["ADD_SUBSCRIBE_FAILED"])
    
    def remove(self, sid : int):
        sql = f"DELETE FROM {self._table} WHERE sid=?"
        with self._connect() as conn:
            try:
                conn.execute(sql, (sid,))
            except sqlite3.DatabaseError as err:
                logger.error("[SubscribeDB.remove Failed] " + str(err))
                raise DatabaseError(L["REMOVE_SUBSCRIBE_FAILED"])
    
    def modify(self, subscribeinfo: Dict):
        sql = f"UPDATE {self._table} SET userid=?, alt=?, time=?, round=?, boss=?, flag=?, msg=? WHERE sid=?"
        with self._connect() as conn:
            try:
                paras = self.unpack_subscribeinfo(subscribeinfo)
                conn.execute(sql, (*paras[1:], paras[0]))
            except sqlite3.DatabaseError as err:
                logger.error("[SubscribeDB.modify Failed] " + str(err))
                raise DatabaseError(L["MODIFY_SUBSCRIBE_FAILED"])
    
    def find_one(self, sid : int):
        sql = f"SELECT {self._columns} FROM {self._table} WHERE sid=?"
        with self._connect() as conn:
            try:
                record = conn.execute(sql, (sid,)).fetchone()
                return self.pack_subscribeinfo(record)
            except sqlite3.DatabaseError as err:
                logger.error("[SubscribeDB.find_one Failed] " + str(err))
                raise DatabaseError(L["SEARCH_SUBSCRIBE_FAILED"])
    
    def find_all(self) -> List:
        sql = f"SELECT {self._columns} FROM {self._table}"
        with self._connect() as conn:
            try:
                records = conn.execute(sql).fetchall()
                return [self.pack_subscribeinfo(record) for record in records]
            except sqlite3.DatabaseError as err:
                logger.error("[SubscribeDB.find_all Failed] " + str(err))
                raise DatabaseError(L["SEARCH_SUBSCRIBE_FAILED"])
    
    def find_by(self, userid : Optional[int] = None, alt : Optional[int] = None, round_ : Optional[int] = None, boss : Optional[int] = None, flag : Optional[int] = None) -> List:
        """Search all records that match the given condition"""
        sql, paras = self.gen_condition_sql(userid=userid, alt=alt, round_=round_, boss=boss, flag=flag)
        if len(paras) != 0:
            sql = f"SELECT {self._columns} FROM {self._table} WHERE {sql}"
            with self._connect() as conn:
                try:
                    records = conn.execute(sql, paras).fetchall()
                    return [self.pack_subscribeinfo(record) for record in records]
                except sqlite3.DatabaseError as err:
                    logger.error("[SubscribeDB.find_by Failed] " + str(err))
                    raise DatabaseError(L["SEARCH_SUBSCRIBE_FAILED"])
    
    def remove_by(self, userid : Optional[int] = None, alt : Optional[int] = None, round_ : Optional[int] = None, boss : Optional[int] = None, flag : Optional[int] = None):
        """Remove all members that match the given condition"""
        sql, paras = self.gen_condition_sql(userid=userid, alt=alt, round_=round_, boss=boss, flag=flag)
        if len(paras) != 0:
            sql = f"DELETE FROM {self._table} WHERE {sql}"
            with self._connect() as conn:
                try:
                    cursor = conn.execute(sql, paras)
                    return cursor.rowcount
                except sqlite3.DatabaseError as err:
                    logger.error("[SubscribeDB.remove_by Failed] " + str(err))
                    raise DatabaseError(L["REMOVE_SUBSCRIBE_FAILED"])
        else:
            raise DatabaseError(L["WRONG_FILTER_SUBSCRIBE_CONDITION"])
