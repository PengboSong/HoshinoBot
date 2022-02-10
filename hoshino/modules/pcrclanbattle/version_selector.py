from hoshino import Service, priv, util
from hoshino.typing import CQEvent

lang = "zh-CN"
L = util.load_localisation(__file__)[lang]

sv = Service('clanbattle-version-selector',
             manage_priv=priv.SUPERUSER, visible=False)

HELP_DESC = f'''
{L["TIP_SELECT_VERSION_PERMISSION_REQUIRED"]}
【{L["USAGE_SELECT_VERSION"]}{L["VERSION_OPEN_SOURCE"]}】
{L["DESC_OPEN_SOURCE"]}
{L["DESC_OLD_CLAN_BATTLE"]}

【{L["USAGE_SELECT_VERSION"]}{L["VERSION_CLOSED_SOURCE"]}】
{L["DESC_CLOSED_SOURCE"]}
{L["DESC_OLD_CLAN_BATTLE"]}

【{L["USAGE_SELECT_VERSION"]}{L["VERSION_CLOSED_SOURCE_WEB"]}】
{L["DESC_CLOSED_SOURCE_WEB"]}
{L["DESC_NEW_CLAN_BATTLE"]}

【{L["USAGE_SELECT_VERSION"]}{L["VERSION_TI"]}】
{L["DESC_TI"]}
{L["DESC_OLD_CLAN_BATTLE"]}
'''.strip()


@sv.on_prefix(*L["CMD_SELECT_VERSION"])
async def select_version(bot, ev: CQEvent):
    gid = ev.group_id
    arg = ev.message.extract_plain_text()
    svs = Service.get_loaded_services()
    cbsvs = {
        L["VERSION_OPEN_SOURCE"]: svs.get('clanbattle'),
        L["VERSION_CLOSED_SOURCE"]: svs.get('clanbattlev3'),
        L["VERSION_CLOSED_SOURCE_WEB"]: svs.get('clanbattlev4'),
        L["VERSION_TI"]: svs.get('clanbattle-Ti'),
    }
    if arg not in cbsvs:
        await bot.finish(ev, HELP_DESC)
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, L["INFO_SELECT_VERSION_PERMISSION_DENIED"])
    if not cbsvs[arg]:
        await bot.finish(ev, L["INFO_SELECT_VERSION_MODULE_MISSING"].format(arg))
    for k, v in cbsvs.items():
        if v is not None:
            v.set_enable(gid) if k == arg else v.set_disable(gid)
    await bot.send(ev, L["INFO_SELECT_VERSION_SUCCESS"].format(arg, cbsvs[arg].help))
