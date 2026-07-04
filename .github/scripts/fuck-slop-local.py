#!/usr/bin/env python3
"""Deep slop pass: em dashes, negative parallelism, puffery in md/mdx. Skips CoC/CHANGELOG/.cursor."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path.home() / "dev/personal"
DRY = "--dry-run" in sys.argv
COMMIT_MSG = "Remove remaining AI slop (fuck-slop pass)"

SCRIPT = Path(__file__).resolve().parent / "deslop-repos.py"
spec = importlib.util.spec_from_file_location("deslop_repos", SCRIPT)
deslop_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(deslop_mod)

deslop = deslop_mod.deslop
should_skip = deslop_mod.should_skip

SKIP_FILES = {
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",  # often upstream covenant forks
}

SKIP_DIR_PARTS = {".cursor", "node_modules", ".venv", "vendor", "dist", "build", ".next"}
SKIP_PATH_SUBSTR = (
    "curriculum-guides/",
    "research/opportunities/",
    ".github/cursor-templates/",
)

NEG_PARALLEL = [
    (
        re.compile(
            r"The biggest user friction isn't the math \(our calculators handle that\): it's",
            re.I,
        ),
        "Users already have the math; the hard part is",
    ),
    (
        re.compile(r"isn't the math[^:]{0,40}: it's", re.I),
        "is finding",
    ),
    (
        re.compile(r"not because [^.;]{2,80}but because", re.I),
        "because",
    ),
]


def em_dash_only(text: str) -> str:
    """Replace em dash separators only; keep en-dashes in K–12, 2023–2024, etc."""
    return re.sub(r"\s—\s", ": ", text)


def fuck_slop(text: str) -> str:
    out = deslop(text)
    out = em_dash_only(out)
    for pat, repl in NEG_PARALLEL:
        out = pat.sub(repl, out)
    out = re.sub(r":\s*:", ": ", out)
    out = re.sub(r"  +", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".mdx"}:
            continue
        if any(p in path.parts for p in SKIP_DIR_PARTS):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if should_skip(rel) or rel in SKIP_FILES or path.name in SKIP_FILES:
            continue
        if any(s in rel for s in SKIP_PATH_SUBSTR):
            continue
        if rel.startswith("room-tba-"):
            continue
        files.append(path)
    return files


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
    for path in iter_files():
        try:
            before = path.read_text(encoding="utf-8")
        except OSError:
            continue
        scanned += 1
        after = fuck_slop(before)
        if after == before:
            continue
        if not DRY:
            path.write_text(after, encoding="utf-8")
        repo = repo_root(path)
        if repo:
            changed.setdefault(repo, []).append(path)
        print(f"{path.relative_to(ROOT)} ({len(before)}→{len(after)} bytes)")

    if not DRY:
        for repo, paths in changed.items():
            try:
                err = commit_repo(repo, paths)
                if err:
                    print(f"PUSH FAIL {repo.name}: {err[:200]}", file=sys.stderr)
                else:
                    print(f"PUSHED {repo.name} ({len(paths)} files)")
            except subprocess.CalledProcessError as exc:
                print(f"COMMIT FAIL {repo.name}: {exc}", file=sys.stderr)

    print(f"\n=== SUMMARY ===")
    print(f"Scanned: {scanned}")
    print(f"Files changed: {sum(len(v) for v in changed.values())}")
    print(f"Repos touched: {len(changed)}")
    if DRY:
        print("(dry run)")


if __name__ == "__main__":
    main()
