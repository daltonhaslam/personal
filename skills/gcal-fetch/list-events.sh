#!/usr/bin/env bash
# List Google Calendar events for a given date.
# Args: --calendar-id <id> --date <YYYY-MM-DD> [--exclude-recurring]
# Output: JSON array of {title, start, end, location}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CALENDAR_ID=""
DATE=""
EXCLUDE_RECURRING=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --calendar-id)      CALENDAR_ID="$2"; shift 2 ;;
        --date)             DATE="$2";         shift 2 ;;
        --exclude-recurring) EXCLUDE_RECURRING=true; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$CALENDAR_ID" ]]; then
    echo "Error: --calendar-id is required" >&2; exit 1
fi
if [[ -z "$DATE" ]]; then
    echo "Error: --date is required (YYYY-MM-DD)" >&2; exit 1
fi

ACCESS_TOKEN=$(bash "$SCRIPT_DIR/../gmail-fetch/refresh-token.sh") || exit 1

CALENDAR_ID="$CALENDAR_ID" DATE="$DATE" EXCLUDE_RECURRING="$EXCLUDE_RECURRING" ACCESS_TOKEN="$ACCESS_TOKEN" python3 << 'PYEOF'
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timezone

access_token  = os.environ["ACCESS_TOKEN"]
calendar_id   = os.environ["CALENDAR_ID"]
date_str      = os.environ["DATE"]
exclude_recur = os.environ["EXCLUDE_RECURRING"] == "true"

# Build RFC3339 timeMin/timeMax in local timezone
local_tz = datetime.now(timezone.utc).astimezone().tzinfo
day_start = datetime.fromisoformat(date_str).replace(hour=0,  minute=0,  second=0,  tzinfo=local_tz)
day_end   = datetime.fromisoformat(date_str).replace(hour=23, minute=59, second=59, tzinfo=local_tz)
time_min  = day_start.isoformat()
time_max  = day_end.isoformat()

encoded_id = urllib.parse.quote(calendar_id, safe="")
params = urllib.parse.urlencode({
    "timeMin": time_min,
    "timeMax": time_max,
    "singleEvents": "true",
    "orderBy": "startTime",
})
url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events?{params}"

req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
with urllib.request.urlopen(req) as resp:
    raw = resp.read().decode()

try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print(f"Error: Calendar API returned non-JSON: {raw[:200]}", file=sys.stderr)
    sys.exit(1)

if "error" in data:
    msg = data["error"].get("message", json.dumps(data["error"]))
    print(f"Error: Calendar API error: {msg}", file=sys.stderr)
    sys.exit(1)

items = data.get("items", [])

if exclude_recur:
    items = [e for e in items if "recurringEventId" not in e]

results = []
for e in items:
    start_raw = e.get("start", {})
    end_raw   = e.get("end", {})

    if "dateTime" in start_raw:
        start = datetime.fromisoformat(start_raw["dateTime"]).strftime("%-I:%M %p")
        end   = datetime.fromisoformat(end_raw["dateTime"]).strftime("%-I:%M %p")
    else:
        start = "all-day"
        end   = "all-day"

    event = {
        "title": e.get("summary", "(no title)"),
        "start": start,
        "end":   end,
    }
    if e.get("location"):
        event["location"] = e["location"]

    results.append(event)

print(json.dumps(results, indent=2))
PYEOF
