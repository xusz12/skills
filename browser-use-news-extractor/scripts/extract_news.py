#!/usr/bin/env python3
"""Extract Reuters China news rows via browser-use and write normalized JSON.

Pipeline (fixed decisions):
1) browser-use --browser <mode> [--headed] open <url>
2) browser-use --browser <mode> [--headed] wait selector main (retry once)
3) browser-use --browser <mode> [--headed] eval <adapter script>
4) normalize + dedupe by URL + keep top N

V1 supports: reuters_china
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_TIME_TEXT = "页面未显示"

ADAPTERS: dict[str, dict[str, str]] = {
    "reuters_china": {
        "default_url": "https://www.reuters.com/world/china/",
        "eval_js": r'''(() => {
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim();
  const isTitle = (t) => t && t.length > 20 && !/^report ad$/i.test(t) && !t.startsWith("<img");
  const toAbs = (href) => {
    try {
      return new URL(href, location.href).href;
    } catch {
      return "";
    }
  };
  const isReutersArticle = (url) => {
    try {
      const u = new URL(url);
      return /(^|\.)reuters\.com$/i.test(u.hostname) && /-\d{4}-\d{2}-\d{2}\/?$/i.test(u.pathname);
    } catch {
      return false;
    }
  };

  const main = document.querySelector("main");
  if (!main) return JSON.stringify({ error: "main_not_found" });

  const rows = [];
  const seen = new Set();

  const pushRow = (titleSource, timeText, datetimeIso, url) => {
    if (!isTitle(titleSource) || !url || seen.has(url)) return;
    seen.add(url);
    rows.push({
      title_source: clean(titleSource),
      time_text: clean(timeText) || "页面未显示",
      datetime_iso: clean(datetimeIso),
      url,
    });
  };

  const times = Array.from(main.querySelectorAll("time"));
  for (const tm of times) {
    const timeText = clean(tm.textContent);
    const datetimeIso = clean(tm.getAttribute("datetime"));

    let container = tm;
    let picked = null;

    for (let i = 0; i < 8 && container; i++) {
      container = container.parentElement;
      if (!container) break;

      const anchors = Array.from(container.querySelectorAll("a[href]"));
      for (const a of anchors) {
        const title = clean(a.textContent);
        const url = toAbs(a.getAttribute("href"));
        if (!isTitle(title) || !isReutersArticle(url)) continue;
        picked = { title, url };
        break;
      }
      if (picked) break;
    }

    if (picked) {
      pushRow(picked.title, timeText, datetimeIso, picked.url);
    }

    if (rows.length >= 40) break;
  }

  if (rows.length < 10) {
    const anchors = Array.from(main.querySelectorAll("a[href]"));
    for (const a of anchors) {
      const title = clean(a.textContent);
      const url = toAbs(a.getAttribute("href"));
      if (!isTitle(title) || !isReutersArticle(url)) continue;

      let timeText = "页面未显示";
      let datetimeIso = "";
      let node = a;
      for (let i = 0; i < 7 && node; i++) {
        const candidate = node.querySelector("time");
        if (candidate) {
          timeText = clean(candidate.textContent) || timeText;
          datetimeIso = clean(candidate.getAttribute("datetime"));
          break;
        }
        node = node.parentElement;
      }

      pushRow(title, timeText, datetimeIso, url);
      if (rows.length >= 40) break;
    }
  }

  return JSON.stringify(rows);
})()''',
    }
}


def clean_text(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def is_absolute_http_url(value: str) -> bool:
    try:
        p = urlparse(value)
    except ValueError:
        return False
    return p.scheme in {"http", "https"} and bool(p.netloc)


def run_command(cmd: list[str], allow_fail: bool = False) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(cmd, text=True, capture_output=True)
    if cp.returncode != 0 and not allow_fail:
        stderr = cp.stderr.strip() or cp.stdout.strip()
        raise RuntimeError(f"command failed ({cp.returncode}): {' '.join(cmd)}\n{stderr}")
    return cp


def command_base(browser_mode: str, headed: bool) -> list[str]:
    base = ["browser-use", "--browser", browser_mode]
    if headed:
        base.append("--headed")
    return base


def parse_eval_result(stdout: str) -> object:
    lines = [line for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("result:"):
            raw = line.split("result:", 1)[1].strip()
            return json.loads(raw)
    raise ValueError("cannot find 'result:' line in browser-use eval output")


def wait_for_main(base_cmd: list[str], retries: int = 1) -> bool:
    attempts = retries + 1
    for idx in range(attempts):
        cp = run_command(base_cmd + ["wait", "selector", "main"], allow_fail=True)
        if cp.returncode == 0 and "found: True" in cp.stdout:
            return True
        if idx < attempts - 1:
            time.sleep(2)
    return False


def normalize_rows(
    rows: list[dict],
    site: str,
    top: int,
) -> tuple[list[dict], list[str]]:
    normalized: list[dict] = []
    warnings: list[str] = []
    seen_urls: set[str] = set()

    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            warnings.append(f"row {idx}: non-object row skipped")
            continue

        title_source = clean_text(row.get("title_source") or row.get("title"))
        time_text = clean_text(row.get("time_text") or row.get("time"), DEFAULT_TIME_TEXT) or DEFAULT_TIME_TEXT
        datetime_iso = clean_text(row.get("datetime_iso") or row.get("datetime"))
        url = clean_text(row.get("url"))

        if len(title_source) < 20:
            warnings.append(f"row {idx}: title too short, skipped")
            continue
        if title_source.lower() == "report ad" or title_source.startswith("<img"):
            warnings.append(f"row {idx}: ad/noise title skipped")
            continue
        if not is_absolute_http_url(url):
            warnings.append(f"row {idx}: invalid absolute url skipped")
            continue

        host = urlparse(url).hostname or ""
        if site == "reuters_china" and "reuters.com" not in host:
            warnings.append(f"row {idx}: non-reuters url skipped")
            continue

        if url in seen_urls:
            continue
        seen_urls.add(url)

        normalized.append(
            {
                "site": site,
                "title_source": title_source,
                "time_text": time_text,
                "datetime_iso": datetime_iso,
                "url": url,
            }
        )

        if len(normalized) >= top:
            break

    if len(normalized) < top:
        warnings.append(f"only {len(normalized)} items available after normalization (target={top})")

    return normalized, warnings


def build_default_output(site: str) -> Path:
    ts = dt.datetime.now().strftime("%Y-%m-%d-%H-%M")
    return Path("/tmp") / f"{ts}_{site}_raw.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract Reuters China news rows via browser-use.")
    parser.add_argument("--site", choices=sorted(ADAPTERS.keys()), default="reuters_china")
    parser.add_argument("--url", default=None, help="Override site default URL")
    parser.add_argument("--top", type=int, default=10, help="Keep top N rows after normalization")
    parser.add_argument(
        "--browser-mode",
        choices=["real", "chromium", "remote"],
        default="real",
        help="browser-use mode",
    )

    headed_group = parser.add_mutually_exclusive_group()
    headed_group.add_argument("--headed", dest="headed", action="store_true", default=True)
    headed_group.add_argument("--no-headed", dest="headed", action="store_false")

    parser.add_argument("--output", default=None, help="Output JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    site_conf = ADAPTERS[args.site]
    target_url = args.url or site_conf["default_url"]
    top = max(1, args.top)

    try:
        base = command_base(args.browser_mode, args.headed)
        run_command(base + ["open", target_url])

        if not wait_for_main(base, retries=1):
            print("ERROR: failed to detect main content after retries", file=sys.stderr)
            return 2

        raw_rows: object | None = None
        for attempt in range(2):
            cp = run_command(base + ["eval", site_conf["eval_js"]], allow_fail=True)
            if cp.returncode != 0:
                if attempt == 0:
                    time.sleep(2)
                    continue
                err = cp.stderr.strip() or cp.stdout.strip()
                print(f"ERROR: eval command failed: {err}", file=sys.stderr)
                return 2

            payload = parse_eval_result(cp.stdout)
            if isinstance(payload, dict) and payload.get("error") == "main_not_found":
                if attempt == 0:
                    wait_for_main(base, retries=1)
                    continue
                print("ERROR: adapter reported main_not_found after retry", file=sys.stderr)
                return 2

            raw_rows = payload
            break

        if not isinstance(raw_rows, list):
            print("ERROR: adapter payload is not a list", file=sys.stderr)
            return 2

        normalized, warnings = normalize_rows(raw_rows, args.site, top)
        if not normalized:
            print("ERROR: no valid rows after normalization", file=sys.stderr)
            for warning in warnings:
                print(f"WARN: {warning}", file=sys.stderr)
            return 2

        output_path = Path(args.output).expanduser().resolve() if args.output else build_default_output(args.site)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(f"Raw extraction file: {output_path}")
        print(f"Items kept: {len(normalized)}")
        if warnings:
            print(f"Warnings: {len(warnings)}", file=sys.stderr)
            for warning in warnings:
                print(f"WARN: {warning}", file=sys.stderr)

        return 0

    except (RuntimeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
