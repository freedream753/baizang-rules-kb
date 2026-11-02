# -*- coding: utf-8 -*-
"""用示例数据渲染卡片 → preview.html，浏览器直接打开预览效果。

也可以把 template.html 的内容粘到 AstrBot Text2Image Playground
（https://t2i-playground.astrbot.app/）里配合测试数据在线调试。
"""
import pathlib
import sys

from jinja2 import Template

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parser import build_data  # noqa: E402

# 用户提供的完整示例回复（用于回归预览模板效果）
EXAMPLE = """【结论】可以撤。流星事件一触发，就进入紧急疏散流程：Alpha-9 的首要目标会自动改成“逃离设施”，遇到 24th 也可以不管它直接走；但走特殊撤离点必须带上 VIP，否则撤不成立。另外，即使 24th 是你的敌对阵营，你也不能在撤离点附近开杀后被判成能撤不撤。

【依据】
· 第五章 5.1 紧急疏散规则：“当紧急疏散开始，所有阵营(除UIU特工组)判为任务失败，首要目标更改为逃离设施，撤离途中可以忽视敌对阵营，具有撤离条件但无撤离意愿，主动杀人具有主观恶性的行为可能会被视作堵撤离点/能撤不撤”；同节另注“特殊事件-流星:该事件发生时回合进度条(右上角)变为黄色，紧急疏散提前触发，此时遵循紧急疏散规则”。
· 06 总则 · 基金会武装单位撤离点规则：“NTF ERROR-11 XI-8 Alpha-9 Nu-7 NU-7 必须携带跟随保护VIP人员（特殊科研人员，人事主管，站点设施主管，NU-7保全顾问 UIU专员 GOC大使）才能撤离特殊撤离点”。
· 6.30 24作战中队 阵营关系：友军：UIU部门 SCP-999；中立：无；敌对：其他阵营都是。

【理由】流星改变的只是紧急疏散的开始时间，规则本身仍然适用于紧急疏散：一出现提示，就按紧急疏散处理，A9 不用再管首要目标，可以直接以撤离为优先。“撤离途中可以忽视敌对阵营”只是允许，并不是要求你必须去打 24th；只是允许你走开。两份限制同时生效：普通撤离点不要求 VIP，特殊撤离点必须带着 VIP 一起撤；如果你明明能撤，却耗在撤离点周边杀 24th，就正好落入“具有撤离条件但无撤离意愿，主动杀人具有主观恶性”，按堵撤离点或能撤不撤来评价。

【处罚】这两类的具体数值本次检索片段未给出，由管理裁量。

【减责或加重】
· 在撤离途中被 24th 先开火、你被迫还击：5.1 例外写“在前往撤离点路上的途中遇敌杀人的、受到威胁必须杀人的”不算能撤不撤。
· 你已经在撤离点范围内、随时能撤还继续追杀：情节加重。
· 伪装人员或间谍在直升机、装甲车处杀人后原地撤离的，另有专项条款，属于 OOC 情形。

【还需确认】
1) 你走的是普通撤离点还是特殊撤离点？特殊撤离点要 VIP，且 VIP 必须是特殊科研、人事主管、站点设施主管、NU-7保全顾问、UIU专员、GOC大使之一。
2) 当时身边有没有这类 VIP 可以带？
3) 流星触发后你是直接离场，还是先在撤离点附近清人？

补充一句：如果你说的“24th 的流星”其实是指某个玩家或某个 24th 阵营的机制，而不是 5.1 里的“特殊事件-流星”，说清楚具体是什么，我再按对应条文核对——这两种情况的结论可能不同。"""


def main() -> None:
    theme = "light" if (sys.argv[1:2] or [""])[0].lower() in ("light", "l", "白天") else "dark"
    tpl_path = pathlib.Path(__file__).parent / "template.html"
    tpl = tpl_path.read_text(encoding="utf-8")
    data = build_data(EXAMPLE, query="A9 流星触发后能撤吗？走特殊撤离点要不要带 VIP？", theme=theme)
    page = (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        "<title>规则卡片预览</title>"
        '<body style="margin:0;padding:24px;'
        + ("background:#cfc9bd;" if theme == "light" else "background:#3a3f47;")
        + 'display:flex;justify-content:center;">'
        + Template(tpl).render(**data)
        + "</body></html>"
    )
    out = pathlib.Path(__file__).parent / "preview.html"
    out.write_text(page, encoding="utf-8")
    print(f"已生成 {out}（{theme} 主题）")


if __name__ == "__main__":
    main()
