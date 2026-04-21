#!/bin/bash
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

CLAUDE=$(ls -td /Users/daltonhaslam/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | head -1)
SKILL="/Users/daltonhaslam/Documents/Claude/Personal/Projects/email-to-todoist-tasks/SKILL.md"
LOG="/Users/daltonhaslam/Documents/Claude/Personal/Projects/email-to-todoist-tasks/email-todoist.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

log "Starting email-to-todoist..."

if [ -z "$CLAUDE" ] || [ ! -x "$CLAUDE" ]; then
    log "ERROR: claude binary not found under ~/.vscode/extensions"
    exit 1
fi

log "Using claude: $CLAUDE"

TODOIST_API_TOKEN=$(security find-generic-password -a "todoist" -s "TODOIST_API_TOKEN" -w 2>/dev/null) || {
    log "ERROR: TODOIST_API_TOKEN not found in Keychain"
    log "Run: security add-generic-password -a todoist -s TODOIST_API_TOKEN -w YOUR_TOKEN"
    exit 1
}
export TODOIST_API_TOKEN

"$CLAUDE" --print --dangerously-skip-permissions < "$SKILL" >> "$LOG" 2>&1

log "email-to-todoist complete."
