#!/usr/bin/env python3
"""Weekly merged-PR digest + Dependabot risk lines. No external APIs — gh + semver heuristics."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


OWNER = "smmariquit"
SEARCH_LIMIT = 100

# Packages where even minor bumps deserve a second look
WATCH_PACKAGES = {
    "next",
    "react",
    "react-dom",
    "astro",
    "vite",
    "@astrojs/",
    "eslint",
    "typescript",
    "tailwindcss",
    "@tailwindcss/",
    "prisma",
    "@prisma/",
    "supabase",
    "@supabase/",
    "svelte",
    "@sveltejs/",
}

BUMP_RE = re.compile(
    r"(?:bump|update)\s+(?:the\s+)?(?P<name>[^\s]+)\s+from\s+(?P<old>v?\d[\w.\-+]*)\s+to\s+(?P<new>v?\d[\w.\-+]*)",
    re.IGNORECASE,
)
SIMPLE_BUMP_RE = re.compile(
    r"bump\s+(?P<name>[^\s]+)\s+from\s+(?P<old>v?\d[\w.\-+]*)\s+to\s+(?P<new>v?\d[\w.\-+]*)",
    re.IGNORECASE,
)


@dataclass
class Pull:
    repo: str
    number: int
    title: str
    url: str
    author: str
    closed_at: str | None


def run_gh(args: list[str]) -> str:
    result = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def search_prs(query: list[str]) -> list[Pull]:
    raw = run_gh(
        [
            "search",
            "prs",
            *query,
            "--owner",
            OWNER,
            "--limit",
            str(SEARCH_LIMIT),
            "--json",
            "number,title,repository,url,closedAt,author",
        ]
    )
    items = json.loads(raw or "[]")
    pulls: list[Pull] = []
    for item in items:
        pulls.append(
            Pull(
                repo=item["repository"]["nameWithOwner"],
                number=item["number"],
                title=item["title"],
                url=item["url"],
                author=item["author"]["login"],
                closed_at=item.get("closedAt"),
            )
        )
    return pulls


def week_window() -> tuple[str, str, str]:
    now = datetime.now(UTC)
    start = now - timedelta(days=7)
    # gh date format: YYYY-MM-DD
    start_s = start.strftime("%Y-%m-%d")
    end_s = now.strftime("%Y-%m-%d")
    label = f"{start_s} → {end_s}"
    return start_s, end_s, label


def parse_versions(title: str) -> tuple[str, str, str] | None:
    for pattern in (BUMP_RE, SIMPLE_BUMP_RE):
        match = pattern.search(title)
        if match:
            return match.group("name"), match.group("old"), match.group("new")
    return None


def strip_v(version: str) -> str:
    return version.lstrip("vV")


def semver_parts(version: str) -> tuple[int, ...]:
    core = strip_v(version).split("-")[0]
    parts: list[int] = []
    for piece in core.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if digits:
            parts.append(int(digits))
        else:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def bump_kind(old: str, new: str) -> str:
    o = semver_parts(old)
    n = semver_parts(new)
    if n[0] > o[0]:
        return "major"
    if n[1] > o[1]:
        return "minor"
    if n[2] > o[2]:
        return "patch"
    return "same"


def is_watch(name: str) -> bool:
    lower = name.lower()
    return any(lower == pkg or lower.startswith(pkg) for pkg in WATCH_PACKAGES)


def risk_line(title: str) -> str:
    parsed = parse_versions(title)
    if not parsed:
      if "group" in title.lower():
          return "medium — dependency group bump; skim the lockfile diff"
      return "unknown — could not parse versions from title"

  name, old, new = parsed
  kind = bump_kind(old, new)
  watch = is_watch(name)

  if kind == "major":
      return f"high — major {name} ({old} → {new}); run build/tests before merge"
  if kind == "minor":
      if watch:
          return f"medium — minor {name} ({old} → {new}); framework-adjacent, smoke-test"
      return f"low — minor {name} ({old} → {new})"
  if kind == "patch":
      if watch and name.lower().startswith("@types/"):
          return f"low — types patch {name}"
      return f"low — patch {name} ({old} → {new})"
  return f"low — no semver change detected for {name}"


def md_pull(p: Pull) -> str:
    return f"- [{p.title}]({p.url}) (#{p.number}, @{p.author})"


def build_report() -> str:
    start, _end, label = week_window()

    merged = search_prs(["--merged", f"--merged-at=>{start}"])
    open_dependabot = search_prs(["--author=app/dependabot", "--state=open"])

    human_merged = [p for p in merged if p.author != "dependabot[bot]"]
    bot_merged = [p for p in merged if p.author == "dependabot[bot]"]

    lines: list[str] = [
        f"# Weekly PR digest ({label})",
        "",
        "Automated via GitHub Actions. Dependabot risk is **semver heuristics**, not an LLM.",
        "",
        f"- Merged PRs (last 7 days): **{len(merged)}**",
        f"- Your merges: **{len(human_merged)}**",
        f"- Dependabot merges: **{len(bot_merged)}**",
        f"- Open Dependabot PRs: **{len(open_dependabot)}**",
        "",
    ]

    if human_merged:
        lines.append("## Your merged PRs")
        lines.append("")
        by_repo: dict[str, list[Pull]] = {}
        for p in human_merged:
            by_repo.setdefault(p.repo, []).append(p)
        for repo in sorted(by_repo):
            lines.append(f"### `{repo}`")
            for p in by_repo[repo]:
                lines.append(md_pull(p))
            lines.append("")

    if bot_merged:
        lines.append("## Dependabot merged (last 7 days)")
        lines.append("")
        for p in bot_merged:
            lines.append(f"- [{p.title}]({p.url}) — _{risk_line(p.title)}_")
        lines.append("")

    if open_dependabot:
        lines.append("## Open Dependabot PRs (merge queue)")
        lines.append("")
        high: list[Pull] = []
        rest: list[Pull] = []
        for p in open_dependabot:
            if risk_line(p.title).startswith("high"):
                high.append(p)
            else:
                rest.append(p)

        if high:
            lines.append("### Review first")
            for p in high:
                lines.append(f"- [{p.repo}#{p.number}]({p.url}): {p.title}")
                lines.append(f"  - **{risk_line(p.title)}**")
            lines.append("")

        lines.append("### Everything else")
        for p in rest:
            lines.append(f"- [{p.repo}#{p.number}]({p.url}): {p.title}")
            lines.append(f"  - {risk_line(p.title)}")
        lines.append("")

    if not merged and not open_dependabot:
        lines.append("_Nothing to report this week._")

    lines.append("---")
    lines.append("_Generated by [`weekly-pr-digest.yml`](.github/workflows/weekly-pr-digest.yml)._")
    return "\n".join(lines)


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    body = build_report()
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(body)
    else:
        print(body)


if __name__ == "__main__":
    main()
