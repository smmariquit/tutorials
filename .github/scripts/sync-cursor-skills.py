#!/usr/bin/env python3
"""Push baseline .cursor skills/rules to smmariquit repos. Skips repos with rich existing setups."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

OWNER = "smmariquit"
TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "cursor-templates"

# Already have project-specific skills — only add baseline if completely missing
SKIP_IF_SKILLS_GTE = 2
RICH_REPOS = {
    "eductools",
    "room-tba",
    "tools",
    "room-tba-feat-isr",
    "room-tba-notify",
    "room-tba-staging-notify",
}

CF_REPOS = {
    "tutorials",
    "kape",
    "the-crib",
    "freshie-guide",
    "joinpizza.fun",
    "uplbtools-me",
    "data-portfolio",
    "scaffolding",
    "web-mobile",
    "ph-github-top",
    "bautista-cayabyab-clan",
    "repairs",
    "uxelbi",
    "uplb-dsg-website",
    "landing-page",
    "gradesim-website",
    "hearthcraft",
    "minecraft-portfolio",
    "eductools",
}


def gh_json(args: list[str]) -> object:
    out = subprocess.check_output(["gh", *args], text=True)
    return json.loads(out) if out.strip() else None


def list_repos(owner: str) -> list[str]:
    out = subprocess.check_output(
        ["gh", "repo", "list", owner, "--limit", "500", "--json", "name,isArchived", "--jq", ".[] | select(.isArchived==false) | .name"],
        text=True,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def file_exists(owner: str, repo: str, path: str) -> bool:
    r = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}/contents/{path}"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def count_skills(owner: str, repo: str) -> int:
    r = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}/contents/.cursor/skills"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return 0
    try:
        items = json.loads(r.stdout)
        return len(items) if isinstance(items, list) else 0
    except json.JSONDecodeError:
        return 0


def put_file(owner: str, repo: str, path: str, content: str, message: str) -> bool:
    body: dict[str, str] = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
    }
    if file_exists(owner, repo, path):
        meta = gh_json(["api", f"repos/{owner}/{repo}/contents/{path}"])
        if isinstance(meta, dict) and meta.get("sha"):
            body["sha"] = meta["sha"]

    proc = subprocess.run(
        ["gh", "api", "-X", "PUT", f"repos/{owner}/{repo}/contents/{path}", "--input", "-"],
        input=json.dumps(body),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"  ! {path}: {proc.stderr.strip()}", file=sys.stderr)
    return proc.returncode == 0


def files_to_sync(repo: str) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    base = TEMPLATE_ROOT / "baseline"
    for src in base.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(base)
        out.append((f".cursor/{rel.as_posix()}", src))

    if repo in CF_REPOS:
        cf = TEMPLATE_ROOT / "cloudflare-pages"
        for src in cf.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(cf)
            out.append((f".cursor/{rel.as_posix()}", src))
    return out


def sync_repo(owner: str, repo: str, dry_run: bool = False) -> str:
    if repo in RICH_REPOS:
        return "skip-rich"
    if count_skills(owner, repo) >= SKIP_IF_SKILLS_GTE:
        return "skip-has-skills"

    targets = files_to_sync(repo)
    if file_exists(owner, repo, ".cursor/skills/repo-baseline/SKILL.md"):
        return "skip-already"

    if dry_run:
        return f"would-sync-{len(targets)}-files"

    ok = 0
    for gh_path, local in targets:
        content = local.read_text(encoding="utf-8")
        if put_file(owner, repo, gh_path, content, "Add baseline Cursor skills and rules"):
            ok += 1
        time.sleep(0.3)  # gentle rate limit
    return f"synced-{ok}-{len(targets)}"


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    owners = ["smmariquit"]
    if "--uplbtools" in sys.argv:
        owners.append("uplbtools")

    summary: dict[str, list[str]] = {}
    for owner in owners:
        for repo in list_repos(owner):
            try:
                result = sync_repo(owner, repo, dry_run=dry_run)
            except subprocess.CalledProcessError as exc:
                result = f"error-{exc}"
            summary.setdefault(result, []).append(f"{owner}/{repo}")
            print(f"{owner}/{repo}: {result}")

    print("\n=== SUMMARY ===")
    for k, v in sorted(summary.items(), key=lambda x: -len(x[1])):
        print(f"{k}: {len(v)}")


if __name__ == "__main__":
    main()
