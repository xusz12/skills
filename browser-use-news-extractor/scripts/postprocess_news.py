#!/usr/bin/env python3
"""Validate translated news rows and export final JSON + Markdown.

Input rows are expected to include Chinese titles in `title` (or `title_zh` as fallback).
The script writes:
- YYYY-MM-DD-HH-MM_<site>_news.json
- YYYY-MM-DD-HH-MM_<site>_news.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_TIME_TEXT = "页面未显示"
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$")


def clean_text(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def is_absolute_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_items(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    else:
        raise ValueError("expected JSON array or object with 'items' array")

    output: list[dict] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"item {idx} is not an object")
        output.append(dict(item))
    return output


def normalize_items(items: list[dict]) -> tuple[list[dict], list[str]]:
    normalized: list[dict] = []
    warnings: list[str] = []
    seen_urls: set[str] = set()

    for idx, item in enumerate(items, start=1):
        site = clean_text(item.get("site"))
        title = clean_text(item.get("title") or item.get("title_zh"))
        time_text = clean_text(item.get("time_text") or item.get("time"), DEFAULT_TIME_TEXT) or DEFAULT_TIME_TEXT
        datetime_iso = clean_text(item.get("datetime_iso") or item.get("datetime"))
        url = clean_text(item.get("url"))

        if not site:
            warnings.append(f"item {idx}: missing site")
            continue
        if not title:
            warnings.append(f"item {idx}: missing translated title")
            continue
        if not is_absolute_http_url(url):
            warnings.append(f"item {idx}: invalid absolute url")
            continue
        if url in seen_urls:
            warnings.append(f"item {idx}: duplicate url skipped")
            continue

        seen_urls.add(url)
        normalized.append(
            {
                "site": site,
                "title": title,
                "time_text": time_text,
                "datetime_iso": datetime_iso,
                "url": url,
            }
        )

    return normalized, warnings


def infer_site_key(items: list[dict]) -> str:
    sites = sorted({item["site"] for item in items})
    if not sites:
        return "unknown"
    if len(sites) == 1:
        key = sites[0]
    else:
        key = "multi"

    key = re.sub(r"[^a-zA-Z0-9]+", "_", key).strip("_").lower()
    return key or "unknown"


def iso_to_local_display(datetime_iso: str) -> str | None:
    raw = clean_text(datetime_iso)
    if not raw:
        return None

    try:
        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        parsed = dt.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None


def render_markdown(items: list[dict]) -> str:
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []

    for item in items:
        site = item["site"]
        if site not in grouped:
            grouped[site] = []
            order.append(site)
        grouped[site].append(item)

    lines: list[str] = []
    for site in order:
        lines.append(f"## {site}")
        for item in grouped[site]:
            local_time = iso_to_local_display(item["datetime_iso"])
            display_time = local_time or item["time_text"] or DEFAULT_TIME_TEXT
            lines.append(f"### **{item['title']}**")
            lines.append(f"- 发布时间：{display_time}")
            lines.append(f"- 链接：({item['url']})")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate translated rows and export JSON+Markdown.")
    parser.add_argument("--input", required=True, help="Translated JSON input path")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument("--timestamp", default=None, help="Filename timestamp YYYY-MM-DD-HH-MM")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    try:
        items = load_items(input_path)
        normalized, warnings = normalize_items(items)
        if not normalized:
            print("ERROR: no valid translated items", file=sys.stderr)
            for warning in warnings:
                print(f"WARN: {warning}", file=sys.stderr)
            return 2

        ts = args.timestamp or dt.datetime.now().strftime("%Y-%m-%d-%H-%M")
        if not TS_RE.match(ts):
            raise ValueError("timestamp must be YYYY-MM-DD-HH-MM")

        site_key = infer_site_key(normalized)
        base_name = f"{ts}_{site_key}_news"

        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{base_name}.json"
        md_path = output_dir / f"{base_name}.md"

        json_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md_path.write_text(render_markdown(normalized), encoding="utf-8")

        print(f"Final JSON: {json_path}")
        print(f"Final Markdown: {md_path}")
        print(f"Items exported: {len(normalized)}")

        if len(normalized) < 10:
            print(f"WARN: fewer than 10 items ({len(normalized)})", file=sys.stderr)
        if warnings:
            print(f"WARNINGS: {len(warnings)}", file=sys.stderr)
            for warning in warnings:
                print(f"WARN: {warning}", file=sys.stderr)

        return 0

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
