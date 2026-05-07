# shopper-agent-deep-analysis

A [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) skill that
runs predefined deep-analysis prompts (anomaly detection, latency measurement,
search-quality scoring, summarization, query analysis) over a Shopper Agent
session's Splunk logs, and produces shareable HTML reports with charts +
statistics.

```
sessionId + stage  ──►  shopper-agent-splunk-query  ──►  Splunk rows
                                                              │
                                                              ▼
                                          one of N predefined sub-skill prompts
                                                              │
                                          ┌───────────────────┴────────────────────┐
                                          ▼                                        ▼
                                  Markdown report in chat              Self-contained HTML report
                                  + Splunk Links Used                  with Chart.js graphs + stats
                                  + What's-next menu                   ready to share via Slack/email
```

The analysis prompts are sourced from
[baleksan/obs-hub](https://github.com/baleksan/obs-hub)'s `skills/` folder
(verbatim, point-in-time copies kept locally).

## Contents

| Path | Purpose |
|---|---|
| `SKILL.md` | The skill definition Claude reads (workflow, core rules, examples). |
| `commands/shopper-agent-obs-hub-analyze.md` | Slash-command argument parsing. |
| `config/defaults.yaml` | Stages, refresh sources, behavior knobs. |
| `sub-skills/` | One `<id>.md` per analysis. **Drop a new file in to register a new analysis** — no code or config edit required. |
| `sub-skills/README.md` | Frontmatter contract for new sub-skills. |
| `scripts/refresh_prompts.sh` | Pull latest prompt bodies from upstream sources. |
| `scripts/render_html.py` | Render an analysis as a shareable HTML report. |
| `templates/report.html.tmpl` | HTML template (Chart.js + marked.js from CDN). |

## Sub-skills shipped today

| ID | Output | What it does |
|---|---|---|
| `anomaly` | markdown | Errors, retry loops, latency spikes, stuck states |
| `anomaly-json` | json | Same as `anomaly` for downstream tooling |
| `latency` | markdown | Per-step duration table + slowdown analysis |
| `quality` | markdown | ESCI relevance + NDCG@5/@10 + follow-up grading |
| `quality-json` | json | Same as `quality` |
| `summary` | json | Chronological timeline + key turning points |
| `query-analysis` | markdown | Lightweight check of the user query |

## Prerequisites

- **Claude Code** ≥ 0.2 (skills must be supported)
- **AI Suite / DX Gateway MCP Adapter** with the `monitoring` profile so the
  `query_splunk` tool (typically `mcp__mcp-adaptor__query_splunk`) is available.
  See: <https://git.soma.salesforce.com/pages/c360-ai-tooling/c360-ai-tooling-docs/installation/>
- Sister skill **`shopper-agent-splunk-query`** installed at
  `~/.claude/skills/shopper-agent-splunk-query/`. This skill delegates all
  Splunk querying to it — there is no fallback.
- **`gh` CLI** (only required if you plan to run `scripts/refresh_prompts.sh`).
- **Python 3.9+** (only required if you plan to use HTML export).

The skill itself is read-only with respect to Splunk and obs-hub.

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

This is preferable if you want to track upstream + keep your own customizations
on a branch.

### Option C — manual copy (no git)

```bash
curl -L https://github.com/baleksan/shopper-agent-deep-analysis/archive/refs/heads/main.tar.gz \
  | tar -xz -C /tmp
mv /tmp/shopper-agent-deep-analysis-main ~/.claude/skills/shopper-agent-obs-hub-analyze
```

### Verify install

In Claude Code:
1. Run `/help` and check the skill registry — you should see
   `shopper-agent-obs-hub-analyze` listed.
2. Run `/shopper-agent-obs-hub-analyze` with no args — it should print short
   help.
3. Run with a `botSessionId` you have access to:
   ```
   /shopper-agent-obs-hub-analyze 019def...453b
   ```
   The skill should pull rows from Splunk and render the analysis menu.

If the skill says the `query_splunk` MCP tool isn't available, complete AI
Suite setup first.

## Configuration

Defaults live in [`config/defaults.yaml`](./config/defaults.yaml). To override
without editing the shipped file, create
`~/.claude/shopper-agent-obs-hub-analyze.yaml` and the skill will deep-merge
your file on top.

Common overrides:

```yaml
# Always show the menu, even if I named an analysis (paranoid mode):
behavior:
  always_show_menu_on_entry: true

# Different cache directory:
behavior:
  pulled_rows_cache_dir: "~/Documents/sa-traces"

# Pin a different upstream branch:
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
1. Resolves session, stage (default `core`), pulls rows from Splunk.
2. Renders the **analysis menu** of available sub-skills.
3. Waits for you to pick one (e.g. `3` for `latency`, or `all`).
4. Runs the chosen prompt, renders results in chat.
5. Always emits the **`Splunk Links Used`** section.
6. Always renders **`What's next?`** offering more analyses or HTML export.

### Run a specific analysis directly

```
/shopper-agent-obs-hub-analyze 019def...785 core anomaly
```

### Export a shareable HTML report

Append `+html` to any request:

```
/shopper-agent-obs-hub-analyze 019def...785 core anomaly +html
```

Or, after the chat-only run, pick `(c)` from the **What's next?** menu.

The HTML report is written to `.agents/artifacts/<sessionId>_<analysisId>.html`
— a self-contained file (~20–30 KB) you can attach to Slack or email.

### Stages

| Stage | What it pulls |
|---|---|
| `core` (default) | Core agent runtime b2usg logs |
| `scrt2` | SCRT2 chat-layer logs |
| `e2e` | Both layers, merged |
| `ux` | MIAW client UX rows |

## Adding a new sub-skill

The list of analyses is auto-discovered from `sub-skills/*.md` at runtime. To
add a new one:

1. Create `sub-skills/<my-new-id>.md` using the template in
   [`sub-skills/README.md`](./sub-skills/README.md):
   ```yaml
   ---
   id: my-new-analysis
   label: My new analysis
   description: One-line description shown in the menu.
   output: markdown    # or json
   order: 80
   ---
   <prompt body — passed verbatim to the LLM>
   ```
2. That's it. The next invocation picks it up.

Optional `upstream:` block keeps it sync'd with a public repo via
`scripts/refresh_prompts.sh`. Optional `html_eligible: false` opts out of HTML
export.

## Refreshing upstream prompts

```bash
# show diffs without writing
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh --dry-run

# overwrite without prompting
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh --force

# refresh just one sub-skill
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh --only latency
```

Only the **body** of each `sub-skills/*.md` is replaced — your local
frontmatter (id, label, description, order, etc.) is preserved.

## How it relates to sister skills

This skill works alongside two siblings in the Shopper Agent / Splunk family:

| Skill | Role |
|---|---|
| [`shopper-agent-splunk-query`](https://git.soma.salesforce.com/) | Pulls Splunk data E2E (SCRT2 + Core). **This skill depends on it.** |
| [`shopper-agent-trace-visualize`](https://git.soma.salesforce.com/) | Pushes a session into the local debug-UI tool at `localhost:8787`. |
| **`shopper-agent-deep-analysis`** *(this repo)* | Runs canned analytical prompts on those rows, with optional HTML export. |

## Architecture (one paragraph)

The skill is a **thin orchestrator**: it never writes SPL of its own. Instead
it (a) verifies the sister Splunk skill + MCP are available, (b) pulls rows
through that sister skill, (c) loads a sub-skill prompt body verbatim from
`sub-skills/<id>.md`, (d) calls the LLM with `(prompt body, splunk rows)`, and
(e) renders the result in chat — plus optionally invokes `render_html.py` to
produce a self-contained HTML file with deterministic charts (Chart.js) and
the LLM's analysis (rendered via `marked.js`). The list of available analyses
is **filesystem-driven** — drop a new markdown file into `sub-skills/` and it
shows up in the menu on next invocation.

## License

MIT — see [LICENSE](./LICENSE).

## Author

Boris Aleksandrovsky · [@baleksan](https://github.com/baleksan)
