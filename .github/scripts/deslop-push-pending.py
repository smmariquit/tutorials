#!/usr/bin/env python3
"""Push pending deslop commits: pull --rebase then push for repos under a root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path.home() / "dev/personal"
MSG = "Remove AI slop from prose (mechanical deslop pass)"


def main() -> None:
    ok = fail = 0
    for git in sorted(ROOT.rglob(".git")):
        if not git.is_dir():
            continue
        repo = git.parent
        head = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if head.stdout.strip() != MSG:
            continue
        ahead = subprocess.run(
            ["git", "rev-list", "--count", "@{u}..HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if ahead.returncode != 0 or ahead.stdout.strip() in {"", "0"}:
            continue
        pull = subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=repo, capture_output=True, text=True)
        if pull.returncode != 0:
            print(f"FAIL pull {repo.name}: {pull.stderr or pull.stdout}")
            fail += 1
            continue
        push = subprocess.run(["git", "push"], cwd=repo, capture_output=True, text=True)
        if push.returncode != 0:
            print(f"FAIL push {repo.name}: {push.stderr or push.stdout}")
            fail += 1
        else:
            print(f"OK {repo.name}")
            ok += 1
    print(f"\nPushed: {ok}, failed: {fail}")


if __name__ == "__main__":
    main()
