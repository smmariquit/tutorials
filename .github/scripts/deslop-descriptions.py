#!/usr/bin/env python3
"""Remove AI slop from GitHub repo description fields (smmariquit + uplbtools)."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "deslop-repos.py"
spec = importlib.util.spec_from_file_location("deslop_repos", SCRIPT)
deslop_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(deslop_mod)

OWNERS = deslop_mod.OWNERS
slop_score = deslop_mod.slop_score
gh_json = deslop_mod.gh_json
list_repos = deslop_mod.list_repos

# Word-level tells only (no markdown punctuation munging)
WORD_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bleverage\b", re.I), "use"),
    (re.compile(r"\brobust\b", re.I), "stable"),
    (re.compile(r"\bcomprehensive\b", re.I), "full"),
    (re.compile(r"\bseamless(ly)?\b", re.I), "smooth"),
    (re.compile(r"\bdelve\b", re.I), "explore"),
    (re.compile(r"\bagentic-AI\b", re.I), "AI"),
]

EXTRA: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"^🌐🎓 Empowering ICT students through decentralized proof of skills$", re.I),
        "🌐🎓 Decentralized proof of skills for ICT students",
    ),
    (re.compile(r"\bdesigned to show the best GitHub has to offer\.?", re.I), "GitHub demo repository."),
    (re.compile(r"\s*Build\. Share\. Inspire\.\s*", re.I), " "),
    (re.compile(r", a quiet reminder that the world keeps turning\.?", re.I), ""),
    (re.compile(r"\bhelping citizens stay safe and guiding city planners toward\b", re.I), "for"),
    (re.compile(r"\bwith type-safe APIs and modern UI\.?", re.I), ""),
    (re.compile(r"\bwith modern UI\.?", re.I), ""),
    (re.compile(r"  +"), " "),
]


def deslop_description(text: str) -> str:
    out = text.strip()
    if re.search(r"^[^—–]{1,80}:", out):
        out = re.sub(r"\s[—–]\s+", ". ", out)
    else:
        out = re.sub(r"\s[—–]\s+", ": ", out)
    for pat, repl in WORD_REPLACEMENTS + EXTRA:
        out = pat.sub(repl, out)
    out = re.sub(r"\.\s+([a-z])", lambda m: ". " + m.group(1).upper(), out)
    out = re.sub(r":\s*:", ": ", out)
    out = re.sub(r"\.\s*\.", ".", out)
    out = re.sub(r"  +", " ", out).strip()
    return out[:350]


def meaningful_change(before: str, after: str) -> bool:
    if before == after:
        return False
    if slop_score(after) < slop_score(before):
        return True
    if re.search(r"[—–]", before) and not re.search(r"[—–]", after):
        return True
    if re.search(r"\bEmpowering\b", before, re.I):
        return True
    if "designed to show the best" in before.lower() and "designed to show the best" not in after.lower():
        return True
    if "Build. Share. Inspire." in before and "Build. Share. Inspire." not in after:
        return True
    return False


def get_description(owner: str, repo: str) -> str | None:
    try:
        data = gh_json(["api", f"repos/{owner}/{repo}"])
        return data.get("description") or ""
    except subprocess.CalledProcessError:
        return None


def set_description(owner: str, repo: str, description: str) -> bool:
    proc = subprocess.run(
        ["gh", "repo", "edit", f"{owner}/{repo}", "--description", description],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    owners = OWNERS
    if "--owner" in sys.argv:
        owners = [sys.argv[sys.argv.index("--owner") + 1]]

    fixed: list[dict] = []
    for owner in owners:
        for repo in list_repos(owner):
            desc = get_description(owner, repo)
            if desc is None or not desc.strip():
                continue
            before_score = slop_score(desc)
            new_desc = deslop_description(desc)
            if not meaningful_change(desc, new_desc):
                continue
            after_score = slop_score(new_desc)
            entry = {
                "repo": f"{owner}/{repo}",
                "before": desc,
                "after": new_desc,
                "score": f"{before_score}→{after_score}",
            }
            if dry_run:
                fixed.append(entry)
                print(f"{entry['repo']} ({entry['score']})")
                print(f"  was: {desc}")
                print(f"  now: {new_desc}")
                continue
            if set_description(owner, repo, new_desc):
                fixed.append(entry)
                print(f"{entry['repo']} ({entry['score']})")
            else:
                print(f"FAIL {owner}/{repo}", file=sys.stderr)
            time.sleep(0.25)

    print(f"\n=== SUMMARY ===")
    print(f"Descriptions updated: {len(fixed)}")
    if dry_run:
        print("(dry run — no changes)")


if __name__ == "__main__":
    main()
