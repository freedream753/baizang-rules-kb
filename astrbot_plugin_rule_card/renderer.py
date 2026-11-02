# -*- coding: utf-8 -*-
"""内置本地渲染器：不依赖 AstrBot 的远程文转图服务，直接用 Playwright 截图。

设计要点：
  - 懒加载：首次渲染才启动 Chromium，之后常驻复用，避免每条消息冷启动；
  - 2 倍采样（device_scale_factor=2）：680px 卡片输出 1360px 宽图，手机上更清晰；
  - 字体由运行环境提供（v1.3.2 起安装包不再携带字体，也不再做 base64/file://
    注入——45MB 的 set_content 载荷会把页面搞崩），模板字体栈首选微软雅黑，
    请确保运行环境已安装（Docker 容器安装方式见 README）；
  - HTML 落盘后用 file:// 打开再截图，对 body（inline-block）元素精确截图，
    输出紧贴卡片、无多余空白；
  - 输出到系统临时目录，自动清理过期文件，不污染 AstrBot data 目录；
  - 不依赖 AstrBot 任何 API，可独立于插件单独测试。
"""
import asyncio
import os
import tempfile
import time
import uuid


def _file_url(path: str) -> str:
    return "file:///" + path.replace("\\", "/").lstrip("/")


class LocalRenderer:
    """共享单个 Chromium 实例的本地 HTML→PNG 渲染器。"""

    def __init__(self, keep_hours: int = 2):
        self._pw = None
        self._browser = None
        self._lock = asyncio.Lock()
        self._out_dir = os.path.join(tempfile.gettempdir(), "astrbot_rule_card")
        self._keep_hours = keep_hours

    async def render(self, tpl: str, data: dict, *, scale: int = 2) -> str:
        """渲染模板并返回本地 PNG 文件路径。抛异常表示本地渲染不可用。"""
        from jinja2 import Template

        html = Template(tpl).render(**data)
        os.makedirs(self._out_dir, exist_ok=True)

        html_path = os.path.join(self._out_dir, f"{uuid.uuid4().hex}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        await self._ensure_browser()
        width = int(data.get("card_width", 680))
        page = await self._browser.new_page(
            viewport={"width": width, "height": 720},
            device_scale_factor=scale,
        )
        out = os.path.join(self._out_dir, f"{uuid.uuid4().hex}.png")
        try:
            await page.goto(_file_url(html_path), wait_until="load")
            try:  # 等字体全部就绪再截图，避免首批截图字体未生效
                await page.evaluate("() => document.fonts.ready")
            except Exception:
                pass
            # 对 body 元素截图：body 为 inline-block，尺寸恰好等于卡片，
            # 避免 full_page 在内容较短时把视口剩余高度也截成透明空白
            await page.locator("body").screenshot(
                path=out,
                omit_background=True,    # 透明背景，露出卡片圆角
                animations="disabled",
                caret="hide",
            )
        finally:
            await page.close()
            try:
                os.remove(html_path)
            except OSError:
                pass
        self._cleanup()
        return out

    async def _ensure_browser(self):
        async with self._lock:
            if self._browser and self._browser.is_connected():
                return
            try:
                from playwright.async_api import async_playwright
            except ImportError as e:
                raise RuntimeError(
                    "本地渲染需要 Playwright：请在 AstrBot 运行环境执行 "
                    "`pip install playwright && playwright install chromium`"
                ) from e
            if self._pw is None:
                self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )

    def drop_browser(self):
        """渲染异常后调用：丢弃可能已崩溃的浏览器实例，下次渲染时重建。"""
        self._browser = None

    def _cleanup(self):
        """清理过期截图与临时 HTML，避免临时目录无限膨胀。"""
        deadline = time.time() - self._keep_hours * 3600
        try:
            for name in os.listdir(self._out_dir):
                if not (name.endswith(".png") or name.endswith(".html")):
                    continue
                p = os.path.join(self._out_dir, name)
                try:
                    if os.path.getmtime(p) < deadline:
                        os.remove(p)
                except OSError:
                    pass
        except OSError:
            pass
