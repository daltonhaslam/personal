#!/usr/bin/env bash
# Create a Google Calendar event.
# Args:
#   --calendar-id <id>       (required)
#   --title <string>         (required)
#   --date <YYYY-MM-DD>      (required if --all-day; else use --start/--end with full datetime)
#   --all-day                (flag — creates an all-day event on --date)
#   --start <YYYY-MM-DDTHH:MM>  (required if not --all-day)
#   --end   <YYYY-MM-DDTHH:MM>  (required if not --all-day)
#   --location <string>      (optional)
#   --description <string>   (optional)
# Output: JSON {id, htmlLink, summary, start, end} on success; {"error": "..."} on failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CALENDAR_ID=""
TITLE=""
DATE=""
ALL_DAY=false
START=""
END=""
LOCATION=""
DESCRIPTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --calendar-id) CALENDAR_ID="$2"; shift 2 ;;
        --title)       TITLE="$2";       shift 2 ;;
        --date)        DATE="$2";        shift 2 ;;
        --all-day)     ALL_DAY=true;     shift ;;
        --start)       START="$2";       shift 2 ;;
        --end)         END="$2";         shift 2 ;;
        --location)    LOCATION="$2";    shift 2 ;;
        --description) DESCRIPTION="$2"; shift 2 ;;
        *) echo "{\"error\": \"Unknown argument: $1\"}" >&2; exit 1 ;;
    esac
done

if [[ -z "$CALENDAR_ID" ]]; then echo '{"error": "--calendar-id required"}' >&2; exit 1; fi
if [[ -z "$TITLE" ]]; then echo '{"error": "--title required"}' >&2; exit 1; fi
if [[ "$ALL_DAY" == "true" ]]; then
    if [[ -z "$DATE" ]]; then echo '{"error": "--date required when --all-day"}' >&2; exit 1; fi
else
    if [[ -z "$START" || -z "$END" ]]; then
        echo '{"error": "--start and --end required when not --all-day"}' >&2; exit 1;
    fi
fi

ACCESS_TOKEN=$(bash "$SCRIPT_DIR/../gmail-fetch/refresh-token.sh") || exit 1

CALENDAR_ID="$CALENDAR_ID" TITLE="$TITLE" DATE="$DATE" ALL_DAY="$ALL_DAY" \
START="$START" END="$END" LOCATION="$LOCATION" DESCRIPTION="$DESCRIPTION" \
ACCESS_TOKEN="$ACCESS_TOKEN" python3 << 'PYEOF'
import json, os, sys, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta

access_token = os.environ["ACCESS_TOKEN"]
calendar_id  = os.environ["CALENDAR_ID"]
title        = os.environ["TITLE"]
all_day      = os.environ["ALL_DAY"] == "true"
date_str     = os.environ.get("DATE", "")
start_str    = os.environ.get("START", "")
end_str      = os.environ.get("END", "")
location     = os.environ.get("LOCATION", "")
description  = os.environ.get("DESCRIPTION", "")

if all_day:
    start_date = datetime.fromisoformat(date_str).date()
    body = {
        "summary": title,
        "start": {"date": start_date.isoformat()},
        "end":   {"date": (start_date + timedelta(days=1)).isoformat()},
    }
else:
    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    start_dt = datetime.fromisoformat(start_str).replace(tzinfo=local_tz)
    end_dt   = datetime.fromisoformat(end_str).replace(tzinfo=local_tz)
    body = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat()},
        "end":   {"dateTime": end_dt.isoformat()},
    }
if location:
    body["location"] = location
if description:
    body["description"] = description

encoded_id = urllib.parse.quote(calendar_id, safe="")
url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events"
data = json.dumps(body).encode()
req = urllib.request.Request(
    url, data=data, method="POST",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    },
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    body_err = e.read().decode()
    print(f'{{"error": "Calendar API HTTP {e.code}: {body_err[:200]}"}}', file=sys.stderr)
    sys.exit(1)

print(json.dumps({
    "id": result.get("id", ""),
    "htmlLink": result.get("htmlLink", ""),
    "summary": result.get("summary", ""),
    "start": result.get("start", {}),
    "end": result.get("end", {}),
}, indent=2))
PYEOF
