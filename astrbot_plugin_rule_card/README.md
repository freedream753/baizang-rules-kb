# astrbot_plugin_rule_card

把"规则助手"的规则解释回复自动渲染成 **SCP 风格卡片图片**发送。

适配 [CN]RXSEND 白藏测试服规则解释机器人，支持两类卡片：

```
规则解释：【结论】【依据】【理由】【处罚】【减责或加重】【还需确认】【下一步】
规则原文：【6.27 UIU特异事故处 · UIU间谍规则①】等多标题长文（■ 小节 / · 列表 / 1. 编号）
```

内置 Playwright 本地渲染（v1.1.0 起），不依赖 AstrBot 的远程文转图公共服务；字体使用运行环境的微软雅黑（v1.3.2 起安装包不再携带字体）。v1.3.4 起配套完整的 compose 挂载持久化方案：Chromium 浏览器、playwright 包、系统依赖库、fallback 字体全部放进数据卷，**容器重建/升级后零重装**。

## 效果

- SCP 档案风卡片：琥珀顶条 + 徽标（规则解释=SCP / 规则原文=ARC）+ 服务器名/日期（`theme=light` 切换为纸面浅色白天主题）
- 全部文字使用微软雅黑（常规+粗体两个字重），由运行环境系统字体提供
- 顶部琥珀虚线框显示玩家提问（Q）
- 规则解释卡片：彩色标签 chip：结论(绿·高亮加粗)、依据(蓝)、理由(青)、处罚(红)、减责或加重(紫)、还需确认(琥珀)、下一步(青绿)、其他(灰)
- 规则原文卡片：【】转为琥珀左条标题（含"踩线/注意/警告/禁止/OOC"字样的段落自动变红），`■` 小节、`·` 列表、`1.` 编号、`⚠` 行转为琥珀叹号
- `·` 开头渲染为 ▪ 列表，`1)` `1.` `1、` 渲染为圆圈编号
- 图片高度随内容自适应（整页截图），透明背景露出圆角，2 倍采样手机端清晰
- 底部固定免责页脚："AI 依据服务器规则文档生成 · 不代表管理团队最终裁定"

## 安装

1. AstrBot WebUI → 插件管理 → 从本地上传安装 `astrbot_plugin_rule_card.zip`（或解压到 `data/plugins/` 后重载插件）
2. **启用本地渲染**（推荐）：在 AstrBot 运行环境执行
   ```bash
   pip install playwright && playwright install chromium
   ```
   Docker 部署则进入容器执行：
   ```bash
   docker exec -it <astrbot容器名> bash -c "pip install playwright && playwright install chromium"
   ```
3. **Docker 部署：全量持久化**（字体 + 浏览器 + playwright 包 + Chromium 系统库全部放进数据卷，容器重建/升级后零重装）：

   第一步，容器内执行一次，把依赖装齐并收集进 `data/`：
   ```bash
   docker exec -it <astrbot容器名> bash
   pip install playwright && python -m playwright install chromium
   python -m playwright install-deps chromium              # apt 安装 Chromium 系统依赖库
   mkdir -p /AstrBot/data/ms-playwright /AstrBot/data/pydeps /AstrBot/data/chrome-deps /AstrBot/data/chrome-fonts
   mv /root/.cache/ms-playwright/* /AstrBot/data/ms-playwright/      # 浏览器 → 数据卷
   SITE=$(python -c "import site; print(site.getsitepackages()[0])")
   cp -r "$SITE"/playwright "$SITE"/greenlet* "$SITE"/pyee* /AstrBot/data/pydeps/   # playwright 包 → 数据卷
   exit
   ```
   第二步，宿主机执行一次，把 apt 新装的系统库和 fallback 字体收集进 `data/`：
   ```bash
   IMG=$(docker inspect astrbot --format '{{.Config.Image}}')
   comm -13 \
     <(docker run --rm --entrypoint sh "$IMG" -c 'dpkg -l | grep ^ii | tr -s " " | cut -d" " -f2' | sort) \
     <(docker exec astrbot sh -c 'dpkg -l | grep ^ii | tr -s " " | cut -d" " -f2' | sort) > /tmp/new_pkgs.txt
   docker exec -i astrbot bash -c 'while read -r p; do
     dpkg -L "$p" | grep -E "^/usr/lib|^/lib" | grep "\.so" | while read -r f; do [ -e "$f" ] && cp -L --parents "$f" /AstrBot/data/chrome-deps/; done
     dpkg -L "$p" | grep "^/usr/share/fonts" | while read -r f; do [ -e "$f" ] && cp -L --parents "$f" /AstrBot/data/chrome-fonts/; done
   done' < /tmp/new_pkgs.txt
   ```
   第三步，`docker-compose.yml` 增加环境变量与挂载，然后 `docker compose up -d` 重建：
   ```yaml
   services:
     astrbot:
       environment:
         - PLAYWRIGHT_BROWSERS_PATH=/AstrBot/data/ms-playwright   # Chromium 浏览器持久化
         - PYTHONPATH=/AstrBot/data/pydeps                        # playwright 包持久化
         - LD_LIBRARY_PATH=/AstrBot/data/chrome-deps/usr/lib/x86_64-linux-gnu:/AstrBot/data/chrome-deps/lib/x86_64-linux-gnu
       volumes:
         - ./data:/AstrBot/data
         - ./data/fonts-msyh:/usr/share/fonts/truetype/yahei:ro                                  # 微软雅黑
         - ./data/chrome-fonts/usr/share/fonts:/usr/share/fonts/truetype/playwright:ro           # emoji/日文等 fallback 字体
         - ./data/fontconfig-cache:/var/cache/fontconfig                                         # 字体缓存
   ```
   微软雅黑 ttc 需提前放到宿主机 `data/fonts-msyh/`。重建后验证：`docker exec astrbot ldd /AstrBot/data/ms-playwright/chromium_headless_shell-*/chrome-linux/chrome-headless-shell | grep "not found"` 无输出即依赖齐全，`fc-list | grep -ci yahei` 应 ≥ 1。
   - 简易方式（不推荐）：`docker cp` 字体进容器 + `python -m playwright install-deps chromium`，但容器每次重建后都要重跑
4. 无需修改 persona 和知识库：LLM 照常输出纯文本，插件在发送前自动转图
5. 本地渲染不可用时自动降级 AstrBot 远程文转图，再失败则保留原始文本回复，不影响正常使用

## 配置

| 配置项 | 默认值 | 说明 |
|---|---|---|
| enabled | true | 开关：是否把规则解释回复渲染为图片 |
| require_tag | true | 仅当回复包含【结论】/【依据】/【处罚】等标签时才渲染，避免误转普通聊天 |
| card_width | 680 | 卡片宽度（像素） |
| server_name | [CN]RXSEND 白藏测试服 | 卡片头部显示的服务器名 |
| bot_name | 规则助手 | 卡片头部显示的机器人名 |
| theme | dark | 卡片主题：`dark` 黑夜（深色底）/ `light` 白天（纸面浅色底），WebUI 下拉选择 |
| enable_doc | true | 开关：规则原文/人物图鉴类长文（≥2 个【】标题 + ≥3 行列表）也渲染为文档卡片 |

## 工作原理

```
LLM 回复 ── on_llm_response 钩子 ──▶ parser 判定卡片类型
     ├─ 含【结论】等标签 ──────▶ build_data（规则解释卡片）
     └─ 多【】标题长文 ────────▶ build_doc_data（规则原文卡片）
        ──▶ renderer 本地渲染：Jinja2 + 系统微软雅黑 ──▶ 内置 Playwright 截图 → 本地 PNG
        ──▶ Image.fromFileSystem 替换 result_chain ──▶ 发送图片
   （本地未装 playwright 时降级 AstrBot html_render 远程渲染 → Image.fromURL）
```

| 文件 | 职责 |
|---|---|
| main.py | 插件入口，挂 on_llm_response 钩子，两类卡片调度 + 本地/远程双渲染调度 |
| parser.py | 纯文本 → 卡片数据（规则解释 / 规则原文两种解析，不依赖 AstrBot，可独立测试）；含 HTML 转义 |
| renderer.py | 内置本地渲染器：懒加载常驻 Chromium、2 倍采样、body 元素精确截图、临时文件自动清理 |
| template.html | Jinja2 卡片模板（HTML + CSS，无外部资源，双模式双主题，字体栈首选微软雅黑） |
| preview.py | 本地预览：`python preview.py` 生成 preview.html 用浏览器打开 |
| _conf_schema.json | WebUI 配置项声明 |

## 模板调试

- 本地：改 `template.html` 后运行 `python preview.py`（黑夜）/ `python preview.py light`（白天），打开生成的 `preview.html`（需 `pip install jinja2`）
- 在线：把 `template.html` 内容粘到 [AstrBot Text2Image Playground](https://t2i-playground.astrbot.app/) 配合测试数据调试

## 注意事项

- 本地渲染需要运行环境装有 Playwright + Chromium（见安装步骤 2）与微软雅黑字体（见安装步骤 3）；截图输出在系统临时目录 `astrbot_rule_card/` 下，自动清理 2 小时前的旧图
- v1.3.0/v1.3.1 曾随包携带字体（base64 内嵌 / file:// 注入），前者 45MB 载荷会触发 `Page.set_content: Page crashed`，故 v1.3.2 起改为使用系统字体、安装包不再携带
- 未装 playwright 时自动降级为 AstrBot 远程文转图（公共服务，可能偶发 502/503，不稳定），建议还是装上 playwright
- `require_tag=false` 时所有 LLM 回复都会转图，不建议：普通聊天也会变成图片
- 文档模式判定阈值：≥2 个【】标题且 ≥3 行 ■/·/编号内容；标题含"踩线/注意/警告/禁止/OOC"的段落标红
- 标签外的开头文本归入"说明"段（灰色），标签后的普通段落附着到当前段，不会丢失内容
- 新增标签配色：在 `parser.py` 的 `TAG_COLOR` 和 `template.html` 的 `.sec-*` 配色类中各加一条即可；白天主题需同步在 `.card.light .sec-*` 中补一条加深配色
- 改主题配色：黑夜/白天的界面色都定义在 `template.html` 顶部 `.card` 与 `.card.light` 的 CSS 变量里（`--bg-card`/`--tx`/`--amber` 等）
