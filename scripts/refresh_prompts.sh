#!/usr/bin/env bash
#
# refresh_prompts.sh — refresh the prompt body of each sub-skill from its
# upstream source (declared in the sub-skill file's YAML frontmatter).
#
# For each `sub-skills/*.md`:
#   1. Parse the frontmatter `upstream:` block (repo / branch / path).
#   2. If absent, skip — the file is locally-authored.
#   3. Fetch the upstream file via `gh api`.
#   4. Replace the BODY (everything after the closing `---`). Preserve
#      the frontmatter exactly.
#   5. Show a per-file diff.
#
# Requires `gh` CLI authenticated against an account with read access to
# the upstream repos.
#
# Usage:
#   ./refresh_prompts.sh               # show diffs, prompt before overwriting
#   ./refresh_prompts.sh --force       # overwrite without prompting
#   ./refresh_prompts.sh --dry-run     # show diffs only, never write
#   ./refresh_prompts.sh --only <id>   # only refresh sub-skills/<id>.md
#
# Exit codes:
#   0  success (or no changes)
#   1  missing dependency / auth failure / repo unreachable
#   2  user declined overwrite

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUB_SKILLS_DIR="$SKILL_DIR/sub-skills"

FORCE=0
DRY_RUN=0
ONLY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --only) ONLY="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,22p' "$0"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Dependency checks.
command -v gh >/dev/null 2>&1 || {
  echo "error: 'gh' (GitHub CLI) is required. Install: https://cli.github.com/" >&2
  exit 1
}
gh auth status >/dev/null 2>&1 || {
  echo "error: gh is not authenticated. Run: gh auth login" >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  echo "error: 'python3' is required to parse YAML frontmatter." >&2
  exit 1
}

# parse_frontmatter <file> → prints "repo|branch|path" or empty if no upstream
parse_frontmatter() {
  python3 - "$1" <<'PY'
import sys, re
p = sys.argv[1]
with open(p) as f:
    txt = f.read()
m = re.match(r'\A---\n(.*?)\n---\n', txt, re.DOTALL)
if not m:
    sys.exit(0)
fm = m.group(1)
# Tiny YAML reader: only supports the keys we care about.
def get_scalar(block, key):
    rx = re.compile(r'^\s*' + re.escape(key) + r':\s*(.+?)\s*$', re.MULTILINE)
    m = rx.search(block)
    if not m:
        return None
    val = m.group(1)
    # Strip quotes
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val
# Find the upstream: block (indented children up to next non-indented key)
m_up = re.search(r'^upstream:\s*$\n((?:[ \t]+.+\n?)+)', fm, re.MULTILINE)
if not m_up:
    sys.exit(0)
ub = m_up.group(1)
repo = get_scalar(ub, 'repo')
branch = get_scalar(ub, 'branch') or 'main'
path = get_scalar(ub, 'path')
if not repo or not path:
    sys.exit(0)
print(f"{repo}|{branch}|{path}")
PY
}

# split_file <file> → emits frontmatter (incl. fences) and body to stdout, separated by NUL
# We use a Python helper for safety.
extract_body_offset() {
  python3 - "$1" <<'PY'
import sys, re
p = sys.argv[1]
with open(p, 'rb') as f:
    data = f.read()
m = re.match(rb'\A---\n.*?\n---\n', data, re.DOTALL)
if not m:
    print(0)
else:
    print(m.end())
PY
}

echo "Refreshing sub-skill prompt bodies from upstream"
echo "Skill dir: $SKILL_DIR"
echo

if [[ ! -d "$SUB_SKILLS_DIR" ]]; then
  echo "error: $SUB_SKILLS_DIR does not exist" >&2
  exit 1
fi

shopt -s nullglob
files=("$SUB_SKILLS_DIR"/*.md)
shopt -u nullglob

if [[ ${#files[@]} -eq 0 ]]; then
  echo "warn: no sub-skill files found in $SUB_SKILLS_DIR" >&2
  exit 0
fi

changes=0
skipped_no_upstream=0

for f in "${files[@]}"; do
  bn="$(basename "$f")"
  # Skip README, dotfiles, underscore-prefixed
  case "$bn" in
    README.md|_*|.*) continue ;;
  esac
  if [[ -n "$ONLY" && "$bn" != "$ONLY.md" ]]; then
    continue
  fi

  meta="$(parse_frontmatter "$f" || true)"
  if [[ -z "$meta" ]]; then
    skipped_no_upstream=$((skipped_no_upstream + 1))
    [[ -n "$ONLY" ]] && echo "ℹ️  $bn — no upstream block, skipping"
    continue
  fi

  IFS='|' read -r repo branch path <<<"$meta"

  echo "── $bn  ($repo@$branch:$path)"

  tmp_body="$(mktemp)"
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_body'" EXIT

  if ! gh api "repos/$repo/contents/$path?ref=$branch" --jq '.content' \
      | base64 -d > "$tmp_body" 2>/dev/null; then
    echo "   ⚠️  could not fetch — skipping"
    rm -f "$tmp_body"
    trap - EXIT
    continue
  fi

  # Compute current body and compare.
  body_offset="$(extract_body_offset "$f")"
  if [[ "$body_offset" -eq 0 ]]; then
    echo "   ⚠️  $bn has no frontmatter — skipping (this script only refreshes the body)"
    rm -f "$tmp_body"
    trap - EXIT
    continue
  fi
  current_body="$(mktemp)"
  tail -c +$((body_offset + 1)) "$f" > "$current_body"

  if cmp -s "$tmp_body" "$current_body"; then
    echo "   ✓ up-to-date"
    rm -f "$tmp_body" "$current_body"
    trap - EXIT
    continue
  fi

  echo "   📝 body changed — diff:"
  diff -u "$current_body" "$tmp_body" | sed 's/^/      /' || true

  if [[ $DRY_RUN -eq 1 ]]; then
    rm -f "$tmp_body" "$current_body"
    trap - EXIT
    changes=$((changes + 1))
    continue
  fi

  if [[ $FORCE -eq 0 ]]; then
    read -r -p "   overwrite? [y/N] " ans
    if [[ ! "$ans" =~ ^[Yy]$ ]]; then
      echo "   → skipped"
      rm -f "$tmp_body" "$current_body"
      trap - EXIT
      continue
    fi
  fi

  # Reassemble: head -c <offset> of original (frontmatter + closing ---) + new body
  new_file="$(mktemp)"
  head -c "$body_offset" "$f" > "$new_file"
  cat "$tmp_body" >> "$new_file"
  mv "$new_file" "$f"
  echo "   → overwritten"

  rm -f "$tmp_body" "$current_body"
  trap - EXIT
  changes=$((changes + 1))
done

echo
if [[ $changes -eq 0 ]]; then
  echo "✅ All sub-skill prompts are up-to-date."
else
  echo "✅ Done. $changes file(s) had upstream changes."
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "   (dry-run — no files were written)"
  fi
fi
if [[ $skipped_no_upstream -gt 0 && -z "$ONLY" ]]; then
  echo "ℹ️  Skipped $skipped_no_upstream locally-authored file(s) without an upstream: block."
fi
