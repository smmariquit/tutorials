#!/usr/bin/env python3
"""Deslop markdown in local git clones under a root directory. One commit per repo."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path.home() / "dev/personal"
DRY = "--dry-run" in sys.argv
COMMIT_MSG = "Remove AI slop from prose (mechanical deslop pass)"

SCRIPT = Path(__file__).resolve().parent / "deslop-repos.py"
spec = importlib.util.spec_from_file_location("deslop_repos", SCRIPT)
deslop_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(deslop_mod)

SKIP_PREFIXES = deslop_mod.SKIP_PATH_PREFIXES
SKIP_FILES = deslop_mod.SKIP_FILES
should_skip = deslop_mod.should_skip
slop_score = deslop_mod.slop_score
deslop = deslop_mod.deslop


def find_repos(root: Path) -> list[Path]:
    repos: list[Path] = []
    for git in root.rglob(".git"):
        if git.is_dir():
            repos.append(git.parent)
    return sorted(set(repos))


def rel_skip(path: Path, repo: Path) -> bool:
    rel = path.relative_to(repo).as_posix()
    return should_skip(rel)


def process_repo(repo: Path) -> dict:
    result = {"repo": repo.name, "fixed": [], "scanned": 0}
    for path in sorted(repo.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in {".md", ".mdx"}:
            continue
        if rel_skip(path, repo):
            continue
        if path.name in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        result["scanned"] += 1
        if slop_score(text) == 0:
            continue
        fixed = deslop(text)
        if fixed == text:
            continue
        rel = path.relative_to(repo).as_posix()
        if not DRY:
            path.write_text(fixed, encoding="utf-8")
        result["fixed"].append(
            {"path": rel, "before": slop_score(text), "after": slop_score(fixed)}
        )
    if result["fixed"] and not DRY:
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", COMMIT_MSG], cwd=repo, check=True)
        push = subprocess.run(["git", "push"], cwd=repo, capture_output=True, text=True)
        if push.returncode != 0:
            result["push_error"] = push.stderr.strip() or push.stdout.strip()
    return result


def main() -> None:
    repos = find_repos(ROOT)
    fixed_repos: list[dict] = []
    for repo in repos:
        try:
            r = process_repo(repo)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {repo.name}: {exc}", file=sys.stderr)
            continue
        if r["fixed"]:
            fixed_repos.append(r)
            print(f"{r['repo']}: fixed {len(r['fixed'])} files")
            for f in r["fixed"]:
                print(f"  {f['path']} ({f['before']}→{f['after']})")
            if r.get("push_error"):
                print(f"  PUSH FAILED: {r['push_error']}")
    print("\n=== SUMMARY ===")
    print(f"Local repos scanned: {len(repos)}")
    print(f"Repos with fixes: {len(fixed_repos)}")
    print(f"Files fixed: {sum(len(r['fixed']) for r in fixed_repos)}")
    if DRY:
        print("(dry run — no commits)")


if __name__ == "__main__":
    main()
