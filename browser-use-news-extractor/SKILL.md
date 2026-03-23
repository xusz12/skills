---
name: browser-use-news-extractor
description: Extract news data with browser-use using a deterministic pipeline and export JSON plus Markdown. Use when the user needs headline/time/url extraction from Reuters China now, and a site-adapter structure that can be extended to additional news sites later.
---

# Browser-use News Extractor

Run a low-decision, repeatable pipeline:
1. Prepare browser session (`close -> open -> wait main`)
2. Extract raw rows from a site adapter (`eval` JavaScript)
3. Normalize and deduplicate by absolute URL
4. Translate titles to Chinese in-model
5. Export JSON and Markdown together

## Scope (V1)

- Implement only `reuters_china` adapter by default.
- Default URL: `https://www.reuters.com/world/china/`.
- Keep architecture adapter-based so new sites can be added without changing the core flow.

## Required Output

### Intermediate JSON (after extraction)

Each item must contain:
- `site`
- `title_source`
- `time_text`
- `datetime_iso`
- `url`

### Final JSON (after translation)

Each item must contain:
- `site`
- `title` (Chinese title)
- `time_text`
- `datetime_iso`
- `url`

### File naming

Use safe timestamp naming and export both files:
- `YYYY-MM-DD-HH-MM_<site>_news.json`
- `YYYY-MM-DD-HH-MM_<site>_news.md`

## Workflow

### Step 1: Extract and normalize (scripts/extract_news.py)

Run:

```bash
python3 scripts/extract_news.py --site reuters_china
```

Default behavior:
- `browser-use close`
- `browser-use --browser real --headed open <url>`
- `browser-use --browser real wait selector main` (retry once)
- `browser-use --browser real eval '<adapter script>'`
- Validate absolute URL, dedupe by URL, preserve order, keep top 10
- If fewer than 10 rows are available, continue and report warning

Optional parameters:

```bash
python3 scripts/extract_news.py \
  --site reuters_china \
  --url https://www.reuters.com/world/china/ \
  --top 10 \
  --browser-mode real \
  --headed \
  --output /tmp/reuters_raw.json
```

### Step 2: Translate titles to Chinese (in-model)

Use extraction output as input.
- Keep all fields unchanged except translated title.
- Write Chinese title into `title`.
- Do not alter ordering.

### Step 3: Export final JSON + Markdown (scripts/postprocess_news.py)

Run:

```bash
python3 scripts/postprocess_news.py \
  --input /tmp/reuters_translated.json \
  --output-dir "$PWD"
```

This command validates translated rows and writes both final files.
In Markdown output, `发布时间` must display local time formatted as `YYYY-MM-DD HH:mm` when `datetime_iso` is available.
Do not print a separate ISO time line in Markdown.

## Resources

- `scripts/extract_news.py`: session prep + adapter extraction + normalization + dedupe
- `scripts/postprocess_news.py`: translated input validation + JSON/Markdown export
- `references/site_adapters.md`: adapter contract and extension guide

## Quality Rules

1. Keep extraction deterministic and adapter-driven.
2. Keep URL dedupe stable (first occurrence wins).
3. Preserve page order after normalization.
4. Keep `time_text` always present; keep `datetime_iso` as empty string when unavailable.
5. Render Markdown `发布时间` as local time (`YYYY-MM-DD HH:mm`) converted from `datetime_iso` when possible.
6. Do not show `发布时间(ISO)` in Markdown; keep ISO only in JSON for traceability.
7. Exclude ad/noise titles (`Report Ad`, empty text, image placeholders).
8. Never print full Markdown content in chat; report file paths and counts.
