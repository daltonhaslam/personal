---
name: todoist-taskpull-highpriority
description: Fetch p1/p2 Todoist tasks due today/overdue/tomorrow or with deadline within 3 days. Returns structured JSON via CLI (Todoist REST API v2 — no MCP).
---

## What This Skill Does

Runs `fetch-tasks.sh` against the Todoist REST API v2 and outputs structured JSON containing all p1/p2 tasks that match either:
- Due date: overdue, today, or tomorrow
- Deadline: within the next 3 days (even if due date is further out)

Returns all matching tasks regardless of project — filter by `project` field in the consumer if needed (e.g., exclude "Someday Maybe").

## How to Invoke

```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/todoist-taskpull-highpriority/fetch-tasks.sh
```

Requires `TODOIST_API_TOKEN` env var. See Prerequisites below.

**API used:** `GET https://api.todoist.com/api/v1/tasks/filter?query=...` (Todoist REST API v1 — v2 was deprecated as of 2026)

## Output Structure

```json
{
  "fetched_at": "2026-04-19T19:00:00",
  "sections": {
    "overdue":       [{"id":"..","content":"..","priority":"p1","project":"Financial","due":"2026-04-17","deadline":null}],
    "today":         [...],
    "tomorrow":      [...],
    "deadline_only": [{"id":"..","content":"..","priority":"p2","project":"Home","due":null,"deadline":"2026-04-21"}]
  },
  "counts": {"overdue":2,"today":1,"tomorrow":3,"deadline_only":1}
}
```

## Field Reference

| Field | Values | Notes |
|-------|--------|-------|
| `priority` | `"p1"` or `"p2"` | p1 = highest |
| `project` | human-readable name | mapped from project_id |
| `due` | ISO date string or `null` | date only (no time) |
| `deadline` | ISO date string or `null` | separate from due date |

**sections.deadline_only** — tasks not in any due-date section but with a deadline ≤ today+3. A task in `tomorrow` with a near deadline appears in `tomorrow` with its `deadline` field populated (not duplicated in `deadline_only`).

## Error Handling

If the script exits non-zero or stdout begins with `{"error":`, treat the task fetch as failed. Log the error message and continue the workflow without task data.

## Prerequisites

`TODOIST_API_TOKEN` must be set in the environment:
- **LaunchAgent context**: extracted from macOS Keychain by `run_daily_brief.sh` before invoking claude
- **Interactive Claude Code**: set in shell profile via `security find-generic-password -a "todoist" -s "TODOIST_API_TOKEN" -w`
- **One-time Keychain setup**: `security add-generic-password -a "todoist" -s "TODOIST_API_TOKEN" -w "YOUR_TOKEN"`
  (Token found at: Todoist → Settings → Integrations → Developer)
