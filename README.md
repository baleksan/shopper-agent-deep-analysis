# shopper-agent-deep-analysis

A [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) skill that
runs predefined deep-analysis prompts (anomaly detection, latency, search
quality, summary, prioritized improvements, query analysis) over a Shopper
Agent session's Splunk logs, and ships shareable HTML reports + GUS work
items as one-click follow-ups.

```
sessionId + stage  ──►  shopper-agent-splunk-query  ──►  Splunk rows
                                                              │
                                                              ▼
                                          one of N predefined sub-skill prompts
                                                              │
                ┌─────────────────────┬───────────────────────┴────────────────────┐
                ▼                     ▼                                            ▼
         Markdown in chat   Self-contained HTML report (Chart.js + stats)   GUS WI + HTML attached
         + Splunk Links     auto-opened in default browser                  filed via sfcli:gus
         + What's-next      shareable on Slack/email                        + Slack DM on long ops
         + Timing
```

The base analysis prompts come from
[`baleksan/obs-hub`](https://github.com/baleksan/obs-hub)'s `skills/` folder
(verbatim, point-in-time copies kept locally and refreshable on demand).
Locally-authored sub-skills (`summary`, `suggested-improvements`) live
alongside.

## Sub-skills shipped today

All sub-skills produce markdown. All can be exported as HTML, attached to a
GUS work item, or both. They are auto-discovered from `sub-skills/*.md` at
runtime — drop a new file in to register a new analysis.

| ID | What it does |
|---|---|
| `summary` | Plain-English summary with sub-headings. Single session OR interval (e.g. all sessions for a customer over a day). |
| `anomaly` | Errors, retry loops, latency spikes, stuck states. |
| `latency` | Per-step duration table, slowdowns, root causes. |
| `suggested-improvements` | Synthesizes findings across aspects into a prioritized **P0/P1/P2 backlog framed as experiments** (hypothesis, single variable, primary + guardrail metrics, sample size, exit criteria, rollback). |
| `quality` | ESCI relevance scoring + NDCG@5/@10 + follow-up grading. |
| `query-analysis` | Lightweight check of the user's query. |

## Contents

| Path | Purpose |
|---|---|
| `SKILL.md` | The skill definition Claude reads (workflow, core rules, examples). |
| `commands/shopper-agent-obs-hub-analyze.md` | Slash-command argument parsing. |
| `config/defaults.yaml` | Stages, refresh sources, behavior knobs. |
| `sub-skills/` | One `<id>.md` per analysis. Filesystem is source of truth. |
| `sub-skills/README.md` | Frontmatter contract for new sub-skills. |
| `scripts/refresh_prompts.sh` | Refresh sub-skill prompt bodies from upstream (per-file `upstream:` frontmatter). |
| `scripts/render_html.py` | Render an analysis as a self-contained HTML report (charts via Chart.js, prose via marked.js, both from CDN). |
| `scripts/project_rows.py` | Project cached Splunk rows down to a per-sub-skill view. ~300x reduction → ~3x LLM speedup. |
| `scripts/attach_html_to_gus.sh` | Upload an HTML report to a GUS work item as a Salesforce File. |
| `templates/report.html.tmpl` | HTML template (collapsible sections, expand/collapse all, charts). |

## Prerequisites

- **Claude Code** ≥ 0.2 (skills must be supported)
- **AI Suite / DX Gateway MCP Adapter** with the `monitoring` profile so the
  `query_splunk` tool (typically `mcp__mcp-adaptor__query_splunk`) is available.
  See: <https://git.soma.salesforce.com/pages/c360-ai-tooling/c360-ai-tooling-docs/installation/>
- Sister skill **`shopper-agent-splunk-query`** installed at
  `~/.claude/skills/shopper-agent-splunk-query/`. This skill delegates all
  Splunk querying to it — there is no fallback.
- **`sfcli:gus`** skill (only required if you plan to file GUS work items via
  `+gus`). It handles auth, sprint resolution, validation-rule fields, and
  honors the user's `MEMORY.md` GUS template.
- **Slack MCP** (only required for long-running-op DM notifications; gracefully
  skipped if unavailable).
- **`gh` CLI** (only required for `scripts/refresh_prompts.sh`).
- **Python 3.9+** for HTML render + row projection.
- **`sf` CLI + `jq`** (only required for `scripts/attach_html_to_gus.sh`).

The skill itself is read-only with respect to Splunk and the obs-hub repo.
Local writes are limited to `.agents/artifacts/`.

## Installation

### Option A — clone directly into `~/.claude/skills/` (simplest)

```bash
git clone https://github.com/baleksan/shopper-agent-deep-analysis.git \
  ~/.claude/skills/shopper-agent-obs-hub-analyze
```

The directory name **must** be `shopper-agent-obs-hub-analyze` — that's the
skill's `name` field. Restart Claude Code and the skill appears in the
registry.

### Option B — clone elsewhere and symlink

```bash
git clone https://github.com/baleksan/shopper-agent-deep-analysis.git ~/dev/shopper-agent-deep-analysis
ln -s ~/dev/shopper-agent-deep-analysis ~/.claude/skills/shopper-agent-obs-hub-analyze
```

Preferable if you want to track upstream + keep your own customizations on a
branch.

### Option C — manual copy (no git)

```bash
curl -L https://github.com/baleksan/shopper-agent-deep-analysis/archive/refs/heads/main.tar.gz \
  | tar -xz -C /tmp
mv /tmp/shopper-agent-deep-analysis-main ~/.claude/skills/shopper-agent-obs-hub-analyze
```

### Verify install

In Claude Code:

1. Run `/help` and look for `shopper-agent-obs-hub-analyze` in the registry.
2. Run `/shopper-agent-obs-hub-analyze` with no args — it should print short
   help.
3. Run with a `botSessionId` you have access to:
   ```
   /shopper-agent-obs-hub-analyze 019def...453b
   ```
   The skill should pull rows from Splunk and render the analysis menu.

If it says the `query_splunk` MCP tool isn't available, complete AI Suite
setup first (`GW_PROFILE=monitoring`).

## Configuration

Defaults live in [`config/defaults.yaml`](./config/defaults.yaml). To override
without editing the shipped file, create
`~/.claude/shopper-agent-obs-hub-analyze.yaml` and the skill will deep-merge
your file on top.

Common overrides:

```yaml
behavior:
  always_show_menu_on_entry: true       # paranoid mode
  pulled_rows_cache_dir: "~/Documents/sa-traces"
  offer_html_export_in_whats_next: true
  always_show_whats_next: true

refresh_defaults:
  repo: baleksan/obs-hub
  branch: my-experiments
```

## Quick start

### Default (chat-only markdown)

```
/shopper-agent-obs-hub-analyze 019def8d-3168-709e-98ec-8a7d3a202785
```

The skill:

1. Verifies prereqs and enumerates sub-skills.
2. Resolves session, stage (default `core`), pulls rows from Splunk (or
   reuses the cache).
3. Renders the **analysis menu**.
4. Waits for you to pick one (e.g. `3` for `latency`, or `all`).
5. Projects rows per the sub-skill's `projection:` tags
   (≈300x size reduction).
6. Calls the LLM with the projected input.
7. Renders the result in chat with **collapsible `<details>` sections**.
8. Always emits **`Splunk Links Used`** + **`Timing`** + **`What's next?`**.

### Run a specific analysis directly

```
/shopper-agent-obs-hub-analyze 019def...785 core anomaly
```

### Export a shareable HTML report (`+html`)

Append `+html` (or "shareable" / "share with X") to any request:

```
/shopper-agent-obs-hub-analyze 019def...785 core anomaly +html
```

Or, after the chat-only run, pick **(c)** from the **What's next?** menu.

The HTML report is written to `.agents/artifacts/<sessionId>_<analysisId>.html`
and **auto-opened in your default browser** (`--no-open` to suppress). It's a
self-contained file (~25–35 KB) with:

- 6 stat cards (rows, distinct turns, unique ops, wall-clock, failures, max latency)
- 4 Chart.js graphs (operations, latency-per-op, timeline, status)
- A full operations table
- The analysis prose (rendered via marked.js) with collapsible H2/H3 subsections
- An "Expand all / Collapse all" toggle in the header

### File a GUS work item (`+gus`)

Append `+gus` (or "file in gus" / "create wi") to any request:

```
/shopper-agent-obs-hub-analyze 019def...785 core anomaly +gus
```

Or pick **(d)** from the **What's next?** menu. The skill will:

1. Auto-render the HTML if it isn't already on disk.
2. Ask for **team name** (required) and **theme** (optional).
3. Show a scope preview, then a `sfcli:gus` write preview (two confirmations).
4. **One WI per analysis output.** For `suggested-improvements` that means
   the entire backlog goes into a single WI; the experiment cards live in
   the attached HTML.
5. Embed the analysis output (Problem / Why / Evidence / inline prose) in
   `Details__c` with the Splunk URL.
6. Attach the HTML report as a Salesforce File via
   `scripts/attach_html_to_gus.sh`.

CC-Chatty team gets your `MEMORY.md` defaults (assignee, product tag, sprint,
QA, PO, validation-rule fields). Other teams get a fresh resolution from
`sfcli:gus` with a callout that your defaults don't apply.

### Slack DM on long operations

Operations exceeding **30s wall-clock** trigger a self-DM via Slack with the
report link, headline finding, and a timing breakdown by stage (prep / splunk
/ llm / render / gus / total). Link choice:

- If `+gus` was used, share the **GUS Salesforce File URL** (clickable from
  Slack web, mobile, anywhere).
- Otherwise, share the `file://` path inside a code-fenced block with a note
  that Slack security blocks `file://` URLs from opening directly — paste
  into a browser address bar.

DMs are skipped under 30s, when Slack is unavailable, or if you ask for "no
slack" / "quiet".

### Stages

| Stage | What it pulls |
|---|---|
| `core` (default) | Core agent runtime b2usg logs |
| `scrt2` | SCRT2 chat-layer logs |
| `e2e` | Both layers, merged |
| `ux` | MIAW client UX rows |

### Input modes

| Mode | Trigger | Sub-skills supported |
|---|---|---|
| **Single session** | sessionId or conversationId | All 6 |
| **Interval** | "summarize SharkNinja for today" / "what happened for Funko in last 6h" | `summary` only — others assume single-session semantics |

## Adding a new sub-skill

The list is auto-discovered from `sub-skills/*.md` at runtime. Drop a file in
following the contract in [`sub-skills/README.md`](./sub-skills/README.md):

```yaml
---
id: my-new-analysis
label: My new analysis
description: One-line description shown in the menu.
output: markdown
order: 80
projection: time,op,status,query    # required for performance
upstream:                           # optional — for refresh script
  repo: baleksan/obs-hub
  branch: main
  path: skills/my_new_analysis.txt
html_eligible: true                 # default; set false to opt out of HTML export
---
<prompt body — passed verbatim to the LLM>
```

Pick a minimal `projection:` tag set so LLM input stays small. Available
tags: `time`, `op`, `status`, `requestId`, `latency`, `query`, `product_titles`,
`product_full`, `followup_meta`, `scapi_meta`, `cache`, `site`, `errors_context`.

## Refreshing upstream prompts

```bash
# show diffs without writing
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh --dry-run

# overwrite without prompting
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh --force

# refresh just one sub-skill
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh --only latency
```

Only the **body** of each `sub-skills/*.md` is replaced — the local
frontmatter (id, label, description, projection, etc.) is preserved.
Sub-skills without an `upstream:` block are skipped (they are local).

## Performance / accuracy notes

- **Input projection** (mandatory): `scripts/project_rows.py` slims the cached
  Splunk rows per sub-skill before the LLM call. Real measurement on a 16-row,
  3-turn session: 691 KB → 2–4 KB (~300x). LLM stage went from 82s to 31s
  (2.7x) on the latency analysis with **zero accuracy regression** —
  validated against verbose-prompt baseline by diffing every numeric and
  field-name claim.

- **Output token economy** (always applied): the LLM is instructed to
  produce engineer-targeted output — fragments OK, bullets over prose,
  imperatives for recommendations, no hedges, no transition fluff. Real
  measurement: −38% to −69% words across the 4 measured sub-skills (54%
  avg) with all numeric claims preserved.

- **Stage timings** (always tracked): every action surfaces a `prep / splunk /
  llm / render / gus / total` breakdown in chat and in any Slack DM.

- **Prompt caching** + **streaming** (when harness exposes them): structure
  the LLM call so the sub-skill body is a cacheable system block; stream
  partial output to the user. No-ops where the harness doesn't support
  them.

## How it relates to sister skills

| Skill | Role |
|---|---|
| [`shopper-agent-splunk-query`](https://git.soma.salesforce.com/) | Pulls Splunk data E2E (SCRT2 + Core). **This skill depends on it.** |
| [`shopper-agent-trace-visualize`](https://git.soma.salesforce.com/) | Pushes a session into the local debug-UI tool at `localhost:8787`. |
| [`sfcli:gus`](https://git.soma.salesforce.com/) | Used by `+gus` to file work items with team defaults + sprint resolution. |
| **`shopper-agent-deep-analysis`** *(this repo)* | Runs canned analytical prompts on those rows, with HTML / GUS / Slack follow-ups. |

## Architecture (one paragraph)

The skill is a **thin orchestrator**: it never writes SPL. It (a) verifies
the sister Splunk skill + MCP are available, (b) pulls rows through the
sister skill (or reuses the per-session cache), (c) projects the rows down
to the per-sub-skill view, (d) loads the sub-skill prompt body verbatim
from `sub-skills/<id>.md` and appends the output-rules block, (e) calls
the LLM with `(prompt body, projected rows)`, and (f) renders the result
in chat — plus optionally invokes `render_html.py` for a self-contained
HTML report (auto-opened), files a GUS WI via `sfcli:gus` with the HTML
attached, and DMs you on Slack for long ops. The list of available
analyses is **filesystem-driven** — drop a markdown file into
`sub-skills/` and it shows up in the menu on next invocation.

## License

MIT — see [LICENSE](./LICENSE).

## Author

Boris Aleksandrovsky · [@baleksan](https://github.com/baleksan)
