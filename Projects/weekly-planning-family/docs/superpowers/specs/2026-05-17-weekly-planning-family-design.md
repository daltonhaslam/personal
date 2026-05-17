# Weekly Planning (Family) — Design

**Date:** 2026-05-17
**Owner:** Dalton Haslam, MD MBA
**Status:** Approved design — ready for implementation plan

---

## 1. Problem

Dalton and Maggie need a consistent weekly planning rhythm to keep family logistics on track: dinners, shopping, Dalton's work-from-home days, Maggie's art time, kids' activities (preschool + elementary), church and temple commitments, major deadlines, finances, date night, and Come Follow Me gospel teaching for the kids.

Today this planning either happens ad hoc or not at all. Information lives across many systems — two shared Google Calendars (general + meals), Dalton's personal Gcal, school calendars, Todoist (10+ shared projects), Dalton's Gmail, Maggie's Gmail, Brightwheel preschool messages — and pulling it together for a Thursday-night discussion is friction enough that the discussion gets skipped.

Full automation isn't the answer. The point of the session is for Dalton and Maggie to talk through the week together; a machine deciding for them defeats the purpose. The goal is to remove the assembly friction so the conversation is easy to start and the decisions actually get captured.

## 2. Goal

A **Claude Code skill** (`/weekly-planning`) that, on invocation, assembles a pre-brief of every relevant source and renders an interactive web form Dalton and Maggie walk through side-by-side. The form has pre-loaded context (read-only) at the top and decision fields (free-text, dropdowns, time pickers, checkboxes) below. On "Save & write back," decisions become Google Calendar events and Todoist tasks in the correct calendars/projects, the page transitions to a summary view showing what was created, and the form HTML is archived locally for later review in Chrome.

Phase 1 ships **no AI assistance inside the session itself** — just pre-loaded context + form + write-back. AI (Claude inside the Code session) is used only during pre-brief generation (retrospective summary + margin/realism flags). Phase 2 adds per-section AI assist buttons once real use reveals which assists matter; Phase 3 optionally adds a chat panel.

## 3. Phasing

| Phase | Scope | Effort | Trigger to start |
|---|---|---|---|
| **Phase 0** | One-time setup: Maggie's Gmail OAuth, "Kid's School" Gmail label + filters, school iCal subscriptions, `Date Night Ideas` Todoist project, `config.yaml` filled out. | ~half day, mostly clicking | Before Phase 1 implementation begins |
| **Phase 1** | The MVP described in §7. Skill assembles brief + form + write-back. No in-session AI assist. | ~3 days of focused build | After Phase 0 complete |
| **Phase 2** | Per-section AI assist buttons (3-4 highest-value first). Form gains a right-side panel. | ~2 days | After 2-3 real Phase 1 sessions; decide which buttons matter from actual use |
| **Phase 3** | Optional chat panel ("ask Claude anything" with full session context). | ~1 day | Only if Phase 2 buttons feel insufficient |
| **Future (unscheduled)** | Email recap send; sender-allowlist for Gmail; weekly-planning iOS Shortcut; meal-rotation/variety tracking. | Variable | Evaluated independently |

## 4. Non-Goals

- No web UI hosted anywhere (local Flask on `localhost:8000` only).
- No LaunchAgent or scheduled pre-fetch — manual invocation only. The 1-3 min fetch latency is acceptable and intentionally controlled by the user.
- No automated decision-making. Claude assembles context and writes back; humans decide.
- No email recap in v1 (deferred to Future).
- No iMessage integration (no MCP available).
- No Dalton work calendar (no MWHC connector).
- No YNAB or financial system integration. Finances is a free-form discussion topic captured in the local session summary only.
- No multi-device live editing. Single Mac, side-by-side.
- No dedup logic on save (the post-save summary view replaces the form, making double-click impossible — see §7.6).
- No calendar conflict suppression (overlapping events are added as-is; user sees overlap in their calendar app).
- No PHI / HIPAA-relevant data anywhere in this project.

## 5. Constraints

- **Execution environment:** macOS (Dalton's laptop), Python 3, Chrome as default browser. The tool is a **Claude Code skill** — invoked inside an interactive Claude Code session, not a standalone executable. This is intentional: interactive Claude Code use is the most insulated path from ongoing Anthropic billing policy changes around headless `claude -p`. LLM calls during pre-brief generation happen inside the same Claude Code conversation that invoked the skill.
- **Auth:** Existing Google Cloud OAuth client (`gmail-fetch` + `gcal-fetch` skills) reused. Maggie's Gmail authenticates under the same OAuth client, with her refresh token stored separately. Read-only scopes only — no `gmail.send` scope needed in v1.
- **AI cost:** Dalton's Claude Max (5x) subscription covers all LLM use via the interactive Claude Code path. No separate Anthropic API key.
- **Public repo:** This project lives in `daltonhaslam/personal` (public). No real names of children, no addresses, no financial detail, no email addresses in committed code. Sensitive specifics live in `config.yaml` and `tokens/` (gitignored — see §6) or in Gmail/Calendar/Todoist themselves.

## 6. Architecture

```
Personal/Projects/weekly-planning-family/
├── README.md                          # short pointer + how to invoke the skill
├── SKILL.md                           # the Claude Code skill — entry point
├── weeklyplanningideas.txt            # original brainstorm notes (kept for reference)
├── .gitignore                         # committed: tokens/, sessions/, config.yaml
├── config.example.yaml                # committed template with placeholders
├── config.yaml                        # gitignored — real values
├── src/
│   ├── fetch_sources.py               # all source pulls → Context dict
│   ├── render_page.py                 # produces session.html from Jinja template
│   ├── render_summary.py              # produces summary HTML shown post-save + archived
│   ├── server.py                      # local Flask app (Phase 2 adds /assist/* routes)
│   └── write_back.py                  # Calendar events + Todoist tasks + summary render
├── prompts/
│   ├── retrospective.md               # prompt template the skill runs for retrospective bullets
│   └── margin_flags.md                # prompt template for margin/realism flags
├── templates/
│   ├── session.html.jinja             # the form template
│   └── summary.html.jinja             # the post-save summary view
├── tests/                             # pytest, synthetic fixtures only (no live API calls)
├── sessions/                          # gitignored — archived past sessions
│   └── YYYY-MM-DD-session.html
├── tokens/                            # gitignored
│   ├── dalton.json                    # Gmail refresh token
│   └── maggie.json                    # Gmail refresh token
└── docs/superpowers/
    ├── specs/                         # this file lives here
    └── plans/                         # implementation plans go here
```

### Boundaries

- `SKILL.md` is the **only** module that drives LLM behavior. It directs Claude (in the user's Code session) through fetches, brief generation, render, and server startup. No Python file calls `claude -p`.
- `fetch_sources.py` handles **all I/O to external systems** (Google Calendar, Gmail, Todoist) and returns a structured `Context` object. Pure data in, pure data out — no LLM calls, no rendering.
- `render_page.py` is the only module that knows about the form's HTML / Jinja layout.
- `render_summary.py` is the only module that knows about the summary view's layout.
- `server.py` is the only module that owns the HTTP surface (`GET /`, `POST /save`, Phase 2 `/assist/*`).
- `write_back.py` handles **all I/O for decision capture** (Calendar create, Todoist create, summary archive). Validates first, never half-writes silently.
- The skill (`SKILL.md`) is the only module that knows the orchestration order.

This means form rendering can change without touching API code, the LLM prompts can change without touching write-back, and the fetch logic can be exercised against fixtures in tests without touching live APIs.

### Data flow (one run)

```
   Thursday ~7:30pm
        │
        ▼
   $ claude   (open Claude Code session)
        │
        ▼
   /weekly-planning   (invoke the skill)
        │
        ▼
   SKILL.md walks Claude through:
        │
        ├─▶ Bash: python -m src.fetch_sources → context.json
        │     │
        │     ├─▶ Google Calendar API (general + meals + schools + personal)
        │     ├─▶ Gmail API (dalton + maggie tokens, filtered)
        │     └─▶ Todoist API (Meals, Date Night Ideas, Screen time, deadlines)
        │
        ├─▶ Claude reads context.json + prompts/retrospective.md → writes retrospective.json
        ├─▶ Claude reads context.json + prompts/margin_flags.md → writes margin_flags.json
        │
        ├─▶ Bash: python -m src.render_page → templates/session.html.jinja → session.html
        │
        ├─▶ Bash: python -m src.server &   (Flask on localhost:8000, background)
        │
        └─▶ Bash: open -a "Google Chrome" http://localhost:8000
                  │
                  ▼
        [Dalton + Maggie walk through form, click Save]
                  │
                  ▼
            server.py POST /save
                  │
                  ▼
            write_back.py:
              ├─▶ validate
              ├─▶ archive session HTML to sessions/YYYY-MM-DD-session.html
              ├─▶ Google Calendar create (general + meals)
              ├─▶ Todoist create (per routing map)
              └─▶ render summary HTML
                  │
                  ▼
            response: summary HTML
                  │
                  ▼
       Chrome page transitions to summary view
                  │
                  ▼
       server auto-shuts down after 30s grace period
```

## 7. Phase 1 — Components

### 7.1 `fetch_sources.py`

Returns a `Context` dataclass holding everything needed to render the page, serialized to `context.json` for the skill to read. Each fetch is independent and parallelizable.

- `fetch_calendar(calendar_id, *, start, end, exclude_recurring=False) → list[Event]`
  Wraps the existing `gcal-fetch` skill. Called once per calendar in config (general, meals, dalton personal, each school).
- `fetch_gmail(account, *, label=None, query=None, max_results=50) → list[Message]`
  Wraps the existing `gmail-fetch` skill, extended to accept `--account dalton|maggie`. Always uses **snippet + metadata mode** (subject, sender, snippet, date) — never full-body in the default fetch. Full-body fetch is reserved for Phase 2 buttons that explicitly request it.
- `fetch_todoist_project(project_name) → list[Task]`
  Wraps existing Todoist skill or direct API call. Called for: `Meals`, `Date Night Ideas`, `Screen time`. Plus `fetch_todoist_deadlines(window_days=14) → list[Task]` for the Major Deadlines section pre-fill.

**Gmail filter strategy** (to control volume and token cost):

- Default query for each Gmail account: `newer_than:7d -category:promotions -label:spam -label:Newsletters`
- `max_results=50` per account. If a 7-day window returns more than 50 messages, take the newest 50 and the skill flags "high inbox volume — review manually" in the margin flags.
- Snippet-only fetch (no full body) by default.
- "Kid's School" label fetch uses the label ID (not display name) to avoid apostrophe encoding issues; same 50-max and snippet-only rules.

**Context dataclass shape:**

```python
@dataclass
class Context:
    week_start: date           # Friday of upcoming week
    week_end: date             # Thursday after that
    horizon_end: date          # week_end + 21 days
    general_events: list[Event]      # next 7d + horizon, from shared general cal
    meal_events_last: list[Event]    # last 7d from shared meal cal (retrospective)
    personal_events: list[Event]     # Dalton personal Gcal, next 7d
    school_events: list[Event]       # all configured school cals merged, next 7d
    dalton_gmail: list[Message]      # last 7d, snippet-only
    maggie_gmail: list[Message]      # last 7d, snippet-only
    kid_school_emails: list[Message] # last 7d, snippet-only
    meals_library: list[Task]        # Meals project tasks
    date_night_ideas: list[Task]
    screen_time_ideas: list[Task]
    upcoming_deadlines: list[Task]
    inbox_volume_flag: bool          # True if any account hit max_results cap
```

### 7.2 Brief generation (driven by `SKILL.md`, no Python file)

The skill instructs Claude (in the user's Code session) to:

1. Read `context.json` written by `fetch_sources.py`.
2. Read `prompts/retrospective.md` and produce a JSON file `retrospective.json` with 5-10 short bullets summarizing last week.
3. Read `prompts/margin_flags.md` and produce a JSON file `margin_flags.json` with 0-5 short flags about the upcoming week, scoped to data already known (calendar conflicts, overcommitted days, gaps). Cannot flag conflicts against fields the user will fill in during the session.

These are LLM tasks the skill performs inline within the Claude Code conversation — no Python module shells out to `claude -p`. The prompt templates are committed Markdown files, version-controlled like code.

**Model selection:** Sonnet 4.6 is the right level for these summarization + light pattern-finding tasks. Opus 4.7 is overkill at ~5x token cost. The skill assumes Sonnet 4.6 (whatever model the user's session is running with).

### 7.3 `render_page.py`

Renders `session.html` from `templates/session.html.jinja` by reading `context.json`, `retrospective.json`, and `margin_flags.json`. Single output file at a known path; `server.py` serves it.

The template defines three bands as described in §7.5.

### 7.4 `server.py`

Minimal Flask app:

- `GET /` → serves `session.html`.
- `POST /save` → accepts the form submission as JSON, hands it to `write_back.py`, returns the rendered summary HTML on success (or per-target retry blocks on partial success). The frontend swaps the page body to this HTML.
- On successful save, server schedules a self-shutdown 30 seconds later (gives the browser time to render the response).
- Phase 2 will add `POST /assist/<button_name>` endpoints (see §12). Phase 1 does not include them.

Runs on `localhost:8000`. No auth (local-only). Single-tenant.

**Abandonment handling:** if no `/save` arrives within 4 hours of startup, server auto-shuts down. User can manually kill via `pkill -f "src.server"` if needed.

### 7.5 `templates/session.html.jinja` — the form

Three bands, top to bottom:

**Top band — context (read-only):**

1. **Header** — week dates, session start timestamp.
2. **Last-week retrospective** — LLM bullets + small "anything else?" note box (free text, optional; goes into summary).
3. **Week ahead at a glance** — 7-day visual grid of all events (general + personal + schools), color-coded by source. Meal calendar excluded (it has its own section).
4. **Horizon (2-4 weeks)** — one-line list of notable upcoming items beyond the 7-day window.
5. **Margin/realism flags** — LLM bullets; section omitted entirely if no flags. Inbox-volume flag (if set) appears here as: "High inbox volume this week — quickly skim your inbox before proceeding."

**Middle band — logistics decisions (user input):**

6. **Dinners** — 7 rows (Fri→Thu). Each row: typeahead from `Meals` Todoist project + free-text fallback. Last week's dinners shown for reference (from meal calendar). "Add new meal" box at bottom → writes to `Meals` project. Decisions write **all-day events** to the shared meal calendar.
7. **Shopping list** — two text areas: necessary (→ `To buy`) and less-necessary (→ `To buy (less necessary)`). One item per line.
8. **Dalton's home schedule** — 5 weekday rows (Mon–Fri). WFH checkbox + "home by" time field. See §7.6 for write rules.
9. **Maggie's art time** — multi-row time-block entry (date + start + end). Writes events to shared general calendar.
10. **Babysitter** — Yes/No. If yes: date + time + who to ask (free text).
11. **Kids' activities** — pre-populated from school calendars + "Kid's School" Gmail label. Pre-loaded rows are **display-only** (events already exist on the school calendar; not re-written). Add new rows for anything not already on calendar (playdates, sports tryouts, etc.) — those get written to the shared general calendar. **Owner per row** (Dalton / Maggie / Both) for pickup/dropoff — captured in the summary view only (calendar events don't take a Todoist assignee).
12. **Church + temple** — pre-populated with anything on shared cal matching church/temple/ministering keywords. Add temple visits, ward activities, ministering assignments.
13. **Around the house** — free-form text area. Each line → task in `Home` project.
14. **Major deadlines** — pre-populated from Todoist deadline tasks (window: next 14 days). Add new ones → `MD ToDos` with deadline field.

**Bottom band — discussion + close:**

15. **Finances** — free-form prompt + text area. No auto-pull, no system write-back. Captured verbatim in the summary view.
16. **Come Follow Me** — pre-populated with this week's lesson title (resolved by deriving the week's reference and constructing the `churchofjesuschrist.org/study/manual/...` URL; fetched at brief-generation time). Text area: who's leading, prep notes.
17. **Fun-anchored close** — pre-populated with 2-3 suggestions each from `Screen time` + `Date Night Ideas`. Pick one or enter new. New idea → writes to `Date Night Ideas`. Final decision → event on shared general calendar.

**Ownership** is integrated into rows that have a decision (small Owner dropdown: Dalton / Maggie / Both), not a separate section.

**Save & write back** — single submit button at the bottom of the form. On click, disables with a spinner ("Writing back…"). On response, page swaps to the summary view (§7.7).

### 7.6 `write_back.py`

On `POST /save`:

1. **Validation pass.** Check for empty required fields (e.g., date when "babysitter = yes" is checked, time fields not blank when present). On any failure, return `400` with per-field errors; the form re-renders with inline error messages. **No** cross-form time-conflict check — overlapping events are allowed.
2. **Archive first.** Save the submitted form payload as `sessions/YYYY-MM-DD-session.html` (via `render_summary.py`) **before any external writes**. Never lose work.
3. **Calendar writes.** For each calendar-bound decision, call Google Calendar create:
   - Shared general cal:
     - **WFH = true** → all-day event titled `Dalton WFH` on that date.
     - **WFH = false, "home by" time set** → 15-min timed event titled `Dalton home` starting at that time (e.g., 5:00 PM → event 5:00-5:15 PM).
     - **Art blocks** — timed event per row (`Maggie art`).
     - **Babysitter slot** — timed event (`Babysitter — [who]`).
     - **Date night** — timed event (`Date night — [activity]`).
     - **New kids' activities** added by the user during the session (see §7.5 #11 — pre-loaded rows are display-only).
   - Shared meal cal: 7 dinner all-day events titled with the meal name.
   - No conflict detection, no dedup. Overlapping events added as-is.
4. **Todoist writes.** For each text-line decision, call Todoist task create per the routing map (§7.8). Each task includes content, project, optional deadline, optional assignee.
5. **Return summary HTML.** `render_summary.py` produces a clean view of: retrospective notes, every decision with owner, finances discussion verbatim, and a per-write breakdown ("Created 4 events on Maggie and Dalton calendar; 7 meals; 12 Todoist tasks across 4 projects"). Failed writes show per-target retry blocks.
6. **Schedule shutdown.** 30 seconds after a successful response, server self-shuts. (Partial-success responses don't trigger shutdown — user may retry failed writes.)

Each external write step is atomic and independent. If Calendar succeeds but Todoist fails, the summary view reports partial success and the user can retry just the failed bits via per-target retry buttons.

### 7.7 `render_summary.py`

Renders the post-save summary HTML from `templates/summary.html.jinja`. Used in two places:

- **In-place page swap after Save** — server returns this HTML; frontend replaces `<body>` with it.
- **Archive** — same HTML written to `sessions/YYYY-MM-DD-session.html` for later viewing.

The summary contains:
- Header: "Weekly Planning — Week of [Fri DD] — Saved [timestamp]"
- The retrospective notes
- Every decision the user made, grouped by section, with owner
- Finances discussion verbatim
- Write-back breakdown (which events/tasks created in which calendars/projects, with links if available)
- A "Failed writes" section (only if any failed) with per-target retry buttons

### 7.8 Routing map

| Form section input | Destination |
|---|---|
| Dinners (7 slots) | Shared meal calendar (all-day events) |
| Shopping list — necessary | Todoist `To buy` |
| Shopping list — less necessary | Todoist `To buy (less necessary)` |
| General to-dos, follow-ups, calls | Todoist `MD ToDos` |
| Home repairs / house items | Todoist `Home` |
| New dinner idea captured | Todoist `Meals` |
| Gift idea for Maggie | Todoist `Maggie's Wish List` |
| Gift idea for Dalton | Todoist `Dalton's Wish List` |
| New movie/show mentioned | Todoist `Screen time` |
| New date night idea brainstormed | Todoist `Date Night Ideas` |
| WFH days, art blocks, babysitter, date night, kids activities (new) | Shared general ("Maggie and Dalton") calendar |

Out of scope (not pulled or written): `Maggie Art`, `Galleries DMV`.

### 7.9 `config.yaml`

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
      token_file: tokens/dalton.json
    - name: maggie
      address: TBD              # captured during Phase 0
      token_file: tokens/maggie.json
  kid_school_label_id: TBD      # fetched from Gmail API after label creation
  default_query: "newer_than:7d -category:promotions -label:spam -label:Newsletters"
  max_results_per_account: 50

todoist:
  projects:
    shopping: "To buy"
    shopping_wants: "To buy (less necessary)"
    general_todos: "MD ToDos"
    home: "Home"
    meals: "Meals"
    date_night_ideas: "Date Night Ideas"
    screen_time: "Screen time"
    gifts_maggie: "Maggie's Wish List"
    gifts_dalton: "Dalton's Wish List"
  collaborator_ids:
    dalton: TBD                 # Todoist user ID for assignee write-back
    maggie: TBD

family:
  owners: [Dalton, Maggie]
  kids:
    - name: TBD
      age: TBD
    - name: TBD
      age: TBD

# Models are listed for reference; actual model used is whatever the Claude Code
# session is running. Sonnet 4.6 is appropriate for all current tasks.
# Haiku 4.5 could be considered for Phase 2 simpler operations (e.g., email categorization).
notes:
  brief_model_assumed: claude-sonnet-4-6
```

A `config.example.yaml` with placeholders is committed. The real `config.yaml` is gitignored.

## 8. Error handling & validation

- **Atomic archive.** Form payload is archived to `sessions/YYYY-MM-DD-session.html` before any external API calls. A crash mid-write-back leaves the archive intact.
- **Per-target atomicity.** Each external write (Calendar create, Todoist create) is independent. Partial success is surfaced in the summary view with per-target retry buttons.
- **Source-fetch failures.** If any source fetch fails (auth expired, network), the pre-brief proceeds with whatever did succeed. The form shows a small banner per missing source: "Maggie's Gmail unavailable — retrieve manually or re-auth." This prevents the whole session from being blocked by one stale token.
- **Required-field validation** before write-back. Empty babysitter date when "yes" is checked, empty art-block end time, etc. No cross-form time-conflict validation (overlapping events allowed by design).
- **Schema validation on config load.** Missing required calendar IDs, missing Todoist project names, malformed kid ages → aborts with a one-line actionable error before any fetch begins.
- **Gmail label lookup.** "Kid's School" label is referenced by stable Gmail label **ID** (not name) in API calls to avoid issues with the apostrophe in the display name.
- **High inbox volume.** If any Gmail account hits the 50-message cap, sets `Context.inbox_volume_flag` → shows a flag in §7.5 #5 so the user knows to skim their inbox manually.
- **CFM lesson fetch failure.** If `churchofjesuschrist.org` is unreachable, the section is rendered with a "couldn't fetch this week's lesson" note and a free text field; the session proceeds.
- **Double-click prevention.** Save button disables with spinner on first click. On successful response, the page body is replaced with the summary view — the button no longer exists in the DOM, making double-submission structurally impossible.

## 9. Testing

Pure functions in `fetch_sources.py` (parsing/normalization helpers) and `write_back.py` (routing logic, validation) are unit-tested against synthetic fixtures committed to the repo. No live API calls in tests. Coverage:

- **Routing map correctness:** for each input section, asserted destination matches §7.8.
- **Required-field validation:** every required field rejects empty/null; optional fields accept empty.
- **WFH write rules:** WFH=true with no "home by" → all-day event; WFH=false with "home by" set → 15-min timed event; WFH=true with "home by" also set → all-day wins, "home by" ignored.
- **Context dataclass shape:** synthetic raw API responses parsed into `Context` produce the expected nested structure.
- **Gmail volume cap:** synthetic 75-message response respects `max_results=50` cap and sets `inbox_volume_flag=True`.
- **HTML render smoke test:** end-to-end on synthetic `Context` + LLM output → load resulting session HTML → assert each of the 17 sections has its expected DOM anchor (`#section-dinners`, etc.).
- **Summary render smoke test:** synthetic decisions → produce summary HTML → assert all decisions present and routing-map summary correct.
- **Server endpoint test:** Flask test client `POST /save` with synthetic payload → assert response body is summary HTML; partial-success scenario returns retry blocks.

The form submit flow is exercised against a Flask test client; no real Calendar/Todoist calls. Live integration is verified manually on the first real Phase 1 session.

## 10. Operational notes

- **How to start a session.** Open Claude Code. Run `/weekly-planning`. Claude orchestrates source fetches, generates the retrospective + margin flags inline (no shell-out), renders the form, starts the local server in the background, and opens Chrome to `localhost:8000`. Wait time: ~1-3 min depending on Gmail volume.
- **How to view a past session.** Past sessions are HTML files in `sessions/`. Open the most recent in Chrome via `open -a "Google Chrome" sessions/$(ls sessions/ | tail -1)`. A small wrapper script `weekly-planning-view` (one-liner, in the repo) provides this. To list all past sessions: `ls sessions/`.
- **Save behavior.** Single click on "Save & write back." Button disables with spinner during the request. Server returns summary HTML, page swaps to it. Server auto-shuts down 30s later.
- **Partial-success retry.** If a write target fails (Todoist API down, etc.), summary view shows a "Retry write-back" button scoped to the failed target. Clicking retries just that target.
- **Session abandonment.** If no save happens within 4 hours, server self-shuts. To kill manually: `pkill -f "src.server"`.
- **Archive retention.** `sessions/*.html` accumulates indefinitely. User can manually delete older ones; no auto-cleanup.
- **Token refresh.** Gmail refresh tokens are long-lived; expect Maggie's to occasionally need re-consent (Google may force re-auth every ~6 months). Surfaced as a fetch error with the exact command to run.
- **Config edits.** New school calendar, new Todoist project, kid age update → edit `config.yaml` and re-run. No code change needed.

## 11. Phase 0 — prerequisites (one-time setup)

These have to be done before Phase 1 is meaningful. Half a day of clicking, no coding.

1. **Add Maggie's Gmail to existing OAuth project.** Same Google Cloud `client_id`/`client_secret`; re-run consent flow logged in as her; store her refresh token in `tokens/maggie.json`. Small tweak to `gmail-fetch` to accept `--account dalton|maggie`. Read-only scopes only.
2. **Create "Kid's School" Gmail label + filters.** Combined label covers preschool (Brightwheel) + elementary. Filters: from-Brightwheel-domain → label; from-elementary-school-domains → label.
3. **Subscribe school iCal feeds in Dalton's Google Calendar.** Already done: `j1uk9rlvto8tejnr6jrjkolhhahf30f0@import.calendar.google.com`. Add preschool + any others as iCal feeds become available.
4. **Create `Date Night Ideas` shared Todoist project.** New, parallels existing `Screen time` and `Meals`.
5. **Confirm exact Todoist project names** in routing map match existing projects (caps/apostrophes matter for API match).
6. **Build `config.yaml`** from `config.example.yaml` — fill in TBD fields: Maggie's address, "Kid's School" label ID, Todoist collaborator IDs, kids' names and ages.
7. **Commit `.gitignore`** with `tokens/`, `sessions/`, `config.yaml` entries before any real values land in the repo.

## 12. Phase 2 — AI assist buttons (deferred)

Built only after 2-3 real Phase 1 sessions reveal which assists actually matter. Candidates ranked by anticipated value:

| Section | Button | Priority |
|---|---|---|
| Dinners | "Suggest dinners around this week's events" (factors in busy nights, prefers easy meals on those nights) | High |
| Shopping list | "Generate shopping list from these dinners" (parses meal ingredients from `Meals` task descriptions) | High |
| Come Follow Me | "Pull lesson + 3 activities for kids ages [X, Y]" (uses kid ages from config) | High |
| Babysitter | "Draft text to ask [person]" | Medium |
| Kids' activities | "Anything I missed in Kid's School emails?" (allowed to fetch full bodies) | Medium |
| Whole form | "Spot conflicts/overcommitment" (re-runs after user fills decisions) | Medium |
| Retrospective | "Summarize what slipped + why" | Low |

**Open architectural question for Phase 2:** the form (running in Chrome, talking to Flask) needs to trigger LLM calls. With the Phase 1 execution model (interactive Claude Code), the natural pattern is:

- Skill stays alive after launching the form (instead of exiting).
- Form button click → Flask writes a request file (`assist_queue/<id>.json`) → skill polls and processes → writes response file → server returns to browser via long-poll or SSE.

This keeps everything subscription-covered (interactive Claude). Alternative is shelling out to `claude -p` per button click, which re-introduces `-p` billing exposure. Decision deferred until Phase 2 is actually built.

## 13. Phase 3 — chat panel (only if needed)

Right-side "ask Claude anything" panel with full session `Context` loaded into the prompt. Useful for one-offs like "what's Maggie's Saturday like?" or "any flights in our shared inbox recently?" Built only if Phase 2 buttons feel insufficient after a few weeks of use. Same Phase 2 architectural question applies.

## 14. Open questions for implementation

- **Maggie's Gmail account address.** Captured during Phase 0 step 1.
- **"Kid's School" Gmail label ID.** Fetched via Gmail API once the label is created (Phase 0 step 2).
- **Todoist collaborator IDs for Dalton and Maggie.** Fetched via Todoist API once and stored in `config.yaml`.
- **Kid first names and ages.** Filled into `config.yaml` (Phase 0 step 6). Used for Phase 2 CFM activity suggestions.
- **Additional school calendar IDs.** Added to `config.yaml` as iCal feeds are subscribed (preschool, future-year elementary).
- **CFM lesson URL pattern.** The exact `churchofjesuschrist.org/study/manual/...` URL construction needs confirmation against a known-good week before relying on it programmatically.
- **`gcal-fetch` multi-calendar handling.** Decide at implementation time whether to extend the skill to accept multiple `--calendar-id` flags in one invocation, or invoke it per calendar and merge in `fetch_sources.py`. Either is acceptable.
- **`weekly-planning-view` wrapper.** Trivial one-liner script — confirm location (`/usr/local/bin/`, `~/.local/bin/`, or in the repo) at implementation time.
