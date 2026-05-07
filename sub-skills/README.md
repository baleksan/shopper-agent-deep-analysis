# Sub-skills

Each file in this directory is one **sub-skill** — a single named analysis
that the parent skill (`shopper-agent-obs-hub-analyze`) can run on a
session's Splunk logs.

**The skill auto-discovers every `*.md` file in this directory.** Drop a
new file in, and it shows up in the menu. No code change required, no
config update required.

## File contract

Each sub-skill is a markdown file with YAML frontmatter + prompt body:

```markdown
---
id: my-new-analysis              # required, unique, kebab-case
label: One-liner shown in menu   # required, ≤ ~70 chars
description: Slightly longer description for the menu's right column.  # required
output: markdown | json          # required — drives validation + rendering
order: 80                        # required — menu sort order (lower = higher)
upstream:                        # optional — refresh script source
  repo: baleksan/obs-hub
  branch: main
  path: skills/my_new_analysis.txt
---

<the prompt body — passed verbatim to the LLM as the system instruction>
```

### Required frontmatter keys

| Key | Type | Notes |
|---|---|---|
| `id` | string | Unique, kebab-case. Becomes the user-facing CLI argument and the menu reply value. |
| `label` | string | One-line label shown in the numbered menu. |
| `description` | string | Slightly longer "what does it do" for the menu / help. |
| `output` | `markdown` \| `json` | Tells the parent skill how to render the response. `json` means the prompt instructs the LLM to return strict JSON, and the parent skill will validate + retry once on parse failure. |
| `order` | integer | Sort order in the menu (ascending). Use 10/20/30/... so new entries can be slotted between existing ones. |

### Optional frontmatter keys

| Key | Type | Notes |
|---|---|---|
| `upstream.repo` | `<owner>/<repo>` | If set, `scripts/refresh_prompts.sh` will fetch from here. |
| `upstream.branch` | string | Default `main`. |
| `upstream.path` | string | Path to the source file in the upstream repo. The script replaces only the **body** of this file (frontmatter is preserved). |
| `requires_stage` | list of stages | If set, the sub-skill only appears when the user picked one of these stages (e.g. `[scrt2, e2e]` for an SCRT2-specific analysis). Default: shown for all stages. |
| `tags` | list of strings | Free-form tags; not used by the menu but useful for grouping later. |
| `html_eligible` | boolean | When `false`, the parent skill refuses to render this sub-skill's output as a shareable HTML report (Step 9). Default: `true`. Set to `false` for sub-skills that are only meaningful as raw chat output. |

## Naming

- Filename matches `id` (e.g. `id: anomaly` → `anomaly.md`).
- Use kebab-case for both filename and `id`.
- Keep the `id` short and memorable — users will type it.

## How the parent skill consumes these files

1. On every invocation, `SKILL.md` Step 3 lists all `*.md` files in this
   directory (excluding this `README.md`), parses frontmatter, sorts by
   `order`, and renders the menu — including the `description` text.
2. When the user picks one (by number, `id`, or label), the parent reads
   the **body** of that file (everything after the closing `---`) verbatim
   and uses it as the LLM system instruction.
3. The `output` field decides how to wrap the response (markdown passthrough
   vs. JSON validation + fenced rendering).

## Adding a new sub-skill

1. Create `<id>.md` in this directory using the template above.
2. (Optional) If the prompt comes from obs-hub, set `upstream:` so the
   refresh script keeps it in sync.
3. That's it. The skill picks it up on next invocation.

## Removing or hiding a sub-skill

- Delete the file → it disappears from the menu.
- Or rename with a leading `_` (e.g. `_archived-foo.md`) — the parent
  skill ignores files starting with `_` or `.`.
