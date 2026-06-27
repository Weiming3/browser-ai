#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch-import Firefox login cookies into Chromium profiles.

从 Firefox 批量导入登录 cookies 到 Chromium profiles。

SECURITY WARNING / 安全警告:
    - This script reads cookies from your local Firefox profile. The cookies
      are equivalent to active login sessions. NEVER share the output profiles.
    - 本脚本会读取你本地 Firefox 的 cookies。这些 cookies 等同于活动登录会话。
      切勿共享输出的 profiles 目录。
    - The resulting profiles live under config/profiles/<site>/ and are
      gitignored by default. Do not change that.
    - 生成的 profiles 保存在 config/profiles/<site>/，默认已被 .gitignore 排除。
      请勿修改。

Workflow / 工作原理:
    1. Read cookies.sqlite from a Firefox profile.
    2. For each enabled Chromium site, extract matching cookies by domain.
    3. Inject them via Playwright into a persistent Chromium context.
    4. Verify the login state by visiting the login URL.

Usage / 用法:
    python import_firefox_login.py                    # Import all chromium sites
    python import_firefox_login.py --list              # List available sites and Firefox cookies
    python import_firefox_login.py --dry-run           # Preview only, do not modify anything
    python import_firefox_login.py --site yuanbao      # Import a single site
    python import_firefox_login.py --profile 1         # Pick a specific Firefox profile
"""
import asyncio
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

SiteDict = dict[str, Any]
FirefoxCookie = dict[str, Any]
FirefoxProfileInfo = dict[str, Any]

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_DIR = SCRIPT_DIR.parent / "config"
SITES_FILE = CONFIG_DIR / "ai_sites.json"
PROFILES_DIR = CONFIG_DIR / "profiles"

FIREFOX_PROFILES_DIR = Path(os.environ["APPDATA"]) / "Mozilla" / "Firefox" / "Profiles"
FIREFOX_INI = Path(os.environ["APPDATA"]) / "Mozilla" / "Firefox" / "profiles.ini"


def load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_sites():
    return load_json(SITES_FILE).get("sites", [])


def get_site(name):
    for s in get_sites():
        if s["name"] == name:
            return s
    return None


def get_profile_path(site_name):
    p = PROFILES_DIR / site_name
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def find_firefox_profiles():
    if not FIREFOX_PROFILES_DIR.exists():
        print("Error: Firefox profiles directory not found at")
        print(f"  {FIREFOX_PROFILES_DIR}")
        return []

    profiles = {}
    for d in sorted(FIREFOX_PROFILES_DIR.iterdir()):
        if d.is_dir():
            cookies_path = d / "cookies.sqlite"
            profiles[d.name] = {
                "name": d.name,
                "path": d,
                "has_cookies": cookies_path.exists(),
                "cookies_size": cookies_path.stat().st_size if cookies_path.exists() else 0,
                "is_default": False,
            }

    if FIREFOX_INI.exists():
        with open(FIREFOX_INI, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        install_match = re.search(r'\[Install[^\]]*\]\s*\n\s*Default=(.+)', content)
        if install_match:
            path_part = install_match.group(1).strip()
            p = Path(os.environ["APPDATA"]) / "Mozilla" / "Firefox" / path_part
            if p.name in profiles:
                profiles[p.name]["is_default"] = True
                return list(profiles.values())

        profile_blocks = re.findall(
            r'\[Profile(\d+)\](.*?)(?=\n\[|\Z)', content,
            re.DOTALL
        )
        for num, block in profile_blocks:
            if re.search(r'\n\s*Default\s*=\s*1', block):
                path_match = re.search(r'\n\s*Path\s*=\s*(.+)', block)
                if path_match:
                    p = Path(os.environ["APPDATA"]) / "Mozilla" / "Firefox" / path_match.group(1).strip()
                    if p.name in profiles:
                        profiles[p.name]["is_default"] = True
                        break

    return list(profiles.values())


def read_firefox_cookies(profile_dir):
    cookies_path = profile_dir / "cookies.sqlite"
    if not cookies_path.exists():
        print(f"  Error: {cookies_path} does not exist")
        return {}

    tmp = Path(tempfile.gettempdir()) / f"_ff_cookies_{os.getpid()}.sqlite"
    try:
        shutil.copy2(str(cookies_path), str(tmp))
    except Exception as e:
        print(f"  Error: cannot copy cookies.sqlite: {e}")
        return {}

    domain_cookies = {}
    try:
        conn = sqlite3.connect(str(tmp))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='moz_cookies'")
        if not cur.fetchone():
            print("  Warning: cookies.sqlite does not contain moz_cookies table; is this an old Firefox?")
            conn.close()
            return {}
        cur.execute("""
            SELECT name, value, host, path, isSecure, isHttpOnly, sameSite, expiry
            FROM moz_cookies
        """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            print("  Warning: cookies.sqlite has no cookie data")
            return {}

        for row in rows:
            host = row["host"]
            if host not in domain_cookies:
                domain_cookies[host] = []
            domain_cookies[host].append({
                "name": row["name"],
                "value": row["value"],
                "host": host,
                "path": row["path"],
                "secure": bool(row["isSecure"]),
                "http_only": bool(row["isHttpOnly"]),
                "same_site": row["sameSite"],
                "expiry": row["expiry"],
            })
    finally:
        try:
            os.remove(str(tmp))
        except Exception:
            pass

    return domain_cookies


def convert_samesite(ff_value: int) -> str:
    mapping = {0: "None", 1: "Lax", 2: "Strict"}
    return mapping.get(ff_value, "Lax")


def cookie_matches_domain(cookie_host, target_domain):
    if cookie_host == target_domain:
        return True
    if cookie_host.startswith("."):
        return target_domain.endswith(cookie_host) or target_domain == cookie_host.lstrip(".")
    return cookie_host == target_domain


def get_domains_for_site(site):
    configured = site.get("cookie_domains", [])
    if configured:
        return configured

    login_url = site.get("login_url", site.get("url", ""))
    parsed = urlparse(login_url)
    host = parsed.netloc.lower()

    bare_host = host[4:] if host.startswith("www.") else host

    parts = bare_host.split(".")
    if len(parts) >= 2:
        root_domain = "." + ".".join(parts[-2:])
    else:
        root_domain = "." + bare_host

    domains = [host, bare_host, root_domain, "." + bare_host]
    domains = list(dict.fromkeys(domains))
    return domains


async def inject_cookies_to_chromium(site, cookies_to_inject, dry_run=False):
    name = site["name"]
    display_name = site["display_name"]
    profile_path = get_profile_path(name)

    if dry_run:
        return {
            "site": name,
            "display": display_name,
            "cookies_found": len(cookies_to_inject),
            "injected": 0,
            "verified": None,
        }

    from playwright.async_api import async_playwright

    p = await async_playwright().start()
    try:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--window-size=1280,800",
            ],
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )

        pw_cookies = []
        skipped = 0
        for c in cookies_to_inject:
            try:
                pw_c = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c["host"],
                    "path": c["path"] or "/",
                    "secure": c["secure"],
                    "httpOnly": c["http_only"],
                    "sameSite": convert_samesite(c["same_site"]),
                    "expires": c["expiry"] / 1000 if c["expiry"] > 1000000000000 else c["expiry"],
                }
                pw_cookies.append(pw_c)
            except Exception:
                skipped += 1

        if pw_cookies:
            try:
                await context.add_cookies(pw_cookies)
            except Exception as e:
                print(f"  Injection failed: {e}")
                await context.close()
                await p.stop()
                return {
                    "site": name,
                    "display": display_name,
                    "cookies_found": len(cookies_to_inject),
                    "injected": 0,
                    "verified": False,
                    "error": str(e),
                }

        verified = await verify_login(context, site)
        await context.close()
        await p.stop()

        return {
            "site": name,
            "display": display_name,
            "cookies_found": len(cookies_to_inject),
            "injected": len(pw_cookies),
            "skipped": skipped,
            "verified": verified,
        }
    except Exception as e:
        try:
            await p.stop()
        except Exception:
            pass
        return {
            "site": name,
            "display": display_name,
            "cookies_found": len(cookies_to_inject),
            "injected": 0,
            "verified": False,
            "error": str(e),
        }


async def verify_login(context: Any, site: SiteDict) -> Optional[bool]:
    login_url = site.get("login_url", site.get("url", ""))
    name = site["name"]
    try:
        page = await context.new_page()
        await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        body = await page.inner_text("body")

        not_logged_in = any(
            kw in body for kw in ["登录", "未登录", "sign in", "Sign in", "login", "Login"]
        )
        logged_in = any(
            kw in body for kw in [
                "退出", "注销", "我的", "个人中心", "设置",
                "新建对话", "历史记录", "logout", "Logout",
            ]
        )

        if name == "baidu":
            logged_in = "用户名" in body or "个人中心" in body or "百度首页" in await page.title()
            not_logged_in = "登录" in body and "退出" not in body

        if name in ("yuanbao", "doubao", "kimi", "tongyi"):
            if "新建对话" in body or "历史记录" in body or "我的" in body:
                logged_in = True
                not_logged_in = False

        await page.close()

        if logged_in:
            return True
        if not_logged_in:
            return False
        return None
    except Exception:
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch-import Firefox login state into Chromium profiles.")
    parser.add_argument("--list", action="store_true", help="List available cookies in Firefox")
    parser.add_argument("--dry-run", action="store_true", help="Preview mode: do not modify anything")
    parser.add_argument("--site", type=str, default=None, help="Only import the specified site")
    parser.add_argument("--profile", type=str, default=None, help="Firefox profile name or number")
    args = parser.parse_args()

    profiles = find_firefox_profiles()
    if not profiles:
        print("No Firefox profiles found")
        sys.exit(1)

    if len(profiles) == 1:
        selected = profiles[0]
    else:
        default = None
        print("\nAvailable Firefox Profiles:")
        for i, prof in enumerate(profiles, 1):
            marker = " [default]" if prof.get("is_default") else ""
            size_mb = prof["cookies_size"] / (1024 * 1024)
            status = f"({size_mb:.1f}MB cookies)" if prof["has_cookies"] else "(no cookies)"
            print(f"  {i}. {prof['name']} {status}{marker}")
            if prof.get("is_default"):
                default = i

        if args.profile:
            try:
                idx = int(args.profile)
                selected = profiles[idx - 1]
            except (ValueError, IndexError):
                print(f"Invalid number: {args.profile}")
                sys.exit(1)
        else:
            if default:
                selected = profiles[default - 1]
                print(f"\nAuto-selected default profile: {selected['name']}")
            else:
                choice = input("\nSelect profile (number): ").strip()
                try:
                    selected = profiles[int(choice) - 1]
                except (ValueError, IndexError):
                    print("Invalid selection")
                    sys.exit(1)

    print(f"\nUsing Firefox profile: {selected['name']}")
    if not selected["has_cookies"]:
        print("This profile has no cookies.sqlite; cannot import")
        sys.exit(1)

    print("Reading Firefox cookies...")
    domain_cookies = read_firefox_cookies(selected["path"])
    total = sum(len(v) for v in domain_cookies.values())
    print(f"  Total: {total} cookies across {len(domain_cookies)} domains")

    sites = [s for s in get_sites() if s.get("enabled", True) and s.get("preferred_engine", "chromium") == "chromium"]
    if args.site:
        sites = [s for s in sites if s["name"] == args.site]
        if not sites:
            print(f"No chromium site matched: {args.site}")
            print(f"Available: {', '.join(s['name'] for s in get_sites() if s.get('preferred_engine') == 'chromium')}")
            sys.exit(1)

    if args.list:
        print(f"\n{'Site':<20} {'Domains':<30} {'Matched cookies':<12}")
        print("-" * 62)
        for site in sites:
            domains = get_domains_for_site(site)
            matched = []
            for d in domains:
                for host, cookies in domain_cookies.items():
                    if cookie_matches_domain(host, d):
                        matched.extend(cookies)
            unique = list({c["name"] for c in matched})
            print(f"{site['name']:<20} {', '.join(domains):<30} {len(unique)}")
            if unique:
                for n in sorted(unique)[:5]:
                    print(f"  {'':<20} {n}")
                if len(unique) > 5:
                    print(f"  {'':<20} ... total {len(unique)}")
        return

    if args.dry_run:
        print(f"\n{'Site':<20} {'Display':<20} {'Cookies':<10} {'Expected'}")
        print("-" * 70)
        for site in sites:
            domains = get_domains_for_site(site)
            matched = []
            for d in domains:
                for host, cookies in domain_cookies.items():
                    if cookie_matches_domain(host, d):
                        matched.extend(cookies)
            unique = list({c["name"] for c in matched})
            status = "[OK] can import" if unique else "[--] no match"
            print(f"{site['name']:<20} {site['display_name']:<20} {len(unique):<10} {status}")
        print(f"\nRun without --dry-run to actually import")
        return

    print(f"\nPreparing to import {len(sites)} sites...")
    results = []

    for site in sites:
        domains = get_domains_for_site(site)
        matched = []
        for d in domains:
            for host, cookies in domain_cookies.items():
                if cookie_matches_domain(host, d):
                    matched.extend(cookies)

        unique_cookies = list({c["name"]: c for c in matched}.values())
        if not unique_cookies:
            print(f"\n  {site['display_name']}: no matching cookies, skipping")
            results.append({
                "site": site["name"],
                "display": site["display_name"],
                "cookies_found": 0,
                "injected": 0,
                "verified": None,
                "skipped": 0,
            })
            continue

        print(f"\n--- {site['display_name']} ---")
        print(f"  Matched {len(unique_cookies)} cookies from: {', '.join(domains)}")
        result = asyncio.run(inject_cookies_to_chromium(site, unique_cookies))
        results.append(result)

        if result.get("error"):
            print(f"  [X] Error: {result['error']}")
        else:
            status = {True: "[OK] logged-in", False: "[X] not logged-in", None: "[?] uncertain"}.get(result["verified"], "[?] uncertain")
            print(f"  Injected {result['injected']} cookies {status}")

    print(f"\n{'='*50}")
    print(f"Import summary")
    print(f"{'='*50}")
    print(f"{'Site':<20} {'cookies':<10} {'injected':<8} {'status'}")
    print("-" * 50)
    success = 0
    for r in results:
        status = {True: "[OK] logged-in", False: "[X] not logged-in", None: "[?] uncertain", "": ""}.get(r.get("verified"), "")
        if r.get("verified") is True:
            success += 1
        print(f"{r['display']:<20} {r['cookies_found']:<10} {r['injected']:<8} {status}")
    print(f"\n{len(results)} sites, {success} verified")
    if success < len(results):
        print("Failed sites may need manual login: python browser_ai.py login <site_name>")


if __name__ == "__main__":
    main()