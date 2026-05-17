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

RESPONSE=$(REFRESH_TOKEN="$REFRESH_TOKEN" CLIENT_ID="$CLIENT_ID" CLIENT_SECRET="$CLIENT_SECRET" python3 << 'PYEOF'
import json, os, urllib.request, urllib.parse

data = urllib.parse.urlencode({
    "grant_type": "refresh_token",
    "refresh_token": os.environ["REFRESH_TOKEN"],
    "client_id": os.environ["CLIENT_ID"],
    "client_secret": os.environ["CLIENT_SECRET"],
}).encode()

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
with urllib.request.urlopen(req) as resp:
    print(resp.read().decode())
PYEOF
) || {
    echo "Error: token refresh request failed" >&2
    exit 1
}

if ! echo "$RESPONSE" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    echo "Error: token endpoint returned non-JSON: ${RESPONSE:0:200}" >&2
    exit 1
fi

ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('access_token',''))")

if [[ -z "$ACCESS_TOKEN" ]]; then
    ERROR=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error_description', d.get('error', 'unknown')))" 2>/dev/null || echo "unknown")
    echo "Error: no access_token in response: $ERROR" >&2
    exit 1
fi

echo "$ACCESS_TOKEN"
