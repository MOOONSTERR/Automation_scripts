# AI 新闻聚合 CLI 工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a TypeScript CLI tool that fetches AI news from 3 RSS feeds, generates a Markdown daily report, and emails it via Gmail SMTP — run via Windows Task Scheduler on weekdays at 09:00.

**Architecture:** Single entry point `src/index.ts` exports pure utility functions (testable) and calls `main()` guarded by an ESM import-check so tests can import without side effects. Unit tests cover all pure functions; network calls (RSS fetch, email) are tested manually.

**Tech Stack:** TypeScript, tsx, rss-parser, nodemailer, dotenv, vitest

---

## File Map

| File | Role |
|---|---|
| `package.json` | deps, scripts (`start`, `test`) |
| `tsconfig.json` | TypeScript ESNext/bundler config |
| `.gitignore` | exclude `.env`, `node_modules`, `output` |
| `.env.example` | env var template + setup instructions |
| `output/.gitkeep` | ensure output dir is tracked |
| `src/index.ts` | all logic: types, pure functions, fetchFeed, sendEmail, main() |
| `src/index.test.ts` | unit tests for pure functions |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `output/.gitkeep`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "ai-news",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "tsx src/index.ts",
    "test": "vitest run"
  },
  "dependencies": {
    "dotenv": "^16.4.5",
    "nodemailer": "^6.9.13",
    "rss-parser": "^3.13.0"
  },
  "devDependencies": {
    "@types/nodemailer": "^6.4.14",
    "tsx": "^4.11.0",
    "typescript": "^5.4.5",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "outDir": "dist"
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create .gitignore**

```
node_modules/
.env
output/
dist/
```

- [ ] **Step 4: Create .env.example**

```
# Gmail 发件账号
GMAIL_USER=your_gmail@gmail.com

# Gmail App Password 获取步骤：
# 1. 访问 https://myaccount.google.com/security
# 2. 开启两步验证（若未开启）
# 3. 搜索"应用专用密码"，创建一个，名称填 ai-news
# 4. 将生成的16位密码（不含空格）填入下方
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# 收件人
RECIPIENT_EMAIL=hubin@jpnelson.com.sg

# ============================================================
# Windows 任务计划程序配置（周一至周五 09:00 自动运行）
# 在 cmd 或 PowerShell 中以管理员身份运行以下命令：
#
# schtasks /create ^
#   /tn "AI News Daily" ^
#   /tr "node \"C:\FULL\PATH\TO\node_modules\.bin\tsx\" \"C:\FULL\PATH\TO\src\index.ts\"" ^
#   /sc weekly ^
#   /d MON,TUE,WED,THU,FRI ^
#   /st 09:00 ^
#   /sd 01/01/2026
#
# 将 C:\FULL\PATH\TO 替换为项目实际路径，例如：
# C:\Users\hubin\OneDrive - JP NELSON EQUIPMENT PTE LTD\Documents\Claude_Projects\AI_News
#
# 验证任务已创建：
# schtasks /query /tn "AI News Daily"
# ============================================================
```

- [ ] **Step 5: Create output/.gitkeep**

Create an empty file at `output/.gitkeep` (touch the file or create it with no content).

- [ ] **Step 6: Install dependencies**

Run: `npm install`

Expected: `node_modules/` created, no errors.

- [ ] **Step 7: Commit**

```bash
git add package.json tsconfig.json .gitignore .env.example output/.gitkeep
git commit -m "feat: scaffold ai-news project"
```

---

## Task 2: Core Types + Pure Utility Functions (TDD)

**Files:**
- Create: `src/index.test.ts`
- Create: `src/index.ts` (partial — types + utilities only)

- [ ] **Step 1: Create src/index.test.ts with failing tests**

```typescript
import { describe, it, expect } from 'vitest';
import { stripHtml, extractDescription, filterRecent, deduplicateByLink } from './index.js';
import type { Article } from './index.js';
import RSSParser from 'rss-parser';

describe('stripHtml', () => {
  it('removes HTML tags', () => {
    expect(stripHtml('<p>Hello <b>world</b></p>')).toBe('Hello world');
  });
  it('handles empty string', () => {
    expect(stripHtml('')).toBe('');
  });
  it('replaces HTML entities with a space', () => {
    expect(stripHtml('A&amp;B')).toBe('A B');
  });
});

describe('extractDescription', () => {
  it('truncates to 100 characters', () => {
    const item = { contentSnippet: 'a'.repeat(200) } as RSSParser.Item;
    expect(extractDescription(item).length).toBe(100);
  });
  it('strips HTML tags', () => {
    const item = { contentSnippet: '<p>Hello world</p>' } as RSSParser.Item;
    expect(extractDescription(item)).toBe('Hello world');
  });
  it('returns empty string when no description fields exist', () => {
    expect(extractDescription({} as RSSParser.Item)).toBe('');
  });
});

describe('filterRecent', () => {
  it('keeps articles within 24 hours', () => {
    const recent: Article = {
      title: 'New', link: 'http://a.com',
      pubDate: new Date(Date.now() - 1 * 60 * 60 * 1000),
      source: 'Test', summary: '',
    };
    const old: Article = {
      title: 'Old', link: 'http://b.com',
      pubDate: new Date(Date.now() - 25 * 60 * 60 * 1000),
      source: 'Test', summary: '',
    };
    expect(filterRecent([recent, old])).toEqual([recent]);
  });
  it('returns empty array when all articles are old', () => {
    const old: Article = {
      title: 'Old', link: 'http://b.com',
      pubDate: new Date(Date.now() - 48 * 60 * 60 * 1000),
      source: 'Test', summary: '',
    };
    expect(filterRecent([old])).toEqual([]);
  });
});

describe('deduplicateByLink', () => {
  it('keeps first article when links are duplicated', () => {
    const a: Article = { title: 'First', link: 'http://x.com', pubDate: new Date(), source: 'S', summary: '' };
    const b: Article = { title: 'Second', link: 'http://x.com', pubDate: new Date(), source: 'S', summary: '' };
    const result = deduplicateByLink([a, b]);
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe('First');
  });
  it('keeps all articles when links are unique', () => {
    const a: Article = { title: 'A', link: 'http://a.com', pubDate: new Date(), source: 'S', summary: '' };
    const b: Article = { title: 'B', link: 'http://b.com', pubDate: new Date(), source: 'S', summary: '' };
    expect(deduplicateByLink([a, b])).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test`

Expected: Several errors like `Cannot find module './index.js'` or `stripHtml is not a function`. Tests must fail before implementation.

- [ ] **Step 3: Create src/index.ts with types and utility functions**

```typescript
import { config } from 'dotenv';
config();

import RSSParser from 'rss-parser';
import nodemailer from 'nodemailer';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';

export interface Article {
  title: string;
  link: string;
  pubDate: Date;
  source: string;
  summary: string;
}

interface FeedConfig {
  name: string;
  url: string;
}

type CustomItem = { contentEncoded?: string };

const FEEDS: FeedConfig[] = [
  { name: 'TechCrunch AI', url: 'https://techcrunch.com/category/artificial-intelligence/feed/' },
  { name: 'The Verge AI', url: 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml' },
  { name: 'Hacker News AI', url: 'https://hnrss.org/newest?q=AI&count=30' },
];

export function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, '').replace(/&[a-z]+;/gi, ' ').trim();
}

export function extractDescription(item: RSSParser.Item & CustomItem): string {
  const raw = item.contentEncoded || item.contentSnippet || item.summary || '';
  return stripHtml(raw).slice(0, 100);
}

export function filterRecent(articles: Article[], hours = 24): Article[] {
  const cutoff = new Date(Date.now() - hours * 60 * 60 * 1000);
  return articles.filter(a => a.pubDate >= cutoff);
}

export function deduplicateByLink(articles: Article[]): Article[] {
  const seen = new Set<string>();
  return articles.filter(a => {
    if (seen.has(a.link)) return false;
    seen.add(a.link);
    return true;
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test`

Expected output:
```
✓ stripHtml > removes HTML tags
✓ stripHtml > handles empty string
✓ stripHtml > replaces HTML entities with a space
✓ extractDescription > truncates to 100 characters
✓ extractDescription > strips HTML tags
✓ extractDescription > returns empty string when no description fields exist
✓ filterRecent > keeps articles within 24 hours
✓ filterRecent > returns empty array when all articles are old
✓ deduplicateByLink > keeps first article when links are duplicated
✓ deduplicateByLink > keeps all articles when links are unique
Test Files  1 passed (1)
Tests  10 passed (10)
```

- [ ] **Step 5: Commit**

```bash
git add src/index.ts src/index.test.ts
git commit -m "feat: add core types and utility functions with tests"
```

---

## Task 3: Markdown Generation (TDD)

**Files:**
- Modify: `src/index.test.ts` (add generateMarkdown tests)
- Modify: `src/index.ts` (add generateMarkdown function)

- [ ] **Step 1: Add failing generateMarkdown tests to src/index.test.ts**

First, update the import line at the top of the file (line 2) to add `generateMarkdown`:

```typescript
import { stripHtml, extractDescription, filterRecent, deduplicateByLink, generateMarkdown } from './index.js';
```

Then append this describe block after the existing `deduplicateByLink` describe block:

```typescript
describe('generateMarkdown', () => {
  const date = '2026-04-21';

  it('includes stats header with article and source counts', () => {
    const map = new Map<string, Article[]>([
      ['TechCrunch AI', [{
        title: 'Test Article', link: 'http://tc.com/1',
        pubDate: new Date('2026-04-21T10:00:00Z'),
        source: 'TechCrunch AI', summary: 'A short summary',
      }]],
    ]);
    const result = generateMarkdown(map, [], date);
    expect(result).toContain('共收录 1 篇，来自 1 个源');
  });

  it('renders article title as markdown link', () => {
    const map = new Map<string, Article[]>([
      ['TechCrunch AI', [{
        title: 'My Article', link: 'http://tc.com/article',
        pubDate: new Date('2026-04-21T10:00:00Z'),
        source: 'TechCrunch AI', summary: '',
      }]],
    ]);
    const result = generateMarkdown(map, [], date);
    expect(result).toContain('[My Article](http://tc.com/article)');
  });

  it('renders article summary as blockquote', () => {
    const map = new Map<string, Article[]>([
      ['TechCrunch AI', [{
        title: 'T', link: 'http://x.com',
        pubDate: new Date('2026-04-21T10:00:00Z'),
        source: 'TechCrunch AI', summary: 'Short summary here',
      }]],
    ]);
    const result = generateMarkdown(map, [], date);
    expect(result).toContain('> Short summary here');
  });

  it('shows no-articles message when map is empty', () => {
    const result = generateMarkdown(new Map(), [], date);
    expect(result).toContain('今日暂无新文章');
  });

  it('appends failed sources at the bottom', () => {
    const result = generateMarkdown(new Map(), ['The Verge AI'], date);
    expect(result).toContain('The Verge AI');
    expect(result).toContain('获取失败');
  });
});
```

- [ ] **Step 2: Run tests to verify generateMarkdown tests fail**

Run: `npm test`

Expected: existing 10 tests still pass, new 5 tests fail with `generateMarkdown is not a function`.

- [ ] **Step 3: Add generateMarkdown to src/index.ts**

Add after the `deduplicateByLink` function:

```typescript
export function generateMarkdown(
  articlesBySource: Map<string, Article[]>,
  failedSources: string[],
  date: string,
): string {
  const allArticles = [...articlesBySource.values()].flat();
  const sourceCount = articlesBySource.size;

  let md = `# AI 新闻日报 · ${date}\n\n`;
  md += `> 共收录 ${allArticles.length} 篇，来自 ${sourceCount} 个源\n\n---\n\n`;

  if (allArticles.length === 0) {
    md += '今日暂无新文章\n';
  } else {
    for (const [source, articles] of articlesBySource) {
      if (articles.length === 0) continue;
      md += `## ${source}\n\n`;
      for (const article of articles) {
        const timeStr = article.pubDate.toISOString().replace('T', ' ').slice(0, 16);
        md += `### [${article.title}](${article.link})\n`;
        md += `**${timeStr}** · ${article.source}\n\n`;
        if (article.summary) {
          md += `> ${article.summary}\n\n`;
        }
        md += '---\n\n';
      }
    }
  }

  if (failedSources.length > 0) {
    md += `\n---\n\n⚠️ 以下源获取失败：${failedSources.join(', ')}\n`;
  }

  return md;
}
```

- [ ] **Step 4: Run tests to verify all 15 pass**

Run: `npm test`

Expected:
```
Test Files  1 passed (1)
Tests  15 passed (15)
```

- [ ] **Step 5: Commit**

```bash
git add src/index.ts src/index.test.ts
git commit -m "feat: add generateMarkdown with tests"
```

---

## Task 4: RSS Fetching + Main Orchestration

**Files:**
- Modify: `src/index.ts` (add fetchFeed, sendEmail, main, ESM guard)

- [ ] **Step 1: Add fetchFeed, sendEmail, and main() to src/index.ts**

Append after the `generateMarkdown` function (before any existing bottom-of-file code):

```typescript
async function fetchFeed(feedConfig: FeedConfig): Promise<Article[]> {
  const parser = new RSSParser<Record<string, never>, CustomItem>({
    customFields: { item: [['content:encoded', 'contentEncoded']] },
  });
  const feed = await parser.parseURL(feedConfig.url);
  return feed.items.map(item => ({
    title: item.title ?? '(无标题)',
    link: item.link ?? '',
    pubDate: new Date(item.pubDate ?? item.isoDate ?? Date.now()),
    source: feedConfig.name,
    summary: extractDescription(item),
  }));
}

async function sendEmail(content: string, subject: string): Promise<void> {
  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.GMAIL_USER,
      pass: process.env.GMAIL_APP_PASSWORD,
    },
  });
  await transporter.sendMail({
    from: process.env.GMAIL_USER,
    to: process.env.RECIPIENT_EMAIL,
    subject,
    text: content,
  });
}

async function main(): Promise<void> {
  const today = new Date().toISOString().slice(0, 10);
  const failedSources: string[] = [];

  const results = await Promise.allSettled(FEEDS.map(f => fetchFeed(f)));

  let allArticles: Article[] = [];
  for (let i = 0; i < results.length; i++) {
    const r = results[i];
    if (r.status === 'fulfilled') {
      allArticles.push(...r.value);
    } else {
      console.error(`[ERROR] Failed to fetch ${FEEDS[i].name}:`, r.reason);
      failedSources.push(FEEDS[i].name);
    }
  }

  allArticles = filterRecent(allArticles);
  allArticles = deduplicateByLink(allArticles);
  allArticles.sort((a, b) => b.pubDate.getTime() - a.pubDate.getTime());

  const successSources = FEEDS.map(f => f.name).filter(n => !failedSources.includes(n));
  const articlesBySource = new Map<string, Article[]>(
    successSources.map(name => [name, allArticles.filter(a => a.source === name)]),
  );

  const markdown = generateMarkdown(articlesBySource, failedSources, today);

  const outputDir = join(process.cwd(), 'output');
  if (!existsSync(outputDir)) mkdirSync(outputDir, { recursive: true });
  const outputPath = join(outputDir, `${today}.md`);
  writeFileSync(outputPath, markdown, 'utf-8');
  console.log(`[OK] Report saved to ${outputPath}`);

  const subject = `AI 新闻日报 · ${today}`;
  try {
    await sendEmail(markdown, subject);
    console.log(`[OK] Email sent to ${process.env.RECIPIENT_EMAIL}`);
  } catch (err) {
    console.error('[ERROR] Email send failed:', err);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `npm test`

Expected: `Tests  15 passed (15)` — adding network functions must not break pure function tests.

- [ ] **Step 3: Create .env from .env.example and fill in real values**

Copy `.env.example` to `.env` and fill in:
- `GMAIL_USER` — your Gmail address
- `GMAIL_APP_PASSWORD` — 16-character App Password from Google Account settings
- `RECIPIENT_EMAIL` — `hubin@jpnelson.com.sg`

- [ ] **Step 4: Manual smoke test — run the script**

Run: `npm start`

Expected console output:
```
[OK] Report saved to C:\...\output\2026-04-21.md
[OK] Email sent to hubin@jpnelson.com.sg
```

Open `output/2026-04-21.md` and verify:
- Header shows `共收录 N 篇，来自 M 个源`
- Articles have titles, links, timestamps, and summaries
- Articles are sorted newest first within each source section

Check inbox at hubin@jpnelson.com.sg for the email.

- [ ] **Step 5: Commit**

```bash
git add src/index.ts
git commit -m "feat: add RSS fetching, email sending, and main orchestration"
```

---

## Task 5: Windows Task Scheduler Setup

**Files:**
- No code changes — configuration only

- [ ] **Step 1: Find the full paths needed for the schtasks command**

Run in PowerShell from the project root:
```powershell
(Get-Command tsx).Source
(Resolve-Path src/index.ts).Path
```

Note the two paths — you will need them in the next step.

- [ ] **Step 2: Register the scheduled task**

Open PowerShell as Administrator and run (replace both paths):

```powershell
schtasks /create `
  /tn "AI News Daily" `
  /tr "node `"C:\FULL\PATH\TO\node_modules\.bin\tsx`" `"C:\FULL\PATH\TO\src\index.ts`"" `
  /sc weekly `
  /d MON,TUE,WED,THU,FRI `
  /st 09:00 `
  /sd 01/01/2026
```

- [ ] **Step 3: Verify the task was registered**

Run: `schtasks /query /tn "AI News Daily" /fo LIST`

Expected output includes:
```
TaskName: \AI News Daily
Status:   Ready
Schedule: Weekly
Days:     Mon, Tue, Wed, Thu, Fri
Start Time: 9:00:00 AM
```

- [ ] **Step 4: Commit final state**

```bash
git add .env.example
git commit -m "docs: add Windows Task Scheduler setup instructions"
```
