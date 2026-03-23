# Site Adapter Contract

Use adapter-based extraction so each site can evolve independently.

## Adapter interface

Each adapter provides:

- `default_url`: default page URL for the site
- `eval_js`: JavaScript string executed through `browser-use eval`

The JavaScript must return JSON serializable output in one of these shapes:

1. Success list:

```json
[
  {
    "title_source": "Original headline",
    "time_text": "13 hours ago",
    "datetime_iso": "2026-03-22T02:42:09.541Z",
    "url": "https://..."
  }
]
```

2. Recoverable error object:

```json
{ "error": "main_not_found" }
```

## Adapter requirements

1. Prefer semantic selectors (`main`, `time`, `a[href]`) over hash-like CSS classes.
2. Emit absolute URLs.
3. Keep `time_text` as shown on page.
4. Fill `datetime_iso` when available, otherwise empty string.
5. Avoid ad/noise content (`Report Ad`, image placeholders, empty titles).
6. Preserve page order before normalization.

## Reuters China notes (V1)

- URL: `https://www.reuters.com/world/china/`
- Stable extraction anchor is usually `main time` + nearby headline links.
- Fallback pass scans Reuters article URLs with date suffix (`.../YYYY-MM-DD/`).

## How to add a new site

1. Add one adapter entry in `extract_news.py`.
2. Define `default_url` and `eval_js`.
3. Keep output fields exactly aligned to the adapter contract.
4. Run extraction dry run and verify:
   - URL absolute
   - title non-empty
   - time fields present
   - top-N and dedupe behavior unchanged
5. Do not modify normalization/export contracts unless all adapters need it.
