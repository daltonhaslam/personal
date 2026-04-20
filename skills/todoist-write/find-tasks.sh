#!/usr/bin/env bash
# Query tasks in a Todoist project and filter by content match.
# Output: JSON array of {id, content} to stdout. Errors to stderr.
# Usage: find-tasks.sh --query <string> --project-id <id>

set -euo pipefail

QUERY=""
PROJECT_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --query)      QUERY="$2";      shift 2 ;;
        --project-id) PROJECT_ID="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$QUERY" ]]; then
    echo '{"error": "--query is required"}' >&2
    exit 1
fi
if [[ -z "$PROJECT_ID" ]]; then
    echo '{"error": "--project-id is required"}' >&2
    exit 1
fi

TODOIST_API_TOKEN=$(security find-generic-password -s TODOIST_API_TOKEN -w 2>/dev/null) || {
    echo '{"error": "TODOIST_API_TOKEN not found in Keychain"}' >&2
    exit 1
}

RESPONSE=$(curl --silent --fail \
    --header "Authorization: Bearer ${TODOIST_API_TOKEN}" \
    --get \
    --data-urlencode "project_id=${PROJECT_ID}" \
    "https://api.todoist.com/api/v1/tasks") || {
    echo '{"error": "Todoist API request failed (HTTP error or network issue)"}' >&2
    exit 1
}

if ! echo "$RESPONSE" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    echo "{\"error\": \"Non-JSON response: ${RESPONSE:0:200}\"}" >&2
    exit 1
fi

TASKS_JSON="$RESPONSE" QUERY_STR="$QUERY" python3 << 'PYEOF'
import json
import os

raw = json.loads(os.environ["TASKS_JSON"])
tasks = raw.get("results", raw) if isinstance(raw, dict) else raw
query = os.environ["QUERY_STR"].lower()

matches = [
    {"id": t["id"], "content": t["content"]}
    for t in tasks
    if query in t.get("content", "").lower()
]

print(json.dumps(matches))
PYEOF
