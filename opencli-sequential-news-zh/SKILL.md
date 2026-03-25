---
name: opencli-sequential-news-zh
description: Run configurable opencli news commands sequentially, skip failed commands, normalize JSON stories, and deduplicate globally by URL before exporting a Chinese Markdown digest. Use when user wants repeatable multi-source news aggregation with easy command add/remove via commands.json and requires model-handled translation (no third-party translation API).
---

# OpenCLI Sequential News ZH

## Workflow

1. Use current working directory as the output directory.
2. Read command configuration:
   - Default: `references/commands.json` inside this skill.
   - Optional override: user-provided config path via `--config`.
3. Run pipeline script sequentially:

```bash
python3 /Users/x/.codex/skills/opencli-sequential-news-zh/scripts/run_news_pipeline.py --config <commands.json> --out-json <tmp_json_path>
```

4. Parse pipeline JSON result:
   - `section_order`: section order from config.
   - `grouped_items`: deduplicated items grouped by section.
   - `errors`: failed commands.
   - `stats`: counts.
5. Translate titles into Chinese in-model:
   - Translate only deduplicated items.
   - Keep `url` and `time` unchanged.
   - If single title translation fails, keep original title and continue.
   - Do not call third-party translation API.
6. Write Markdown file to current working directory:
   - Filename format: `YYYY-MM-DD-HH-mm_fullNews.md`.
   - Timezone: `Asia/Shanghai` unless user explicitly requests another timezone.
7. Append `## errors` section at the end with failed command summaries.

## commands.json Format

Use JSON array of objects:

```json
[
  {
    "section": "middle-east",
    "command": ["opencli", "ReutersBrowser", "news", "https://www.reuters.com/world/middle-east/", "--limit", "10", "--format", "json"]
  }
]
```

Rules:
- Keep order as desired final processing order.
- Add/remove sources by adding/removing objects only.
- `command` supports string array (recommended) or shell string.

## Markdown Output Contract

For each section in `section_order`, always emit a section header even when no stories remain after deduplication:

```markdown
## section（N条）

### [中文标题](https://...)
- 发布时间：YYYY-MM-DD HH:MM:SS
```

Constraints:
- Missing time must be `页面未显示`.
- Preserve first-seen order: command order first, then source order.
- Global dedupe key is absolute URL exact match.
- Add final block:

```markdown
## errors

### 1. section
- 命令：`...`
- 错误：...
```

## Validation Checklist

1. Pipeline runs all commands sequentially.
2. Failed command does not stop later commands.
3. Duplicate URLs are removed globally, keeping first occurrence.
4. Translation is model-handled, not external translation API.
5. All sections are present, including `（0条）` sections.
