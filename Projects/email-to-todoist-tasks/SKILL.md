---
name: email-to-todoist-tasks
description: Scan Gmail inbox for actionable tasks and add them to the Todoist "personal" project nightly.
---

You are scanning Dalton Haslam's Gmail for actionable emails and adding tasks to his Todoist Personal project. This task runs every evening at 7pm.

## Available Tools
- Bash tool (for Gmail CLI scripts and Todoist CLI scripts)

---

## Step 1 — Get Today's Date
```bash
python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d'))"
```

---

## Step 2 — Scan Gmail
Run via Bash:
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh \
  --query "newer_than:1d -in:trash -in:spam -label:Newsletters" \
  --max-results 40
```
This searches ALL mail folders (inbox, archived, sent, etc.) — not just the inbox. Newsletters, trash, and spam are excluded. Returns a JSON array of `{id, threadId, snippet, subject, from, date}`. Assess actionability from these fields. For ambiguous emails that need full body to confirm, run:
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh \
  --message-id <id> --depth full
```

**Skip (not actionable):**
- Newsletters and marketing emails
- Automated notifications (shipping, account alerts, etc.)
- Pure receipts or statements with no action needed
- Purely informational emails (FYI only)

**Flag as actionable (needs a task):**
- Emails requiring a reply, decision, approval, or follow-up
- Emails with a concrete action item or deadline
- Event invitations or RSVPs needed
- Bills or requests requiring payment or response

---

## Step 3 — Extract Task Details
For each actionable email, build:
- **Task name**: concise, action-oriented (e.g. "Reply to John re: contract review", "RSVP to school event by Friday")
- **Due date**: the calendar date the email was received (YYYY-MM-DD), formatted for Todoist as `YYYY-MM-DD`
- **Deadline**: if the email body mentions a specific deadline date, include it in the description
- **Description**: `From: [sender name/email] | Subject: [subject] | Deadline: [date if found, else omit]`

---

## Step 4 — Check for Duplicates
Before adding each task, run:
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/todoist-write/find-tasks.sh \
  --query "<task name>" \
  --project-id 6Crg6xfrxV9Pj3x8
```
Returns a JSON array. If the array is non-empty (a task with a similar name already exists), skip it — do not add a duplicate.

---

## Step 5 — Add Tasks to Todoist
For each new, non-duplicate actionable task, run:
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/todoist-write/add-task.sh \
  --content "<task name>" \
  --description "<From: [sender] | Subject: [subject] | Deadline: [date if found, else omit]>"
```
Defaults applied automatically: due = today, priority = p2, project = Personal (6Crg6xfrxV9Pj3x8), label = claude.

---

## Rules
- NEVER send any email. Read only.
- Do not create duplicate tasks.
- If no actionable emails are found, output: "No new actionable emails found today."
- Always include enough context in the task description so Dalton can identify which email it came from without opening Gmail.
