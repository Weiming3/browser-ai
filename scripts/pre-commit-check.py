#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-commit safety check.

提交前安全检查。

Two modes / 两种模式:

  1. Manual:  python scripts/pre-commit-check.py
     Scans the working tree for sensitive files or content.

  2. Hook:    cp scripts/pre-commit-check.py .git/hooks/pre-commit
     Runs on every `git commit`; exits non-zero to abort the commit
     when something dangerous is staged.

It blocks / 它会阻止:

  - Staging any path under config/profiles/ (browser session data).
  - Staging config/ai_sites.json or config/search_routes.json
    (the runtime configs that may contain your custom sites).
  - Staging any *.log file or *.lock file.
  - Tracking known credential patterns: GitHub tokens, AWS keys,
    OpenAI/Anthropic keys, generic API keys, hard-coded Windows paths.

It does NOT modify your files. It only reports and exits.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

BLOCKED_PATH_PATTERNS = [
    re.compile(r"^config/profiles/"),
    re.compile(r"^config/ai_sites\.json$"),
    re.compile(r"^config/search_routes\.json$"),
    re.compile(r".*\.log$"),
    re.compile(r".*\.lock$"),
    re.compile(r"^.*/chrome_debug\.log$"),
]

CREDENTIAL_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub personal access token (ghp_)"),
    (re.compile(r"gho_[A-Za-z0-9]{20,}"), "GitHub OAuth token (gho_)"),
    (re.compile(r"ghs_[A-Za-z0-9]{20,}"), "GitHub server token (ghs_)"),
    (re.compile(r"ghu_[A-Za-z0-9]{20,}"), "GitHub user token (ghu_)"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained PAT"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI/Anthropic style secret key"),
    (re.compile(r"sk_live_[A-Za-z0-9]{20,}"), "Stripe live secret"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "Google API key"),
]

PATH_PATTERNS = [
    re.compile(r"C:\\Users\\[^\\/\s\"']+", re.IGNORECASE),
    re.compile(r"/Users/[a-zA-Z0-9._-]+/", re.IGNORECASE),
    re.compile(r"/home/[a-zA-Z0-9._-]+/", re.IGNORECASE),
    re.compile(r"G:\\Trae的聊天", re.IGNORECASE),
    re.compile(r"H:\\Trae", re.IGNORECASE),
]

SCAN_EXTENSIONS = {".py", ".json", ".md", ".txt", ".yml", ".yaml", ".bat", ".sh", ".ini", ".cfg", ".toml", ".env"}


def run_git(*args):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def get_staged_files():
    out = run_git("diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB")
    if out:
        return [line.strip() for line in out.splitlines() if line.strip()]
    files = []
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in {"__pycache__", ".git", "node_modules"} for part in p.parts):
            continue
        if p.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        files.append(str(p.relative_to(REPO_ROOT)).replace(os.sep, "/"))
    return files


def scan_path_safety(staged):
    bad = []
    for rel in staged:
        rel_unix = rel.replace(os.sep, "/")
        for pat in BLOCKED_PATH_PATTERNS:
            if pat.search(rel_unix):
                bad.append((rel, f"path matches {pat.pattern}"))
    return bad


def scan_content(staged):
    findings = []
    for rel in staged:
        rel_unix = rel.replace(os.sep, "/")
        if rel_unix.startswith("scripts/pre-commit-check.py"):
            continue
        if rel_unix.endswith(".example.json"):
            continue
        full = REPO_ROOT / rel
        if not full.exists() or not full.is_file():
            continue
        if full.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat, label in CREDENTIAL_PATTERNS:
            for m in pat.finditer(text):
                findings.append((rel, f"credential pattern ({label}): {m.group(0)[:8]}..."))
                break
        for pat in PATH_PATTERNS:
            if pat.search(text):
                findings.append((rel, f"hard-coded local path: {pat.pattern}"))
                break
    return findings


def main():
    staged = get_staged_files()
    if not staged:
        print("[OK] No files to scan.")
        return 0

    print(f"Scanning {len(staged)} file(s)...\n")

    path_issues = scan_path_safety(staged)
    content_issues = scan_content(staged)

    if not path_issues and not content_issues:
        print("[OK] No sensitive files or content detected.")
        return 0

    print("[X] Potential issues found:\n")

    if path_issues:
        print("Blocked paths / 阻止的路径:")
        for path, reason in path_issues:
            print(f"  - {path}")
            print(f"      {reason}")
        print()

    if content_issues:
        print("Content matches / 内容匹配:")
        for path, reason in content_issues:
            print(f"  - {path}")
            print(f"      {reason}")
        print()

    print("=" * 60)
    print("Aborting commit. / 已中止提交。")
    print("=" * 60)
    print()
    print("Fix options / 修复方法:")
    print("  - Remove the offending file(s) from staging:")
    print("      git restore --staged <file>")
    print("  - If the file is essential and safe, edit it to remove the secret")
    print("    or replace with an environment variable.")
    print("  - For local config files, ensure they are listed in .gitignore.")
    return 1


if __name__ == "__main__":
    sys.exit(main())