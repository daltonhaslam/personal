#!/usr/bin/env bash
# Add a task to Todoist via REST API.
# Output: created task JSON to stdout. Errors to stderr.
# Usage: add-task.sh --content <string> [--description <string>] [--due-string <string>]
#                    [--priority <1-4>] [--project-id <id>] [--labels <comma-separated>]
#
# Defaults (applied unless overridden):
#   --due-string  "today"
#   --priority    3              (p2; Todoist scale: 4=p1, 3=p2, 2=p3, 1=p4)
#   --project-id  6Crg6xfrxV9Pj3x8  (Personal project)
#   --labels      "claude"

set -euo pipefail

CONTENT=""
DESCRIPTION=""
DUE_STRING="today"
PRIORITY="3"
PROJECT_ID="6Crg6xfrxV9Pj3x8"
LABELS="claude"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --content)     CONTENT="$2";     shift 2 ;;
        --description) DESCRIPTION="$2"; shift 2 ;;
        --due-string)  DUE_STRING="$2";  shift 2 ;;
        --priority)    PRIORITY="$2";    shift 2 ;;
        --project-id)  PROJECT_ID="$2";  shift 2 ;;
        --labels)      LABELS="$2";      shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$CONTENT" ]]; then
    echo '{"error": "--content is required"}' >&2
    exit 1
fi

TODOIST_API_TOKEN=$(security find-generic-password -s TODOIST_API_TOKEN -w 2>/dev/null) || {
    echo '{"error": "TODOIST_API_TOKEN not found in Keychain"}' >&2
    exit 1
}

BODY=$(CONTENT="$CONTENT" DESCRIPTION="$DESCRIPTION" DUE_STRING="$DUE_STRING" \
       PRIORITY="$PRIORITY" PROJECT_ID="$PROJECT_ID" LABELS="$LABELS" \
       python3 << 'PYEOF'
import json
import os

payload = {
    "content":    os.environ["CONTENT"],
    "due_string": os.environ["DUE_STRING"],
    "priority":   int(os.environ["PRIORITY"]),
    "project_id": os.environ["PROJECT_ID"],
    "labels":     [l.strip() for l in os.environ["LABELS"].split(",") if l.strip()],
}

desc = os.environ.get("DESCRIPTION", "")
if desc:
    payload["description"] = desc

print(json.dumps(payload))
PYEOF
)

RESPONSE=$(curl --silent --fail \
    --header "Authorization: Bearer ${TODOIST_API_TOKEN}" \
    --header "Content-Type: application/json" \
    --data "$BODY" \
    "https://api.todoist.com/api/v1/tasks") || {
    echo '{"error": "Todoist API request failed (HTTP error or network issue)"}' >&2
    exit 1
}

if ! echo "$RESPONSE" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    echo "{\"error\": \"Non-JSON response: ${RESPONSE:0:200}\"}" >&2
    exit 1
fi

TASK_JSON="$RESPONSE" python3 << 'PYEOF'
import json
import os

t = json.loads(os.environ["TASK_JSON"])
PRIORITY_MAP = {4: "p1", 3: "p2", 2: "p3", 1: "p4"}

output = {
    "id":       t["id"],
    "content":  t["content"],
    "due":      (t.get("due") or {}).get("date"),
    "priority": PRIORITY_MAP.get(t.get("priority", 1), "p4"),
    "labels":   t.get("labels", []),
    "url":      t.get("url"),
}
print(json.dumps(output))
PYEOF
