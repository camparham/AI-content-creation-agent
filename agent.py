import os
import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient
import gspread
import urllib.request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_SEARCHES = 10
REPORTS_DIR = Path(__file__).parent / "reports"
OUTPUT_DIR = Path(__file__).parent / "output"
MEMORY_FILE = Path(__file__).parent / "memory.json"
CURRICULUM_FILE = Path(__file__).parent / "curriculum.json"
CONTENT_HUB_FILE = Path(__file__).parent / "content-hub.md"
SERVICE_ACCOUNT_FILE = Path(__file__).parent / "service-account.json"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
]

TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information on a topic. "
            "Use specific, targeted queries. Avoid re-searching topics already covered. "
            f"You have a budget of {MAX_SEARCHES} searches total — use them wisely."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string",
                },
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "description": "Use 'advanced' for complex or nuanced topics, 'basic' for factual lookups",
                },
            },
            "required": ["query"],
        },
    }
]


def load_memory() -> list:
    if not MEMORY_FILE.exists():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_to_memory(topic: str, clarifications: dict, search_plan: list, report_path: Path) -> None:
    sessions = load_memory()
    sessions.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "topic": topic,
        "clarifications": clarifications,
        "search_queries": search_plan,
        "report_path": str(report_path),
    })
    MEMORY_FILE.write_text(json.dumps(sessions, indent=2), encoding="utf-8")


def build_system_prompt(
    topic: str,
    clarifications: dict,
    search_plan: list,
    searches_remaining: int,
    past_sessions: list = [],
) -> str:
    clarification_text = "\n".join(f"- {k}: {v}" for k, v in clarifications.items())
    plan_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(search_plan))

    memory_text = ""
    if past_sessions:
        lines = []
        for s in past_sessions[-5:]:
            queries_preview = ", ".join(s.get("search_queries", [])[:3])
            lines.append(f"- {s['date']}: \"{s['topic']}\" — queries included: {queries_preview}")
        memory_text = "\nPRIOR RESEARCH SESSIONS (avoid re-covering the same ground unless asked):\n" + "\n".join(lines) + "\n"

    return f"""You are a thorough research assistant. Your job is to research the topic below, \
synthesize findings from multiple sources, and write a well-structured Markdown report.

TOPIC: {topic}
{memory_text}
RESEARCH CONTEXT (from user):
{clarification_text}

SEARCH PLAN (execute in order, skip if already covered):
{plan_text}

SEARCH BUDGET: You have {searches_remaining} web searches remaining.
When you have gathered enough information or used your budget, stop searching and write the report.

REPORT FORMAT — your final message MUST be a complete Markdown document with these exact sections:

# [Descriptive Title]
**Generated:** {datetime.now().strftime("%Y-%m-%d")}
**Topic:** {topic}

## Executive Summary
(2-3 sentences summarizing the key takeaway)

## Key Findings
(bullet points, one per major finding)

## Detailed Analysis
(subsections as needed, with inline citations)

## Sources
(list every URL you cited as a markdown link)

RULES:
- Cite sources inline as [Source Name](URL)
- Do not repeat searches you have already done
- Be specific and factual, not vague
- Write the report as your FINAL response once research is complete
"""


def load_curriculum() -> list:
    if not CURRICULUM_FILE.exists():
        return []
    return json.loads(CURRICULUM_FILE.read_text(encoding="utf-8"))


def get_next_curriculum_topic() -> dict | None:
    for entry in load_curriculum():
        if entry.get("status") == "pending":
            return entry
    return None


def mark_curriculum_done(topic_id: int) -> None:
    entries = load_curriculum()
    for entry in entries:
        if entry["id"] == topic_id:
            entry["status"] = "done"
            break
    CURRICULUM_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def curriculum_clarifications(entry: dict) -> dict:
    return {
        "What is the primary keyword for this video?": entry["keyword"],
        "Who is the target audience? (beginner/intermediate/advanced)": entry["audience"],
        "What platform is this for? (YouTube/TikTok/LinkedIn)": entry["platform"],
        "What's the main pain point this video solves?": entry["pain_point"],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Research Workflow Agent")
    parser.add_argument("topic", nargs="*", help="Topic to research (interactive mode)")
    parser.add_argument("--auto", action="store_true", help="Run next pending curriculum topic automatically")
    return parser.parse_args()


def get_topic() -> str:
    args = parse_args()
    if args.topic:
        return " ".join(args.topic)
    return input("\nWhat topic would you like me to research? ").strip()


def gather_clarifications(topic: str) -> dict:
    print(f"\nLet me ask you a few questions to focus the research on '{topic}'...\n")

    questions = [
        "What is the primary keyword for this video?",
        "Who is the target audience? (beginner/intermediate/advanced)",
        "What platform is this for? (YouTube/TikTok/LinkedIn)",
        "What's the main pain point this video solves?",
    ]

    clarifications = {}
    for q in questions:
        print(f"  {q}")
        answer = input("  Your answer: ").strip()
        clarifications[q] = answer if answer else "(no preference)"
        print()

    return clarifications


def build_search_plan(
    client: anthropic.Anthropic, topic: str, clarifications: dict
) -> list:
    context = "\n".join(f"- {k}: {v}" for k, v in clarifications.items())

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=600,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Topic: {topic}\n\nResearch context:\n{context}\n\n"
                        f"Generate {MAX_SEARCHES} web search queries to thoroughly research this topic. "
                        "Order them from most to least important. "
                        "Return ONLY a JSON array of query strings, nothing else."
                    ),
                }
            ],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        queries = json.loads(raw)
    except Exception:
        queries = [f"{topic} overview", f"{topic} key facts", f"{topic} recent developments"]

    print(f"\nResearch plan ({len(queries)} searches queued):")
    for i, q in enumerate(queries[:5], 1):
        print(f"  {i}. {q}")
    if len(queries) > 5:
        print(f"  ... and {len(queries) - 5} more")
    print()

    return queries


def run_research_loop(
    client: anthropic.Anthropic,
    tavily: TavilyClient,
    topic: str,
    clarifications: dict,
    search_plan: list,
    past_sessions: list = [],
) -> str:
    searches_used = 0
    messages = [
        {
            "role": "user",
            "content": f"Please research '{topic}' using your search plan and write a comprehensive report. Begin.",
        }
    ]

    print("Researching", end="", flush=True)

    while True:
        system = build_system_prompt(
            topic, clarifications, search_plan, MAX_SEARCHES - searches_used, past_sessions
        )
        active_tools = TOOLS if searches_used < MAX_SEARCHES else []

        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=system,
            tools=active_tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if not tool_calls:
            print(" done.\n")
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return final_text

        tool_results = []
        for tool_call in tool_calls:
            if tool_call.name == "web_search":
                query = tool_call.input.get("query", "")
                depth = tool_call.input.get("search_depth", "basic")
                print(".", end="", flush=True)

                try:
                    result = tavily.search(
                        query=query,
                        search_depth=depth,
                        max_results=5,
                        include_answer=True,
                    )
                    searches_used += 1

                    formatted = f"Search query: {query}\n\n"
                    if result.get("answer"):
                        formatted += f"Summary: {result['answer']}\n\n"
                    for r in result.get("results", []):
                        formatted += f"**{r.get('title', 'Untitled')}**\n"
                        formatted += f"URL: {r.get('url', '')}\n"
                        formatted += f"{r.get('content', '')[:600]}\n\n"

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": formatted,
                        }
                    )
                except Exception as e:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": f"Search failed: {e}",
                            "is_error": True,
                        }
                    )

        messages.append({"role": "user", "content": tool_results})

        if searches_used >= MAX_SEARCHES:
            messages.append(
                {
                    "role": "user",
                    "content": "You have used your full search budget. Please write the final report now using what you have found.",
                }
            )


def save_report(topic: str, report_markdown: str) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^\w\s-]", "", topic.lower())
    slug = re.sub(r"[\s_]+", "-", slug)[:50].strip("-")
    filename = f"{date_str}-{slug}.md"

    path = REPORTS_DIR / filename
    path.write_text(report_markdown, encoding="utf-8")
    return path


CONTENT_SYSTEM_PROMPT = """
You are a YouTube content assistant specializing in SEO optimization for beginner SQL learners.

DATASET: All examples must use a simple retail dataset with these tables:
- customers (customer_id, name, email, city)
- orders (order_id, customer_id, order_date, total_amount)
- products (product_id, name, category, price)
- order_items (order_id, product_id, quantity, unit_price)

DEFAULT RULE: Always use JOINs in SQL examples unless the user explicitly says not to.
Every query should connect at least two tables. Use the retail business questions as the reason
why the JOIN is needed: "Which customers haven't ordered this month?",
"What are our top-selling products?", "Which cities drive the most revenue?" etc.

QUERY TEACHING RULE: Never show a SQL query without step-by-step guidance.
For every query in every script, follow this exact pattern:
1. State the business question in plain English
2. Explain why the naive approach fails or is insufficient
3. Show the full SQL query in a code block
4. Explain each key clause in plain English — what it does and why it's there
5. State the business insight the result gives in one sentence

When writing scripts and descriptions:
- Use high-volume keywords naturally (SQL tutorial, SQL for beginners, data analytics, learn SQL, retail dataset)
- Place primary keywords in the first 30 seconds of scripts
- Keep keyword density under 2%
- Write for search intent first, creativity second
- Always write for beginner data analysts and SQL learners
"""


def generate_content_drafts(client: anthropic.Anthropic, topic: str, report: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=CONTENT_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Generate a complete content package for a micro-learning SQL video about: '{topic}'\n\n"
                    f"REPORT:\n{report[:3000]}\n\n"
                    "STEP 0 — viral research: Analyze the top 5 viral YouTube videos on this topic. Identify:\n"
                    "- Title structures and primary keywords used\n"
                    "- Hook patterns in the first 30 seconds\n"
                    "- Common CTA structures\n"
                    "Apply those patterns to everything you write below.\n\n"
                    "Follow this process in order and return a JSON object with these exact keys:\n\n"
                    "1. content_strategy — Write a specific content strategy for this topic using this framework:\n"
                    "   Hook: A 1-3 second hook specific to this topic that stops the scroll. Bold statement, surprising fact, or direct promise of value.\n"
                    "   Value/Body: What this video teaches step by step. Every point should teach, entertain, or build toward the payoff.\n"
                    "   CTA: A specific call to action telling the viewer exactly what to do next.\n\n"
                    "2. script — Using the content_strategy above, write a ~400-500 word long-form video script (3:30-5 min). "
                    "Structure: HOOK (5-10 sec) → INTRO (frame the business question, 20-30 sec) → VALUE BODY (2:30-3:30) → CTA (20-30 sec). "
                    "Place the primary keyword in the first 30 seconds. Business question first, syntax second.\n\n"
                    "VALUE BODY rules — for each SQL query in the script:\n"
                    "  1. State the business question in plain English first\n"
                    "  2. Explain WHY the naive approach (e.g. GROUP BY) fails or is limiting\n"
                    "  3. Show the full SQL query in a code block\n"
                    "  4. Walk through each key clause in plain English — what it does and why it matters\n"
                    "  5. State the business insight the result gives you in one sentence\n"
                    "  Repeat this pattern for each query. Never show a query without explaining it line by line.\n\n"
                    "End with: 'I'm Cam, your upskilling and reskilling coach, don't forget to subscribe for more AI and data help!'\n\n"
                    "3. marketing_strategy — Write a platform-specific marketing strategy:\n"
                    "   YouTube: How to position this for search and retention\n"
                    "   TikTok: Hook angle and hashtag strategy for short-form\n"
                    "   LinkedIn: Professional framing for a data/analytics audience\n\n"
                    "4. platform — Using the marketing_strategy above, return a JSON object with these exact keys:\n"
                    "   youtube_title: SEO title under 70 chars, includes primary keyword\n"
                    "   youtube_description: full YouTube description with keyword-rich opener, → bullet list of what's covered, business questions answered, CTA, 'www.linkedin.com/in/camparham1/', hashtags\n"
                    "   tiktok: title line + 2-3 punchy sentences + hashtags\n"
                    "   linkedin: 4-6 lines, punchy opener, context lines, '🎬 Link in comments', hashtags\n"
                    "   thumbnail_text: max 5 words, readable at mobile size\n\n"
                    "Return ONLY valid JSON with keys: content_strategy, script, marketing_strategy, platform\n"
                    "The platform value must itself be a JSON object with keys: youtube_title, youtube_description, tiktok, linkedin, thumbnail_text"
                ),
            }
        ],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)


def submit_to_heygen(script: str) -> str:
    api_key = os.getenv("HEYGEN_API_KEY")
    avatar_id = os.getenv("HEYGEN_AVATAR_ID")
    voice_id = os.getenv("HEYGEN_VOICE_ID")

    if not all([api_key, avatar_id, voice_id]):
        raise ValueError("HEYGEN_API_KEY, HEYGEN_AVATAR_ID, and HEYGEN_VOICE_ID must be set in .env")

    payload = json.dumps({
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": voice_id
                }
            }
        ],
        "dimension": {"width": 1280, "height": 720}
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.heygen.com/v2/video/generate",
        data=payload,
        headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    video_id = result.get("data", {}).get("video_id")
    if not video_id:
        raise ValueError(f"HeyGen did not return a video_id: {result}")

    return f"https://app.heygen.com/videos/{video_id}"


def append_to_content_hub(topic: str, drafts: dict) -> None:
    existing = CONTENT_HUB_FILE.read_text(encoding="utf-8") if CONTENT_HUB_FILE.exists() else ""

    episode_count = len(re.findall(r"^## Episode \d+", existing, re.MULTILINE))
    next_episode = episode_count + 1

    block = f"""
## Episode {next_episode} — {topic}

### Content Strategy

{drafts.get('content_strategy', '')}

---

### Script

> {drafts.get('script', '').replace(chr(10), chr(10) + '> ')}

---

### Marketing Strategy

{drafts.get('marketing_strategy', '')}

---

### Platform Copy

{drafts.get('platform', '')}

---
---
"""

    if CONTENT_HUB_FILE.exists():
        content = CONTENT_HUB_FILE.read_text(encoding="utf-8")
        # Insert after the header block (first ---) so newest episodes appear at top
        insert_at = content.find("\n---\n") + 5
        updated = content[:insert_at] + block + content[insert_at:]
    else:
        updated = f"# SQL Upskilling Content Hub\n\n---\n{block}"

    CONTENT_HUB_FILE.write_text(updated, encoding="utf-8")


def to_cell(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n\n".join(f"{k.upper().replace('_', ' ')}: {to_cell(v)}" for k, v in value.items())
    if isinstance(value, list):
        return "\n".join(f"- {to_cell(i)}" for i in value)
    return str(value)


def get_or_create_worksheet(spreadsheet, name: str, rows: int = 1000, cols: int = 20):
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)


def setup_sheet(spreadsheet) -> None:
    pipeline = get_or_create_worksheet(spreadsheet, "Pipeline")
    if not pipeline.row_values(1):
        pipeline.append_row([
            "#", "Date Generated", "Topic", "Status", "Title",
            "Thumbnail Text", "Publish Date", "Notes"
        ])

    scripts = get_or_create_worksheet(spreadsheet, "Scripts")
    if not scripts.row_values(1):
        scripts.append_row([
            "#", "Date Generated", "Topic", "Script",
            "YouTube Description", "TikTok", "LinkedIn"
        ])


def create_calendar_event(topic: str, title: str, publish_date: str, script_summary: str) -> str:
    """Create a Google Calendar event for a scheduled video publish.
    publish_date format: YYYY-MM-DD
    Returns the event URL.
    """
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_FILE), scopes=GOOGLE_SCOPES)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": f"🎬 Publish: {title}",
        "description": (
            f"Topic: {topic}\n\n"
            f"Script preview:\n{script_summary[:500]}...\n\n"
            f"Status: Draft\n"
            f"Channel: AI & Data Thinking with Cam"
        ),
        "start": {"date": publish_date},
        "end": {"date": publish_date},
        "colorId": "2",  # Sage green
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},   # 1 day before
                {"method": "popup", "minutes": 60},         # 1 hour before
            ],
        },
    }

    result = service.events().insert(calendarId=calendar_id, body=event).execute()
    return result.get("htmlLink", "")


def write_to_sheet(topic: str, drafts: dict, episode_num: int, heygen_url: str = "") -> None:
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("  Skipping sheet — GOOGLE_SHEET_ID not set in .env")
        return

    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_FILE), scopes=GOOGLE_SCOPES)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(sheet_id)
    setup_sheet(spreadsheet)

    today = datetime.now().strftime("%b %-d")
    platform = drafts.get("platform", {})
    if isinstance(platform, str):
        platform = {}

    title = platform.get("youtube_title", topic)
    thumbnail = platform.get("thumbnail_text", "")
    youtube_desc = platform.get("youtube_description", "")
    tiktok = platform.get("tiktok", "")
    linkedin = platform.get("linkedin", "")
    script = to_cell(drafts.get("script", ""))

    pipeline = spreadsheet.worksheet("Pipeline")
    pipeline.append_row([
        episode_num,
        today,
        topic,
        "Draft",
        title,
        thumbnail,
        "",   # Publish Date — user fills in
        "",   # Notes
    ])

    scripts = spreadsheet.worksheet("Scripts")
    scripts.append_row([
        episode_num,
        today,
        topic,
        script,
        youtube_desc,
        tiktok,
        linkedin,
    ])


def save_script_for_editing(topic: str, drafts: dict) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^\w\s-]", "", topic.lower())
    slug = re.sub(r"[\s_]+", "-", slug)[:50].strip("-")
    path = OUTPUT_DIR / f"{slug}.md"
    platform = drafts.get("platform", {}) if isinstance(drafts.get("platform"), dict) else {}
    content = f"# {platform.get('youtube_title', topic)}\n\n"
    content += f"**Thumbnail:** {platform.get('thumbnail_text', '')}\n\n"
    content += f"---\n\n## SCRIPT\n\n{drafts.get('script', '')}\n\n"
    content += f"---\n\n## YOUTUBE DESCRIPTION\n\n{platform.get('youtube_description', '')}\n\n"
    content += f"---\n\n## TIKTOK\n\n{platform.get('tiktok', '')}\n\n"
    content += f"---\n\n## LINKEDIN\n\n{platform.get('linkedin', '')}\n"
    path.write_text(content, encoding="utf-8")
    return path


def read_script_from_file(path: Path, drafts: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## SCRIPT\n\n(.*?)\n\n---", text, re.DOTALL)
    if match:
        drafts = dict(drafts)
        drafts["script"] = match.group(1).strip()
    return drafts


def main():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not anthropic_key or not tavily_key:
        print("Error: ANTHROPIC_API_KEY and TAVILY_API_KEY must be set in .env")
        print("Copy .env.example to .env and fill in your keys.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=anthropic_key)
    tavily = TavilyClient(api_key=tavily_key)

    args = parse_args()
    auto_mode = args.auto

    if auto_mode:
        entry = get_next_curriculum_topic()
        if not entry:
            print("All curriculum topics are done. Nothing to run.")
            sys.exit(0)

        total = len(load_curriculum())
        done = sum(1 for e in load_curriculum() if e["status"] == "done")
        print(f"\n[Auto] Running topic {entry['id']}/{total}: {entry['topic']}")
        print(f"[Auto] Progress: {done}/{total} topics completed\n")

        topic = entry["topic"]
        clarifications = curriculum_clarifications(entry)
    else:
        topic = get_topic()
        if not topic:
            print("No topic provided. Exiting.")
            sys.exit(1)

        past_sessions = load_memory()
        if past_sessions:
            print(f"\n(Memory: {len(past_sessions)} prior session(s) loaded)")

        clarifications = gather_clarifications(topic)

    past_sessions = load_memory()
    search_plan = build_search_plan(client, topic, clarifications)

    print("Starting research...\n")
    report = run_research_loop(client, tavily, topic, clarifications, search_plan, past_sessions)

    path = save_report(topic, report)
    save_to_memory(topic, clarifications, search_plan, path)
    print(f"Report saved to: {path}")
    print(f"Word count: ~{len(report.split()):,}")

    if auto_mode:
        print("Generating content drafts...", end="", flush=True)
        try:
            drafts = generate_content_drafts(client, topic, report)
            append_to_content_hub(topic, drafts)
            episode_count = sum(1 for e in load_curriculum() if e["status"] == "done")
            print(" done.")

            script_path = save_script_for_editing(topic, drafts)
            print(f"\nScript saved to: {script_path}")
            import subprocess
            vscode = "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
            subprocess.Popen([vscode, str(script_path)])
            input("\nEdit the script in VS Code, then press Enter to push to Google Sheets...")

            drafts = read_script_from_file(script_path, drafts)
            print("Writing to Google Sheet...", end="", flush=True)
            write_to_sheet(topic, drafts, episode_count, "")
            print(" done.")

            try:
                platform = drafts.get("platform", {})
                title = (platform.get("youtube_title", "") if isinstance(platform, dict) else "") or topic
                from datetime import timedelta
                publish_date = (datetime.now() + timedelta(days=1 + (episode_count - 1) * 2)).strftime("%Y-%m-%d")
                event_url = create_calendar_event(topic, title, publish_date, to_cell(drafts.get("script", "")))
                print(f"Calendar event: {event_url}")
            except Exception as e:
                print(f"Calendar failed: {e}")

            mark_curriculum_done(entry["id"])
            print(f"[Auto] Marked '{topic}' as done.")
        except Exception as e:
            import traceback
            print(f"\n[Error] {e}")
            traceback.print_exc()
    else:
        add_to_hub = input("\nGenerate content drafts? (y/n): ").strip().lower()
        if add_to_hub == "y":
            print("Generating content drafts...", end="", flush=True)
            try:
                drafts = generate_content_drafts(client, topic, report)
                append_to_content_hub(topic, drafts)
                episode_count = sum(1 for e in load_curriculum() if e["status"] == "done")
                print(" done.")

                script_path = save_script_for_editing(topic, drafts)
                print(f"\nScript saved to: {script_path}")
                import subprocess
                subprocess.Popen(["code", str(script_path)])
                input("\nEdit the script in VS Code, then press Enter to push to Google Sheets...")

                drafts = read_script_from_file(script_path, drafts)
                print("Writing to Google Sheet...", end="", flush=True)
                write_to_sheet(topic, drafts, episode_count, "")
                print(" done.")
            except Exception as e:
                import traceback
                print(f"\n[Error] {e}")
                traceback.print_exc()


if __name__ == "__main__":
    main()
