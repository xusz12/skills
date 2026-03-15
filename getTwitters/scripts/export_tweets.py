#!/usr/bin/env python3
"""Fetch tweets for one or more accounts and export markdown."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KIND_CN = {
    "original": "原创",
    "quote": "引用",
    "retweet": "转推",
}

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
URL_ONLY_RE = re.compile(r"^(https?://\S+\s*)+$")

DEFAULT_ACCOUNTS = [
    "ilyasut",
    "mingchikuo",
    "WaylandZhang",
    "ivanalog_com",
    "jakevin7",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch tweets for accounts via twitter CLI, classify, translate to Chinese, "
            "and export markdown."
        )
    )
    parser.add_argument(
        "--accounts",
        nargs="+",
        default=DEFAULT_ACCOUNTS,
        help="One or more account handles. Default: built-in 5 accounts.",
    )
    parser.add_argument(
        "--date",
        help="Target date in YYYY-MM-DD. Default: today in --timezone.",
    )
    parser.add_argument(
        "--timezone",
        default="Asia/Shanghai",
        help="Timezone for date filtering. Default: Asia/Shanghai.",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=20,
        help="Max tweets fetched per account. Default: 20.",
    )
    parser.add_argument(
        "--output",
        help="Output markdown path. Default: tweets_YYYY-MM-DD.md.",
    )
    parser.add_argument(
        "--raw-dir",
        help="Optional directory to save raw JSON per account.",
    )
    parser.add_argument(
        "--disable-translation",
        action="store_true",
        help="Disable non-Chinese to Chinese translation.",
    )
    parser.set_defaults(author_guard=True)
    parser.add_argument(
        "--author-guard",
        dest="author_guard",
        action="store_true",
        help="Keep only tweets clearly belonging to each target handle (default).",
    )
    parser.add_argument(
        "--no-author-guard",
        dest="author_guard",
        action="store_false",
        help="Disable author guard.",
    )
    return parser.parse_args()


def run_twitter_user_posts(handle: str, limit: int) -> dict:
    cmd = [
        "twitter",
        "user-posts",
        handle,
        "-n",
        str(limit),
        "--full-text",
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"twitter CLI failed for @{handle}: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON for @{handle}: {exc}") from exc


def parse_created_at(item: dict, tz: ZoneInfo) -> datetime | None:
    created_at = item.get("createdAt")
    if created_at:
        try:
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            return dt.astimezone(tz)
        except ValueError:
            pass

    created_local = item.get("createdAtLocal")
    if created_local:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                naive = datetime.strptime(created_local, fmt)
                return naive.replace(tzinfo=tz)
            except ValueError:
                continue
    return None


def detect_kind(item: dict) -> str:
    if item.get("isRetweet"):
        return "retweet"
    if item.get("quotedTweet"):
        return "quote"
    return "original"


def normalize(text: str | None) -> str:
    if not text:
        return ""
    return text.replace("```", "``\\`").strip()


class ChineseTranslator:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._translator = None
        self._cache: dict[str, str] = {}
        self._warned = False

    def _lazy_init(self):
        if self._translator is not None:
            return
        from deep_translator import GoogleTranslator

        self._translator = GoogleTranslator(source="auto", target="zh-CN")

    def translate(self, text: str) -> str:
        if not self.enabled:
            return text

        key = text.strip()
        if not key:
            return text
        if key in self._cache:
            return self._cache[key]

        try:
            self._lazy_init()
            translated = self._translator.translate(key)
        except Exception as exc:  # noqa: BLE001
            if not self._warned:
                print(
                    f"[WARN] Translation failed, fallback to original text: {exc}",
                    file=sys.stderr,
                )
                self._warned = True
            translated = key

        self._cache[key] = translated
        return translated


def should_translate(text: str, lang_hint: str | None = None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if lang_hint and lang_hint.lower().startswith("zh"):
        return False
    if URL_ONLY_RE.fullmatch(stripped):
        return False
    if CJK_RE.search(stripped):
        return False
    return any(ch.isalpha() for ch in stripped)


def maybe_translate_text(
    text: str | None,
    translator: ChineseTranslator,
    lang_hint: str | None = None,
) -> str:
    raw = text or ""
    if should_translate(raw, lang_hint):
        return translator.translate(raw)
    return raw


def keep_for_handle(item: dict, handle: str) -> bool:
    h = handle.lower()
    author = (item.get("author") or {}).get("screenName", "")
    retweeted_by = item.get("retweetedBy") or ""
    if author.lower() == h:
        return True
    if item.get("isRetweet") and retweeted_by.lower() == h:
        return True
    return False


def detect_display_name(data: list[dict], handle: str) -> str:
    h = handle.lower()
    for item in data:
        author = item.get("author") or {}
        if (author.get("screenName") or "").lower() == h:
            name = (author.get("name") or "").strip()
            if name:
                return name
    return handle


def build_markdown(rows_by_handle: dict[str, list[dict]], display_names: dict[str, str]) -> str:
    lines: list[str] = []
    for handle, rows in rows_by_handle.items():
        title = f"{display_names.get(handle, handle)} （@{handle}）"
        lines.append(f"## {title}")
        if not rows:
            lines.append("今日无符合条件的推文。")
            lines.append("")
            continue

        lines.append("")
        for idx, row in enumerate(rows, start=1):
            lines.append(
                f"##### {idx}. [{KIND_CN[row['kind']]}]({row['url']})发布时间（北京时间）：{row['dt'].strftime('%Y-%m-%d %H:%M')}"
            )
            if row["kind"] == "quote":
                lines.append("**引用：**")
                lines.append("```text")
                lines.append(normalize(row["text"]))
                lines.append("```")
                lines.append("**被引用：**")
                lines.append("```text")
                lines.append(normalize(row.get("quoted_text", "")))
                lines.append("```")
            else:
                lines.append("```text")
                lines.append(normalize(row["text"]))
                lines.append("```")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    tz = ZoneInfo(args.timezone)

    if args.date:
        target_date = args.date
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError as exc:
            raise SystemExit(f"Invalid --date: {exc}") from exc
    else:
        target_date = datetime.now(tz).strftime("%Y-%m-%d")

    output = args.output or f"tweets_{target_date}.md"

    raw_dir = Path(args.raw_dir) if args.raw_dir else None
    if raw_dir:
        raw_dir.mkdir(parents=True, exist_ok=True)

    rows_by_handle: dict[str, list[dict]] = {}
    display_names: dict[str, str] = {}
    had_error = False
    translator = ChineseTranslator(enabled=not args.disable_translation)

    for handle in args.accounts:
        try:
            envelope = run_twitter_user_posts(handle, args.limit)
        except Exception as exc:  # noqa: BLE001
            had_error = True
            print(f"[WARN] {exc}", file=sys.stderr)
            rows_by_handle[handle] = []
            display_names[handle] = handle
            continue

        if raw_dir:
            (raw_dir / f"{handle}.json").write_text(
                json.dumps(envelope, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        data = envelope.get("data", [])
        display_names[handle] = detect_display_name(data, handle)

        kept: list[dict] = []
        for item in data:
            if args.author_guard and not keep_for_handle(item, handle):
                continue

            dt = parse_created_at(item, tz)
            if dt is None:
                continue
            if dt.strftime("%Y-%m-%d") != target_date:
                continue

            tweet_id = item.get("id")
            if not tweet_id:
                continue

            kind = detect_kind(item)
            text = maybe_translate_text(item.get("text", ""), translator, item.get("lang"))

            quoted = item.get("quotedTweet") or {}
            quoted_text = maybe_translate_text(
                quoted.get("text", ""),
                translator,
                quoted.get("lang"),
            )

            kept.append(
                {
                    "dt": dt,
                    "kind": kind,
                    "url": f"https://x.com/{handle}/status/{tweet_id}",
                    "text": text,
                    "quoted_text": quoted_text,
                }
            )

        kept.sort(key=lambda x: x["dt"], reverse=True)
        rows_by_handle[handle] = kept

    md = build_markdown(rows_by_handle, display_names)
    output_path = Path(output)
    output_path.write_text(md, encoding="utf-8")
    print(f"[OK] Wrote markdown: {output_path.resolve()}")

    if had_error:
        print("[WARN] Some accounts failed to fetch; output contains successful accounts only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
