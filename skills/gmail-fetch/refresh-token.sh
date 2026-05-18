#!/usr/bin/env bash
# Exchange stored Gmail refresh token for a short-lived access token.
# Args: [--account dalton|maggie]   (default: dalton)
# Output: access token to stdout. Errors to stderr.

set -euo pipefail

ACCOUNT="dalton"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --account) ACCOUNT="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

case "$ACCOUNT" in
    dalton)
        REFRESH_KEY="GMAIL_REFRESH_TOKEN"
        ;;
    maggie)
        REFRESH_KEY="GMAIL_REFRESH_TOKEN_MAGGIE"
        ;;
    *)
        echo "Error: --account must be 'dalton' or 'maggie' (got '$ACCOUNT')" >&2
        exit 1
        ;;
esac

REFRESH_TOKEN=$(security find-generic-password -s "$REFRESH_KEY" -w 2>/dev/null) || {
    echo "Error: $REFRESH_KEY not found in Keychain" >&2
    exit 1
}
CLIENT_ID=$(security find-generic-password -s GMAIL_CLIENT_ID -w 2>/dev/null) || {
    echo "Error: GMAIL_CLIENT_ID not found in Keychain" >&2
    exit 1
}
CLIENT_SECRET=$(security find-generic-password -s GMAIL_CLIENT_SECRET -w 2>/dev/null) || {
    echo "Error: GMAIL_CLIENT_SECRET not found in Keychain" >&2
    exit 1
}

RESULT=$(REFRESH_TOKEN="$REFRESH_TOKEN" CLIENT_ID="$CLIENT_ID" CLIENT_SECRET="$CLIENT_SECRET" python3 << 'PYEOF'
import json, os, sys, urllib.request, urllib.parse

data = urllib.parse.urlencode({
    "grant_type": "refresh_token",
    "refresh_token": os.environ["REFRESH_TOKEN"],
    "client_id": os.environ["CLIENT_ID"],
    "client_secret": os.environ["CLIENT_SECRET"],
}).encode()

try:
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode()
except Exception as e:
    print(f"ERR\trequest failed: {e}")
    sys.exit(0)

try:
    payload = json.loads(body)
except ValueError:
    print(f"ERR\tnon-JSON response: {body[:200]}")
    sys.exit(0)

token = payload.get("access_token")
if not token:
    err = payload.get("error_description") or payload.get("error") or "unknown"
    print(f"ERR\tno access_token: {err}")
    sys.exit(0)

print(f"OK\t{token}")
PYEOF
)

case "$RESULT" in
    OK$'\t'*)  echo "${RESULT#OK$'\t'}" ;;
    ERR$'\t'*) echo "Error: ${RESULT#ERR$'\t'}" >&2; exit 1 ;;
    *)         echo "Error: unexpected token-helper output" >&2; exit 1 ;;
esac
