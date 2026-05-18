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
