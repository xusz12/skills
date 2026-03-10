---
name: get-twitters
description: Fetch tweets from specific X/Twitter accounts with the local `twitter` CLI and format the results for the user. Use when the user asks to collect recent or same-day posts from one or more accounts, filter out retweets or replies, convert timestamps to a requested timezone, translate non-Chinese tweets into Chinese, or present the results as ordered Markdown digests with tweet links.
---

# Get Twitters

## Overview

Use the local `twitter` CLI to collect posts from specific accounts, filter them to the user’s requested date window, and render the output in Markdown.

Prefer this skill when the user cares about exact tweet recency, account order, timezone-normalized times, and a clean per-account report.

## Workflow

1. Confirm the CLI is available with `twitter --help` if the environment is uncertain.
2. Fetch recent posts per handle with `twitter user-posts <handle> -n 30 --json`.
3. Increase `-n` to `50` only if the first fetch may not cover the requested date window.
4. Parse each post's `createdAt`, convert it to the requested timezone, and keep only posts inside the requested time range.
5. Exclude pure retweets by dropping items where `isRetweet` is `true`.
6. Exclude replies when the user asks for timeline posts only.
7. Build the canonical tweet link as `https://x.com/<handle>/status/<tweet_id>`.
8. If a kept post is not in Chinese, translate the full visible tweet text into Chinese.
9. Preserve URLs, `@mentions`, product names, and line breaks in the translated output.
10. Render the final result in the user’s requested account order.

## Filtering Rules

- Treat the requested timezone as authoritative. If the user says "北京时间", use `Asia/Shanghai`.
- When the user says "today", interpret it using the requested timezone, not UTC.
- If the CLI output mixes in posts from unrelated accounts, keep only items whose author handle matches the requested account.
- If reply detection is ambiguous, be conservative and exclude clear reply-shaped posts rather than risking false positives.
- If a kept post has an obviously truncated body and completeness matters, try `twitter tweet <tweet_id> --json` once and use the best available text.

## Output Format

- Preserve the account order requested by the user.
- Group output by account unless the user explicitly asks for a merged timeline.
- Use Markdown.
- For each kept tweet, include only the fields the user asked for. Common fields are:
  - `发布时间（北京时间）`
  - `推文链接`
  - `内容`
- If an account has no matching posts, write `今日无符合条件的推文。`

## Notes

- The `twitter` CLI may return truncated text for some posts. Note that limitation in the response if it affects completeness.
- Network access to `x.com` may require running the CLI outside the sandbox.
- If the user refines the field list or account order after the first run, rerun the fetch and regenerate the final Markdown instead of manually editing stale output.
