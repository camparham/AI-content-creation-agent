import os
import sys
import json
import re
import argparse
import shutil
import subprocess
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient
import gspread
import urllib.request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-4-6"
MODEL = DEFAULT_MODEL  # kept for any external code importing the old name

# Used only if a live models.list() call fails (no key yet, offline, older API version).
# The UI always prefers the live list from the user's own API key so this rarely matters.
FALLBACK_MODELS = [
    {"id": "claude-sonnet-4-6", "display_name": "Claude Sonnet 4.6"},
    {"id": "claude-opus-4-1", "display_name": "Claude Opus 4.1"},
    {"id": "claude-haiku-4-5", "display_name": "Claude Haiku 4.5"},
]
MAX_SEARCHES = 10
ROOT = Path(__file__).parent
REPORTS_DIR = ROOT / "reports"
OUTPUT_DIR = ROOT / "output"
MEMORY_FILE = ROOT / "memory.json"  # legacy; migrated into report frontmatter on read
QUEUE_FILE = ROOT / "queue.json"
SERVICE_ACCOUNT_FILE = ROOT / "service-account.json"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
]

CLARIFICATION_QUESTIONS = [
    "What is the primary keyword or search phrase?",
    "Who is your target audience?",
    "What platform is this for? (YouTube, TikTok, Instagram, LinkedIn, etc.)",
    "What content format? (short-form video, long-form video, carousel, blog, newsletter)",
    "What is the main goal or pain point this piece should address?",
    "Example/template to match the tone and style of (optional)",
]

TONE_EXAMPLE_QUESTION = CLARIFICATION_QUESTIONS[5]

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
                "query": {"type": "string", "description": "The search query string"},
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "description": "Use 'advanced' for complex topics, 'basic' for factual lookups",
                },
            },
            "required": ["query"],
        },
    }
]


OUTPUT_LENGTH_PRESETS = {
    "brief": {
        "label": "Brief",
        "word_range": "800-1200",
        "max_tokens": 3000,
        "report_excerpt_chars": 2500,
        "draft_max_tokens": 4000,
    },
    "normal": {
        "label": "Normal",
        "word_range": "1500-2000",
        "max_tokens": 5000,
        "report_excerpt_chars": 5000,
        "draft_max_tokens": 6000,
    },
    "long": {
        "label": "Long",
        "word_range": "2500-3500",
        "max_tokens": 8000,
        "report_excerpt_chars": 8000,
        "draft_max_tokens": 8000,
    },
    "extended": {
        "label": "Extended",
        "word_range": "3500-5000",
        "max_tokens": 16000,
        "report_excerpt_chars": 12000,
        "draft_max_tokens": 12000,
    },
}


def output_length_config() -> dict:
    key = os.getenv("OUTPUT_LENGTH", "normal").strip().lower()
    if key not in OUTPUT_LENGTH_PRESETS:
        key = "normal"
    return {"key": key, **OUTPUT_LENGTH_PRESETS[key]}


def creator_config() -> dict:
    return {
        "creator_name": os.getenv("CREATOR_NAME", "").strip(),
        "channel_name": os.getenv("CHANNEL_NAME", "Content Channel").strip(),
        "linkedin_url": os.getenv("LINKEDIN_URL", "").strip(),
    }


def format_sheet_date() -> str:
    now = datetime.now()
    return f"{now.strftime('%b')} {now.day}"


def slugify(text: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug)[:max_len].strip("-")
    return slug or "content"


def parse_json_response(raw: str):
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return json.loads(raw)


def parse_report_file(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    try:
        meta = json.loads(text[4:end])
    except json.JSONDecodeError:
        return {}, text
    return meta, text[end + 5 :].lstrip()


def compose_report_file(meta: dict, body: str) -> str:
    return f"---\n{json.dumps(meta, indent=2)}\n---\n\n{body.lstrip()}"


def topic_from_report_path(path: Path) -> str:
    stem = path.stem
    if len(stem) >= 11 and stem[10] == "-":
        return stem[11:].replace("-", " ")
    return stem.replace("-", " ")


def migrate_legacy_memory() -> None:
    """One-time migration: merge memory.json metadata into report frontmatter."""
    if not MEMORY_FILE.exists():
        return

    try:
        sessions = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return

    for session in sessions:
        path = Path(session.get("report_path", ""))
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        meta, body = parse_report_file(text)
        if meta:
            continue
        meta = {
            "date": session.get("date", datetime.now().strftime("%Y-%m-%d")),
            "topic": session.get("topic", topic_from_report_path(path)),
            "clarifications": session.get("clarifications", {}),
            "search_queries": session.get("search_queries", []),
        }
        path.write_text(compose_report_file(meta, body), encoding="utf-8")

    MEMORY_FILE.unlink(missing_ok=True)


def load_all_report_sessions() -> list[dict]:
    """Return report metadata oldest-first (replaces memory.json)."""
    migrate_legacy_memory()
    if not REPORTS_DIR.exists():
        return []

    items = []
    for path in REPORTS_DIR.glob("*.md"):
        meta, _ = parse_report_file(path.read_text(encoding="utf-8"))
        items.append({
            "date": meta.get("date", path.name[:10] if len(path.name) >= 10 else ""),
            "topic": meta.get("topic", topic_from_report_path(path)),
            "clarifications": meta.get("clarifications", {}),
            "search_queries": meta.get("search_queries", []),
            "report_path": path,
        })

    items.sort(key=lambda item: (item["date"], item["topic"]))
    return items


def list_report_history() -> list[dict]:
    """Return saved reports, newest first."""
    sessions = load_all_report_sessions()
    return list(reversed(sessions))


def load_report(path: Path) -> str:
    _, body = parse_report_file(path.read_text(encoding="utf-8"))
    return body


def load_report_record(path: Path) -> dict:
    meta, body = parse_report_file(path.read_text(encoding="utf-8"))
    return {
        "date": meta.get("date", path.name[:10] if len(path.name) >= 10 else ""),
        "topic": meta.get("topic", topic_from_report_path(path)),
        "clarifications": meta.get("clarifications", {}),
        "search_queries": meta.get("search_queries", []),
        "report_path": path,
        "report": body,
    }


def build_system_prompt(
    topic: str,
    clarifications: dict,
    search_plan: list,
    searches_remaining: int,
    past_sessions: list | None = None,
) -> str:
    past_sessions = past_sessions or []
    length = output_length_config()
    context_only, _ = split_tone_example(clarifications)
    clarification_text = "\n".join(f"- {k}: {v}" for k, v in context_only.items())
    plan_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(search_plan))

    memory_text = ""
    if past_sessions:
        lines = []
        for session in past_sessions[-5:]:
            preview = ", ".join(session.get("search_queries", [])[:3])
            lines.append(f"- {session['date']}: \"{session['topic']}\" — queries included: {preview}")
        memory_text = (
            "\nPRIOR RESEARCH SESSIONS (avoid re-covering the same ground unless asked):\n"
            + "\n".join(lines)
            + "\n"
        )

    return f"""You are a thorough research assistant for content creators. Research the topic below, \
synthesize findings from multiple sources, and write a well-structured Markdown report.

TOPIC: {topic}
{memory_text}
CREATOR CONTEXT:
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

## Content Angles
(3-5 angles a creator could turn into videos, posts, or newsletters)

## Sources
(list every URL you cited as a markdown link)

RULES:
- Target length: {length["word_range"]} words for the full report ({length["max_tokens"]} token budget)
- Complete every section above before finishing — do not stop mid-section
- Cite sources inline as [Source Name](URL)
- Do not repeat searches you have already done
- Be specific and factual, not vague
- Write the report as your FINAL response once research is complete — no preamble
"""


def load_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))


def get_next_queue_item() -> dict | None:
    for entry in load_queue():
        if entry.get("status") == "pending":
            return entry
    return None


def mark_queue_done(item_id: int) -> None:
    entries = load_queue()
    for entry in entries:
        if entry["id"] == item_id:
            entry["status"] = "done"
            break
    QUEUE_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def queue_clarifications(entry: dict) -> dict:
    mapping = {
        CLARIFICATION_QUESTIONS[0]: entry.get("keyword", entry.get("topic", "")),
        CLARIFICATION_QUESTIONS[1]: entry.get("audience", "general audience"),
        CLARIFICATION_QUESTIONS[2]: entry.get("platform", "YouTube"),
        CLARIFICATION_QUESTIONS[3]: entry.get("format", "long-form video"),
        CLARIFICATION_QUESTIONS[4]: entry.get("goal", entry.get("pain_point", "Educate the audience")),
        CLARIFICATION_QUESTIONS[5]: entry.get("example", "(no preference)"),
    }
    return mapping


def parse_args():
    parser = argparse.ArgumentParser(
        description="Topic-agnostic content research and draft agent for creators"
    )
    parser.add_argument("topic", nargs="*", help="Topic to research")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run the next pending item from queue.json",
    )
    return parser.parse_args()


def get_topic(args) -> str:
    if args.topic:
        return " ".join(args.topic)
    return input("\nWhat topic would you like to create content about? ").strip()


def gather_clarifications(topic: str) -> dict:
    print(f"\nA few questions to focus content for '{topic}'...\n")
    clarifications = {}
    for question in CLARIFICATION_QUESTIONS:
        print(f"  {question}")
        answer = input("  Your answer: ").strip()
        clarifications[question] = answer if answer else "(no preference)"
        print()
    return clarifications


def build_search_plan(
    client: anthropic.Anthropic, topic: str, clarifications: dict, model: str = DEFAULT_MODEL
) -> list:
    context_only, _ = split_tone_example(clarifications)
    context = "\n".join(f"- {k}: {v}" for k, v in context_only.items())
    try:
        response = client.messages.create(
            model=model,
            max_tokens=600,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Topic: {topic}\n\nCreator context:\n{context}\n\n"
                        f"Generate {MAX_SEARCHES} web search queries to research this topic for content creation. "
                        "Include audience intent, trends, competitor angles, and platform-specific hooks where useful. "
                        "Order from most to least important. "
                        "Return ONLY a JSON array of query strings, nothing else."
                    ),
                }
            ],
        )
        queries = parse_json_response(response.content[0].text)
    except Exception:
        queries = [
            f"{topic} content ideas",
            f"{topic} audience questions",
            f"{topic} trends",
        ]

    print(f"\nResearch plan ({len(queries)} searches queued):")
    for i, query in enumerate(queries[:5], 1):
        print(f"  {i}. {query}")
    if len(queries) > 5:
        print(f"  ... and {len(queries) - 5} more")
    print()
    return queries


def get_clients() -> tuple[anthropic.Anthropic, TavilyClient]:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not anthropic_key or not tavily_key:
        raise RuntimeError("ANTHROPIC_API_KEY and TAVILY_API_KEY must be set in .env")
    return anthropic.Anthropic(api_key=anthropic_key), TavilyClient(api_key=tavily_key)


def list_available_models() -> dict:
    """Fetch models the caller's own API key can currently bill against.

    Queries Anthropic's /v1/models endpoint live instead of hardcoding a list, so
    new/retired models show up automatically without a code change. Falls back to
    FALLBACK_MODELS if the key is missing, the call fails, or the installed SDK
    doesn't support it yet — callers can check "live" to tell the user which case
    they're in.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return {"models": FALLBACK_MODELS, "live": False}

    try:
        client = anthropic.Anthropic(api_key=anthropic_key)
        page = client.models.list(limit=100)
        models = [{"id": m.id, "display_name": m.display_name or m.id} for m in page.data]
        if not models:
            return {"models": FALLBACK_MODELS, "live": False}
        return {"models": models, "live": True}
    except Exception:
        return {"models": FALLBACK_MODELS, "live": False}


def env_status() -> dict:
    length = output_length_config()
    return {
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "tavily": bool(os.getenv("TAVILY_API_KEY")),
        "google_sheet": bool(os.getenv("GOOGLE_SHEET_ID")),
        "google_calendar": bool(os.getenv("GOOGLE_CALENDAR_ID")),
        "service_account": SERVICE_ACCOUNT_FILE.exists(),
        "output_length": length["label"],
        "output_word_range": length["word_range"],
        "output_max_tokens": length["max_tokens"],
    }


def run_research_loop(
    client: anthropic.Anthropic,
    tavily: TavilyClient,
    topic: str,
    clarifications: dict,
    search_plan: list,
    past_sessions: list | None = None,
    on_search: Callable[[str, int, int], None] | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    past_sessions = past_sessions or []
    searches_used = 0
    messages = [
        {
            "role": "user",
            "content": (
                f"Please research '{topic}' using your search plan and write a comprehensive report. Begin."
            ),
        }
    ]

    print("Researching", end="", flush=True)

    while True:
        system = build_system_prompt(
            topic, clarifications, search_plan, MAX_SEARCHES - searches_used, past_sessions
        )
        active_tools = TOOLS if searches_used < MAX_SEARCHES else []

        response = client.messages.create(
            model=model,
            max_tokens=output_length_config()["max_tokens"],
            system=system,
            tools=active_tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            print(" done.\n")
            return next((block.text for block in response.content if hasattr(block, "text")), "")

        tool_results = []
        for tool_call in tool_calls:
            if tool_call.name != "web_search":
                continue

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
                if on_search:
                    on_search(query, searches_used, MAX_SEARCHES)

                formatted = f"Search query: {query}\n\n"
                if result.get("answer"):
                    formatted += f"Summary: {result['answer']}\n\n"
                for item in result.get("results", []):
                    formatted += f"**{item.get('title', 'Untitled')}**\n"
                    formatted += f"URL: {item.get('url', '')}\n"
                    formatted += f"{item.get('content', '')[:600]}\n\n"

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": formatted,
                    }
                )
            except Exception as exc:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": f"Search failed: {exc}",
                        "is_error": True,
                    }
                )

        messages.append({"role": "user", "content": tool_results})

        if searches_used >= MAX_SEARCHES:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You have used your full search budget. "
                        "Please write the final report now using what you have found."
                    ),
                }
            )


def save_report(
    topic: str,
    report_markdown: str,
    clarifications: dict,
    search_plan: list,
) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}-{slugify(topic)}.md"
    meta = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "topic": topic,
        "clarifications": clarifications,
        "search_queries": search_plan,
    }
    path.write_text(compose_report_file(meta, report_markdown), encoding="utf-8")
    return path


def split_tone_example(clarifications: dict) -> tuple[dict, str]:
    """Pull the tone/template example out of the clarifications dict.

    It needs separate handling because it's free-form prose (not a short
    answer), so dumping it into the one-line-per-question context block
    would truncate or mangle it.
    """
    context = dict(clarifications)
    example = context.pop(TONE_EXAMPLE_QUESTION, "")
    if not example or example.strip() in ("", "(no preference)"):
        return context, ""
    return context, example.strip()


def build_content_system_prompt(clarifications: dict) -> str:
    config = creator_config()
    creator_line = ""
    if config["creator_name"]:
        creator_line = f"The creator's name is {config['creator_name']}. "

    context, tone_example = split_tone_example(clarifications)
    context_text = "\n".join(f"- {k}: {v}" for k, v in context.items())

    tone_block = ""
    if tone_example:
        tone_block = f"""
TONE & TEMPLATE EXAMPLE:
The creator supplied the example below. Study its tone, voice, pacing, and structure,
and closely mirror them in your writing. Do not copy its subject matter or specific
phrases — only match the style and format.
\"\"\"
{tone_example}
\"\"\"
"""

    return f"""You are a content strategist and scriptwriter for digital creators across any niche.

{creator_line}Adapt tone, structure, and examples to the creator context below. Do not assume any specific
subject matter, dataset, or industry unless the context calls for it.

CREATOR CONTEXT:
{context_text}
{tone_block}
WRITING RULES:
- Match the requested platform and format exactly
- Lead with audience value, not jargon
- Place the primary keyword naturally in the opening when writing video scripts
- Keep keyword density under 2%
- Use clear hooks, structured value, and a specific CTA
- Write for search intent and retention first
- Never invent facts that are not supported by the research report
"""


def build_content_user_prompt(topic: str, report: str, clarifications: dict) -> str:
    config = creator_config()
    sign_off = ""
    if config["creator_name"]:
        sign_off = (
            f"\nEnd the script with a natural sign-off from {config['creator_name']} "
            "and a subscribe/follow CTA appropriate to the platform.\n"
        )

    linkedin_note = ""
    if config["linkedin_url"]:
        linkedin_note = f"\nInclude this link in the YouTube description when relevant: {config['linkedin_url']}\n"

    context_only, _ = split_tone_example(clarifications)
    context = "\n".join(f"- {k}: {v}" for k, v in context_only.items())
    length = output_length_config()
    return f"""Generate a complete content package for: '{topic}'

RESEARCH REPORT:
{report[: length["report_excerpt_chars"]]}

CREATOR CONTEXT:
{context}

STEP 0 — study what performs on the target platform for this topic. Identify:
- Title/thumbnail patterns
- Hook patterns in the first few seconds or opening lines
- Common CTA structures

Apply those patterns to everything below.

Return a JSON object with these exact keys:

1. content_strategy
   - Hook: scroll-stopping opener for this topic and platform
   - Value/Body: what the piece teaches or delivers, step by step
   - CTA: one clear next action for the audience

2. script
   Write the primary deliverable for the requested format:
   - short-form video: ~120-180 words, one core idea, fast pacing
   - long-form video: ~400-600 words, HOOK → INTRO → VALUE BODY → CTA
   - carousel/blog/newsletter: sectioned copy with strong headings
   Match the platform named in the creator context.
{sign_off}

3. marketing_strategy
   Platform-specific promotion notes for the primary platform plus repurposing ideas
   for at least one secondary platform.

4. platform
   A JSON object with these keys:
   - primary_title: title/headline under 70 characters when possible
   - primary_description: full description/caption for the main platform
   - short_form: copy for short-form or alternate platform
   - social_post: professional or community post copy
   - thumbnail_text: max 5 words, readable at mobile size
{linkedin_note}
Return ONLY valid JSON with keys: content_strategy, script, marketing_strategy, platform
"""


def generate_content_drafts(
    client: anthropic.Anthropic,
    topic: str,
    report: str,
    clarifications: dict,
    model: str = DEFAULT_MODEL,
) -> dict:
    response = client.messages.create(
        model=model,
        max_tokens=output_length_config()["draft_max_tokens"],
        system=build_content_system_prompt(clarifications),
        messages=[
            {
                "role": "user",
                "content": build_content_user_prompt(topic, report, clarifications),
            }
        ],
    )
    return parse_json_response(response.content[0].text)


def submit_to_heygen(script: str) -> str:
    api_key = os.getenv("HEYGEN_API_KEY")
    avatar_id = os.getenv("HEYGEN_AVATAR_ID")
    voice_id = os.getenv("HEYGEN_VOICE_ID")

    if not all([api_key, avatar_id, voice_id]):
        raise ValueError("HEYGEN_API_KEY, HEYGEN_AVATAR_ID, and HEYGEN_VOICE_ID must be set in .env")

    payload = json.dumps(
        {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": voice_id,
                    },
                }
            ],
            "dimension": {"width": 1280, "height": 720},
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.heygen.com/v2/video/generate",
        data=payload,
        headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    video_id = result.get("data", {}).get("video_id")
    if not video_id:
        raise ValueError(f"HeyGen did not return a video_id: {result}")

    return f"https://app.heygen.com/videos/{video_id}"


def format_strategy_section(value) -> str:
    if isinstance(value, dict):
        return "\n\n".join(
            f"**{key.replace('_', ' ').title()}:** {item}"
            for key, item in value.items()
        )
    return str(value)


def to_cell(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n\n".join(f"{k.upper().replace('_', ' ')}: {to_cell(v)}" for k, v in value.items())
    if isinstance(value, list):
        return "\n".join(f"- {to_cell(item)}" for item in value)
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
            "Thumbnail Text", "Publish Date", "Notes",
        ])

    scripts = get_or_create_worksheet(spreadsheet, "Scripts")
    if not scripts.row_values(1):
        scripts.append_row([
            "#", "Date Generated", "Topic", "Script",
            "Primary Description", "Short Form", "Social Post",
        ])


def create_calendar_event(topic: str, title: str, publish_date: str, script_summary: str) -> str:
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    channel_name = creator_config()["channel_name"]
    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_FILE), scopes=GOOGLE_SCOPES)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": f"Publish: {title}",
        "description": (
            f"Topic: {topic}\n\n"
            f"Script preview:\n{script_summary[:500]}...\n\n"
            f"Status: Draft\n"
            f"Channel: {channel_name}"
        ),
        "start": {"date": publish_date},
        "end": {"date": publish_date},
        "colorId": "2",
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 60},
            ],
        },
    }

    result = service.events().insert(calendarId=calendar_id, body=event).execute()
    return result.get("htmlLink", "")


def write_to_sheet(topic: str, drafts: dict, episode_num: int) -> None:
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("  Skipping sheet — GOOGLE_SHEET_ID not set in .env")
        return

    if not SERVICE_ACCOUNT_FILE.exists():
        print("  Skipping sheet — service-account.json not found")
        return

    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_FILE), scopes=GOOGLE_SCOPES)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(sheet_id)
    setup_sheet(spreadsheet)

    platform = drafts.get("platform", {})
    if isinstance(platform, str):
        platform = {}

    title = platform.get("primary_title", topic)
    thumbnail = platform.get("thumbnail_text", "")
    primary_description = platform.get("primary_description", "")
    short_form = platform.get("short_form", "")
    social_post = platform.get("social_post", "")
    script = to_cell(drafts.get("script", ""))

    pipeline = spreadsheet.worksheet("Pipeline")
    pipeline.append_row([
        episode_num,
        format_sheet_date(),
        topic,
        "Draft",
        title,
        thumbnail,
        "",
        "",
    ])

    scripts = spreadsheet.worksheet("Scripts")
    scripts.append_row([
        episode_num,
        format_sheet_date(),
        topic,
        script,
        primary_description,
        short_form,
        social_post,
    ])


def draft_path_for_topic(topic: str) -> Path:
    return OUTPUT_DIR / f"{slugify(topic)}.md"


def extract_markdown_section(text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n\n(.*?)(?:\n\n---|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def load_draft_from_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    thumbnail_match = re.search(r"^\*\*Thumbnail:\*\* (.*)$", text, re.MULTILINE)

    return {
        "content_strategy": extract_markdown_section(text, "CONTENT STRATEGY"),
        "marketing_strategy": extract_markdown_section(text, "MARKETING STRATEGY"),
        "script": extract_markdown_section(text, "SCRIPT"),
        "platform": {
            "primary_title": title_match.group(1).strip() if title_match else path.stem,
            "thumbnail_text": thumbnail_match.group(1).strip() if thumbnail_match else "",
            "primary_description": extract_markdown_section(text, "PRIMARY DESCRIPTION"),
            "short_form": extract_markdown_section(text, "SHORT FORM"),
            "social_post": extract_markdown_section(text, "SOCIAL POST"),
        },
    }


def save_script_for_editing(topic: str, drafts: dict) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = draft_path_for_topic(topic)
    platform = drafts.get("platform", {}) if isinstance(drafts.get("platform"), dict) else {}

    content = f"# {platform.get('primary_title', topic)}\n\n"
    content += f"**Thumbnail:** {platform.get('thumbnail_text', '')}\n\n"
    content += "---\n\n## CONTENT STRATEGY\n\n"
    content += f"{format_strategy_section(drafts.get('content_strategy', ''))}\n\n"
    content += "---\n\n## MARKETING STRATEGY\n\n"
    content += f"{format_strategy_section(drafts.get('marketing_strategy', ''))}\n\n"
    content += "---\n\n## SCRIPT\n\n"
    content += f"{drafts.get('script', '')}\n\n"
    content += "---\n\n## PRIMARY DESCRIPTION\n\n"
    content += f"{platform.get('primary_description', '')}\n\n"
    content += "---\n\n## SHORT FORM\n\n"
    content += f"{platform.get('short_form', '')}\n\n"
    content += "---\n\n## SOCIAL POST\n\n"
    content += f"{platform.get('social_post', '')}\n"
    path.write_text(content, encoding="utf-8")
    return path


def read_script_from_file(path: Path, drafts: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## SCRIPT\n\n(.*?)\n\n---", text, re.DOTALL)
    if match:
        drafts = dict(drafts)
        drafts["script"] = match.group(1).strip()
    return drafts


def update_drafts_script(drafts: dict, script: str) -> dict:
    updated = dict(drafts)
    updated["script"] = script.strip()
    return updated


def publish_drafts(topic: str, drafts: dict) -> dict:
    episode_num = next_episode_number()
    write_to_sheet(topic, drafts, episode_num)

    result = {"episode_num": episode_num, "calendar_url": ""}
    if SERVICE_ACCOUNT_FILE.exists() and os.getenv("GOOGLE_CALENDAR_ID"):
        platform = drafts.get("platform", {})
        title = platform.get("primary_title", topic) if isinstance(platform, dict) else topic
        publish_date = (datetime.now() + timedelta(days=episode_num)).strftime("%Y-%m-%d")
        result["calendar_url"] = create_calendar_event(
            topic, title, publish_date, to_cell(drafts.get("script", ""))
        )
    return result


def run_full_research(
    topic: str,
    clarifications: dict,
    on_search: Callable[[str, int, int], None] | None = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    client, tavily = get_clients()
    past_sessions = load_all_report_sessions()
    search_plan = build_search_plan(client, topic, clarifications, model)
    report = run_research_loop(
        client, tavily, topic, clarifications, search_plan, past_sessions, on_search, model
    )
    report_path = save_report(topic, report, clarifications, search_plan)
    return {
        "search_plan": search_plan,
        "report": report,
        "report_path": report_path,
    }


def run_full_drafts(topic: str, report: str, clarifications: dict, model: str = DEFAULT_MODEL) -> dict:
    client, _ = get_clients()
    drafts = generate_content_drafts(client, topic, report, clarifications, model)
    script_path = save_script_for_editing(topic, drafts)
    return {"drafts": drafts, "script_path": script_path}


def open_in_editor(path: Path) -> None:
    editor = shutil.which("code") or shutil.which("cursor")
    if editor:
        subprocess.Popen([editor, str(path)])
        return

    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def next_episode_number() -> int:
    if OUTPUT_DIR.exists():
        return len(list(OUTPUT_DIR.glob("*.md"))) + 1
    return len(list_report_history()) + 1


def run_content_pipeline(
    client: anthropic.Anthropic,
    topic: str,
    report: str,
    clarifications: dict,
    queue_entry: dict | None = None,
) -> None:
    print("Generating content drafts...", end="", flush=True)
    drafts = generate_content_drafts(client, topic, report, clarifications)
    print(" done.")

    script_path = save_script_for_editing(topic, drafts)
    print(f"\nDraft saved to: {script_path}")
    open_in_editor(script_path)
    input("\nEdit the draft in your editor, then press Enter to push to Google Sheets...")

    drafts = read_script_from_file(script_path, drafts)
    episode_num = next_episode_number()

    print("Writing to Google Sheet...", end="", flush=True)
    write_to_sheet(topic, drafts, episode_num)
    print(" done.")

    if SERVICE_ACCOUNT_FILE.exists() and os.getenv("GOOGLE_CALENDAR_ID"):
        try:
            platform = drafts.get("platform", {})
            title = platform.get("primary_title", topic) if isinstance(platform, dict) else topic
            publish_date = (datetime.now() + timedelta(days=episode_num)).strftime("%Y-%m-%d")
            event_url = create_calendar_event(topic, title, publish_date, to_cell(drafts.get("script", "")))
            print(f"Calendar event: {event_url}")
        except Exception as exc:
            print(f"Calendar failed: {exc}")

    if queue_entry:
        mark_queue_done(queue_entry["id"])
        print(f"[Auto] Marked '{topic}' as done.")


def main():
    try:
        client, tavily = get_clients()
    except RuntimeError as exc:
        print(f"Error: {exc}")
        print("Copy .env.example to .env and fill in your keys.")
        sys.exit(1)
    args = parse_args()
    queue_entry = None

    if args.auto:
        queue_entry = get_next_queue_item()
        if not queue_entry:
            print("All queue items are done, or queue.json is missing. Nothing to run.")
            sys.exit(0)

        total = len(load_queue())
        done = sum(1 for entry in load_queue() if entry.get("status") == "done")
        print(f"\n[Auto] Running item {queue_entry['id']}/{total}: {queue_entry['topic']}")
        print(f"[Auto] Progress: {done}/{total} items completed\n")

        topic = queue_entry["topic"]
        clarifications = queue_clarifications(queue_entry)
    else:
        topic = get_topic(args)
        if not topic:
            print("No topic provided. Exiting.")
            sys.exit(1)

        past_sessions = load_all_report_sessions()
        if past_sessions:
            print(f"\n(Prior reports: {len(past_sessions)} loaded from reports/)")
        clarifications = gather_clarifications(topic)

    past_sessions = load_all_report_sessions()
    search_plan = build_search_plan(client, topic, clarifications)

    print("Starting research...\n")
    report = run_research_loop(client, tavily, topic, clarifications, search_plan, past_sessions)

    path = save_report(topic, report, clarifications, search_plan)
    print(f"Report saved to: {path}")
    print(f"Word count: ~{len(report.split()):,}")

    should_generate = args.auto
    if not should_generate:
        should_generate = input("\nGenerate content drafts? (y/n): ").strip().lower() == "y"

    if should_generate:
        try:
            run_content_pipeline(client, topic, report, clarifications, queue_entry)
        except Exception as exc:
            import traceback

            print(f"\n[Error] {exc}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
