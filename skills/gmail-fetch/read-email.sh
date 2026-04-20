#!/usr/bin/env bash
# Fetch a single Gmail message.
# Args: --message-id <id> --depth snippet|full (default: full)
# Output: JSON {subject, from, date, snippet} or {subject, from, date, body}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MESSAGE_ID=""
DEPTH="full"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --message-id) MESSAGE_ID="$2"; shift 2 ;;
        --depth)      DEPTH="$2";      shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$MESSAGE_ID" ]]; then
    echo "Error: --message-id is required" >&2
    exit 1
fi

if [[ "$DEPTH" != "snippet" && "$DEPTH" != "full" ]]; then
    echo "Error: --depth must be 'snippet' or 'full'" >&2
    exit 1
fi

ACCESS_TOKEN=$(bash "$SCRIPT_DIR/refresh-token.sh") || exit 1

MESSAGE_ID="$MESSAGE_ID" DEPTH="$DEPTH" ACCESS_TOKEN="$ACCESS_TOKEN" python3 << 'PYEOF'
import json, os, sys, urllib.request, urllib.parse, base64, re
from html.parser import HTMLParser

access_token = os.environ["ACCESS_TOKEN"]
message_id = os.environ["MESSAGE_ID"]
depth = os.environ["DEPTH"]
base = "https://gmail.googleapis.com/gmail/v1/users/me"

def gmail_get(path):
    req = urllib.request.Request(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

if depth == "snippet":
    params = urllib.parse.urlencode(
        {"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
        doseq=True
    )
    detail = gmail_get(f"/messages/{message_id}?{params}")
    hdrs = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
    print(json.dumps({
        "subject": hdrs.get("Subject", "(no subject)"),
        "from": hdrs.get("From", ""),
        "date": hdrs.get("Date", ""),
        "snippet": detail.get("snippet", ""),
    }, indent=2))
    sys.exit(0)

# depth == "full"
detail = gmail_get(f"/messages/{message_id}?format=full")
hdrs = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}

def decode_body(data):
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

def find_parts(payload, mime_type):
    results = []
    if payload.get("mimeType") == mime_type:
        data = payload.get("body", {}).get("data", "")
        if data:
            results.append(decode_body(data))
    for part in payload.get("parts", []):
        results.extend(find_parts(part, mime_type))
    return results

class HtmlToMarkdown(HTMLParser):
    HEADING_MAP = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
    SKIP_TAGS = {"img", "style", "script", "head"}

    def __init__(self):
        super().__init__()
        self.result = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if tag in self.HEADING_MAP:
            self.result.append(f"\n{self.HEADING_MAP[tag]} ")
        elif tag == "li":
            self.result.append("\n- ")
        elif tag in ("p", "div", "tr"):
            self.result.append("\n")
        elif tag == "br":
            self.result.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
            self.result.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        self.result.append(data)

    def get_text(self):
        text = "".join(self.result)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

def html_to_markdown(html):
    parser = HtmlToMarkdown()
    parser.feed(html)
    return parser.get_text()

payload = detail.get("payload", {})
html_parts = find_parts(payload, "text/html")
plain_parts = find_parts(payload, "text/plain")

if html_parts:
    body = html_to_markdown(html_parts[0])
elif plain_parts:
    body = plain_parts[0].strip()
else:
    data = payload.get("body", {}).get("data", "")
    body = decode_body(data).strip() if data else ""

print(json.dumps({
    "subject": hdrs.get("Subject", "(no subject)"),
    "from": hdrs.get("From", ""),
    "date": hdrs.get("Date", ""),
    "body": body,
}, indent=2))
PYEOF
