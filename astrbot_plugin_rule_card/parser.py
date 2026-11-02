# -*- coding: utf-8 -*-
"""把“规则助手”的纯文本回复解析成卡片模板数据。

不依赖 AstrBot，可单独测试（preview.py 复用本文件）。
解析目标格式见 prompt/02-系统提示词.md【输出格式】：
    【结论】...（可同行跟内容，也可另起一行）
    【依据】
    · 引用条文一行一条
    【理由】...
    【处罚】...
    【减责或加重】
    · 仅列触发项
    【还需确认】
    1) ...  2) ...
    【下一步】...
不在【】标签里的开头文本归入“说明”段，标签外的普通段落附着到当前段。
"""
import re
from datetime import date

SECTION_RE = re.compile(r"^【(.+?)】\s*(.*)$")
BULLET_RE = re.compile(r"^·\s*(.*)$")
# 1) 2) 3. 4、 均识别为编号；"5.1 条款"点后无空格，不会误判
NUM_RE = re.compile(r"^(\d{1,2})(?:\s*[)）]|\.\s+|\s*、)\s*(.*)$")
SUBHEAD_RE = re.compile(r"^■\s*(.*)$")

# 已知标签 → 配色；未收录的标签统一用灰色
TAG_COLOR = {
    "结论": "green",
    "依据": "blue",
    "理由": "cyan",
    "处罚": "red",
    "减责或加重": "purple",
    "还需确认": "amber",
    "注意": "amber",
    "警告": "red",
    "下一步": "teal",
    "补充": "gray",
}

# 触发渲染的判定标签（require_tag=True 时，回复含其中任意一个即视为规则解释）
KNOWN_TAGS = ("结论", "依据", "处罚", "理由", "减责或加重", "还需确认", "下一步")


def _esc(s: str) -> str:
    """AstrBot 的 html_render 不开 autoescape，这里手动转义防止规则原文里的 <> & 破坏排版。"""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _line(text: str) -> dict:
    m = BULLET_RE.match(text)
    if m:
        return {"kind": "bullet", "text": _esc(m.group(1).strip())}
    m = NUM_RE.match(text)
    if m:
        return {"kind": "number", "num": m.group(1), "text": _esc(m.group(2).strip())}
    return {"kind": "text", "text": _esc(text)}


def parse_sections(text: str) -> list:
    sections, cur = [], None
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = SECTION_RE.match(line)
        if m:
            cur = {"tag": m.group(1).strip(), "lines": []}
            sections.append(cur)
            if m.group(2).strip():  # 标签同行带了内容，如【结论】可以撤。
                cur["lines"].append(_line(m.group(2).strip()))
            continue
        if cur is None:  # 回复开头没有标签
            cur = {"tag": "说明", "lines": []}
            sections.append(cur)
        cur["lines"].append(_line(line))
    for sec in sections:
        sec["color"] = TAG_COLOR.get(sec["tag"], "gray")
        sec["highlight"] = sec["tag"] == "结论"
    return sections


def looks_like_rule_reply(text: str) -> bool:
    return any(f"【{t}】" in text for t in KNOWN_TAGS)


def build_data(
    text: str,
    query: str = "",
    *,
    card_width: int = 680,
    server_name: str = "[CN]RXSEND 白藏测试服",
    bot_name: str = "规则助手",
    theme: str = "dark",
) -> dict:
    q = query.strip()
    if len(q) > 64:  # 问题太长只截取，避免卡片头部爆掉
        q = q[:64] + "…"
    return {
        "card_width": int(card_width),
        "server_name": _esc(server_name),
        "bot_name": _esc(bot_name),
        "date": date.today().strftime("%Y/%m/%d"),
        "query": _esc(q) if q else "",
        "sections": parse_sections(text),
        "theme": "light" if str(theme).lower() == "light" else "dark",
        "doc": False,
    }


# ==================== 文档模式（规则原文 / 人物图鉴等长文） ====================

# 标题含这些词时整段用红色（易踩线/警示内容）
_DOC_RED_WORDS = ("踩线", "注意", "警告", "禁止", "OOC")
_DOC_MIN_HEADS = 2   # 至少 2 个【】标题才判定为文档
_DOC_MIN_LINES = 3   # 且至少 3 行结构化内容（■/·/编号）


def _doc_line(text: str) -> dict:
    m = SUBHEAD_RE.match(text)
    if m:
        return {"kind": "h", "text": _esc(m.group(1).strip())}
    m = BULLET_RE.match(text)
    if m:
        return {"kind": "bullet", "text": _esc(m.group(1).strip())}
    m = NUM_RE.match(text)
    if m:
        return {"kind": "number", "num": m.group(1), "text": _esc(m.group(2).strip())}
    if text.startswith("⚠"):  # ⚠ 字形容器里可能缺失，转为样式化叹号
        return {"kind": "warn", "text": _esc(text.lstrip("⚠ ").strip())}
    return {"kind": "text", "text": _esc(text)}


def looks_like_rule_doc(text: str) -> bool:
    """判定是否为“规则原文/图鉴”类长文：≥2 个【】标题 + ≥3 行 ■/·/编号内容。"""
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]
    heads = sum(1 for ln in lines if SECTION_RE.match(ln))
    if heads < _DOC_MIN_HEADS:
        return False
    struct = sum(
        1 for ln in lines
        if SUBHEAD_RE.match(ln) or BULLET_RE.match(ln) or NUM_RE.match(ln)
    )
    return struct >= _DOC_MIN_LINES


def build_doc_data(
    text: str,
    query: str = "",
    *,
    card_width: int = 680,
    server_name: str = "[CN]RXSEND 白藏测试服",
    bot_name: str = "规则助手",
    theme: str = "dark",
) -> dict:
    """把规则原文/图鉴类文本解析成文档卡片数据（结构同 build_data，doc=True）。"""
    q = query.strip()
    if len(q) > 64:
        q = q[:64] + "…"
    sections, cur = [], None
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = SECTION_RE.match(line)
        if m:
            heading = m.group(1).strip()
            cur = {"tag": _esc(heading),
                   "color": "red" if any(w in heading for w in _DOC_RED_WORDS) else "amber",
                   "lines": []}
            sections.append(cur)
            if m.group(2).strip():
                cur["lines"].append(_doc_line(m.group(2).strip()))
            continue
        if cur is None:
            cur = {"tag": "说明", "color": "gray", "lines": []}
            sections.append(cur)
        cur["lines"].append(_doc_line(line))
    return {
        "card_width": int(card_width),
        "server_name": _esc(server_name),
        "bot_name": _esc(bot_name),
        "date": date.today().strftime("%Y/%m/%d"),
        "query": _esc(q) if q else "",
        "sections": sections,
        "theme": "light" if str(theme).lower() == "light" else "dark",
        "doc": True,
    }
