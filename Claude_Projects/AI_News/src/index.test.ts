import { describe, it, expect } from 'vitest';
import { stripHtml, extractDescription, filterRecent, deduplicateByLink, generateMarkdown } from './index.js';
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
