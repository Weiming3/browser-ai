"""
Smoke tests for browser-ai toolkit.

Basic sanity checks that do NOT require Playwright or Camoufox installed.
They only verify that the code structure, imports, and critical functions
are syntactically valid and behave as expected.

测试方式 / How to run:
    python -m pytest tests/test_smoke.py -v
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
CONFIG_DIR = PROJECT_ROOT / "config"


# ── Module importables  ──────────────────────────────────────────────

def _load_script_module():
    sys.path.insert(0, str(SCRIPTS_DIR))
    import browser_ai
    return browser_ai


# ── Tests ────────────────────────────────────────────────────────────

class TestSmoke:
    """Basic smoke tests that do not need browser engines."""

    def test_module_imports(self):
        """module-level imports raise no errors"""
        mod = _load_script_module()
        for name in (
            "get_sites", "get_site", "get_profile_path",
            "get_login_lock_path", "match_route", "score_result",
            "extract_urls", "launch_chromium", "launch_camoufox",
        ):
            assert hasattr(mod, name), f"missing function: {name}"

    def test_get_login_lock_path(self):
        """lock path uses tempdir, no hard-coded paths"""
        mod = _load_script_module()
        lock = mod.get_login_lock_path("test_site")
        assert "browser_ai_test_site.lock" in str(lock)
        assert str(tempfile.gettempdir()) in str(lock)

    def test_match_route_weixin(self):
        """keyword '公众号' should route to weixin_article"""
        mod = _load_script_module()
        routes = mod.load_json(CONFIG_DIR / "search_routes.example.json")
        route = mod.match_route("跨境电商公众号", routes)
        assert route["task_type"] == "weixin_article"

    def test_match_route_tech(self):
        """keyword '代码' should route to tech_question"""
        mod = _load_script_module()
        routes = mod.load_json(CONFIG_DIR / "search_routes.example.json")
        route = mod.match_route("python异步代码", routes)
        assert route["task_type"] == "tech_question"

    def test_match_route_default(self):
        """unknown query should route to general_search"""
        mod = _load_script_module()
        routes = mod.load_json(CONFIG_DIR / "search_routes.example.json")
        route = mod.match_route("zzznotriggerwordxxx999", routes)
        assert route["task_type"] == "general_search"

    def test_score_result_success(self):
        """a successful result should score > 0"""
        mod = _load_script_module()
        result = {"success": True, "length": 1500}
        score = mod.score_result(result, weight=1.0)
        assert 0 < score <= 1.0

    def test_score_result_failure(self):
        """a failed result should score 0"""
        mod = _load_script_module()
        result = {"success": False, "error": "timeout"}
        score = mod.score_result(result, weight=1.0)
        assert score == 0.0

    def test_extract_urls(self):
        """extract_urls should find weixin URLs"""
        mod = _load_script_module()
        text = (
            "some text https://mp.weixin.qq.com/s/abc123 "
            "and https://weixin.sogou.com/link?url=xxx more"
        )
        urls = mod.extract_urls(text)
        assert len(urls) == 2
        assert "mp.weixin.qq.com" in urls[0]

    def test_extract_urls_empty(self):
        """extract_urls returns empty list when no URLs present"""
        mod = _load_script_module()
        urls = mod.extract_urls("no urls here")
        assert isinstance(urls, list)
        assert len(urls) == 0

    def test_example_json_valid(self):
        """ai_sites.example.json is valid JSON and contains sites"""
        data = json.loads((CONFIG_DIR / "ai_sites.example.json").read_text("utf-8"))
        assert "sites" in data
        assert len(data["sites"]) > 0

    def test_search_routes_valid(self):
        """search_routes.example.json is valid JSON and contains routes"""
        data = json.loads((CONFIG_DIR / "search_routes.example.json").read_text("utf-8"))
        assert "routes" in data
        assert len(data["routes"]) > 0


class TestImportFirefoxLogin(TestSmoke):
    """Smoke tests for import_firefox_login.py (no Firefox needed)."""

    def _load_module(self):
        sys.path.insert(0, str(SCRIPTS_DIR))
        import import_firefox_login
        return import_firefox_login

    def test_module_imports(self):
        mod = self._load_module()
        for name in (
            "load_json", "get_sites", "get_site",
            "get_profile_path", "convert_samesite",
            "cookie_matches_domain",
        ):
            assert hasattr(mod, name), f"missing: {name}"

    def test_convert_samesite(self):
        mod = self._load_module()
        assert mod.convert_samesite(0) == "None"
        assert mod.convert_samesite(1) == "Lax"
        assert mod.convert_samesite(2) == "Strict"
        assert mod.convert_samesite(999) == "Lax"

    def test_cookie_matches_domain_exact(self):
        mod = self._load_module()
        assert mod.cookie_matches_domain("example.com", "example.com") is True

    def test_cookie_matches_domain_wildcard(self):
        mod = self._load_module()
        assert mod.cookie_matches_domain(".example.com", "sub.example.com") is True

    def test_cookie_matches_domain_no_match(self):
        mod = self._load_module()
        assert mod.cookie_matches_domain("other.com", "example.com") is False
