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

**Status:** Not started  
**Affects:** `Projects/email-to-todoist-tasks/SKILL.md`

### Goal
Replace MCP `find-tasks` + `add-tasks` calls with direct Todoist REST API scripts.

### Context
- `email-to-todoist-tasks` runs daily at 7 PM via cloud RemoteTrigger
- Currently calls MCP `find-tasks` to dedup-check before adding, then `add-tasks` to create tasks
- Todoist Personal project ID: `6Crg6xfrxV9Pj3x8`
- Auth: `TODOIST_API_TOKEN` already in Keychain (used by `fetch-tasks.sh` — no setup needed)
- Todoist API docs: `https://developer.todoist.com/rest/v2/`

### Scripts to Create

**`skills/todoist-write/find-tasks.sh`**
- Args: `--query <string>` `--project-id <id>`
- Calls: `GET https://api.todoist.com/rest/v2/tasks?project_id=<id>` then filters by content match
- Or use filter endpoint: `GET https://api.todoist.com/api/v1/tasks/filter?query=<query>`
- Returns: JSON array of matching tasks (id, content, due, priority)
- Use case: dedup check before adding a new task

**`skills/todoist-write/add-task.sh`**
- Args: `--content <string>` `--due-string <string>` `--description <string>` `--project-id <id>`
- Calls: `POST https://api.todoist.com/rest/v2/tasks`
- Body: JSON with content, due_string, description, project_id
- Returns: created task JSON
- Use case: add an actionable email as a Todoist task

### SKILL.md Update
Replace in `email-to-todoist-tasks/SKILL.md`:
- MCP `find-tasks` call → `bash /path/to/find-tasks.sh --query "..." --project-id 6Crg6xfrxV9Pj3x8`
- MCP `add-tasks` call → `bash /path/to/add-task.sh --content "..." --due-string "..." --description "..." --project-id 6Crg6xfrxV9Pj3x8`

### Verification
1. `bash skills/todoist-write/find-tasks.sh --query "test" --project-id 6Crg6xfrxV9Pj3x8` → confirm JSON array output
2. `bash skills/todoist-write/add-task.sh --content "Test task" --due-string "today" --description "test" --project-id 6Crg6xfrxV9Pj3x8` → confirm task appears in Todoist app
3. Trigger `email-to-todoist-tasks` manually → verify tasks created, no MCP calls in session

---

## Conversion 2: Gmail Fetch CLI Skill

**Status:** Not started  
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
       'credentials.json',
       scopes=['https://www.googleapis.com/auth/gmail.readonly']
   )
   creds = flow.run_local_server(port=0)
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

### Scripts to Create

**`skills/gmail-fetch/refresh-token.sh`**
- Internal helper — called by other scripts, not directly by SKILL.md
- Reads Keychain credentials, POSTs to `https://oauth2.googleapis.com/token`
- Prints access token to stdout
- Scripts source this or capture its output as `ACCESS_TOKEN=$(bash refresh-token.sh)`

**`skills/gmail-fetch/search-emails.sh`**
- Args: `--query <gmail_search_string>` `--max-results <n>`
- Calls: `GET /messages?q=<query>&maxResults=<n>`
- Returns: JSON array of `{id, threadId, snippet}`

**`skills/gmail-fetch/read-email.sh`**
- Args: `--message-id <id>`
- Calls: `GET /messages/<id>?format=full`
- Returns: JSON with `{subject, from, date, body}` — body decoded from base64, plain text preferred over HTML, stripped to readable text

### SKILL.md Updates (4 files)
Replace all `gmail_search_messages` → `bash .../search-emails.sh --query "..." --max-results N`  
Replace all `gmail_read_message` → `bash .../read-email.sh --message-id <id>`

### Verification
1. `bash skills/gmail-fetch/search-emails.sh --query "is:unread" --max-results 5` → JSON array
2. `bash skills/gmail-fetch/read-email.sh --message-id <id from above>` → readable decoded body
3. Trigger daily-brief manually → email section populates correctly

---

## Conversion 3: Google Calendar Fetch CLI Skill

**Status:** Not started  
**Affects:** `Projects/daily-brief/SKILL.md` (2 calls); also sets up what-now-widget

### Goal
Replace MCP `gcal_list_events` in daily-brief with a direct Calendar API script.

### Context
- Two calendars queried in daily-brief: personal + shared calendar
- Fetches tomorrow's events (00:00–23:59 local time)
- **Shares Google OAuth infrastructure with Gmail** — same Keychain credentials, same `refresh-token.sh` helper. No additional setup if Gmail skill already built.
- One additional step: enable **Google Calendar API** in the same Cloud project used for Gmail
- Calendar REST endpoint: `GET https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events`
- Params: `timeMin`, `timeMax` (RFC3339), `singleEvents=true`, `orderBy=startTime`

### Script to Create

**`skills/gcal-fetch/list-events.sh`**
- Args: `--calendar-id <id>` `--date <YYYY-MM-DD>`
- Calls Calendar API with timeMin/timeMax spanning the full given date in local timezone
- Returns: JSON array of `{title, start, end, location}` — stripped of noise (attendees, raw descriptions)
- Can call `../gmail-fetch/refresh-token.sh` for the access token (shared Google account)

### SKILL.md Update
Replace both `gcal_list_events` calls in `daily-brief/SKILL.md` with:
`bash .../list-events.sh --calendar-id <id> --date <tomorrow>`

### Verification
1. `bash skills/gcal-fetch/list-events.sh --calendar-id primary --date $(date -v+1d +%Y-%m-%d)` → events listed
2. Trigger daily-brief manually → calendar section correct

---

## File Map

```
Personal/
├── Projects/
│   ├── mcp-to-cli-roadmap.md              ← THIS FILE
│   ├── daily-brief/SKILL.md               ← update in conversions 2 + 3
│   ├── email-to-todoist-tasks/SKILL.md    ← update in conversions 1 + 2
│   ├── weekly-newsletter-podcast/SKILL.md ← update in conversion 2
│   └── monthly-comms-maintenance/SKILL.md ← update in conversion 2
└── skills/
    ├── todoist-taskpull-highpriority/
    │   └── fetch-tasks.sh                 ← REFERENCE IMPLEMENTATION
    ├── todoist-write/                     ← CREATE in conversion 1
    │   ├── find-tasks.sh
    │   └── add-task.sh
    ├── gmail-fetch/                       ← CREATE in conversion 2
    │   ├── refresh-token.sh
    │   ├── search-emails.sh
    │   └── read-email.sh
    └── gcal-fetch/                        ← CREATE in conversion 3
        └── list-events.sh
```
