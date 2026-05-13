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
  const user = process.env.GMAIL_USER;
  const pass = process.env.GMAIL_APP_PASSWORD;
  const to = process.env.RECIPIENT_EMAIL;
  if (!user || !pass || !to) {
    throw new Error('Missing required env vars: GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL');
  }
  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: { user, pass },
  });
  await transporter.sendMail({
    from: user,
    to,
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
  main().catch(err => {
    console.error('[FATAL]', err);
    process.exit(1);
  });
}
