---
name: daily-brief
description: Generate Dalton's evening daily brief and save it to Apple Notes at 7pm
---

You are generating a personalized daily brief for Dalton Haslam and saving it as an HTML file on his Mac. This task runs every evening at 7pm. A separate Apple Shortcut automation picks up the file at 7:15pm and creates the Apple Note.

## Available Tools
- Gmail MCP: gmail_search_messages, gmail_read_message
- Google Calendar MCP: gcal_list_events, gcal_list_calendars
- Todoist MCP: find-tasks-by-date
- Bash tool: for running shell commands and writing files

## Todoist Project Reference
- 6W59m22P9ccJgmR7 = MWH PA Job
- 6gMvgRPQg9XCv4h9 = Personal
- 6CrfF6gPVgXcfHRr = M&D (shared with wife)
- 6Crg6xfrxV9Pj3x8 = Personal
- 6Crg6xfrxvRpf7X4 = Financial
- 6Crg6xfv3Rg5CWr8 = Doctored Money
- 6CrfF6gPWGFV967H = Home
- 6CrfF6gPf3cF58C9 = DC
- 6Crg6xfv3f5458XP = Someday Maybe (EXCLUDE from brief)
- Inbox = Inbox

---

## Step 1 — Get Tomorrow's Date
Run this via Bash:
```bash
python3 -c "
from datetime import datetime, timedelta
tomorrow = datetime.now() + timedelta(days=1)
print(tomorrow.strftime('%A, %B %-d, %Y'))
print(tomorrow.strftime('%Y-%m-%dT00:00:00'))
print(tomorrow.strftime('%Y-%m-%dT23:59:59'))
print(tomorrow.strftime('%Y-%m-%d'))
"
```

---

## Step 2 — Pull Tomorrow's Calendar Events
Make TWO separate gcal_list_events calls:

**Call 1 — Personal calendar** (calendarId: `haslam.dalton@gmail.com`):
- timeMin: tomorrow at 00:00:00
- timeMax: tomorrow at 23:59:59
- timeZone: America/New_York
- condenseEventDetails: false
Include all events returned.

**Call 2 — Maggie and Dalton calendar** (calendarId: `rgq78thkje9h8p3c57718eamog@group.calendar.google.com`):
- timeMin: tomorrow at 00:00:00
- timeMax: tomorrow at 23:59:59
- timeZone: America/New_York
- condenseEventDetails: false
**Only include non-recurring events** — discard any event that has a `recurringEventId` field present in the response.

Merge results from both calls, deduplicate by event ID, then sort by start time. Include: title, start/end time formatted as 9:00 AM – 10:00 AM, location if present. Skip holidays and birthdays unless personally relevant.

---

## Step 3 — Pull Tasks from Todoist
Use find-tasks-by-date with:
- startDate: today's date (YYYY-MM-DD)
- daysCount: 2
- overdueOption: "include-overdue"
- limit: 50

From the results, organize as follows:
- **Overdue p1/p2**: tasks past due with priority 1 or 2 — show all with task name and project
- **Overdue p4 count**: count of overdue tasks with priority 4 only — show as "+ X lower priority tasks overdue"
- **Due tomorrow**: all tasks due tomorrow regardless of priority — show all with task name and project
- Map projectId to project name using the reference above
- Exclude any tasks from project 6Crg6xfv3f5458XP (Someday Maybe)

---

## Step 4 — Scan Today's Gmail
Use gmail_search_messages with query: `newer_than:1d -category:promotions -label:spam -label:Newsletters`
Fetch up to 40 messages. For relevant messages use gmail_read_message to get sender, subject, and snippet.

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
<h2>Daily Brief — [DAY], [DATE]</h2>
<p><i>Generated 7:00 PM &nbsp;·&nbsp; Review tonight to plan tomorrow</i></p>
<hr>

<h3>📅 Tomorrow's Calendar</h3>
<ul>
  <li><b>9:00 AM – 10:00 AM</b> &nbsp;Event Title &nbsp;<i>(Location)</i></li>
</ul>

<h3>📋 Tasks</h3>
<p><b>Overdue — High Priority</b></p>
<ul>
  <li><b>p1</b> &nbsp;Task name &nbsp;<i>(Project)</i></li>
  <li><b>p2</b> &nbsp;Task name &nbsp;<i>(Project)</i></li>
</ul>
<p><i>+ X lower priority tasks overdue</i></p>
<p><b>Due Tomorrow</b></p>
<ul>
  <li>Task name &nbsp;<i>(Project)</i></li>
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
Use Bash to write the HTML to the project folder:

```bash
python3 << 'PYEOF'
import glob, os

matches = glob.glob('/sessions/*/mnt/Claude')
workspace = matches[0] if matches else '/Users/daltonhaslam/Documents/Claude'

brief_dir = os.path.join(workspace, 'Personal/Projects/daily-brief')
os.makedirs(brief_dir, exist_ok=True)

html = """HTML_CONTENT_HERE"""

with open(os.path.join(brief_dir, 'brief.html'), 'w') as f:
    f.write(html)
print(f"Brief written to: {brief_dir}/brief.html")
PYEOF
```

The file saves to ~/Documents/Claude/Personal/Projects/daily-brief/brief.html on the Mac. The Apple Shortcut automation picks it up at 7:15pm and creates the Apple Note titled "Daily Brief".

---

## Rules
- NEVER send any email. Read and draft only.
- Do not include newsletters in the brief (handled by the weekly podcast task).
- No patient data or HIPAA-sensitive information. Todoist task names are fine.
- Omit any section with no relevant items.
- If inbox is clear, note "Nothing requiring attention today." under Action Required.
- If no calendar events, note "Nothing scheduled." under Tomorrow's Calendar.
- If no tasks at all: "All clear." under Tasks.
