#!/usr/bin/env python3
"""No-slop pass on user-facing website copy: i18n JSON, Astro pages, MDX content, UI strings."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path.home() / "dev/personal"
DRY = "--dry-run" in sys.argv
COMMIT_MSG = "Remove AI slop from website copy (noslop pass)"

spec = importlib.util.spec_from_file_location(
    "fuck_slop_local",
    Path(__file__).resolve().parent / "fuck-slop-local.py",
)
fsl = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fsl)

fuck_slop = fsl.fuck_slop

SKIP_PARTS = {".cursor", "node_modules", ".git", ".venv", "dist", "build", ".next", ".output", "package-lock.json"}
SKIP_SUBSTR = (
    "/data/opportunity",
    "opportunity-images.json",
    "room-tba-staging",
    "room-tba-notify",
    "room-tba-feat",
    "room-tba-demo",
    ".github/cursor-templates",
)


def deslop_string(s: str) -> str:
    if not isinstance(s, str) or not s.strip():
        return s
    return fuck_slop(s)


def deslop_json_obj(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: deslop_json_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deslop_json_obj(v) for v in obj]
    if isinstance(obj, str):
        return deslop_string(obj)
    return obj


def deslop_json_file(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = deslop_json_obj(data)
    return json.dumps(out, ensure_ascii=False, indent=2) + "\n"


def is_ui_tsx_line(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith("//") or s.startswith("*") or s.startswith("/*"):
        return False
    if re.search(r"(title|description|aria-label|placeholder|alt)=", line):
        return True
    if re.search(r"[>'\"`][^<'\"]* — ", line):
        return True
    if re.search(r">\s*[^<{][^<]*—", line):
        return True
    if re.search(r" — ", line) and not s.startswith("//") and not s.startswith("*"):
        return True


def deslop_tsx(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    for line in lines:
        if is_ui_tsx_line(line):
            out.append(fuck_slop(line))
        else:
            out.append(line)
    return "".join(out)


def should_process(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if any(p in path.parts for p in SKIP_PARTS):
        return False
    if any(s in rel for s in SKIP_SUBSTR):
        return False
    if path.name == "package-lock.json":
        return False
    if path.suffix == ".json" and "messages" in path.parts:
        return True
    if path.suffix in {".mdx", ".md"} and "src/content" in rel:
        return True
    if path.suffix == ".astro" and ("src/pages" in rel or "src/layouts" in rel):
        return True
    if path.suffix in {".tsx", ".jsx"} and any(
        x in rel
        for x in (
            "CookieConsent",
            "accessibility/",
            "src/pages/Home",
            "WriteupExercise",
            "WriteupExercises",
            "StatesOfMatter",
            "doctor-now-global-ui/src/pages",
        )
    ):
        return True
    if path.suffix == ".html" and path.name == "index.html" and "public" in path.parts:
        return True
    return False


def transform(path: Path) -> str | None:
    if path.suffix == ".json":
        return deslop_json_file(path)
    if path.suffix in {".tsx", ".jsx"}:
        return deslop_tsx(path)
    return fuck_slop(path.read_text(encoding="utf-8"))


def repo_root(path: Path) -> Path | None:
    for parent in [path.parent, *path.parents]:
        if (parent / ".git").is_dir():
            return parent
    return None


def commit_repo(repo: Path, paths: list[Path]) -> str | None:
    rels = [str(p.relative_to(repo)) for p in paths]
    subprocess.run(["git", "add", "--"] + rels, cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", COMMIT_MSG], cwd=repo, check=True)
    pull = subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=repo, capture_output=True, text=True)
    if pull.returncode != 0:
        return pull.stderr or pull.stdout
    push = subprocess.run(["git", "push"], cwd=repo, capture_output=True, text=True)
    if push.returncode != 0:
        return push.stderr or push.stdout
    return None


def main() -> None:
    changed: dict[Path, list[Path]] = {}
    scanned = 0
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not should_process(path):
            continue
        scanned += 1
        try:
            before = path.read_text(encoding="utf-8")
            after = transform(path)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"SKIP {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
            continue
        if after is None or after == before:
            continue
        if not DRY:
            path.write_text(after, encoding="utf-8")
        repo = repo_root(path)
        if repo:
            changed.setdefault(repo, []).append(path)
        print(f"{path.relative_to(ROOT)}")

    if not DRY:
        for repo, paths in changed.items():
            try:
                err = commit_repo(repo, paths)
                if err:
                    print(f"PUSH FAIL {repo.name}: {err[:180]}", file=sys.stderr)
                else:
                    print(f"PUSHED {repo.name} ({len(paths)} files)")
            except subprocess.CalledProcessError as exc:
                print(f"COMMIT FAIL {repo.name}: {exc}", file=sys.stderr)

    print(f"\n=== SUMMARY ===")
    print(f"Scanned: {scanned}")
    print(f"Files changed: {sum(len(v) for v in changed.values())}")
    print(f"Repos: {len(changed)}")
    if DRY:
        print("(dry run)")


if __name__ == "__main__":
    main()
