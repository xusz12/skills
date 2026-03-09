---
name: news-newspaper-layout
description: |
  Transforms structured news summary files (Markdown or JSON) into a beautiful, printable newspaper-style HTML page. Use this skill whenever the user wants to:
  - Turn a news digest, daily briefing, or news summary into a newspaper layout
  - Create a visually styled HTML page from a list of news headlines
  - Generate a "报纸版面" (newspaper layout) from news data
  - Make news content easier and more enjoyable to read
  - Render any multi-category news list as a styled front page or broadsheet

  Always trigger this skill when the user asks for "报纸版面", "newspaper layout", "新闻排版", "news digest page", or wants to visualize a news feed. The output is always a single self-contained HTML file with zero external dependencies (except Google Fonts).
---

# News Newspaper Layout Skill

Converts a structured news summary (Markdown / JSON / plain text) into a self-contained, visually polished newspaper-style HTML page — ready to open in any browser.

---

## Step 1 — Parse the Input

Read the uploaded or referenced news file. Extract for each article:
- **Headline** (title / 标题)
- **Timestamp** (发布时间) — keep original format ("3 hours ago", "March 7", ISO strings all accepted)
- **URL** (链接)
- **Category / Section** (板块) — group articles by section

If the file has summary stats (total count, generation time, source names), capture them for the masthead.

---

## Step 2 — Design Decisions (commit before coding)

Choose ONE aesthetic direction and execute it fully. For news content the default is **classic broadsheet** (see below), but adapt if the user requests something different (e.g., tabloid, tech-magazine, dark mode).

### Default: Classic Broadsheet

| Element | Value |
|---|---|
| Paper color | `#f5f0e8` (warm ivory) |
| Ink color | `#1a1008` (near-black) |
| Accent color | `#8b1a1a` (dark red) |
| Display font | `Playfair Display` (Google Fonts) — headlines |
| Body font | `Libre Baskerville` (Google Fonts) — meta, labels |
| Chinese body font | `Noto Serif SC` (Google Fonts) — Chinese prose |
| Texture | SVG feTurbulence noise layer via `::before` pseudo-element |
| Shadow | `box-shadow: 0 4px 40px rgba(0,0,0,0.45)` on the newspaper container |

Vary section accent colors to aid visual navigation (red, slate blue, forest green, orange, etc.).

---

## Step 3 — HTML Structure (top to bottom)

Build the page in this order:

### 3a. Breaking News Ticker
```html
<div class="ticker">
  <div class="ticker-inner" id="ticker"><!-- top 5 headlines --></div>
</div>
```
- Black background, white text
- CSS `translateX` infinite loop animation (55s)
- JS: duplicate `innerHTML` for seamless looping

### 3b. Masthead
```
[source line]
[NEWSPAPER NAME — large Playfair Display 900 weight]
[subtitle / tagline]
[edition number | EDITION TAG | date]
```

### 3c. Section Navigation Bar
One `<a>` per section, `border-right` dividers, hover highlights to ink color, active section in accent color.

### 3d. Content Body

Use CSS Grid for layout. Key grid patterns:

| Layout | CSS | Use case |
|---|---|---|
| 2-col asymmetric | `grid-template-columns: 2fr 1fr` | Top story + sidebar |
| 3-col equal | `grid-template-columns: repeat(3, 1fr)` | Mid-tier articles |
| 4-col equal | `grid-template-columns: repeat(4, 1fr)` | Briefs / short items |
| Feature | `grid-template-columns: 3fr 2fr` | Lead story |

**Article importance hierarchy:**

| Class | Font size | When to use |
|---|---|---|
| `.headline-xl` | ~34px / clamp | #1 story of the section |
| `.headline-lg` | ~24px | 2nd most important |
| `.headline-md` | ~18px | Standard article |
| `.headline-sm` | 14px | Brief |
| `.headline-xs` | 12.5px | Filler / short item |

**Between articles in the same row:** use `border-right: 1px solid rgba(26,16,8,0.18)` on all but the last child.

**Section header pattern:**
```html
<div class="section-header [accent|slate|forest]">
  <span class="label">板块名</span>
  <span class="count">N 篇报道</span>
  <hr> <!-- flex: 1 rule line -->
  <span class="count">ENGLISH NAME</span>
</div>
```

**Featured story pattern (top story of World/International section):**
```html
<div class="featured">
  <span class="kicker">战事 · 最新进展</span>
  <div class="grid-feature">
    <div><!-- large headline + 2-sentence summary --></div>
    <div><!-- pull-quote + briefs-list sidebar --></div>
  </div>
</div>
```

**Briefs list** (for sidebar / compact sections):
```html
<ul class="briefs-list">
  <li>
    <a href="...">Headline text</a>
    <span class="brief-time">Source · time</span>
  </li>
</ul>
```

### 3e. Footer
```
[© copyright line]   [sources list]   [generation timestamp]
```

---

## Step 4 — CSS Essentials

Always include these rules:

```css
/* Paper texture */
.newspaper::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,...feTurbulence baseFrequency='0.9'...");
  pointer-events: none;
  z-index: 10;
  opacity: 0.6;
}

/* Staggered article fade-in */
.article {
  animation: fadeIn 0.5s ease both;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Responsive collapse */
@media (max-width: 768px) {
  .grid-3, .grid-4, .grid-5, .grid-main, .grid-feature {
    grid-template-columns: 1fr;
  }
}
```

---

## Step 5 — JavaScript

Minimal JS, two tasks only:

```js
// 1. Staggered animation delay
document.querySelectorAll('.article').forEach((el, i) => {
  el.style.animationDelay = `${i * 0.04}s`;
});

// 2. Seamless ticker loop
const ticker = document.getElementById('ticker');
ticker.innerHTML += ticker.innerHTML;
```

---

## Step 6 — Output

- Write the complete file to `/mnt/user-data/outputs/YYYY-MM-DD_newspaper.html`
- Call `present_files` with the output path
- Give a one-sentence summary (e.g. "已将 67 条新闻整理为 7 个板块的报纸版面。")

---

## Layout Assignment Guide

Use this heuristic to assign articles to layout slots:

| Section size | Layout strategy |
|---|---|
| 1–3 articles | Single featured block + briefs list |
| 4–6 articles | Featured (col-span-2) + 2 standard + briefs |
| 7–10 articles | Top story full-width OR 3fr/2fr feature, then grid-3 or grid-4 for the rest |
| Mixed sections | Pair two sections side-by-side with `grid-main` (2fr + 1fr), separated by `border-left` |

For **China / 中国 sections**: use slate blue (`#2c4a6e`) as the label background.  
For **Tech sections**: use default dark ink.  
For **Business / 财经**: use forest green (`#2d5a3d`).  
For **Breaking / International**: use accent red (`#8b1a1a`).

---

## Quality Checklist

Before writing the file, verify:
- [ ] Every headline links to its original URL (`target="_blank"`)
- [ ] Ticker contains the 4–6 most important headlines
- [ ] At least one `featured` block with a kicker label
- [ ] Section headers use colored `.label` badges
- [ ] Responsive `@media` query present
- [ ] Ticker JS loop present
- [ ] Google Fonts `<link>` in `<head>`
- [ ] No external JS dependencies (Vanilla CSS/JS only)
- [ ] File saved to `/mnt/user-data/outputs/`