# AI Content Creation Agent

I use Claude Code and VS Code to produce tailored YouTube content fast. Claude acts as a thought partner — it asks me clarifying questions before writing anything, and I control every output before it ships.

Built by [Cam Parham](https://www.linkedin.com/in/camparham1/) | [AI & Data Thinking with Cam](https://www.youtube.com/@datathinkingwithcam)

---

## The Core Idea

Most AI writing tools give you generic output. This agent gives you output that matches your exact format, dataset, audience, and SEO strategy — because it's constrained by two guardrail systems before it writes a single word:

1. **`CLAUDE.md`** — a rules file loaded into every session that defines teaching philosophy, SEO rules, title formulas, and which skill file to use for each content type
2. **Skills files** — format contracts that lock the model into a specific structure, word count, dataset, and tone per content type

Without these, Claude improvises. With them, every script follows the same structure as the last one.

---

## 3 Workflows

### Workflow 1 — Automated SQL Curriculum

```bash
python agent.py --auto
```

Runs the next pending topic from a 12-topic beginner SQL curriculum. No manual input required — topic, keyword, audience, and pain point are all read from `curriculum.json`.

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

VS Code opens automatically. Edit the script, press Enter, and it ships to Google Sheets and creates a Google Calendar publish event.

---

### Workflow 2 — SQL One-Off

```bash
python agent.py "SQL GROUP BY"
```

Before researching anything, the agent stops and asks 4 clarifying questions:

```
Let me ask you a few questions to focus the research on 'SQL GROUP BY'...

  What is the primary keyword for this video?
  Your answer: SQL GROUP BY for beginners

  Who is the target audience? (beginner/intermediate/advanced)
  Your answer: beginner

  What platform is this for? (YouTube/TikTok/LinkedIn)
  Your answer: YouTube

  What's the main pain point this video solves?
  Your answer: Don't know how to summarize data by groups
```

These answers get passed directly into the research plan and script prompt. The output is specific to those answers — not a generic SQL tutorial.

Same flow after: research → VS Code → edit → push to Google Sheets.

---

### Workflow 3 — AI Shorts One-Off

For 60-second AI instructional videos, the agent reads `Skills_ai_shorts.md` before writing anything. Same thought-partner step — 6 clarifying questions — then generates a 150-word short-form script with hook, value body, and CTA.

Different skill file = completely different output format, length, and tone.

---

## The Guardrails System

### `CLAUDE.md` — Rules of Engagement

Every Claude Code session loads this file automatically. It defines:

- **Teaching philosophy** — data thinking first, syntax second. Always frame the business question before introducing SQL.
- **SEO rules** — primary keywords in the first 30 seconds, density under 2%, title formula, long-tail keywords in descriptions only
- **Skills routing** — tells Claude which skill file to read before writing any script
- **Hard constraints** — always use the retail dataset, never exceed 6 SQL clauses, always end with the required closing line

This file is why the agent can't freelance. It can't decide to use a different dataset, write a shorter script, or skip the business question framing. The rules are always loaded.

### Skills Files — Format Contracts

| Skill File | Content Type | Format |
|---|---|---|
| `Skills_sql_long-form.md` | SQL tutorials | 400–500 words, HOOK→INTRO→VALUE BODY→CTA, max 4 SQL clauses, retail dataset |
| `Skills_ai_shorts.md` | AI instructional Shorts | 60 sec / ~150 words, one concept only, practical use case |
| `Skills_bigquery_looker.md` | HR analytics tutorials | Up to 15 min, SQL + Looker Studio walkthrough, Meridian Financial Services dataset |

Each skill file contains:
- A dataset reference table (exact table and column names)
- Sample business questions the dataset supports
- The exact script structure with timing
- SEO keywords specific to that content type
- An output checklist Claude must satisfy before returning a result

The agent reads the relevant skill file before generating anything. If the file says 400–500 words, it writes 400–500 words — not 150, not 800.

---

## Human in the Loop

Nothing ships without review. After every generation:

1. The script saves to `output/<topic>.md`
2. The file opens automatically in VS Code
3. The terminal waits with: `Edit the script in VS Code, then press Enter to push to Google Sheets...`
4. You edit anything you want — rewrite the hook, adjust the SQL query, change the CTA
5. Press Enter — the edited version (not the original) gets pushed to Google Sheets

Claude drafts. You approve. The final output is always yours.

---

## Google Sheets as the Content Repository

Google Sheets is the centralized hub where every piece of content lands after the VS Code edit step. Two APIs power this:

- **Google Sheets API v4** via `gspread` + `google-auth` — authenticates with a service account JSON key, opens the sheet by ID, and appends rows to named tabs
- **Google Calendar API** via `google-api-python-client` — same service account credentials, creates an all-day publish event with the script preview in the event description

### Pipeline Tab — metadata per episode

One row per run. This is the editorial dashboard — status, title, thumbnail, and publish date at a glance.

| Column | What's stored |
|---|---|
| # | Episode number (auto-incremented from curriculum) |
| Date Generated | Date the agent ran |
| Topic | e.g. "SQL HAVING Clause" |
| Status | `Draft` — change to `Approved` manually before publishing |
| Title | SEO-optimized YouTube title (from `platform.youtube_title`) |
| Thumbnail Text | Max 5 words (from `platform.thumbnail_text`) |
| Publish Date | User fills in — every 2 days by default |
| Notes | Free text |

### Scripts Tab — full content per episode

One row per run. This is the content library — everything needed to publish a video in one row.

| Column | What's stored |
|---|---|
| # | Episode number |
| Date Generated | Date the agent ran |
| Topic | Topic name |
| Script | Full 400–500 word script — the version you edited in VS Code |
| YouTube Description | Keyword-rich description with → bullet list, CTA, LinkedIn URL, hashtags |
| TikTok | Short punchy copy + hashtags |
| LinkedIn | 4–6 line professional post + hashtags |

### Curriculum Tab — editorial calendar

Populated once on first run from `curriculum.json`. All 12 topics with their SQL concept, business question, SEO keyword, and status (`pending` / `done`). This tab shows exactly where you are in the series at a glance.

### Content Strategy

Before writing the script, the agent generates a content strategy with three fields:

- **Hook** — the specific 1–3 second statement that stops the scroll
- **Value/Body** — what the video teaches step by step, in order
- **CTA** — the exact next action for the viewer

This strategy is what drives the script structure. It's also saved locally to `content-hub.md` alongside every script as a record of the editorial thinking behind each episode.

---

## SQL Curriculum

12 beginner topics in `curriculum.json`, each with a business question, SEO keyword, and status:

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

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
```

| Key | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) — free tier: 1,000 searches/month |
| `GOOGLE_SHEET_ID` | From the URL of your Google Sheet |
| `GOOGLE_CALENDAR_ID` | Your Gmail address |

You also need a Google Cloud service account with Sheets + Calendar APIs enabled. Save the JSON key as `service-account.json` in the project root and share your Sheet with the service account email.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| [Claude Code](https://claude.ai/code) | Development environment + agentic loop |
| [Claude API (Anthropic)](https://anthropic.com) | Script generation + research synthesis |
| [Tavily](https://tavily.com) | Web search for topic research |
| [gspread](https://github.com/burnash/gspread) | Google Sheets API |
| [Google Calendar API](https://developers.google.com/calendar) | Publish schedule |

---

## Project Structure

```
agent.py                  — main agent
CLAUDE.md                 — LLM rules of engagement (loaded every session)
Skills_sql_long-form.md   — format contract for SQL long-form videos
Skills_ai_shorts.md       — format contract for AI Shorts
Skills_bigquery_looker.md — format contract for BigQuery + Looker Studio series
curriculum.json           — 12 SQL topics with status tracking
data/                     — retail SQL dataset (customers, orders, products, order_items)
output/                   — generated scripts open here in VS Code
reports/                  — web research reports
workflow/                 — pipeline documentation
```

---

*Built with Claude Code | AI & Data Thinking with Cam*
