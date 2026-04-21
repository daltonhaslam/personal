---
name: daily-brief
description: Generate Dalton's evening daily brief and save it as brief.html on his Mac
---

You are generating a personalized daily brief for Dalton Haslam and saving it as an HTML file on his local Mac. You are running locally via the claude CLI — not in a cloud sandbox. No path discovery needed; use the hardcoded paths below.

---

## Step 1 — Get Tomorrow's Date
Run this via Bash:
```bash
python3 -c "
from datetime import datetime, timedelta
tomorrow = datetime.now() + timedelta(days=1)
print(tomorrow.strftime('%A, %B %-d, %Y'))
print(tomorrow.strftime('%Y-%m-%d'))
"
```
Line 1 is the display date; line 2 (`YYYY-MM-DD`) is used in Step 2.

---

## Step 2 — Pull Tomorrow's Calendar Events
Run TWO bash commands using the `YYYY-MM-DD` date from Step 1:

**Call 1 — Personal calendar:**
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gcal-fetch/list-events.sh \
  --calendar-id "haslam.dalton@gmail.com" \
  --date <YYYY-MM-DD>
```

**Call 2 — Maggie and Dalton shared calendar (recurring events excluded):**
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gcal-fetch/list-events.sh \
  --calendar-id "rgq78thkje9h8p3c57718eamog@group.calendar.google.com" \
  --date <YYYY-MM-DD> \
  --exclude-recurring
```

Each returns a JSON array of `{title, start, end, location}`. Merge results from both calls, deduplicate by title+start, sort by start. Include: title, start/end time formatted as 9:00 AM – 10:00 AM, location if present. Skip holidays and birthdays unless personally relevant.

---

## Step 3 — Pull Tasks from Todoist
Run via Bash:
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/todoist-taskpull-highpriority/fetch-tasks.sh
```
If the script exits non-zero or stdout begins with `{"error":`, write "Task fetch failed" under Tasks and skip to Step 4.

Read the JSON output into working memory. Organize as follows:

**Past Due** — tasks in `sections.overdue` (due before today)
- List each: task content and project name. Skip any task where project is "Someday Maybe".

**Due Today** — tasks in `sections.today`
- List each: task content and project name. Skip any task where project is "Someday Maybe".

**Due Tomorrow** — tasks in `sections.tomorrow`
- List each: task content and project name. Skip any task where project is "Someday Maybe".

**Upcoming Deadlines** — tasks in `sections.deadline_only` PLUS any task in the above sections where the `deadline` field is non-null
- List each: task content, project, deadline date formatted as "Apr 22". Skip "Someday Maybe".

Omit a subsection entirely if it has no tasks after filtering.

---

## Step 4 — Scan Today's Gmail
Run via Bash:
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh \
  --query "newer_than:1d -category:promotions -label:spam -label:Newsletters" \
  --max-results 40
```
Returns a JSON array of `{id, threadId, snippet, subject, from, date}`. Categorize each message from these fields directly. If an email is ambiguous and needs full body context, run:
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh \
  --message-id <id> --depth full
```

Categorize each into ONE bucket:
- **Action Required**: needs a reply, approval, decision, or follow-up
- **Family**: household coordination, kids' school, family activities, spouse
- **Church**: ward communication, Young Men, bishop, LDS-related
- **Financial**: bills, payment confirmations, statements, receipts
- **FYI**: worth knowing, no action needed
- **Skip**: automated notifications, marketing, irrelevant items, newsletters

---

## Step 5 — Format the Brief as HTML
Build an HTML document. Omit any section with zero items. Keep each line concise.

```html
<style>
  body, h2, h3, p, li, b, i {
    color: #1a1a1a;
  }
  @media (prefers-color-scheme: dark) {
    body, h2, h3, p, li, b, i {
      color: #f0f0f0;
    }
  }
</style>

<h2>Daily Brief — [DAY], [DATE]</h2>
<p><i>Generated 7:00 PM &nbsp;·&nbsp; Review tonight to plan tomorrow</i></p>
<hr>

<h3>📅 Tomorrow's Calendar</h3>
<ul>
  <li><b>9:00 AM – 10:00 AM</b> &nbsp;Event Title &nbsp;<i>(Location)</i></li>
</ul>

<h3>📋 Tasks</h3>
<p><b>Past Due</b></p>
<ul>
  <li><b>p1</b> &nbsp;Task name &nbsp;<i>(Project)</i></li>
</ul>
<p><b>Due Today</b></p>
<ul>
  <li><b>p2</b> &nbsp;Task name &nbsp;<i>(Project)</i></li>
</ul>
<p><b>Due Tomorrow</b></p>
<ul>
  <li><b>p1</b> &nbsp;Task name &nbsp;<i>(Project)</i></li>
</ul>
<p><b>Upcoming Deadlines</b></p>
<ul>
  <li>Task name &nbsp;<i>(Project)</i> &nbsp;— deadline <b>Apr 22</b></li>
</ul>

<h3>⚡ Action Required</h3>
<ul>
  <li><b>Sender Name</b> — Subject — one-line note on what's needed</li>
</ul>

<h3>👨‍👩‍👦 Family</h3>
<ul>
  <li><b>Sender</b> — Subject — brief summary</li>
</ul>

<h3>⛪ Church</h3>
<ul>
  <li><b>Sender</b> — Subject — brief summary</li>
</ul>

<h3>💰 Financial</h3>
<ul>
  <li><b>Sender</b> — Subject — brief summary</li>
</ul>

<h3>ℹ️ FYI</h3>
<ul>
  <li><b>Sender</b> — Subject — brief summary</li>
</ul>
```

---

## Step 6 — Write to File
Use Bash to write the HTML to the hardcoded path:

```bash
python3 << 'PYEOF'
html = """HTML_CONTENT_HERE"""

with open('/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/brief.html', 'w') as f:
    f.write(html)
print("Brief written to: /Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/brief.html")
PYEOF
```

---

## Rules
- NEVER send any email. Read and draft only.
- Do not include newsletters in the brief (handled by the weekly podcast task).
- No patient data or HIPAA-sensitive information. Todoist task names are fine.
- Omit any section with no relevant items.
- If inbox is clear, note "Nothing requiring attention today." under Action Required.
- If no calendar events, note "Nothing scheduled." under Tomorrow's Calendar.
- If no tasks at all: "All clear." under Tasks.
