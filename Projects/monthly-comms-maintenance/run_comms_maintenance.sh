#!/bin/bash
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

CLAUDE=$(ls -td /Users/daltonhaslam/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | head -1)
SKILL="/Users/daltonhaslam/Documents/Claude/Personal/Projects/monthly-comms-maintenance/SKILL.md"
REPORT="/Users/daltonhaslam/Documents/Claude/Personal/Projects/monthly-comms-maintenance/maintenance.html"
LOG="/Users/daltonhaslam/Documents/Claude/Personal/Projects/monthly-comms-maintenance/comms-maintenance.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

log "Starting comms maintenance..."

if [ -z "$CLAUDE" ] || [ ! -x "$CLAUDE" ]; then
    log "ERROR: claude binary not found under ~/.vscode/extensions"
    exit 1
fi

log "Using claude: $CLAUDE"

"$CLAUDE" --print --dangerously-skip-permissions < "$SKILL" >> "$LOG" 2>&1

if [ ! -f "$REPORT" ]; then
    log "ERROR: maintenance.html was not written by claude"
    exit 1
fi

log "maintenance.html written. Creating Apple Note..."

export REPORT_PATH="$REPORT"
export NOTE_TITLE="Comm OS Maintenance — $(date +'%B %Y')"

python3 << 'PYEOF'
import subprocess, os, tempfile

report_path = os.environ['REPORT_PATH']
note_title = os.environ['NOTE_TITLE']

script = f'''tell application "Notes"
    tell account "iCloud"
        set noteTitle to "{note_title}"
        set htmlContent to do shell script "cat " & quoted form of "{report_path}"
        try
            set matchingNotes to every note whose name is noteTitle
            repeat with n in matchingNotes
                delete n
            end repeat
        end try
        make new note with properties {{name:noteTitle, body:htmlContent}}
    end tell
end tell'''

with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', delete=False) as f:
    f.write(script)
    tmp = f.name

try:
    result = subprocess.run(['osascript', tmp], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"osascript error: {result.stderr}")
        raise SystemExit(1)
    print("Apple Note created successfully")
finally:
    os.unlink(tmp)
PYEOF

log "Apple Note created successfully."
log "Comms maintenance complete."
