"""Sort existing '## 최근 작업' sections so newest entries appear first (by date).

Usage:
    uv run python scripts/reverse_recent_work.py <projects_dir> [--dry-run]
"""
import argparse
import re
import sys
from pathlib import Path


HEADING = "## 최근 작업"
DATE_RE = re.compile(r"\[\[(\d{4}-\d{2}-\d{2})")


def reverse_section(content: str) -> tuple[str, bool]:
    if HEADING not in content:
        return content, False
    lines = content.split("\n")
    heading_idx = -1
    section_end = len(lines)
    for i, line in enumerate(lines):
        if heading_idx == -1:
            if line.strip() == HEADING:
                heading_idx = i
            continue
        if line.startswith("## "):
            section_end = i
            break
    if heading_idx == -1:
        return content, False

    body = lines[heading_idx + 1 : section_end]
    # Trim trailing blank lines inside section, preserve one at the end
    trailing_blanks = 0
    while body and body[-1].strip() == "":
        body.pop()
        trailing_blanks += 1

    # Group each bullet with its continuation lines (indented)
    groups: list[list[str]] = []
    current: list[str] = []
    for line in body:
        if line.startswith("- "):
            if current:
                groups.append(current)
            current = [line]
        else:
            if current:
                current.append(line)
            else:
                # Stray pre-bullet content — keep as its own group to preserve
                current = [line]
    if current:
        groups.append(current)

    if len(groups) <= 1:
        return content, False

    def group_date(g: list[str]) -> str:
        m = DATE_RE.search(g[0])
        return m.group(1) if m else ""

    sorted_groups = sorted(groups, key=group_date, reverse=True)
    if sorted_groups == groups:
        return content, False
    groups = sorted_groups
    new_body: list[str] = []
    for g in groups:
        new_body.extend(g)
    new_body.extend([""] * trailing_blanks)

    new_lines = lines[: heading_idx + 1] + new_body + lines[section_end:]
    return "\n".join(new_lines), True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("projects_dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.projects_dir.is_dir():
        print(f"not a directory: {args.projects_dir}", file=sys.stderr)
        return 1

    changed = 0
    for md in sorted(args.projects_dir.glob("*.md")):
        original = md.read_text()
        new_content, did = reverse_section(original)
        if not did:
            continue
        changed += 1
        print(f"{'[dry] ' if args.dry_run else ''}reversed: {md.name}")
        if not args.dry_run:
            md.write_text(new_content)

    print(f"\n{changed} file(s) {'would be ' if args.dry_run else ''}updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
