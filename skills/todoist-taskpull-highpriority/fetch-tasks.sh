#!/usr/bin/env bash
# Fetch p1/p2 Todoist tasks due today/overdue/tomorrow or with deadline within 3 days.
# Output: JSON to stdout. Errors to stderr.
# Requires: TODOIST_API_TOKEN env var

set -euo pipefail

if [[ -z "${TODOIST_API_TOKEN:-}" ]]; then
    echo '{"error": "TODOIST_API_TOKEN is not set"}' >&2
    exit 1
fi

BASE_URL="https://api.todoist.com/api/v1/tasks/filter"
AUTH="Authorization: Bearer ${TODOIST_API_TOKEN}"

# Call A: p1/p2 tasks due today, overdue, or tomorrow
QUERY_A="(today | overdue | tomorrow) & (p1 | p2)"

# Call B: p1/p2 tasks with deadline within next 3 days
# "before: +4 days" is exclusive, capturing deadlines today through 3 days out
QUERY_B="deadline before: +4 days & (p1 | p2)"

RESPONSE_A=$(curl --silent --fail \
    --header "$AUTH" \
    --get \
    --data-urlencode "query=${QUERY_A}" \
    "${BASE_URL}") || {
        echo "{\"error\": \"Todoist API call A failed (HTTP error or network issue)\"}" >&2
        exit 1
    }

RESPONSE_B=$(curl --silent --fail \
    --header "$AUTH" \
    --get \
    --data-urlencode "query=${QUERY_B}" \
    "${BASE_URL}") || {
        echo "{\"error\": \"Todoist API call B failed (HTTP error or network issue)\"}" >&2
        exit 1
    }

# Validate JSON (guard against HTML error pages from Todoist)
if ! echo "$RESPONSE_A" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    echo "{\"error\": \"Call A returned non-JSON: ${RESPONSE_A:0:200}\"}" >&2
    exit 1
fi

if ! echo "$RESPONSE_B" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    echo "{\"error\": \"Call B returned non-JSON: ${RESPONSE_B:0:200}\"}" >&2
    exit 1
fi

# Pass JSON blobs via env vars to avoid shell quoting issues with task content
TASKS_A_JSON="$RESPONSE_A" TASKS_B_JSON="$RESPONSE_B" python3 << 'PYEOF'
import json
import os
from datetime import date, datetime, timedelta

PROJECT_NAMES = {
    "6W59m22P9ccJgmR7": "MWH PA Job",
    "6gMvgRPQg9XCv4h9": "Personal",
    "6CrfF6gPVgXcfHRr": "M&D",
    "6Crg6xfrxV9Pj3x8": "Personal",
    "6Crg6xfrxvRpf7X4": "Financial",
    "6Crg6xfv3Rg5CWr8": "Doctored Money",
    "6CrfF6gPWGFV967H": "Home",
    "6CrfF6gPf3cF58C9": "DC",
    "6Crg6xfv3f5458XP": "Someday Maybe",
}

PRIORITY_MAP = {4: "p1", 3: "p2", 2: "p3", 1: "p4"}

tasks_a = json.loads(os.environ["TASKS_A_JSON"]).get("results", [])
tasks_b = json.loads(os.environ["TASKS_B_JSON"]).get("results", [])

today = date.today()
tomorrow = today + timedelta(days=1)
deadline_window_end = today + timedelta(days=3)


def get_due_date(task):
    due = task.get("due")
    if not due:
        return None
    s = due.get("date", "")
    return date.fromisoformat(s[:10]) if s else None


def get_deadline_date(task):
    dl = task.get("deadline")
    if not dl:
        return None
    s = dl.get("date", "")
    return date.fromisoformat(s[:10]) if s else None


def normalize(task):
    due = get_due_date(task)
    dl = get_deadline_date(task)
    pid = task.get("project_id", "")
    return {
        "id": task["id"],
        "content": task["content"],
        "priority": PRIORITY_MAP.get(task.get("priority", 1), "p4"),
        "project": PROJECT_NAMES.get(pid, f"Unknown ({pid})"),
        "project_id": pid,
        "due": due.isoformat() if due else None,
        "deadline": dl.isoformat() if dl else None,
    }


# Merge and deduplicate by task id (Call A takes precedence)
merged = {t["id"]: t for t in tasks_a}
for t in tasks_b:
    merged.setdefault(t["id"], t)

all_tasks = [normalize(t) for t in merged.values()]

overdue, today_tasks, tomorrow_tasks, deadline_only = [], [], [], []

for t in all_tasks:
    due = date.fromisoformat(t["due"]) if t["due"] else None
    dl = date.fromisoformat(t["deadline"]) if t["deadline"] else None

    placed = False
    if due is not None:
        if due < today:
            overdue.append(t)
            placed = True
        elif due == today:
            today_tasks.append(t)
            placed = True
        elif due == tomorrow:
            tomorrow_tasks.append(t)
            placed = True

    if not placed and dl is not None and today <= dl <= deadline_window_end:
        deadline_only.append(t)


def sort_key(t):
    return (t["priority"], t["content"].lower())


overdue.sort(key=sort_key)
today_tasks.sort(key=sort_key)
tomorrow_tasks.sort(key=sort_key)
deadline_only.sort(key=lambda t: (t["deadline"] or "", t["content"].lower()))

output = {
    "fetched_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "sections": {
        "overdue": overdue,
        "today": today_tasks,
        "tomorrow": tomorrow_tasks,
        "deadline_only": deadline_only,
    },
    "counts": {
        "overdue": len(overdue),
        "today": len(today_tasks),
        "tomorrow": len(tomorrow_tasks),
        "deadline_only": len(deadline_only),
    },
}

print(json.dumps(output, indent=2))
PYEOF
