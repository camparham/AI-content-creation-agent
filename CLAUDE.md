# Research Workflow Agent

A CLI tool that researches any topic using Claude + Tavily web search, then saves a structured Markdown report.

## Skills

| Content Type | Skill File |
|---|---|
| SQL long-form tutorials (3:30–5 min) | `Skills_sql_long-form.md` |
| AI instructional videos (Shorts) | `Skills_ai_shorts.md` |
| BigQuery + Looker Studio HR analytics (up to 15 min) | `Skills_bigquery_looker.md` |

When creating video content, read the relevant skill file first before writing any script, title, or description.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys
```

**API keys needed:**
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `TAVILY_API_KEY` — from app.tavily.com (free tier: 1000 searches/month)

## Usage

```bash
python agent.py --auto              # runs next pending SQL curriculum topic
python agent.py "SQL GROUP BY"      # interactive mode — any SQL topic
python agent.py                     # prompts for topic
```

The agent uses `Skills_sql_long-form.md` for all script generation. Produces a 400–500 word script, YouTube description, and platform copy → saves to `content-hub.md` and Google Sheets.

## Project Structure

```
agent.py          — the entire agent (~250 lines)
reports/          — generated reports (gitignored content)
requirements.txt
.env.example
```

## Architecture

Single-file agent using the Anthropic SDK's tool-use agentic loop:
- Claude generates clarifying questions and a search plan before researching
- A `while` loop runs until Claude returns a message with no `tool_use` blocks
- Tavily search budget capped at 10 calls per run; remaining budget is passed in the system prompt so Claude self-paces
- Final message from Claude is the complete Markdown report



## Creator Profile 

Name: Cam 

Brand: AI & Data Thinking with Cam

Goal: Create accessible, easy to consume and actionable content that helps people understand the foundational skillset of data thinking. 

Teaching philosophy: Data thinking first, syntax second--always start with the business question before writing a single line of SQL. 


## Content Pillars 

1. SQL tutorials for non-technical beginners using reliable datasets.
2. Data thinking methodology -- teach how to think about data, not just syntax. 
3. SQL adoption and tools for data beginners. 
4. AI tutorials for non-technical users 

## Teaching Methodology 

* Always frame the business question before introducing a SQL concept

* Show real simple uses cases, not abstract examples 

* One concept per video -- never overload beginners

* Use a maximum of 6 SQL clauses in each video

* Write queries people can actually use 

## Script Format

**SQL long-form tutorials:** 3:30–5 minutes, ~400–500 words. Structure: HOOK → INTRO → VALUE BODY → CTA. Never write a 60-second or 150-word script for SQL tutorials.

**AI Shorts:** 60 seconds, ~150 words. Structure: HOOK → VALUE BODY → CTA.

Full format details, SEO rules, and output checklists are in the relevant skill file (see Skills section above). Always read the skill file before writing any script.

## SEO Keywords 

Primary (highest search volume — always include one in the title)

* SQL tutorial for beginners
* learn SQL
* SQL for beginners
* how to become a data analyst
* SQL queries explained
* data analyst skills

### Secondary (use in descriptions and first 30 seconds of script)

* SQL use cases
* SQL data exploration
* data cleaning in SQL
* SQL aggregate functions
* SQL SELECT statement
* SQL GROUP BY
* SQL JOIN explained
* SQL WHERE clause
* SQL SUM AVG COUNT
* real world SQL examples
* SQL practice dataset
* data thinking


### Long-Tail (high intent, lower competition — ideal for descriptions)

* SQL tutorial for beginners step by step
* how to write your first SQL query
* SQL for non programmers
* SQL for data analysts
* learn SQL with real data
* SQL use cases for business
* how to analyze data with SQL

### Trending Education Hashtags (2025-2026)
#SQLtutorial #learnSQL #SQLforbeginners #dataanalyst #dataanalytics
#aggregatefunctions #SQLqueries #learninpublic #upskilling #dataanalysis #AIDataThinking

# Rules

* Place primary keywords in the first 30 seconds of every script
* Keep keyword density under 2%
* Write for search intent first, creativity second
* Always write for beginner data analysts and SQL learners
* Use long-tail keywords in descriptions, not titles
* Titles stay under 70 characters for mobile readability
* Add my LinkedIN url in each description:  www.linkedin.com/in/camparham1/
* Always ask clarifying questions before starting. a complex task 
* Show your plan and steps before executing
* Keep reports and summaries concise-- bullet points over paragraphs 
* Save all output files to the output folder 
* Cite sources when doing research 
* Script should always conclude with "I'm Cam, your upskilling and reskilling coach, don't forget to subscribe for more AI and data help!"
* Use a retail dataset with the following table names and made up data: orders, sales, and customers

# Project structure 
- workflow/ - workflow instruction files (plain English recipes and agent follows) 
- output/ - Finished deliverables (reports, drafts, analysis)
- resources/ - Reference docs and templates 

# YouTube Description Format 

[Keyword-rich first 2 sentences — shown before "show more"]

[What's covered — arrow list → matching exactly what's in the video]

[Business questions answered → plain English]

[Series tease + CTA — subscribe and bell]

[Series tag line]
[LinkedIn URL]

[Hashtags — 10-12 max]

Required Hashtags
#SQLtutorial #learnSQL #dataanalytics #SQLforbeginners #aggregatefunctions #dataanalyst #retaildataset #learninpublic #upskilling #AIDataThinking


# Title Formula

Lead with the SQL concept or keyword
Include a number when possible (3 tips, 1 line, 5 use cases)
End with audience signal (for beginners, every analyst needs)
Always include "SQL" in the title

Examples:

"SQL SUM() for Beginners — Calculate Total Revenue in 1 Line"
"3 SQL Best Practices Every Beginner Needs Before Querying Data"
"Before You Write a Single Line of SQL, Think Like This"


# Thumbnail Text Rules

Max 5 words
Must be readable at mobile size
Include a number or SQL function name when possible
Best performer: "Total Revenue in 1 Line of SQL"


## Brand Colors

Background: #dafdb9 (mint green) or dark #1a1a1a
Accent: White
SQL text color: #dafdb9 on dark backgrounds


## Target Platforms

YouTube, LinkedIn, TikTok. Platform-specific format and length are defined in the relevant skill file.

# Viral Research Instructions
When researching content for any topic:

Find the top 5 viral YouTube videos on the topic
Analyze: title structure, keywords, first 30 seconds of description, hook patterns, CTA style
Identify common patterns across titles and hooks
Apply those patterns to Cam's script and description
Flag which keywords are high search volume
Analyze patterns only — never copy titles, descriptions, or scripts verbatim


### Agent Clarifying Questions
Before writing any script or description, ask:

What is the primary keyword for this video?
Who is the target audience? (beginner / intermediate / advanced)
What platform is this for? (YouTube / TikTok / LinkedIn)
Should this video solve for a business question?
What's the one thing this video teaches that no other SQL tutorial teaches the same way?
Does this video solve a problem someone would pay to solve faster?




When creating SQL long-form video content, follow the skill in Skills_sql_long-form.md