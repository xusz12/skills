---
name: reuters-multi-section-top10-zh-devtools
description: Extract headlines from Reuters sections, BBC News, Ars Technica, and TechCrunch Latest using Chrome DevTools, deduplicate by URL globally, and export Markdown to the current project folder.
---

# Multi-Source Top10 Zh Devtools Export

Use Chrome DevTools to extract headlines deterministically from Reuters section pages, BBC News, Ars Technica, and TechCrunch Latest.

## Supported URLs (Common)

1. `https://www.reuters.com/technology/`
2. `https://www.reuters.com/business/`
3. `https://www.reuters.com/world/`
4. `https://www.reuters.com/world/china/`
5. `https://www.bbc.com/news`
6. `https://arstechnica.com/`
7. `https://techcrunch.com/latest/`

Use all supported URLs as defaults unless the user provides a custom URL list.

## Workflow

1. Build URL list:
   - If the user provides multiple URLs, use them all.
   - Otherwise use default list: `https://www.reuters.com/technology/`, `https://www.reuters.com/business/`, `https://www.reuters.com/world/`, `https://www.reuters.com/world/china/`, `https://www.bbc.com/news`, `https://arstechnica.com/`, `https://techcrunch.com/latest/`.
2. Process each URL sequentially in visible-browser mode (no parallel fetch):
   - Run the Chrome DevTools session with a visible browser window (browser UI enabled).
   - Create one tab with `mcp__chrome-devtools__new_page` for the first URL, then use `mcp__chrome-devtools__navigate_page` for each remaining URL in the same tab.
   - Run extraction script directly via `mcp__chrome-devtools__evaluate_script` — do **not** call `take_snapshot` upfront.
   - Only call `mcp__chrome-devtools__take_snapshot` when any of the following conditions are met:
     - Script returns `{ error: 'main_not_found' }` (page may not have finished rendering; use snapshot to verify DOM state before retrying)
     - Script returns fewer than 3 items (determine whether content is genuinely sparse or DOM is not yet loaded)
     - Page structure appears abnormal (use snapshot to diagnose before retrying or skipping)
   - Keep first 10 valid items currently available on the page, in page order for that URL.
   - Store raw extraction results only at this stage: `section`, `time`, original `title`, and absolute `url`.
3. Derive section key from URL path:
   - `.../world/china/` -> `china`
   - `.../world/` -> `world`
   - `.../business/` -> `business`
   - `.../technology/` -> `technology`
   - `https://www.bbc.com/news` -> `bbc_news`
   - `https://arstechnica.com/` -> `arstechnica`
   - `https://techcrunch.com/latest/` -> `techcrunch_latest`
4. After all URLs have been processed, deduplicate globally across all collected stories using absolute URL as unique key:
   - Merge all section results in collection order (URL list order + DOM order).
   - Keep the first occurrence for each URL and drop later duplicates.
   - Preserve remaining item order.
5. Translate the deduplicated titles in one batch:
   - Translate only after global URL deduplication is complete.
   - Preserve item order and section assignment.
   - Keep `time` and `url` unchanged; only replace the original title text with natural Chinese.
6. Export Markdown only to the current project folder (current working directory):
   - Write output to a file named `yyyy-mm-dd-hh-mm_news.md` (example: `2026-02-27-14-35_news.md`).
   - Do not print the full Markdown content in chat.
   - Only report completion and exported file path.
7. Before finishing the skill, close Chrome DevTools session:
   - Close opened pages with `mcp__chrome-devtools__list_pages` + `mcp__chrome-devtools__close_page` when possible.
   - Ensure DevTools process is closed (for example: `pkill -f chrome-devtools-mcp`) before final completion.

## Markdown File Format

```markdown
## bbc_news
### **中文标题1**
- 发布时间：页面未显示
- 链接：(https://...)
```

Use grouped section blocks in the file. No table output.
Keep section grouping derived during extraction even though title translation happens later in a single batch.

## Extraction Script Pattern (Domain-Aware)

Use this `evaluate_script` pattern. It selects a site-specific extraction path (`reuters.com` / `bbc.com` / `arstechnica.com` / `techcrunch.com`) and falls back to a generic article parser when needed.

```javascript
() => {
  const main = document.querySelector('main');
  if (!main) return { error: 'main_not_found' };

  const host = location.hostname.replace(/^www\./, '');
  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const toAbs = (href) => {
    try {
      return new URL(href, location.href).href;
    } catch {
      return null;
    }
  };

  // Reuters path: article URL contains trailing date segment like ...-2026-02-27/
  if (host === 'reuters.com') {
    const timeRe =
      /(\d+\s*(?:mins?|minutes?|hours?)\s+ago|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}|\d{1,2}:\d{2}\s*[AP]M\s*GMT[+-]\d+)/i;
    const articleUrlRe = /-\d{4}-\d{2}-\d{2}\/$/;

    const anchors = Array.from(main.querySelectorAll('a[href]'))
      .map((a) => ({ a, url: toAbs(a.getAttribute('href')) }))
      .filter(({ url }) => !!url && articleUrlRe.test(url));

    const byUrl = new Map();
    let order = 0;

    for (const { a, url } of anchors) {
      const rawTitle = normalize(a.textContent);
      const validTitle = rawTitle.length > 20 && rawTitle.toLowerCase() !== 'category';

      let time = 'N/A';
      let node = a;
      for (let i = 0; i < 10 && node; i++) {
        const m = normalize(node.textContent).match(timeRe);
        if (m) {
          time = m[1];
          break;
        }
        node = node.parentElement;
      }

      if (!byUrl.has(url)) {
        byUrl.set(url, { order: order++, time, title: validTitle ? rawTitle : '', url });
      } else if (!byUrl.get(url).title && validTitle) {
        const cur = byUrl.get(url);
        cur.title = rawTitle;
        if (cur.time === 'N/A' && time !== 'N/A') cur.time = time;
        byUrl.set(url, cur);
      }
    }

    return Array.from(byUrl.values())
      .filter((x) => x.title)
      .sort((a, b) => a.order - b.order)
      .slice(0, 10)
      .map(({ time, title, url }) => ({ time, title, url }));
  }

  // BBC News path: extract only main news article/live links and keep page-order.
  // Time must be captured from the same anchor text to avoid cross-card misassignment.
  if (host === 'bbc.com') {
    const isNewsLink = (href) => {
      try {
        const u = new URL(href, location.href);
        return u.hostname.includes('bbc.com') && /\/news\/(articles|live)\//.test(u.pathname);
      } catch {
        return false;
      }
    };

    const anchors = Array.from(main.querySelectorAll('a')).filter((a) => a.querySelector('h1, h2, h3'));

    const seen = new Set();
    const rows = [];

    for (const a of anchors) {
      const titleEl = a.querySelector('h1, h2, h3');
      const title = normalize(titleEl?.textContent || '');
      const url = toAbs(a.getAttribute('href'));
      if (!title || !url || !isNewsLink(url) || seen.has(url)) continue;

      // Strictly match time within current card text only.
      const cardText = normalize(a.innerText || a.textContent || '');
      const m = cardText.match(/\b\d+\s*(?:mins?|minutes?|hours?|hrs?|days?)\s+ago\b/i);
      const time = m ? normalize(m[0]) : '页面未显示';

      rows.push({ time, title, url });
      seen.add(url);
      if (rows.length >= 10) break;
    }

    return rows;
  }

  // Ars Technica path: prefer article cards and <time datetime>
  if (host === 'arstechnica.com') {
    const articleUrlRe = /arstechnica\.com\/.+\/\d{4}\/\d{2}\//;
    const seen = new Set();
    const rows = [];

    for (const article of Array.from(main.querySelectorAll('article'))) {
      const titleLink =
        article.querySelector('h1 a[href], h2 a[href], h3 a[href], .listing-title a[href]') ||
        article.querySelector('a[href*="/20"]');
      if (!titleLink) continue;

      const url = toAbs(titleLink.getAttribute('href'));
      if (!url || !articleUrlRe.test(url) || seen.has(url)) continue;

      const title = normalize(titleLink.textContent);
      if (title.length < 12) continue;

      const timeEl = article.querySelector('time');
      const time = normalize(timeEl?.getAttribute('datetime') || timeEl?.textContent || 'N/A');

      rows.push({ time, title, url });
      seen.add(url);
      if (rows.length >= 20) break;
    }

    return rows.slice(0, 10);
  }

  // TechCrunch Latest path: page uses loop cards (not semantic <article> for feed rows)
  if (host === 'techcrunch.com' && /\/latest\/?$/.test(location.pathname)) {
    const articleUrlRe = /^https:\/\/techcrunch\.com\/\d{4}\/\d{2}\/\d{2}\//;
    const timeRe = /\b\d+\s*(?:minute|minutes|hour|hours|day|days)\s+ago\b/i;

    const anchors = Array.from(
      main.querySelectorAll('.loop-card__title a[href], a[href*="techcrunch.com/20"]')
    );

    const seen = new Set();
    const rows = [];

    for (const a of anchors) {
      const title = normalize(a.textContent);
      const url = toAbs(a.getAttribute('href'));
      if (!title || title.length < 20 || !url || !articleUrlRe.test(url) || seen.has(url)) continue;

      const card = a.closest('.loop-card__content') || a.closest('.loop-card') || a.parentElement;
      const cardText = normalize(card?.innerText || card?.textContent || '');
      const timeMatch = cardText.match(timeRe);

      rows.push({
        time: timeMatch ? normalize(timeMatch[0]) : '页面未显示',
        title,
        url,
      });
      seen.add(url);

      if (rows.length >= 10) break;
    }

    return rows;
  }

  // Generic fallback for similar news layouts
  const fallback = [];
  const seen = new Set();
  for (const article of Array.from(main.querySelectorAll('article'))) {
    const titleLink = article.querySelector('h1 a[href], h2 a[href], h3 a[href], a[href]');
    if (!titleLink) continue;

    const url = toAbs(titleLink.getAttribute('href'));
    if (!url || seen.has(url)) continue;

    const title = normalize(titleLink.textContent);
    if (title.length < 10) continue;

    const timeEl = article.querySelector('time');
    const time = normalize(timeEl?.getAttribute('datetime') || timeEl?.textContent || 'N/A');

    fallback.push({ time, title, url });
    seen.add(url);
    if (fallback.length >= 10) break;
  }

  return fallback;
};
```

## Script Suitability Notes (BBC + TechCrunch)

1. BBC homepage mixes headline streams, live blogs, and ranked blocks; URL filtering to `/news/articles/` and `/news/live/` avoids most navigation/video noise.
2. Some BBC cards do not show visible time; keep `页面未显示` rather than inferring.
3. Time extraction must stay card-local (`a.innerText`) to prevent borrowing nearby card timestamps.
4. TechCrunch `/latest/` feed commonly renders story rows as `.loop-card__content` blocks, so `article`-only parsing is not reliable.
5. For TechCrunch, filter to canonical story URLs (`/YYYY/MM/DD/...`) and dedupe by absolute URL to avoid category/footer/popular duplicates.
6. For TechCrunch, extract time from the same loop-card text block to avoid cross-card time leakage.

## Quality Checks

1. Fetch top 10 for every URL in the input list, not just one URL.
2. Before global URL deduplication, collect up to 10 items per URL from the content directly available on the page.
3. After global URL deduplication, fewer than 10 items in a section is acceptable.
4. Do not call `take_snapshot` unless a trigger condition is met (see Workflow step 2). On normal pages this call is unnecessary and wastes time.
5. Ensure URL is absolute and belongs to the current target site (`reuters.com`, `bbc.com`, `arstechnica.com`, or `techcrunch.com`).
6. Exclude navigation links, ads, and footer links.
7. Keep timestamps exactly as shown on page (for Ars, prefer `<time datetime>` when available; for BBC/TechCrunch missing values use `页面未显示`).
8. Before translation, deduplicate all collected stories globally by absolute URL and preserve first occurrence order.
9. Batch-translate only the deduplicated titles into natural Chinese without changing factual meaning.
10. Do not translate items that will later be dropped by global URL deduplication.
11. Export Markdown file to the current project folder only using the filename format `yyyy-mm-dd-hh-mm_news.md`, and do not print full Markdown content in chat.
12. Ensure Chrome DevTools session is closed before finishing.
