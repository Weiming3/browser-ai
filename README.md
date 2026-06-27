<p align="center">
	<span>>简体中文<</span>
	&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
	<a href="README_en.md" lang="en" hreflang="en">English</a>
</p>

# Browser-AI Toolkit / 浏览器 AI 工具集

<p align="center">
	<img src="https://stone.professorlee.work/api/stone/Weiming3/browser-ai" alt="Stone Badge">
</p>

> 一个 CLI，把同一句话同时丢给一堆 AI 和搜索引擎，然后把答案排好序端回来。

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Playwright](https://img.shields.io/badge/powered%20by-playwright-green)](https://playwright.dev/)

---

## 这是干嘛的？

`browser-ai` 是一个 Python CLI：把单条查询同时分发给多个 AI 服务（腾讯元宝、Kimi、通义千问、知乎直答、豆包……）和搜索引擎（百度、Google、搜狗微信），等所有源返回后做统一排序，输出一个综合结果。

底层基于 Playwright，提供两个可按站点切换的引擎：

- **Chromium + 持久化 profile**：用于需要保留登录态的站点。
- **Camoufox**（反检测 Firefox）：用于对普通浏览器进行指纹识别的搜索/抓取类站点。

站点配置完全由 `config/ai_sites.json` 数据驱动。新增站点只需复制一段配置并修改选择器，**无需改动任何 Python 代码**。

---

## 和 OpenRouter / LiteLLM 有什么不同？

看到这里第一反应很可能是「这不就是又一个 AI router 吗？」——问题合理，但**路由对象完全不同**。

|  | OpenRouter / LiteLLM / OneAPI / Portkey | browser-ai |
|---|---|---|
| 路由对象 | LLM **API 端点** | AI **网页产品** + **搜索引擎网页** |
| 调用方式 | HTTP API（OpenAI 兼容格式） | 浏览器自动化（Playwright） |
| 鉴权 | API Key（按 token 计费） | 你自己的**登录态**（cookie / persistent profile） |
| 覆盖范围 | 有公开 API 的 LLM 提供商 | 有网页 UI 的一切——**包括没 API 的** |
| 输出 | 单个模型的文本回复 | 多源页面文本 + **统一打分排序** |
| 形态 | 后端服务 / 网关 | 本地 CLI |

API router 做不到的三件事，`browser-ai` 都覆盖：

**1. 那些「没 API、只有网页」的源。**

腾讯元宝、知乎直答、Web 版豆包、B 站 AI 总结、搜狗微信——这些都没有公开 API，但都是有用信源。API router 物理上摸不到这一层。

**2. 主流 LLM 看不到的「围墙花园」内容。**

Gemini、GPT、Claude 这类模型有训练截止日期，而且语料重度偏向英文。它们对中文平台围墙内的内容覆盖非常弱：

- **微信公众号**：中文长文的主战场，Google 几乎索引不到，模型训练数据里也稀薄。
- **百度贴吧、知乎、小红书**：反爬严格、登录门槛高，西方爬虫根本看不见。
- **中文平台的实时内容**：上周刚发的帖子、新出的爆款文章，模型压根没见过。

`browser-ai` 通过搜狗微信（目前唯一的公开公众号聚合入口）、百度、加上你登录好的元宝 / Kimi 会话，**直接抓活的、带中文场景的真实资料**，而不是问一个 LLM 它几年前的记忆。`weixin` 命令就是为这个场景设计的——搜狗 + 百度 + 元宝三路包抄同一个查询，把 AI 看不到的中文长文搜回来，**给 LLM 的回答补充一个它够不着的思考维度**。

**3. AI + 搜索引擎混合扇出。**

大多数 AI router 只在 LLM 之间扇出。`browser-ai` 把 AI 产品和搜索引擎（百度、Google、搜狗微信）混在同一次查询里——这是「边问 AI、边找参考资料」的唯一实用做法。

**一句话总结**：OpenRouter 做的是「**API 抽象层**」；`browser-ai` 做的是「**网页抽象层**」——把任何带网页的 AI 产品或搜索引擎，捏成一个统一查询目标。

---

## 和 `@playwright/mcp` 有什么不同？

> `@playwright/mcp` 是微软官方维护的 Playwright MCP 服务器：把浏览器自动化能力暴露成 MCP 工具，让 AI agent 可以一步步指挥浏览器。

它和 `browser-ai` **不在同一个层面竞争**——一个把浏览器暴露给 AI，另一个是基于浏览器的预设工作流。

|  | `@playwright/mcp` | browser-ai |
|---|---|---|
| 本质 | 通用浏览器遥控器（MCP 工具集） | 预设工作流 CLI |
| 决策者 | AI agent 自己（一步步操作） | JSON 配置（开箱即用） |
| 执行模式 | 单标签页串行 | 多站点并行扇出（`asyncio.gather`） |
| 站点知识 | 通用，每次让 AI 现场摸索 | 预配每个 AI 站点的选择器 / 等待逻辑 |
| 反检测 | 无 | `navigator.webdriver` 掩蔽 + 可选 Camoufox |
| 登录态 | 无 explicit 管理 | `config/profiles/` 按站点分目录 + Firefox cookie 导入 |
| 意图路由 | 无 | `search_routes.json` 按关键词决定探哪些站点 |
| 评分排序 | 无 | 三阶段 probe → evaluate → deep-dive |
| 公众号搜索 | 无 | `weixin` 命令三路包抄 |

**一句话总结**：

> `@playwright/mcp` 给 AI agent 一本**空白笔记本和一支笔**；`browser-ai` 是已经填好的**答题卡**，连笔迹都描过一遍了。

### 推荐两者都装

它们解决的问题不同，建议都装：

```bash
# browser-ai：CLI 工作流（多源聚合、反检测、预配站点）
pip install playwright camoufox
playwright install chromium
camoufox fetch

# @playwright/mcp：MCP 工具集（让 Claude / Cursor / Cline 直接控制浏览器）
npm install -g @playwright/mcp
```

- `@playwright/mcp` 适合「**让 AI 自由探索新站点**」的开放场景。
- `browser-ai` 适合「**中文 AI 产品聚合 + 围墙花园数据获取**」的预设场景。

两个装上互不冲突，按场景切换用。

---

## 快速开始

### 方式一：`pip install`（推荐给最终用户）

```bash
pip install browser-ai-cli
playwright install chromium

# 可选：反检测场景用得到
camoufox fetch

# 首次运行会自动把模板配置拷到 ~/.config/browser-ai/config/
browser-ai-cli list

# 登录某个站点（会弹一个真的浏览器窗口，自己手动登录一下就行）
browser-ai-cli login yuanbao

# 全网智能搜索：AI + 搜索引擎一起上
browser-ai-cli search "python 异步编程最佳实践"

# 公众号文章：搜狗 + 百度 + 元宝三路包抄
browser-ai-cli weixin "微信公众号 跨境电商"
```

> pip 安装模式下，配置和登录态落在 `~/.config/browser-ai/`（XDG 风格），和系统其他 dotfiles 一处管理。本地 checkout 模式下仍是仓库根目录的 `config/`，老用户行为不变。

### 方式二：clone 仓库自己改（推荐给二次开发）

```bash
git clone https://github.com/Weiming3/browser-ai.git
cd browser-ai
pip install -r requirements.txt
playwright install chromium

# 可选：装上 Camoufox，反检测场景用得到
pip install camoufox
camoufox fetch

# 把示例配置复制成你自己的本地配置
cp config/ai_sites.example.json config/ai_sites.json
cp config/search_routes.example.json config/search_routes.json

# 看看现在接了哪些站点
python scripts/browser_ai.py list

# 登录某个站点（会弹一个真的浏览器窗口，自己手动登录一下就行）
python scripts/browser_ai.py login yuanbao

# 全网智能搜索：AI + 搜索引擎一起上
python scripts/browser_ai.py search "python 异步编程最佳实践"

# 想单独戳某个源也行
python scripts/browser_ai.py probe "kimi 长文本"
```

---

## 从 Firefox 导入已有登录态

如果某些站点你已经在 Firefox 里登录过，不必再手动登录一次。`scripts/import_firefox_login.py` 会读取你本机 Firefox 的 `cookies.sqlite` 数据库，把对应的 cookie 写入到 `config/profiles/` 下对应的 Chromium profile 目录中。

```bash
# 先 dry-run 看看会动哪些 cookie
python scripts/import_firefox_login.py --dry-run

# 确认无误后再真跑
python scripts/import_firefox_login.py

# 只导入某个站点的 cookie
python scripts/import_firefox_login.py --site yuanbao
```

强烈建议第一次使用先跑 `--dry-run` 预览。

---

## 目录结构

```
browser-ai/
├── scripts/
│   ├── browser_ai.py             # 主 CLI
│   ├── import_firefox_login.py   # Firefox 登录态搬运工
│   └── pre-commit-check.py       # 提交前安全检查
├── config/
│   ├── ai_sites.example.json     # 模板，复制成 ai_sites.json
│   └── search_routes.example.json
├── tests/
│   └── test_smoke.py             # 26 个冒烟测试
├── README.md
├── README_en.md
├── LICENSE
├── pyproject.toml         # pip 包元数据 + entry point
├── requirements.txt
├── .gitignore
└── .gitattributes
```

---

## 加一个新 AI 站点

最快是跑向导：

```bash
python scripts/browser_ai.py add-site
```

愿意直接改 JSON 的话，从 `config/ai_sites.json` 里复制一段 site，改这几个字段就够了：`name`、`url`、`login_url`、`login_hint`、`selectors.input`、`selectors.submit`、`selectors.response`、`preferred_engine`。重启 CLI，新站点就上线了。

---

## 引擎怎么选？

| 引擎 | 适用场景 |
|------|----------|
| Chromium + profile | 需要登录态的站点（元宝、Kimi、豆包、B站）。 |
| Camoufox | 搜索/抓取类站点对无头 Chromium 不友好（百度、Google、搜狗微信）。 |

在 `ai_sites.json` 里给每个站点设一个 `preferred_engine` 就完事，**只这一个开关**。两个引擎相互独立——想留就留，想拆就拆，反正不是承重墙。

---

## 真正要看两眼的就这两件事

**一、登录态别往仓库里塞。**

`config/profiles/` 里装的是 cookies、localStorage、IndexedDB，基本等同于每个站点的活动登录会话。`.gitignore` 默认已经把它排除在外了，**别动这一行**。真正的 `config/ai_sites.json` 也在 gitignore 里，模板是 `*.example.json` 那两份。仓库自带的 `scripts/pre-commit-check.py` 会拦下任何想偷偷把这俩文件加进去的 commit。建议这样用：

```bash
python scripts/pre-commit-check.py                       # 每次提交前手动跑
cp scripts/pre-commit-check.py .git/hooks/pre-commit   # 装成 git hook 自动拦截
```

**二、站点的服务条款还是老大。**

绝大多数 AI 平台的服务条款都明确禁止自动化访问。本工具就自己研究用，别拿去当爬虫服务赚钱，也别去薅别人的付费内容。被限流、被封 IP、被发律师函，都跟作者没关系，谢谢。

---

## 一些零碎

- `login` 和 `--headed` 一定弹窗，其他命令默认静默。
- 百度/Google 无头模式有时候会跳验证码，加 `--headed` 就行。
- 默认配置是样例，**不是真理**。按自己工作流改好再发给别人看。

---

## 许可证

MIT —— 见 [LICENSE](LICENSE)。