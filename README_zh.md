<p align="center">
	<span>>简体中文<</span>
	&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
	<a href="README.md">English</a>
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

## 快速开始

```bash
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

# 公众号文章：搜狗 + 百度 + 元宝三路包抄
python scripts/browser_ai.py weixin "微信公众号 跨境电商"
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
├── README_zh.md
├── LICENSE
├── .gitignore
├── .gitattributes
└── requirements.txt
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