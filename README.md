# Browser-AI Toolkit / 浏览器AI工具

> A configuration-driven Playwright toolkit for orchestrating multiple AI chatbots and search engines through a unified CLI.
>
> 一个由配置驱动的 Playwright 工具集，通过统一 CLI 编排多个 AI 对话机器人和搜索引擎。

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Playwright](https://img.shields.io/badge/powered%20by-playwright-green)](https://playwright.dev/)

---

## ⚠️ Legal Disclaimer / 法律免责声明

**English:**

This project is a **personal learning and research tool**. By using it you agree that:

- You will **comply with the Terms of Service** of every site you target (Yuanbao, Kimi, Tongyi, Zhida, Doubao, Baidu, Google, Sogou, etc.). Most AI platforms forbid automated access in their ToS.
- You will **not use this for commercial scraping, bulk data collection, or to bypass paid content**.
- The author **assumes no liability** for account bans, IP blocks, civil claims, or any other consequence arising from your use of this software.
- The included anti-detect techniques (`init_script` to mask `navigator.webdriver`, Camoufox for fingerprint resistance) are present for educational purposes. Removing them is a valid choice.

**中文:**

本项目是**个人学习与研究工具**。使用本工具即表示你同意：

- 你将**自行遵守各目标站点的服务条款**（元宝、Kimi、通义、知乎直答、豆包、百度、Google、搜狗等）。大多数 AI 平台的服务条款禁止自动化访问。
- 你**不会将其用于商业爬取、批量数据采集或绕过付费内容**。
- 对于因使用本软件导致的账号封禁、IP 拉黑、民事诉讼或其他任何后果，**作者不承担任何责任**。
- 项目中包含的反检测技术（通过 `init_script` 隐藏 `navigator.webdriver` 标识、使用 Camoufox 抵抗指纹识别）仅用于学习目的，**移除它们是合理的选择**。

---

## English

### What is this?

`browser-ai` is a Python CLI that fans-out a single user query to multiple AI services (Yuanbao, Kimi, Tongyi, Zhida, Doubao, ...) and search engines (Baidu, Google, Sogou WeChat) and ranks the results. It is built on top of Playwright with two interchangeable engines:

- **Chromium + persistent profile** for sites that require login state.
- **Camoufox** (anti-detect Firefox) for scraping/search-heavy sites that fingerprint regular browsers.

Site configuration is **100% data-driven** through `config/ai_sites.json`. To add a new site, copy an entry in the JSON and tweak the selectors — no code change required.

### Highlights

- **Dual engines**, picked per-site via `preferred_engine`.
- **Intent-based routing** via `config/search_routes.json` — the CLI inspects the query keywords and picks the right probe set.
- **Three-phase pipeline**: probe → evaluate → deep-dive.
- **Batch import** of Firefox login cookies into Chromium profiles (useful when you already have sessions in Firefox).
- **Interactive wizard** to add a new AI site (`add-site`).
- **Cross-platform** (Windows / macOS / Linux).

### Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# Optional: install Camoufox for the anti-detect engine
pip install camoufox
camoufox fetch

# 2. Prepare your local config (the example files are templates, not used at runtime)
cp config/ai_sites.example.json config/ai_sites.json
cp config/search_routes.example.json config/search_routes.json

# 3. List configured sites
python scripts/browser_ai.py list

# 4. Log into a site (Chromium visible window)
python scripts/browser_ai.py login yuanbao

# 5. Run a smart search
python scripts/browser_ai.py search "python asyncio best practices"

# 6. Or just probe one source
python scripts/browser_ai.py probe "kimi long-text"

# 7. WeChat article search (sogou + baidu + yuanbao fallback)
python scripts/browser_ai.py weixin "微信公众号 跨境电商"
```

### Optional: import login state from Firefox

```bash
# Preview first
python scripts/import_firefox_login.py --dry-run

# Actually import
python scripts/import_firefox_login.py

# Import only one site
python scripts/import_firefox_login.py --site yuanbao
```

### Layout

```
browser-ai/
├── scripts/
│   ├── browser_ai.py             # Main CLI
│   └── import_firefox_login.py   # Batch import Firefox cookies
├── config/
│   ├── ai_sites.example.json     # Site template (copy to ai_sites.json)
│   └── search_routes.example.json
├── README.md                     # this file
├── LICENSE
├── requirements.txt
└── .gitignore
```

### SECURITY: Read before you use

> **⚠️ You are solely responsible for any damage caused by leaking your session data.**
> **⚠️ 因泄露 session 数据造成的所有后果，由使用者自行承担。**

- **NEVER commit `config/profiles/`.** Each subdirectory holds cookies, localStorage and IndexedDB for one site — equivalent to an active login session. The `.gitignore` excludes it by default; **do NOT override that, even temporarily**.
- **NEVER commit `config/ai_sites.json`** with sensitive `cookie_domains` either — it is also gitignored. Use the `*.example.json` files as templates.
- **NEVER run `git add .` blindly.** Always review `git status` before committing.
- The Firefox import script reads your local `cookies.sqlite`. It only ever writes to the local profile directory under `config/profiles/`. Do not move those profiles to a shared folder or cloud storage.
- This repo ships with `hooks/pre-commit-check.py` (see `scripts/pre-commit-check.py`). If you set it up as a Git hook, it will **block any commit** that accidentally stages `config/profiles/`, log files, or known credential patterns. Recommended:

  ```bash
  # From the project root:
  python scripts/pre-commit-check.py          # run once before committing
  cp scripts/pre-commit-check.py .git/hooks/pre-commit   # install as git hook
  ```

### Add a new AI site

The fastest path is `add-site`:

```bash
python scripts/browser_ai.py add-site
```

Otherwise copy an entry in `config/ai_sites.json` and update: `name`, `url`, `login_url`, `login_hint`, `selectors.input`, `selectors.submit`, `selectors.response`, `preferred_engine`.

### Why two engines?

| Engine | When to use |
|--------|-------------|
| Chromium + profile | Sites where you need persistent login state (Yuanbao, Kimi, Doubao, Bilibili). |
| Camoufox | Search/scraping sites that block headless Chromium (Baidu, Google, Sogou WeChat). |

### Notes

- `login` and `--headed` always open a visible window. Other commands run headless by default.
- Baidu/Google headless may still trigger captcha; use `--headed` when that happens.
- The default site config is a sample. Tailor it to your own workflow before publishing or sharing.

---

## 中文

### 这是什么？

`browser-ai` 是一个 Python 命令行工具，把单个查询同时发给多个 AI 服务（腾讯元宝、Kimi、通义千问、知乎直答、豆包等）和搜索引擎（百度、Google、搜狗微信），并对结果排序。底层用 Playwright，支持两种可互换的引擎：

- **Chromium + 持久化 profile**：用于需要登录态的站点。
- **Camoufox**（反检测 Firefox）：用于对普通浏览器进行指纹识别的搜索/抓取类站点。

站点配置 **100% 数据驱动**，放在 `config/ai_sites.json`。添加新站点只需复制 JSON 里的一项，修改选择器即可，**不用改代码**。

### 主要特性

- **双引擎**，通过 `preferred_engine` 按站点选择。
- **基于意图的路由**（`config/search_routes.json`）：CLI 根据查询关键词自动选择试探集。
- **三阶段流水线**：试探 → 评估 → 深度搜索。
- **批量导入 Firefox 登录态**到 Chromium profile（你已经在 Firefox 登录过的会话可以直接复用）。
- **交互式向导**添加新 AI 站点（`add-site`）。
- **跨平台**（Windows / macOS / Linux）。

### 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 可选：安装 Camoufox 反检测引擎
pip install camoufox
camoufox fetch

# 2. 准备本地配置（example 文件只是模板，运行时不会自动读取）
cp config/ai_sites.example.json config/ai_sites.json
cp config/search_routes.example.json config/search_routes.json

# 3. 查看已配置站点
python scripts/browser_ai.py list

# 4. 登录某站点（弹出 Chromium 可视化窗口）
python scripts/browser_ai.py login yuanbao

# 5. 智能搜索
python scripts/browser_ai.py search "python 异步编程最佳实践"

# 6. 单源试探
python scripts/browser_ai.py probe "kimi 长文本"

# 7. 公众号文章搜索（搜狗 + 百度 + 元宝 迂回）
python scripts/browser_ai.py weixin "微信公众号 跨境电商"
```

### 可选：从 Firefox 导入登录态

```bash
# 先预览
python scripts/import_firefox_login.py --dry-run

# 实际导入
python scripts/import_firefox_login.py

# 只导入某个站点
python scripts/import_firefox_login.py --site yuanbao
```

### 目录结构

```
browser-ai/
├── scripts/
│   ├── browser_ai.py             # 主 CLI
│   └── import_firefox_login.py   # 批量导入 Firefox cookies
├── config/
│   ├── ai_sites.example.json     # 站点模板（复制为 ai_sites.json）
│   └── search_routes.example.json
├── README.md                     # 本文件
├── LICENSE
├── requirements.txt
└── .gitignore
```

### ⚠️ 安全：使用前必读

- **绝对不要提交 `config/profiles/`。** 每个子目录保存一个站点的 cookies、localStorage 和 IndexedDB，等同于一个活动的登录会话。`.gitignore` 默认排除它，**请勿改动这一项**。
- **也不要提交 `config/ai_sites.json`**（同样在 .gitignore 中），用 `*.example.json` 作为模板。
- **永远不要直接 `git add .`**。提交前一定要先看 `git status`。
- Firefox 导入脚本只会读你本机的 `cookies.sqlite`，且只写入 `config/profiles/` 下的本地目录。**不要把这些 profile 移到共享目录**。

### 添加新 AI 站点

最快的方式是 `add-site` 向导：

```bash
python scripts/browser_ai.py add-site
```

或者手动复制 `config/ai_sites.json` 里的一个 site 块，修改 `name`、`url`、`login_url`、`login_hint`、`selectors.input`、`selectors.submit`、`selectors.response`、`preferred_engine` 即可。

### 为什么需要两个引擎？

| 引擎 | 适用场景 |
|------|----------|
| Chromium + profile | 需要持久登录态的站点（元宝、Kimi、豆包、B站）。 |
| Camoufox | 对无头 Chromium 进行反检测的搜索/抓取类站点（百度、Google、搜狗微信）。 |

### 注意事项

- `login` 和 `--headed` 模式会强制弹窗，其他命令默认静默运行。
- 百度/Google 在 headless 模式下仍可能触发验证码，必要时加 `--headed`。
- 默认配置是样例，请根据自己的工作流调整后再发布或分享。

---

## License / 许可证

MIT — see [LICENSE](LICENSE).