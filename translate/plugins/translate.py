import re
from nonebot import on_command, CommandSession
from nonebot import on_natural_language, NLPSession, IntentCommand
from sogou_tr import sogou_tr
from datetime import datetime, timedelta

# sogou_tr使用帮助：
# print(sogou_tr('hello world'))  # -> '你好世界'
# print(sogou_tr('hello world', to_lang='de'))  # ->'Hallo Welt'
# print(sogou_tr('hello world', to_lang='fr'))  # ->'Salut tout le monde'
# print(sogou_tr('hello world', to_lang='ja'))  # ->'ハローワールド'


@on_command('translate', aliases=('翻译', '翻訳'))
async def translate(session: CommandSession):
    text = session.get('text')
    if text:
        translation = await get_translation(text)
        await session.send(translation)
    else:
        await session.send('翻译姬待命中...')


@translate.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip() # 删去首尾空白
    if stripped_arg:
        session.state['text'] = stripped_arg
    else:
        session.state['text'] = None
    return


async def get_translation(text: str) -> str:
    if not hasattr(get_translation, 'cdtime'):
        get_translation.cdtime = datetime.now() - timedelta(seconds=3)
    now = datetime.now()
    if(now < get_translation.cdtime):
        return '翻译姬冷却中...'
    else:
        get_translation.cdtime = datetime.now() + timedelta(seconds=1)
        ret = sogou_tr(text)
        # print(sogou_tr.json)
        return ret if '0' != sogou_tr.json.get('errorCode') else '翻译姬出错了 ごめんなさい！'

'''
db = {
    '173681-1': '173681-1价格为114514.00円',
    '350218-1': '350218-1值1919810.00津巴布韦币'
}


@on_command('查询test', only_to_me=False)
async def lookup_test(session:CommandSession):

    res = []
    for i in session.state['items']:
        if i in db:
            res.append(db[i])

    await session.send('\n'.join(res))


@lookup_test.args_parser
async def lookup_test_parser(session:CommandSession):
    if 'items' not in session.state:
        session.state['items'] = session.current_arg.strip().split()
    return


@on_natural_language(only_to_me=False)
async def nlp_lookup_test(session:NLPSession):
    rex = re.compile(r'\d+-\d+')
    res = [ m.group() for m in rex.finditer(session.msg_text.strip()) ]
    if res:
        return IntentCommand(90.0, '查询test', args={'items': res})
'''