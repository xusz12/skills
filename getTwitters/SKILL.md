---
name: getTwitters
description: Fetch recent posts from one or more X/Twitter accounts with the local `twitter` CLI, classify each post as 原创/引用/转推, translate non-Chinese text into Chinese, and export a Markdown digest.
---

# Get Twitters

## Overview

Use this skill when the user asks to fetch tweets from one or more X/Twitter accounts, keep posts in a target date window, and export a Markdown file.

Default behavior:
- Date window: today in `Asia/Shanghai`
- Translation: enabled (non-Chinese -> Chinese)
- Author guard: enabled (filter mixed and ad posts by handle)
- Default accounts: `ilyasut`, `mingchikuo`, `WaylandZhang`, `ivanalog_com`, `fxtrader`, `dongxi_nlp`, `jakevin7`

## Workflow

1. Validate CLI availability if uncertain:

```bash
twitter --help
```

2. Fetch posts per handle:

```bash
twitter user-posts <handle> -n <N> --json --full-text
```

3. Convert timestamps to requested timezone and keep only posts in the target date.

4. Classify each kept post:
- `转推`: `isRetweet == true`
- `引用`: has `quotedTweet` and not retweet
- `原创`: neither retweet nor quote

5. Translate non-Chinese text to Chinese before writing Markdown.

6. Render Markdown in requested account order.

## Output Format

- Group by account heading:

```markdown
## <display_name> （@<handle>）
```

- Per post:

```markdown
##### <index>. [原创|引用|转推](tweet_url)发布时间（北京时间）：YYYY-MM-DD HH:mm
```

- Post body uses `text` fenced code block.
- Quote posts add both `引用` and `被引用` blocks.
- If an account has no matching posts for the date, output:

```markdown
今日无符合条件的推文。
```

## Script

Use the bundled script from this skill directory:

```bash
python3 scripts/export_tweets.py -n 20
```

Common options:
- `--accounts <a> <b> ...` (optional; default: built-in 7 accounts)
- `--date YYYY-MM-DD` (default: today in timezone)
- `--timezone Asia/Shanghai`
- `-n, --limit 20`
- `--output tweets_YYYY-MM-DD.md`
- `--disable-translation`
- `--author-guard` (enable safety check; default)
- `--no-author-guard` (disable safety check)

## Notes

- Run twitter fetch commands outside sandbox when environment requires browser cookies or Keychain access.
- If translation fails, keep original text and continue.
