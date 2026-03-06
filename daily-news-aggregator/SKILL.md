---
name: daily-news-aggregator
description: Aggregate same-day news markdown files in the current project folder into one summary markdown file, deduplicate stories by exact URL, and keep deduplicated stories in their original groups.
---

# Daily News Aggregator

Use this skill to merge today's news markdown files, remove duplicates by URL while preserving first-seen order, then keep deduplicated news in the original input groups (for example: technology/business/world/...).

## Workflow

1. Identify candidate files in the current working directory:
   - Match file name pattern: `yyyy-mm-dd-hh-mm_news.md`
   - Keep only files whose date prefix equals today's date
   - Exclude output file itself to avoid re-reading generated content
2. Parse news items from each file in filename ascending order:
   - Title line format: `### **...**`
   - Time line format: `- 发布时间：...`
   - Link line format: `- 链接：(https://...)`
3. Deduplicate globally by exact URL string:
   - Keep first occurrence
   - Drop later duplicates even if title/time differs
4. Keep deduplicated entries in original groups:
   - Parse section headers in input files: `## <group>`
   - If the same URL appears in multiple groups, keep it in the first-seen group
   - Preserve first-seen order within each group
5. Write one output file:
   - File name: `yyyy-mm-dd_news_summary.md`
   - Output structure: dynamic group sections in first-seen order
   - Do not print full markdown content in chat; only report path and stats

## Script

Run:

```bash
python3 /Users/x/.codex/skills/daily-news-aggregator/scripts/merge_daily_news.py --dir "$PWD"
```

Useful options:

- `--date YYYY-MM-DD` override target day
- `--output <filename>` custom output filename
- `--pattern <glob>` customize input scan pattern (default `*_news.md`)

## Output Format

```markdown
# Daily News Summary - YYYY-MM-DD
- 被汇总文件：file1.md, file2.md
- 去重前条目总数：M
- 被去重条目数：D
- 去重后条目总数：K
- 分组统计：technology T 条，business B 条，world W 条，...
- 生成时间：YYYY-MM-DD HH:MM:SS
- 扫描文件数：N

## daily_news_summary (YYYY-MM-DD)
### technology（T）
### **中文标题**
- 发布时间：...
- 链接：(https://...)
### business（B）
### **中文标题**
- 发布时间：...
- 链接：(https://...)
### world（W）
### **中文标题**
- 发布时间：...
- 链接：(https://...)
### 其他来源分组（...）
### **中文标题**
- 发布时间：...
- 链接：(https://...)
```

## Failure Handling

- If no same-day input files are found, report that no output is generated.
- If malformed entries exist, skip them and continue processing.
- If file read/write fails, return explicit error message with file path.
