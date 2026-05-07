---
name: shopper-agent-obs-hub-analyze
description: |
  Run a predefined obs-hub analysis (anomaly detection, latency measurement,
  search-quality assessment, summarization, query analysis) over the Splunk
  results for a single Shopper Agent session. Given a `sessionId` (and optional
  `stage`, default `core`), the skill presents a menu of analyses sourced from
  the obs-hub project (https://github.com/baleksan/obs-hub), pulls the matching
  Splunk logs via the sister `shopper-agent-splunk-query` skill, and then
  applies the chosen analysis prompt to those logs.

  Use whenever the user asks to "analyze", "run anomaly detection on",
  "measure latency for", "score search quality of", "summarize", or "deep
  analyze" a session — and you have a sessionId (botSessionId or
  conversationId) to work from. Trigger phrases include: "obs-hub",
  "anomaly detection", "search quality assessment", "ESCI", "NDCG",
  "latency breakdown", "deep analysis on session".
compatibility: |
  Requires the sister skill `shopper-agent-splunk-query` to be installed and
  working (it provides the Splunk pull). That in turn requires AI Suite's
  DX Gateway MCP Adapter with the "monitoring" profile and the
  `query_splunk` tool (typically `mcp__mcp-adaptor__query_splunk`).

  If the sister skill is missing or its MCP isn't available, stop and tell
  the user — don't try to query Splunk directly.
---

# Shopper Agent ↔ Obs-Hub Analyze

This skill is the analysis half of the Shopper Agent / Splunk family. The
sister skills handle data ingestion; this one applies a **predefined
analytical prompt** (from [`baleksan/obs-hub`](https://github.com/baleksan/obs-hub))
to those raw logs to produce a structured report.

```
sessionId + stage  ─►  shopper-agent-splunk-query  ─►  Splunk rows  ─►  obs-hub prompt  ─►  structured report
                       (sister skill, this skill           (this skill)              (this skill)
                        delegates the data pull)
```

## 📏 Conciseness (always apply)

- **Be tight, not exhaustive.** Reports are read in chat — every section
  earns its place. If a sub-skill asks for "3-8 bullets", give 3-5; aim
  for the lower bound.
- **One example per claim, not three.** When you've already shown
  evidence in §2, do not re-list the same numbers in §3 / §4 / §5.
  Reference back instead.
- **Drop section headings that have nothing in them.** If "Missing or
  Skipped Steps" has no real findings, write a one-liner ("All expected
  steps observed") instead of a multi-row table of "✅ correctly absent".
- **Tables over paragraphs**, but only when there are ≥ 3 rows worth
  showing. A 1-row "table" is just a sentence in disguise.
- **Skip the meta-commentary**: don't narrate what you're about to do
  ("Now I'll examine…"), don't restate the user's question, don't
  re-introduce the session metadata that's already in the header.
- **No verbose hedging.** Replace "It's worth noting that..." / "One
  thing to consider..." with the bare statement.
- **Soft cap**: aim for ≤ ~600 words of prose+evidence in the analysis
  body for a single sub-skill on a small (< 50-row) session. JSON
  outputs are exempt from word counts but still avoid repeated content.
- **The "What's next?" menu is the exception** — it's a state display,
  always rendered fully.

## 🪗 Collapsible chat sections (always apply for analyses)

Chat reports go through a markdown renderer that supports HTML
pass-through (AI Suite Electron app, Claude.ai web, GitHub-flavored
renderers, etc.). Use `<details><summary>` blocks so the user can fold
sections inline — same UX as the HTML export.

### Convention

| Section | Wrap? | Default state |
|---|---|---|
| Top header table (sessionId, stage, time range, row count, …) | ❌ no wrap | always visible |
| First H2 of the analysis body (the "Summary" / "Step Duration Table" / "Executive Summary") | ✅ wrap | `<details open>` |
| All other H2 sections of the analysis body (Evidence, Impact, Root Causes, Recommendations, etc.) | ✅ wrap | `<details>` (collapsed by default) |
| `## 🔗 Splunk Links Used` | ✅ wrap | `<details>` (collapsed) |
| `## ▶️ What's next?` | ❌ no wrap — never collapse | always visible |

Rationale: with most sections collapsed by default, the chat surface
shows ≈ 5–8 lines of executive content + the summary block, with
everything else one click away. This is the chat-side equivalent of the
HTML report's "expand/collapse all" buttons.

### Format

````markdown
<details open>
<summary><strong>1) Anomaly Summary</strong></summary>

- 🔴 SCAPI dominates every search turn at ~3.6–4.0 s
- 🟠 …
- 🟢 …

</details>

<details>
<summary><strong>2) Evidence</strong></summary>

| Anomaly | Snippet |
|---|---|
| … | … |

</details>
````

### Rules

- **Always wrap the heading text in `<strong>`** inside `<summary>` so it
  retains visual weight when collapsed.
- **Always leave a blank line** between `</summary>` and the section
  content — many renderers won't parse the markdown body otherwise.
- **Always leave a blank line** before `</details>` for the same reason.
- **Don't wrap H3 / smaller subsections** in chat (too noisy at chat scale).
  In the HTML report, H3s are wrapped automatically — keep chat tighter.
- **Keep the header table inline** (not wrapped) — it's at-a-glance
  metadata the user must see.
- **Keep "What's next?" inline** (not wrapped) — it's the interactive
  next step.
- **JSON output sub-skills** (`*_json.txt`) wrap the entire JSON block in
  a single `<details>` named "JSON output" — the schema is rigid and not
  meant to be browsed section-by-section.

### Worked example (snippet for the `anomaly` sub-skill)

````markdown
# 🔬 Obs-Hub Analysis — `<sessionId>`

| Field | Value |
|---|---|
| … | … |

---

<details open>
<summary><strong>1) Anomaly Summary</strong></summary>

- 🔴 SCAPI hybrid call dominates every search turn at ~3.6–4.0 s
- 🟠 `B2CProductSearchAction` is double-logged …
- 🟢 No errors, retries, or stalls

</details>

<details>
<summary><strong>2) Evidence</strong></summary>

| Anomaly | Snippet |
|---|---|
| SCAPI hotspot | `HybridCallSCAPI=3957` |

</details>

<details>
<summary><strong>3) Likely Impact</strong></summary>

Each turn lands at ~5–6 seconds, dominated by SCAPI. …

</details>

<details>
<summary><strong>🔗 Splunk Links Used</strong></summary>

- **Core — full session (preprod):** …

</details>

## ▶️ What's next?

(menu — never wrapped)
````

## ⛳ Core rules (always apply)

These behaviors are **mandatory** on every invocation. Do not skip them,
do not collapse them into a single step, do not silently default.

1. **Menu on entry.** If the user did NOT explicitly name a sub-skill (one
   of the analysis IDs from the menu, or `all`), pause and render the
   numbered menu defined in [Step 3](#step-3--render-the-analysis-menu-mandatory-when-no-analysis-was-named).
   Wait for their pick. Don't assume `default_analysis` — even if it's set
   in config, still show the menu unless the user said "skip the menu" /
   "use my default".
2. **Splunk links every time.** Every report (success or failure)
   ends with a `## 🔗 Splunk Links Used` section listing the **exact**
   queries you ran to produce the data, as clickable web URLs. See
   [Step 7](#step-7--always-output-the-splunk-links-used-mandatory).
3. **What's next on exit.** After every successful analysis output, render
   the [Step 8](#step-8--ask-whats-next-mandatory) follow-up menu offering
   `(a)` continue with another sub-skill on the same data, `(b)` start
   a fresh analysis on a different session, or `(c)` export the most
   recent analysis as a shareable HTML report. Wait for input.
4. **HTML export is opt-in but always offered.** Every report in chat is
   markdown by default. The user can request an HTML export by including
   `+html` / "html report" / "shareable" in the request, or by picking
   option `(c)` in the "what's next" menu. See
   [Step 9](#step-9--export-html-report-on-request).

If you skip any of these, you have not completed the skill correctly.

## When to use this skill vs siblings

| User intent | Use |
|---|---|
| "Trace conversation X end-to-end" | `shopper-agent-splunk-query` |
| "Show me the trace in the debug UI" | `shopper-agent-trace-visualize` |
| **"Run anomaly detection on session X"** | **this skill** |
| **"Score search quality for session X"** | **this skill** |
| **"Measure latency for session X"** | **this skill** |
| **"Summarize session X as JSON"** | **this skill** |
| Free-form Splunk URL or SPL | `splunk` |

If the user just wants to *see* the events, route to `shopper-agent-splunk-query`.
This skill is for **interpretive analysis on top of those events** using one of
the canned obs-hub prompts.

## The sub-skills (auto-discovered)

Sub-skills live as individual markdown files in `sub-skills/`. **The skill
auto-discovers every `*.md` file there.** No code edits, no config edits.
Drop a new file in, and it shows up in the menu on next invocation.

Each sub-skill file has YAML frontmatter (metadata) and a prompt body. The
frontmatter contract is documented in [`sub-skills/README.md`](sub-skills/README.md).
Required keys: `id`, `label`, `description`, `output` (markdown|json),
`order`. Optional: `upstream:` (for refresh), `requires_stage:`, `tags:`.

### How to enumerate sub-skills

At the start of any invocation that needs the menu, do this:

1. List `sub-skills/*.md`.
2. **Skip** files matching `README.md`, `_*.md`, or `.*.md`.
3. For each remaining file, read the frontmatter into a dict.
4. Validate required keys (`id`, `label`, `description`, `output`, `order`).
   If a file fails validation, warn the user and skip it — don't crash.
5. Sort by `order` ascending, then `id` alphabetically as tiebreaker.
6. Respect `requires_stage` if set: hide sub-skills whose `requires_stage`
   list does not include the current stage.

This list is the source of truth for:
- The Step 3 menu shown on entry.
- The Step 8 "What's next?" menu shown after results.
- The slash command's argument validation (which IDs are valid).
- The `all` / `all-remaining` shortcuts.

### Loading a sub-skill prompt

When the user picks a sub-skill `<id>`:
1. Open `sub-skills/<id>.md`.
2. Skip the frontmatter (everything from the opening `---` to the next `---`).
3. Take the **body** verbatim and pass it to the LLM as the system /
   instruction prompt, alongside the Splunk rows. Do not paraphrase, do
   not summarize, do not inject extra context above it.

### Custom requests

If the user asks for an analysis not present in `sub-skills/` (e.g. "cost
analysis"), tell them which IDs are available, and offer to either:
- Pass through their custom instruction as a one-off prompt (no file
  written), or
- Help them author a new sub-skill file (point them at
  `sub-skills/README.md`).

## Configuration

Resolution order (highest wins):

1. Per-query flags from the user.
2. `~/.claude/shopper-agent-obs-hub-analyze.yaml` (user override — optional).
3. `config/defaults.yaml` (ships with the skill).

Keys you'll read:

- `default_stage` — defaults to `core`. Must be one of the valid stages below.
- `default_analysis` — fallback when the user doesn't pick. Ships unset; the
  skill prompts the user instead.
- `stages` — map of stage name → which Splunk pull to run via the sister skill.
- `prompts_dir` — relative path to the prompts cache (default `./prompts`).
- `obs_hub_repo` — upstream repo (`baleksan/obs-hub`). Used by the refresh
  script — never queried at run time.

### Valid stages

| Stage | Meaning | Sister-skill workflow used |
|---|---|---|
| `core` (default) | Core agent runtime b2usg logs | "Analyze a specific Bot Session (Core-only deep dive)" — Step 3 + Step 5-Core |
| `scrt2` | SCRT2 chat layer logs | Step 2 (SCRT2 events) + Step 5-SCRT2 (errors) |
| `e2e` | Both layers, merged timeline | Full E2E workflow (Steps 1–5) |
| `ux` | MIAW client UX rows | The `uxRows` pull from `shopper-agent-trace-visualize` SKILL.md, Step 2 |

If the user gave a stage that isn't one of these, ask them to pick — don't
guess. If they gave only a `botSessionId` (no `conversationId`) and ask for
`scrt2` or `e2e`, run the bot-session → conversation reverse lookup from
`shopper-agent-trace-visualize` Step 1b before falling back to `core`-only.

## Workflow

### Step 1 — Verify prerequisites

Before doing anything else:

1. Check that the sister skill `shopper-agent-splunk-query` is installed at
   `~/.claude/skills/shopper-agent-splunk-query/`. If missing, stop and point
   the user there.
2. Check that `query_splunk` (typically `mcp__mcp-adaptor__query_splunk`) is in
   the available tools list. If missing, stop and follow the same Prerequisites
   steps the sister skill documents (AI Suite install → auth → `GW_PROFILE=monitoring`).
3. Enumerate `sub-skills/*.md` (see "How to enumerate sub-skills" above).
   - Skip `README.md`, `_*.md`, and `.*.md`.
   - At least one valid sub-skill file must exist. If the directory is
     empty or every file fails frontmatter validation, stop and tell the
     user to run `scripts/refresh_prompts.sh` (or to add a sub-skill file
     manually using the contract in `sub-skills/README.md`).
   - Hold the parsed list in memory — both Step 3 and Step 8 use it.

### Step 2 — Resolve sessionId, stage, analysis

Parse the user's request for:

- **sessionId** (required). Could be a `conversationId` (any UUID) or a
  `botSessionId` (UUID starting with `019`). Detect via the same regex the
  sister skill uses: `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`.
- **stage** (optional, defaults to `default_stage` from config = `core`).
- **analysis** (optional). If the user named one ("run anomaly detection",
  "summarize as JSON"), match it to an ID from the table above. Otherwise,
  go to Step 3 and offer the menu.

Announce what you resolved before continuing:

> *"Got it — session `019def…453b`, stage `core`. Pick one of the analyses
> below or tell me which one to run."*

### Step 3 — Render the analysis menu (mandatory when no analysis was named)

**This step is non-optional unless the user explicitly named one of the
sub-skill IDs (or `all`) in their request.** Do not silently fall back to
`default_analysis`. Do not guess from context. If in doubt, show the menu.

Build the menu **dynamically from the sub-skills list** you enumerated in
Step 1. For each sub-skill (in `order` ascending):

- Number it sequentially starting at 1.
- Show `id` on the left, `description` on the right.
- (Optional) append the `output` type as a tag: `[md]` or `[json]`.

Render template (the actual contents come from `sub-skills/*.md`):

```
Pick an analysis to run on session <sessionId> (stage: <stage>):

  <n>. <id>          — <description>  [<output>]
  <n>. <id>          — <description>  [<output>]
  ...

Reply with a number (1-N), the ID, or "all" to run every analysis.
```

Then **stop and wait for the user to pick**.

Accept any of:
- The sequential number (`3`)
- The exact `id` (`latency`)
- A case-insensitive match against `id` or `label`
- `all` to run every sub-skill (confirm first — each is a paid LLM call)

If the user explicitly says "skip the menu" or "use my default", honor
`default_analysis` from config — but only when they ask for it.

### Step 4 — Pull Splunk results via the sister skill

Delegate the data pull. Don't write your own SPL.

- For `stage=core`: invoke the sister skill's "Analyze a specific Bot Session
  (Core-only deep dive)" workflow.
- For `stage=scrt2`: use Step 2 + Step 5-SCRT2 from the sister skill.
- For `stage=e2e`: use the full E2E workflow (Steps 1–5).
- For `stage=ux`: use the `uxRows` query template from `shopper-agent-trace-visualize`
  SKILL.md, Step 2.

In all cases, request **raw output** from the sister skill (it has a `raw`
output mode). You want `_time` + `_raw` columns plus any first-class fields
(e.g. `level`, `service`, `logger`, `operation`, `userQuery`). The obs-hub
prompts work best on raw or lightly-parsed log lines — over-formatted markdown
tables strip too much signal.

If the sister skill returns zero rows, stop. Don't run the analysis on an
empty input — the LLM will hallucinate. Tell the user the pull was empty
and suggest widening the time range.

### Step 5 — Apply the chosen prompt

For each chosen analysis:

1. Open `sub-skills/<id>.md`. Skip the YAML frontmatter (everything from
   the opening `---` to the next `---` line). Take the **body** verbatim.
2. Determine output mode from the frontmatter `output:` field
   (`markdown` or `json`).
3. Build the LLM call as:

   ```
   System / instruction:
     <body of sub-skills/<id>.md, unmodified>

   User:
     Session ID: <sessionId>
     Stage: <stage>
     Time range: <earliest> → <latest>
     Splunk rows (chronological):

     <one row per line, _time then _raw, no extra formatting>
   ```

4. If `output: json` (per the frontmatter), render the response inside a
   fenced ```json``` block. Validate it's parseable; if not, retry once
   with a correction note ("Your previous response was not valid JSON.
   Return only valid JSON conforming to the schema above.").

5. If `output: markdown`, render the response as-is.

If the user picked `all`, run them sequentially (or in parallel if the runtime
allows independent LLM calls), and stitch into a single report with one
section per analysis.

### Step 6 — Render the report body

Header every report with the resolved context so the user can verify:

```markdown
# 🔬 Obs-Hub Analysis — <sessionId>

| Field | Value |
|-------|-------|
| Session ID | <sessionId> |
| Stage | <stage> |
| Environment / Org | <env> / <org> |
| Time range | <earliest> → <latest> |
| Analysis | <id> (sub-skills/<id>.md) |
| Splunk rows analyzed | <N> |
| Prompt source | sub-skills/<id>.md (upstream: <upstream.repo>@<upstream.branch>:<upstream.path>, if set) |

---

<analysis output>
```

If the prompt produced JSON, include the raw JSON inside a fenced block AND a
short human-readable summary above it (one paragraph). If the prompt produced
markdown, include it verbatim under the header.

After the body, **always** append Step 7 (Splunk Links Used) and Step 8
(What's next). Both are mandatory — see those steps for exact wording.

### Step 7 — Always output the Splunk links used (mandatory)

Every report — successful, partial, or failed — must end with a section
titled `## 🔗 Splunk Links Used` that lists the **exact** queries you ran to
build the analysis input. One bullet per query. Each bullet must contain:

- A short label (e.g. *"Core — full session"*, *"SCRT2 — events for conversation"*).
- The clickable Splunk web URL with the SPL search string and time range
  pre-filled. Use the env's `web_endpoint` + `web_app_path` from the sister
  skill's config.
- A one-line note on what the query returned (row count, or "no rows", or
  "timed out").

Template:

```markdown
## 🔗 Splunk Links Used

- **Core — full session (preprod):**
  `<CORE_WEB_ENDPOINT><CORE_WEB_APP_PATH>?q=search%20<URL_ENCODED_SPL>&earliest=<E>&latest=<L>`
  *Returned 16 rows in 36 s.*

- **Core — error scan (preprod):**
  `<…>`
  *Returned 0 rows.*

- **SCRT2 — events for conversation (preprod):**
  `<SCRT2_WEB_ENDPOINT><SCRT2_WEB_APP_PATH>?q=search%20<URL_ENCODED_SPL>&earliest=<E>&latest=<L>`
  *Skipped — stage was `core`-only.*
```

Rules:
- **Build one link per Splunk query you actually ran.** If you ran 3
  queries (e.g. main pull + identity check + error scan), output 3 bullets.
- **Always include the time range** — even if the user didn't specify one,
  show the resolved earliest/latest you used.
- **Annotate skipped queries.** If a stage was out of scope (e.g.
  `stage=core` so you skipped SCRT2), still list a placeholder bullet
  saying "skipped — stage was X" so the user knows what was *not* checked.
- **Never elide or shorten URLs** with `…`. The user must be able to click
  through to the raw data.

If the env config has `core_prod_pods` (prod, pod-sharded), use the same
`<CORE_INDEX_EXPR>` you sent to Splunk — `index=<pod>` or `index IN (...)` —
URL-encoded.

### Step 8 — Ask "what's next" (mandatory)

After the Splunk-Links section, **always** render this follow-up menu and
**stop**. Wait for the user to choose before doing anything else.

Build this menu **dynamically** from the same sub-skills list you used in
Step 3. For each sub-skill, append `(✓ already run)` if it has been
executed in this session.

Render template:

```markdown
---

## ▶️ What's next?

**(a)** Continue analyzing the same session — pick another sub-skill on the
data already pulled (no new Splunk hits):

  <n>. <id>          — <description>  [<output>]   <(✓ already run) if applicable>
  <n>. <id>          — <description>  [<output>]
  ...
  <N+1>. all-remaining — Run every analysis you haven't run yet on this session.

**(b)** Start a new analysis on a different session. Reply with the
new `sessionId` (and optional stage) and I'll pull fresh data.

**(c)** Export the most recent analysis as a shareable HTML report
(self-contained, with charts and stats). I'll write it to
`.agents/artifacts/<sessionId>_<analysisId>.html`. Reply `c` or `html`.

Reply with `a<n>` (e.g. `a3`), `b <sessionId>`, `c`, or just the number /
ID of a sub-skill if it's unambiguous.
```

Rules:
- **Mark `(✓ already run)`** next to every sub-skill ID the user has
  already executed in this session, so the menu reflects state.
- **Reuse the in-memory Splunk rows** for option (a) — do NOT re-query
  Splunk. The data was already pulled in Step 4; a follow-up sub-skill
  just feeds those same rows into a different sub-skill prompt body.
- For option (b), restart from Step 1 (verify prereqs → enumerate
  sub-skills → resolve session → pull → menu → analyze → links → next?).
- If the user picks `all-remaining`, count the remaining sub-skills
  (those without `(✓ already run)`) and confirm before kicking off N LLM
  calls.
- Treat ambiguous answers ("anomaly", "3", "latency please") as picks for
  option (a) — match by ID or number first, free-text second.
- Treat `c`, `html`, `export`, `export html`, `share` as picks for
  option (c) — go to Step 9.

### Step 9 — Export HTML report (on request)

Triggers (any of):
- User included `+html`, `+report`, "html report", "shareable", or
  "export" in their original request.
- User picked option `(c)` in the "What's next?" menu.
- User explicitly says "make an HTML report for that" / "export that as
  HTML".

Behavior:

1. **Check eligibility.** Read the chosen sub-skill's frontmatter:
   if `html_eligible: false` is set, refuse politely and explain.
   Default is eligible.
2. **Locate inputs** (all already on disk from Steps 4-5):
   - `<rows-file>` — the cached Splunk rows
     (`.agents/artifacts/<sessionId>_raw.json` per the
     `pulled_rows_cache_dir` config).
   - `<analysis-file>` — write the LLM's response body to
     `.agents/artifacts/<sessionId>_<analysisId>.md` (or `.json` for
     JSON analyses) before invoking the renderer. If you didn't save
     it during Step 6, save it now.
   - `<meta-file>` — generate a small JSON containing the **exact**
     Splunk Links Used section as a structured list:
     ```json
     {
       "splunk_links": [
         { "label": "...", "url": "...", "note": "..." }
       ]
     }
     ```
     Save to `.agents/artifacts/<sessionId>_<analysisId>_meta.json`.
3. **Invoke the renderer:**
   ```bash
   python3 ~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/render_html.py \
     --session-id=<sessionId> \
     --stage=<stage> \
     --environment=<env> \
     --org=<org> \
     --earliest=<earliest> \
     --latest=<latest> \
     --analysis-id=<id> \
     --analysis-label="<label from sub-skill frontmatter>" \
     --analysis-output=markdown|json \
     --analysis-file=<path-to-llm-output> \
     --rows-file=<path-to-rows> \
     --meta-file=<path-to-meta> \
     --out=.agents/artifacts/<sessionId>_<analysisId>.html
   ```

   ⚠️ **Use `=` syntax for every flag** (`--earliest=-7d@d`, not
   `--earliest -7d@d`). Time values that start with `-` will otherwise
   confuse argparse.

4. **Confirm in chat** with the absolute path and a `file://` URL the
   user can click. Mention the file is self-contained (Chart.js +
   marked.js are loaded from CDN; nothing else is needed) and can be
   shared by attaching it to Slack / email.
5. **Multiple analyses on the same session** (option `all`, or after
   running several sub-skills in succession): when the user asks for
   HTML, default to rendering **the most recent analysis only**. If
   they want every analysis as HTML, render N files (one per analysis
   ID) — confirm before producing N files.

What the renderer does (deterministic, no LLM):
- Parses each Splunk row's `_raw` to extract operation, status, latency,
  stages, userQuery, requestId.
- Computes: total rows, distinct turns, unique ops, wall-clock duration,
  failure count, max latency, status breakdown.
- Renders 4 charts (Chart.js): Operations by type (doughnut), Latency per
  operation (bar with avg+max), Timeline (scatter), Status breakdown
  (doughnut, color-coded).
- Renders an Operations table with all rows, status badges, stage
  durations.
- Renders the analysis body (markdown via `marked.js`, or pretty-printed
  JSON inside a `<pre>`).
- Renders the Splunk Links Used section as clickable links.

The output is a single ~20-30 KB HTML file. Open via
`file://<absolute-path>` or attach directly to Slack.

## Refreshing prompts from upstream

Each sub-skill file may declare an `upstream:` block in its frontmatter
pointing at a source repo + branch + path. The refresh script walks
`sub-skills/*.md`, fetches the upstream body for any file that has
`upstream:`, and replaces **only the body** (frontmatter is preserved
verbatim). Files without `upstream:` are skipped — locally-authored
sub-skills are safe.

```bash
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh --dry-run
~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/refresh_prompts.sh --force
```

The script uses the `gh` CLI (no auth token in this skill — it relies on
the user's existing GitHub auth) and reports a per-file diff before
overwriting.

To **add** a new sub-skill (whether sourced upstream or authored locally),
just drop a new file into `sub-skills/` following the contract in
`sub-skills/README.md`. No code or config edit required — it shows up in
the menu on next invocation.

## What NOT to do

- ❌ Do **not** paraphrase a sub-skill's prompt body at runtime. Load the
  body verbatim. The wording and schema are deliberate.
- ❌ Do **not** invent SPL. Always delegate to `shopper-agent-splunk-query`.
- ❌ Do **not** run an analysis with zero rows of input.
- ❌ Do **not** run every sub-skill by default — each one is a paid LLM call.
  Only do it when the user explicitly says `all` and you've confirmed.
- ❌ Do **not** fetch from upstream repos at runtime. Refresh is an
  explicit user-driven action via `scripts/refresh_prompts.sh`.
- ❌ Do **not** maintain a parallel hardcoded list of sub-skills anywhere.
  The filesystem is the source of truth.

## Examples

### Example 1 — Default (core stage, anomaly detection)

User: *"Run anomaly detection on session 019def8d-3168-709e-98ec-8a7d3a202785"*

→ Resolve: sessionId=`019def8d-…`, stage=`core` (default), analysis=`anomaly`.
→ Sister skill: Core-only deep dive → returns ~40 rows.
→ Read body of `sub-skills/anomaly.md`, build LLM call with rows.
→ Render markdown report under the standard header.

### Example 2 — User picks from menu

User: *"Analyze session 019def…  in core"*

→ Resolve: sessionId, stage=`core`. No analysis specified.
→ Render the menu (Step 3). Wait for input.
→ User: *"3"*. → Run `latency`.
→ Pull rows + apply body of `sub-skills/latency.md`.

### Example 3 — E2E quality assessment

User: *"Score search quality end-to-end for conversation 8ec19111-08ca-4986-ba67-f33f7af213a8"*

→ Resolve: sessionId=conversationId, stage=`e2e`, analysis=`quality`.
→ Sister skill: full E2E pull → unified rows from SCRT2 + Core.
→ Apply body of `sub-skills/quality.md`.
→ Output the ESCI table, NDCG@5/@10, suggestion quality.

### Example 4 — Suggested improvements (cross-aspect synthesis)

User: *"What should we improve in this session? Give me a backlog."*

→ Resolve session, pull rows (or reuse from cache).
→ Apply body of `sub-skills/suggested-improvements.md`.
→ Output the prioritized P0/P1/P2 backlog with experiment cards
  (hypothesis, single variable, primary + guardrail metrics, exit
  criteria) for each item. Best run **after** `anomaly`, `latency`, or
  `quality` so the synthesis has prior findings to draw on, but works
  standalone too.

### Example 5 — Stage UX

User: *"Anomaly detection on UX events for conversation X"*

→ Resolve: stage=`ux`, analysis=`anomaly`.
→ Pull MIAW UX rows via the `shopper-agent-trace-visualize` MIAW Client UX
  template (Step 2 there).
→ Apply body of `sub-skills/anomaly.md`.

## Workflow tips for the model

1. **Verify MCP + sister skill first.** Bail early if either is missing.
2. **Always show the menu (Step 3)** when the user didn't name an analysis.
   Don't silently pick `default_analysis` — the menu is short and worth
   confirming. The only exceptions: the user explicitly said "skip the menu"
   or "use my default", or they explicitly named one of the IDs / `all`.
3. **Always emit Splunk Links Used (Step 7).** One bullet per query you ran,
   each with the full clickable URL, time range, and a one-line result note.
   Never elide URLs. Always list skipped stages too.
4. **Always ask "what's next?" (Step 8).** After the analysis output and the
   Splunk links section, render the follow-up menu and stop. Mark already-
   run sub-skills as `(✓ already run)` so the menu reflects state.
5. **Cache the Splunk rows in-session.** Option (a) of the "what's next"
   menu must reuse the rows you already pulled — do NOT re-query Splunk for
   a follow-up sub-skill on the same session. Save them to
   `.agents/artifacts/<sessionId>_raw.json` so cross-turn continuation works.
6. **Load prompts from `sub-skills/<id>.md`.** Skip the YAML frontmatter,
   take the body verbatim. Never inline a prompt. The user can edit a
   sub-skill file locally to tweak behavior, and the next run picks it up.
7. **Use raw Splunk output.** The prompts expect log-like content, not
   pre-summarized tables. Ask the sister skill for `raw`.
8. **Validate JSON outputs.** If the prompt's filename ends `_json.txt` and
   the model returned non-JSON, retry once with a correction note.
9. **Keep the header consistent.** Same fields every time, even on errors.
10. **Don't auto-refresh prompts.** Tell the user how to do it via the
    script and let them decide when.
11. **This skill is read-only** with respect to Splunk and the obs-hub
    repo — no writes there. Local writes are limited to
    `.agents/artifacts/` (cached rows, saved analysis bodies, generated
    HTML reports).
12. **HTML renderer flag syntax.** When invoking
    `scripts/render_html.py`, always use `=` syntax for every flag —
    `--earliest=-7d@d`, never `--earliest -7d@d`. argparse will treat a
    `-`-prefixed value as a missing arg otherwise.
