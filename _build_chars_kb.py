# -*- coding: utf-8 -*-
"""把 _chars_raw.txt（白藏服务器人物介绍.docx 提取文本）重建成人物图鉴知识库。

设计约定（与规则库 _build_kb.py 一致）：
- 一阵营一文件，文件名 08-人物-*.md；
- 数值、措辞照抄原文，缺失字段写"原文未写"，不脑补；
- 每个角色一个 ### 标题块，配合知识库"按标题切分"，一次检索命中一个角色；
- 每个角色标注"规则阵营"（对应 06-阵营-*.md），供机器人把"角色→阵营→关系"串起来；
- 仅删除"点击输入文本"和纯◼占位行，其余原样保留。
"""
import re, os
from collections import Counter

RAW = open('_chars_raw.txt', encoding='utf-8').read().splitlines()

TERM = '。！？；…'
# 新条目开头标记：出现即不再向上一行拼接
NEWITEM = re.compile(
    r'^(?:主动技能|被动技能|天赋|直觉|人物特质|人物特性|特殊物品|特殊装备|特殊技能|'
    r'[①②③④⑤][技能：:]|G技能|[αβγ]主动技能|开局携带|携带|配备|可穿戴|不可穿戴|'
    r'机械单位配备|可以选择|每次|右键|按[RGTF]|如果|被道德伦理检察官|自制小刀可使用|SCP-\d|阵营[:：]|等级|出生地点|生命|体力|'
    r'自带|设施主管可以|设施保全顾问|所有九尾狐|无人机可部署|回收协议|怒气值满后|'
    r'我爱科学|mio服联动阵营|「|资深科学家是|特殊科研人员是|'
    r'(?:MP40|K98|G43|MG34|M30改)$)')
GET_TYPES = {'初始角色', '常规支援', '条件呼叫', '事件角色', '顾问呼叫', '条件召唤'}


def norm(s):
    """组名/角色名归一化：去引号、空白、间隔号，便于容错匹配。"""
    return re.sub(r'[\s"“”「」\'·・]', '', s)


# ---------------- 组 → 文件 / 规则阵营 映射 ----------------
META = {
    'D级人员': ('08-人物-D级人员.md', '6.1 D级人员', None),
    '科研团队': ('08-人物-科研团队.md', '6.13 科研部门/特殊科研部门', None),
    '特殊科研人员': ('08-人物-特殊科研人员.md', '6.13 科研部门/特殊科研部门', None),
    '安保部门': ('08-人物-安保部门.md', '6.3 设施安保部门', None),
    '驻站MTF机动特遣队': ('08-人物-驻站MTF机动特遣队.md', '6.4 设施站点MTF机动特遣队（通用规则见 6.2）', None),
    'QRT快速反应部队': ('08-人物-QRT快速反应部队.md', '6.11 QRT 快速反应部队', None),
    'MTF-XI-8-G1转轮G1后勤维护小组': ('08-人物-XI-8-G1后勤维护小组.md', '6.10 XI-8-G1 转轮机动特遣队', None),
    'RTF快速反应特遣队': ('08-人物-RTF快速反应特遣队.md', '6.12 RTF 快速反应特遣队', None),
    'MTF-XI-8-D3廷达罗斯猎犬': ('08-人物-XI-8-D3廷达罗斯猎犬.md', '6.17 XI-8-D3「廷达罗斯猎犬」机动特遣队', None),
    '九尾狐机动特遣队Epsilan-11': ('08-人物-九尾狐Epsilon-11.md', '6.5 Epsilon-11 九尾狐机动特遣队', None),
    '九尾狐机动特遣队EPSERROR-11': ('08-人物-EPSERROR-11.md', '6.6 Epsi-ERROR-11 机动特遣队',
        '注意：原文阵营字段写为「九尾狐机动特遣队」，但规则库中该队为独立阵营 6.6 Epsi-ERROR-11，关系判定以 6.6 文件为准。'),
    'NU-7落锤-穹顶武装机动小组': ('08-人物-NU-7穹顶机动小组.md', '6.8 NU-7 落锤穹顶机动特遣队', None),
    '机动特遣队ALPHA-9最后的希望': ('08-人物-ALPHA-9.md', '6.9 Alpha-9 最后的希望机动特遣队', None),
    '混沌分裂者': ('08-人物-混沌分裂者.md', '6.14 混沌分裂者', None),
    '混沌分裂者-第三掠夺者小队': ('08-人物-混沌掠夺者小队.md', '6.16 混沌分裂者-掠夺者小队',
        '注意：本组角色原文阵营字段写为「混沌分裂者」，规则库中掠夺者小队为独立阵营 6.16，关系判定以 6.16 为准。'),
    'UIU特异事故处特工组': ('08-人物-UIU特工组.md', '6.27 UIU 特异事故处', None),
    'UIU特异事故处陆军组': ('08-人物-UIU陆军组.md', '6.27 UIU 特异事故处', None),
    'UIU白棋部队': ('08-人物-UIU白棋部队.md', '6.28 UIU-白棋部队',
        '注意：本组角色原文阵营字段多写为「UIU特异事故处」（含一处笔误「IUI」），规则库中白棋为独立阵营 6.28，关系判定以 6.28 为准。'),
    'UIU黑旗行动小组': ('08-人物-UIU黑棋行动小组.md', '6.29 UIU 黑棋行动小组',
        '注意：原文标题混用「黑旗/黑棋」，规则库统一为「黑棋」（6.29）；本组角色原文阵营字段写为「UIU特异事故处」，关系判定以 6.29 为准。'),
    '第24特种部队': ('08-人物-第24特种部队.md', '6.30 美国联邦第24特种作战中队', None),
    'GOC全球超自然联盟': ('08-人物-GOC全球超自然联盟.md', '6.23 GOC（核弹任务）/ 6.24 GOC 大使',
        '注意：原文未注明该组属核弹任务（6.23）还是大使（6.24），判定关系时两个文件都需核对。'),
    'GOC全球超自然联盟-激流金属': ('08-人物-GOC激流金属.md', '6.24b GOC 激流金属', None),
    'GRU-P掠食者行动七组': ('08-人物-GRU-P行动七组.md', '6.21 GRU-P「掠食者」行动7组', None),
    'UIU拦截者行动小组': ('08-人物-UIU拦截者.md', '6.22 UIU「拦截者」行动小组',
        '注意：本组角色原文阵营字段写为「UIU特异事故处」，规则库中拦截者为独立阵营 6.22，关系判定以 6.22 为准。'),
    '欲肉教会': ('08-人物-欲肉教会.md', '6.33 欲肉教会（含羔羊）', None),
    '蛇之手': ('08-人物-蛇之手.md', '6.20 蛇之手', None),
    'SKP异界探索组C队': ('08-人物-SKP异常特遣队.md', '6.32 SKP 异常特遣队', None),
    '赫曼·富勒的不安马戏团ACTS收藏组': ('08-人物-马戏团ACTS收藏组.md', '6.31 赫曼·富勒的不安马戏团-家族ACTS收集组', None),
    '猩红之王之子': ('08-人物-猩红之王之子.md', '6.25 猩红之王之子', None),
    'SCP': ('08-人物-SCP.md', '6.18 SCP 阵营', None),
}

# 角色 → 规则阵营 特例（出生组 ≠ 实际阵营）
CHAR_MAP = {
    'D级人员全球超自然联盟间谍': '6.23/6.24 GOC 全球超自然联盟',
    '欲肉教派羔羊': '6.33 欲肉教会（含羔羊）',
    '蛇之手间谍': '6.20 蛇之手',
    'UIU间谍': '6.27 UIU 特异事故处',
    '混沌分裂者间谍': '6.14 混沌分裂者',
    '落锤-设施保全顾问': '6.8 NU-7 落锤穹顶机动特遣队',
    'SCP-999-2': '6.19 SCP-999（帮助人类；关系判定不要套用 6.18）',
}

META_N = {norm(k): v for k, v in META.items()}
CHAR_MAP_N = {norm(k): v for k, v in CHAR_MAP.items()}

# ---------------- 解析 ----------------
groups = []          # [{name, intro, chars:[{name, f:{...}, traits:[]}]}]
changelog = []
cur_g = None
cur_c = None


def joinable(prev, line):
    return prev and not prev.rstrip().endswith(tuple(TERM)) and not NEWITEM.match(line)


for line in RAW:
    m = re.match(r'^\[(.+?)\]\s?(.*)$', line)
    if not m:
        continue
    style, text = m.group(1), m.group(2).strip()
    if not text:
        continue
    if style in ('Heading 1', 'Heading 2'):
        cur_c = None
        if norm(text) == norm('改动日志'):
            cur_g = None
            continue
        cur_g = {'name': text, 'intro': [], 'chars': []}
        groups.append(cur_g)
        continue
    if style == 'Heading 3':
        cur_c = {'name': text, 'f': {}, 'traits': []}
        cur_g['chars'].append(cur_c)
        continue
    # 普通文本
    if text == '点击输入文本' or re.fullmatch(r'[◼◾■]+', text):
        continue
    target = cur_c if cur_c is not None else (cur_g['intro'] if cur_g else changelog)
    if cur_c is None:
        if cur_g is None:
            changelog.append(text)
        else:
            if cur_g['intro'] and joinable(cur_g['intro'][-1], text):
                cur_g['intro'][-1] += text
            else:
                cur_g['intro'].append(text)
        continue
    f = cur_c['f']
    if re.match(r'^阵营[:：]', text):
        f['camp'] = re.sub(r'^阵营[:：]', '', text)
    elif re.match(r'^等级[:：]?', text):
        f['lvl'] = re.sub(r'^等级[:：]?\s*', '', text)
    elif re.match(r'^出生地点[:：]', text):
        f['birth'] = re.sub(r'^出生地点[:：]', '', text)
    elif re.match(r'^生命[:：]', text):
        f['hp'] = re.sub(r'^生命[:：]', '', text)
    elif re.match(r'^体力[:：]', text):
        f['sta'] = re.sub(r'^体力[:：]', '', text)
    elif text in GET_TYPES:
        f['get'] = text
    else:
        if cur_c['traits'] and joinable(cur_c['traits'][-1], text):
            cur_c['traits'][-1] += text
        else:
            cur_c['traits'].append(text)

# ---------------- 生成角色文件 ----------------
os.makedirs('kb', exist_ok=True)
report = []
for g in groups:
    meta = META_N.get(norm(g['name']))
    if meta is None:
        print('!! 未映射分组:', g['name'])
        continue
    fn, rule_camp, note = meta
    camps = [c['f'].get('camp', '') for c in g['chars'] if c['f'].get('camp')]
    defaults = {k for k, v in Counter(camps).items() if v == max(Counter(camps).values())} if camps else set()
    L = []
    L.append(f'# 08 人物图鉴 · {g["name"]}')
    L.append('')
    L.append(f'> 规则库对应阵营：{rule_camp}。阵营关系、首要目标、专属规则见对应 06-阵营 文件。')
    L.append('> 本文件只回答"这个角色是谁、属于哪个阵营、有什么特性"；违不违规、怎么处罚一律以规则条文为准。')
    if note:
        L.append(f'> {note}')
    L.append('')
    if g['intro']:
        L.append('## 阵营简介（原文）')
        L.append('')
        for t in g['intro']:
            L.append(t)
        L.append('')
    for c in g['chars']:
        f = c['f']
        rule = CHAR_MAP_N.get(norm(c['name']), rule_camp)
        L.append(f'### {c["name"]}')
        L.append(f'- 规则阵营：{rule}')
        base = '｜'.join([
            f'原文阵营：{f.get("camp", "原文未写")}',
            f'等级：{f.get("lvl", "原文未写")}',
            f'获取方式：{f.get("get", "原文未写")}',
            f'出生地点：{f.get("birth", "原文未写")}',
        ])
        L.append(f'- {base}')
        L.append(f'- 生命：{f.get("hp", "原文未写")}｜体力：{f.get("sta", "原文未写")}')
        if camps and f.get('camp') and f['camp'] not in defaults:
            L.append(f'- ⚠ 出生于「{g["name"]}」分组，但原文阵营字段为「{f["camp"]}」，判定关系时以此阵营为准（间谍/派驻/渗透角色）。')
        if c['traits']:
            L.append('- 特性（原文）：')
            for t in c['traits']:
                L.append(f'  - {t}')
        L.append('')
    open(os.path.join('kb', fn), 'w', encoding='utf-8').write('\n'.join(L).rstrip() + '\n')
    report.append((g['name'], fn, len(g['chars'])))

print('=== 生成结果 ===')
total = 0
for name, fn, n in report:
    total += n
    print(f'{n:3d}  {fn}')
print('角色总数:', total)
print()
print('=== 组映射表（供 08-人物图鉴-总览 使用）===')
for name, fn, n in report:
    meta = META_N[norm(name)]
    print(f'| {name} | {meta[1]} | {fn} | {n} |')
print()
print('=== 改动日志（原文）===')
for t in changelog:
    print(t)
