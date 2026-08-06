# SKILL: SQL Long-Form Tutorials (3:30–5 min)

Use this skill for any SQL-focused long-form video content request — scripts, descriptions, titles, thumbnails.

---

## Teaching Methodology

- Always frame the business question before introducing any SQL concept
- Show real, simple use cases — not abstract examples
- One concept per video — never overload beginners
- Use a maximum of 4 SQL clauses per video
- Write queries people can actually use
- Always use the retail dataset (see Dataset Reference below)
- Walk through dataset → query → result → business insight in that order

---

## Dataset Reference

All scripts must use this retail dataset. Tables and key columns:

| Table | Key Columns | Good For |
|---|---|---|
| `customers` | customer_id, name, email, city | filtering by location, counting customers, JOINs |
| `orders` | order_id, customer_id, order_date, total_amount | revenue totals, date filtering, aggregations |
| `order_items` | order_id, product_id, quantity, unit_price | line-item analysis, quantity sums, revenue by product |
| `products` | product_id, name, category, price | category breakdowns, price filtering, JOINs |

**Sample business questions this dataset supports:**
- Which city has the most customers?
- What was total revenue last quarter?
- Which product category generates the most sales?
- Who are our top 5 customers by spend?
- How many orders include more than one item?

---

## Agent Clarifying Questions

Before writing any script or description, ask:

1. What is the primary keyword for this video?
2. What SQL concept is being covered? (SELECT, GROUP BY, JOIN, WHERE, aggregate functions, etc.)
3. Who is the target audience? (beginner / intermediate / advanced)
4. What platform is this for? (YouTube / TikTok / LinkedIn)
5. What's the specific business question this video answers?
6. What's the one thing this video teaches that no other SQL tutorial teaches the same way?

---

## Script Format (3:30–5 min / ~400–500 words)

| Section | Timing | Purpose |
|---|---|---|
| **HOOK** | First 5–10 seconds | Stop the scroll. Lead with a result, bold claim, or a pain point the viewer recognizes. |
| **INTRO** | 20–30 seconds | Frame the business question. Tell viewers exactly what we're building and why it matters. |
| **VALUE BODY** | 2:30–3:30 | Walk through: dataset context → business question → SQL query → result → insight. Show the query building up step by step. |
| **CTA** | 20–30 seconds | Specific and actionable. Tell viewers what to do next and why. Tease the next video. |

**Closing line (required, word for word):**
> "I'm Cam, your upskilling and reskilling coach, don't forget to subscribe for more AI and data help!"

**Value Body structure:**
1. Introduce the dataset table(s) being used
2. State the business question in plain English
3. Write the SQL query (max 4 clauses)
4. Show the result
5. Explain the business insight in one sentence

---

## SEO Keywords

### Primary (always include one in the title)
- SQL tutorial for beginners
- learn SQL
- SQL for beginners
- how to become a data analyst
- SQL queries explained
- data analyst skills

### Secondary (use in descriptions and first 30 seconds of script)
- SQL use cases
- SQL data exploration
- data cleaning in SQL
- SQL aggregate functions
- SQL SELECT statement
- SQL GROUP BY
- SQL JOIN explained
- SQL WHERE clause
- SQL SUM AVG COUNT
- real world SQL examples
- SQL practice dataset
- data thinking

### Long-Tail (high intent — ideal for descriptions)
- SQL tutorial for beginners step by step
- how to write your first SQL query
- SQL for non programmers
- SQL for data analysts
- learn SQL with real data
- SQL use cases for business
- how to analyze data with SQL

### Hashtags
`#SQLtutorial` `#learnSQL` `#SQLforbeginners` `#dataanalyst` `#dataanalytics` `#aggregatefunctions` `#SQLqueries` `#learninpublic` `#upskilling` `#dataanalysis` `#AIDataThinking`

**Required hashtags (always include):**
`#SQLtutorial` `#learnSQL` `#dataanalytics` `#SQLforbeginners` `#aggregatefunctions` `#dataanalyst` `#retaildataset` `#learninpublic` `#upskilling` `#AIDataThinking`

---

## Title Formula

- Lead with the SQL concept or keyword
- Include a number when possible (3 tips, 1 line, 5 use cases)
- End with audience signal (for beginners, every analyst needs, step by step)
- Always include "SQL" in the title
- Under 70 characters for mobile readability

**Examples:**
- "SQL GROUP BY Explained — Analyze Sales Data Like a Pro"
- "SQL SUM() for Beginners — Calculate Total Revenue in 3 Steps"
- "SQL JOINs Explained with Real Retail Data — Beginner Tutorial"
- "How to Write Your First SQL Query — Step by Step for Beginners"

---

## Thumbnail Text Rules

- Max 5 words
- Must be readable at mobile size
- Include a SQL function name or number when possible
- Best performer format: *"Total Revenue in 3 Lines of SQL"*

---

## YouTube Description Format

```
[Keyword-rich first 2 sentences — shown before "show more"]

[What's covered — arrow list → matching exactly what's in the video]

[Business questions answered → plain English]

[Series tease + CTA — subscribe and bell]

[Series tag line]
[LinkedIn: www.linkedin.com/in/camparham1/]

[Hashtags — 10–12 max]
```

**Keyword rules:**
- Primary keywords in the first 30 seconds of every script
- Keep keyword density under 2%
- Write for search intent first, creativity second
- Use long-tail keywords in descriptions, not titles

---

## Viral Research Instructions

When researching content for a topic:

1. Find the top 5 viral YouTube videos on the topic
2. Analyze: title structure, keywords, first 30 seconds of description, hook patterns, CTA style
3. Identify common patterns across titles and hooks
4. Apply those patterns to Cam's script and description
5. Flag which keywords are trending vs. saturated
6. Analyze patterns only — never copy titles, descriptions, or scripts verbatim



# Output Format
For every content request, deliver:

✅ Video title (SEO optimized)
✅ 3:30 - 5:00 minute script (hook,topic intro, value body, CTA)
✅ YouTube description (matching script exactly)
✅ Thumbnail text suggestion
✅ Hashtags
---

## Output Checklist

Every content request must deliver:

- [ ] Video title (SEO optimized, under 70 chars)
- [ ] Script (~400–500 words, HOOK → INTRO → VALUE BODY → CTA)
- [ ] Script uses the retail dataset (customers, orders, order_items, or products)
- [ ] Script includes a sample SQL query (max 4 clauses)
- [ ] Script ends with required closing line
- [ ] YouTube description (matching script structure)
- [ ] Thumbnail text suggestion (max 5 words)
- [ ] Hashtags (10–12, required set included)
