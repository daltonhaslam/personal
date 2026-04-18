#!/bin/bash
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

# Pick the latest installed claude VS Code extension binary
CLAUDE=$(ls -td /Users/daltonhaslam/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | head -1)
SKILL="/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/SKILL.md"
BRIEF="/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/brief.html"
LOG="/Users/daltonhaslam/Documents/Claude/Personal/Projects/daily-brief/daily-brief.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

log "Starting daily brief..."

if [ -z "$CLAUDE" ] || [ ! -x "$CLAUDE" ]; then
    log "ERROR: claude binary not found under ~/.vscode/extensions"
    exit 1
fi

log "Using claude: $CLAUDE"

# Run claude with SKILL.md as the prompt
"$CLAUDE" --print --dangerously-skip-permissions < "$SKILL" >> "$LOG" 2>&1

# Verify brief was written
if [ ! -f "$BRIEF" ]; then
    log "ERROR: brief.html was not written by claude"
    exit 1
fi

log "brief.html written. Creating Apple Note..."

export BRIEF_PATH="$BRIEF"
export NOTE_TITLE="Daily Brief — $(date +'%A, %B %-d')"

python3 << 'PYEOF'
import subprocess, os, tempfile

brief_path = os.environ['BRIEF_PATH']
note_title = os.environ['NOTE_TITLE']

# AppleScript reads the HTML directly from disk — avoids all string-escaping issues
script = f'''tell application "Notes"
    tell account "iCloud"
        set noteTitle to "{note_title}"
        set htmlContent to do shell script "cat " & quoted form of "{brief_path}"
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
log "Daily brief complete."
