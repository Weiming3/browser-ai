<p align="center">
	<a href="README.md" lang="zh-CN" hreflang="zh-CN">简体中文</a>
	&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
	<span>>English<</span>
</p>

# Browser-AI Toolkit

<p align="center">
	<img src="https://stone.professorlee.work/api/stone/Weiming3/browser-ai" alt="Stone Badge">
</p>

> One CLI to ask a bunch of AI chatbots and search engines the same question, and get ranked answers back.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Playwright](https://img.shields.io/badge/powered%20by-playwright-green)](https://playwright.dev/)

---

## What is this?

`browser-ai` is a Python CLI that fans a single query out to multiple AI services (Yuanbao, Kimi, Tongyi, Zhida, Doubao, …) and search engines (Baidu, Google, Sogou WeChat), waits for all sources to respond, and ranks the combined results.

Under the hood it runs on Playwright with two interchangeable engines:

- **Chromium with a persistent profile** — for sites that require login state.
- **Camoufox** — an anti-detect Firefox build, for sites that fingerprint regular browsers.

Site configuration is **100% data-driven** through `config/ai_sites.json`. To plug in a new site you copy an entry and tweak the selectors — no Python changes required.

---

## How is this different from OpenRouter / LiteLLM?

The natural first reaction is "isn't this just another AI router?" — fair question, but the routing target is different.

|  | OpenRouter / LiteLLM / OneAPI / Portkey | browser-ai |
|---|---|---|
| Routing target | LLM **API endpoints** | AI **web products** + **search engine pages** |
| Call mechanism | HTTP API (OpenAI-compatible) | Browser automation (Playwright) |
| Auth | API keys (token billing) | Your own **login sessions** (cookies / profiles) |
| Coverage | LLM providers that expose an API | Anything with a web UI — **even without an API** |
| Output | One model's text reply | Page text from multiple sources + **ranked aggregation** |
| Form factor | Backend service / gateway | Local CLI |

There are three concrete things an API router can't do that `browser-ai` covers:

**1. Sources that have no API, only a website.**

Tencent Yuanbao, Zhihu Zhida, Doubao on the web, Bilibili AI summaries, Sogou WeChat — none expose a public API, yet all are useful query targets. An API router physically can't see this layer.

**2. Walled-garden content that mainstream LLMs can't see.**

Gemini, GPT and Claude have training cutoffs and are heavily English-centric. They have weak coverage of content that lives behind Chinese platform walls:

- **WeChat public accounts (公众号)** — the dominant long-form channel in Chinese, almost never indexed by Google and barely represented in training corpora.
- **Baidu Tieba, Zhihu, Xiaohongshu** — strict anti-scraping, login-gated, invisible to Western crawlers.
- **Real-time Chinese content** — anything posted last week, any new viral article: the model has never seen it.

`browser-ai` reaches these sources through Sogou WeChat (the only public WeChat aggregator), Baidu, and your logged-in Yuanbao/Kimi sessions. You're **scraping live, in-context Chinese-language ground truth**, not asking an LLM what it remembers from two years ago. The `weixin` command is built for exactly this — Sogou + Baidu + Yuanbao fan out the same query and surface Chinese long-form content the LLM can't reach, **adding a thinking dimension that the model's own knowledge can't supply**.

**3. Mixed AI + search fanout.**

Most AI routers only fan out across LLMs. `browser-ai` mixes AI products with search engines (Baidu, Google, Sogou WeChat) in the same query — which is the only practical way to "ask the AI and look up references" in one shot.

**In one line:** OpenRouter is an **API abstraction layer**. `browser-ai` is a **web abstraction layer** — it turns any web-accessible AI product or search engine into a unified query target.

---

## How is this different from `@playwright/mcp`?

> `@playwright/mcp` is Microsoft's official Playwright MCP server: it exposes browser automation as MCP tools so any AI agent can drive a browser step-by-step.

It does **not** compete with `browser-ai` on the same layer — one exposes the browser to the AI, the other is a pre-built workflow on top of the browser.

|  | `@playwright/mcp` | browser-ai |
|---|---|---|
| Nature | Generic browser remote (MCP toolset) | Predefined workflow CLI |
| Decision maker | The AI agent itself (step-by-step) | JSON config files (ready out of the box) |
| Execution mode | Single tab, sequential | Multi-site parallel fan-out (`asyncio.gather`) |
| Site knowledge | Generic — agent figures it out each time | Per-site selectors and wait logic preconfigured |
| Anti-detect | None | `navigator.webdriver` masking + optional Camoufox |
| Login state | No explicit management | Per-site `config/profiles/` dirs + Firefox cookie import |
| Intent routing | None | `search_routes.json` decides which sites to probe |
| Scoring / ranking | None | Three-stage: probe → evaluate → deep-dive |
| WeChat search | None | `weixin` command: Sogou + Baidu + Yuanbao fan-out |

**One-liner:**

> `@playwright/mcp` gives the AI agent a **blank notebook and a pen**. `browser-ai` is the **filled-in answer sheet** — the writing's already done.

### Recommended: install both

They solve different problems; install both:

```bash
# browser-ai: CLI workflow (multi-source aggregation, anti-detect, preconfigured sites)
pip install playwright camoufox
playwright install chromium
camoufox fetch

# @playwright/mcp: MCP toolset (lets Claude / Cursor / Cline drive a browser directly)
npm install -g @playwright/mcp
```

- `@playwright/mcp` fits **"let the AI freely explore new sites"** open-ended scenarios.
- `browser-ai` fits **"Chinese AI product aggregation + walled-garden data retrieval"** predefined scenarios.

Install both — they don't conflict. Pick whichever fits the task.

---

## Quick start

### Option A: `pip install` (recommended for end users)

```bash
pip install browser-ai-cli
playwright install chromium

# Optional: anti-detect engine
camoufox fetch

# First run auto-copies the example configs into ~/.config/browser-ai/config/
browser-ai-cli list

# Log into one site (opens a real browser window — log in there, then close it)
browser-ai-cli login yuanbao

# Fan out a search across AI + search engines
browser-ai-cli search "python asyncio best practices"

# Find WeChat articles via Sogou + Baidu + Yuanbao fallback
browser-ai-cli weixin "微信公众号 跨境电商"
```

> Under `pip install`, your config and login sessions live in `~/.config/browser-ai/` (XDG-style), keeping them with the rest of your dotfiles. Local checkouts still use the repo's own `config/` directory — existing behavior is unchanged.

### Option B: clone the repo (recommended for hacking)

```bash
git clone https://github.com/Weiming3/browser-ai.git
cd browser-ai
pip install -r requirements.txt
playwright install chromium

# Optional: pull in Camoufox for the anti-detect engine
pip install camoufox
camoufox fetch

# Copy the example configs into your local working ones
cp config/ai_sites.example.json config/ai_sites.json
cp config/search_routes.example.json config/search_routes.json

# See what's wired up
python scripts/browser_ai.py list

# Log into one site (opens a real browser window — log in there, then close it)
python scripts/browser_ai.py login yuanbao

# Fan out a search across AI + search engines
python scripts/browser_ai.py search "python asyncio best practices"

# Or poke a single source
python scripts/browser_ai.py probe "kimi long-text"
```

---

## Importing Firefox login state

If you've already signed into some sites in Firefox, you don't have to log in again. `scripts/import_firefox_login.py` reads your local Firefox `cookies.sqlite` and writes the matching cookies into the Chromium profiles under `config/profiles/`.

```bash
# Preview which cookies would be imported
python scripts/import_firefox_login.py --dry-run

# Run the actual import
python scripts/import_firefox_login.py

# Import cookies for a single site only
python scripts/import_firefox_login.py --site yuanbao
```

Always run `--dry-run` first to verify the import set.

---

## Layout

```
browser-ai/
├── scripts/
│   ├── browser_ai.py             # main CLI
│   ├── import_firefox_login.py   # Firefox cookie bridge
│   └── pre-commit-check.py       # safety net before commits
├── config/
│   ├── ai_sites.example.json     # template — copy to ai_sites.json
│   └── search_routes.example.json
├── tests/
│   └── test_smoke.py             # 26 smoke tests
├── README.md
├── README_en.md
├── LICENSE
├── pyproject.toml         # pip metadata + entry point
├── requirements.txt
├── .gitignore
└── .gitattributes
```

---

## Adding a new AI site

Easiest is the wizard:

```bash
python scripts/browser_ai.py add-site
```

If you prefer to edit JSON directly, copy a site block in `config/ai_sites.json` and update: `name`, `url`, `login_url`, `login_hint`, `selectors.input`, `selectors.submit`, `selectors.response`, `preferred_engine`. Restart the CLI and the new site is live.

---

## Which engine do I use?

| Engine | Reach for it when… |
|--------|--------------------|
| Chromium + profile | The site needs you logged in (Yuanbao, Kimi, Doubao, Bilibili). |
| Camoufox | A search/scraping site blocks headless Chromium (Baidu, Google, Sogou WeChat). |

Set `preferred_engine` per site in `ai_sites.json` and that's the only switch you flip. Both engines are independent — keep them both in if you want, rip them out if you don't. They're not load-bearing.

---

## Two things you actually need to know

**1. Keep your session data off the repo.**

`config/profiles/` holds cookies, localStorage and IndexedDB — basically active login sessions for each site. The `.gitignore` already excludes it; **leave it that way**. The real `config/ai_sites.json` is gitignored too, and the `*.example.json` files are templates you copy from. The bundled `scripts/pre-commit-check.py` blocks any commit that tries to sneak those files in. Recommended:

```bash
python scripts/pre-commit-check.py                       # run before each commit
cp scripts/pre-commit-check.py .git/hooks/pre-commit   # install as git hook
```

**2. The site's ToS still wins.**

Most AI platforms ban automated access in their terms. Use this for personal research, not for scraping-as-a-service or anything that earns money from someone else's content. The author isn't liable if you get rate-limited, IP-banned, or worse.

---

## Misc notes

- `login` and `--headed` always open a visible window. Everything else runs headless.
- Baidu/Google headless can still hit a captcha — pass `--headed` when that happens.
- The default site config is a sample, not gospel. Tune it to how you actually work before you share it.

---

## License

MIT — see [LICENSE](LICENSE).