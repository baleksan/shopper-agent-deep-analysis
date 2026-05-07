#!/usr/bin/env bash
#
# attach_html_to_gus.sh — attach an HTML file to a GUS work item as a
# Salesforce File (ContentVersion + ContentDocumentLink).
#
# Usage:
#   attach_html_to_gus.sh <wi-id> <html-path> [<title>]
#
# <wi-id> is the ADM_Work__c Salesforce Id (15- or 18-char). Get it from
# the W-XXX work-item details after creation.
#
# Requires:
#   - `sf` CLI authenticated against the `gus` org alias
#     (test: `sf org display --target-org gus`)
#   - `jq`, `curl`, `base64`
#
# Exit codes:
#   0  success
#   1  bad args / missing dependency
#   2  ContentVersion create failed
#   3  ContentDocumentId lookup failed
#   4  ContentDocumentLink create failed

set -euo pipefail

WI_ID="${1:-}"
HTML_PATH="${2:-}"
TITLE="${3:-}"

if [[ -z "$WI_ID" || -z "$HTML_PATH" ]]; then
  sed -n '4,12p' "$0"
  exit 1
fi

if [[ -z "$TITLE" ]]; then
  TITLE="$(basename "$HTML_PATH" .html)"
fi

if [[ ! -f "$HTML_PATH" ]]; then
  echo "error: file not found: $HTML_PATH" >&2
  exit 1
fi

for cmd in sf jq curl base64; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "error: '$cmd' is required" >&2
    exit 1
  }
done

# Resolve auth + instance URL.
META=$(sf org display --target-org gus --json 2>/dev/null) || {
  echo "error: 'sf org display --target-org gus' failed. Run:" >&2
  echo "  sf org login web --instance-url https://gus.my.salesforce.com --alias gus" >&2
  exit 1
}
ACCESS_TOKEN=$(echo "$META" | jq -r '.result.accessToken // empty')
INSTANCE_URL=$(echo "$META" | jq -r '.result.instanceUrl // empty')
if [[ -z "$ACCESS_TOKEN" || -z "$INSTANCE_URL" ]]; then
  echo "error: could not resolve gus access token / instance URL" >&2
  exit 1
fi

PATH_ON_CLIENT="$(basename "$HTML_PATH")"

echo "→ uploading $HTML_PATH to GUS WI $WI_ID"
echo "  size: $(wc -c < "$HTML_PATH") bytes"

# Step A: create ContentVersion (the file blob).
B64=$(base64 -i "$HTML_PATH" | tr -d '\n')
CV_BODY=$(jq -n --arg t "$TITLE" --arg p "$PATH_ON_CLIENT" --arg d "$B64" \
  '{Title:$t, PathOnClient:$p, VersionData:$d}')

CV_RESPONSE=$(curl -sS -X POST "$INSTANCE_URL/services/data/v60.0/sobjects/ContentVersion" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CV_BODY")

CV_ID=$(echo "$CV_RESPONSE" | jq -r '.id // empty')
if [[ -z "$CV_ID" ]]; then
  echo "error: ContentVersion create failed:" >&2
  echo "$CV_RESPONSE" >&2
  exit 2
fi
echo "  ContentVersion Id: $CV_ID"

# Step B: resolve ContentDocumentId from the freshly-created ContentVersion.
CD_ID=$(sf data query --target-org gus --json \
  -q "SELECT ContentDocumentId FROM ContentVersion WHERE Id='$CV_ID'" \
  | jq -r '.result.records[0].ContentDocumentId // empty')
if [[ -z "$CD_ID" ]]; then
  echo "error: could not resolve ContentDocumentId for ContentVersion $CV_ID" >&2
  exit 3
fi
echo "  ContentDocumentId: $CD_ID"

# Step C: link the file to the work item.
LINK_RESULT=$(sf data create record --target-org gus \
  --sobject ContentDocumentLink \
  --values "ContentDocumentId='$CD_ID' LinkedEntityId='$WI_ID' ShareType='V' Visibility='AllUsers'" \
  --json)

if echo "$LINK_RESULT" | jq -e '.result.success == true' >/dev/null; then
  LINK_ID=$(echo "$LINK_RESULT" | jq -r '.result.id')
  echo
  echo "✅ Attached '$TITLE' to work item $WI_ID"
  echo "   ContentDocumentLink Id: $LINK_ID"
  echo "   File URL: $INSTANCE_URL/lightning/r/ContentDocument/$CD_ID/view"
else
  echo "error: ContentDocumentLink create failed:" >&2
  echo "$LINK_RESULT" >&2
  exit 4
fi
