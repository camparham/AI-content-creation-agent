# How the Automated Cron → Google Sheets Pipeline Works

## Overview

Every day at 6am ET, your Mac automatically runs the agent, generates a long-form SQL video content package, and pushes it to your Google Sheet — no manual input required.

---

## What Runs and When

| What | Value |
|---|---|
| Schedule | Daily at 6:00am ET (11:00 UTC) |
| Command | `python agent.py --auto` |
| Log file | `cron.log` in project root |

---

## Step-by-Step: What Happens Each Morning

**Step 1 — Cron triggers the script**
Your Mac's cron scheduler wakes up at 6am ET and runs `python agent.py --auto`.

**Step 2 — Agent reads the curriculum**
The script opens `curriculum.json` and finds the first topic where `"status": "pending"`. Topics run in order (1 through 12). Once a topic is marked done, it's skipped forever.

**Step 3 — Clarifications are pulled from the curriculum**
Instead of asking you questions, the agent reads the topic's metadata directly:
- Primary keyword
- Target audience
- Platform
- Pain point

**Step 4 — Web research runs**
The agent uses Tavily to run up to 10 searches on the topic and synthesizes findings into a research report. The report is saved to `reports/`.

**Step 5 — Content package is generated**
Claude generates a complete content package from the research:
- Content strategy
- 400–500 word long-form script (HOOK → INTRO → VALUE BODY → CTA)
- Marketing strategy
- Platform copy (YouTube title, description, TikTok, LinkedIn)

**Step 6 — Content hub is updated**
The content package is appended to `content-hub.md` as a new episode entry.

**Step 7 — Row is pushed to Google Sheets**
A new row is written to your Sheet with these columns:

| Column | Value |
|---|---|
| A | Episode number |
| B | Date (e.g. "May 27") |
| C | Day of week |
| D | "Long-form" |
| E | Topic name |
| F | Content strategy |
| G | Script |
| H | Marketing strategy |
| I | Platform copy |
| J | "Draft" |
| K | (empty — Scheduled Time) |
| L | (empty — Notes) |

**Step 8 — Topic marked done**
The topic's `"status"` is updated to `"done"` in `curriculum.json` so the next run picks the next topic.

---

## How to Review Content Before Publishing

Every row lands in your Sheet with status **"Draft"** (column J). Your review workflow:

1. Open your Google Sheet each morning
2. Read the script in column G
3. When you're happy with it, change column J from `"Draft"` to `"Approved"`
4. Nothing publishes automatically — you control when content goes live

---

## How to Check If It Ran

```bash
cat /Users/cam/Documents/my-first-agent-real/cron.log
```

A successful run ends with:
```
[Auto] Marked 'SQL GROUP BY' as done in curriculum.json
```

---

## How to Check Curriculum Progress

Open `curriculum.json` — each topic shows its current status:
- `"pending"` — not yet run
- `"done"` — completed and pushed to Sheets

---

## How to Run It Manually (Any Time)

```bash
cd /Users/cam/Documents/my-first-agent-real
python agent.py --auto
```

This runs the next pending topic immediately, same as the scheduled run.

---

## Prerequisites for This to Work

| Requirement | Where |
|---|---|
| Mac must be on and awake at 6am | Your machine |
| `ANTHROPIC_API_KEY` set in `.env` | Project root |
| `TAVILY_API_KEY` set in `.env` | Project root |
| `GOOGLE_SHEET_ID` set in `.env` | Project root |
| `service-account.json` present | Project root |
| Google Sheet shared with service account email | Google Sheets |

---

## Troubleshooting

**Nothing appeared in the Sheet**
Check `cron.log` for errors. Common causes:
- Mac was asleep at 6am
- Missing env variable (`GOOGLE_SHEET_ID` not set)
- Service account not shared on the Sheet

**Wrong topic ran**
Check `curriculum.json` — find the topic with `"status": "done"` that shouldn't be, and change it back to `"pending"`.

**All 12 topics are done**
The agent will print `"All curriculum topics are done. Nothing to run."` Add new topics to `curriculum.json` with `"status": "pending"` to continue.
