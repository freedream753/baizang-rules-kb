# -*- coding: utf-8 -*-
"""astrbot_plugin_rule_card —— 把“规则助手”的规则解释回复渲染成 SCP 风格卡片图片。

渲染链路（v1.1.0 起内置渲染，不再依赖 AstrBot 的远程文转图服务）：
  1. 内置本地渲染（renderer.py）：Jinja2 渲染 template.html → Playwright 截图 → 本地 PNG；
  2. 本地不可用（未装 playwright 等）时降级 AstrBot 的 html_render 远程渲染；
  3. 都失败则保留原文回复，不影响使用。

本插件挂 on_llm_response 钩子：当 LLM 回复符合规则解释格式
（含【结论】/【依据】/【处罚】等标签）时，把文本解析成结构化数据，
渲染为图片并替换原文本回复。

安装：把本目录整体放进 AstrBot 的 data/plugins/ 下，重载插件即可。
推荐执行 `pip install playwright && playwright install chromium` 启用本地渲染。
"""
import os

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.provider import LLMResponse
from astrbot.api.star import Context, Star, register

try:
    from .parser import build_data, build_doc_data, looks_like_rule_doc, looks_like_rule_reply
    from .renderer import LocalRenderer
except ImportError:  # 直接以脚本方式加载时的兜底
    from parser import build_data, build_doc_data, looks_like_rule_doc, looks_like_rule_reply  # noqa: F401
    from renderer import LocalRenderer  # noqa: F401

TPL_PATH = os.path.join(os.path.dirname(__file__), "template.html")
with open(TPL_PATH, "r", encoding="utf-8") as _f:
    TPL = _f.read()


@register("astrbot_plugin_rule_card", "wujunze",
          "把规则回复渲染为 SCP 风格卡片图片（规则解释/规则原文两类，黑夜/白天主题，使用系统微软雅黑）", "v1.3.4")
class RuleCardPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.cfg = config
        self.renderer = LocalRenderer()
        self._local_disabled = False  # 环境缺 playwright 时置位，跳过本地尝试

    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp: LLMResponse):
        """LLM 回复后触发：符合规则解释格式则替换为图片卡片。"""
        if not self.cfg.get("enabled", True):
            return
        try:
            text = self._reply_text(resp)
            if not text:
                return
            query = (event.message_str or "").strip() if event else ""
            is_reply = looks_like_rule_reply(text)
            is_doc = looks_like_rule_doc(text)
            # require_tag 开启时只渲染两类卡片回复，避免把普通聊天也转成图
            if self.cfg.get("require_tag", True) and not (is_reply or is_doc):
                return

            # 规则解释（【结论】等标签）优先，其次规则原文/图鉴类长文
            if is_reply:
                data = build_data(
                    text, query,
                    card_width=self.cfg.get("card_width", 680),
                    server_name=self.cfg.get("server_name", "[CN]RXSEND 白藏测试服"),
                    bot_name=self.cfg.get("bot_name", "规则助手"),
                    theme=self.cfg.get("theme", "dark"),
                )
            elif self.cfg.get("enable_doc", True) and is_doc:
                data = build_doc_data(
                    text, query,
                    card_width=self.cfg.get("card_width", 680),
                    server_name=self.cfg.get("server_name", "[CN]RXSEND 白藏测试服"),
                    bot_name=self.cfg.get("bot_name", "规则助手"),
                    theme=self.cfg.get("theme", "dark"),
                )
            else:  # require_tag=false 且不像卡片格式的普通回复
                data = build_data(
                    text, query,
                    card_width=self.cfg.get("card_width", 680),
                    server_name=self.cfg.get("server_name", "[CN]RXSEND 白藏测试服"),
                    bot_name=self.cfg.get("bot_name", "规则助手"),
                    theme=self.cfg.get("theme", "dark"),
                )
            out = await self._render_card(data)
            if not out:
                return
            # 用图片替换原文本消息链（本地路径或远程 URL）
            if out.startswith("http"):
                resp.result_chain.chain = [Image.fromURL(out)]
            else:
                resp.result_chain.chain = [Image.fromFileSystem(out)]
            logger.info("规则解释回复已渲染为图片卡片")
        except Exception:
            logger.exception("规则卡片渲染失败，保留原始文本回复")

    async def _render_card(self, data: dict) -> str:
        """本地渲染优先，失败则降级 AstrBot 远程文转图；均失败返回空串。"""
        if not self._local_disabled:
            try:
                path = await self.renderer.render(TPL, data)
                return path
            except Exception as e:
                if "Playwright" in str(e):
                    self._local_disabled = True  # 环境缺失，后续直接走远程
                    logger.warning("未检测到 Playwright，本地渲染已停用，改用远程文转图")
                else:
                    self.renderer.drop_browser()
                    logger.exception("本地渲染失败，尝试 AstrBot 远程文转图")

        url = await self.html_render(
            TPL, data,
            options={
                "type": "png",
                "omit_background": True,
                "full_page": True,
                "animations": "disabled",
            },
        )
        return url or ""

    @staticmethod
    def _reply_text(resp) -> str:
        """兼容 completion 为纯文本或多模态列表两种情况。"""
        c = getattr(resp, "completion", None)
        if isinstance(c, str) and c.strip():
            return c
        chain = getattr(getattr(resp, "result_chain", None), "chain", None) or []
        return "".join(p.text for p in chain if isinstance(p, Plain))
