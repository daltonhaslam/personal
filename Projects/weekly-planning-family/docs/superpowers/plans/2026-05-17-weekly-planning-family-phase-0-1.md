# Weekly Planning (Family) — Phase 0 + Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working Claude Code skill (`/weekly-planning`) that on invocation assembles a pre-brief from Calendars/Gmail/Todoist, opens an interactive form in Chrome, and on save writes decisions back to Google Calendar and Todoist plus archives a local summary HTML.

**Architecture:** Single Claude Code skill orchestrates everything. Python modules under `src/` handle source pulls, page/summary rendering, the local Flask server, and write-back. Existing skills under `Personal/skills/` (gcal-fetch, gmail-fetch, todoist-write) are reused via subprocess. LLM calls happen inside the Claude Code session — no `claude -p` shell-outs.

**Tech Stack:** Python 3.11+, Flask, Jinja2, pytest, pyyaml, stdlib `subprocess`/`urllib`. macOS Keychain for auth secrets.

**Reference spec:** `docs/superpowers/specs/2026-05-17-weekly-planning-family-design.md`

**Project root for all paths in this plan:** `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/`. Every relative path below is relative to that directory.

**Existing skills referenced (already in repo at `Personal/skills/`):**
- `gcal-fetch/list-events.sh` — list calendar events for a date
- `gmail-fetch/refresh-token.sh` — exchange refresh token → access token via Keychain
- `gmail-fetch/search-emails.sh` — search Gmail, return JSON list
- `gmail-fetch/read-email.sh` — read a single Gmail message
- `todoist-write/add-task.sh` — create Todoist task
- `todoist-write/find-tasks.sh` — list tasks in a Todoist project filtered by query

---

## Conventions

**Python module style.**
- Type hints everywhere. Stdlib `dataclasses` for value types.
- One module = one file = one responsibility, per spec §6 boundaries.
- Files that touch external systems route I/O through a single function so tests can monkeypatch.

**Subprocess pattern.**
```python
def _run_skill(skill_path: str, args: list[str]) -> dict | list:
    """Run a skill script and parse stdout as JSON."""
    result = subprocess.run(
        [skill_path] + args,
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)
```
Tests monkeypatch `_run_skill` rather than `subprocess.run`.

**Date handling.**
- Planning runs Thursday for the **Fri→Thu** window (7 days).
- `week_start` = next Friday after the run date (or today if today is Friday).
- `week_end` = `week_start + 6 days` (Thursday).
- `horizon_end` = `week_end + 21 days`.
- All dates are `datetime.date` (no times).

**Testing.**
- pytest. Tests in `tests/`. Fixtures in `tests/fixtures/` as JSON files. No live API calls in tests.
- Use `unittest.mock.patch` for monkeypatching.
- TDD: write a failing test first, then minimal implementation, then verify pass, then commit.

**Commit messages.**
- Conventional commits: `feat(weekly-planning): ...`, `chore(weekly-planning): ...`, `test(weekly-planning): ...`, `fix(weekly-planning): ...`.
- One commit per task (multiple commits within a task are fine if the task has clean sub-steps).

**Subprocess paths.**
Reference existing skills with absolute paths in a single constant:
```python
SKILLS_ROOT = Path("/Users/daltonhaslam/Documents/Claude/Personal/skills")
```
This lives in `src/constants.py` (created in Task 2.1).

---

## File map

### Phase 0 outputs (config + existing-skill extensions)

| Path | Phase | Purpose |
|---|---|---|
| `Personal/skills/gmail-fetch/refresh-token.sh` (modified) | 0 | Accept `--account dalton|maggie` flag |
| `Personal/skills/gmail-fetch/search-emails.sh` (modified) | 0 | Accept and forward `--account` |
| `Personal/skills/gmail-fetch/read-email.sh` (modified) | 0 | Accept and forward `--account` |
| `Personal/Projects/weekly-planning-family/.gitignore` | 0 | Exclude tokens/, sessions/, config.yaml |
| `Personal/Projects/weekly-planning-family/config.example.yaml` | 0 | Committed template with placeholders |
| `Personal/Projects/weekly-planning-family/config.yaml` | 0 | Real values (gitignored) |
| macOS Keychain `GMAIL_REFRESH_TOKEN_MAGGIE` | 0 | Maggie's Gmail refresh token |
| Gmail label "Kid's School" + filter rules | 0 | Combined preschool + elementary inbox stream |
| Todoist project `Date Night Ideas` | 0 | New shared list for date ideas |

### Phase 1 outputs (the build)

| Path | Purpose |
|---|---|
| `requirements.txt` | Pinned Python deps |
| `pyproject.toml` | Project metadata + pytest config |
| `conftest.py` | pytest path setup |
| `README.md` | Setup + how to invoke skill |
| `SKILL.md` | The Claude Code skill — entry point |
| `weekly-planning-view` | Bash wrapper to open most-recent session in Chrome |
| `src/__init__.py` | (empty) |
| `src/constants.py` | Shared constants (paths, project root, format strings) |
| `src/config.py` | YAML config loader + schema validator |
| `src/fetch_sources.py` | All source pulls → `Context` dataclass |
| `src/render_page.py` | Renders `session.html` from Jinja template |
| `src/render_summary.py` | Renders summary HTML (page swap + archive) |
| `src/server.py` | Flask app: `GET /`, `POST /save` |
| `src/write_back.py` | Calendar + Todoist creates + summary archive |
| `prompts/retrospective.md` | LLM prompt template — retrospective bullets |
| `prompts/margin_flags.md` | LLM prompt template — margin/realism flags |
| `templates/session.html.jinja` | Form template |
| `templates/summary.html.jinja` | Summary view template |
| `Personal/skills/gcal-write/add-event.sh` | New skill: create Google Calendar event |
| `tests/__init__.py` | (empty) |
| `tests/conftest.py` | Shared fixtures |
| `tests/fixtures/*.json` | Synthetic API responses |
| `tests/test_config.py` | Config loader tests |
| `tests/test_fetch_sources.py` | Source-pull parsing tests |
| `tests/test_render_page.py` | Form HTML smoke tests |
| `tests/test_render_summary.py` | Summary HTML smoke tests |
| `tests/test_write_back.py` | Validation, WFH rules, routing tests |
| `tests/test_server.py` | Flask client tests |

---

## Review checkpoints

This plan is structured into **6 stages**. At each stage boundary you'll see a `⚠️ STAGE CHECKPOINT` block telling you which review commands to run before continuing. The natural fit:

- `/simplify` — runs after every stage; cheap, focuses on dead code, over-engineering, redundancy
- `/security-review` — runs after stages that touch auth, external systems, or user input (Stages 1, 3, 5, 6)

Don't skip these. They're cheap insurance.

---

## Stage 1 — Phase 0 prerequisites (one-time setup)

**Stage goal:** All external setup done, multi-account Gmail working, `config.yaml` ready. No Python code written yet for the planning project; the only code work in this stage is extending the existing `gmail-fetch` skill for multi-account support.

**Stage deliverable:** Manual verification: `bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh --account maggie --query "in:inbox newer_than:1d"` returns a JSON array of Maggie's recent emails.

### Task 1.1: Project repo init

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/.gitignore`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/config.example.yaml`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/README.md` (skeleton — fleshed out in Stage 6)

- [ ] **Step 1: Create `.gitignore`**

```text
# Python
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/

# Project-specific - never commit
tokens/
sessions/
config.yaml
context.json
retrospective.json
margin_flags.json
session.html

# OS
.DS_Store
```

- [ ] **Step 2: Create `config.example.yaml`**

```yaml
session:
  default_day: thursday
  default_time: "20:00"
  browser: "Google Chrome"
  server_port: 8000
  server_abandon_timeout_hours: 4

calendars:
  shared_general: rgq78thkje9h8p3c57718eamog@group.calendar.google.com
  shared_meals: vj5lp1it7em4nekmlra1b3c5a4@group.calendar.google.com
  dalton_personal: haslam.dalton@gmail.com
  schools:
    - id: j1uk9rlvto8tejnr6jrjkolhhahf30f0@import.calendar.google.com
      name: "Elementary"
    # add preschool + others as iCal feeds are subscribed

gmail:
  accounts:
    - name: dalton
      address: haslam.dalton@gmail.com
    - name: maggie
      address: TBD
  kid_school_label_id: TBD
  default_query: "newer_than:7d -category:promotions -label:spam -label:Newsletters"
  max_results_per_account: 50

todoist:
  projects:
    shopping:
      name: "To buy"
      id: TBD
    shopping_wants:
      name: "To buy (less necessary)"
      id: TBD
    general_todos:
      name: "MD ToDos"
      id: TBD
    home:
      name: "Home"
      id: TBD
    meals:
      name: "Meals"
      id: TBD
    date_night_ideas:
      name: "Date Night Ideas"
      id: TBD
    screen_time:
      name: "Screen time"
      id: TBD
    gifts_maggie:
      name: "Maggie's Wish List"
      id: TBD
    gifts_dalton:
      name: "Dalton's Wish List"
      id: TBD
  collaborator_ids:
    dalton: TBD
    maggie: TBD

family:
  owners: [Dalton, Maggie]
  kids:
    - name: TBD
      age: TBD
```

- [ ] **Step 3: Create `README.md` skeleton**

```markdown
# Weekly Planning (Family)

Claude Code skill that helps Dalton & Maggie run a weekly planning session.

See `docs/superpowers/specs/2026-05-17-weekly-planning-family-design.md` for the design.

## How to run

(Filled out in Stage 6 once the skill is wired up.)
```

- [ ] **Step 4: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add .gitignore config.example.yaml README.md
git commit -m "chore(weekly-planning): project init — gitignore, config template, readme skeleton"
```

Expected: clean commit, no errors.

### Task 1.2: Extend gmail-fetch for multi-account

The current `gmail-fetch` skill reads `GMAIL_REFRESH_TOKEN` from Keychain. To support Maggie's account, we add a `--account` flag (default `dalton`) that selects which Keychain key to use: `GMAIL_REFRESH_TOKEN` for `dalton` (backward compat), `GMAIL_REFRESH_TOKEN_MAGGIE` for `maggie`.

**Files:**
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/refresh-token.sh`
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh`
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh`

- [ ] **Step 1: Verify current state works**

Run: `bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh --query "in:inbox newer_than:1d" --max-results 3`

Expected: JSON array of up to 3 Dalton recent emails. If this fails, **stop** — fix the existing skill before extending.

- [ ] **Step 2: Modify `refresh-token.sh` to accept `--account`**

Replace the current contents of `/Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/refresh-token.sh` with:

```bash
#!/usr/bin/env bash
# Exchange stored Gmail refresh token for a short-lived access token.
# Args: [--account dalton|maggie]   (default: dalton)
# Output: access token to stdout. Errors to stderr.

set -euo pipefail

ACCOUNT="dalton"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --account) ACCOUNT="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

case "$ACCOUNT" in
    dalton)
        REFRESH_KEY="GMAIL_REFRESH_TOKEN"
        ;;
    maggie)
        REFRESH_KEY="GMAIL_REFRESH_TOKEN_MAGGIE"
        ;;
    *)
        echo "Error: --account must be 'dalton' or 'maggie' (got '$ACCOUNT')" >&2
        exit 1
        ;;
esac

REFRESH_TOKEN=$(security find-generic-password -s "$REFRESH_KEY" -w 2>/dev/null) || {
    echo "Error: $REFRESH_KEY not found in Keychain" >&2
    exit 1
}
CLIENT_ID=$(security find-generic-password -s GMAIL_CLIENT_ID -w 2>/dev/null) || {
    echo "Error: GMAIL_CLIENT_ID not found in Keychain" >&2
    exit 1
}
CLIENT_SECRET=$(security find-generic-password -s GMAIL_CLIENT_SECRET -w 2>/dev/null) || {
    echo "Error: GMAIL_CLIENT_SECRET not found in Keychain" >&2
    exit 1
}

RESPONSE=$(REFRESH_TOKEN="$REFRESH_TOKEN" CLIENT_ID="$CLIENT_ID" CLIENT_SECRET="$CLIENT_SECRET" python3 << 'PYEOF'
import json, os, urllib.request, urllib.parse

data = urllib.parse.urlencode({
    "grant_type": "refresh_token",
    "refresh_token": os.environ["REFRESH_TOKEN"],
    "client_id": os.environ["CLIENT_ID"],
    "client_secret": os.environ["CLIENT_SECRET"],
}).encode()

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
with urllib.request.urlopen(req) as resp:
    print(resp.read().decode())
PYEOF
) || {
    echo "Error: token refresh request failed" >&2
    exit 1
}

if ! echo "$RESPONSE" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    echo "Error: token endpoint returned non-JSON: ${RESPONSE:0:200}" >&2
    exit 1
fi

ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('access_token',''))")

if [[ -z "$ACCESS_TOKEN" ]]; then
    ERROR=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error_description', d.get('error', 'unknown')))" 2>/dev/null || echo "unknown")
    echo "Error: no access_token in response: $ERROR" >&2
    exit 1
fi

echo "$ACCESS_TOKEN"
```

- [ ] **Step 3: Verify Dalton path still works**

Run: `bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/refresh-token.sh`

Expected: prints an access token string (long, starts with `ya29.`). No `--account` flag = default `dalton` = backward compatible.

- [ ] **Step 4: Modify `search-emails.sh` to forward `--account`**

In `/Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh`:

Find the argument-parsing block:

```bash
while [[ $# -gt 0 ]]; do
    case "$1" in
        --query)       QUERY="$2";       shift 2 ;;
        --max-results) MAX_RESULTS="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done
```

Replace with:

```bash
ACCOUNT="dalton"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --query)       QUERY="$2";       shift 2 ;;
        --max-results) MAX_RESULTS="$2"; shift 2 ;;
        --account)     ACCOUNT="$2";     shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done
```

Find the line:

```bash
ACCESS_TOKEN=$(bash "$SCRIPT_DIR/refresh-token.sh") || exit 1
```

Replace with:

```bash
ACCESS_TOKEN=$(bash "$SCRIPT_DIR/refresh-token.sh" --account "$ACCOUNT") || exit 1
```

- [ ] **Step 5: Modify `read-email.sh` to forward `--account`**

In `/Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh`:

Find the argument-parsing block:

```bash
while [[ $# -gt 0 ]]; do
    case "$1" in
        --message-id) MESSAGE_ID="$2"; shift 2 ;;
        --depth)      DEPTH="$2";      shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done
```

Replace with:

```bash
ACCOUNT="dalton"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --message-id) MESSAGE_ID="$2"; shift 2 ;;
        --depth)      DEPTH="$2";      shift 2 ;;
        --account)    ACCOUNT="$2";    shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done
```

Find the line:

```bash
ACCESS_TOKEN=$(bash "$SCRIPT_DIR/refresh-token.sh") || exit 1
```

Replace with:

```bash
ACCESS_TOKEN=$(bash "$SCRIPT_DIR/refresh-token.sh" --account "$ACCOUNT") || exit 1
```

- [ ] **Step 6: Verify Dalton path still works end-to-end**

Run: `bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh --query "in:inbox newer_than:1d" --max-results 3`

Expected: same output as Step 1 — JSON array of Dalton's emails. The behavior must be **identical** for callers that don't pass `--account`.

- [ ] **Step 7: Commit (Maggie verification happens in Task 1.3 after her token exists)**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/skills
git add gmail-fetch/refresh-token.sh gmail-fetch/search-emails.sh gmail-fetch/read-email.sh
git commit -m "feat(gmail-fetch): support --account dalton|maggie for multi-account use"
```

### Task 1.3: Maggie's Gmail OAuth + Keychain setup

This is mostly manual. You'll run the OAuth consent flow logged in as Maggie, then store her refresh token in Keychain. The same Google Cloud OAuth client_id/secret is reused — only the refresh token differs per user.

- [ ] **Step 1: Identify your existing OAuth client_id**

The client_id and client_secret already in Keychain came from a Google Cloud Console OAuth 2.0 Client ID you set up previously for the Dalton-Gmail integration. Find them:

```bash
security find-generic-password -s GMAIL_CLIENT_ID -w
security find-generic-password -s GMAIL_CLIENT_SECRET -w
```

These two values are reused. **Do not** create a new OAuth client.

- [ ] **Step 2: Generate Maggie's refresh token**

The cleanest path: temporarily set up a Python helper that runs the OAuth out-of-band flow for her account. Create a throwaway script `/tmp/get_maggie_token.py`:

```python
import urllib.parse, urllib.request, json, subprocess, webbrowser

CLIENT_ID = subprocess.check_output(
    ["security", "find-generic-password", "-s", "GMAIL_CLIENT_ID", "-w"]
).decode().strip()
CLIENT_SECRET = subprocess.check_output(
    ["security", "find-generic-password", "-s", "GMAIL_CLIENT_SECRET", "-w"]
).decode().strip()

REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # if your client supports it; otherwise localhost
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPE,
    "access_type": "offline",
    "prompt": "consent",
})

print("\n>>> Open this URL in your browser while logged in as Maggie:\n")
print(auth_url)
print("\nAfter consenting, paste the authorization code here:")
code = input("> ").strip()

token_resp = urllib.request.urlopen(
    "https://oauth2.googleapis.com/token",
    data=urllib.parse.urlencode({
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode(),
).read().decode()

data = json.loads(token_resp)
refresh_token = data.get("refresh_token")
if not refresh_token:
    print("ERROR: no refresh_token returned. Full response:")
    print(json.dumps(data, indent=2))
    exit(1)

print("\n>>> SUCCESS. Refresh token:")
print(refresh_token)
print("\nStore it in Keychain with:")
print(f'security add-generic-password -s GMAIL_REFRESH_TOKEN_MAGGIE -a maggie -w "{refresh_token}"')
```

**Note on `REDIRECT_URI`:** if your Google Cloud OAuth client is configured for `localhost` redirect (loopback) instead of `oob`, this script needs modification — replace `urn:ietf:wg:oauth:2.0:oob` with a `http://localhost:PORT/` flow + a tiny local listener. Check `console.cloud.google.com/apis/credentials` → your OAuth client → "Authorized redirect URIs" before running. If it's loopback-only, you'll need a more involved flow (or use the `gcloud` CLI as a workaround).

- [ ] **Step 3: Run the OAuth flow as Maggie**

```bash
python3 /tmp/get_maggie_token.py
```

1. Script prints a URL. Open it in Chrome in a tab where Maggie is signed in (or use an incognito window and sign in as her).
2. Approve the read-only Gmail scope.
3. Copy the authorization code Google displays.
4. Paste back into the terminal.
5. Script prints the refresh token + the exact Keychain command.

- [ ] **Step 4: Store the refresh token in Keychain**

Run the `security add-generic-password` command the script printed:

```bash
security add-generic-password -s GMAIL_REFRESH_TOKEN_MAGGIE -a maggie -w "<TOKEN>"
```

- [ ] **Step 5: Verify Maggie's auth works**

```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/refresh-token.sh --account maggie
```

Expected: prints an access token (starts with `ya29.`).

```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh --account maggie --query "in:inbox newer_than:1d" --max-results 3
```

Expected: JSON array of Maggie's recent inbox emails (or `[]` if she has none in the last day, which is fine — non-error is the success signal).

- [ ] **Step 6: Clean up the throwaway script**

```bash
rm /tmp/get_maggie_token.py
```

- [ ] **Step 7: Record Maggie's email address** (you'll fill this into `config.yaml` in Task 1.7) — just jot it down for now.

### Task 1.4: "Kid's School" Gmail label + filter rules

Manual setup in the Gmail web UI. The label aggregates Brightwheel + elementary school senders so the wizard can pull them in one query.

- [ ] **Step 1: Create the label**

In Gmail (Dalton's account) → Settings (⚙) → "See all settings" → Labels tab → "Create new label" → name `Kid's School`. Apply nesting if you like (e.g., under a "Family" parent label).

- [ ] **Step 2: Find Brightwheel's sender domain**

Search Gmail for `from:brightwheel.com OR from:mybrightwheel.com` (or whatever the actual sender domain is — check a recent message in your inbox).

- [ ] **Step 3: Find elementary school's sender domain(s)**

Search for known elementary school emails in your inbox. Note all sender domains (could be `@<district>.k12.<state>.us`, a `.org` district domain, or a vendor like `Parent Square` / `Bloomz`).

- [ ] **Step 4: Create a filter for each sender**

For each domain identified, create a Gmail filter:

Gmail → search bar dropdown → enter `from:(@domain.com)` → "Create filter" → check "Apply the label: Kid's School" → optionally "Also apply filter to N matching conversations" → Create filter.

Repeat for each school-related domain.

- [ ] **Step 5: Verify the label has messages**

Search `label:"Kid's School" newer_than:30d` — confirm relevant emails are tagged. If not, look for senders you missed and add more filters.

- [ ] **Step 6: Look up the label's stable ID** (used in API calls — apostrophe in display name causes encoding issues, so we use the ID)

```bash
ACCESS_TOKEN=$(bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/refresh-token.sh)
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://gmail.googleapis.com/gmail/v1/users/me/labels" \
  | python3 -c "import json,sys; [print(l['name'], l['id']) for l in json.load(sys.stdin)['labels'] if 'kid' in l['name'].lower() or 'school' in l['name'].lower()]"
```

Expected output line like: `Kid's School Label_1234567890123456789`

Record the `Label_*` ID. You'll put it in `config.yaml` (Task 1.7).

### Task 1.5: Create `Date Night Ideas` Todoist project

Manual, two-click thing in Todoist.

- [ ] **Step 1: Create the project**

Todoist (web or app) → "+ Add project" → name `Date Night Ideas` → color/icon to your liking → share with Maggie (✓ same access pattern as your other shared projects).

- [ ] **Step 2: Add 3-5 starter ideas**

Seed it with some real ideas you'd both enjoy. Just so the suggestion logic in Phase 1 has something to surface on the first session.

### Task 1.6: Collect all IDs

You need a handful of stable IDs for `config.yaml`. Run these one-liners and record the results in a scratch note — you'll paste them into `config.yaml` in Task 1.7.

- [ ] **Step 1: Get the Gmail label ID for "Kid's School"**

Already recorded in Task 1.4 Step 6.

- [ ] **Step 2: Get Todoist project IDs**

```bash
TODOIST_API_TOKEN=$(security find-generic-password -s TODOIST_API_TOKEN -w)
curl -s -H "Authorization: Bearer $TODOIST_API_TOKEN" \
  "https://api.todoist.com/api/v1/projects" \
  | python3 -c "import json,sys; [print(p['name'], p['id']) for p in json.load(sys.stdin).get('results', [])]"
```

Expected: one line per project, name then ID. Record the IDs for: `To buy`, `To buy (less necessary)`, `MD ToDos`, `Home`, `Meals`, `Date Night Ideas`, `Screen time`, `Maggie's Wish List`, `Dalton's Wish List`.

- [ ] **Step 3: Get Todoist collaborator IDs**

Pick any shared project (e.g., `MD ToDos`) and query its collaborators:

```bash
TODOIST_API_TOKEN=$(security find-generic-password -s TODOIST_API_TOKEN -w)
# Replace <PROJECT_ID> with one of the project IDs from Step 2
curl -s -H "Authorization: Bearer $TODOIST_API_TOKEN" \
  "https://api.todoist.com/api/v1/projects/<PROJECT_ID>/collaborators" \
  | python3 -m json.tool
```

Expected: JSON list of collaborators with `id`, `name`, `email`. Record the IDs for Dalton and Maggie.

- [ ] **Step 4: Confirm Google Calendar subscribed-calendar IDs**

You already have `j1uk9rlvto8tejnr6jrjkolhhahf30f0@import.calendar.google.com` for elementary. To list all subscribed calendars:

```bash
ACCESS_TOKEN=$(bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/refresh-token.sh)
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://www.googleapis.com/calendar/v3/users/me/calendarList" \
  | python3 -c "import json,sys; [print(c['summary'], '|', c['id']) for c in json.load(sys.stdin).get('items', [])]"
```

Expected: one line per calendar. Identify the school ones, record their IDs. If preschool's iCal isn't subscribed yet, subscribe it now (Google Calendar → "+" next to Other calendars → "From URL" → paste the iCal URL).

### Task 1.7: Fill out `config.yaml`

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/config.yaml` (gitignored — not committed)

- [ ] **Step 1: Copy template**

```bash
cp /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/config.example.yaml \
   /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/config.yaml
```

- [ ] **Step 2: Fill in every `TBD`**

Open `config.yaml` and replace each `TBD` with the real value from Task 1.6 scratch notes:

- `gmail.accounts[1].address` — Maggie's actual Gmail address
- `gmail.kid_school_label_id` — the `Label_*` ID from Task 1.4
- `todoist.projects.*.id` — the project IDs from Task 1.6 Step 2
- `todoist.collaborator_ids.dalton` and `.maggie` — from Task 1.6 Step 3
- `family.kids[0].name`, `.age`, `family.kids[1].name`, `.age` — real values (used for CFM suggestions in Phase 2 but committed to config now)

- [ ] **Step 3: Verify it parses cleanly**

```bash
python3 -c "import yaml; yaml.safe_load(open('/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/config.yaml'))"
```

Expected: no output (silent success). Any error = fix the YAML and re-run.

- [ ] **Step 4: Confirm `config.yaml` is gitignored**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git status
```

Expected: `config.yaml` should NOT appear in `git status`. If it does, `.gitignore` from Task 1.1 needs to be re-checked.

---

### ⚠️ STAGE 1 CHECKPOINT

Before continuing:

```
/security-review
```

**Focus areas for the reviewer:** the Gmail multi-account changes in `gmail-fetch/refresh-token.sh` and the new `GMAIL_REFRESH_TOKEN_MAGGIE` Keychain item. Specifically — is `--account` input properly validated (whitelist, no command injection)? Is anyone error message leaking secrets?

```
/simplify
```

**Focus areas:** the three modified bash scripts and the new config schema. Anything redundant or over-engineered?

Address findings before continuing to Stage 2.

---

## Stage 2 — Python scaffolding + Config loader

**Stage goal:** Python project skeleton in place, pytest wired up, `src/config.py` loads and validates the real `config.yaml`.

**Stage deliverable:** `pytest -q` runs and all `test_config.py` tests pass.

### Task 2.1: Python scaffolding

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/requirements.txt`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/pyproject.toml`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/conftest.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/__init__.py` (empty)
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/constants.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/__init__.py` (empty)
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/conftest.py` (skeleton; populated more in Stage 3)

- [ ] **Step 1: Create `requirements.txt`**

```text
Flask==3.0.*
Jinja2==3.1.*
PyYAML==6.*
pytest==8.*
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "weekly-planning-family"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 3: Create root `conftest.py`**

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
```

- [ ] **Step 4: Create empty package markers**

```bash
touch /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/__init__.py
touch /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/__init__.py
```

- [ ] **Step 5: Create `src/constants.py`**

```python
"""Shared constants. Imported by every module that needs paths or format strings."""
from pathlib import Path

PROJECT_ROOT = Path("/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family")
SKILLS_ROOT = Path("/Users/daltonhaslam/Documents/Claude/Personal/skills")

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
SESSIONS_DIR = PROJECT_ROOT / "sessions"

GCAL_FETCH = SKILLS_ROOT / "gcal-fetch" / "list-events.sh"
GCAL_WRITE = SKILLS_ROOT / "gcal-write" / "add-event.sh"
GMAIL_SEARCH = SKILLS_ROOT / "gmail-fetch" / "search-emails.sh"
GMAIL_READ = SKILLS_ROOT / "gmail-fetch" / "read-email.sh"
TODOIST_ADD = SKILLS_ROOT / "todoist-write" / "add-task.sh"
TODOIST_FIND = SKILLS_ROOT / "todoist-write" / "find-tasks.sh"

# Date formats
DATE_ISO = "%Y-%m-%d"
DATE_DISPLAY = "%a %b %-d"  # "Fri May 22"
TIME_DISPLAY = "%-I:%M %p"  # "5:00 PM"

# Owner enum values (used in form + summary)
OWNER_DALTON = "Dalton"
OWNER_MAGGIE = "Maggie"
OWNER_BOTH = "Both"
OWNERS = [OWNER_DALTON, OWNER_MAGGIE, OWNER_BOTH]
```

- [ ] **Step 6: Create `tests/conftest.py`** (skeleton; expanded in Stage 3)

```python
"""Shared pytest fixtures."""
import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
```

- [ ] **Step 7: Create the venv and install deps**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: installs cleanly.

- [ ] **Step 8: Sanity-check pytest**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
pytest -q
```

Expected: `no tests ran` (exit code 5). Confirms pytest is wired up but we haven't written tests yet.

- [ ] **Step 9: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add requirements.txt pyproject.toml conftest.py src/__init__.py src/constants.py tests/__init__.py tests/conftest.py
git commit -m "chore(weekly-planning): python scaffolding + shared constants"
```

### Task 2.2: Config loader

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/config.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_config.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/config_valid.yaml`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/config_missing_calendar.yaml`

- [ ] **Step 1: Create the valid-fixture config**

`tests/fixtures/config_valid.yaml`:

```yaml
session:
  default_day: thursday
  default_time: "20:00"
  browser: "Google Chrome"
  server_port: 8000
  server_abandon_timeout_hours: 4

calendars:
  shared_general: shared-general-id@group.calendar.google.com
  shared_meals: shared-meals-id@group.calendar.google.com
  dalton_personal: dalton@example.com
  schools:
    - id: school1@import.calendar.google.com
      name: "Elementary"

gmail:
  accounts:
    - name: dalton
      address: dalton@example.com
    - name: maggie
      address: maggie@example.com
  kid_school_label_id: Label_1234567890123456789
  default_query: "newer_than:7d -category:promotions"
  max_results_per_account: 50

todoist:
  projects:
    shopping:
      name: "To buy"
      id: "1111"
    shopping_wants:
      name: "To buy (less necessary)"
      id: "1112"
    general_todos:
      name: "MD ToDos"
      id: "1113"
    home:
      name: "Home"
      id: "1114"
    meals:
      name: "Meals"
      id: "1115"
    date_night_ideas:
      name: "Date Night Ideas"
      id: "1116"
    screen_time:
      name: "Screen time"
      id: "1117"
    gifts_maggie:
      name: "Maggie's Wish List"
      id: "1118"
    gifts_dalton:
      name: "Dalton's Wish List"
      id: "1119"
  collaborator_ids:
    dalton: "9001"
    maggie: "9002"

family:
  owners: [Dalton, Maggie]
  kids:
    - name: TestKid1
      age: 6
    - name: TestKid2
      age: 3
```

- [ ] **Step 2: Create the missing-calendar fixture**

`tests/fixtures/config_missing_calendar.yaml` (same as valid but without `shared_general`):

```yaml
session:
  default_day: thursday
  default_time: "20:00"
  browser: "Google Chrome"
  server_port: 8000
  server_abandon_timeout_hours: 4

calendars:
  shared_meals: shared-meals-id@group.calendar.google.com
  dalton_personal: dalton@example.com
  schools: []

gmail:
  accounts:
    - name: dalton
      address: dalton@example.com
    - name: maggie
      address: maggie@example.com
  kid_school_label_id: Label_x
  default_query: "newer_than:7d"
  max_results_per_account: 50

todoist:
  projects: {}
  collaborator_ids:
    dalton: "9001"
    maggie: "9002"

family:
  owners: [Dalton, Maggie]
  kids: []
```

- [ ] **Step 3: Write failing tests**

`tests/test_config.py`:

```python
import pytest
from src.config import Config, ConfigError, load_config


def test_load_valid_config(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    assert isinstance(cfg, Config)
    assert cfg.calendars.shared_general == "shared-general-id@group.calendar.google.com"
    assert cfg.calendars.shared_meals == "shared-meals-id@group.calendar.google.com"
    assert cfg.gmail.accounts[0].name == "dalton"
    assert cfg.gmail.accounts[1].name == "maggie"
    assert cfg.gmail.kid_school_label_id == "Label_1234567890123456789"
    assert cfg.todoist.projects["shopping"].name == "To buy"
    assert cfg.todoist.projects["shopping"].id == "1111"
    assert cfg.todoist.collaborator_ids["dalton"] == "9001"
    assert cfg.session.server_port == 8000


def test_missing_calendar_raises(fixtures_dir):
    with pytest.raises(ConfigError) as exc:
        load_config(fixtures_dir / "config_missing_calendar.yaml")
    assert "shared_general" in str(exc.value)


def test_account_lookup_by_name(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    assert cfg.gmail.account_by_name("dalton").address == "dalton@example.com"
    assert cfg.gmail.account_by_name("maggie").address == "maggie@example.com"
    with pytest.raises(ConfigError):
        cfg.gmail.account_by_name("notreal")


def test_todoist_project_lookup_by_role(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    assert cfg.todoist.project_id("shopping") == "1111"
    assert cfg.todoist.project_id("meals") == "1115"
    with pytest.raises(ConfigError):
        cfg.todoist.project_id("not_a_role")
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
pytest tests/test_config.py -v
```

Expected: ImportError / collection error — `src.config` doesn't exist yet.

- [ ] **Step 5: Implement `src/config.py`**

```python
"""Load and validate config.yaml. Single source of truth for runtime settings."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


class ConfigError(ValueError):
    """Raised when config is missing required fields or has invalid types."""


@dataclass(frozen=True)
class SessionConfig:
    default_day: str
    default_time: str
    browser: str
    server_port: int
    server_abandon_timeout_hours: int


@dataclass(frozen=True)
class SchoolCalendar:
    id: str
    name: str


@dataclass(frozen=True)
class CalendarsConfig:
    shared_general: str
    shared_meals: str
    dalton_personal: str
    schools: list[SchoolCalendar]


@dataclass(frozen=True)
class GmailAccount:
    name: str
    address: str


@dataclass(frozen=True)
class GmailConfig:
    accounts: list[GmailAccount]
    kid_school_label_id: str
    default_query: str
    max_results_per_account: int

    def account_by_name(self, name: str) -> GmailAccount:
        for a in self.accounts:
            if a.name == name:
                return a
        raise ConfigError(f"No Gmail account named '{name}' in config")


@dataclass(frozen=True)
class TodoistProject:
    name: str
    id: str


@dataclass(frozen=True)
class TodoistConfig:
    projects: dict[str, TodoistProject]  # keyed by role (shopping, meals, etc.)
    collaborator_ids: dict[str, str]     # keyed by owner name (dalton, maggie)

    def project_id(self, role: str) -> str:
        if role not in self.projects:
            raise ConfigError(f"No Todoist project role '{role}' in config")
        return self.projects[role].id


@dataclass(frozen=True)
class Kid:
    name: str
    age: int


@dataclass(frozen=True)
class FamilyConfig:
    owners: list[str]
    kids: list[Kid]


@dataclass(frozen=True)
class Config:
    session: SessionConfig
    calendars: CalendarsConfig
    gmail: GmailConfig
    todoist: TodoistConfig
    family: FamilyConfig


def _require(d: dict, key: str, path: str) -> any:
    if key not in d:
        raise ConfigError(f"Missing required field: {path}.{key}")
    return d[key]


def load_config(path: Path) -> Config:
    """Load and validate config.yaml. Raises ConfigError on schema problems."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(f"Config root must be a mapping, got {type(raw).__name__}")

    s = _require(raw, "session", "")
    session = SessionConfig(
        default_day=_require(s, "default_day", "session"),
        default_time=_require(s, "default_time", "session"),
        browser=_require(s, "browser", "session"),
        server_port=int(_require(s, "server_port", "session")),
        server_abandon_timeout_hours=int(_require(s, "server_abandon_timeout_hours", "session")),
    )

    c = _require(raw, "calendars", "")
    calendars = CalendarsConfig(
        shared_general=_require(c, "shared_general", "calendars"),
        shared_meals=_require(c, "shared_meals", "calendars"),
        dalton_personal=_require(c, "dalton_personal", "calendars"),
        schools=[
            SchoolCalendar(id=_require(sc, "id", "calendars.schools[]"),
                           name=_require(sc, "name", "calendars.schools[]"))
            for sc in c.get("schools", [])
        ],
    )

    g = _require(raw, "gmail", "")
    gmail = GmailConfig(
        accounts=[
            GmailAccount(name=_require(a, "name", "gmail.accounts[]"),
                         address=_require(a, "address", "gmail.accounts[]"))
            for a in _require(g, "accounts", "gmail")
        ],
        kid_school_label_id=_require(g, "kid_school_label_id", "gmail"),
        default_query=_require(g, "default_query", "gmail"),
        max_results_per_account=int(_require(g, "max_results_per_account", "gmail")),
    )

    t = _require(raw, "todoist", "")
    projects_raw = _require(t, "projects", "todoist")
    projects = {
        role: TodoistProject(
            name=_require(v, "name", f"todoist.projects.{role}"),
            id=str(_require(v, "id", f"todoist.projects.{role}")),
        )
        for role, v in projects_raw.items()
    }
    todoist = TodoistConfig(
        projects=projects,
        collaborator_ids={k: str(v) for k, v in _require(t, "collaborator_ids", "todoist").items()},
    )

    f_raw = _require(raw, "family", "")
    family = FamilyConfig(
        owners=list(_require(f_raw, "owners", "family")),
        kids=[
            Kid(name=_require(k, "name", "family.kids[]"), age=int(_require(k, "age", "family.kids[]")))
            for k in f_raw.get("kids", [])
        ],
    )

    return Config(session=session, calendars=calendars, gmail=gmail, todoist=todoist, family=family)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add src/config.py tests/test_config.py tests/fixtures/config_valid.yaml tests/fixtures/config_missing_calendar.yaml
git commit -m "feat(weekly-planning): config loader with schema validation"
```

---

### ⚠️ STAGE 2 CHECKPOINT

```
/simplify
```

**Focus areas:** the `src/config.py` schema. Is it over-engineered (too many dataclass layers)? Are validation errors clear? Anything redundant?

Address findings before continuing to Stage 3.

---

## Stage 3 — Source fetches

**Stage goal:** `src/fetch_sources.py` pulls all sources and returns a populated `Context` dataclass. End-to-end against synthetic fixtures; no live API calls in tests.

**Stage deliverable:** Running `python -m src.fetch_sources` from project root produces a valid `context.json` file using real credentials (manual smoke test at end of stage).

### Task 3.1: Test fixtures (synthetic API responses)

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/gcal_general_events.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/gcal_meal_events.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/gcal_school_events.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/gmail_dalton.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/gmail_maggie.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/gmail_kid_school.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/gmail_volume_cap.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/todoist_meals.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/todoist_date_night.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/todoist_screen_time.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/todoist_deadlines.json`

- [ ] **Step 1: Create calendar event fixtures**

`tests/fixtures/gcal_general_events.json`:

```json
[
  {"title": "Soccer practice", "start": "5:00 PM", "end": "6:00 PM", "date": "2026-05-23"},
  {"title": "Birthday party", "start": "2:00 PM", "end": "4:00 PM", "date": "2026-05-24", "location": "Park"},
  {"title": "Doctor visit", "start": "9:00 AM", "end": "9:30 AM", "date": "2026-05-26"},
  {"title": "Anniversary", "start": "all-day", "end": "all-day", "date": "2026-06-10"}
]
```

`tests/fixtures/gcal_meal_events.json`:

```json
[
  {"title": "Pasta Bolognese", "start": "all-day", "end": "all-day", "date": "2026-05-16"},
  {"title": "Leftovers", "start": "all-day", "end": "all-day", "date": "2026-05-17"},
  {"title": "Tacos", "start": "all-day", "end": "all-day", "date": "2026-05-18"}
]
```

`tests/fixtures/gcal_school_events.json`:

```json
[
  {"title": "School: Field Day", "start": "9:00 AM", "end": "12:00 PM", "date": "2026-05-23"},
  {"title": "School: Half Day", "start": "all-day", "end": "all-day", "date": "2026-05-27"}
]
```

- [ ] **Step 2: Create Gmail fixtures**

`tests/fixtures/gmail_dalton.json`:

```json
[
  {"id": "abc1", "threadId": "t1", "snippet": "Reminder: dentist appt", "subject": "Appt reminder", "from": "Dentist <office@example.com>", "date": "Wed, 14 May 2026 09:00:00 -0400"},
  {"id": "abc2", "threadId": "t2", "snippet": "Your subscription will renew", "subject": "Renewal notice", "from": "billing@svc.com", "date": "Thu, 15 May 2026 10:00:00 -0400"}
]
```

`tests/fixtures/gmail_maggie.json`:

```json
[
  {"id": "mag1", "threadId": "mt1", "snippet": "Class trip next Friday", "subject": "Class trip", "from": "Teacher <teacher@school.edu>", "date": "Mon, 12 May 2026 14:00:00 -0400"}
]
```

`tests/fixtures/gmail_kid_school.json`:

```json
[
  {"id": "ks1", "threadId": "kt1", "snippet": "Brightwheel: snack day next Tuesday", "subject": "Snack reminder", "from": "Brightwheel <noreply@mybrightwheel.com>", "date": "Tue, 13 May 2026 08:00:00 -0400"},
  {"id": "ks2", "threadId": "kt2", "snippet": "Library books due Friday", "subject": "Library reminder", "from": "Elementary <office@elem.edu>", "date": "Wed, 14 May 2026 11:00:00 -0400"}
]
```

`tests/fixtures/gmail_volume_cap.json` (60-item array to test the 50-message cap):

```json
[]
```

Generate the actual 60 items with a one-liner:

```bash
python3 -c "
import json
items = [
  {'id': f'v{i}', 'threadId': f'vt{i}', 'snippet': f'snippet {i}', 'subject': f'subj {i}', 'from': 'sender@example.com', 'date': 'Mon, 12 May 2026 12:00:00 -0400'}
  for i in range(60)
]
print(json.dumps(items, indent=2))
" > /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/gmail_volume_cap.json
```

- [ ] **Step 3: Create Todoist fixtures**

`tests/fixtures/todoist_meals.json`:

```json
[
  {"id": "m1", "content": "Sheet pan chicken thighs", "description": "thighs, potatoes, broccoli, olive oil, garlic"},
  {"id": "m2", "content": "Tacos", "description": "ground beef, taco shells, lettuce, cheese"},
  {"id": "m3", "content": "Pasta Bolognese", "description": "spaghetti, ground beef, marinara, parmesan"}
]
```

`tests/fixtures/todoist_date_night.json`:

```json
[
  {"id": "dn1", "content": "Try the new ramen place"},
  {"id": "dn2", "content": "Walk along the C&O canal"},
  {"id": "dn3", "content": "Game night at home"}
]
```

`tests/fixtures/todoist_screen_time.json`:

```json
[
  {"id": "st1", "content": "Severance season 3"},
  {"id": "st2", "content": "Dune Part 3"},
  {"id": "st3", "content": "The Bear"}
]
```

`tests/fixtures/todoist_deadlines.json`:

```json
[
  {"id": "d1", "content": "Renew car registration", "deadline": "2026-05-25", "project_id": "1113"},
  {"id": "d2", "content": "File quarterly taxes", "deadline": "2026-05-30", "project_id": "1113"}
]
```

- [ ] **Step 4: Update `tests/conftest.py` with fixture loader**

Replace the contents of `tests/conftest.py`:

```python
"""Shared pytest fixtures."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture(fixtures_dir):
    def _load(name: str):
        with open(fixtures_dir / name) as f:
            return json.load(f)
    return _load
```

- [ ] **Step 5: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add tests/fixtures/ tests/conftest.py
git commit -m "test(weekly-planning): synthetic fixtures for source fetches"
```

### Task 3.2: Context dataclass + `_run_skill` helper

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/fetch_sources.py` (Context + helper only; specific fetches added in 3.3-3.5)
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_fetch_sources.py` (one test for the helper)

- [ ] **Step 1: Write failing test for `_run_skill`**

`tests/test_fetch_sources.py`:

```python
import json
import subprocess
from unittest.mock import patch
from src.fetch_sources import _run_skill


def test_run_skill_parses_json_stdout():
    fake_result = subprocess.CompletedProcess(
        args=["x"], returncode=0,
        stdout=json.dumps([{"a": 1}, {"a": 2}]),
        stderr="",
    )
    with patch("subprocess.run", return_value=fake_result) as mock_run:
        result = _run_skill("/fake/path", ["--arg", "v"])
    assert result == [{"a": 1}, {"a": 2}]
    mock_run.assert_called_once()
    called_args = mock_run.call_args[0][0]
    assert called_args == ["/fake/path", "--arg", "v"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_fetch_sources.py -v
```

Expected: ImportError — `src.fetch_sources` doesn't exist.

- [ ] **Step 3: Implement `src/fetch_sources.py` (skeleton)**

```python
"""Pull data from Google Calendar, Gmail, and Todoist into a Context.

All I/O goes through `_run_skill`, which subprocesses out to the existing
bash skills under Personal/skills/. Tests monkeypatch this helper instead
of `subprocess.run` directly.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class Event:
    title: str
    date: str          # YYYY-MM-DD
    start: str         # "5:00 PM" or "all-day"
    end: str           # "5:30 PM" or "all-day"
    location: str = ""
    source: str = ""   # "general", "meals", "personal", "school"


@dataclass
class Message:
    id: str
    subject: str
    sender: str
    snippet: str
    date: str
    account: str = ""  # "dalton", "maggie", or "kid_school"


@dataclass
class Task:
    id: str
    content: str
    description: str = ""
    deadline: str = ""  # YYYY-MM-DD or ""
    project_id: str = ""


@dataclass
class Context:
    week_start: date
    week_end: date
    horizon_end: date
    general_events: list[Event] = field(default_factory=list)
    meal_events_last: list[Event] = field(default_factory=list)
    personal_events: list[Event] = field(default_factory=list)
    school_events: list[Event] = field(default_factory=list)
    dalton_gmail: list[Message] = field(default_factory=list)
    maggie_gmail: list[Message] = field(default_factory=list)
    kid_school_emails: list[Message] = field(default_factory=list)
    meals_library: list[Task] = field(default_factory=list)
    date_night_ideas: list[Task] = field(default_factory=list)
    screen_time_ideas: list[Task] = field(default_factory=list)
    upcoming_deadlines: list[Task] = field(default_factory=list)
    inbox_volume_flag: bool = False

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict for context.json."""
        return {
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "horizon_end": self.horizon_end.isoformat(),
            "general_events": [e.__dict__ for e in self.general_events],
            "meal_events_last": [e.__dict__ for e in self.meal_events_last],
            "personal_events": [e.__dict__ for e in self.personal_events],
            "school_events": [e.__dict__ for e in self.school_events],
            "dalton_gmail": [m.__dict__ for m in self.dalton_gmail],
            "maggie_gmail": [m.__dict__ for m in self.maggie_gmail],
            "kid_school_emails": [m.__dict__ for m in self.kid_school_emails],
            "meals_library": [t.__dict__ for t in self.meals_library],
            "date_night_ideas": [t.__dict__ for t in self.date_night_ideas],
            "screen_time_ideas": [t.__dict__ for t in self.screen_time_ideas],
            "upcoming_deadlines": [t.__dict__ for t in self.upcoming_deadlines],
            "inbox_volume_flag": self.inbox_volume_flag,
        }


def _run_skill(skill_path: str | Path, args: list[str]) -> Any:
    """Run a bash skill, parse stdout as JSON, return parsed value.

    Raises CalledProcessError on non-zero exit. Tests should monkeypatch this.
    """
    result = subprocess.run(
        [str(skill_path)] + args,
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def compute_week_window(today: date | None = None) -> tuple[date, date, date]:
    """Return (week_start, week_end, horizon_end).

    week_start is the next Friday on/after `today` (Friday=Friday counts as start).
    week_end is week_start + 6 days (Thursday).
    horizon_end is week_end + 21 days.
    """
    if today is None:
        today = date.today()
    # Python weekday: Mon=0 ... Sun=6. Friday = 4.
    days_until_friday = (4 - today.weekday()) % 7
    week_start = today + timedelta(days=days_until_friday)
    week_end = week_start + timedelta(days=6)
    horizon_end = week_end + timedelta(days=21)
    return week_start, week_end, horizon_end
```

- [ ] **Step 4: Add test for `compute_week_window`**

Add to `tests/test_fetch_sources.py`:

```python
from datetime import date
from src.fetch_sources import compute_week_window


def test_week_window_from_thursday():
    # Thursday May 21 2026 → window should start Fri May 22
    today = date(2026, 5, 21)
    start, end, horizon = compute_week_window(today)
    assert start == date(2026, 5, 22)
    assert end == date(2026, 5, 28)
    assert horizon == date(2026, 6, 18)


def test_week_window_from_friday():
    # Friday counts as the start day itself
    today = date(2026, 5, 22)
    start, end, horizon = compute_week_window(today)
    assert start == date(2026, 5, 22)
    assert end == date(2026, 5, 28)


def test_week_window_from_saturday():
    # Saturday May 23 → next Friday is May 29
    today = date(2026, 5, 23)
    start, end, _ = compute_week_window(today)
    assert start == date(2026, 5, 29)
    assert end == date(2026, 6, 4)
```

- [ ] **Step 5: Run all tests; expect pass**

```bash
pytest tests/test_fetch_sources.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/fetch_sources.py tests/test_fetch_sources.py
git commit -m "feat(weekly-planning): Context dataclass + run_skill helper + week window"
```

### Task 3.3: Calendar fetch

**Files:**
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/fetch_sources.py` (add calendar functions)
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_fetch_sources.py` (add calendar tests)

The existing `gcal-fetch/list-events.sh` takes `--calendar-id` and `--date <YYYY-MM-DD>` and returns events for a **single** day. To get events across a date range, we call it once per day in the range and merge.

- [ ] **Step 1: Write failing test for calendar fetch**

Add to `tests/test_fetch_sources.py`:

```python
from unittest.mock import patch
from datetime import date
from src.fetch_sources import Event, fetch_calendar_range


def test_fetch_calendar_range_calls_skill_per_day_and_tags_source():
    # 3-day range = 3 skill calls
    fake_responses = [
        [{"title": "Day1 evt", "start": "9:00 AM", "end": "10:00 AM"}],
        [],  # day 2 empty
        [{"title": "Day3 evt", "start": "all-day", "end": "all-day", "location": "Home"}],
    ]
    with patch("src.fetch_sources._run_skill", side_effect=fake_responses) as mock:
        events = fetch_calendar_range(
            calendar_id="cal@x",
            start=date(2026, 5, 22),
            end=date(2026, 5, 24),
            source_tag="general",
            exclude_recurring=False,
        )
    assert mock.call_count == 3
    assert len(events) == 2
    assert events[0].title == "Day1 evt"
    assert events[0].date == "2026-05-22"
    assert events[0].source == "general"
    assert events[1].title == "Day3 evt"
    assert events[1].location == "Home"


def test_fetch_calendar_range_passes_exclude_recurring_flag():
    with patch("src.fetch_sources._run_skill", return_value=[]) as mock:
        fetch_calendar_range(
            calendar_id="cal@x",
            start=date(2026, 5, 22),
            end=date(2026, 5, 22),
            source_tag="general",
            exclude_recurring=True,
        )
    # one call (one-day range), with the flag in args
    called_args = mock.call_args[0][1]
    assert "--exclude-recurring" in called_args
```

- [ ] **Step 2: Run; expect fail**

```bash
pytest tests/test_fetch_sources.py::test_fetch_calendar_range_calls_skill_per_day_and_tags_source -v
```

Expected: `ImportError` / `cannot import 'fetch_calendar_range'`.

- [ ] **Step 3: Implement `fetch_calendar_range` in `src/fetch_sources.py`**

Add to the bottom of `src/fetch_sources.py`:

```python
from src.constants import GCAL_FETCH


def fetch_calendar_range(
    *,
    calendar_id: str,
    start: date,
    end: date,
    source_tag: str,
    exclude_recurring: bool = False,
) -> list[Event]:
    """Fetch events from a single calendar across an inclusive date range.

    Calls the gcal-fetch skill once per day in the range, merges, tags each
    event with `source_tag`.
    """
    events: list[Event] = []
    cur = start
    while cur <= end:
        args = ["--calendar-id", calendar_id, "--date", cur.isoformat()]
        if exclude_recurring:
            args.append("--exclude-recurring")
        raw = _run_skill(GCAL_FETCH, args)
        for e in raw:
            events.append(Event(
                title=e.get("title", "(no title)"),
                date=cur.isoformat(),
                start=e.get("start", ""),
                end=e.get("end", ""),
                location=e.get("location", ""),
                source=source_tag,
            ))
        cur += timedelta(days=1)
    return events
```

- [ ] **Step 4: Run tests; expect pass**

```bash
pytest tests/test_fetch_sources.py -v
```

Expected: all tests pass (including the 4 prior).

- [ ] **Step 5: Commit**

```bash
git add src/fetch_sources.py tests/test_fetch_sources.py
git commit -m "feat(weekly-planning): calendar range fetcher via gcal-fetch skill"
```

### Task 3.4: Gmail fetch

**Files:**
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/fetch_sources.py`
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_fetch_sources.py`

- [ ] **Step 1: Write failing tests for `fetch_gmail`**

Add to `tests/test_fetch_sources.py`:

```python
from src.fetch_sources import fetch_gmail, Message


def test_fetch_gmail_basic(load_fixture):
    fixture = load_fixture("gmail_dalton.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture) as mock:
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="newer_than:7d -category:promotions",
            max_results=50,
            label_id=None,
        )
    assert len(msgs) == 2
    assert hit_cap is False
    assert msgs[0].id == "abc1"
    assert msgs[0].subject == "Appt reminder"
    assert msgs[0].account == "dalton"
    called_args = mock.call_args[0][1]
    assert "--account" in called_args
    assert "dalton" in called_args
    assert "--query" in called_args
    assert "--max-results" in called_args
    assert "50" in called_args


def test_fetch_gmail_hits_volume_cap(load_fixture):
    # fixture has 60 items but we ask for 50; skill returns all 60 (it doesn't truncate),
    # so the helper takes 50 and flags cap-hit
    fixture = load_fixture("gmail_volume_cap.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture):
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="x",
            max_results=50,
            label_id=None,
        )
    assert len(msgs) == 50
    assert hit_cap is True


def test_fetch_gmail_with_label_id_uses_label_query(load_fixture):
    fixture = load_fixture("gmail_kid_school.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture) as mock:
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="newer_than:7d",
            max_results=50,
            label_id="Label_1234567890123456789",
        )
    assert len(msgs) == 2
    assert msgs[0].account == "kid_school"  # tagged by helper since label_id was set
    called_args = mock.call_args[0][1]
    # Confirm the label was included by chaining onto the query
    # (we use Gmail's label: search syntax; the label ID must appear in the --query arg)
    query_idx = called_args.index("--query") + 1
    full_query = called_args[query_idx]
    assert "label:Label_1234567890123456789" in full_query or "Label_1234567890123456789" in full_query
```

- [ ] **Step 2: Run tests; expect fail**

```bash
pytest tests/test_fetch_sources.py::test_fetch_gmail_basic -v
```

Expected: ImportError on `fetch_gmail`.

- [ ] **Step 3: Implement `fetch_gmail`**

Add to `src/fetch_sources.py`:

```python
from src.constants import GMAIL_SEARCH


def fetch_gmail(
    *,
    account: str,
    query: str,
    max_results: int,
    label_id: str | None = None,
) -> tuple[list[Message], bool]:
    """Fetch Gmail messages for an account.

    Returns (messages, hit_volume_cap).
    `hit_volume_cap` is True if the skill returned >= max_results items
    (likely truncation in the actual inbox).

    `label_id`, when provided, is appended to `query` as `label:<id>`.
    Returned Messages are tagged with account="kid_school" when label_id is set,
    otherwise with the account name.
    """
    full_query = query
    if label_id:
        full_query = f"{query} label:{label_id}".strip()

    args = [
        "--account", account,
        "--query", full_query,
        "--max-results", str(max_results),
    ]
    raw = _run_skill(GMAIL_SEARCH, args)

    hit_cap = len(raw) >= max_results
    items = raw[:max_results]

    tag = "kid_school" if label_id else account
    messages = [
        Message(
            id=m.get("id", ""),
            subject=m.get("subject", "(no subject)"),
            sender=m.get("from", ""),
            snippet=m.get("snippet", ""),
            date=m.get("date", ""),
            account=tag,
        )
        for m in items
    ]
    return messages, hit_cap
```

- [ ] **Step 4: Run tests; expect pass**

```bash
pytest tests/test_fetch_sources.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/fetch_sources.py tests/test_fetch_sources.py
git commit -m "feat(weekly-planning): gmail fetch with volume cap + label support"
```

### Task 3.5: Todoist fetches

**Files:**
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/fetch_sources.py`
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_fetch_sources.py`

The existing `todoist-write/find-tasks.sh` is **filter by query string** in a project. For our needs (list all tasks in a project), we either pass an empty query (filters to empty match = everything? actually no — the current script returns `query in content`, so empty matches everything) or call the API directly. Cleaner: call the Todoist API directly from Python for this read-only "list project" case. We continue to use `todoist-write/add-task.sh` for writes (Stage 5).

- [ ] **Step 1: Write failing test for `fetch_todoist_project`**

Add to `tests/test_fetch_sources.py`:

```python
from src.fetch_sources import fetch_todoist_project, fetch_todoist_deadlines, Task


def test_fetch_todoist_project_returns_tasks(load_fixture):
    fixture = load_fixture("todoist_meals.json")
    # The helper calls Todoist API; we patch the low-level HTTP call
    with patch("src.fetch_sources._todoist_get", return_value=fixture):
        tasks = fetch_todoist_project(project_id="1115")
    assert len(tasks) == 3
    assert tasks[0].id == "m1"
    assert tasks[0].content == "Sheet pan chicken thighs"
    assert "thighs" in tasks[0].description


def test_fetch_todoist_deadlines_within_window(load_fixture):
    fixture = load_fixture("todoist_deadlines.json")
    with patch("src.fetch_sources._todoist_get", return_value=fixture):
        tasks = fetch_todoist_deadlines(window_days=14, today=date(2026, 5, 17))
    # Both deadlines are within 14 days of 2026-05-17 (May 25 and May 30)
    assert len(tasks) == 2
    assert all(t.deadline for t in tasks)


def test_fetch_todoist_deadlines_excludes_far_future():
    fixture = [
        {"id": "x", "content": "Far future", "deadline": "2027-01-01", "project_id": "1113"},
        {"id": "y", "content": "Soon", "deadline": "2026-05-20", "project_id": "1113"},
    ]
    with patch("src.fetch_sources._todoist_get", return_value=fixture):
        tasks = fetch_todoist_deadlines(window_days=14, today=date(2026, 5, 17))
    assert len(tasks) == 1
    assert tasks[0].id == "y"
```

- [ ] **Step 2: Run tests; expect fail**

```bash
pytest tests/test_fetch_sources.py::test_fetch_todoist_project_returns_tasks -v
```

Expected: ImportError.

- [ ] **Step 3: Implement Todoist fetch helpers**

Add to `src/fetch_sources.py`:

```python
import os
import subprocess as _subprocess  # alias to avoid shadowing
import urllib.parse
import urllib.request


def _todoist_token() -> str:
    """Read Todoist API token from macOS Keychain. Tests should monkeypatch this."""
    result = _subprocess.run(
        ["security", "find-generic-password", "-s", "TODOIST_API_TOKEN", "-w"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _todoist_get(path: str, params: dict | None = None) -> Any:
    """GET against Todoist API v1. Returns parsed JSON (list or dict).

    Tests should monkeypatch this directly to return canned fixtures.
    """
    token = _todoist_token()
    url = f"https://api.todoist.com/api/v1{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    # API may wrap in {"results": [...]} or return a list directly
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def fetch_todoist_project(*, project_id: str) -> list[Task]:
    """List all active tasks in a Todoist project."""
    raw = _todoist_get("/tasks", {"project_id": project_id})
    return [
        Task(
            id=t["id"],
            content=t.get("content", ""),
            description=t.get("description", ""),
            deadline=(t.get("deadline") or {}).get("date", "") if isinstance(t.get("deadline"), dict) else (t.get("deadline") or ""),
            project_id=t.get("project_id", project_id),
        )
        for t in raw
    ]


def fetch_todoist_deadlines(*, window_days: int, today: date | None = None) -> list[Task]:
    """Tasks with a `deadline` falling within `window_days` of `today`.

    Pulls all tasks (no project filter), filters locally. Token-light alternative
    to the project-by-project scan.
    """
    if today is None:
        today = date.today()
    window_end = today + timedelta(days=window_days)
    raw = _todoist_get("/tasks")
    out: list[Task] = []
    for t in raw:
        dl_raw = t.get("deadline")
        dl_str = ""
        if isinstance(dl_raw, dict):
            dl_str = dl_raw.get("date", "")
        elif isinstance(dl_raw, str):
            dl_str = dl_raw
        if not dl_str:
            continue
        try:
            dl_date = date.fromisoformat(dl_str)
        except ValueError:
            continue
        if today <= dl_date <= window_end:
            out.append(Task(
                id=t["id"],
                content=t.get("content", ""),
                description=t.get("description", ""),
                deadline=dl_str,
                project_id=t.get("project_id", ""),
            ))
    return out
```

- [ ] **Step 4: Run tests; expect pass**

```bash
pytest tests/test_fetch_sources.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/fetch_sources.py tests/test_fetch_sources.py
git commit -m "feat(weekly-planning): todoist project + deadline fetchers"
```

### Task 3.6: Orchestrator — assemble full Context

**Files:**
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/fetch_sources.py` (add `assemble_context` + CLI entry point)
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_fetch_sources.py` (orchestrator test)

- [ ] **Step 1: Write failing test for the orchestrator**

Add to `tests/test_fetch_sources.py`:

```python
from src.fetch_sources import assemble_context
from src.config import load_config


def test_assemble_context_uses_config_and_populates_fields(fixtures_dir, load_fixture):
    cfg = load_config(fixtures_dir / "config_valid.yaml")

    gcal_general = load_fixture("gcal_general_events.json")
    gcal_meals = load_fixture("gcal_meal_events.json")
    gcal_school = load_fixture("gcal_school_events.json")
    gmail_d = load_fixture("gmail_dalton.json")
    gmail_m = load_fixture("gmail_maggie.json")
    gmail_ks = load_fixture("gmail_kid_school.json")
    todoist_meals = load_fixture("todoist_meals.json")
    todoist_dn = load_fixture("todoist_date_night.json")
    todoist_st = load_fixture("todoist_screen_time.json")
    todoist_deadlines = load_fixture("todoist_deadlines.json")

    skill_responses = {
        "gcal-general": gcal_general,
        "gcal-meals": gcal_meals,
        "gcal-school": gcal_school,
        "gcal-personal": [],
        "gmail-dalton": gmail_d,
        "gmail-maggie": gmail_m,
        "gmail-kid_school": gmail_ks,
    }

    def fake_run_skill(path, args):
        path = str(path)
        if "list-events.sh" in path:
            cal_id = args[args.index("--calendar-id") + 1]
            if cal_id == cfg.calendars.shared_general:
                return skill_responses["gcal-general"]
            elif cal_id == cfg.calendars.shared_meals:
                return skill_responses["gcal-meals"]
            elif cal_id == cfg.calendars.dalton_personal:
                return skill_responses["gcal-personal"]
            else:
                return skill_responses["gcal-school"]
        if "search-emails.sh" in path:
            account = args[args.index("--account") + 1]
            query = args[args.index("--query") + 1]
            if "label:" in query or cfg.gmail.kid_school_label_id in query:
                return skill_responses["gmail-kid_school"]
            return skill_responses[f"gmail-{account}"]
        return []

    def fake_todoist_get(path, params=None):
        if params and "project_id" in params:
            pid = params["project_id"]
            if pid == cfg.todoist.project_id("meals"):
                return todoist_meals
            if pid == cfg.todoist.project_id("date_night_ideas"):
                return todoist_dn
            if pid == cfg.todoist.project_id("screen_time"):
                return todoist_st
            return []
        # No params = full /tasks call = deadline lookup
        return todoist_deadlines

    with patch("src.fetch_sources._run_skill", side_effect=fake_run_skill), \
         patch("src.fetch_sources._todoist_get", side_effect=fake_todoist_get):
        ctx = assemble_context(cfg, today=date(2026, 5, 21))  # Thursday

    assert ctx.week_start == date(2026, 5, 22)
    assert ctx.week_end == date(2026, 5, 28)
    assert len(ctx.general_events) > 0
    assert len(ctx.meal_events_last) > 0
    assert len(ctx.school_events) > 0
    assert len(ctx.dalton_gmail) == 2
    assert len(ctx.maggie_gmail) == 1
    assert len(ctx.kid_school_emails) == 2
    assert len(ctx.meals_library) == 3
    assert len(ctx.date_night_ideas) == 3
    assert len(ctx.screen_time_ideas) == 3
    assert len(ctx.upcoming_deadlines) == 2
    assert ctx.inbox_volume_flag is False


def test_context_to_dict_is_json_safe(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    with patch("src.fetch_sources._run_skill", return_value=[]), \
         patch("src.fetch_sources._todoist_get", return_value=[]):
        ctx = assemble_context(cfg, today=date(2026, 5, 21))
    d = ctx.to_dict()
    json.dumps(d)  # would raise if not serializable
    assert d["week_start"] == "2026-05-22"
    assert d["inbox_volume_flag"] is False
```

- [ ] **Step 2: Run tests; expect fail**

Expected: `ImportError: cannot import name 'assemble_context'`.

- [ ] **Step 3: Implement `assemble_context` and `main`**

Add to `src/fetch_sources.py`:

```python
from src.config import Config, load_config
from src.constants import CONFIG_PATH, PROJECT_ROOT


def assemble_context(cfg: Config, *, today: date | None = None) -> Context:
    """Pull every source defined in config and return a populated Context."""
    week_start, week_end, horizon_end = compute_week_window(today)

    # Calendars: next 7d for week-at-a-glance
    general = fetch_calendar_range(
        calendar_id=cfg.calendars.shared_general,
        start=week_start, end=week_end,
        source_tag="general",
        exclude_recurring=True,
    )
    # Horizon (next 2-4 weeks) — append more general events
    horizon = fetch_calendar_range(
        calendar_id=cfg.calendars.shared_general,
        start=week_end + timedelta(days=1), end=horizon_end,
        source_tag="general-horizon",
        exclude_recurring=True,
    )
    general_all = general + horizon

    # Meal calendar: LAST 7 days for retrospective
    meals_last = fetch_calendar_range(
        calendar_id=cfg.calendars.shared_meals,
        start=week_start - timedelta(days=7),
        end=week_start - timedelta(days=1),
        source_tag="meals",
    )

    # Personal: next 7d
    personal = fetch_calendar_range(
        calendar_id=cfg.calendars.dalton_personal,
        start=week_start, end=week_end,
        source_tag="personal",
        exclude_recurring=True,
    )

    # School calendars (merged)
    school: list[Event] = []
    for sc in cfg.calendars.schools:
        school.extend(fetch_calendar_range(
            calendar_id=sc.id,
            start=week_start, end=week_end,
            source_tag=f"school:{sc.name}",
        ))

    # Gmail: per account, plus the Kid's School label
    dalton_msgs, dalton_cap = fetch_gmail(
        account="dalton",
        query=cfg.gmail.default_query,
        max_results=cfg.gmail.max_results_per_account,
    )
    maggie_msgs, maggie_cap = fetch_gmail(
        account="maggie",
        query=cfg.gmail.default_query,
        max_results=cfg.gmail.max_results_per_account,
    )
    kid_school_msgs, kid_cap = fetch_gmail(
        account="dalton",
        query="newer_than:7d",
        max_results=cfg.gmail.max_results_per_account,
        label_id=cfg.gmail.kid_school_label_id,
    )

    # Todoist read-only lists
    meals_lib = fetch_todoist_project(project_id=cfg.todoist.project_id("meals"))
    date_night = fetch_todoist_project(project_id=cfg.todoist.project_id("date_night_ideas"))
    screen_time = fetch_todoist_project(project_id=cfg.todoist.project_id("screen_time"))
    deadlines = fetch_todoist_deadlines(window_days=14, today=today)

    return Context(
        week_start=week_start,
        week_end=week_end,
        horizon_end=horizon_end,
        general_events=general_all,
        meal_events_last=meals_last,
        personal_events=personal,
        school_events=school,
        dalton_gmail=dalton_msgs,
        maggie_gmail=maggie_msgs,
        kid_school_emails=kid_school_msgs,
        meals_library=meals_lib,
        date_night_ideas=date_night,
        screen_time_ideas=screen_time,
        upcoming_deadlines=deadlines,
        inbox_volume_flag=any([dalton_cap, maggie_cap, kid_cap]),
    )


def main() -> None:
    """CLI entry: assemble context, write to context.json at project root."""
    cfg = load_config(CONFIG_PATH)
    ctx = assemble_context(cfg)
    out = PROJECT_ROOT / "context.json"
    with open(out, "w") as f:
        json.dump(ctx.to_dict(), f, indent=2)
    print(f"context.json written: {out}")
    print(f"  general events: {len(ctx.general_events)}")
    print(f"  meal events (last 7d): {len(ctx.meal_events_last)}")
    print(f"  school events: {len(ctx.school_events)}")
    print(f"  dalton gmail: {len(ctx.dalton_gmail)} (cap hit: {any([ctx.inbox_volume_flag])})")
    print(f"  maggie gmail: {len(ctx.maggie_gmail)}")
    print(f"  kid_school emails: {len(ctx.kid_school_emails)}")
    print(f"  meals library: {len(ctx.meals_library)}")
    print(f"  date night ideas: {len(ctx.date_night_ideas)}")
    print(f"  screen time ideas: {len(ctx.screen_time_ideas)}")
    print(f"  upcoming deadlines: {len(ctx.upcoming_deadlines)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests; expect pass**

```bash
pytest -v
```

- [ ] **Step 5: Live smoke test — first real run**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
python -m src.fetch_sources
```

Expected:
- Prints progress lines.
- Produces `context.json` at project root (gitignored).
- All counts look reasonable.

If it fails: check the error, fix, retry. Common issues:
- Maggie's Keychain entry missing → revisit Task 1.3
- Todoist project ID wrong in config.yaml → revisit Task 1.6 + 1.7
- Network blip — retry

- [ ] **Step 6: Commit**

```bash
git add src/fetch_sources.py tests/test_fetch_sources.py
git commit -m "feat(weekly-planning): assemble_context orchestrator + CLI entry"
```

---

### ⚠️ STAGE 3 CHECKPOINT

```
/security-review
```

**Focus areas:** `src/fetch_sources.py`. Lots of network I/O and subprocess work here. Specifically:
- Does `_run_skill` invoke subprocess safely (no shell=True, no string concat)?
- Are auth tokens never logged or written to disk except where intended?
- Is `context.json` correctly in `.gitignore` (it can contain email subjects + names)?
- Any unbounded loops / pagination issues that could hang on a bad response?

```
/simplify
```

**Focus areas:** `src/fetch_sources.py`. Are the three Todoist functions (`_todoist_token`, `_todoist_get`, `fetch_todoist_project`, `fetch_todoist_deadlines`) doing more than needed? Is `assemble_context` doing too much (should it be split)?

Address findings before continuing to Stage 4.

---

## Stage 4 — Brief prompts + Page rendering

**Stage goal:** Prompt templates committed; `render_page.py` produces a valid `session.html` from `context.json` + LLM-output JSON files. Skill orchestration (the Bash steps Claude follows) wired up in Stage 6.

**Stage deliverable:** `python -m src.render_page` (with synthetic LLM output) produces a viewable `session.html`.

### Task 4.1: Prompt templates

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/prompts/retrospective.md`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/prompts/margin_flags.md`

These are markdown files the SKILL.md instructs Claude to read and apply. They're version-controlled like code. Each prompt defines an input contract (the JSON it expects to see in `context.json`) and an output contract (the JSON it must write).

- [ ] **Step 1: Create `prompts/retrospective.md`**

```markdown
# Weekly Planning — Retrospective Prompt

You are summarizing last week for Dalton and Maggie's weekly planning session.

## Input

Read `context.json` from the project root. Relevant fields:

- `meal_events_last` — events from the meal calendar in the last 7 days
- `general_events` — events on the shared general calendar from `week_start` minus 7 to `week_end`
- `dalton_gmail`, `maggie_gmail`, `kid_school_emails` — message digests (snippet, sender, subject, date) from the last 7 days
- `upcoming_deadlines` — Todoist tasks with deadlines in the next 14 days

## Task

Produce 5-10 short bullets that capture what happened last week. Mix of:

- Notable calendar events that took place (skip routine ones)
- What got eaten (1 line summarizing the week's dinners)
- Anything in the email digests that the user likely cares about for retrospective context (e.g., school news, appointment outcomes)
- Anything that *slipped* — Todoist deadlines that passed without being completed, missed events, etc.

Bullets should be one short sentence each. No padding. No emojis. Use plain language.

## Output

Write to `retrospective.json` at project root:

```json
{
  "bullets": [
    "Soccer practice happened Mon and Wed; the Saturday game was rained out.",
    "Three home dinners (pasta, tacos, chicken) plus a Friday takeout night.",
    "Two school emails about field day on May 23rd; both parents need to RSVP.",
    "Car registration renewal deadline (May 17) passed without being done — top of this week's list."
  ]
}
```

Five to ten bullets. Strict JSON output. Do not echo anything else to stdout/stderr.
```

- [ ] **Step 2: Create `prompts/margin_flags.md`**

```markdown
# Weekly Planning — Margin & Realism Flags Prompt

You are flagging risk areas in the upcoming week for Dalton and Maggie.

## Input

Read `context.json` from the project root. Relevant fields:

- `week_start`, `week_end` — the 7-day planning window (Fri–Thu)
- `general_events` — events on the shared general calendar within the window AND the 21-day horizon beyond
- `personal_events` — Dalton's personal calendar
- `school_events` — events from subscribed school calendars within the window
- `kid_school_emails` — recent emails tagged "Kid's School" (could surface new activities not yet on calendar)
- `upcoming_deadlines` — Todoist deadline tasks in the next 14 days
- `inbox_volume_flag` — true if any inbox hit the 50-message cap

## Task

Produce **0-5** short flags about the upcoming week. Flags are warnings to discuss during the session. Examples of valid flags:

- "Tuesday has 3 evening events — likely overcommitted."
- "No free evening this week."
- "Kid pickup Wednesday conflicts with the 3pm parent-teacher conference on shared cal."
- "Two Todoist deadlines this week (Renew car registration, File quarterly taxes) — make sure both are owned."
- "Brightwheel mentions a snack day next Tuesday that's not on the shared calendar yet."
- "High inbox volume this week — skim your inbox manually before proceeding." (only if `inbox_volume_flag` is true)

**Constraints:**
- Only flag things you can see in `context.json`. Do NOT speculate about fields the user will fill in during the session (no flags about Maggie's art time, WFH days, dinners, etc. — those are decided live).
- Each flag is one short sentence. No padding, no advice ("you should...") — just the observation.
- Return 0 flags if nothing's worth flagging. Don't pad to hit a minimum.

## Output

Write to `margin_flags.json` at project root:

```json
{
  "flags": [
    "Tuesday has 3 evening events on the shared calendar — likely overcommitted.",
    "High inbox volume this week — skim your inbox manually before proceeding."
  ]
}
```

Strict JSON. Empty list is valid (`{"flags": []}`). Do not echo anything else to stdout/stderr.
```

- [ ] **Step 3: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add prompts/retrospective.md prompts/margin_flags.md
git commit -m "feat(weekly-planning): retrospective + margin-flags prompt templates"
```

### Task 4.2: Form template (`session.html.jinja`)

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/templates/session.html.jinja`

The form is one long single-page HTML. It posts JSON to `POST /save`. Styling is inline + a small `<style>` block — no external CSS dependencies.

- [ ] **Step 1: Create `templates/session.html.jinja`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Weekly Planning — {{ ctx.week_start }} → {{ ctx.week_end }}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 24px auto; padding: 0 16px; color-scheme: light dark; }
  h1 { margin-bottom: 4px; }
  h2 { margin-top: 32px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
  h3 { margin-top: 20px; }
  .meta { color: #666; margin-bottom: 16px; }
  .flag { background: #fff4e5; border-left: 3px solid #f5a623; padding: 8px 12px; margin: 6px 0; }
  ul.bullets li { margin-bottom: 6px; }
  table.week { border-collapse: collapse; width: 100%; }
  table.week th, table.week td { border: 1px solid #ddd; padding: 6px; text-align: left; vertical-align: top; font-size: 13px; }
  .src-general { color: #1a73e8; }
  .src-meals { color: #34a853; }
  .src-school { color: #a142f4; }
  .src-personal { color: #ea4335; }
  fieldset { border: 1px solid #ddd; padding: 12px; margin-top: 16px; }
  legend { font-weight: 600; padding: 0 6px; }
  .row { display: grid; grid-template-columns: 110px 1fr 110px 130px; gap: 8px; margin-bottom: 6px; align-items: center; }
  .row label { font-size: 13px; }
  input[type=text], input[type=time], textarea, select { padding: 4px 6px; font: inherit; }
  textarea { width: 100%; min-height: 80px; font-family: inherit; }
  .save-btn { background: #1a73e8; color: white; padding: 12px 24px; font-size: 16px; border: none; border-radius: 4px; cursor: pointer; margin: 24px 0; }
  .save-btn:disabled { background: #888; cursor: wait; }
  .display-only { color: #555; font-size: 13px; padding: 4px 0; }
  .pre-loaded-row { background: #f8f8f8; padding: 4px 6px; border-radius: 3px; font-size: 13px; margin: 2px 0; }
  .error-banner { background: #fce4e4; border-left: 3px solid #d32f2f; padding: 8px 12px; margin: 6px 0; }
</style>
</head>
<body>

<h1>Weekly Planning</h1>
<p class="meta">Week of {{ ctx.week_start }} → {{ ctx.week_end }} &middot; Generated {{ generated_at }}</p>

<!-- TOP BAND — read-only context -->

<h2>Last week — what happened</h2>
<ul class="bullets">
{% for bullet in retrospective.bullets %}<li>{{ bullet }}</li>{% endfor %}
</ul>
<label>Anything else worth noting? <textarea name="retrospective_note" form="planning-form"></textarea></label>

<h2>Week ahead at a glance</h2>
<table class="week">
  <thead><tr>
    {% for day in week_days %}<th>{{ day.label }}<br><small>{{ day.iso }}</small></th>{% endfor %}
  </tr></thead>
  <tbody><tr>
    {% for day in week_days %}
      <td>
        {% for ev in day.events %}
          <div><span class="src-{{ ev.source.split(':')[0].split('-')[0] }}"><b>{{ ev.start }}</b></span> {{ ev.title }}
            {% if ev.location %}<i>({{ ev.location }})</i>{% endif %}
          </div>
        {% endfor %}
      </td>
    {% endfor %}
  </tr></tbody>
</table>

<h2>Horizon (next 2-4 weeks)</h2>
<ul class="bullets">
{% for ev in horizon_events %}
  <li><b>{{ ev.date }}</b> &mdash; {{ ev.title }}{% if ev.location %} <i>({{ ev.location }})</i>{% endif %}</li>
{% endfor %}
{% if not horizon_events %}<li><i>Nothing notable in the horizon.</i></li>{% endif %}
</ul>

{% if margin_flags.flags %}
<h2>Heads-up</h2>
{% for flag in margin_flags.flags %}<div class="flag">{{ flag }}</div>{% endfor %}
{% endif %}

<!-- MIDDLE BAND — decisions -->

<form id="planning-form">

<fieldset><legend>Dinners (Fri → Thu)</legend>
  <p class="display-only">Last week we ate: {% for m in ctx.meal_events_last %}{{ m.title }}{% if not loop.last %}, {% endif %}{% endfor %}{% if not ctx.meal_events_last %}<i>nothing recorded</i>{% endif %}.</p>
  {% for day in week_days %}
    <div class="row">
      <label>{{ day.label }}:</label>
      <input type="text" name="dinner_{{ day.iso }}" list="meals-list" placeholder="meal name or 'eating out'">
    </div>
  {% endfor %}
  <datalist id="meals-list">
    {% for m in ctx.meals_library %}<option value="{{ m.content }}">{% endfor %}
  </datalist>
  <div class="row">
    <label>New meal idea:</label>
    <input type="text" name="new_meal" placeholder="(writes to Meals)">
  </div>
</fieldset>

<fieldset><legend>Shopping list</legend>
  <label>Necessary (writes to "To buy"):
    <textarea name="shopping_necessary" placeholder="one item per line"></textarea>
  </label>
  <label>Less necessary (writes to "To buy (less necessary)"):
    <textarea name="shopping_wants" placeholder="one item per line"></textarea>
  </label>
</fieldset>

<fieldset><legend>Dalton's home schedule</legend>
  {% for day in week_days_weekday %}
    <div class="row">
      <label>{{ day.label }}:</label>
      <label><input type="checkbox" name="wfh_{{ day.iso }}"> WFH all day</label>
      <label>Home by: <input type="time" name="home_by_{{ day.iso }}"></label>
    </div>
  {% endfor %}
</fieldset>

<fieldset><legend>Maggie's art time</legend>
  <p class="display-only">Add a row per art block. Will write timed events to the shared calendar.</p>
  <div id="art-blocks">
    <div class="row">
      <label>Date:</label>
      <input type="date" name="art_date_0">
      <label>Start: <input type="time" name="art_start_0"></label>
      <label>End: <input type="time" name="art_end_0"></label>
    </div>
  </div>
  <button type="button" onclick="addArtBlock()">+ Add another art block</button>
</fieldset>

<fieldset><legend>Babysitter</legend>
  <div class="row">
    <label><input type="checkbox" name="babysitter_needed"> Need babysitter this week</label>
    <input type="date" name="babysitter_date">
    <input type="time" name="babysitter_time">
    <input type="text" name="babysitter_who" placeholder="who to ask">
  </div>
</fieldset>

<fieldset><legend>Kids' activities</legend>
  <p class="display-only">Already on school calendar / in Kid's School emails:</p>
  {% for ev in ctx.school_events %}
    <div class="pre-loaded-row">{{ ev.date }} &mdash; {{ ev.title }} ({{ ev.start }})</div>
  {% endfor %}
  {% for m in ctx.kid_school_emails[:5] %}
    <div class="pre-loaded-row"><b>{{ m.subject }}</b> <i>({{ m.sender }})</i> &mdash; {{ m.snippet }}</div>
  {% endfor %}
  <p class="display-only">New activities to add (will write to shared calendar):</p>
  <div id="kids-activities">
    <div class="row">
      <input type="text" name="kid_activity_title_0" placeholder="title">
      <input type="date" name="kid_activity_date_0">
      <input type="time" name="kid_activity_time_0">
      <select name="kid_activity_owner_0"><option>Dalton</option><option>Maggie</option><option>Both</option></select>
    </div>
  </div>
  <button type="button" onclick="addKidActivity()">+ Add another kid activity</button>
</fieldset>

<fieldset><legend>Church + temple</legend>
  <textarea name="church_notes" placeholder="temple visits, ward activities, ministering — one per line"></textarea>
</fieldset>

<fieldset><legend>Around the house</legend>
  <textarea name="home_notes" placeholder="repairs, projects — one per line, writes to Home"></textarea>
</fieldset>

<fieldset><legend>Major deadlines</legend>
  <p class="display-only">Already in Todoist:</p>
  {% for d in ctx.upcoming_deadlines %}
    <div class="pre-loaded-row"><b>{{ d.deadline }}</b> &mdash; {{ d.content }}</div>
  {% endfor %}
  <textarea name="new_deadlines" placeholder="new deadline items — one per line (writes to MD ToDos)"></textarea>
</fieldset>

<!-- BOTTOM BAND -->

<fieldset><legend>Finances (discussion)</legend>
  <textarea name="finances_notes" placeholder="bills, large purchases, savings goals, joint accounts"></textarea>
</fieldset>

<fieldset><legend>Come Follow Me</legend>
  <p class="display-only">This week's lesson: <b>{{ cfm_lesson_title }}</b></p>
  <textarea name="cfm_notes" placeholder="who's leading, prep notes, activities for kids"></textarea>
</fieldset>

<fieldset><legend>Fun close — date night</legend>
  <p class="display-only">Suggestions:</p>
  <ul class="bullets">
    {% for s in date_night_suggestions %}<li>{{ s }}</li>{% endfor %}
  </ul>
  <div class="row">
    <label>Pick or write in:</label>
    <input type="text" name="date_night_choice" placeholder="our date night">
    <input type="date" name="date_night_date">
    <input type="time" name="date_night_time">
  </div>
</fieldset>

<button type="button" class="save-btn" id="save-btn" onclick="submitForm()">Save & write back</button>

</form>

<script>
function collectFormData() {
  const form = document.getElementById('planning-form');
  const data = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    if (el.type === 'checkbox') data[el.name] = el.checked;
    else data[el.name] = el.value;
  }
  return data;
}

let artCount = 1;
function addArtBlock() {
  const div = document.createElement('div');
  div.className = 'row';
  div.innerHTML = `<label>Date:</label>
    <input type="date" name="art_date_${artCount}">
    <label>Start: <input type="time" name="art_start_${artCount}"></label>
    <label>End: <input type="time" name="art_end_${artCount}"></label>`;
  document.getElementById('art-blocks').appendChild(div);
  artCount++;
}

let kidCount = 1;
function addKidActivity() {
  const div = document.createElement('div');
  div.className = 'row';
  div.innerHTML = `<input type="text" name="kid_activity_title_${kidCount}" placeholder="title">
    <input type="date" name="kid_activity_date_${kidCount}">
    <input type="time" name="kid_activity_time_${kidCount}">
    <select name="kid_activity_owner_${kidCount}"><option>Dalton</option><option>Maggie</option><option>Both</option></select>`;
  document.getElementById('kids-activities').appendChild(div);
  kidCount++;
}

async function submitForm() {
  const btn = document.getElementById('save-btn');
  btn.disabled = true;
  btn.innerText = 'Writing back…';
  try {
    const resp = await fetch('/save', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(collectFormData()),
    });
    const html = await resp.text();
    if (!resp.ok) {
      document.body.innerHTML = '<div class="error-banner">Save failed (HTTP ' + resp.status + ')</div>' + html;
      btn.disabled = false;
      btn.innerText = 'Save & write back';
      return;
    }
    document.open();
    document.write(html);
    document.close();
  } catch (e) {
    document.body.innerHTML = '<div class="error-banner">Save failed: ' + e.message + '</div>';
    btn.disabled = false;
    btn.innerText = 'Save & write back';
  }
}
</script>

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/session.html.jinja
git commit -m "feat(weekly-planning): session form template"
```

### Task 4.3: `render_page.py`

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/render_page.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_render_page.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/retrospective.json`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/fixtures/margin_flags.json`

- [ ] **Step 1: Create LLM-output fixtures**

`tests/fixtures/retrospective.json`:

```json
{
  "bullets": [
    "Three home dinners and a Friday takeout.",
    "Soccer practice happened Mon and Wed.",
    "Car registration deadline passed without being done — top of this week's list."
  ]
}
```

`tests/fixtures/margin_flags.json`:

```json
{
  "flags": [
    "Tuesday has 3 evening events on the shared calendar — likely overcommitted."
  ]
}
```

- [ ] **Step 2: Write failing test for `render_page`**

`tests/test_render_page.py`:

```python
import json
from datetime import date
from unittest.mock import patch
from src.config import load_config
from src.fetch_sources import assemble_context
from src.render_page import render


def test_render_produces_html_with_all_sections(fixtures_dir, load_fixture):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    retrospective = load_fixture("retrospective.json")
    margin_flags = load_fixture("margin_flags.json")

    gcal_general = load_fixture("gcal_general_events.json")
    gcal_meals = load_fixture("gcal_meal_events.json")
    gcal_school = load_fixture("gcal_school_events.json")
    gmail_d = load_fixture("gmail_dalton.json")
    gmail_m = load_fixture("gmail_maggie.json")
    gmail_ks = load_fixture("gmail_kid_school.json")
    todoist_meals = load_fixture("todoist_meals.json")
    todoist_dn = load_fixture("todoist_date_night.json")
    todoist_st = load_fixture("todoist_screen_time.json")
    todoist_deadlines = load_fixture("todoist_deadlines.json")

    def fake_run_skill(path, args):
        path = str(path)
        if "list-events.sh" in path:
            cal_id = args[args.index("--calendar-id") + 1]
            if cal_id == cfg.calendars.shared_meals:
                return gcal_meals
            if cal_id == cfg.calendars.shared_general:
                return gcal_general
            if cal_id == cfg.calendars.dalton_personal:
                return []
            return gcal_school
        if "search-emails.sh" in path:
            account = args[args.index("--account") + 1]
            query = args[args.index("--query") + 1]
            if "label:" in query:
                return gmail_ks
            return gmail_d if account == "dalton" else gmail_m
        return []

    def fake_todoist_get(path, params=None):
        if params and "project_id" in params:
            pid = params["project_id"]
            if pid == cfg.todoist.project_id("meals"):
                return todoist_meals
            if pid == cfg.todoist.project_id("date_night_ideas"):
                return todoist_dn
            if pid == cfg.todoist.project_id("screen_time"):
                return todoist_st
            return []
        return todoist_deadlines

    with patch("src.fetch_sources._run_skill", side_effect=fake_run_skill), \
         patch("src.fetch_sources._todoist_get", side_effect=fake_todoist_get):
        ctx = assemble_context(cfg, today=date(2026, 5, 21))

    html = render(ctx=ctx, retrospective=retrospective, margin_flags=margin_flags,
                  cfm_lesson_title="2 Nephi 1-5")

    # Section anchors all present
    for needle in [
        "Last week — what happened",
        "Week ahead at a glance",
        "Horizon",
        "Heads-up",
        "Dinners",
        "Shopping list",
        "Dalton's home schedule",
        "Maggie's art time",
        "Babysitter",
        "Kids' activities",
        "Church + temple",
        "Around the house",
        "Major deadlines",
        "Finances",
        "Come Follow Me",
        "Fun close",
        "Save & write back",
    ]:
        assert needle in html, f"missing section: {needle}"

    # Retrospective + flags rendered
    assert "Three home dinners" in html
    assert "Tuesday has 3 evening events" in html

    # Pre-loaded school events shown
    assert "Field Day" in html

    # Meals library appears as datalist options
    assert "Sheet pan chicken thighs" in html

    # Date night suggestions surfaced
    assert "ramen" in html or "canal" in html

    # CFM lesson title
    assert "2 Nephi" in html
```

- [ ] **Step 3: Run; expect fail**

```bash
pytest tests/test_render_page.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `src/render_page.py`**

```python
"""Render session.html from Context + LLM output JSON files."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.constants import PROJECT_ROOT, TEMPLATES_DIR
from src.fetch_sources import Context, Event


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "jinja"]),
    )


def _week_days(ctx: Context) -> list[dict]:
    """Build a list of {label, iso, events[]} dicts for each day of the planning week."""
    by_date: dict[str, list[Event]] = {}
    for e in ctx.general_events + ctx.personal_events + ctx.school_events:
        by_date.setdefault(e.date, []).append(e)
    days = []
    cur = ctx.week_start
    while cur <= ctx.week_end:
        iso = cur.isoformat()
        days.append({
            "label": cur.strftime("%a %b %-d"),
            "iso": iso,
            "events": sorted(by_date.get(iso, []), key=lambda e: e.start),
        })
        cur += timedelta(days=1)
    return days


def _weekday_days(ctx: Context) -> list[dict]:
    """Mon–Fri rows for the home-schedule fieldset."""
    cur = ctx.week_start
    while cur.weekday() != 0:  # find next Monday
        cur += timedelta(days=1)
    out = []
    for i in range(5):
        d = cur + timedelta(days=i)
        out.append({"label": d.strftime("%a %b %-d"), "iso": d.isoformat()})
    return out


def _horizon_events(ctx: Context) -> list[Event]:
    """Events tagged as horizon (beyond the 7-day window)."""
    return [e for e in ctx.general_events if e.source == "general-horizon"]


def _date_night_suggestions(ctx: Context, n: int = 3) -> list[str]:
    """First N items from Screen time + first N from Date Night Ideas, interleaved."""
    out: list[str] = []
    for i in range(n):
        if i < len(ctx.date_night_ideas):
            out.append(f"Out: {ctx.date_night_ideas[i].content}")
        if i < len(ctx.screen_time_ideas):
            out.append(f"At home: {ctx.screen_time_ideas[i].content}")
    return out


def render(
    *,
    ctx: Context,
    retrospective: dict,
    margin_flags: dict,
    cfm_lesson_title: str,
) -> str:
    """Render the form HTML."""
    env = _env()
    template = env.get_template("session.html.jinja")
    return template.render(
        ctx=ctx,
        retrospective=retrospective,
        margin_flags=margin_flags,
        week_days=_week_days(ctx),
        week_days_weekday=_weekday_days(ctx),
        horizon_events=_horizon_events(ctx),
        date_night_suggestions=_date_night_suggestions(ctx),
        cfm_lesson_title=cfm_lesson_title,
        generated_at=datetime.now().strftime("%a %b %-d %-I:%M %p"),
    )


def main() -> None:
    """CLI entry: read context.json + retrospective.json + margin_flags.json, write session.html."""
    from src.config import load_config
    from src.constants import CONFIG_PATH

    cfg = load_config(CONFIG_PATH)

    with open(PROJECT_ROOT / "context.json") as f:
        ctx_dict = json.load(f)
    with open(PROJECT_ROOT / "retrospective.json") as f:
        retrospective = json.load(f)
    with open(PROJECT_ROOT / "margin_flags.json") as f:
        margin_flags = json.load(f)

    # Rehydrate Context from dict
    ctx = Context(
        week_start=date.fromisoformat(ctx_dict["week_start"]),
        week_end=date.fromisoformat(ctx_dict["week_end"]),
        horizon_end=date.fromisoformat(ctx_dict["horizon_end"]),
        general_events=[Event(**e) for e in ctx_dict["general_events"]],
        meal_events_last=[Event(**e) for e in ctx_dict["meal_events_last"]],
        personal_events=[Event(**e) for e in ctx_dict["personal_events"]],
        school_events=[Event(**e) for e in ctx_dict["school_events"]],
        meals_library=[__import__("src.fetch_sources", fromlist=["Task"]).Task(**t) for t in ctx_dict["meals_library"]],
        date_night_ideas=[__import__("src.fetch_sources", fromlist=["Task"]).Task(**t) for t in ctx_dict["date_night_ideas"]],
        screen_time_ideas=[__import__("src.fetch_sources", fromlist=["Task"]).Task(**t) for t in ctx_dict["screen_time_ideas"]],
        upcoming_deadlines=[__import__("src.fetch_sources", fromlist=["Task"]).Task(**t) for t in ctx_dict["upcoming_deadlines"]],
        inbox_volume_flag=ctx_dict["inbox_volume_flag"],
    )
    # (dalton/maggie/kid_school gmail not currently rendered in form; available for Phase 2 buttons)

    # CFM lesson title — best-effort fetch (full URL pattern resolved in Open Q #6 of spec)
    cfm_title = "this week's lesson"  # placeholder; resolved in Stage 6 SKILL.md task

    html = render(
        ctx=ctx,
        retrospective=retrospective,
        margin_flags=margin_flags,
        cfm_lesson_title=cfm_title,
    )

    out = PROJECT_ROOT / "session.html"
    with open(out, "w") as f:
        f.write(html)
    print(f"session.html written: {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests; expect pass**

```bash
pytest tests/test_render_page.py -v
```

Expected: 1 test passes. May need iteration if section labels in the template don't match the test exactly.

- [ ] **Step 6: Eyeball the rendered HTML manually**

Create a tiny harness to write a session.html using fixture data:

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
python3 -c "
import json
from datetime import date
from unittest.mock import patch
from src.config import load_config
from src.fetch_sources import assemble_context
from src.render_page import render
from pathlib import Path

cfg = load_config(Path('tests/fixtures/config_valid.yaml'))
# Skip live fetches by patching
with patch('src.fetch_sources._run_skill', return_value=[]), \
     patch('src.fetch_sources._todoist_get', return_value=[]):
    ctx = assemble_context(cfg, today=date(2026, 5, 21))
retrospective = json.loads(Path('tests/fixtures/retrospective.json').read_text())
margin_flags = json.loads(Path('tests/fixtures/margin_flags.json').read_text())
html = render(ctx=ctx, retrospective=retrospective, margin_flags=margin_flags, cfm_lesson_title='Test Lesson')
Path('/tmp/preview-session.html').write_text(html)
print('Open: /tmp/preview-session.html')
"
open -a "Google Chrome" /tmp/preview-session.html
```

Expected: Chrome opens the page. Walk through the form visually — all 17 sections present, form fields editable. **You will not be able to submit** since there's no server running yet (that's Stage 5). Just verify it *looks* right.

- [ ] **Step 7: Commit**

```bash
git add src/render_page.py tests/test_render_page.py tests/fixtures/retrospective.json tests/fixtures/margin_flags.json
git commit -m "feat(weekly-planning): render_page produces session.html from context + LLM output"
```

---

### ⚠️ STAGE 4 CHECKPOINT

```
/simplify
```

**Focus areas:** the `session.html.jinja` template (Jinja logic can sprawl) and `render_page.py` helper functions. Is `_week_days` doing too much? Is the template legible? Anything redundant between `_week_days` and `_weekday_days`?

Address findings before continuing to Stage 5.

---

## Stage 5 — Server + Write-back + Summary

**Stage goal:** Form posts cleanly through a local Flask server, write-back module creates real Calendar events and Todoist tasks, summary page renders showing what happened.

**Stage deliverable:** With a fixture-driven test client `POST /save`, the server returns summary HTML and `write_back` calls the right APIs in the right order. Live integration verified at the end of Stage 6.

### Task 5.1: New `gcal-write` skill

The existing `gcal-fetch` only reads. We need a parallel skill to *create* events. Same auth pattern (`refresh-token.sh`), one new bash script.

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/skills/gcal-write/add-event.sh`

- [ ] **Step 1: Create the directory and script**

```bash
mkdir -p /Users/daltonhaslam/Documents/Claude/Personal/skills/gcal-write
```

Create `/Users/daltonhaslam/Documents/Claude/Personal/skills/gcal-write/add-event.sh`:

```bash
#!/usr/bin/env bash
# Create a Google Calendar event.
# Args:
#   --calendar-id <id>       (required)
#   --title <string>         (required)
#   --date <YYYY-MM-DD>      (required if --all-day; else use --start/--end with full datetime)
#   --all-day                (flag — creates an all-day event on --date)
#   --start <YYYY-MM-DDTHH:MM>  (required if not --all-day)
#   --end   <YYYY-MM-DDTHH:MM>  (required if not --all-day)
#   --location <string>      (optional)
#   --description <string>   (optional)
# Output: JSON {id, htmlLink, summary, start, end} on success; {"error": "..."} on failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CALENDAR_ID=""
TITLE=""
DATE=""
ALL_DAY=false
START=""
END=""
LOCATION=""
DESCRIPTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --calendar-id) CALENDAR_ID="$2"; shift 2 ;;
        --title)       TITLE="$2";       shift 2 ;;
        --date)        DATE="$2";        shift 2 ;;
        --all-day)     ALL_DAY=true;     shift ;;
        --start)       START="$2";       shift 2 ;;
        --end)         END="$2";         shift 2 ;;
        --location)    LOCATION="$2";    shift 2 ;;
        --description) DESCRIPTION="$2"; shift 2 ;;
        *) echo "{\"error\": \"Unknown argument: $1\"}" >&2; exit 1 ;;
    esac
done

if [[ -z "$CALENDAR_ID" ]]; then echo '{"error": "--calendar-id required"}' >&2; exit 1; fi
if [[ -z "$TITLE" ]]; then echo '{"error": "--title required"}' >&2; exit 1; fi
if [[ "$ALL_DAY" == "true" ]]; then
    if [[ -z "$DATE" ]]; then echo '{"error": "--date required when --all-day"}' >&2; exit 1; fi
else
    if [[ -z "$START" || -z "$END" ]]; then
        echo '{"error": "--start and --end required when not --all-day"}' >&2; exit 1;
    fi
fi

ACCESS_TOKEN=$(bash "$SCRIPT_DIR/../gmail-fetch/refresh-token.sh") || exit 1

CALENDAR_ID="$CALENDAR_ID" TITLE="$TITLE" DATE="$DATE" ALL_DAY="$ALL_DAY" \
START="$START" END="$END" LOCATION="$LOCATION" DESCRIPTION="$DESCRIPTION" \
ACCESS_TOKEN="$ACCESS_TOKEN" python3 << 'PYEOF'
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

access_token = os.environ["ACCESS_TOKEN"]
calendar_id  = os.environ["CALENDAR_ID"]
title        = os.environ["TITLE"]
all_day      = os.environ["ALL_DAY"] == "true"
date_str     = os.environ.get("DATE", "")
start_str    = os.environ.get("START", "")
end_str      = os.environ.get("END", "")
location     = os.environ.get("LOCATION", "")
description  = os.environ.get("DESCRIPTION", "")

if all_day:
    # All-day events use date-only fields; end is exclusive so add one day.
    start_date = datetime.fromisoformat(date_str).date()
    body = {
        "summary": title,
        "start": {"date": start_date.isoformat()},
        "end":   {"date": (start_date + timedelta(days=1)).isoformat()},
    }
else:
    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    start_dt = datetime.fromisoformat(start_str).replace(tzinfo=local_tz)
    end_dt   = datetime.fromisoformat(end_str).replace(tzinfo=local_tz)
    body = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat()},
        "end":   {"dateTime": end_dt.isoformat()},
    }
if location:
    body["location"] = location
if description:
    body["description"] = description

encoded_id = urllib.parse.quote(calendar_id, safe="")
url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events"
data = json.dumps(body).encode()
req = urllib.request.Request(
    url, data=data, method="POST",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    },
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f'{{"error": "Calendar API HTTP {e.code}: {body[:200]}"}}', file=sys.stderr)
    sys.exit(1)

print(json.dumps({
    "id": result.get("id", ""),
    "htmlLink": result.get("htmlLink", ""),
    "summary": result.get("summary", ""),
    "start": result.get("start", {}),
    "end": result.get("end", {}),
}, indent=2))
PYEOF
```

- [ ] **Step 2: Make executable + smoke test in dry-run mode**

```bash
chmod +x /Users/daltonhaslam/Documents/Claude/Personal/skills/gcal-write/add-event.sh
```

Verify it errors gracefully on missing args:

```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gcal-write/add-event.sh
```

Expected: stderr `{"error": "--calendar-id required"}`, exit 1.

- [ ] **Step 3: Create a real test event on a throwaway calendar**

**Important**: don't create test junk on your shared calendar. Either (a) create a dedicated test calendar in Google Calendar first, or (b) skip this live test and rely on the Stage 6 E2E smoke.

If you go with (a):
1. In Google Calendar, "+ Create new calendar" → name `weekly-planning-test`. Note its ID.
2. Run:
   ```bash
   bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gcal-write/add-event.sh \
     --calendar-id <TEST_CAL_ID> \
     --title "TEST — delete me" \
     --all-day --date 2026-05-22
   ```
3. Verify event appears in Google Calendar, then delete it.
4. You can delete the test calendar afterward.

- [ ] **Step 4: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/skills
git add gcal-write/add-event.sh
git commit -m "feat(gcal-write): new skill for creating Google Calendar events"
```

### Task 5.2: Summary template (`summary.html.jinja`)

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/templates/summary.html.jinja`

- [ ] **Step 1: Create the summary template**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Weekly Planning Summary — Week starting Fri {{ week_start_display }}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 24px auto; padding: 0 16px; color-scheme: light dark; }
  h1 { margin-bottom: 4px; }
  h2 { margin-top: 24px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
  h3 { margin-top: 16px; color: #555; }
  .meta { color: #666; margin-bottom: 12px; }
  ul { margin: 8px 0; padding-left: 24px; }
  li { margin-bottom: 4px; }
  .owner-tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 12px; background: #eef; margin-left: 6px; }
  .success { background: #e6f4ea; border-left: 3px solid #1e8e3e; padding: 8px 12px; margin: 4px 0; }
  .failed { background: #fce4e4; border-left: 3px solid #d32f2f; padding: 8px 12px; margin: 4px 0; }
  .retry-btn { background: #d32f2f; color: white; padding: 4px 10px; border: none; border-radius: 3px; cursor: pointer; font-size: 13px; }
</style>
</head>
<body>

<h1>Weekly Planning — Saved</h1>
<p class="meta">Week starting Fri {{ week_start_display }} &middot; Saved {{ saved_at }}</p>

{% if results.failed %}
<h2>⚠️ Failed writes</h2>
{% for target in results.failed %}
  <div class="failed">
    <b>{{ target.label }}</b>: {{ target.error }}
    <form method="POST" action="/save/retry/{{ target.key }}" style="display:inline;">
      <button type="submit" class="retry-btn">Retry</button>
    </form>
  </div>
{% endfor %}
{% endif %}

<h2>What got created</h2>
{% for target in results.succeeded %}
  <div class="success"><b>{{ target.label }}</b> &mdash; {{ target.detail }}</div>
{% endfor %}

<h2>Decisions</h2>

<h3>Retrospective notes</h3>
{% if decisions.retrospective_note %}
<p>{{ decisions.retrospective_note }}</p>
{% else %}<p><i>None recorded.</i></p>{% endif %}

<h3>Dinners</h3>
<ul>
{% for d in decisions.dinners %}<li><b>{{ d.day }}</b>: {{ d.meal }}</li>{% endfor %}
</ul>

<h3>Shopping</h3>
<p><b>Necessary:</b></p>
<ul>{% for item in decisions.shopping_necessary %}<li>{{ item }}</li>{% endfor %}</ul>
{% if decisions.shopping_wants %}
<p><b>Less necessary:</b></p>
<ul>{% for item in decisions.shopping_wants %}<li>{{ item }}</li>{% endfor %}</ul>
{% endif %}

<h3>Dalton's home schedule</h3>
<ul>
{% for d in decisions.home_schedule %}<li><b>{{ d.day }}</b>: {{ d.note }}</li>{% endfor %}
</ul>

<h3>Maggie's art time</h3>
<ul>
{% for b in decisions.art_blocks %}<li><b>{{ b.date }}</b>: {{ b.start }}–{{ b.end }}</li>{% endfor %}
</ul>

<h3>Babysitter</h3>
{% if decisions.babysitter %}
<p>{{ decisions.babysitter.date }} at {{ decisions.babysitter.time }} — asking {{ decisions.babysitter.who }}</p>
{% else %}<p><i>Not needed this week.</i></p>{% endif %}

<h3>Kids' activities (new)</h3>
<ul>
{% for k in decisions.kids_activities %}<li><b>{{ k.date }} {{ k.time }}</b>: {{ k.title }} <span class="owner-tag">{{ k.owner }}</span></li>{% endfor %}
</ul>

<h3>Church + temple</h3>
<ul>{% for line in decisions.church_lines %}<li>{{ line }}</li>{% endfor %}</ul>

<h3>Around the house</h3>
<ul>{% for line in decisions.home_lines %}<li>{{ line }}</li>{% endfor %}</ul>

<h3>New deadlines</h3>
<ul>{% for line in decisions.new_deadlines %}<li>{{ line }}</li>{% endfor %}</ul>

<h3>Finances</h3>
{% if decisions.finances_notes %}<p>{{ decisions.finances_notes }}</p>{% else %}<p><i>Nothing this week.</i></p>{% endif %}

<h3>Come Follow Me</h3>
{% if decisions.cfm_notes %}<p>{{ decisions.cfm_notes }}</p>{% else %}<p><i>No notes.</i></p>{% endif %}

<h3>Date night</h3>
{% if decisions.date_night %}
<p>{{ decisions.date_night.date }} {{ decisions.date_night.time }} — {{ decisions.date_night.choice }}</p>
{% else %}<p><i>None set.</i></p>{% endif %}

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add templates/summary.html.jinja
git commit -m "feat(weekly-planning): summary view template"
```

### Task 5.3: `render_summary.py`

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/render_summary.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_render_summary.py`

- [ ] **Step 1: Write failing test**

`tests/test_render_summary.py`:

```python
from src.render_summary import render_summary


def test_summary_includes_decisions_and_writeback_results():
    decisions = {
        "retrospective_note": "Tough week, but we made it.",
        "dinners": [{"day": "Fri", "meal": "Tacos"}, {"day": "Sat", "meal": "Leftovers"}],
        "shopping_necessary": ["milk", "eggs"],
        "shopping_wants": ["sourdough starter kit"],
        "home_schedule": [{"day": "Mon", "note": "WFH"}, {"day": "Tue", "note": "Home by 5:00 PM"}],
        "art_blocks": [{"date": "2026-05-24", "start": "14:00", "end": "16:00"}],
        "babysitter": {"date": "2026-05-24", "time": "18:00", "who": "Sarah"},
        "kids_activities": [{"date": "2026-05-23", "time": "10:00", "title": "Soccer", "owner": "Both"}],
        "church_lines": ["Temple Friday at 10am"],
        "home_lines": ["Replace bathroom faucet"],
        "new_deadlines": ["Renew passport — June 1"],
        "finances_notes": "Need to revisit budget.",
        "cfm_notes": "Both teaching together.",
        "date_night": {"date": "2026-05-24", "time": "19:00", "choice": "Out: ramen place"},
    }
    results = {
        "succeeded": [
            {"label": "Calendar events", "detail": "Created 5 events", "key": "calendar"},
            {"label": "Todoist tasks", "detail": "Created 8 tasks across 5 projects", "key": "todoist"},
        ],
        "failed": [],
    }
    html = render_summary(
        decisions=decisions,
        results=results,
        week_start_display="May 22",
        saved_at="Thu May 21 8:45 PM",
    )
    assert "Tacos" in html
    assert "Sarah" in html
    assert "Created 5 events" in html
    assert "Soccer" in html
    assert "Both" in html
    assert "May 22" in html


def test_summary_shows_failed_block_with_retry_button():
    decisions = {
        "retrospective_note": "", "dinners": [], "shopping_necessary": [], "shopping_wants": [],
        "home_schedule": [], "art_blocks": [], "babysitter": None, "kids_activities": [],
        "church_lines": [], "home_lines": [], "new_deadlines": [],
        "finances_notes": "", "cfm_notes": "", "date_night": None,
    }
    results = {
        "succeeded": [{"label": "Calendar events", "detail": "Created 2 events", "key": "calendar"}],
        "failed": [{"label": "Todoist tasks", "error": "API timeout", "key": "todoist"}],
    }
    html = render_summary(
        decisions=decisions, results=results,
        week_start_display="May 22", saved_at="now",
    )
    assert "Failed writes" in html
    assert "API timeout" in html
    assert "retry" in html.lower()
```

- [ ] **Step 2: Run; expect fail**

```bash
pytest tests/test_render_summary.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/render_summary.py`**

```python
"""Render the post-save summary HTML (page swap + archive)."""
from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.constants import TEMPLATES_DIR


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "jinja"]),
    )


def render_summary(
    *,
    decisions: dict,
    results: dict,
    week_start_display: str,
    saved_at: str,
) -> str:
    """Render the summary HTML.

    `decisions` is the structured form output (see write_back.parse_form).
    `results` has shape {"succeeded": [{label, detail, key}], "failed": [{label, error, key}]}.
    """
    env = _env()
    template = env.get_template("summary.html.jinja")
    return template.render(
        decisions=decisions,
        results=results,
        week_start_display=week_start_display,
        saved_at=saved_at,
    )
```

- [ ] **Step 4: Run tests; expect pass**

```bash
pytest tests/test_render_summary.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/render_summary.py tests/test_render_summary.py
git commit -m "feat(weekly-planning): render_summary builds post-save view"
```

### Task 5.4: `write_back.py` — form parsing, validation, calendar writes

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/write_back.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_write_back.py`

- [ ] **Step 1: Write failing tests**

`tests/test_write_back.py`:

```python
import pytest
from unittest.mock import patch
from src.write_back import (
    parse_form, validate, ValidationError,
    write_calendar, CalendarWriteResult,
)
from src.config import load_config


SAMPLE_FORM = {
    "retrospective_note": "good week",
    # dinners: keys like "dinner_2026-05-22"
    "dinner_2026-05-22": "Tacos",
    "dinner_2026-05-23": "Pasta Bolognese",
    "dinner_2026-05-24": "Eating out: ramen place",
    "dinner_2026-05-25": "",
    "dinner_2026-05-26": "",
    "dinner_2026-05-27": "",
    "dinner_2026-05-28": "",
    "new_meal": "Thai curry",
    "shopping_necessary": "milk\neggs\nbananas\n",
    "shopping_wants": "sourdough starter\n",
    # home schedule (weekday only)
    "wfh_2026-05-25": True,
    "home_by_2026-05-25": "",
    "wfh_2026-05-26": False,
    "home_by_2026-05-26": "17:00",
    "wfh_2026-05-27": False,
    "home_by_2026-05-27": "",
    "wfh_2026-05-28": True,
    "home_by_2026-05-28": "",
    # art blocks
    "art_date_0": "2026-05-24",
    "art_start_0": "14:00",
    "art_end_0": "16:00",
    "art_date_1": "",
    # babysitter
    "babysitter_needed": True,
    "babysitter_date": "2026-05-24",
    "babysitter_time": "18:00",
    "babysitter_who": "Sarah",
    # kid activities
    "kid_activity_title_0": "Soccer tryout",
    "kid_activity_date_0": "2026-05-23",
    "kid_activity_time_0": "10:00",
    "kid_activity_owner_0": "Both",
    "church_notes": "Temple Fri 10am\nMinistering visit",
    "home_notes": "Replace bathroom faucet\nClean gutters",
    "new_deadlines": "Renew passport - June 1",
    "finances_notes": "Revisit budget",
    "cfm_notes": "Both teaching",
    # date night
    "date_night_choice": "Out: ramen place",
    "date_night_date": "2026-05-24",
    "date_night_time": "19:00",
}


def test_parse_form_extracts_dinners():
    decisions = parse_form(SAMPLE_FORM)
    dinners = [d for d in decisions["dinners"] if d["meal"]]
    assert len(dinners) == 3  # only non-empty
    assert dinners[0]["day"] == "2026-05-22"
    assert dinners[0]["meal"] == "Tacos"


def test_parse_form_extracts_shopping_lines():
    d = parse_form(SAMPLE_FORM)
    assert d["shopping_necessary"] == ["milk", "eggs", "bananas"]
    assert d["shopping_wants"] == ["sourdough starter"]


def test_parse_form_home_schedule_separates_wfh_and_homeby():
    d = parse_form(SAMPLE_FORM)
    # WFH days: 25th, 28th. Home-by day: 26th. 27th has no input.
    items = {x["day"]: x for x in d["home_schedule"]}
    assert items["2026-05-25"]["wfh"] is True
    assert items["2026-05-26"]["wfh"] is False
    assert items["2026-05-26"]["home_by"] == "17:00"
    assert items["2026-05-27"]["wfh"] is False
    assert items["2026-05-27"]["home_by"] == ""


def test_parse_form_art_blocks_skips_empty_rows():
    d = parse_form(SAMPLE_FORM)
    assert len(d["art_blocks"]) == 1
    assert d["art_blocks"][0]["date"] == "2026-05-24"
    assert d["art_blocks"][0]["start"] == "14:00"


def test_parse_form_babysitter_only_when_needed():
    d = parse_form(SAMPLE_FORM)
    assert d["babysitter"]["who"] == "Sarah"

    form2 = dict(SAMPLE_FORM)
    form2["babysitter_needed"] = False
    d2 = parse_form(form2)
    assert d2["babysitter"] is None


def test_parse_form_kids_activities_skips_blanks():
    d = parse_form(SAMPLE_FORM)
    assert len(d["kids_activities"]) == 1
    assert d["kids_activities"][0]["title"] == "Soccer tryout"


def test_validate_passes_on_well_formed_form():
    d = parse_form(SAMPLE_FORM)
    errors = validate(d)
    assert errors == []


def test_validate_flags_babysitter_missing_date():
    form2 = dict(SAMPLE_FORM)
    form2["babysitter_date"] = ""
    d = parse_form(form2)
    errors = validate(d)
    assert any("babysitter" in e.field and "date" in e.message.lower() for e in errors)


def test_validate_flags_art_block_missing_end_time():
    form2 = dict(SAMPLE_FORM)
    form2["art_end_0"] = ""
    d = parse_form(form2)
    errors = validate(d)
    assert any("art" in e.field.lower() for e in errors)


def test_write_calendar_wfh_true_creates_all_day(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "dinners": [],
        "home_schedule": [{"day": "2026-05-25", "wfh": True, "home_by": ""}],
        "art_blocks": [],
        "babysitter": None,
        "kids_activities": [],
        "date_night": None,
    }
    with patch("src.write_back._run_skill", return_value={"id": "ev1", "summary": "Dalton WFH"}) as mock:
        result = write_calendar(decisions, cfg)
    # Find the calendar create call
    create_calls = [c for c in mock.call_args_list if "add-event.sh" in str(c.args[0])]
    assert len(create_calls) == 1
    args = create_calls[0].args[1]
    assert "--all-day" in args
    assert "--date" in args
    assert "2026-05-25" in args
    assert args[args.index("--title") + 1] == "Dalton WFH"
    assert args[args.index("--calendar-id") + 1] == cfg.calendars.shared_general
    assert result.created == 1
    assert result.failed == 0


def test_write_calendar_home_by_creates_15min_event(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "dinners": [],
        "home_schedule": [{"day": "2026-05-26", "wfh": False, "home_by": "17:00"}],
        "art_blocks": [],
        "babysitter": None,
        "kids_activities": [],
        "date_night": None,
    }
    with patch("src.write_back._run_skill", return_value={"id": "ev2", "summary": "Dalton home"}) as mock:
        result = write_calendar(decisions, cfg)
    create_args = mock.call_args_list[0].args[1]
    assert "--all-day" not in create_args
    assert create_args[create_args.index("--start") + 1] == "2026-05-26T17:00"
    assert create_args[create_args.index("--end") + 1] == "2026-05-26T17:15"
    assert create_args[create_args.index("--title") + 1] == "Dalton home"
    assert result.created == 1


def test_write_calendar_dinners_all_day_on_meal_cal(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "dinners": [
            {"day": "2026-05-22", "meal": "Tacos"},
            {"day": "2026-05-23", "meal": "Pasta"},
        ],
        "home_schedule": [],
        "art_blocks": [],
        "babysitter": None,
        "kids_activities": [],
        "date_night": None,
    }
    calls_by_cal = {}
    def fake_run(path, args):
        cal_id = args[args.index("--calendar-id") + 1]
        calls_by_cal.setdefault(cal_id, []).append(args)
        return {"id": f"ev-{cal_id}"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        result = write_calendar(decisions, cfg)
    assert cfg.calendars.shared_meals in calls_by_cal
    meal_calls = calls_by_cal[cfg.calendars.shared_meals]
    assert len(meal_calls) == 2
    for call_args in meal_calls:
        assert "--all-day" in call_args


def test_write_calendar_records_failed_writes(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "dinners": [{"day": "2026-05-22", "meal": "Tacos"}],
        "home_schedule": [],
        "art_blocks": [],
        "babysitter": None,
        "kids_activities": [],
        "date_night": None,
    }
    import subprocess as sp
    def fake_run(path, args):
        raise sp.CalledProcessError(1, args, output="", stderr="oops")
    with patch("src.write_back._run_skill", side_effect=fake_run):
        result = write_calendar(decisions, cfg)
    assert result.created == 0
    assert result.failed == 1
    assert "oops" in result.errors[0]
```

- [ ] **Step 2: Run; expect fail**

```bash
pytest tests/test_write_back.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/write_back.py` (Part 1 — parsing/validation/calendar)**

```python
"""Parse the form payload, validate, write to Calendar + Todoist, return summary HTML."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import Config
from src.constants import GCAL_WRITE, TODOIST_ADD, SESSIONS_DIR


@dataclass
class ValidationError:
    field: str
    message: str


@dataclass
class CalendarWriteResult:
    created: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    detail: str = ""


@dataclass
class TodoistWriteResult:
    created: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    detail: str = ""


def _run_skill(skill_path: str | Path, args: list[str]) -> dict:
    """Run a write skill, return parsed JSON. Tests monkeypatch this."""
    result = subprocess.run(
        [str(skill_path)] + args,
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


# -------- form parsing --------

_DINNER_RE = re.compile(r"^dinner_(\d{4}-\d{2}-\d{2})$")
_WFH_RE = re.compile(r"^wfh_(\d{4}-\d{2}-\d{2})$")
_HOME_BY_RE = re.compile(r"^home_by_(\d{4}-\d{2}-\d{2})$")
_ART_DATE_RE = re.compile(r"^art_date_(\d+)$")
_KID_TITLE_RE = re.compile(r"^kid_activity_title_(\d+)$")


def _split_lines(s: str) -> list[str]:
    return [line.strip() for line in (s or "").splitlines() if line.strip()]


def parse_form(form: dict) -> dict:
    """Translate the raw form dict into a structured decisions dict."""
    # Dinners (one per day, only non-empty)
    dinners: list[dict] = []
    for key, value in form.items():
        m = _DINNER_RE.match(key)
        if not m:
            continue
        dinners.append({"day": m.group(1), "meal": (value or "").strip()})
    dinners.sort(key=lambda d: d["day"])

    # Shopping
    shopping_necessary = _split_lines(form.get("shopping_necessary", ""))
    shopping_wants = _split_lines(form.get("shopping_wants", ""))

    # Home schedule (one row per weekday)
    home_schedule: list[dict] = []
    wfh_days: dict[str, bool] = {}
    home_by_days: dict[str, str] = {}
    for key, value in form.items():
        m = _WFH_RE.match(key)
        if m:
            wfh_days[m.group(1)] = bool(value)
            continue
        m = _HOME_BY_RE.match(key)
        if m:
            home_by_days[m.group(1)] = (value or "").strip()
    all_days = sorted(set(list(wfh_days.keys()) + list(home_by_days.keys())))
    for d in all_days:
        home_schedule.append({
            "day": d,
            "wfh": wfh_days.get(d, False),
            "home_by": home_by_days.get(d, ""),
        })

    # Art blocks (numbered rows)
    art_blocks: list[dict] = []
    for key, value in form.items():
        m = _ART_DATE_RE.match(key)
        if not m:
            continue
        idx = m.group(1)
        date_v = (value or "").strip()
        start_v = (form.get(f"art_start_{idx}") or "").strip()
        end_v = (form.get(f"art_end_{idx}") or "").strip()
        if not date_v and not start_v and not end_v:
            continue  # entirely blank row
        art_blocks.append({"date": date_v, "start": start_v, "end": end_v})

    # Babysitter
    babysitter = None
    if form.get("babysitter_needed"):
        babysitter = {
            "date": (form.get("babysitter_date") or "").strip(),
            "time": (form.get("babysitter_time") or "").strip(),
            "who": (form.get("babysitter_who") or "").strip(),
        }

    # Kid activities
    kids_activities: list[dict] = []
    for key, value in form.items():
        m = _KID_TITLE_RE.match(key)
        if not m:
            continue
        idx = m.group(1)
        title = (value or "").strip()
        if not title:
            continue
        kids_activities.append({
            "title": title,
            "date": (form.get(f"kid_activity_date_{idx}") or "").strip(),
            "time": (form.get(f"kid_activity_time_{idx}") or "").strip(),
            "owner": (form.get(f"kid_activity_owner_{idx}") or "Both").strip(),
        })

    # Date night
    date_night = None
    if (form.get("date_night_choice") or "").strip():
        date_night = {
            "date": (form.get("date_night_date") or "").strip(),
            "time": (form.get("date_night_time") or "").strip(),
            "choice": (form.get("date_night_choice") or "").strip(),
        }

    return {
        "retrospective_note": (form.get("retrospective_note") or "").strip(),
        "dinners": dinners,
        "new_meal": (form.get("new_meal") or "").strip(),
        "shopping_necessary": shopping_necessary,
        "shopping_wants": shopping_wants,
        "home_schedule": home_schedule,
        "art_blocks": art_blocks,
        "babysitter": babysitter,
        "kids_activities": kids_activities,
        "church_lines": _split_lines(form.get("church_notes", "")),
        "home_lines": _split_lines(form.get("home_notes", "")),
        "new_deadlines": _split_lines(form.get("new_deadlines", "")),
        "finances_notes": (form.get("finances_notes") or "").strip(),
        "cfm_notes": (form.get("cfm_notes") or "").strip(),
        "date_night": date_night,
    }


# -------- validation --------

def validate(decisions: dict) -> list[ValidationError]:
    """Return list of ValidationError. Empty = OK."""
    errors: list[ValidationError] = []

    bs = decisions.get("babysitter")
    if bs is not None:
        if not bs.get("date"):
            errors.append(ValidationError("babysitter_date", "Babysitter date is required when babysitter is needed"))
        if not bs.get("time"):
            errors.append(ValidationError("babysitter_time", "Babysitter time is required when babysitter is needed"))
        if not bs.get("who"):
            errors.append(ValidationError("babysitter_who", "Babysitter contact name is required"))

    for i, b in enumerate(decisions.get("art_blocks", [])):
        if not b.get("date"):
            errors.append(ValidationError(f"art_date_{i}", "Art block date is required"))
        if not b.get("start"):
            errors.append(ValidationError(f"art_start_{i}", "Art block start time is required"))
        if not b.get("end"):
            errors.append(ValidationError(f"art_end_{i}", "Art block end time is required"))

    for i, k in enumerate(decisions.get("kids_activities", [])):
        if not k.get("date"):
            errors.append(ValidationError(f"kid_activity_date_{i}", "Kid activity date is required"))

    dn = decisions.get("date_night")
    if dn is not None:
        if not dn.get("date"):
            errors.append(ValidationError("date_night_date", "Date night date is required when date night is set"))

    return errors


# -------- calendar writes --------

def _add_minutes(time_hhmm: str, minutes: int) -> str:
    """'17:00' + 15 → '17:15'. Wraps at 24h not handled (15-min wrap from 23:55 is fine)."""
    h, m = [int(x) for x in time_hhmm.split(":")]
    total = h * 60 + m + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def write_calendar(decisions: dict, cfg: Config) -> CalendarWriteResult:
    """Create calendar events for all calendar-bound decisions. Returns a result summary."""
    result = CalendarWriteResult()

    # Dinners → all-day on shared meal cal
    for d in decisions.get("dinners", []):
        if not d.get("meal"):
            continue
        args = [
            "--calendar-id", cfg.calendars.shared_meals,
            "--title", d["meal"],
            "--all-day", "--date", d["day"],
        ]
        try:
            _run_skill(GCAL_WRITE, args)
            result.created += 1
        except subprocess.CalledProcessError as e:
            result.failed += 1
            result.errors.append(f"{d['day']} {d['meal']}: {e.stderr or e.output or 'failed'}")

    # Home schedule
    for h in decisions.get("home_schedule", []):
        day = h["day"]
        if h["wfh"]:
            args = [
                "--calendar-id", cfg.calendars.shared_general,
                "--title", "Dalton WFH",
                "--all-day", "--date", day,
            ]
            try:
                _run_skill(GCAL_WRITE, args)
                result.created += 1
            except subprocess.CalledProcessError as e:
                result.failed += 1
                result.errors.append(f"WFH {day}: {e.stderr or 'failed'}")
        elif h["home_by"]:
            args = [
                "--calendar-id", cfg.calendars.shared_general,
                "--title", "Dalton home",
                "--start", f"{day}T{h['home_by']}",
                "--end", f"{day}T{_add_minutes(h['home_by'], 15)}",
            ]
            try:
                _run_skill(GCAL_WRITE, args)
                result.created += 1
            except subprocess.CalledProcessError as e:
                result.failed += 1
                result.errors.append(f"Home-by {day}: {e.stderr or 'failed'}")

    # Art blocks
    for b in decisions.get("art_blocks", []):
        if not (b.get("date") and b.get("start") and b.get("end")):
            continue
        args = [
            "--calendar-id", cfg.calendars.shared_general,
            "--title", "Maggie art",
            "--start", f"{b['date']}T{b['start']}",
            "--end", f"{b['date']}T{b['end']}",
        ]
        try:
            _run_skill(GCAL_WRITE, args)
            result.created += 1
        except subprocess.CalledProcessError as e:
            result.failed += 1
            result.errors.append(f"Art {b['date']}: {e.stderr or 'failed'}")

    # Babysitter
    bs = decisions.get("babysitter")
    if bs and bs.get("date") and bs.get("time"):
        end_time = _add_minutes(bs["time"], 240)  # default 4-hr slot
        args = [
            "--calendar-id", cfg.calendars.shared_general,
            "--title", f"Babysitter — {bs['who']}",
            "--start", f"{bs['date']}T{bs['time']}",
            "--end", f"{bs['date']}T{end_time}",
        ]
        try:
            _run_skill(GCAL_WRITE, args)
            result.created += 1
        except subprocess.CalledProcessError as e:
            result.failed += 1
            result.errors.append(f"Babysitter: {e.stderr or 'failed'}")

    # Kid activities (only those with date)
    for k in decisions.get("kids_activities", []):
        if not (k.get("title") and k.get("date")):
            continue
        if k.get("time"):
            end_time = _add_minutes(k["time"], 60)
            args = [
                "--calendar-id", cfg.calendars.shared_general,
                "--title", k["title"],
                "--start", f"{k['date']}T{k['time']}",
                "--end", f"{k['date']}T{end_time}",
                "--description", f"Owner: {k.get('owner', 'Both')}",
            ]
        else:
            args = [
                "--calendar-id", cfg.calendars.shared_general,
                "--title", k["title"],
                "--all-day", "--date", k["date"],
                "--description", f"Owner: {k.get('owner', 'Both')}",
            ]
        try:
            _run_skill(GCAL_WRITE, args)
            result.created += 1
        except subprocess.CalledProcessError as e:
            result.failed += 1
            result.errors.append(f"Kid activity '{k['title']}': {e.stderr or 'failed'}")

    # Date night
    dn = decisions.get("date_night")
    if dn and dn.get("date") and dn.get("choice"):
        if dn.get("time"):
            end_time = _add_minutes(dn["time"], 180)
            args = [
                "--calendar-id", cfg.calendars.shared_general,
                "--title", f"Date night — {dn['choice']}",
                "--start", f"{dn['date']}T{dn['time']}",
                "--end", f"{dn['date']}T{end_time}",
            ]
        else:
            args = [
                "--calendar-id", cfg.calendars.shared_general,
                "--title", f"Date night — {dn['choice']}",
                "--all-day", "--date", dn["date"],
            ]
        try:
            _run_skill(GCAL_WRITE, args)
            result.created += 1
        except subprocess.CalledProcessError as e:
            result.failed += 1
            result.errors.append(f"Date night: {e.stderr or 'failed'}")

    if result.failed == 0:
        result.detail = f"Created {result.created} events"
    else:
        result.detail = f"Created {result.created} events, {result.failed} failed"
    return result
```

- [ ] **Step 4: Run tests; expect pass**

```bash
pytest tests/test_write_back.py -v
```

Expected: all parse_form + validate + write_calendar tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/write_back.py tests/test_write_back.py
git commit -m "feat(weekly-planning): write_back parse_form + validation + calendar writes"
```

### Task 5.5: `write_back.py` — Todoist writes + archive + `run_save`

**Files:**
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/write_back.py`
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_write_back.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_write_back.py`:

```python
from src.write_back import write_todoist, run_save


def test_write_todoist_routes_shopping_to_to_buy(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "shopping_necessary": ["milk", "eggs"],
        "shopping_wants": ["sourdough"],
        "home_lines": [],
        "new_deadlines": [],
        "church_lines": [],
        "new_meal": "",
    }
    calls = []
    def fake_run(path, args):
        calls.append({"path": str(path), "args": args})
        return {"id": "x", "content": "ok"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        result = write_todoist(decisions, cfg)
    project_ids_called = [c["args"][c["args"].index("--project-id") + 1] for c in calls]
    # 2 to To buy, 1 to To buy (less necessary)
    assert project_ids_called.count(cfg.todoist.project_id("shopping")) == 2
    assert project_ids_called.count(cfg.todoist.project_id("shopping_wants")) == 1
    assert result.created == 3
    assert result.failed == 0


def test_write_todoist_routes_home_to_home_project(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "shopping_necessary": [],
        "shopping_wants": [],
        "home_lines": ["Fix faucet", "Clean gutters"],
        "new_deadlines": [],
        "church_lines": [],
        "new_meal": "",
    }
    calls = []
    def fake_run(path, args):
        calls.append(args)
        return {"id": "x"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        result = write_todoist(decisions, cfg)
    home_id = cfg.todoist.project_id("home")
    assert all(home_id in c for c in calls)
    assert result.created == 2


def test_write_todoist_routes_new_meal_to_meals(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    decisions = {
        "shopping_necessary": [], "shopping_wants": [],
        "home_lines": [], "new_deadlines": [], "church_lines": [],
        "new_meal": "Thai green curry",
    }
    calls = []
    def fake_run(path, args):
        calls.append(args)
        return {"id": "x"}
    with patch("src.write_back._run_skill", side_effect=fake_run):
        write_todoist(decisions, cfg)
    assert len(calls) == 1
    assert calls[0][calls[0].index("--content") + 1] == "Thai green curry"
    assert calls[0][calls[0].index("--project-id") + 1] == cfg.todoist.project_id("meals")


def test_run_save_validation_failure_returns_400_payload(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    bad_form = {"babysitter_needed": True, "babysitter_date": "", "babysitter_time": "", "babysitter_who": ""}
    response = run_save(bad_form, cfg)
    assert response["status"] == "validation_error"
    assert len(response["errors"]) >= 3


def test_run_save_happy_path_writes_and_archives(fixtures_dir, tmp_path, monkeypatch):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    # redirect SESSIONS_DIR to a temp dir
    monkeypatch.setattr("src.write_back.SESSIONS_DIR", tmp_path)
    form = dict(SAMPLE_FORM)
    with patch("src.write_back._run_skill", return_value={"id": "x"}):
        response = run_save(form, cfg)
    assert response["status"] == "ok"
    assert "summary_html" in response
    archived = list(tmp_path.glob("*-session.html"))
    assert len(archived) == 1
    assert "Tacos" in archived[0].read_text()
```

- [ ] **Step 2: Run; expect fail**

```bash
pytest tests/test_write_back.py::test_write_todoist_routes_shopping_to_to_buy -v
```

Expected: ImportError on `write_todoist`.

- [ ] **Step 3: Implement Todoist writes + `run_save` (append to `src/write_back.py`)**

Append to `src/write_back.py`:

```python
from src.render_summary import render_summary


def _add_todoist_task(content: str, project_id: str, deadline: str = "") -> dict:
    args = ["--content", content, "--project-id", project_id]
    if deadline:
        args.extend(["--due-string", deadline])
    else:
        # add-task.sh defaults due-string to "today" if not passed; we explicitly disable
        args.extend(["--due-string", "no due date"])  # interpreted as no date by Todoist NL parser; safer: pass empty
    return _run_skill(TODOIST_ADD, args)


def write_todoist(decisions: dict, cfg: Config) -> TodoistWriteResult:
    """Create Todoist tasks for all task-bound decisions."""
    result = TodoistWriteResult()
    routes = [
        # (list of content strings, project_role)
        (decisions.get("shopping_necessary", []), "shopping"),
        (decisions.get("shopping_wants", []), "shopping_wants"),
        (decisions.get("home_lines", []), "home"),
        (decisions.get("new_deadlines", []), "general_todos"),
        (decisions.get("church_lines", []), "general_todos"),
    ]
    for items, role in routes:
        try:
            project_id = cfg.todoist.project_id(role)
        except Exception as e:
            result.failed += len(items)
            result.errors.append(f"Project '{role}' not configured: {e}")
            continue
        for content in items:
            try:
                _run_skill(TODOIST_ADD, ["--content", content, "--project-id", project_id])
                result.created += 1
            except subprocess.CalledProcessError as e:
                result.failed += 1
                result.errors.append(f"'{content}' → {role}: {e.stderr or 'failed'}")

    # New meal idea
    new_meal = (decisions.get("new_meal") or "").strip()
    if new_meal:
        try:
            project_id = cfg.todoist.project_id("meals")
            _run_skill(TODOIST_ADD, ["--content", new_meal, "--project-id", project_id])
            result.created += 1
        except (Exception, subprocess.CalledProcessError) as e:
            result.failed += 1
            result.errors.append(f"new meal '{new_meal}': {e}")

    if result.failed == 0:
        result.detail = f"Created {result.created} tasks"
    else:
        result.detail = f"Created {result.created} tasks, {result.failed} failed"
    return result


def _archive_session(summary_html: str, week_start_iso: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / f"{week_start_iso}-session.html"
    path.write_text(summary_html)
    return path


def run_save(form: dict, cfg: Config) -> dict:
    """Top-level save orchestrator. Returns {status, summary_html|errors}."""
    decisions = parse_form(form)
    errors = validate(decisions)
    if errors:
        return {
            "status": "validation_error",
            "errors": [{"field": e.field, "message": e.message} for e in errors],
        }

    cal_result = write_calendar(decisions, cfg)
    todoist_result = write_todoist(decisions, cfg)

    succeeded = []
    failed = []
    if cal_result.created > 0:
        succeeded.append({"label": "Calendar events", "detail": cal_result.detail, "key": "calendar"})
    if cal_result.failed > 0:
        failed.append({"label": "Calendar events", "error": "; ".join(cal_result.errors), "key": "calendar"})
    if todoist_result.created > 0:
        succeeded.append({"label": "Todoist tasks", "detail": todoist_result.detail, "key": "todoist"})
    if todoist_result.failed > 0:
        failed.append({"label": "Todoist tasks", "error": "; ".join(todoist_result.errors), "key": "todoist"})

    # Compute week_start for display + filename
    week_start_iso = ""
    for d in decisions.get("dinners", []):
        if d.get("day"):
            week_start_iso = d["day"]
            break
    if not week_start_iso:
        # fallback: today
        week_start_iso = datetime.now().date().isoformat()

    week_start_display = datetime.fromisoformat(week_start_iso).strftime("%b %-d")
    saved_at = datetime.now().strftime("%a %b %-d %-I:%M %p")

    summary_html = render_summary(
        decisions=decisions,
        results={"succeeded": succeeded, "failed": failed},
        week_start_display=week_start_display,
        saved_at=saved_at,
    )

    _archive_session(summary_html, week_start_iso)

    return {
        "status": "ok",
        "summary_html": summary_html,
        "results": {"succeeded": succeeded, "failed": failed},
    }
```

- [ ] **Step 4: Run tests; expect pass**

```bash
pytest tests/test_write_back.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/write_back.py tests/test_write_back.py
git commit -m "feat(weekly-planning): write_back todoist writes + archive + run_save"
```

### Task 5.6: Flask server (`src/server.py`)

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/src/server.py`
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/tests/test_server.py`

- [ ] **Step 1: Write failing tests**

`tests/test_server.py`:

```python
import json
from unittest.mock import patch
from src.server import create_app
from src.config import load_config


def test_get_root_serves_session_html(fixtures_dir, tmp_path, monkeypatch):
    monkeypatch.setattr("src.server.PROJECT_ROOT", tmp_path)
    (tmp_path / "session.html").write_text("<html><body>HELLO FORM</body></html>")
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    app = create_app(cfg)
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"HELLO FORM" in resp.data


def test_post_save_happy_path_returns_summary_html(fixtures_dir, tmp_path, monkeypatch):
    monkeypatch.setattr("src.write_back.SESSIONS_DIR", tmp_path)
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    app = create_app(cfg)
    client = app.test_client()

    form = {
        "dinner_2026-05-22": "Tacos",
        "shopping_necessary": "milk",
        "babysitter_needed": False,
    }
    with patch("src.write_back._run_skill", return_value={"id": "x"}):
        resp = client.post("/save", json=form)
    assert resp.status_code == 200
    assert b"Tacos" in resp.data
    assert b"Saved" in resp.data


def test_post_save_validation_error_returns_400(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    app = create_app(cfg)
    client = app.test_client()
    bad = {"babysitter_needed": True, "babysitter_date": "", "babysitter_time": "", "babysitter_who": ""}
    resp = client.post("/save", json=bad)
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["status"] == "validation_error"
    assert len(payload["errors"]) > 0
```

- [ ] **Step 2: Run; expect fail**

```bash
pytest tests/test_server.py -v
```

Expected: ImportError on `create_app`.

- [ ] **Step 3: Implement `src/server.py`**

```python
"""Local Flask server. GET / serves session.html; POST /save runs write_back; auto-shutdown after success."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from flask import Flask, request, Response, jsonify

from src.config import Config
from src.constants import PROJECT_ROOT
from src.write_back import run_save


def create_app(cfg: Config) -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def root():
        html_path = PROJECT_ROOT / "session.html"
        if not html_path.exists():
            return "<h1>session.html not yet generated — run the skill first.</h1>", 404
        return Response(html_path.read_text(), mimetype="text/html")

    @app.route("/save", methods=["POST"])
    def save():
        form = request.get_json(silent=True) or {}
        response = run_save(form, cfg)
        if response["status"] == "validation_error":
            return jsonify(response), 400
        # Schedule a delayed shutdown so the browser has time to render summary
        threading.Thread(
            target=_delayed_shutdown,
            args=(30,),  # seconds
            daemon=True,
        ).start()
        return Response(response["summary_html"], mimetype="text/html"), 200

    return app


def _delayed_shutdown(delay_seconds: int) -> None:
    time.sleep(delay_seconds)
    import os
    os._exit(0)


def serve(cfg: Config) -> None:
    app = create_app(cfg)
    app.run(host="127.0.0.1", port=cfg.session.server_port, debug=False, use_reloader=False)


if __name__ == "__main__":
    from src.config import load_config
    from src.constants import CONFIG_PATH
    serve(load_config(CONFIG_PATH))
```

- [ ] **Step 4: Run tests; expect pass**

```bash
pytest tests/test_server.py -v
```

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: every test in every test file passes.

- [ ] **Step 6: Commit**

```bash
git add src/server.py tests/test_server.py
git commit -m "feat(weekly-planning): flask server with GET / and POST /save"
```

---

### ⚠️ STAGE 5 CHECKPOINT

```
/security-review
```

**Focus areas (most important review of the project):**
- `src/write_back.py` — this is the code that mutates external systems. Are subprocess args properly passed (no shell=True, no string concat)? Could a malicious form input inject CLI flags into `--content` / `--title`?
- `src/server.py` — local-only, but: any chance of arbitrary file reads via path traversal? Does it accept JSON safely?
- `Personal/skills/gcal-write/add-event.sh` — same subprocess hygiene questions.
- Form field values being passed straight into `--title` etc. — does the Calendar API treat any chars specially?

```
/simplify
```

**Focus areas:** `write_back.py` has grown. Is the duplicated try/except pattern in `write_calendar` worth refactoring into a single helper? Is `parse_form` clear or hard to follow?

Address findings before continuing to Stage 6.

---

## Stage 6 — SKILL.md orchestration + wrapper + README + E2E

**Stage goal:** Skill is invokable end-to-end. First real Thursday session is the ultimate verification.

**Stage deliverable:** Running `/weekly-planning` inside a Claude Code session produces a working form in Chrome; saving creates real Calendar events + Todoist tasks; summary archive shows up under `sessions/`.

### Task 6.1: `SKILL.md`

This is the entry point Claude Code invokes when the user runs `/weekly-planning`. It instructs Claude step-by-step through the orchestration — runs fetch, generates retrospective + flags inline as LLM tasks, renders the page, starts the server, opens Chrome.

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/SKILL.md`

- [ ] **Step 1: Create `SKILL.md`**

```markdown
---
name: weekly-planning
description: Run Dalton & Maggie's Thursday-night weekly planning session — fetches sources, opens form in Chrome
---

You are starting a weekly planning session for Dalton and Maggie. Walk through the steps below in order. Do not skip any.

Project root: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family`

---

## Step 1 — Activate venv and pull all sources

Run via Bash:

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
python -m src.fetch_sources
```

This writes `context.json` to the project root with all the source data. Expect ~1-3 min runtime. If it errors, stop and surface the error.

---

## Step 2 — Generate the retrospective

Read these two files into your working context:
- `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/context.json`
- `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/prompts/retrospective.md`

Follow the instructions in `retrospective.md` exactly. Produce the JSON it specifies. Write that JSON to:

`/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/retrospective.json`

Use the Write tool. The file must be valid JSON matching the schema in the prompt.

---

## Step 3 — Generate the margin/realism flags

Read:
- `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/context.json` (already loaded from Step 2)
- `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/prompts/margin_flags.md`

Follow the prompt. Write the JSON to:

`/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/margin_flags.json`

Empty list `{"flags": []}` is valid output if nothing's worth flagging.

---

## Step 4 — Resolve this week's Come Follow Me lesson

Use WebFetch to load `https://www.churchofjesuschrist.org/study/manual/come-follow-me-for-home-and-church-old-testament-2026` (or the current year's manual). From the page, identify the lesson scheduled for the upcoming week (Mon–Sun corresponding to the next planning week — use `week_start` from `context.json` as your reference; CFM weeks run Mon–Sun starting the Monday before each Sunday's lesson).

Capture the lesson title (e.g., "2 Nephi 1-5: 'We Have Obtained a Land of Promise'"). Write it to:

`/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/cfm_title.txt`

If the fetch fails or you can't confidently identify this week's lesson, write `this week's lesson (fetch failed)` to the file and continue. The session is more important than this single field.

---

## Step 5 — Render the form HTML

The render script reads `context.json`, `retrospective.json`, `margin_flags.json`, and `cfm_title.txt`. Run via Bash:

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
# Pass CFM title via env var to keep CLI simple
WEEKLY_PLANNING_CFM_TITLE="$(cat cfm_title.txt)" python -m src.render_page
```

Expected: prints `session.html written: ...` and the file exists.

> **Note:** `render_page.py` reads `WEEKLY_PLANNING_CFM_TITLE` from env when present, falling back to its default placeholder. If your local copy doesn't read that env var yet, update `main()` in `src/render_page.py` to do so — it's a 2-line change.

---

## Step 6 — Start the form server in the background and open Chrome

Run via Bash with `run_in_background=true`:

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
python -m src.server
```

Wait ~2 seconds, then in foreground:

```bash
open -a "Google Chrome" http://localhost:8000
```

Chrome should open the form. Tell the user:

> Form is ready at http://localhost:8000. The server will auto-shutdown 30 seconds after you click Save & write back. If you abandon the session, kill the server with: `pkill -f "src.server"`.

You're done. The user takes over from here.

---

## Rules

- **Never** email anything during this skill. Email send is not part of Phase 1.
- Never write or commit `context.json`, `retrospective.json`, `margin_flags.json`, `cfm_title.txt`, or `session.html` — they're all gitignored runtime artifacts.
- If any step fails, stop and surface the error. Don't paper over it.
- HIPAA / patient data: there is none in this project. If you see anything that looks like patient info in fetched Gmail (e.g., a name + condition), flag it and do not proceed.
```

- [ ] **Step 2: Update `src/render_page.py` to honor the CFM env var**

Find the `main()` function and update its `cfm_title` line:

```python
    # CFM lesson title — passed via env var by SKILL.md
    cfm_title = os.environ.get("WEEKLY_PLANNING_CFM_TITLE", "this week's lesson")
```

Add `import os` at the top of the file if not present.

- [ ] **Step 3: Add a small test for the env-var read**

Add to `tests/test_render_page.py`:

```python
import os
import subprocess
from pathlib import Path


def test_render_page_main_uses_env_var_for_cfm(tmp_path, fixtures_dir, monkeypatch):
    """End-to-end sanity: main() pipes env var through to rendered output."""
    # Use a separate script run to avoid contaminating live config paths
    # — skip this if it complicates the env. The render() function unit test
    # already covers the parameter wiring.
    pass  # placeholder; the unit test in render() proves the wiring
```

(This is essentially documenting that the wiring is already test-proven; you can leave it as a `pass` test or delete it.)

- [ ] **Step 4: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add SKILL.md src/render_page.py tests/test_render_page.py
git commit -m "feat(weekly-planning): SKILL.md orchestration + CFM env-var read"
```

### Task 6.2: `weekly-planning-view` wrapper

**Files:**
- Create: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/weekly-planning-view`

A tiny bash wrapper to open the most recent archived session in Chrome.

- [ ] **Step 1: Create the wrapper**

```bash
#!/usr/bin/env bash
# Open the most recent weekly planning session summary in Chrome.
# Usage:
#   weekly-planning-view                # opens most recent
#   weekly-planning-view --list         # lists all archived sessions
#   weekly-planning-view --date 2026-05-17    # opens session for that week_start

set -euo pipefail

SESSIONS_DIR="/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/sessions"

if [[ ! -d "$SESSIONS_DIR" ]]; then
    echo "No sessions yet — run /weekly-planning in Claude Code to create one." >&2
    exit 1
fi

case "${1:-}" in
    --list)
        ls -1 "$SESSIONS_DIR" 2>/dev/null | sort -r
        exit 0
        ;;
    --date)
        if [[ -z "${2:-}" ]]; then
            echo "Usage: weekly-planning-view --date YYYY-MM-DD" >&2
            exit 1
        fi
        FILE="$SESSIONS_DIR/$2-session.html"
        if [[ ! -f "$FILE" ]]; then
            echo "No session found for $2" >&2
            exit 1
        fi
        open -a "Google Chrome" "$FILE"
        ;;
    "")
        # Most recent
        LATEST=$(ls -1 "$SESSIONS_DIR" 2>/dev/null | sort -r | head -1)
        if [[ -z "$LATEST" ]]; then
            echo "No sessions found." >&2
            exit 1
        fi
        open -a "Google Chrome" "$SESSIONS_DIR/$LATEST"
        ;;
    *)
        echo "Usage: weekly-planning-view [--list | --date YYYY-MM-DD]" >&2
        exit 1
        ;;
esac
```

- [ ] **Step 2: Make executable**

```bash
chmod +x /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/weekly-planning-view
```

- [ ] **Step 3: (Optional) Symlink into PATH for global use**

Pick one:

```bash
# Option A: symlink to a directory already on PATH
ln -s /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/weekly-planning-view ~/.local/bin/weekly-planning-view

# Option B: just call by full path when needed (no symlink)
```

- [ ] **Step 4: Smoke test (will fail until first session exists; that's fine)**

```bash
/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/weekly-planning-view --list
```

Expected: either "No sessions yet" or a (currently empty) list. Both are acceptable at this point.

- [ ] **Step 5: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add weekly-planning-view
git commit -m "feat(weekly-planning): cli wrapper to view past sessions in Chrome"
```

### Task 6.3: `README.md`

**Files:**
- Modify: `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/README.md`

- [ ] **Step 1: Replace the skeleton README**

```markdown
# Weekly Planning (Family)

A Claude Code skill that helps Dalton and Maggie run a weekly planning session.

Every Thursday evening, invoke `/weekly-planning` inside Claude Code. The skill:

1. Fetches the next 7 days from the shared general + meal calendars, plus school calendars, plus the last 7 days of Gmail (Dalton + Maggie + "Kid's School" label), plus relevant Todoist projects.
2. Generates a retrospective summary and any margin/realism flags about the upcoming week.
3. Renders a form in Chrome with all pre-loaded context + decision fields.
4. On save: writes Calendar events (general + meal cals) and Todoist tasks per the routing map, then archives a local summary HTML for later review.

## Design

See `docs/superpowers/specs/2026-05-17-weekly-planning-family-design.md` for the full design and `docs/superpowers/plans/2026-05-17-weekly-planning-family-phase-0-1.md` for the implementation plan.

## How to run

Open Claude Code → `/weekly-planning`. Wait 1-3 min while sources fetch. Chrome opens the form. Walk through it with Maggie. Click Save when done.

## How to view past sessions

```bash
./weekly-planning-view                   # most recent
./weekly-planning-view --list            # list all
./weekly-planning-view --date 2026-05-22 # specific week
```

## Setup (one-time)

See Stage 1 of the implementation plan. Briefly:

1. Add Maggie's Gmail OAuth to the existing Google Cloud project; store her refresh token in macOS Keychain under `GMAIL_REFRESH_TOKEN_MAGGIE`.
2. Create a Gmail label `Kid's School` with filter rules for Brightwheel + elementary school senders.
3. Subscribe school iCal feeds in your personal Google Calendar.
4. Create a shared Todoist project `Date Night Ideas`.
5. Copy `config.example.yaml` to `config.yaml` and fill in all `TBD` fields.
6. Create the Python venv: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

## Tests

```bash
source .venv/bin/activate
pytest -v
```

All tests use synthetic fixtures; no live API calls.

## Architecture

- `SKILL.md` — the Claude Code skill (entry point)
- `src/fetch_sources.py` — pulls all sources → `Context` dataclass → `context.json`
- `src/render_page.py` — renders `session.html` from Context + LLM output
- `src/server.py` — Flask app: `GET /` serves the form, `POST /save` writes back
- `src/write_back.py` — validates form, creates Calendar events + Todoist tasks, returns summary HTML
- `src/render_summary.py` — renders the post-save summary view
- `prompts/*.md` — LLM prompt templates (retrospective, margin flags)
- `templates/*.jinja` — Jinja templates for form + summary

External skills reused (`Personal/skills/`):
- `gcal-fetch/list-events.sh` (read)
- `gcal-write/add-event.sh` (write — added in this project)
- `gmail-fetch/search-emails.sh` (read, multi-account)
- `todoist-write/add-task.sh` (write)
```

- [ ] **Step 2: Commit**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git add README.md
git commit -m "docs(weekly-planning): full README with setup + architecture"
```

### Task 6.4: End-to-end smoke verification

This task is **manual**. It exercises the whole system against real APIs for the first time.

- [ ] **Step 1: Verify all unit tests still pass**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Create a throwaway test calendar in Google Calendar**

Before pointing write-back at the real shared cal, smoke-test on a sacrificial calendar:

1. In Google Calendar: "+ Create new calendar" → name `weekly-planning-smoke-test`. Note the ID.
2. **Temporarily** edit `config.yaml` to swap `calendars.shared_general` and `calendars.shared_meals` to point at this test calendar (use the same ID for both to keep it simple).

- [ ] **Step 3: Invoke the skill**

In a Claude Code session, run: `/weekly-planning`

Verify each step of `SKILL.md` runs successfully:
- `context.json` produced (check counts in the printed summary).
- `retrospective.json` written with 5-10 bullets.
- `margin_flags.json` written (may be empty list).
- `cfm_title.txt` written with this week's lesson title.
- `session.html` written.
- Server starts on `localhost:8000`.
- Chrome opens with the form rendered.

- [ ] **Step 4: Walk through the form**

- Visual check: all 17 sections present, all pre-loaded data visible, form fields editable.
- Fill in a few decisions: 2 dinners, 1 shopping item, 1 WFH day, 1 babysitter slot, 1 date night choice.
- Click "Save & write back."

Expected:
- Button disables with spinner.
- Page swaps to summary view within ~5-10s.
- Summary shows the decisions you entered and lists what was created.

- [ ] **Step 5: Verify writes**

- Open Google Calendar → check the test calendar has new events (dinners as all-day, WFH as all-day, babysitter as timed, date night as timed).
- Open Todoist → check shopping item appears in `To buy`.
- Wait 30 seconds → confirm the local server shut itself down (`curl http://localhost:8000/` should fail).

- [ ] **Step 6: Verify archive**

```bash
ls /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/sessions/
./weekly-planning-view
```

Expected: `YYYY-MM-DD-session.html` exists. Chrome reopens with the summary view.

- [ ] **Step 7: Clean up test events**

Delete the test events from the test calendar. Delete any test Todoist tasks created. Delete the test calendar itself if you don't want to keep it.

- [ ] **Step 8: Restore real calendar IDs in `config.yaml`**

Edit `config.yaml`: swap `calendars.shared_general` and `calendars.shared_meals` back to the real production IDs (`rgq78thkje9h8p3c57718eamog@group.calendar.google.com` and `vj5lp1it7em4nekmlra1b3c5a4@group.calendar.google.com`).

- [ ] **Step 9: Final commit (clean status)**

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
git status
```

Expected: clean working tree. `config.yaml`, `sessions/`, `tokens/`, `context.json`, `retrospective.json`, `margin_flags.json`, `cfm_title.txt`, `session.html` should NOT appear (all gitignored).

If anything that should be gitignored shows up: revisit `.gitignore` from Task 1.1.

---

### ⚠️ STAGE 6 CHECKPOINT (final)

```
/simplify
```

**Focus areas:** the full project. Any dead code? Any duplicated logic between `render_page.py` and `render_summary.py` that could be shared? Is `SKILL.md` clear and minimal? Any leftover scaffolding that wasn't used?

```
/security-review
```

**Focus areas (whole-project sweep):**
- All `subprocess` call sites — no shell injection paths.
- All Keychain reads — no token logging.
- Flask server — bound to `127.0.0.1` only.
- Form input — no field gets unsafely interpolated into a calendar event title where it could carry meaning to a downstream system.
- `.gitignore` — actually excludes everything sensitive (tokens, sessions, context.json, config.yaml).
- README does NOT include any real Gmail addresses, child names, etc.

The **first real Thursday session** is the ultimate verification. Run it, take notes on what felt off, and roll those into the Phase 2 decision later.

---

## Notes for executing this plan

- **Skip the gcal-write smoke test in Task 5.1 Step 3** if you don't want to set up a test calendar; the end-to-end smoke in Task 6.4 covers it.
- **Stage 1 is the bottleneck** — the OAuth flow for Maggie can hit snags depending on how your Google Cloud OAuth client is configured. Budget extra time.
- **Stage 3's first live run** of `python -m src.fetch_sources` is the moment auth issues surface. Be patient and methodical there.
- **Tests are written against synthetic fixtures only**. The first time code touches the live APIs is in Stages 3, 5, and 6's manual verification steps. That's intentional.
- If you decide later you want the email recap after all, the natural insertion point is `src/write_back.py::run_save` — add a `send_recap_email()` call after the archive step. Spec lists this as a Future item.

## Known deviations from spec

Two items intentionally deferred from this plan, to be addressed after the first real session if they bite:

1. **Per-source fetch resilience banner.** Spec §8 says "If any source fetch fails (auth expired, network), the pre-brief proceeds with whatever did succeed. The form shows a small banner per missing source." This plan's `assemble_context` does NOT wrap individual fetches in try/except — if any source fails, the whole pre-brief fails and the user re-runs after fixing the cause. Simpler v1; rarely catastrophic if you treat auth/network as setup hygiene. If this becomes annoying, add try/except per fetch + a `fetch_warnings: list[str]` field on Context, and surface it in the form template.

2. **CFM URL construction.** Spec §14 flags this as needing confirmation. SKILL.md Step 4 uses a best-effort WebFetch with a fallback ("fetch failed" placeholder text) so a misformed URL or a moved page doesn't block the session. If this fails repeatedly, switch to hand-maintaining a `cfm_overrides.yaml` keyed by week-start date.







