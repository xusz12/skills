#!/usr/bin/env python3
"""Build n3 delta markdown for getnews branch1/branch2 workflows."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

SUMMARY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_news_summary\.md$")
N1_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-\d{2}-\d{2}_news\.md$")
ROOT_SECTION_RE = re.compile(r"^##\s+daily_news_summary\s*\(\d{4}-\d{2}-\d{2}\)\s*$")
LEGACY_GROUP_RE = re.compile(r"^##\s+(.+?)\s*$")
GROUP_RE = re.compile(r"^###\s+(?!\*\*)(.+?)(?:（\d+）)?\s*$")
TITLE_RE = re.compile(r"^###\s+\*\*(.+?)\*\*\s*$")
TIME_RE = re.compile(r"^-\s*发布时间：\s*(.*)\s*$")
LINK_RE = re.compile(r"^-\s*链接：\(([^)]+)\)\s*$")
DEFAULT_GROUP = "未分组"


def parse_args() -> argparse.Namespace:
    today = dt.date.today().isoformat()
    parser = argparse.ArgumentParser(
        description="Compute n3 delta for getnews branch1/branch2 by exact URL."
    )
    parser.add_argument("--dir", default=".", help="Directory containing summary files")
    parser.add_argument("--date", default=today, help="Target date in YYYY-MM-DD")
    parser.add_argument(
        "--mode",
        choices=["branch1", "branch2"],
        default="branch1",
        help="branch1: n2 minus oldDay-n2; branch2: latest n1 minus current n2",
    )
    parser.add_argument(
        "--new",
        default=None,
        help=(
            "Path to current input file. "
            "branch1 default: <date>_news_summary.md; "
            "branch2 default: latest same-day n1 file in --dir"
        ),
    )
    parser.add_argument(
        "--old",
        default=None,
        help="Path to oldDay-n2 file for branch1 (default: auto-pick nearest previous date)",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Path to current n2 file for branch2 (default: <date>_news_summary.md in --dir)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output filename (default: <date>_news_delta.md)",
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


def discover_old_summary(base_dir: Path, target_date: str, exclude_name: str) -> Path | None:
    candidates: list[tuple[str, Path]] = []
    for path in sorted(base_dir.glob("*_news_summary.md"), key=lambda p: p.name):
        if not path.is_file():
            continue
        if path.name == exclude_name:
            continue
        match = SUMMARY_RE.match(path.name)
        if not match:
            continue
        file_date = match.group(1)
        if file_date < target_date:
            candidates.append((file_date, path))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def discover_latest_n1(base_dir: Path, target_date: str) -> Path | None:
    candidates: list[Path] = []
    for path in sorted(base_dir.glob("*_news.md"), key=lambda p: p.name):
        if not path.is_file():
            continue
        match = N1_RE.match(path.name)
        if not match:
            continue
        if match.group(1) != target_date:
            continue
        candidates.append(path)

    if not candidates:
        return None
    return candidates[-1]


def build_delta_entries(
    new_entries: list[dict[str, str]],
    baseline_urls: set[str],
) -> tuple[list[dict[str, str]], list[str], dict[str, list[dict[str, str]]]]:
    delta_entries: list[dict[str, str]] = []
    group_order: list[str] = []
    grouped_entries: dict[str, list[dict[str, str]]] = {}
    seen_delta_urls: set[str] = set()

    for item in new_entries:
        url = item.get("url", "")
        if not url:
            continue
        if url in baseline_urls:
            continue
        if url in seen_delta_urls:
            continue
        seen_delta_urls.add(url)

        group = (item.get("group") or DEFAULT_GROUP).strip() or DEFAULT_GROUP
        normalized = {
            "group": group,
            "title": item.get("title", "").strip(),
            "time": (item.get("time") or "页面未显示").strip() or "页面未显示",
            "url": url,
        }
        delta_entries.append(normalized)

        if group not in grouped_entries:
            grouped_entries[group] = []
            group_order.append(group)
        grouped_entries[group].append(normalized)

    return delta_entries, group_order, grouped_entries


def render_markdown(
    target_date: str,
    header_lines: list[str],
    delta_entries: list[dict[str, str]],
    group_order: list[str],
    grouped_entries: dict[str, list[dict[str, str]]],
) -> str:
    now_local = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    group_stats = "，".join(
        f"{group} {len(grouped_entries[group])} 条" for group in group_order
    ) or "无"

    lines = [f"# Daily News Delta - {target_date}", *header_lines, f"- 分组统计：{group_stats}", f"- 生成时间：{now_local}", "", f"## daily_news_delta ({target_date})", ""]

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

    output_name = args.output or f"{target_date}_news_delta.md"
    output_path = base_dir / output_name

    if args.mode == "branch1":
        new_path = Path(args.new).resolve() if args.new else base_dir / f"{target_date}_news_summary.md"
        if not new_path.exists() or not new_path.is_file():
            print(f"ERROR: n2 file not found: {new_path}", file=sys.stderr)
            return 2

        old_path: Path | None
        if args.old:
            old_path = Path(args.old).resolve()
            if not old_path.exists() or not old_path.is_file():
                print(f"ERROR: oldDay-n2 file not found: {old_path}", file=sys.stderr)
                return 2
        else:
            old_path = discover_old_summary(base_dir, target_date, new_path.name)

        try:
            new_entries = parse_entries(new_path)
        except OSError as exc:
            print(f"ERROR: failed to read n2 file {new_path}: {exc}", file=sys.stderr)
            return 1

        old_entries: list[dict[str, str]] = []
        old_name = "无（按空集合处理）"
        old_date = "N/A"
        if old_path:
            try:
                old_entries = parse_entries(old_path)
            except OSError as exc:
                print(f"ERROR: failed to read oldDay-n2 file {old_path}: {exc}", file=sys.stderr)
                return 1
            old_name = old_path.name
            m_old = SUMMARY_RE.match(old_path.name)
            old_date = m_old.group(1) if m_old else "未知"

        old_urls = {item["url"] for item in old_entries if item.get("url")}
        delta_entries, group_order, grouped_entries = build_delta_entries(new_entries, old_urls)
        dropped = len(new_entries) - len(delta_entries)
        header_lines = [
            f"- 模式：branch1",
            f"- 当前n2：{new_path.name}",
            f"- 对比oldDay-n2：{old_name}",
            f"- oldDay日期：{old_date}",
            f"- 差集前条目总数：{len(new_entries)}",
            f"- 被过滤条目数：{dropped}",
            f"- 差集后条目总数：{len(delta_entries)}",
        ]
        markdown = render_markdown(
            target_date=target_date,
            header_lines=header_lines,
            delta_entries=delta_entries,
            group_order=group_order,
            grouped_entries=grouped_entries,
        )
    else:
        new_path = Path(args.new).resolve() if args.new else discover_latest_n1(base_dir, target_date)
        if new_path is None or not new_path.exists() or not new_path.is_file():
            print(f"ERROR: latest same-day n1 file not found for {target_date} in {base_dir}", file=sys.stderr)
            return 2

        baseline_path = Path(args.baseline).resolve() if args.baseline else base_dir / f"{target_date}_news_summary.md"
        if not baseline_path.exists() or not baseline_path.is_file():
            print(f"ERROR: current n2 file not found: {baseline_path}", file=sys.stderr)
            return 2

        try:
            new_entries = parse_entries(new_path)
        except OSError as exc:
            print(f"ERROR: failed to read n1 file {new_path}: {exc}", file=sys.stderr)
            return 1

        try:
            baseline_entries = parse_entries(baseline_path)
        except OSError as exc:
            print(f"ERROR: failed to read n2 file {baseline_path}: {exc}", file=sys.stderr)
            return 1

        baseline_urls = {item["url"] for item in baseline_entries if item.get("url")}
        delta_entries, group_order, grouped_entries = build_delta_entries(new_entries, baseline_urls)
        dropped = len(new_entries) - len(delta_entries)
        header_lines = [
            f"- 模式：branch2",
            f"- 当前n1：{new_path.name}",
            f"- 对比n2：{baseline_path.name}",
            f"- 差集前条目总数：{len(new_entries)}",
            f"- 被过滤条目数：{dropped}",
            f"- 差集后条目总数：{len(delta_entries)}",
        ]
        markdown = render_markdown(
            target_date=target_date,
            header_lines=header_lines,
            delta_entries=delta_entries,
            group_order=group_order,
            grouped_entries=grouped_entries,
        )

    try:
        output_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: failed to write {output_path}: {exc}", file=sys.stderr)
        return 1

    print(f"Delta generated: {output_path}")
    if args.mode == "branch1":
        print(
            "n2 entries: "
            f"{len(new_entries)} | Filtered by oldDay: {dropped} | "
            f"n3 entries: {len(delta_entries)}"
        )
        print(f"oldDay-n2: {old_name}")
    else:
        print(
            "n1 entries: "
            f"{len(new_entries)} | Filtered by current n2: {dropped} | "
            f"n3 entries: {len(delta_entries)}"
        )
        print(f"current n2: {baseline_path.name}")
    if group_order:
        print(
            "Groups: "
            + " | ".join(f"{g}: {len(grouped_entries[g])}" for g in group_order)
        )
    else:
        print("Groups: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
