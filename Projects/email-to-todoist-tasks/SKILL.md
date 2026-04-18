---
name: email-to-todoist-tasks
description: Scan Gmail inbox for actionable tasks and add them to the Todoist "personal" project nightly.
---

You are scanning Dalton Haslam's Gmail for actionable emails and adding tasks to his Todoist Personal project. This task runs every evening at 7pm.

## Available Tools
- Gmail MCP: gmail_search_messages, gmail_read_message
- Todoist MCP (use full tool names as listed below):
  - mcp__b83d701b-1e39-48fa-a982-c906ee421dc6__find-tasks
  - mcp__b83d701b-1e39-48fa-a982-c906ee421dc6__add-tasks
- Write tool and Bash tool (for writing/deleting the failure notification file)

---

## Step 1 — Get Today's Date
```bash
python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d'))"
```

---

## Step 2 — Scan Gmail
Use gmail_search_messages with query: `newer_than:1d -in:trash -in:spam -label:Newsletters`

This searches ALL mail folders (inbox, archived, sent, etc.) — not just the inbox. Newsletters, trash, and spam are excluded. Retrieve up to 40 messages. For each one that looks promising based on subject/sender, use gmail_read_message to read the full content.

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
Before adding each task, use mcp__b83d701b-1e39-48fa-a982-c906ee421dc6__find-tasks to search the Personal project (project ID: 6Crg6xfrxV9Pj3x8) for existing tasks with a similar name. If a task with the same or highly similar subject already exists (open or recently completed), skip it — do not add a duplicate.

---

## Step 5 — Add Tasks to Todoist
For each new, non-duplicate actionable task, use mcp__b83d701b-1e39-48fa-a982-c906ee421dc6__add-tasks:
- projectId: `6Crg6xfrxV9Pj3x8` (Personal — sky blue)
- content: the task name
- due_date: date email was received
- description: the context string from Step 3

---

## Step 6 — Write or Delete Notification File

The notification file path is: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/email-to-todoist-tasks/todoistfailure/todoist_failure.txt`

This file is monitored by an Apple Shortcut on Dalton's Mac. When the file exists, the Shortcut fires and creates an Apple Note alerting him that Todoist sync failed and listing the missed tasks. Always complete this step on every run — do not skip it.

**If Todoist calls failed (authentication error or any write failure):**
Use the Write tool to create or overwrite the file at the path above. Contents should be plain text including:
- Date of the run
- Error encountered (e.g. "Authentication failure")
- Bulleted list of each task that failed to be added, with its full description

**If all Todoist writes succeeded (or no actionable emails were found):**
Delete the file using Bash:
```bash
rm -f '/Users/daltonhaslam/Documents/Claude/Personal/Projects/email-to-todoist-tasks/todoistfailure/todoist_failure.txt'
```

This signals to the Shortcut that no failure occurred and clears any prior alert.

---

## Rules
- NEVER send any email. Read only.
- Do not create duplicate tasks.
- If no actionable emails are found, output: "No new actionable emails found today." and still complete Step 6 (mount folder, then delete todoist_failure.txt if it exists).
- Always include enough context in the task description so Dalton can identify which email it came from without opening Gmail.
- Always complete Step 6 on every run.
