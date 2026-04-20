# MCP → CLI Conversion Roadmap

## Why This Exists

Replacing MCP tool calls with direct REST API shell scripts to:
- Reduce token usage (MCP responses are verbose; scripts return exactly what's needed)
- Reduce variability (deterministic curl calls vs. MCP tool parsing)
- Improve reliability (no MCP layer failures; portable to local LaunchAgent execution)

## Proven Pattern (Reference Implementation)

`Personal/skills/todoist-taskpull-highpriority/fetch-tasks.sh`

Key conventions to follow in all new scripts:
- Auth: `security find-generic-password -s <service> -w` from macOS Keychain
- Output: JSON to stdout; errors to stderr with `exit 1`
- Validation: check for non-JSON responses (guard against HTML error pages)
- Pass large strings to Python via env vars to avoid shell quoting issues
- `set -euo pipefail` at top of every script

---

## Conversion 1: Todoist Write CLI Skill

**Status:** Complete  
**Affects:** `Projects/email-to-todoist-tasks/SKILL.md`

### Goal
Replace MCP `find-tasks` + `add-tasks` calls with direct Todoist REST API scripts.

### Context
- `email-to-todoist-tasks` runs daily at 7 PM via cloud RemoteTrigger
- Currently calls MCP `find-tasks` to dedup-check before adding, then `add-tasks` to create tasks
- Todoist Personal project ID: `6Crg6xfrxV9Pj3x8`
- Auth: `TODOIST_API_TOKEN` already in Keychain (used by `fetch-tasks.sh` — no setup needed)
- Todoist API docs: `https://developer.todoist.com/rest/v2/`

### Scripts Created

> **API Note:** `rest/v2` returns **410 Gone** — it is deprecated. Use `api/v1` for all Todoist calls. Confirmed working: `GET/POST https://api.todoist.com/api/v1/tasks`. The existing `fetch-tasks.sh` already uses `api/v1`; follow that pattern.

**`skills/todoist-write/find-tasks.sh`** ✅ Done
- Args: `--query <string>` `--project-id <id>`
- Calls: `GET https://api.todoist.com/api/v1/tasks?project_id=<id>` then filters by content match (Python, case-insensitive substring)
- Response shape: `{"results": [...]}` — unwrap before filtering
- Returns: JSON array of `{id, content}` for matching tasks
- Use case: dedup check before adding a new task

**`skills/todoist-write/add-task.sh`** ✅ Done
- Required: `--content <string>`
- Optional (with defaults): `--due-string "today"` `--priority 3` (p2) `--project-id 6Crg6xfrxV9Pj3x8` `--labels "claude"` `--description <string>`
- Calls: `POST https://api.todoist.com/api/v1/tasks`
- Body: JSON built in Python via env vars
- Returns: compact task JSON `{id, content, due, priority, labels, url}`
- Use case: add an actionable email (or any input) as a Todoist task

### Verification
1. ✅ `bash skills/todoist-write/find-tasks.sh --query "test" --project-id 6Crg6xfrxV9Pj3x8` → `[]`
2. ✅ `bash skills/todoist-write/add-task.sh --content "Test task CLI" --description "testing"` → task with p2/claude/today confirmed
3. ⬜ Trigger `email-to-todoist-tasks` manually → verify tasks created, no MCP calls in session

---

## Conversion 2: Gmail Fetch CLI Skill

**Status:** Complete  
**Affects:** All 4 active projects (daily-brief, email-to-todoist-tasks, weekly-newsletter-podcast, monthly-comms-maintenance)

### Goal
Replace MCP `gmail_search_messages` + `gmail_read_message` across all projects.

### Context
- Gmail is the heaviest MCP consumer: daily-brief (up to 41 calls/run), email-to-todoist (up to 41), weekly-podcast (5+ calls), monthly-maintenance (21+ calls)
- **Gmail requires OAuth 2.0** — no static API token equivalent. API keys only work for public Google APIs.
- **Refresh tokens do not expire on a timer** — only revoked if unused for 6+ months or manually revoked. After one-time setup, scripts behave like static tokens.
- Auth flow: refresh token + client credentials stored in Keychain; `refresh-token.sh` exchanges them for a short-lived access token on each run, transparently.
- Gmail REST API base: `https://gmail.googleapis.com/gmail/v1/users/me`

### One-Time OAuth Setup (do before building scripts)

1. Go to Google Cloud Console → create or reuse a project
2. Enable the **Gmail API**
3. Create OAuth 2.0 credentials → **Desktop app** type → download `credentials.json`
4. Run one-time authorization to capture the refresh token:
   ```bash
   pip3 install google-auth-oauthlib
   python3 - <<'EOF'
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_secrets_file(
       '/Users/daltonhaslam/.config/google/credentials.json',
       scopes=[
           'https://www.googleapis.com/auth/gmail.readonly',
           'https://www.googleapis.com/auth/calendar.readonly',
       ]
   )
   creds = flow.run_local_server(port=0, prompt='consent')
   print("REFRESH TOKEN:", creds.refresh_token)
   print("CLIENT ID:", creds.client_id)
   print("CLIENT SECRET:", creds.client_secret)
   EOF
   ```
5. Store credentials in Keychain:
   ```bash
   security add-generic-password -a gmail -s GMAIL_REFRESH_TOKEN -w "<refresh_token>"
   security add-generic-password -a gmail -s GMAIL_CLIENT_ID     -w "<client_id>"
   security add-generic-password -a gmail -s GMAIL_CLIENT_SECRET -w "<client_secret>"
   ```

### Scripts Created

**`skills/gmail-fetch/refresh-token.sh`** ✅ Done
- Internal helper — called by other scripts, not directly by SKILL.md
- Reads Keychain: `GMAIL_REFRESH_TOKEN`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`
- POSTs to `https://oauth2.googleapis.com/token`
- Prints access token to stdout; exits 1 on failure

**`skills/gmail-fetch/search-emails.sh`** ✅ Done
- Args: `--query <gmail_search_string>` `--max-results <n>` (default: 40)
- Flow: 1 search call → N metadata calls per result (format=metadata)
- Returns: JSON array of `{id, threadId, snippet, subject, from, date}`
- Empty result: `[]`
- Snippet: HTML entities decoded, invisible Unicode chars stripped

**`skills/gmail-fetch/read-email.sh`** ✅ Done
- Args: `--message-id <id>` `--depth snippet|full` (default: full)
- `--depth snippet`: metadata call → `{subject, from, date, snippet}`
- `--depth full`: full message → `{subject, from, date, body}`
  - Body: prefers HTML → markdown (skip images, convert headings/lists/paragraphs)
  - Fallback: plain text as-is
  - Base64 URL-safe decoded

### SKILL.md Updates (4 files) ✅ Done
- daily-brief Step 4: `search-emails.sh` replaces `gmail_search_messages`; `read-email.sh --depth full` available for ambiguous messages
- email-to-todoist Step 2: same pattern
- weekly-newsletter-podcast Step 1: per-source search + `read-email.sh --depth full` for each newsletter
- monthly-comms-maintenance Steps 1–3: search-only for audits; `read-email.sh --depth full` for new candidates

### Verification
1. ✅ `bash skills/gmail-fetch/search-emails.sh --query "is:unread" --max-results 3` → enriched JSON array
2. ✅ `bash skills/gmail-fetch/read-email.sh --message-id <id> --depth full` → decoded markdown body
3. ⬜ Trigger daily-brief manually → email section categorized correctly without MCP calls
4. ⬜ Trigger email-to-todoist manually → tasks created, no MCP calls in session

---

## Conversion 3: Google Calendar Fetch CLI Skill

**Status:** Complete  
**Affects:** `Projects/daily-brief/SKILL.md` (2 calls); also sets up what-now-widget

### Goal
Replace MCP `gcal_list_events` in daily-brief with a direct Calendar API script.

### Context
- Two calendars queried in daily-brief: personal + shared calendar
- Fetches tomorrow's events (00:00–23:59 local time)
- **Shares Google OAuth infrastructure with Gmail** — same Keychain credentials, same `refresh-token.sh` helper. No additional setup if Gmail skill already built.
- One additional step: enable **Google Calendar API** in the same Cloud project used for Gmail
- **OAuth scope:** the shared refresh token must include `calendar.readonly` — re-run OAuth flow with `prompt='consent'` requesting both `gmail.readonly` and `calendar.readonly` scopes, then update `GMAIL_REFRESH_TOKEN` in Keychain
- Calendar REST endpoint: `GET https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events`
- Params: `timeMin`, `timeMax` (RFC3339), `singleEvents=true`, `orderBy=startTime`

### Script Created

**`skills/gcal-fetch/list-events.sh`** ✅ Done
- Args: `--calendar-id <id>` `--date <YYYY-MM-DD>` `--exclude-recurring` (optional)
- Reuses `../gmail-fetch/refresh-token.sh` for auth (shared Google OAuth credentials)
- Computes RFC3339 timeMin/timeMax in local timezone via Python
- URL-encodes calendarId; calls `GET .../calendars/{id}/events` with `singleEvents=true&orderBy=startTime`
- `--exclude-recurring` drops any item with `recurringEventId` present
- Returns: JSON array of `{title, start, end, location}` — location omitted if absent; times as `"9:00 AM"` or `"all-day"`

### Verification
1. ✅ `bash skills/gcal-fetch/list-events.sh --calendar-id "haslam.dalton@gmail.com" --date $(date -v+1d +%Y-%m-%d)` → events listed
2. ✅ Trigger daily-brief manually → calendar section correct, no MCP calls

---

## File Map

```
Personal/
├── Projects/
│   ├── mcp-to-cli-roadmap.md              ← THIS FILE
│   ├── daily-brief/SKILL.md               ← updated: conversions 2 + 3
│   ├── email-to-todoist-tasks/SKILL.md    ← updated: conversions 1 + 2
│   ├── weekly-newsletter-podcast/SKILL.md ← updated: conversion 2
│   └── monthly-comms-maintenance/SKILL.md ← updated: conversion 2
└── skills/
    ├── todoist-taskpull-highpriority/
    │   └── fetch-tasks.sh                 ← REFERENCE IMPLEMENTATION
    ├── todoist-write/                     ← conversion 1
    │   ├── find-tasks.sh
    │   └── add-task.sh
    ├── gmail-fetch/                       ← conversion 2
    │   ├── refresh-token.sh               ← shared by gcal-fetch (Google OAuth)
    │   ├── search-emails.sh
    │   └── read-email.sh
    └── gcal-fetch/                        ← conversion 3
        └── list-events.sh
```
