#!/usr/bin/env bash
# Search Gmail and return enriched message list with headers.
# Args: --query <gmail_search_string> --max-results <n> (default: 40)
# Output: JSON array of {id, threadId, snippet, subject, from, date}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUERY=""
MAX_RESULTS=40

while [[ $# -gt 0 ]]; do
    case "$1" in
        --query)       QUERY="$2";       shift 2 ;;
        --max-results) MAX_RESULTS="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$QUERY" ]]; then
    echo "Error: --query is required" >&2
    exit 1
fi

ACCESS_TOKEN=$(bash "$SCRIPT_DIR/refresh-token.sh") || exit 1

QUERY="$QUERY" MAX_RESULTS="$MAX_RESULTS" ACCESS_TOKEN="$ACCESS_TOKEN" python3 << 'PYEOF'
import json, os, sys, urllib.request, urllib.parse, html, re

access_token = os.environ["ACCESS_TOKEN"]
query = os.environ["QUERY"]
max_results = int(os.environ["MAX_RESULTS"])
base = "https://gmail.googleapis.com/gmail/v1/users/me"

def gmail_get(path):
    req = urllib.request.Request(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

# Step 1: search for message IDs
params = urllib.parse.urlencode({"q": query, "maxResults": max_results})
search_result = gmail_get(f"/messages?{params}")
messages = search_result.get("messages", [])

if not messages:
    print("[]")
    sys.exit(0)

# Step 2: enrich each message with metadata headers + snippet
results = []
for msg in messages:
    mid = msg["id"]
    params = urllib.parse.urlencode(
        {"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
        doseq=True
    )
    detail = gmail_get(f"/messages/{mid}?{params}")
    headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
    snippet = html.unescape(detail.get("snippet", ""))
    snippet = re.sub(r"[\u034f\u200c\u200b\u00ad]+", "", snippet).strip()
    results.append({
        "id": detail["id"],
        "threadId": detail["threadId"],
        "snippet": snippet,
        "subject": headers.get("Subject", "(no subject)"),
        "from": headers.get("From", ""),
        "date": headers.get("Date", ""),
    })

print(json.dumps(results, indent=2))
PYEOF
