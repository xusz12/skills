#!/usr/bin/env python3
"""Merge same-day news markdown files, deduplicate by URL, and classify by topic."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-\d{2}-\d{2}_news\.md$")
TITLE_RE = re.compile(r"^###\s+\*\*(.+?)\*\*\s*$")
TIME_RE = re.compile(r"^-\s*发布时间：\s*(.*)\s*$")
LINK_RE = re.compile(r"^-\s*链接：\(([^)]+)\)\s*$")

CATEGORY_ORDER = ["politics", "economy", "technology", "other"]
CATEGORY_LABELS = {
    "politics": "政治",
    "economy": "经济",
    "technology": "科技",
    "other": "其他",
}
CATEGORY_KEYWORDS = {
    "politics": (
        "politic",
        "government",
        "election",
        "parliament",
        "congress",
        "senate",
        "minister",
        "diplom",
        "military",
        "defense",
        "sanction",
        "ceasefire",
        "president",
        "prime minister",
        "白宫",
        "政治",
        "政府",
        "选举",
        "国会",
        "议会",
        "总统",
        "总理",
        "外交",
        "军事",
        "国防",
        "制裁",
        "战争",
    ),
    "economy": (
        "econom",
        "inflation",
        "gdp",
        "cpi",
        "unemployment",
        "jobs",
        "labor",
        "labour",
        "central bank",
        "interest rate",
        "fed",
        "ecb",
        "treasury",
        "bond",
        "budget",
        "deficit",
        "tariff",
        "trade",
        "market",
        "stocks",
        "shares",
        "earnings",
        "revenue",
        "profit",
        "ipo",
        "bankruptcy",
        "经济",
        "通胀",
        "失业",
        "就业",
        "央行",
        "利率",
        "债券",
        "财政",
        "预算",
        "赤字",
        "贸易",
        "关税",
        "股市",
        "股票",
        "财报",
        "营收",
        "利润",
        "并购",
        "破产",
    ),
    "technology": (
        "technology",
        "tech",
        "artificial intelligence",
        "chip",
        "semiconductor",
        "software",
        "hardware",
        "cloud",
        "cyber",
        "startup",
        "smartphone",
        "iphone",
        "android",
        "robot",
        "quantum",
        "data center",
        "algorithm",
        "openai",
        "科技",
        "人工智能",
        "芯片",
        "半导体",
        "软件",
        "硬件",
        "云计算",
        "网络安全",
        "初创",
        "手机",
        "机器人",
        "量子",
        "数据中心",
        "算法",
    ),
}


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

    with path.open("r", encoding="utf-8") as fp:
        for raw_line in fp:
            line = raw_line.rstrip("\n")

            m_title = TITLE_RE.match(line)
            if m_title:
                if current and current.get("title") and current.get("url"):
                    if not current.get("time"):
                        current["time"] = "页面未显示"
                    entries.append(current)
                current = {"title": m_title.group(1).strip(), "time": "", "url": ""}
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


def classify_entry(item: dict[str, str]) -> str:
    title = item.get("title", "")
    url = item.get("url", "")
    text = f"{title} {url}".lower()
    parsed = urlparse(url)
    path = parsed.path.lower()
    host = parsed.netloc.lower()

    scores = {
        category: sum(1 for keyword in keywords if keyword in text)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }

    if "/technology" in path or "/tech" in path or "techcrunch.com" in host or "arstechnica.com" in host:
        scores["technology"] += 2
    if "/business" in path or "/markets" in path or "/finance" in path or "/economy" in path:
        scores["economy"] += 2
    if "/politics" in path or "/government" in path:
        scores["politics"] += 1

    best_category = max(CATEGORY_ORDER[:-1], key=lambda category: scores[category])
    if scores[best_category] == 0:
        return "other"
    return best_category


def render_markdown(
    target_date: str,
    source_files: list[str],
    scanned_files: int,
    pre_dedup_count: int,
    dropped_count: int,
    deduped_entries: list[dict[str, str]],
    categorized_entries: dict[str, list[dict[str, str]]],
) -> str:
    now_local = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    category_stats = "，".join(
        f"{CATEGORY_LABELS[category]} {len(categorized_entries[category])} 条"
        for category in CATEGORY_ORDER
    )
    lines = [
        f"# Daily News Summary - {target_date}",
        f"- 被汇总文件：{', '.join(source_files)}",
        f"- 去重前条目总数：{pre_dedup_count}",
        f"- 被去重条目数：{dropped_count}",
        f"- 去重后条目总数：{len(deduped_entries)}",
        f"- 分类统计：{category_stats}",
        f"- 生成时间：{now_local}",
        f"- 扫描文件数：{scanned_files}",
        "",
        f"## daily_news_summary ({target_date})",
        "",
    ]

    for category in CATEGORY_ORDER:
        category_label = CATEGORY_LABELS[category]
        items = categorized_entries[category]
        lines.append(f"### {category_label}（{len(items)}）")
        if not items:
            lines.extend(["- 无条目", ""])
            continue

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
    categorized_entries: dict[str, list[dict[str, str]]] = {
        category: [] for category in CATEGORY_ORDER
    }
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
            item["category"] = classify_entry(item)
            deduped.append(item)
            categorized_entries[item["category"]].append(item)

    dropped_total = parsed_total - len(deduped)
    markdown = render_markdown(
        target_date,
        [path.name for path in files],
        len(files),
        parsed_total,
        dropped_total,
        deduped,
        categorized_entries,
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
    print(
        "Categories: "
        + " | ".join(
            f"{CATEGORY_LABELS[category]}: {len(categorized_entries[category])}"
            for category in CATEGORY_ORDER
        )
    )
    if warnings:
        for warning in warnings:
            print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
