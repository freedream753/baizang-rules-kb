# -*- coding: utf-8 -*-
"""把 _rules_raw.txt 重建成带层级标题的 Markdown 知识库（逐章一文件）。"""
import re, os

RAW = open('_rules_raw.txt', encoding='utf-8').read().splitlines()
L = [''] + [x.strip() for x in RAW]          # 1-based
N = len(RAW)

# ---- 手工标注的标题（行号 -> (级别, 标题)） ----
HEAD = {
    10: (2, '第一章 服务器基本规则'),
    11: (3, '1.1 对局剩余时间'),
    13: (3, '1.2 开黑行为'),
    16: (3, '1.3 作弊'),
    18: (3, '1.4 举报流程'),
    28: (3, '1.5 广告宣传'),
    30: (3, '1.6 语音/文字频道'),
    38: (3, '1.7 其他恶意行为'),
    42: (3, '1.8 关于处罚'),

    53: (2, '第二章 玩法规则'),
    55: (3, '2.1 违反角色扮演准则（OOC）'),
    58: (4, '间谍通用规则'),
    63: (3, '2.2 合作撤离'),
    65: (3, '2.3 损害同阵营利益'),
    69: (3, '2.4 关于 SCP-409'),
    73: (3, '2.5 关于 SCP-035'),
    80: (3, '2.6 特殊事件优先级'),
    92: (3, '2.7 恶意阻挡规则（举报需附虚拟ID）'),
    93: (4, '门阻挡'),
    100: (4, '电梯阻挡'),
    102: (3, '2.8 其他'),
    103: (4, '鞭尸'),
    105: (4, '记ID'),
    108: (4, '支援单位'),
    112: (4, '设施总面板'),
    116: (4, '对讲机频道'),
    122: (3, '2.9 堵出生点'),
    126: (4, '出生点判定图示'),
    133: (3, '2.10 D级人员关押保护区'),
    136: (3, '2.11 死亡记忆'),
    140: (4, '换路定义（原文编号 4）'),
    142: (3, '2.12 利用BUG'),

    158: (2, '第三章 指挥命令规则'),
    160: (3, '3.1 广播命令'),
    165: (3, '3.2 现场命令'),
    171: (3, '3.3 过快读秒（5秒）'),
    173: (3, '3.4 不合理命令'),
    190: (3, '3.5 合理命令'),
    196: (3, '3.6 不同阵营对防化服的态度'),
    201: (3, '3.7 持有（保有枪支）命令'),

    203: (2, '第四章 击杀和武器规则'),
    204: (3, '4.1 击杀队友（TK）'),
    207: (3, '4.2 交火线'),
    221: (3, '4.3 信息差规则'),
    226: (3, '4.4 自卫反击'),
    229: (3, '4.5 合理命令击杀'),
    234: (3, '4.6 无理由击杀（RDM）'),
    242: (3, '4.7 武器规则'),
    243: (4, '电击器'),
    246: (4, '武器定义'),
    248: (3, '4.8 人物模型问题规则'),
    257: (3, '4.9 推理击杀'),

    269: (2, '第五章 撤离点规则'),
    270: (3, '5.1 紧急疏散规则'),
    274: (4, '堵撤离点'),
    283: (4, '能撤不撤'),
    287: (4, '堵撤离点与能撤不撤的例外'),
    296: (3, '5.2 撤离疏散区域'),
    297: (4, '各撤离点界限范围图示'),

    303: (2, '第六章 阵营职责规则'),
    305: (3, '6.1 D级人员'),
    314: (3, '6.2 基金会军事单位通用规则'),
    315: (4, '通用基金会武装单位规则'),
    327: (4, '基金会武装单位撤离点规则'),
    329: (4, '基金会单位指挥表'),
    330: (5, '基金会行政架构指挥'),
    337: (5, '基金会调度命令冲突'),
    340: (5, '基金会职级部门命令冲突'),
    344: (4, '指挥系统职级规则'),
    350: (3, '6.3 设施安保部门'),
    365: (3, '6.4 设施站点MTF机动特遣队'),
    386: (3, '6.5 Epsilon-11 九尾狐机动特遣队'),
    403: (3, '6.6 Epsi-ERROR-11 机动特遣队'),
    424: (3, '6.7 NU-7-CBRN 核能化学排'),
    434: (3, '6.8 NU-7 落锤穹顶机动特遣队'),
    451: (3, '6.9 Alpha-9 最后的希望机动特遣队'),
    459: (3, '6.10 XI-8-G1 转轮机动特遣队'),
    468: (3, '6.11 QRT 快速反应部队'),
    477: (3, '6.12 RTF 快速反应特遣队'),
    490: (3, '6.13 科研部门/特殊科研部门'),
    499: (3, '6.14 混沌分裂者'),
    523: (3, '6.15 混沌分裂者-深潜部队（预留阵营）'),
    525: (3, '6.16 混沌分裂者-掠夺者小队'),
    542: (3, '6.17 XI-8-D3「廷达罗斯猎犬」机动特遣队'),
    553: (3, '6.18 SCP 阵营'),
    575: (3, '6.19 SCP-999'),
    584: (3, '6.20 蛇之手'),
    603: (3, '6.21 GRU-P「掠食者」行动7组'),
    625: (3, '6.22 UIU「拦截者」行动小组'),
    640: (3, '6.23 GOC 全球超级燃联盟（核弹任务）'),
    661: (3, '6.24 GOC 激流金属'),
    687: (3, '6.25 猩红之王之子'),
    701: (3, '6.26 UIU 部门通用规则'),
    707: (3, '6.27 UIU 特异事故处'),
    737: (3, '6.28 UIU-白棋部队'),
    751: (3, '6.29 UIU 黑棋行动小组'),
    766: (3, '6.30 美国联邦第24特种作战中队'),
    777: (3, '6.31 赫曼·富勒的不安马戏团-家族ACTS收集组'),
    790: (3, '6.32 SKP 异常特遣队'),
    806: (3, '6.33 欲肉教会（含羔羊）'),

    828: (2, '第七章 规则版本改动记录'),
    830: (3, '7.1 规则改动记录'),
}

# 不输出的行（标题、目录、章节包装、总述——总述写入手写的 00 文件）
SKIP = {1, 2, 3, 4, 5, 6, 7, 8, 9}

CH_FILE = {
    '第一章': '01-第一章-服务器基本规则.md',
    '第二章': '02-第二章-玩法规则.md',
    '第三章': '03-第三章-指挥命令规则.md',
    '第四章': '04-第四章-击杀和武器规则.md',
    '第五章': '05-第五章-撤离点规则.md',
    '第六章': '06-第六章-阵营职责规则.md',
    '第七章': '07-第七章-规则版本改动记录.md',
}

# 原文只有图片、没有文字的位置：插入占位说明，避免 AI 以为文本已完整
IMG_NOTE = {
    24: '【图片缺失】原文档此处为“举报/申诉流程图”。',
    126: '【图片缺失】以下为原文档中的出生点判定图，仅有标注名称，没有文字说明具体范围：',
    297: '【图片缺失】以下为原文档中的各撤离点界限范围图，仅有标注名称，没有文字说明具体范围：',
    485: '【图片缺失】原文档此处为“单向门区域”示意图。',
}

TERM = '。！？；：…!?;:）)」』”"'
NOJOIN = re.compile(r'^(?:[一二三四五六七八九十]+[、.]|\d+[、.]|[○◎●◾]|第[一二三四五六七八九十]+[章节条]|'
                    r'友军[:：]|中立[:：]|敌对[:：]|首要目标[:：]|阵营关系|例外[:：]|关于SCP|'
                    r'\d{4}[/\s]\d{1,2}[/\s]\d{1,2}|时间段|特殊事件)')
DATE = re.compile(r'^\d{4}[/\s]\d{1,2}[/\s]\d{1,2}')


def clean_oc(name):
    name = re.sub(r'^[○◎●◾]\s*', '', name)
    name = re.sub(r'[①-⑳]+\s*$', '', name).strip()
    return name


out = []          # (chapter_key, level, text)
chapter = None
chapter_short = ''
last_o = ''
stack = {}        # 级别 -> 标题
buf = []


def flush():
    global buf
    if buf:
        out.append((chapter, 0, ''.join(buf)))
        buf = []


for i in range(1, N + 1):
    if i in SKIP:
        continue
    line = L[i]
    if not line:
        continue

    if i in HEAD:
        flush()
        lvl, title = HEAD[i]
        if lvl == 2:
            chapter = title.split(' ')[0]
            chapter_short = title.split(' ', 1)[1] if ' ' in title else title
            if chapter not in CH_FILE:
                chapter = '第六章'
                chapter_short = '阵营职责规则'
        stack = {k: v for k, v in stack.items() if k < lvl}
        stack[lvl] = title
        out.append((chapter, lvl, title))
        if i in IMG_NOTE:
            out.append((chapter, 0, IMG_NOTE[i]))
        continue

    if line.startswith('○'):
        flush()
        name = clean_oc(line)
        if chapter == '第六章' and last_o and '首要目标' in last_o:
            short = re.sub(r'（.*?）', '', chapter_short).strip()
            if not name.startswith(short):
                name = f'{short} · {name}'
        out.append((chapter, 4, name))
        if i in IMG_NOTE:
            out.append((chapter, 0, IMG_NOTE[i]))
        last_o = line
        continue

    if chapter == '第七章' and DATE.match(line):
        flush()
        out.append((chapter, 4, line))
        continue

    # 正文：判断是否与上一行同段
    if i in IMG_NOTE:
        flush()
        prev_ok = False
    else:
        prev_ok = False

    if buf:
        prev = buf[-1]
        soft = ('（', '(', '：', ':', '，', '、', '“', '‘', '如', '但', '并', '且', '或', '与', '和')
        joinable = (
            prev and prev[-1] not in TERM
            and len(prev) >= 8
            and not NOJOIN.match(line)
            and prev.endswith(soft)
        )
        if joinable:
            buf.append(line)
            continue
        flush()

    buf.append(line)
    if i in IMG_NOTE:
        flush()
        out.append((chapter, 0, IMG_NOTE[i]))

flush()

os.makedirs('kb', exist_ok=True)
files = {}
for ch, lvl, text in out:
    key = CH_FILE.get(ch or '第一章', '99.md')
    files.setdefault(key, []).append((lvl, text))

for fn, items in files.items():
    lines_out = []
    for lvl, text in items:
        if lvl == 0:
            lines_out.append(text)
            lines_out.append('')
        else:
            lines_out.append('#' * lvl + ' ' + text)
            lines_out.append('')
    open(os.path.join('kb', fn), 'w', encoding='utf-8').write('\n'.join(lines_out).rstrip() + '\n')
    print(fn, len(items))
