#!/usr/bin/env python3
"""Scan and fix AI slop in markdown prose across GitHub repos. Rossmann rules, mechanical pass."""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import time
from pathlib import PurePosixPath

OWNERS = ["smmariquit", "uplbtools"]

SKIP_PATH_PREFIXES = (
    ".cursor/",
    ".github/cursor-templates/",
    "node_modules/",
    "vendor/",
    "dist/",
    "build/",
    ".next/",
)

SKIP_FILES = {
    "CHANGELOG.md",  # often auto-generated
}

# Mechanical prose fixes (order matters)
REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bFurthermore,?\s*", re.I), ""),
    (re.compile(r"\bMoreover,?\s*", re.I), "Also, "),
    (re.compile(r"\bIn today'?s (fast-paced )?world,?\s*", re.I), ""),
    (re.compile(r"\bIt'?s worth noting that\s*", re.I), ""),
    (re.compile(r"\bIt'?s important to note that\s*", re.I), ""),
    (re.compile(r"\bWhen it comes to\s+", re.I), "For "),
    (re.compile(r"\bAt the end of the day,?\s*", re.I), ""),
    (re.compile(r"\bWhether you'?re\b", re.I), "If you are"),
    (re.compile(r"\bdelve\b", re.I), "explore"),
    (re.compile(r"\bdelving\b", re.I), "exploring"),
    (re.compile(r"\bleverage\b", re.I), "use"),
    (re.compile(r"\bleverages\b", re.I), "uses"),
    (re.compile(r"\bleveraged\b", re.I), "used"),
    (re.compile(r"\bleveraging\b", re.I), "using"),
    (re.compile(r"\butilize\b", re.I), "use"),
    (re.compile(r"\butilizes\b", re.I), "uses"),
    (re.compile(r"\butilized\b", re.I), "used"),
    (re.compile(r"\butilizing\b", re.I), "using"),
    (re.compile(r"\brobust\b", re.I), "stable"),
    (re.compile(r"\bseamless(ly)?\b", re.I), "smooth"),
    (re.compile(r"\bcomprehensive\b", re.I), "full"),
    (re.compile(r"\bsignificantly\b", re.I), ""),
    (re.compile(r"\bpivotal\b", re.I), "key"),
    (re.compile(r"\bparamount\b", re.I), "main"),
    (re.compile(r"\bunderscore(s|d)?\b", re.I), "highlight"),
    (re.compile(r"\bnavigate the\b", re.I), "work through the"),
    (re.compile(r"\bfoster(s|ing)?\b", re.I), "support"),
    (re.compile(r"\bstreamline(s|d)?\b", re.I), "simplify"),
    (re.compile(r"\bMoreover\b", re.I), "Also"),
    (re.compile(r"\bAdditionally,?\s*", re.I), ""),
    (re.compile(r"\bIn essence,?\s*", re.I), ""),
    (re.compile(r"\bTo put it simply,?\s*", re.I), ""),
    (re.compile(r"\bThat being said,?\s*", re.I), ""),
    # em dash variants → colon in list contexts, period otherwise
    (re.compile(r"\)\s*—\s*"), "): "),
    (re.compile(r"\*\*\s*—\s*"), "**: "),
    (re.compile(r"\s—\s*"), ": "),
    (re.compile(r"\s–\s*"), ": "),
    (re.compile(r"(?<![\-])\-\-(?![\-])"), ", "),
    (re.compile(r"  +"), " "),
    (re.compile(r"\n{3,}"), "\n\n"),
]


def gh_json(args: list[str]) -> object:
    return json.loads(subprocess.check_output(["gh", *args], text=True))


def list_repos(owner: str) -> list[str]:
    out = subprocess.check_output(
        ["gh", "repo", "list", owner, "--limit", "500", "--json", "name,isArchived", "--jq", ".[] | select(.isArchived==false) | .name"],
        text=True,
    )
    return [x.strip() for x in out.splitlines() if x.strip()]


def should_skip(path: str) -> bool:
    if path in SKIP_FILES:
        return True
    return any(path.startswith(p) for p in SKIP_PATH_PREFIXES)


def get_md_paths(owner: str, repo: str) -> list[str]:
    try:
        meta = gh_json(["api", f"repos/{owner}/{repo}"])
        branch = meta["default_branch"]
        tree = gh_json(["api", f"repos/{owner}/{repo}/git/trees/{branch}?recursive=1"])
    except subprocess.CalledProcessError:
        return []
    paths: list[str] = []
    for item in tree.get("tree", []):
        if item.get("type") != "blob":
            continue
        p = item["path"]
        if not (p.endswith(".md") or p.endswith(".mdx")):
            continue
        if should_skip(p):
            continue
        paths.append(p)
    return paths


def get_file(owner: str, repo: str, path: str) -> tuple[str | None, str | None]:
    try:
        data = gh_json(["api", f"repos/{owner}/{repo}/contents/{path}"])
        if isinstance(data, list) or data.get("encoding") != "base64":
            return None, None
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return content, data["sha"]
    except subprocess.CalledProcessError:
        return None, None


def slop_score(text: str) -> int:
    score = 0
    for pat, _ in REPLACEMENTS:
        score += len(pat.findall(text))
    score += len(re.findall(r"—|–", text))
    score += len(re.findall(r"\bnot (just|only) .{1,50} but\b", text, re.I))
    return score


def deslop_prose(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out_lines: list[str] = []
    for line in lines:
        # Preserve YAML frontmatter delimiters and markdown HR
        if re.match(r"^---\s*$", line):
            out_lines.append(line)
            continue
        chunk = line
        for pat, repl in REPLACEMENTS:
            chunk = pat.sub(repl, chunk)
        chunk = re.sub(r" +([,.])", r"\1", chunk)
        out_lines.append(chunk)
    out = "".join(out_lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out


def deslop(text: str) -> str:
    parts = re.split(r"(```[\s\S]*?```)", text)
    out: list[str] = []
    for i, part in enumerate(parts):
        if part.startswith("```"):
            out.append(part)
        else:
            out.append(deslop_prose(part))
    return "".join(out)


def put_file(owner: str, repo: str, path: str, content: str, sha: str, message: str) -> bool:
    body = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha,
    }
    proc = subprocess.run(
        ["gh", "api", "-X", "PUT", f"repos/{owner}/{repo}/contents/{path}", "--input", "-"],
        input=json.dumps(body),
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def process_repo(owner: str, repo: str, dry_run: bool = False) -> dict:
    result = {"repo": f"{owner}/{repo}", "scanned": 0, "fixed": [], "skipped": 0}
    paths = get_md_paths(owner, repo)
    for path in paths:
        content, sha = get_file(owner, repo, path)
        if content is None or sha is None:
            result["skipped"] += 1
            continue
        result["scanned"] += 1
        before_score = slop_score(content)
        if before_score == 0:
            continue
        fixed = deslop(content)
        if fixed == content:
            continue
        after_score = slop_score(fixed)
        if dry_run:
            result["fixed"].append({"path": path, "before": before_score, "after": after_score})
            continue
        if put_file(owner, repo, path, fixed, sha, "Remove AI slop from prose (mechanical deslop pass)"):
            result["fixed"].append({"path": path, "before": before_score, "after": after_score})
        time.sleep(0.35)
    return result


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    owners = OWNERS
    if "--owner" in sys.argv:
        owners = [sys.argv[sys.argv.index("--owner") + 1]]
    skip_until = None
    if "--skip-until" in sys.argv:
        skip_until = sys.argv[sys.argv.index("--skip-until") + 1]
        skipping = True
    else:
        skipping = False

    all_fixed: list[dict] = []
    total_files = 0
    for owner in owners:
        for repo in list_repos(owner):
            if skipping:
                if repo == skip_until:
                    skipping = False
                else:
                    continue
            try:
                r = process_repo(owner, repo, dry_run=dry_run)
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR {owner}/{repo}: {exc}", file=sys.stderr)
                continue
            total_files += r["scanned"]
            if r["fixed"]:
                all_fixed.append(r)
                print(f"{r['repo']}: fixed {len(r['fixed'])} files")
                for f in r["fixed"]:
                    print(f"  {f['path']} ({f['before']}→{f['after']} slop hits)")
            time.sleep(0.2)

    print(f"\n=== SUMMARY ===")
    print(f"Repos with fixes: {len(all_fixed)}")
    print(f"Files fixed: {sum(len(r['fixed']) for r in all_fixed)}")
    print(f"Files scanned: {total_files}")
    if dry_run:
        print("(dry run — no commits)")


if __name__ == "__main__":
    main()
