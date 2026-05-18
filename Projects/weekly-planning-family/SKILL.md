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

## Step 2 — Generate retrospective, margin flags, and CFM lesson (in parallel)

These three outputs are independent. **Issue all the tool calls in a single response** so they run concurrently.

Reads (issue in parallel):
- `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/context.json`
- `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/prompts/retrospective.md`
- `/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family/prompts/margin_flags.md`
- WebFetch `https://www.churchofjesuschrist.org/study/manual/come-follow-me-for-home-and-church-old-testament-2026` (or the current year's manual) — find the lesson for the week containing `week_start` from `context.json` (CFM weeks run Mon–Sun).

After all reads complete, follow each prompt's instructions exactly and write three files (Writes can also batch in one response):

- `retrospective.json` — schema per `retrospective.md`.
- `margin_flags.json` — schema per `margin_flags.md`. Empty `{"flags": []}` is valid.
- `cfm_title.txt` — full lesson title (e.g., `Joshua 1–8; 23–24: "Be Strong and of a Good Courage"`).

**Per-output failure handling:**
- If WebFetch fails or you can't confidently identify this week's lesson, write `this week's lesson (fetch failed)` to `cfm_title.txt` and continue. Do NOT block the JSON outputs on the CFM step.
- If a JSON write fails, fix and retry — the session can't proceed without all three artifacts present.

---

## Step 3 — Render the form HTML

The render script reads `context.json`, `retrospective.json`, `margin_flags.json`, and `cfm_title.txt`. Run via Bash:

```bash
cd /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-planning-family
source .venv/bin/activate
# Pass CFM title via env var to keep CLI simple
WEEKLY_PLANNING_CFM_TITLE="$(cat cfm_title.txt)" python -m src.render_page
```

Expected: prints `session.html written: ...` and the file exists.

---

## Step 4 — Start the form server in the background and open Chrome

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
