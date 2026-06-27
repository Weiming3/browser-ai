#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Browser-AI Toolkit — Multi-Site AI Aggregator
浏览器AI工具 - 多站点AI聚合器

A configuration-driven Playwright toolkit that orchestrates multiple AI
chatbots and search engines through a unified CLI. Designed for engineers
who want to fan-out a single query to several AI services, route tasks to
the right site by intent, and persist browser sessions locally.

一个由配置驱动的 Playwright 工具集，通过统一 CLI 编排多个 AI 对话机器人和
搜索引擎。适合需要把一个查询同时发给多个 AI 服务、按意图路由到合适站点、
并在本地持久化浏览器会话的工程师使用。

Features / 功能:
    - Dual engines / 双引擎:
        * Chromium + persistent profile (sites that require login state)
        * Camoufox (anti-detect Firefox) for scraping/search-heavy sites
    - JSON-driven site config (add new sites without editing code)
    - Intent-based routing via search_routes.json
    - Quality scoring + deep-dive recommendations

Usage / 用法:
    python browser_ai.py login [site_name]    # Login to AI sites (Chromium visible)
    python browser_ai.py list                 # List configured sites
    python browser_ai.py add-site             # Interactive wizard to add a new site
    python browser_ai.py search "keyword"     # Smart search (route + probe + score)
    python browser_ai.py probe "keyword"      # Probe-only search
    python browser_ai.py open <site_name>     # Open a site directly
    python browser_ai.py weixin "keyword"     # WeChat article search (sogou + yuanbao)

Options / 选项:
    --headed      Force visible browser window
    --headless    Force silent mode (no window)
    --engine chromium|camoufox  Force a specific engine

SECURITY NOTE / 安全提示:
    - The `config/profiles/` directory contains browser session data (cookies,
      localStorage, IndexedDB) and is gitignored by default.
    - DO NOT commit your own session data; it would expose your logins.
    - Never run `git add .` blindly. Always review what is staged.
"""
import asyncio
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

try:
    from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
except ImportError:
    print("Error: playwright is not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    from camoufox.async_api import AsyncCamoufox
    from camoufox.addons import DefaultAddons
    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_DIR = SCRIPT_DIR.parent / "config"
SITES_FILE = CONFIG_DIR / "ai_sites.json"
ROUTES_FILE = CONFIG_DIR / "search_routes.json"
PROFILES_DIR = CONFIG_DIR / "profiles"

DEFAULT_HEADLESS: bool = True
FORCE_ENGINE: Optional[str] = None

SiteDict = dict[str, Any]
CookieDict = dict[str, Any]
ChromiumHandle = tuple[Playwright, BrowserContext, Page]
CamoufoxHandle = tuple[Any, Any, Page]
EngineHandle = Union[ChromiumHandle, CamoufoxHandle]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_sites() -> list[SiteDict]:
    data = load_json(SITES_FILE)
    return data.get("sites", [])


def get_site(name: str) -> Optional[SiteDict]:
    for s in get_sites():
        if s["name"] == name:
            return s
    return None


def get_profile_path(site_name: str) -> str:
    p = PROFILES_DIR / site_name
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def get_login_lock_path(site_name: str) -> Path:
    return Path(tempfile.gettempdir()) / f"browser_ai_{site_name}.lock"


async def launch_chromium(site_name: str, headless: Optional[bool] = None) -> ChromiumHandle:
    if headless is None:
        headless = DEFAULT_HEADLESS
    p = await async_playwright().start()
    profile_path = get_profile_path(site_name)
    context = await p.chromium.launch_persistent_context(
        user_data_dir=profile_path,
        headless=headless,
        args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--disable-dev-shm-usage',
            '--disable-setuid-sandbox',
            '--window-size=1280,800',
            '--start-maximized',
        ],
        viewport={"width": 1280, "height": 800},
        locale='zh-CN',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        bypass_csp=True,
        java_script_enabled=True,
    )
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        window.chrome = { runtime: {} };
        Object.defineProperty(window, 'CDP', {get: () => undefined});
    """)
    pages = context.pages
    if len(pages) == 0:
        page = await context.new_page()
    else:
        page = pages[0]
    return p, context, page


async def launch_camoufox(headless: Optional[bool] = None) -> CamoufoxHandle:
    if headless is None:
        headless = DEFAULT_HEADLESS
    if not CAMOUFOX_AVAILABLE:
        raise RuntimeError("Camoufox is not installed. Run: pip install camoufox")
    fox = AsyncCamoufox(
        headless=headless,
        exclude_addons=[DefaultAddons.UBO]
    )
    browser = await fox.__aenter__()
    page = await browser.new_page()
    return fox, browser, page


async def close_camoufox(fox: Any, browser: Any) -> None:
    try:
        await browser.close()
    except Exception:
        pass
    try:
        await fox.__aexit__(None, None, None)
    except Exception:
        pass


async def close_browser(p: Playwright, context: BrowserContext) -> None:
    try:
        await context.close()
    except Exception:
        pass
    try:
        await p.stop()
    except Exception:
        pass


async def launch_browser(site_name: str, headless: Optional[bool] = None, engine: Optional[str] = None) -> tuple[str, EngineHandle]:
    site = get_site(site_name)
    if engine is None:
        engine = FORCE_ENGINE
    if engine is None and site:
        engine = site.get("preferred_engine", "chromium")
    if engine is None:
        engine = "chromium"

    if engine == "camoufox":
        fox, browser, page = await launch_camoufox(headless)
        return engine, (fox, browser, page)
    else:
        p, context, page = await launch_chromium(site_name, headless)
        return engine, (p, context, page)


async def close_browser_by_engine(engine: str, handle: EngineHandle) -> None:
    if engine == "camoufox":
        fox, browser, page = handle
        await close_camoufox(fox, browser)
    else:
        p, context, page = handle
        await close_browser(p, context)


async def cmd_login(site_name: Optional[str] = None) -> None:
    sites = [s for s in get_sites() if s.get("enabled", True)]
    if not sites:
        print("No sites configured. Run: python browser_ai.py add-site")
        return

    if site_name:
        target = get_site(site_name)
        if not target:
            print(f"Site not found: {site_name}")
            print(f"Available: {', '.join(s['name'] for s in sites)}")
            return
    else:
        print("\n=== Configured AI Sites ===")
        for i, s in enumerate(sites, 1):
            caps = ", ".join(s.get("capabilities", []))
            profile_path = PROFILES_DIR / s["name"]
            has_profile = "logged-in" if profile_path.exists() and any(profile_path.iterdir()) else "not-logged-in"
            print(f"  {i}. {s['display_name']} ({s['name']}) [{caps}] {has_profile}")
        print(f"  0. Login all sites")
        choice = input("\nSelect a site number: ").strip()
        if not choice:
            return
        try:
            idx = int(choice)
        except ValueError:
            print("Invalid input")
            return
        if idx == 0:
            for s in sites:
                await login_one(s)
            return
        if idx < 1 or idx > len(sites):
            print("Invalid number")
            return
        target = sites[idx - 1]

    await login_one(target)


async def login_one(site, timeout=120):
    name = site["name"]
    print(f"\n--- Login to {site['display_name']} ---")
    print(f"Hint: {site.get('login_hint', 'Please log in manually in the opened window')}")
    print(f"URL: {site['login_url']}")
    print("Opening Chromium browser (visible window)...\n")

    p, context, page = await launch_chromium(name, headless=False)
    try:
        await page.goto(site["login_url"], wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"Failed to open page: {e}")

    print(">>> Browser is open. Please complete login in the window. <<<")
    print(">>> Close the browser window when you are done. <<<")

    lock_path = get_login_lock_path(name)
    lock_path.write_text("waiting", encoding="utf-8")
    print(f">>> A lock file was created at {lock_path}.")
    print(">>> Login is saved automatically when you delete that lock file.")
    try:
        while lock_path.exists():
            await asyncio.sleep(2)
    except Exception:
        pass

    await close_browser(p, context)
    print(f"[OK] {site['display_name']} session saved to Chromium profile")
    print(f"      Path: {get_profile_path(name)}")


def cmd_list() -> None:
    sites = get_sites()
    if not sites:
        print("No sites configured")
        return
    print("\n=== AI Sites ===")
    print(f"{'Name':<20} {'Display':<20} {'Engine':<12} {'Capabilities':<25} {'Status'}")
    print("-" * 95)
    for s in sites:
        caps = ", ".join(s.get("capabilities", []))
        engine = s.get("preferred_engine", "chromium")
        enabled = "enabled" if s.get("enabled", True) else "disabled"
        profile_dir = PROFILES_DIR / s["name"]
        has_profile = "logged-in" if profile_dir.exists() and any(profile_dir.iterdir()) else "not-logged-in"
        print(f"{s['name']:<20} {s['display_name']:<20} {engine:<12} {caps:<25} {enabled} {has_profile}")
    print(f"\nConfig file: {SITES_FILE}")
    print(f"Profiles directory: {PROFILES_DIR}")


def cmd_add_site():
    print("\n=== Add New AI Site ===")
    print("Press Ctrl+C to cancel. Press Enter to accept defaults.\n")

    name = input("Site ID (English, e.g. my_ai): ").strip()
    if not name:
        print("Name is required")
        return

    if get_site(name):
        print(f"Site {name} already exists. Will overwrite.")

    display_name = input("Display name (e.g. My AI): ").strip() or name
    url = input("Site URL (e.g. https://my-ai.com/): ").strip()
    if not url:
        print("URL is required")
        return

    login_url = input(f"Login URL (default {url}): ").strip() or url
    login_hint = input("Login hint (e.g. login with phone number): ").strip() or "Please log in manually in the opened page"

    print("\nCapabilities (comma-separated, e.g. search,chat,summarize):")
    print("  search=search  chat=chat  summarize=summarize  file_upload=file_upload  video_ai=video AI")
    caps_input = input("Capabilities: ").strip()
    capabilities = [c.strip() for c in caps_input.split(",") if c.strip()] if caps_input else ["chat"]

    print("\nEngine:")
    print("  chromium  - sites that need login state (recommended for AI chat)")
    print("  camoufox  - search/scraping sites with stronger anti-detect")
    engine = input("Preferred engine (default chromium): ").strip() or "chromium"

    print("\nCSS selectors (leave blank for auto-detection):")
    input_sel = input("Input selector (default: textarea): ").strip() or "textarea"
    submit_sel = input("Submit selector (default: button[type='submit']): ").strip() or "button[type='submit']"
    response_sel = input("Response selector (default: div.answer): ").strip() or "div.answer"

    new_site = {
        "name": name,
        "display_name": display_name,
        "url": url,
        "login_url": login_url,
        "login_hint": login_hint,
        "capabilities": capabilities,
        "preferred_engine": engine,
        "selectors": {
            "input": input_sel,
            "submit": submit_sel,
            "response": response_sel
        },
        "special": None,
        "enabled": True
    }

    data = load_json(SITES_FILE)
    sites = data.get("sites", [])
    sites = [s if s["name"] != name else new_site for s in sites]
    if not any(s["name"] == name for s in sites):
        sites.append(new_site)
    data["sites"] = sites
    save_json(SITES_FILE, data)

    print(f"\n[OK] Site {display_name} saved to {SITES_FILE}")
    print(f"      Run 'python browser_ai.py login {name}' to log in.")


async def cmd_open(site_name):
    site = get_site(site_name)
    if not site:
        print(f"Site not found: {site_name}")
        return
    engine = site.get("preferred_engine", "chromium")
    print(f"Opening {site['display_name']} with engine: {engine}...")
    engine, handle = await launch_browser(site_name, headless=False, engine=engine)
    try:
        if engine == "camoufox":
            fox, browser, page = handle
        else:
            p, context, page = handle
        await page.goto(site["url"], wait_until="domcontentloaded", timeout=30000)
        print(f"Opened: {await page.title()}")
        print("Press Enter to close the browser...")
        input()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_browser_by_engine(engine, handle)


async def cmd_search(query: str, dry_run: bool = False) -> None:
    routes = load_json(ROUTES_FILE)
    route = match_route(query, routes)
    print(f"\n=== Smart Search: {query} ===")
    print(f"Task type: {route['task_type']} - {route.get('description', '')}")

    probe_sources = route.get("probe_sources", [])

    if dry_run:
        print(f"\n--- DRY RUN: would probe {len(probe_sources)} sources ---")
        for src in probe_sources:
            site = get_site(src["site"])
            if not site:
                continue
            print(f"  - {site['display_name']} ({site['name']}) engine={site.get('preferred_engine', 'chromium')} weight={src['weight']}")
            print(f"      reason: {src.get('reason', '')}")
        print(f"\nDeep-dive action: {route.get('deep_dive_action', 'Let an AI summarize')}")
        return

    print(f"\n--- Phase 1: probe {len(probe_sources)} sources ---")
    probe_results = {}
    for src in probe_sources:
        site_name = src["site"]
        site = get_site(site_name)
        if not site or not site.get("enabled", True):
            continue
        engine = site.get("preferred_engine", "chromium")
        print(f"\n>> Probing {site['display_name']} (engine={engine}, weight={src['weight']})...")
        result = await probe_one(site, query)
        probe_results[site_name] = {
            "site": site,
            "weight": src["weight"],
            "result": result,
            "reason": src.get("reason", "")
        }
        score = score_result(result, src["weight"])
        print(f"   Score: {score:.2f} - {src.get('reason', '')}")

    print("\n--- Phase 2: evaluate results ---")
    scored = [(name, score_result(r["result"], r["weight"]), r) for name, r in probe_results.items()]
    scored.sort(key=lambda x: x[1], reverse=True)
    for name, score, r in scored:
        print(f"  {r['site']['display_name']:<20} score={score:.2f}")

    threshold = routes.get("quality_scoring", {}).get("deep_dive_threshold", 0.6)
    top = [x for x in scored if x[1] >= threshold]
    if not top and scored:
        top = scored[:1]

    if top:
        print(f"\n--- Phase 3: deep dive ---")
        print(f"Deep dive sources: {', '.join(r['site']['display_name'] for _, _, r in top)}")
        print(f"Suggested action: {route.get('deep_dive_action', 'Let an AI summarize')}")
        print("\n>>> AI assistant will decide the deep dive strategy based on the results above <<<")


def match_route(query: str, routes: dict[str, Any]) -> dict[str, Any]:
    route_list = routes.get("routes", [])
    query_lower = query.lower()
    for route in route_list:
        keywords = route.get("trigger_keywords", [])
        if any(kw.lower() in query_lower for kw in keywords):
            return route
    return routes.get("default_route", {"task_type": "general_search", "probe_sources": []})


async def probe_one(site, query):
    name = site["name"]
    sels = site.get("selectors", {})
    engine = site.get("preferred_engine", "chromium")

    try:
        engine, handle = await launch_browser(name, headless=DEFAULT_HEADLESS, engine=engine)
        if engine == "camoufox":
            fox, browser, page = handle
        else:
            p, context, page = handle

        try:
            await page.goto(site["url"], wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            filled = False
            input_sel = sels.get("input", "textarea")
            submit_sel = sels.get("submit", "button[type='submit']")

            try:
                elem = page.locator(input_sel).first
                if await elem.count() > 0:
                    try:
                        await elem.fill(query, timeout=5000)
                        filled = True
                    except Exception:
                        await elem.fill(query, force=True, timeout=5000)
                        filled = True
                    await page.wait_for_timeout(500)
                    try:
                        await page.locator(submit_sel).first.click(timeout=5000)
                    except Exception:
                        await page.keyboard.press("Enter")
                    await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"   Fill failed: {e}")

            if not filled:
                try:
                    url = page.url
                    if 'baidu.com' in url:
                        from urllib.parse import quote
                        search_url = f'https://www.baidu.com/s?wd={quote(query)}'
                        await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                        await page.wait_for_timeout(5000)
                except Exception as e:
                    print(f"   URL search also failed: {e}")

            body_text = await page.inner_text("body")
            verify_keywords = ['安全验证', '拖动左侧滑块', '请输入验证码', 'VerifyCode', 'captcha', 'wappass.baidu.com']
            if any(kw in body_text for kw in verify_keywords) or 'wappass.baidu.com' in page.url:
                return {
                    "success": False,
                    "error": "captcha_or_verification_triggered",
                    "text": body_text[:500],
                    "length": len(body_text),
                    "urls": [],
                    "engine": engine
                }

            response_sel = sels.get("response", "body")
            try:
                text = await page.locator(response_sel).first.inner_text(timeout=5000)
            except Exception:
                text = body_text

            try:
                js_links = await page.eval_on_selector_all(
                    'a',
                    'elements => elements.map(e => e.href).filter(h => h && (h.includes("mp.weixin.qq.com") || h.includes("weixin.sogou.com/link")))'
                )
                weixin_urls = js_links[:10]
            except Exception:
                weixin_urls = []

            return {
                "success": True,
                "text": text[:3000] if text else "",
                "length": len(text) if text else 0,
                "urls": weixin_urls,
                "all_urls": weixin_urls,
                "engine": engine
            }
        finally:
            await close_browser_by_engine(engine, handle)
    except Exception as e:
        return {"success": False, "error": str(e), "text": "", "length": 0, "engine": engine}


def score_result(result, weight):
    if not result.get("success"):
        return 0.0
    length = result.get("length", 0)
    length_score = min(length / 3000, 1.0)
    return length_score * weight


async def cmd_probe(query: str, dry_run: bool = False) -> None:
    routes = load_json(ROUTES_FILE)
    route = match_route(query, routes)
    print(f"\n=== Probe Search: {query} ===")
    print(f"Matched route: {route['task_type']}")

    for src in route.get("probe_sources", []):
        site = get_site(src["site"])
        if not site:
            continue
        engine = site.get("preferred_engine", "chromium")
        print(f"\n>> {site['display_name']} (engine={engine})")
        result = await probe_one(site, query)
        print(f"   success: {result.get('success')}")
        print(f"   length: {result.get('length', 0)}")
        if result.get("text"):
            print(f"   preview: {result['text'][:300]}...")


async def cmd_weixin(query: str, dry_run: bool = False) -> None:
    print(f"\n=== WeChat Article Search: {query} ===")
    print("Strategy: sogou-weixin (Camoufox) + baidu site:mp.weixin.qq.com + yuanbao AI\n")

    if dry_run:
        print("DRY RUN: would query the following sources:")
        for name in ("sogou_weixin", "baidu", "yuanbao"):
            site = get_site(name)
            if site:
                print(f"  - {site['display_name']} ({site['name']}) engine={site.get('preferred_engine', 'chromium')}")
        return

    print("--- Path 1: sogou weixin search (Camoufox) ---")
    sogou = get_site("sogou_weixin")
    if sogou:
        result = await probe_one(sogou, query)
        text = result.get("text", "")
        if "验证码" in text or "VerifyCode" in text:
            print("! Sogou requires captcha, falling back to path 2")
            result["success"] = False
        if result.get("success") and text:
            print(f"Sogou result length: {result['length']}")
            print(f"Preview:\n{text[:1000]}")
            urls = result.get("urls", [])
            if urls:
                print(f"\nFound {len(urls)} related links (first 5):")
                for i, url in enumerate(urls[:5], 1):
                    print(f"  {i}. {url}")
        else:
            print(f"Sogou search failed: {result.get('error', 'unknown error')}")

    print("\n--- Path 2: baidu site:mp.weixin.qq.com (Camoufox) ---")
    baidu = get_site("baidu")
    if baidu:
        baidu_query = f"site:mp.weixin.qq.com {query}"
        result = await probe_one(baidu, baidu_query)
        if result.get("success") and result.get("text"):
            print(f"Baidu result length: {result['length']}")
            print(f"Preview:\n{result['text'][:1500]}")
            urls = extract_urls(result.get("text", ""))
            if urls:
                print(f"\nFound {len(urls)} possible article links:")
                for i, url in enumerate(urls[:5], 1):
                    print(f"  {i}. {url}")
        else:
            print(f"Baidu search failed: {result.get('error', 'unknown error')}")

    print("\n--- Path 3: yuanbao AI with web search (Chromium, requires login) ---")
    yuanbao = get_site("yuanbao")
    if yuanbao:
        ai_query = f"请帮我搜索关于「{query}」的微信公众号文章，列出文章标题、作者和链接"
        result = await probe_one(yuanbao, ai_query)
        text = result.get("text", "")
        if "登录" in text or "未登录" in text:
            print("! Yuanbao requires login. Run: python browser_ai.py login yuanbao")
        elif result.get("success") and text:
            print(f"Yuanbao result length: {result['length']}")
            print(f"Preview:\n{text[:2000]}")
        else:
            print(f"Yuanbao search failed: {result.get('error', 'unknown error')}")


def extract_urls(text):
    patterns = [
        r'https?://mp\.weixin\.qq\.com/[^\s<>"\')]+',
        r'https?://weixin\.sogou\.com/link\?[^\s<>"\')]+',
    ]
    urls = []
    for pattern in patterns:
        urls.extend(re.findall(pattern, text))
    if not urls:
        general_pattern = r'https?://[^\s<>"\')]+'
        urls = re.findall(general_pattern, text)
    return urls


def parse_args() -> tuple[list[str], bool]:
    """解析命令行参数"""
    global DEFAULT_HEADLESS, FORCE_ENGINE
    args = sys.argv[1:]
    if "--headed" in args:
        DEFAULT_HEADLESS = False
        args.remove("--headed")
    if "--headless" in args:
        DEFAULT_HEADLESS = True
        args.remove("--headless")
    if "--engine" in args:
        idx = args.index("--engine")
        if idx + 1 < len(args):
            FORCE_ENGINE = args[idx + 1]
            args.pop(idx + 1)
            args.pop(idx)
    dry_run = False
    if "--dry-run" in args:
        dry_run = True
        args.remove("--dry-run")
    return args, dry_run


def main() -> None:
    args, dry_run = parse_args()
    if len(args) < 1:
        print(__doc__)
        return

    cmd = args[0]
    cmd_args = args[1:]

    if cmd == "login":
        asyncio.run(cmd_login(cmd_args[0] if cmd_args else None))
    elif cmd == "list":
        cmd_list()
    elif cmd == "add-site":
        cmd_add_site()
    elif cmd == "open":
        if not cmd_args:
            print("Usage: python browser_ai.py open <site_name>")
            return
        asyncio.run(cmd_open(cmd_args[0]))
    elif cmd == "search":
        if not cmd_args:
            print("Usage: python browser_ai.py search \"keyword\"")
            return
        asyncio.run(cmd_search(" ".join(cmd_args), dry_run=dry_run))
    elif cmd == "probe":
        if not cmd_args:
            print("Usage: python browser_ai.py probe \"keyword\"")
            return
        asyncio.run(cmd_probe(" ".join(cmd_args), dry_run=dry_run))
    elif cmd == "weixin":
        if not cmd_args:
            print("Usage: python browser_ai.py weixin \"keyword\"")
            return
        asyncio.run(cmd_weixin(" ".join(cmd_args), dry_run=dry_run))
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()