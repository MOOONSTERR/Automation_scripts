# AI 新闻聚合 CLI 工具 · 设计文档

**日期：** 2026-04-21  
**状态：** 已审批

---

## 概述

一个 TypeScript CLI 工具，每天定时抓取 3 个 RSS 源的最近 24 小时 AI 新闻，生成 Markdown 日报保存到本地，并通过 Gmail SMTP 发送到指定邮箱。

---

## 项目结构

```
AI_News/
├── src/
│   └── index.ts          # 唯一入口，全部逻辑
├── output/               # 生成的 Markdown 日报（按日期命名）
├── .env                  # 敏感配置（不提交 git）
├── .env.example          # 配置示例与说明
├── package.json
└── tsconfig.json
```

---

## 依赖

| 包 | 类型 | 用途 |
|---|---|---|
| `rss-parser` | dependency | 解析 RSS/XML feed |
| `nodemailer` | dependency | Gmail SMTP 发信 |
| `dotenv` | dependency | 加载 .env 环境变量 |
| `tsx` | devDependency | 直接运行 TypeScript |
| `typescript` | devDependency | 类型支持 |
| `@types/nodemailer` | devDependency | nodemailer 类型定义 |

运行命令：`npx tsx src/index.ts`

---

## 环境变量（.env）

```
GMAIL_USER=你的gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
RECIPIENT_EMAIL=hubin@jpnelson.com.sg
```

Gmail App Password 获取方式：Google 账号 → 安全性 → 两步验证 → 应用专用密码。

---

## RSS 源

| 源名称 | URL |
|---|---|
| TechCrunch AI | https://techcrunch.com/category/artificial-intelligence/feed/ |
| The Verge AI | https://www.theverge.com/rss/ai-artificial-intelligence/index.xml |
| Hacker News AI | https://hnrss.org/newest?q=AI&count=30 |

---

## 数据流

```
RSS源(3个) → 并发 fetch → rss-parser 解析
→ 过滤：只保留 pubDate 在 24 小时内的文章
→ 去重：按 link 字段去重
→ 每篇提取：title / link / pubDate / source / description 前100字
→ 按 pubDate 倒序排列
→ 生成 Markdown 文件
→ 发送邮件
```

**description 处理：** 优先取 `content:encoded`，其次取 `description`，去除 HTML 标签后截取前 100 个字符。

---

## 输出格式

**文件名：** `output/YYYY-MM-DD.md`（每次运行覆盖当天文件）

**Markdown 结构：**

```markdown
# AI 新闻日报 · 2026-04-21

> 共收录 18 篇，来自 3 个源

---

## TechCrunch AI

### [文章标题](https://链接)
**2026-04-21 14:30** · TechCrunch AI

> 这里是文章摘要的前100个字符……

---

## The Verge AI

...
```

文章按来源分组，同一来源内按时间倒序排列。

---

## 邮件

- **收件人：** hubin@jpnelson.com.sg
- **发件人：** GMAIL_USER（Gmail SMTP）
- **主题：** `AI 新闻日报 · YYYY-MM-DD`
- **正文：** Markdown 纯文本内容

---

## 错误处理

| 场景 | 处理方式 |
|---|---|
| 单个 RSS 源抓取失败 | 跳过该源，继续处理其余源，日报末尾注明"X 源获取失败" |
| 24小时内无文章 | 生成日报，写明"今日暂无新文章" |
| 邮件发送失败 | 打印错误到 stderr，本地文件已保存，不中断程序 |
| 所有错误 | 输出到 stderr，方便任务计划程序捕获日志 |

---

## Windows 任务计划配置

- **触发时间：** 周一至周五 09:00
- **程序：** `node`
- **参数：** `"C:\path\to\node_modules\.bin\tsx" "C:\path\to\src\index.ts"`
- **起始位置：** 项目根目录

具体配置步骤见 `.env.example`。
