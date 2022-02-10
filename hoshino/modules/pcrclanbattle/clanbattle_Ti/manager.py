from ast import Sub
from datetime import datetime, timezone, timedelta
from typing import Dict, Iterable, List, Tuple, Optional

from hoshino import util
from hoshino.modules.pcrclanbattle.clanbattle.cmdv2 import subscribe

from .aliases import ServerCode, RecordFlag, SubscribeFlag
from .argtype import check_server_name
from .database import ClanDB, MemberDB, ClanBattleDB, SubscribeDB
from .exceptions import NotFoundError, ParseError


config = util.load_config(__file__)
lang = config["LANG"]
L = util.load_localisation(__file__)[lang]   # Short of localisation


class ClanBattleManager(object):
    """Core PCR clan battle manager"""

    def __init__(self, grp):
        """Each manager class is bound with a QQ group chat"""
        self.groupid = grp
        self.clan = ClanDB()
        self.members = MemberDB()

    @staticmethod
    def UTC_delta(server):
        """Determine UTC delta hours according to server"""
        return 9 if server == ServerCode.SERVER_JP.value else 8

    @staticmethod
    def get_clandate(time: datetime, hourdelta: int) -> Tuple[int, int, int]:
        """Convert natural time to PCR Clan Clock

        PCR clan data update at localtime 5 a.m..
        Each clan day starts from 5 a.m. UTC+N (N=8 for CN,TW and N=9 fir JP)
        Therefore, natural time 5 a.m. UTC+N -> 0 a.m. (PCR Clan Clock)
        Each clan month starts from MM 20th to MM+1 10th
        For example, natural time Sept. 2nd, 2019 4 a.m. -> Aug. 1st, 2019 23 p.m. (PCR Clan Clock)
        """
        ctime = time.astimezone(timezone(timedelta(hours=hourdelta - 5)))
        year = ctime.year
        month = ctime.month
        day = ctime.day
        if day < 21:
            month -= 1
        if month < 1:
            month = 12
            year -= 1
        return (year, month, day)

    @staticmethod
    def next_boss(rcode: int, bcode: int) -> Tuple[int, int]:
        return (rcode, bcode + 1) if bcode < 5 else (rcode + 1, 1)

    @staticmethod
    def get_server_table(server: int) -> Dict:
        """Load server table from config JSON according to server"""
        tag = check_server_name(server)
        if tag != "UNKNOWN":
            return config["SERVER_" + tag]
        else:
            raise ParseError(L["INVALID_SERVER_CODE"])

    @staticmethod
    def current_tier(rcode: int, server: int) -> int:
        table = ClanBattleManager.get_server_table(server)
        for tier in table:
            if (rcode >= tier["START_ROUND"]) and ((rcode <= tier["END_ROUND"]) or (tier["END_ROUND"] == -1)):
                return tier["TIER"]
        return 0

    @staticmethod
    def get_boss_info(rcode: int, bcode: int, server: int) -> Tuple[int, float]:
        """Get boss total HP and score rate"""
        tier = ClanBattleManager.current_tier(rcode, server)
        if tier == 0:
            raise ParseError(L["INVALID_TIER"])
        table = ClanBattleManager.get_server_table(server)
        tierinfo = table[tier - 1]
        if tierinfo["TIER"] != tier:
            raise ParseError(L["INVALID_TIER"])
        if (bcode < 1) or (bcode > 5):
            raise ParseError(L["INVALID_BOSS_CODE"])
        # Boss code ranges from 1 to 5, index starts from 0
        boss_hp = tierinfo["BOSS_HP"][bcode - 1]
        score_rate = tierinfo["SCORE_RATE"][bcode - 1]
        return (boss_hp, score_rate)

    @staticmethod
    def cal_score(rcode: int, bcode: int, damage: int, server: int) -> int:
        """Record score = score rate x damage"""
        _, score_rate = ClanBattleManager.get_boss_info(rcode, bcode, server)
        return round(score_rate * damage)

    def fetch_battle_record(self, clanid: int, time: datetime) -> ClanBattleDB:
        """Returns battle record data handler from current group ID, clan ID and clan date"""
        server = self.fetch_clan(clanid)["server"]
        hourdelta = self.UTC_delta(server)
        year, month, _ = self.get_clandate(time, hourdelta)
        tablename = ClanBattleDB.set_table_name(
            groupid=self.groupid, clanid=clanid, year=year, month=month)
        return ClanBattleDB(tablename)

    def fecth_subscribe_tree(self, clanid: int, time: datetime) -> SubscribeDB:
        """Returns subscribe data handler from current group ID, clan ID and clan date"""
        server = self.fetch_clan(clanid)["server"]
        hourdelta = self.UTC_delta(server)
        year, month, _ = self.get_clandate(time, hourdelta)
        tablename = SubscribeDB.set_table_name(
            groupid=self.groupid, clanid=clanid, year=year, month=month)
        return SubscribeDB(tablename)

    # -*- CLAN OPERATIONS -*-
    def add_clan(self, clanid: int, name: str, server: int):
        return self.clan.add(ClanDB.pack_claninfo(self.groupid, clanid, name, server))

    def remove_clan(self, clanid: int):
        return self.clan.remove(self.groupid, clanid)

    def modify_clan(self, clanid: int, name: str, server: int):
        return self.clan.modify(ClanDB.pack_claninfo(self.groupid, clanid, name, server))

    def fetch_clan(self, clanid: int):
        return self.clan.find_one(clanid)

    def check_clan(self, clanid: int) -> bool:
        return True if self.fetch_clan(clanid) else False

    def fetch_clan_with_check(self, clanid: int):
        if (clan := self.fetch_clan(clanid)):
            return clan
        else:
            raise NotFoundError(L["CLAN_NOT_FOUND"])

    def list_clans(self):
        return self.clan.find_by_groupid(self.groupid)
    # -*- CLAN OPERATIONS END -*-

    # -*- MEMBER OPERATIONS -*-
    def add_member(self, userid: int, alter: int, name: str, clanid: int):
        return self.members.add(MemberDB.pack_memberinfo(userid, alter, name, self.groupid, clanid))

    def remove_member(self, userid: int, alter: int):
        return self.members.remove(userid, alter)

    def clear_members(self, clanid: Optional[int] = None):
        return self.members.remove_by(groupid=self.groupid, clanid=clanid)

    def modify_member(self, userid: int, alter: int, name: str, clanid: int):
        return self.members.modify(MemberDB.pack_memberinfo(userid, alter, name, self.groupid, clanid))

    def fetch_member(self, userid: int, alter: int):
        return member if (member := self.members.find_one(userid, alter)) and member["groupid"] == self.groupid else None

    def check_member(self, userid: int, alter: int) -> bool:
        return True if self.fetch_member(userid, alter) else False

    def list_members(self, clanid: Optional[int] = None) -> List:
        return self.members.find_by(groupid=self.groupid, clanid=clanid)

    def list_accounts(self, userid: Optional[int] = None) -> List:
        return self.members.find_by(groupid=self.groupid, userid=userid)
    # -*- MEMBER OPERATIONS END -*-

    # -*- RUN OPERATIONS -*-
    def add_run(self, userid: int, alter: int, time: datetime, rcode: int, bcode: int, damage: int, flag: int):
        if member := self.fetch_member(userid, alter):
            record = self.fetch_battle_record(member["clanid"], time)
            return record.add(ClanBattleDB.pack_battleinfo((0, userid, alter, time, rcode, bcode, damage, flag)))
        else:
            raise NotFoundError(L["MEMBER_NOT_FOUND"])

    def remove_run(self, rid: int, clanid: int, time: datetime):
        record = self.fetch_battle_record(clanid, time)
        return record.remove(rid)

    def modify_run(self, rid: int, userid: int, alter: int, time: datetime, rcode: int, bcode: int, damage: int, flag: int):
        if member := self.fetch_member(userid, alter):
            record = self.fetch_battle_record(member["clanid"], time)
            return record.modify(ClanBattleDB.pack_battleinfo((rid, userid, alter, time, rcode, bcode, damage, flag)))
        else:
            raise NotFoundError(L["MEMBER_NOT_FOUND"])

    def fetch_run(self, rid: int, clanid: int, time: datetime):
        record = self.fetch_battle_record(clanid, time)
        return record.find_one(rid)

    def list_run(self, clanid: int, time: datetime) -> List:
        record = self.fetch_battle_record(clanid, time)
        return record.find_all()

    def list_run_by_user(self, userid: int, alter: int, time: datetime) -> List:
        if member := self.fetch_member(userid, alter):
            record = self.fetch_battle_record(member["clanid"], time)
            return record.find_by(userid=userid, alter=alter)
        else:
            raise NotFoundError(L["MEMBER_NOT_FOUND"])

    @staticmethod
    def filter_run_by_day(run_list: Iterable, time: datetime, hourdelta: int) -> List:
        _, _, day = ClanBattleManager.get_clandate(time, hourdelta)
        return list(filter(lambda run: ClanBattleManager.get_clandate(run["time"], hourdelta)[-1] == day, run_list))

    def list_run_by_day(self, clanid: int, time: datetime, hourdelta: int):
        return self.filter_run_by_day(
            run_list=self.list_run(clanid, time),
            time=time,
            hourdelta=hourdelta)

    def list_run_by_user_day(self, userid: int, alter: int, time: datetime, hourdelta: int) -> List:
        return self.filter_run_by_day(
            run_list=self.list_run_by_user(userid, alter, time),
            time=time, hourdelta=hourdelta)
    # -*- RUN OPERATIONS END -*-

    # -*- SUMMARY OPERATIONS -*-
    def sum_run(self, clanid: int, time: datetime, hourdelta: int, one_day_only: bool = True) -> List[Tuple]:
        res = []
        members = self.list_members(clanid)
        record = self.fetch_battle_record(clanid, time)
        for member in members:
            run_list = record.find_by(
                userid=member["userid"], alter=member["alter"])
            if one_day_only:
                run_list = self.filter_run_by_day(
                    run_list=run_list, time=time, hourdelta=hourdelta)
            res.append((member, run_list))
        return res

    def sum_damage(self, clanid: int, time: datetime) -> List[Tuple]:
        clan = self.fetch_clan_with_check(clanid)
        hourdelta = self.UTC_delta(clan["server"])
        res = []
        for member, run_list in self.sum_run(clanid=clanid, time=time, hourdelta=hourdelta, one_day_only=False):
            damages = [0 for _ in range(6)]
            for run in run_list:
                damage = run["damage"]
                damages[0] += damage
                damages[run["boss"]] += damage
            res.append((member["userid"], member["alter"],
                       member["name"], damages))
        return res

    def sum_score(self, clanid: int, time: datetime) -> List[Tuple]:
        clan = self.fetch_clan_with_check(clanid)
        hourdelta = self.UTC_delta(clan["server"])
        res = []
        for member, run_list in self.sum_run(clanid=clanid, time=time, hourdelta=hourdelta, one_day_only=False):
            score = sum([self.cal_score(record["round"], record["boss"],
                        record["damage"], clan["server"]) for record in run_list])
            res.append(
                (member["userid"], member["alter"], member["name"], score))
        return res

    @staticmethod
    def sum_run_list(run_list: Iterable) -> Tuple[int, int, int, int]:
        """
        Summarize count of each flag types in given run list.        

        Count results are given as normal, tail, leftover, lost.
        """
        normal, tail, leftover, lost = 0, 0, 0, 0
        for record in run_list:
            flag = record["flag"]
            if flag == RecordFlag.TAIL.value:
                tail += 1
            elif flag == RecordFlag.LEFTOVER.value:
                leftover += 1
            elif flag == RecordFlag.LOST.value:
                lost += 1
            else:
                normal += 1
        return normal, tail, leftover, lost

    def list_remain_run(self, clanid: int, time: datetime) -> List[Tuple]:
        """
        Summarize count of remain run and leftover.

        Remain run is marked as remain, and remain leftover is marked as rleftover.
        Total length of run list = normal + tail + leftover + lost
        remain = 3 - (normal + lost + tail)
        rleftover = tail - leftover
        """
        clan = self.fetch_clan_with_check(clanid)
        hourdelta = self.UTC_delta(clan["server"])
        res = []
        for member, run_list in self.sum_run(clanid=clanid, time=time, hourdelta=hourdelta, one_day_only=True):
            normal, tail, leftover, lost = self.sum_run_list(run_list)
            remain = 3 - (normal + lost + tail)
            rleftover = tail - leftover
            res.append((member["userid"], member["alter"],
                       member["name"], remain, rleftover))
        return res

    def check_progress(self, clanid: int, time: datetime) -> Tuple[int, int, int]:
        """
        Check current round and boss progress.

        Current round and boss are determined by the last submitted record.
        """
        clan = self.fetch_clan_with_check(clanid)
        record = self.fetch_battle_record(clanid, time)
        run_list = record.find_all()
        current_round, current_boss = 1, 1
        remain_hp, _ = self.get_boss_info(
            current_round, current_boss, clan["server"])
        if len(run_list) != 0:
            current_round = run_list[-1]["round"]
            current_boss = run_list[-1]["boss"]
        for run in reversed(run_list):
            if run["round"] == current_round and run["boss"] == current_boss:
                remain_hp -= run["damage"]
        return (current_round, current_boss, remain_hp)
    # -*- SUMMARY OPERATIONS END -*-

    # -*- SUBSCRIBE OPERATIONS -*-
    def add_subscribe(self, userid: int, alter: int, time: datetime, rcode: int, bcode: int, flag: int, msg: str):
        if member := self.fetch_member(userid, alter):
            tree = self.fecth_subscribe_tree(member["clanid"], time)
            return tree.add(SubscribeDB.pack_subscribeinfo((0, userid, alter, time, rcode, bcode, flag, msg)))
        else:
            raise NotFoundError(L["MEMBER_NOT_FOUND"])

    def remove_subscribe(self, sid: int, clanid: int, time: datetime):
        tree = self.fecth_subscribe_tree(clanid, time)
        return tree.remove(sid)

    def modify_subscribe(self, sid: int, userid: int, alter: int, time: datetime, rcode: int, bcode: int, flag: int, msg: str):
        if member := self.fetch_member(userid, alter):
            tree = self.fecth_subscribe_tree(member["clanid"], time)
            return tree.modify(SubscribeDB.pack_subscribeinfo((sid, userid, alter, time, rcode, bcode, flag, msg)))
        else:
            raise NotFoundError(L["MEMBER_NOT_FOUND"])

    def fetch_subscribe(self, sid: int, clanid: int, time: datetime):
        tree = self.fecth_subscribe_tree(clanid, time)
        return tree.find_one(sid)

    def list_subscribes(self, clanid: int, time: datetime) -> List:
        tree = self.fecth_subscribe_tree(clanid, time)
        return tree.find_all()

    def list_subscribes_by_user(self, userid: int, alter: int, time: datetime) -> List:
        if member := self.fetch_member(userid, alter):
            tree = self.fecth_subscribe_tree(member["clanid"], time)
            return tree.find_by(userid=userid, alter=alter)
        else:
            raise NotFoundError(L["MEMBER_NOT_FOUND"])

    @staticmethod
    def filter_subscribes_by_day(subscribes_list: Iterable, time: datetime, hourdelta: int) -> List:
        _, _, day = ClanBattleManager.get_clandate(time, hourdelta)
        return list(filter(lambda subscribe: ClanBattleManager.get_clandate(subscribe["time"], hourdelta)[-1] == day, subscribes_list))

    def list_subscribes_by_day(self, clanid: int, time: datetime, hourdelta: int) -> List:
        return self.filter_subscribes_by_day(
            subscribes_list=self.list_subscribes(clanid, time),
            time=time, hourdelta=hourdelta)

    def list_subscribes_by_user_day(self, userid: int, alter: int, time: datetime, hourdelta: int) -> List:
        return self.filter_subscribes_by_day(
            subscribes_list=self.list_subscribes_by_user(userid, alter, time),
            time=time, hourdelta=hourdelta)

    @staticmethod
    def conditional_filter_subscribes(subscribes_list: Iterable, rcode: Optional[int] = None, bcode: Optional[int] = None, flags: Iterable[int] = ()) -> List:
        res = subscribes_list
        if rcode is not None:
            res = list(
                filter(lambda subscribe: subscribe["round"] == rcode, res))
        if bcode is not None:
            res = list(
                filter(lambda subscribe: subscribe["boss"] == bcode, res))
        if len(flags) != 0:
            res = list(
                filter(lambda subscribe: subscribe["flag"] in flags, res))
        return res

    def list_subscribes_active(self, clanid: int, time: datetime, hourdelta: int, one_day_only: bool = True) -> List:
        """List all active subscribes (including normal, whole)"""
        filter_res = self.list_subscribes_by_day(
            clanid, time, hourdelta) if one_day_only else self.list_subscribes(clanid, time)
        return self.conditional_filter_subscribes(
            subscribes_list=filter_res,
            flags=(SubscribeFlag.NORMAL.value, SubscribeFlag.WHOLE.value))

    def list_subscribes_by_detail(self, userid: int, alter: int, time: datetime, rcode: int, bcode: int) -> List:
        """Check whether user has already subscribed target boss"""
        return self.conditional_filter_subscribes(
            subscribes_list=self.list_subscribes_by_user(userid, alter, time),
            rcode=rcode, bcode=bcode,
            flags=(SubscribeFlag.NORMAL.value, SubscribeFlag.WHOLE.value))

    def list_subscribes_by_boss(self, clanid: int, time: datetime, rcode: int, bcode: int) -> List:
        """List all active subscribes of target boss"""
        return self.conditional_filter_subscribes(
            subscribes_list=self.list_subscribes(clanid, time),
            rcode=rcode, bcode=bcode,
            flags=(SubscribeFlag.NORMAL.value, SubscribeFlag.WHOLE.value))

    def list_subscribes_ontree(self, clanid: int, time: datetime, rcode: int, bcode: int) -> List:
        """List all subscribes (with user information) on tree of target boss"""
        return self.conditional_filter_subscribes(
            subscribes_list=self.list_subscribes(clanid, time),
            rcode=rcode, bcode=bcode,
            flags=(SubscribeFlag.ONTREE.value,))
    
    def list_subscribes_locked(self, clanid: int, time: datetime, rcode: int, bcode: int) -> List:
        """List all locked boss subscribes"""
        return self.conditional_filter_subscribes(
            subscribes_list=self.list_subscribes(clanid, time),
            rcode=rcode, bcode=bcode,
            flags=(SubscribeFlag.LOCKED.value))

    def check_boss_locked(self, clanid: int, time: datetime, rcode: int, bcode: int) -> bool:
        """Check whether target boss is locked"""
        return len(self.list_subscribes_locked(clanid, time, rcode, bcode)) != 0

    def unlock_boss(self, clanid: int, time: datetime, rcode: int, bcode: int):
        """Change locked subscribe flag to finished"""
        filter_res = self.conditional_filter_subscribes(
            subscribes_list=self.list_subscribes(clanid, time),
            rcode=rcode, bcode=bcode,
            flags=(SubscribeFlag.LOCKED.value,))
        for record in filter_res:
            record["flag"] = SubscribeFlag.FINISHED.value
            self.modify_subscribe(**record)

    # -*- SUBSCRIBE OPERATIONS END -*-
