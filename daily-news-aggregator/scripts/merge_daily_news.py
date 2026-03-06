#!/usr/bin/env python3
"""Merge same-day news markdown files and deduplicate by URL within original groups."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path


FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-\d{2}-\d{2}_news\.md$")
GROUP_RE = re.compile(r"^##\s+(.+?)\s*$")
TITLE_RE = re.compile(r"^###\s+\*\*(.+?)\*\*\s*$")
TIME_RE = re.compile(r"^-\s*发布时间：\s*(.*)\s*$")
LINK_RE = re.compile(r"^-\s*链接：\(([^)]+)\)\s*$")
DEFAULT_GROUP = "未分组"


def parse_args() -> argparse.Namespace:
    today = dt.date.today().isoformat()
    parser = argparse.ArgumentParser(
        description="Aggregate same-day news markdown files and dedupe by exact URL."
    )
    parser.add_argument("--dir", default=".", help="Directory to scan (default: current directory)")
    parser.add_argument("--date", default=today, help="Target date in YYYY-MM-DD")
    parser.add_argument("--pattern", default="*_news.md", help="Glob pattern for candidate files")
    parser.add_argument(
        "--output",
        default=None,
        help="Output filename (default: <date>_news_summary.md)",
    )
    return parser.parse_args()


def discover_files(base_dir: Path, target_date: str, pattern: str, output_name: str) -> list[Path]:
    files: list[Path] = []
    for path in sorted(base_dir.glob(pattern), key=lambda p: p.name):
        if not path.is_file():
            continue
        if path.name == output_name:
            continue
        match = FILENAME_RE.match(path.name)
        if not match:
            continue
        if match.group(1) != target_date:
            continue
        files.append(path)
    return files


def parse_entries(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    current_group = DEFAULT_GROUP

    with path.open("r", encoding="utf-8") as fp:
        for raw_line in fp:
            line = raw_line.rstrip("\n")

            m_group = GROUP_RE.match(line)
            if m_group:
                if current and current.get("title") and current.get("url"):
                    if not current.get("time"):
                        current["time"] = "页面未显示"
                    entries.append(current)
                current = None
                current_group = m_group.group(1).strip() or DEFAULT_GROUP
                continue

            m_title = TITLE_RE.match(line)
            if m_title:
                if current and current.get("title") and current.get("url"):
                    if not current.get("time"):
                        current["time"] = "页面未显示"
                    entries.append(current)
                current = {
                    "group": current_group,
                    "title": m_title.group(1).strip(),
                    "time": "",
                    "url": "",
                }
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

    if current and current.get("title") and current.get("url"):
        if not current.get("time"):
            current["time"] = "页面未显示"
        entries.append(current)

    return entries


def render_markdown(
    target_date: str,
    source_files: list[str],
    scanned_files: int,
    pre_dedup_count: int,
    dropped_count: int,
    deduped_entries: list[dict[str, str]],
    group_order: list[str],
    grouped_entries: dict[str, list[dict[str, str]]],
) -> str:
    now_local = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    group_stats = "，".join(
        f"{group} {len(grouped_entries[group])} 条" for group in group_order
    ) or "无"
    lines = [
        f"# Daily News Summary - {target_date}",
        f"- 被汇总文件：{', '.join(source_files)}",
        f"- 去重前条目总数：{pre_dedup_count}",
        f"- 被去重条目数：{dropped_count}",
        f"- 去重后条目总数：{len(deduped_entries)}",
        f"- 分组统计：{group_stats}",
        f"- 生成时间：{now_local}",
        f"- 扫描文件数：{scanned_files}",
        "",
        f"## daily_news_summary ({target_date})",
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

    output_name = args.output or f"{target_date}_news_summary.md"
    output_path = base_dir / output_name

    if not base_dir.exists() or not base_dir.is_dir():
        print(f"ERROR: directory not found: {base_dir}", file=sys.stderr)
        return 2

    files = discover_files(base_dir, target_date, args.pattern, output_name)
    if not files:
        print(
            f"No input files found for date {target_date} in {base_dir}. "
            "Skipped summary generation."
        )
        return 0

    parsed_total = 0
    deduped: list[dict[str, str]] = []
    group_order: list[str] = []
    grouped_entries: dict[str, list[dict[str, str]]] = {}
    seen_urls: set[str] = set()
    warnings: list[str] = []

    for file_path in files:
        try:
            items = parse_entries(file_path)
        except OSError as exc:
            warnings.append(f"failed to read {file_path.name}: {exc}")
            continue

        parsed_total += len(items)
        for item in items:
            url = item["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            group = item.get("group", DEFAULT_GROUP).strip() or DEFAULT_GROUP
            if group not in grouped_entries:
                grouped_entries[group] = []
                group_order.append(group)
            item["group"] = group
            deduped.append(item)
            grouped_entries[group].append(item)

    dropped_total = parsed_total - len(deduped)
    markdown = render_markdown(
        target_date,
        [path.name for path in files],
        len(files),
        parsed_total,
        dropped_total,
        deduped,
        group_order,
        grouped_entries,
    )

    try:
        output_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: failed to write {output_path}: {exc}", file=sys.stderr)
        return 1

    print(f"Summary generated: {output_path}")
    print(
        "Scanned files: "
        f"{len(files)} | Before dedup: {parsed_total} | "
        f"Dropped: {dropped_total} | After dedup: {len(deduped)}"
    )
    if group_order:
        print(
            "Groups: "
            + " | ".join(
                f"{group}: {len(grouped_entries[group])}" for group in group_order
            )
        )
    else:
        print("Groups: none")
    if warnings:
        for warning in warnings:
            print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
