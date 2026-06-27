<p align="center">
	<a href="README_zh.md">简体中文</a>
	&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
	<span>>English<</span>
</p>

# Browser-AI Toolkit

<p align="center">
	<img src="https://stone.professorlee.work/api/stone/Weiming3/browser-ai" alt="Stone Badge">
</p>

> A configuration-driven Playwright toolkit for orchestrating multiple AI chatbots and search engines through a unified CLI.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Playwright](https://img.shields.io/badge/powered%20by-playwright-green)](https://playwright.dev/)

---

## Legal Disclaimer

This project is a **personal learning and research tool**. By using it you agree that:

- You will **comply with the Terms of Service** of every site you target (Yuanbao, Kimi, Tongyi, Zhida, Doubao, Baidu, Google, Sogou, etc.). Most AI platforms forbid automated access in their ToS.
- You will **not use this for commercial scraping, bulk data collection, or to bypass paid content**.
- The author **assumes no liability** for account bans, IP blocks, civil claims, or any other consequence arising from your use of this software.
- The included anti-detect techniques (`init_script` to mask `navigator.webdriver`, Camoufox for fingerprint resistance) are present for educational purposes. Removing them is a valid choice.

---

## What is this?

`browser-ai` is a Python CLI that fans-out a single user query to multiple AI services (Yuanbao, Kimi, Tongyi, Zhida, Doubao, ...) and search engines (Baidu, Google, Sogou WeChat) and ranks the results. It is built on top of Playwright with two interchangeable engines:

- **Chromium + persistent profile** for sites that require login state.
- **Camoufox** (anti-detect Firefox) for scraping/search-heavy sites that fingerprint regular browsers.

Site configuration is **100% data-driven** through `config/ai_sites.json`. To add a new site, copy an entry in the JSON and tweak the selectors — no code change required.

### Highlights

- **Dual engines**, picked per-site via `preferred_engine`.
- **Intent-based routing** via `config/search_routes.json` — the CLI inspects the query keywords and picks the right probe set.
- **Three-phase pipeline**: probe -> evaluate -> deep-dive.
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
│   ├── import_firefox_login.py   # Batch import Firefox cookies
│   └── pre-commit-check.py       # Safety check hook
├── config/
│   ├── ai_sites.example.json     # Site template (copy to ai_sites.json)
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

### SECURITY: Read before you use

> **You are solely responsible for any damage caused by leaking your session data.**

- **NEVER commit `config/profiles/`.** Each subdirectory holds cookies, localStorage and IndexedDB for one site — equivalent to an active login session. The `.gitignore` excludes it by default; **do NOT override that, even temporarily**.
- **NEVER commit `config/ai_sites.json`** with sensitive `cookie_domains` either — it is also gitignored. Use the `*.example.json` files as templates.
- **NEVER run `git add .` blindly.** Always review `git status` before committing.
- The Firefox import script reads your local `cookies.sqlite`. It only ever writes to the local profile directory under `config/profiles/`. Do not move those profiles to a shared folder or cloud storage.
- This repo ships with `scripts/pre-commit-check.py`. If you set it up as a Git hook, it will **block any commit** that accidentally stages `config/profiles/`, log files, or known credential patterns. Recommended:

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

## License

MIT — see [LICENSE](LICENSE).