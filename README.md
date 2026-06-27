<p align="center">
	<a href="README_zh.md">简体中文</a>
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

## Quick start

```bash
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

# Find WeChat articles via Sogou + Baidu + Yuanbao fallback
python scripts/browser_ai.py weixin "微信公众号 跨境电商"
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
├── README_zh.md
├── LICENSE
├── .gitignore
├── .gitattributes
└── requirements.txt
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