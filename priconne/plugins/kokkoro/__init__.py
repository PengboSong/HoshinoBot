import re
import logging
from nonebot import on_command, CommandSession, MessageSegment
from nonebot.permission import GROUP_MEMBER, GROUP_ADMIN
from aiocqhttp.exceptions import ActionFailed
from .gacha import Gacha
from .arena import Arena
from ..util import delete_msg, silence, get_cqimg, CharaHelper, USE_PRO_VERSION


@on_command('十连', aliases=('十连抽', '来个十连', '来发十连', '十连扭蛋'), only_to_me=False)
async def gacha_10(session:CommandSession):
    at = str(MessageSegment.at(session.ctx['user_id']))
    
    gacha = Gacha()
    result, hiishi = gacha.gacha_10()
    silence_time = hiishi * 6 if hiishi < 200 else hiishi * 60

    if USE_PRO_VERSION:
        # 转成CQimg
        result = [ CharaHelper.get_id(x) for x in result ]
        res1 = CharaHelper.gen_team_pic(result[ :5])
        res2 = CharaHelper.gen_team_pic(result[5: ])
        res = CharaHelper.concat_team_pic([res1, res2])
        res = CharaHelper.pic2b64(res)
        res = MessageSegment.image(res)
    else:
        res1 = ' '.join(result[0:5])
        res2 = ' '.join(result[5: ])
        res = f'{res1}\n{res2}'

    await delete_msg(session)
    await silence(session, silence_time)
    msg = f'{at}\n新たな仲間が増えますよ！\n{res}'
    # print(msg)
    print('len(msg)=', len(msg))
    await session.send(msg)


@on_command('卡池资讯', aliases=('看看卡池', '康康卡池'), only_to_me=True)
async def gacha_info(session:CommandSession):
    gacha = Gacha()
    up_chara = gacha.up
    if USE_PRO_VERSION:
        up_chara = map(lambda x: get_cqimg(CharaHelper.get_picname(CharaHelper.get_id(x)), 'priconne') + x, up_chara)
    up_chara = '\n'.join(up_chara)
    await session.send(f"本期卡池主打的角色：\n{up_chara}\nUP角色合计={(gacha.up_prob/10):.1f}% 3星出率={(gacha.s3_prob)/10:.1f}%")
    await delete_msg(session)


@on_command('竞技场查询', aliases=('怎么拆', '怎么解', '怎么打'), only_to_me=False)
async def arena_query(session:CommandSession):

    logger = logging.getLogger('kokkoro.arena_query')
    logger.setLevel(logging.DEBUG)

    argv = session.current_arg.strip()
    print(argv)
    argv = re.sub(r'[\?？呀啊哇]', ' ', argv)
    print(argv)
    argv = argv.split()
    print(argv)

    print(f'竞技场查询：{argv}')
    logger.info(f'竞技场查询：{argv}')

    if 5 < len(argv):
        await session.send('编队不能多于5名角色')
        return
    defen = Arena.user_input(argv)
    if 100001 in defen:
        await session.send('编队中含未知角色，请尝试使用官方译名')
        return 
    if len(defen) != len(set(defen)):
        await session.send('编队中出现重复角色')
        return

    res = Arena.do_query(defen)

    if not len(res):
        await session.send('抱歉没有查询到解法')
        return

    await silence(session, 120)       # 避免过快查询

    print('query completed, Start generating pics')
    pics = [ CharaHelper.gen_team_pic(team, 128) for team in res ]
    print('pic generated. Start concat pics')
    pics = CharaHelper.concat_team_pic(pics)
    print('concat finished. Converting to base64')
    pics = CharaHelper.pic2b64(pics)
    print('base64 ready! len=', len(pics))
    pics = MessageSegment.image(pics)

    header = f'已为{MessageSegment.at(session.ctx["user_id"])}骑士君查询到以下胜利队伍：\n'
    footer = '\n禁言是为了避免查询频繁，请打完本场竞技场后再来查询'
    msg = f'{header}{pics}{footer}'
    print('len(msg)=', len(msg))

    logger.info('sending pics...')
    await session.send(msg)
    logger.info('Finished sending.')