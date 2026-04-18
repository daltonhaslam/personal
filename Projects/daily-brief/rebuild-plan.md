# Daily Brief — Local Rebuild Plan
> **COMPLETED 2026-04-18.** All steps implemented and tested. LaunchAgent active. See SKILL.md and run_daily_brief.sh for current state.


## Goal
A fully local, zero-touch automation that generates a personalized daily brief every evening and creates an Apple Note — no cloud agents, no Apple Shortcuts required. The only requirement: Mac is on at 7pm.

---

## Why Rebuild
The current setup was migrated from Claude Cowork and carries cloud-architecture assumptions:
- SKILL.md has session-mounting logic (`/sessions/*/mnt/Claude`) for cloud sandboxes
- Delivery uses a file → Apple Shortcut chain (unnecessary complexity)
- Scheduling used a RemoteTrigger (cloud agent — cannot write to local filesystem)

The new architecture is purely local: LaunchAgent → shell script → `claude` CLI → brief.html → osascript (AppleScript) → Apple Note. No Apple Shortcuts, no remote triggers.

---

## New Architecture

```
7:00 PM
  └─ LaunchAgent fires (com.dalton.daily-brief.plist)
       └─ runs run_daily_brief.sh
            ├─ invokes: claude -p < SKILL.md  (locally, with MCP access)
            │    ├─ pulls Gmail (MCP)
            │    ├─ pulls Google Calendar (MCP)
            │    ├─ pulls Todoist (MCP)
            │    └─ writes brief.html to project dir
            └─ runs osascript → creates Apple Note titled "Daily Brief — [Date]"
```

---

## Step 0 — Clean Up Old Setup

### A. Disable the RemoteTrigger
A stale RemoteTrigger (`trig_01BhaBkH7TR1ZVzGgLEdpEQe`, name: "daily-brief") exists in the claude.ai account.
- Go to https://claude.ai/code/scheduled and disable or delete it.
- It was a cloud agent and could never write local files. It should not remain active.

### B. Archive the old SKILL.md
Rename the current `SKILL.md` to `SKILL.md.cowork-archive` so it's preserved but not used.

### C. Remove (or ignore) Scheduled/ config
`Personal/Scheduled/daily-brief.md` references the RemoteTrigger workflow. It can be deleted or left as documentation of the old approach — it does not affect the new build.

---

## Step 1 — MCP Access (Already Verified ✅)

**Pre-verified before this plan was handed off.** The `claude` CLI binary successfully accessed Todoist and Gmail MCP connectors outside of VS Code in a standalone terminal session. No additional MCP configuration is needed.

The binary to use:
```
/Users/daltonhaslam/.vscode/extensions/anthropic.claude-code-2.1.114-darwin-arm64/resources/native-binary/claude
```

No fallback path needed — proceed directly to Step 2.

---

## Step 2 — Build the New SKILL.md

Rebuild SKILL.md from scratch with local assumptions only. Remove all cloud/Cowork artifacts.

### What changes from the old version:
- Remove `/sessions/*/mnt/Claude` glob logic — hardcode the path directly
- Remove the "Available Tools" section (that was for Cowork context injection)
- Step 6 (Write to File) becomes simpler — just write to the hardcoded path
- Add a clear "you are running locally on Dalton's Mac" statement at the top

### Keep the same data logic:
- Step 1: Get tomorrow's date via python3
- Step 2: Pull calendar events from both calendars (filter recurring from shared calendar)
- Step 3: Pull Todoist tasks (overdue p1/p2 + p4 count + due tomorrow)
- Step 4: Scan Gmail last 24h (categorize into Action Required / Family / Church / Financial / FYI / Skip)
- Step 5: Format as HTML (same template)
- Step 6: Write to `/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/brief.html`

### Todoist project reference (preserve exactly):
```
6W59m22P9ccJgmR7 = MWH PA Job
6gMvgRPQg9XCv4h9 = Personal
6CrfF6gPVgXcfHRr = M&D (shared with wife)
6Crg6xfrxV9Pj3x8 = Personal
6Crg6xfrxvRpf7X4 = Financial
6Crg6xfv3Rg5CWr8 = Doctored Money
6CrfF6gPWGFV967H = Home
6CrfF6gPf3cF58C9 = DC
6Crg6xfv3f5458XP = Someday Maybe (EXCLUDE)
Inbox = Inbox
```

### Calendar IDs:
- Personal: `haslam.dalton@gmail.com`
- Shared: `rgq78thkje9h8p3c57718eamog@group.calendar.google.com` (non-recurring events only)

---

## Step 3 — Build run_daily_brief.sh

Create `/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/run_daily_brief.sh`

### Script responsibilities:
1. Set PATH so `python3` and other tools are found (LaunchAgents have a stripped PATH)
2. Define the claude binary path
3. Run `claude --print` with SKILL.md as the prompt and `--dangerously-skip-permissions`
4. Verify `brief.html` was written successfully
5. Run osascript to create the Apple Note
6. Log results to `daily-brief.log`

### Skeleton:
```bash
#!/bin/bash
set -e

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

CLAUDE="/Users/daltonhaslam/.vscode/extensions/anthropic.claude-code-2.1.114-darwin-arm64/resources/native-binary/claude"
SKILL="/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/SKILL.md"
BRIEF="/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/brief.html"
LOG="/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/daily-brief.log"

echo "[$(date)] Starting daily brief..." >> "$LOG"

# Run claude with SKILL.md as prompt
"$CLAUDE" --print --dangerously-skip-permissions < "$SKILL" >> "$LOG" 2>&1

# Verify brief was written
if [ ! -f "$BRIEF" ]; then
    echo "[$(date)] ERROR: brief.html was not written." >> "$LOG"
    exit 1
fi

echo "[$(date)] brief.html written. Creating Apple Note..." >> "$LOG"

# Create Apple Note via osascript
BRIEF_CONTENT=$(cat "$BRIEF")
DATE_LABEL=$(date +'%A, %B %-d')

osascript << EOF
tell application "Notes"
    tell account "iCloud"
        -- Delete any existing Daily Brief note from today to avoid duplicates
        set existingNotes to every note whose name starts with "Daily Brief"
        repeat with n in existingNotes
            delete n
        end repeat
        -- Create new note
        make new note with properties {name:"Daily Brief — $DATE_LABEL", body:"$BRIEF_CONTENT"}
    end tell
end tell
EOF

echo "[$(date)] Apple Note created successfully." >> "$LOG"
```

### Important implementation notes:
- The osascript HTML escaping must be tested carefully — single quotes in email content will break the heredoc. Use Python to call osascript if escaping is a problem:
  ```python
  python3 -c "
  import subprocess, sys
  html = open('brief.html').read()
  # Pass HTML via AppleScript property list to avoid escaping issues
  ..."
  ```
- Consider using `osascript -e` line by line or writing to a temp `.applescript` file and running it
- The "delete existing Daily Brief notes" logic should only delete today's — or just overwrite. Decide during implementation.

---

## Step 4 — Build the LaunchAgent Plist

Create: `~/Library/LaunchAgents/com.dalton.daily-brief.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dalton.daily-brief</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/run_daily_brief.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>19</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/daily-brief.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/daily-brief-error.log</string>
</dict>
</plist>
```

### Load/reload commands:
```bash
# Load for the first time
launchctl load ~/Library/LaunchAgents/com.dalton.daily-brief.plist

# To reload after changes
launchctl unload ~/Library/LaunchAgents/com.dalton.daily-brief.plist
launchctl load ~/Library/LaunchAgents/com.dalton.daily-brief.plist

# To test immediately (without waiting for 7pm)
launchctl start com.dalton.daily-brief
```

---

## Step 5 — Test End-to-End

Run in this order:

### Test 1: Shell script directly
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/run_daily_brief.sh
```
- Verify `brief.html` is created with real content
- Verify Apple Note appears in Notes.app under iCloud
- Check `daily-brief.log` for errors

### Test 2: LaunchAgent trigger
```bash
launchctl start com.dalton.daily-brief
```
- Same verification as Test 1
- Confirms the plist and script path are correct

### Test 3: Observe the 7pm fire
- Let it run at the scheduled time on a subsequent day
- Confirm a new Apple Note appears without any manual action

---

## Final File Structure

```
Personal/Projects/daily-brief/
├── SKILL.md                  ← rebuilt (local-first)
├── SKILL.md.cowork-archive   ← old version preserved
├── run_daily_brief.sh        ← new wrapper script
├── rebuild-plan.md           ← this file
├── .gitignore                ← already ignores brief.html; add *.log
├── brief.html                ← output (gitignored)
├── daily-brief.log           ← run log (gitignored)
└── daily-brief-error.log     ← error log (gitignored)

~/Library/LaunchAgents/
└── com.dalton.daily-brief.plist  ← scheduler
```

---

## Key Decisions for the Implementing Session

1. **MCP test must happen first** (Step 1) before writing any other code. Everything depends on whether the claude CLI can reach Gmail/Calendar/Todoist outside VS Code.

2. **osascript escaping** is the trickiest implementation detail. If the HTML brief contains quotes or special characters (it will), the heredoc approach breaks. Use Python subprocess with a temp AppleScript file as the safer option.

3. **Note replacement strategy**: Currently the osascript deletes all notes starting with "Daily Brief" before creating a new one. This is aggressive — consider only deleting today's note, or keeping a rolling 7-day history.

4. **Claude binary path**: The plist hardcodes the VS Code extension binary path, which changes when the extension updates. Consider symlinking it or finding a more stable path. Check if a stable `claude` symlink exists at `/usr/local/bin/claude` or `/opt/homebrew/bin/claude` — if not, create one.

5. **LaunchAgent runs as the logged-in user**: Good — it has keychain access, filesystem access, and can drive Notes.app via AppleScript.
