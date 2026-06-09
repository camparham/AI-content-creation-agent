# AI Content Creation Agent

A CLI tool that researches any SQL topic, writes a long-form YouTube script, opens it in VS Code for editing, then pushes the final version to Google Sheets — all from one command.

Built by [Cam Parham](https://www.linkedin.com/in/camparham1/) | [AI & Data Thinking with Cam](https://www.youtube.com/@AIDataThinking)

---

## What It Does

```
python agent.py --auto
```

1. Picks the next SQL topic from a 12-topic curriculum
2. Researches it using Tavily web search (up to 10 queries)
3. Generates a 400–500 word long-form script following `Skills_sql_long-form.md`
4. Opens the script in VS Code so you can edit it before it ships
5. Pushes the edited script + YouTube description to Google Sheets
6. Creates a Google Calendar event for the publish date
7. Marks the topic done and advances the curriculum

---

## Demo

```bash
# Run the next topic in the curriculum automatically
python agent.py --auto

# Run any SQL topic interactively
python agent.py "SQL GROUP BY"

# Prompt for a topic
python agent.py
```

**What you'll see in the terminal:**
```
[Auto] Running topic 8/12: SQL HAVING Clause
[Auto] Progress: 7/12 topics completed

Research plan (10 searches queued):
  1. SQL HAVING clause beginner tutorial
  2. SQL HAVING vs WHERE difference explained
  ...

Researching.......... done.
Generating content drafts... done.

Script saved to: output/sql-having-clause.md

Edit the script in VS Code, then press Enter to push to Google Sheets...
```

**VS Code opens automatically with:**
- YouTube title
- Thumbnail text
- Full script (editable)
- YouTube description
- TikTok and LinkedIn copy

**After you press Enter:**
```
Writing to Google Sheet... done.
Calendar event: https://calendar.google.com/...
[Auto] Marked 'SQL HAVING Clause' as done.
```

---

## Curriculum

12 beginner SQL topics built into `curriculum.json`, each with a business question and SEO keyword:

| # | Topic | Business Question |
|---|---|---|
| 1 | SQL SELECT | Which customers are from Chicago? |
| 2 | SQL WHERE | Which orders were over $50? |
| 3 | SQL ORDER BY | What are our most expensive products? |
| 4 | SQL COUNT | How many orders did we receive this month? |
| 5 | SQL SUM | What was our total revenue last month? |
| 6 | SQL AVG | What is the average order value per customer? |
| 7 | SQL GROUP BY | What is total revenue by product category? |
| 8 | SQL HAVING | Which categories generated over $500? |
| 9 | SQL INNER JOIN | Which customers placed orders and what did they buy? |
| 10 | SQL LEFT JOIN | Which customers have never placed an order? |
| 11 | SQL Subqueries | Which customers spent more than the average? |
| 12 | SQL Window Functions | Who is the top customer by spend in each city? |

---

## Google Sheets Output

Two tabs are written on every run:

**Pipeline tab** — one row per episode:
`# | Date | Topic | Status | Title | Thumbnail | Publish Date | Notes`

**Scripts tab** — full content per episode:
`# | Date | Topic | Script | YouTube Description | TikTok | LinkedIn`

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. API keys

```bash
cp .env.example .env
```

Edit `.env` and add:

| Key | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) — free tier: 1,000 searches/month |
| `GOOGLE_SHEET_ID` | From the URL of your Google Sheet |
| `GOOGLE_CALENDAR_ID` | Your Gmail address |

### 3. Google Sheets service account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable Sheets API + Calendar API
3. Create a service account → download JSON key → save as `service-account.json` in the project root
4. Share your Google Sheet with the service account email

---

## Project Structure

```
agent.py                  — main agent (~750 lines)
curriculum.json           — 12 SQL topics with status tracking
Skills_sql_long-form.md   — script format rules and SEO guidelines
Skills_ai_shorts.md       — AI Shorts format (separate series)
Skills_bigquery_looker.md — BigQuery + Looker Studio series (separate series)
data/                     — retail SQL dataset (customers, orders, products, order_items)
output/                   — generated scripts (gitignored)
reports/                  — research reports (gitignored)
workflow/                 — pipeline documentation
```

---

## Tech Stack

| Tool | Purpose |
|---|---|
| [Claude (Anthropic)](https://anthropic.com) | Script generation + research synthesis |
| [Tavily](https://tavily.com) | Web search for research |
| [gspread](https://github.com/burnash/gspread) | Google Sheets API |
| [Google Calendar API](https://developers.google.com/calendar) | Publish schedule |

---

## Teaching Philosophy

> Data thinking first, syntax second — always start with the business question before writing a single line of SQL.

Every script in this series:
- Opens with a real business question from a retail dataset
- Explains why the naive approach fails before showing the solution
- Walks through each SQL clause in plain English
- Ends with a one-sentence business insight

---

*Built with Claude Code | AI & Data Thinking with Cam*
