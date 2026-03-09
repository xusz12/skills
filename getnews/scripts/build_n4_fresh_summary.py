#!/usr/bin/env python3
"""Build n4 fresh-summary markdown for getnews branch1/branch2 workflows."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT_SECTION_RE = re.compile(
    r"^##\s+daily_news_(?:summary|delta|freshSummary)\s*\(\d{4}-\d{2}-\d{2}\)\s*$"
)
LEGACY_GROUP_RE = re.compile(r"^##\s+(.+?)\s*$")
GROUP_RE = re.compile(r"^###\s+(?!\*\*)(.+?)(?:（\d+）)?\s*$")
TITLE_RE = re.compile(r"^###\s+\*\*(.+?)\*\*\s*$")
TIME_RE = re.compile(r"^-\s*发布时间：\s*(.*)\s*$")
LINK_RE = re.compile(r"^-\s*链接：\(([^)]+)\)\s*$")
DEFAULT_GROUP = "未分组"


def parse_args() -> argparse.Namespace:
    today = dt.date.today().isoformat()
    parser = argparse.ArgumentParser(
        description="Compute n4 fresh summary for getnews branch1/branch2 workflows."
    )
    parser.add_argument("--dir", default=".", help="Directory containing news markdown files")
    parser.add_argument("--date", default=today, help="Target date in YYYY-MM-DD")
    parser.add_argument(
        "--mode",
        choices=["branch1", "branch2"],
        default="branch1",
        help="branch1: n4=n3; branch2: n4=old n4 + new n3",
    )
    parser.add_argument(
        "--new",
        default=None,
        help="Path to current n3 file (default: <date>_news_delta.md in --dir)",
    )
    parser.add_argument(
        "--old",
        default=None,
        help="Path to existing n4 file for branch2 (default: <date>_news_freshSummary.md in --dir)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output filename (default: <date>_news_freshSummary.md)",
    )
    return parser.parse_args()


def _finalize_current(entries: list[dict[str, str]], current: dict[str, str] | None) -> None:
    if current and current.get("title") and current.get("url"):
        if not current.get("time"):
            current["time"] = "页面未显示"
        entries.append(current)


def parse_entries(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    current_group = DEFAULT_GROUP

    with path.open("r", encoding="utf-8") as fp:
        for raw_line in fp:
            line = raw_line.rstrip("\n")

            if ROOT_SECTION_RE.match(line):
                _finalize_current(entries, current)
                current = None
                continue

            m_title = TITLE_RE.match(line)
            if m_title:
                _finalize_current(entries, current)
                current = {
                    "group": current_group,
                    "title": m_title.group(1).strip(),
                    "time": "",
                    "url": "",
                }
                continue

            m_group = GROUP_RE.match(line)
            if m_group:
                _finalize_current(entries, current)
                current = None
                current_group = m_group.group(1).strip() or DEFAULT_GROUP
                continue

            m_legacy_group = LEGACY_GROUP_RE.match(line)
            if m_legacy_group:
                _finalize_current(entries, current)
                current = None
                current_group = m_legacy_group.group(1).strip() or DEFAULT_GROUP
                continue

            if current is None:
                continue

            m_time = TIME_RE.match(line)
            if m_time and not current.get("time"):
                current["time"] = m_time.group(1).strip() or "页面未显示"
                continue

            m_link = LINK_RE.match(line)
            if m_link and not current.get("url"):
                current["url"] = m_link.group(1).strip()
                continue

    _finalize_current(entries, current)
    return entries


def combine_entries(
    old_entries: list[dict[str, str]],
    new_entries: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str], dict[str, list[dict[str, str]]]]:
    combined_entries: list[dict[str, str]] = []
    group_order: list[str] = []
    grouped_entries: dict[str, list[dict[str, str]]] = {}

    for item in [*old_entries, *new_entries]:
        group = (item.get("group") or DEFAULT_GROUP).strip() or DEFAULT_GROUP
        normalized = {
            "group": group,
            "title": item.get("title", "").strip(),
            "time": (item.get("time") or "页面未显示").strip() or "页面未显示",
            "url": item.get("url", "").strip(),
        }
        if not normalized["title"] or not normalized["url"]:
            continue

        combined_entries.append(normalized)
        if group not in grouped_entries:
            grouped_entries[group] = []
            group_order.append(group)
        grouped_entries[group].append(normalized)

    return combined_entries, group_order, grouped_entries


def render_markdown(
    target_date: str,
    header_lines: list[str],
    combined_entries: list[dict[str, str]],
    group_order: list[str],
    grouped_entries: dict[str, list[dict[str, str]]],
) -> str:
    now_local = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    group_stats = "，".join(
        f"{group} {len(grouped_entries[group])} 条" for group in group_order
    ) or "无"

    lines = [
        f"# Daily News Fresh Summary - {target_date}",
        *header_lines,
        f"- 条目总数：{len(combined_entries)}",
        f"- 分组统计：{group_stats}",
        f"- 生成时间：{now_local}",
        "",
        f"## daily_news_freshSummary ({target_date})",
        "",
    ]

    if not group_order:
        lines.extend(["- 无条目", ""])
        return "\n".join(lines).rstrip() + "\n"

    for group in group_order:
        items = grouped_entries[group]
        lines.append(f"### {group}（{len(items)}）")
        for item in items:
            lines.extend(
                [
                    f"### **{item['title']}**",
                    f"- 发布时间：{item['time']}",
                    f"- 链接：({item['url']})",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    base_dir = Path(args.dir).resolve()
    target_date = args.date

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", target_date):
        print(f"ERROR: invalid --date format: {target_date}", file=sys.stderr)
        return 2

    if not base_dir.exists() or not base_dir.is_dir():
        print(f"ERROR: directory not found: {base_dir}", file=sys.stderr)
        return 2

    output_name = args.output or f"{target_date}_news_freshSummary.md"
    output_path = base_dir / output_name

    new_path = Path(args.new).resolve() if args.new else base_dir / f"{target_date}_news_delta.md"
    if not new_path.exists() or not new_path.is_file():
        print(f"ERROR: n3 file not found: {new_path}", file=sys.stderr)
        return 2

    try:
        new_entries = parse_entries(new_path)
    except OSError as exc:
        print(f"ERROR: failed to read n3 file {new_path}: {exc}", file=sys.stderr)
        return 1

    old_entries: list[dict[str, str]] = []
    old_name = "无"
    if args.mode == "branch2":
        old_path = Path(args.old).resolve() if args.old else base_dir / f"{target_date}_news_freshSummary.md"
        if not old_path.exists() or not old_path.is_file():
            print(f"ERROR: existing n4 file not found: {old_path}", file=sys.stderr)
            return 2
        try:
            old_entries = parse_entries(old_path)
        except OSError as exc:
            print(f"ERROR: failed to read n4 file {old_path}: {exc}", file=sys.stderr)
            return 1
        old_name = old_path.name

    combined_entries, group_order, grouped_entries = combine_entries(old_entries, new_entries)

    if args.mode == "branch1":
        header_lines = [
            "- 模式：branch1",
            f"- 当前n3：{new_path.name}",
            "- 计算规则：n4 = n3",
        ]
    else:
        header_lines = [
            "- 模式：branch2",
            f"- 旧n4：{old_name}",
            f"- 新增n3：{new_path.name}",
            "- 计算规则：n4 = old n4 + new n3",
            f"- 旧n4条目数：{len(old_entries)}",
            f"- 新增n3条目数：{len(new_entries)}",
        ]

    markdown = render_markdown(
        target_date=target_date,
        header_lines=header_lines,
        combined_entries=combined_entries,
        group_order=group_order,
        grouped_entries=grouped_entries,
    )

    try:
        output_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: failed to write {output_path}: {exc}", file=sys.stderr)
        return 1

    print(f"Fresh summary generated: {output_path}")
    if args.mode == "branch1":
        print(f"n3 entries: {len(new_entries)} | n4 entries: {len(combined_entries)}")
    else:
        print(
            f"old n4 entries: {len(old_entries)} | "
            f"new n3 entries: {len(new_entries)} | "
            f"n4 entries: {len(combined_entries)}"
        )
    if group_order:
        print("Groups: " + " | ".join(f"{g}: {len(grouped_entries[g])}" for g in group_order))
    else:
        print("Groups: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
