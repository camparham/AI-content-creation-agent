# Camai — AI Content Creation App

A browser-based content research and script generation tool. Works for any topic — not just SQL. Once launched, everything happens in your browser; no terminal interaction needed.

## How this differs from `my-first-agent-real`

| | `my-first-agent-real` | Camai (`PR_1/v2`) |
|---|---|---|
| Interface | CLI — answer prompts in terminal | Web app — fill out forms in browser |
| Topic scope | SQL curriculum focused | Any topic (YouTube, TikTok, LinkedIn, etc.) |
| How to run | `python agent.py` | `streamlit run app.py` |
| Editing drafts | Opens VS Code, edit file manually | Edit directly in the browser before publishing |
| Publishing | Always pushes to Google Sheets | Optional — confirm in browser before pushing |

## Setup

```bash
pip install -r requirements.txt
# Add your API keys to a .env file:
# ANTHROPIC_API_KEY
# TAVILY_API_KEY
# GOOGLE_SHEET_ID (optional)
# GOOGLE_CALENDAR_ID (optional)
```

## Usage

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`) in your browser.

## Workflow (all in browser)

1. **Brief** — Enter your topic and fill in 5 fields: keyword, audience, platform, format, and goal
2. **Research** — Agent searches the web and generates a research report
3. **Drafts** — Review and edit your script, platform copy, and marketing strategy in the browser
4. **Publish** — Push finalized drafts to Google Sheets and optionally create a Google Calendar event
