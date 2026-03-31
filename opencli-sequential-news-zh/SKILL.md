---
name: opencli-sequential-news-zh
description: Run configurable opencli news commands sequentially, skip failed commands, normalize JSON stories, and deduplicate globally by URL before producing daily fresh-news and per-run fresh-news markdown digests. Use when user wants repeatable multi-source news aggregation with easy command add/remove via commands.json and requires model-handled translation (no third-party translation API).
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

4. Prepare incremental payload:

```bash
python3 /Users/x/.codex/skills/opencli-sequential-news-zh/scripts/run_incremental_news.py prepare --current-json <tmp_json_path> --state-dir <state_dir> --out-json <incremental_json_path>
```

5. Parse incremental JSON result:
   - `run_fresh_items_raw`: this run's fresh stories after removing yesterday URLs and earlier same-day URLs.
   - `daily_fresh_items_raw`: today's cumulative fresh stories after removing yesterday URLs.
   - `items_to_translate`: stories whose titles still need model translation for display.
   - `current_run_errors`: failed commands from this run.
   - `daily_errors`: accumulated failed commands for the current day.
6. Translate titles into Chinese in-model:
   - Translate only `items_to_translate`.
   - Translation must stay in the model, not inside any script.
   - Write a JSON object mapping URL to translated title, for example:

```json
{
  "https://example.com/story": "中文标题"
}
```

7. Finalize outputs:

```bash
python3 /Users/x/.codex/skills/opencli-sequential-news-zh/scripts/run_incremental_news.py finalize --incremental-json <incremental_json_path> --translated-json <translated_json_path> --state-dir <state_dir> --out-dir <current_working_directory>
```

8. Finalize writes exactly two user-facing Markdown files:
   - `YYYY-MM-DD_dailyFreshNews.md`: one rolling summary file per day.
   - `YYYY-MM-DD-HH-mm_freshNews.md`: one per-run fresh-news file.
   - Timezone: `Asia/Shanghai` unless user explicitly requests another timezone.
9. Hidden state is stored separately in the state directory, one JSON file per day.

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

## Output Contract

For each output Markdown file, always emit a section header even when no stories remain after filtering:

```markdown
## section（N条）

### [中文标题](https://...)
- 发布时间：YYYY-MM-DD HH:MM:SS
```

Constraints:
- Missing time must be `页面未显示`.
- Preserve first-seen order: command order first, then source order.
- Global dedupe key is absolute URL exact match.
- Daily filtering removes yesterday's URLs.
- Per-run filtering removes yesterday's URLs and URLs seen earlier the same day.
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
6. Finalize writes `YYYY-MM-DD_dailyFreshNews.md` and `YYYY-MM-DD-HH-mm_freshNews.md`, not `*_fullNews.md`.
