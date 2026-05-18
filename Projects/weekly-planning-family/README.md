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
