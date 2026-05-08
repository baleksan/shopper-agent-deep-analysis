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
- **Action results are even tighter.** When the user runs an
  action (`+html`, `+gus`, file attach, etc.), the post-action
  response should be **one sentence per discrete action taken**, plus
  the resulting links / IDs in a small table or list. Skip the
  congratulatory framing and recap of inputs the user just gave you.
  - ❌ "I've successfully completed step 1, which involved rendering
    the HTML report. Then I moved on to step 2, which was creating the
    GUS work item. After that I attached..."
  - ✅ "Rendered HTML, created W-22400143, attached the report.
    Links: [...]."
- **Surface only what the user needs to act on next.** Errors,
  unexpected schema mismatches, and pending questions get called out;
  routine successes don't.

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

## 🪄 Output token economy (always apply to LLM calls)

Sub-skill outputs are read by engineers, not customers. Optimize for
information density per token. **Append these rules verbatim to every
sub-skill prompt body** when building the Step-5 LLM call — they sit
between the sub-skill body and the per-session data:

```
=== Output rules (token economy) ===
- Fragments fine. Drop articles when meaning survives.
- 1 sentence per finding max. Bullet glyphs over prose.
- Tables for ≥3 data points. Numbers in cells, not sentences.
- No transition / closing / restate phrases ("In summary…",
  "It's worth noting…", "Looking at the data…"). State the thing.
- No hedges ("perhaps", "it may be", "this could indicate"). State with
  the supporting number instead.
- No section preambles. Heading is enough.
- Recommendations as imperatives. "Add cache." not "We should consider
  adding a cache."
- Cite ms/counts/IDs inline once. Don't repeat across sections.
- Use →  for cause/effect, × for "didn't happen", + for "also". Skip
  the words.
- 2-line cap per bullet.
- Direct quotes (user queries, log lines, schema fields) go verbatim —
  these rules don't apply inside quoted material.
=== End output rules ===
```

Don't paraphrase these rules at runtime. Append the literal block
above. The LLM is more reliable with rule lists than with re-explained
constraints.

**Don't apply these rules to:**
- The standard report header (sessionId, env, time range, row count) — those are key-value, already terse.
- Splunk Links Used — URLs are URLs.
- The "What's next?" menu — state display, must be readable.
- The chat-rendered Timing table.

**Validation requirement**: when changing these rules, re-run each
sub-skill on a known dataset, diff findings against the previous
output. Drop a rule if it removed a finding.

## 🚀 LLM speed (always apply)

The LLM is the dominant cost — typically 80-95% of `total` time. Three
levers, all accuracy-neutral when applied as specified.

### 1. Input projection (mandatory)

The cached `<sessionId>_raw.json` rows include the full SCAPI
`ProductSearchResponse` (image groups, prices, URLs). For most
analyses, those bytes are noise. Each sub-skill declares a
`projection:` tag list in its frontmatter; the orchestrator runs
`scripts/project_rows.py` to slim the rows before sending them to the
LLM.

In Step 5 (apply prompt), **always project before building the LLM
call**:

```bash
python3 ~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/project_rows.py \
  --rows-file=.agents/artifacts/<sessionId>_raw.json \
  --include="<projection from sub-skill frontmatter>" \
  --out=.agents/artifacts/<sessionId>_<analysisId>_input.txt
```

Then feed `_input.txt` (one row per line, projected fields only) to
the LLM as the user message. Typical reduction: **150-300x** for
non-quality sub-skills (691 KB → 2-4 KB).

If a sub-skill omits `projection:`, fall back to the full raw rows
(slow). Warn in chat that this is happening so the sub-skill author
can fix it.

**Don't** project for `quality` if the analysis specifically needs
full image / price metadata; the `product_full` tag is available
when needed (rare).

### 2. Prompt caching (when API allows)

Anthropic's API caches stable prompt prefixes. Structure the LLM
call so the **sub-skill prompt body** (which doesn't change across
sessions) is the cacheable system block, and only the per-session
**rows + metadata** are the variable user message:

```
system: <body of sub-skills/<id>.md, marked cache-control: ephemeral>
user:   Session ID: ...
        Time range: ...
        Splunk rows (projected):
        ...
```

Sub-skill body cache hits give a **10-25% reduction** on cold runs
where the user picks the same analysis twice in a row, and similar
gains across users running the same analysis. If the harness doesn't
expose cache-control, this is a no-op — don't error.

**Don't** put per-session data (sessionId, rows) in the cached
block. Cache misses cost more than they save when the cache key
churns.

### 3. Streaming responses (when harness allows)

If the harness exposes LLM streaming, request a streaming response
and surface partial output to the user as it arrives. Wall-clock is
unchanged but perceived latency drops dramatically — a 60s analysis
feels like 5s if the user sees the executive summary at second 5.

If the harness doesn't expose streaming, skip — don't try to fake it.

## ⏱️ Stage timings (always track)

For every user-initiated action, track wall-clock time per stage and
surface the breakdown both in chat (at the end of the report) and in
the Slack DM (when one is sent). The breakdown answers "why did that
take 45s?" without the user having to ask.

**Stages** (skip stages that didn't run):

| Stage | Starts when | Ends when |
|---|---|---|
| `prep` | user replies | sub-skill resolved, prereqs verified, sub-skills enumerated |
| `splunk` | first MCP `query_splunk` call | last Splunk row received (or cache hit confirmed) |
| `llm` | analysis prompt sent to LLM | LLM response complete + JSON-validated (if applicable) |
| `render` | `render_html.py` invoked | HTML file written to disk |
| `screenshot` | `screenshot_html.py` invoked | PNG written to disk |
| `gus` | `sfcli:gus` write begins | `ContentDocumentLink` confirmed (or write fails) |
| `total` | user replies | last action complete |

**Render in chat** as a small table inside a `<details>` block named
`⏱ Timing` placed just before the "What's next?" menu:

```markdown
<details>
<summary><strong>⏱ Timing</strong></summary>

| Stage | Time |
|---|---|
| prep   | 0.4 s |
| splunk | 0.0 s *(cache hit)* |
| llm    | 12.1 s |
| render | 0.5 s |
| **total** | **13.0 s** |

</details>
```

Mark stages annotated with `(cache hit)` / `(skipped)` clearly so the
user knows the zero isn't suspicious. If a stage didn't run at all,
omit its row.

**Include the same table in the Slack DM** when one is sent (see
below) — same format, just a Slack-flavored markdown table.

## 📣 Long-running notifications (Slack DM)

When an action takes long enough that the user is likely to switch
tabs / context-switch, send a self-DM on Slack on completion so they
don't have to babysit the chat.

**Trigger threshold**: any single action (Splunk pull, LLM analysis,
HTML render, GUS write+attach, or any combination chained with
`+html` / `+gus`) whose `total` stage time exceeds **30 seconds**.

**How**:
1. Get the user's Slack user_id once per session — you already know it
   for AI Suite users (the system surfaces it in Slack tool descriptions
   as the "current logged in user's user_id"). Don't ask the user; if
   you can't resolve it, log a warning in chat and skip the DM.
2. **Pick the link to share, in this priority order:**
   - If the analysis was attached to a GUS WI in this session, use
     the **GUS Salesforce File URL**
     (`https://gus.my.salesforce.com/lightning/r/ContentDocument/<id>/view`).
     This is clickable from Slack web/mobile/anywhere.
   - Otherwise, use the **`file://` URL** AND include a one-line
     explanation that Slack security blocks `file://` URLs from
     opening directly, so the user must copy the path and paste it
     into a browser address bar.
   - Never include both — pick one, surface clearly.
3. Call `mcp__plugin_slack_slack__slack_send_message` with `channel_id =
   <user's own user_id>` (a self-DM) and a message of this shape:

   **When linked to a GUS WI:**
   ```
   ✅ Obs-Hub analysis ready — <sub-skill-id> on session <sessionId-short>

   • <one-line headline finding>
   • Report: [📄 Open <sub-skill-id> report](https://gus.my.salesforce.com/lightning/r/ContentDocument/<id>/view)
   • Linked to: [W-XXXXXXXX](https://gus.lightning.force.com/lightning/r/ADM_Work__c/<id>/view)

   ⏱ Timing
   | Stage | Time |
   |---|---|
   | ... | ... |
   | **total** | **<n>s** |

   Reply in chat to continue.
   ```

   **When NOT linked to a GUS WI (most common):**
   ```
   ✅ Obs-Hub analysis ready — <sub-skill-id> on session <sessionId-short>

   • <one-line headline finding>
   • Report path:
     `/Users/.../019xxxxxx_<analysisId>.html`

   ⚠️ Slack security blocks `file://` links from opening directly.
   Copy the path above and paste it into your browser address bar
   (or open it from Finder). The file is self-contained — no server
   needed.

   ⏱ Timing
   | Stage | Time |
   |---|---|
   | ... | ... |
   | **total** | **<n>s** |

   Reply in chat to continue.
   ```

   Use `slack_send_message` directly (not `slack_send_message_draft`) —
   this is a transactional notification, not a draft for review.
   Send the **path inside a code-fenced block (single backticks)** so
   the user can triple-click to select the whole thing.

**Skip the DM when**:
- The total time was < 30s (the user is still watching).
- The user explicitly said "quiet" / "no slack" / "don't ping me".
- The Slack tool is unavailable (gracefully skip, mention in chat).

**Don't**:
- DM on every step. One DM per user-initiated action, not per
  Splunk query / per LLM call.
- Include sensitive data in the DM (org IDs are fine; raw SCAPI
  payloads are not).
- Use Slack channels — always DM the user, never post publicly.
- Send the full report body — only the link/path + headline + timing.
- Format `file://` URLs as markdown links (Slack will render them
  clickable but they won't open). Use a plain code-fenced path
  instead, with the explanation.

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
3. **HTML report + screenshot preview by default.** After every successful
   analysis, immediately (a) render the self-contained HTML report via
   `scripts/render_html.py` (with `--no-open`), (b) capture a PNG
   snapshot of the top of that report via `scripts/screenshot_html.py`,
   and (c) embed the PNG in chat as a clickable image that links to the
   HTML file. This replaces the verbose chat-side analysis dump — the
   chat surface gets a tight executive summary (≤ 6 bullets / 1 small
   table) plus the screenshot. Full prose, tables, charts, and Splunk
   links live inside the HTML. See
   [Step 9](#step-9--render-html--screenshot-default-after-every-analysis).
   Sub-skills with `html_eligible: false` (none ship today; flag
   reserved) skip this — chat gets the full report instead.
4. **What's next on exit.** After the screenshot is shown, render
   the [Step 8](#step-8--ask-whats-next-mandatory) follow-up menu offering
   `(a)` continue with another sub-skill on the same data, or `(b)` start
   a fresh analysis on a different session. Wait for input.
5. **Filing a GUS work item is a post-action available on every
   sub-skill.** It's a follow-up the user can request inline (`+gus`)
   or from the "what's next" menu (option `(c)`). When chosen, the
   skill (a) asks for **team name** (required) and **theme**
   (optional), (b) reuses the HTML report rendered in Step 9 (already
   on disk), (c) creates the WI via `sfcli:gus` with the analysis
   output embedded in `Details__c`, and (d) attaches the HTML as a
   Salesforce File via `scripts/attach_html_to_gus.sh`. See
   [Step 10](#step-10--file-gus-work-item-on-request).

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

## Input modes

The skill supports **two input modes** for the data pull. Pick one based
on what the user asked for.

### Single-session mode (default)

The user gave a `botSessionId`, `conversationId`, or both. Most
sub-skills (`anomaly`, `latency`, `quality`, `query-analysis`,
`suggested-improvements`, `create-gus-wi`) only operate on
single-session input.

### Interval mode

Triggered when the user asks "what happened today for X", "give me a
summary for SharkNinja last 6 hours", "summarize Funko's traffic
yesterday", etc. — i.e. a **customer/site/org** + **time window**
instead of a session ID.

In this mode:
1. Resolve customer → org_id + pod via the sister skill's
   `customer_pods` mapping (or ask the user if unmapped).
2. Pull rows aggregated across all sessions in the window. Use a
   broader query than single-session mode:
   ```
   <CORE_INDEX_EXPR> <CORE_LOG_FILTER> organizationId="<ORG_ID>"
   earliest=<earliest> latest=<latest>
   | sort 0 _time asc
   | head 5000
   ```
   Cap at `behavior.max_rows_per_analysis × 10` (default 5000) to
   stay inside the MCP's 5,000-event limit.
3. Confirm with the user before running for windows larger than
   24h on a busy customer — that may exceed the row cap.

**Sub-skills that support interval mode**: only `summary` today.
The others assume single-session semantics (per-step latency,
per-turn ESCI scoring, etc.) and would produce nonsense across
multiple sessions. If the user picks an interval-incompatible
sub-skill in interval mode, refuse and point at `summary` instead.

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

### Step 6 — Save the analysis body and render the chat snapshot

The full analysis prose is **not** dumped into chat. It's written to disk
so Step 9 can render it into HTML, and chat gets a tight snapshot
instead.

1. **Save the LLM body to disk** at
   `.agents/artifacts/<sessionId>_<analysisId>.md` (or `.json` for
   JSON-output sub-skills). Keep it verbatim — that file is the
   canonical analysis artifact.

2. **Render the chat snapshot** with the standard header followed by
   an executive summary block:

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

   **TL;DR**
   - 🔴 / 🟠 / 🟢  3-5 bullets max — most-actionable findings only.
   - Each bullet ≤ 1 line, with one number for evidence.
   - No tables here unless a single 2-column numeric table tells the
     story more compactly than bullets would.

   <Step-9 inline image goes here — see Step 9 for exact markdown.>
   ```

   Hard rules for the chat snapshot:
   - **No more than 5 TL;DR bullets** and **no full Step Duration / Evidence /
     Recommendations tables** in chat. Those live in the HTML.
   - The image inserted by Step 9 IS the body of the report in chat.
     Don't paraphrase the HTML's contents — point at it.
   - If the sub-skill is `output: json`, render only a 1-paragraph
     human summary as TL;DR; the JSON itself only appears in the HTML.

3. **Skip the snapshot for `html_eligible: false` sub-skills** (none
   ship today). Those still use the old behavior — full prose in chat.

After the snapshot+image, **always** append Step 7 (Splunk Links Used) and
Step 8 (What's next). Both are mandatory — see those steps for exact wording.

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

**(c)** File a GUS work item from the most recent analysis. I'll ask for
your **team name** (required) and an optional **theme**, then create the
WI via `sfcli:gus` with the analysis output embedded in `Details__c` and
the HTML report attached as a Salesforce File. Reply `c` or `gus`.

Reply with `a<n>` (e.g. `a3`), `b <sessionId>`, `c`, or just the
number / ID of a sub-skill if it's unambiguous.

(The HTML report + screenshot is already produced automatically — no
separate "export" step needed. Click the image above to open it.)
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
- Treat `c`, `gus`, `+gus`, `file wi`, `file ticket` as picks for
  option (c) — go to Step 10.
- The HTML export step is no longer user-driven — it always runs in
  Step 9 right after the analysis. If a user explicitly types `html`,
  `+html`, `share`, etc., just point them at the screenshot already in
  chat and the file path it links to.

### Step 9 — Render HTML + screenshot (default, after every analysis)

This step **runs by default** after every successful analysis whose
sub-skill is `html_eligible` (i.e. all of them today). It is **not**
user-driven — the user does not have to ask for HTML; they get it
automatically along with a clickable screenshot preview in chat.

Skip only if the sub-skill has `html_eligible: false` (none ship today;
flag reserved). In that case, fall back to the pre-2026-05 behavior of
dumping full prose into chat.

Behavior:

1. **Locate inputs** (all already on disk from Steps 4-6):
   - `<rows-file>` — cached Splunk rows
     (`.agents/artifacts/<sessionId>_raw.json` per the
     `pulled_rows_cache_dir` config).
   - `<analysis-file>` — the LLM body, saved during Step 6 to
     `.agents/artifacts/<sessionId>_<analysisId>.md` (or `.json`).
   - `<meta-file>` — write the **exact** Splunk Links Used section
     as a structured list and save to
     `.agents/artifacts/<sessionId>_<analysisId>_meta.json`:
     ```json
     {
       "splunk_links": [
         { "label": "...", "url": "...", "note": "..." }
       ]
     }
     ```

2. **Render the HTML in the background, with `--no-open`.** The
   user does not want a browser tab opening every time — they want
   the snapshot in chat. Always pass `--no-open`:
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
     --analysis-file=<analysis-file> \
     --rows-file=<rows-file> \
     --meta-file=<meta-file> \
     --no-open \
     --out=.agents/artifacts/<sessionId>_<analysisId>.html
   ```

   ⚠️ **Use `=` syntax for every flag** (`--earliest=-7d@d`, not
   `--earliest -7d@d`). argparse otherwise treats `-`-prefixed values
   as missing.

3. **Capture a PNG screenshot of the top of the report** via
   headless Chrome (or qlmanage fallback):
   ```bash
   python3 ~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/screenshot_html.py \
     --html=.agents/artifacts/<sessionId>_<analysisId>.html \
     --out=.agents/artifacts/<sessionId>_<analysisId>.png \
     --width=1280 --height=900
   ```
   - Default viewport (1280×900) captures the standard header + the
     first few sections, which is the right amount of "preview".
   - Pass `--full-page` only if the user asks for a full-page
     screenshot. The default short preview is what plays nicely in
     chat.
   - If the script reports the qlmanage fallback (no Chrome found),
     warn the user once: "Snapshot quality limited — install Chrome
     for full-fidelity previews including charts."

4. **Display the screenshot inline + provide a click-through link.**
   This is the chat surface's primary view of the report. The reliable
   pattern in AI Suite / most chat renderers is **two separate
   elements**, not a markdown `[![image](file://...)](file://...)`:

   - **Display the PNG inline** by calling the **`Read` tool** on the
     PNG path. Claude's `Read` of an image surfaces it visually in
     chat. This works everywhere — `![](file://...)` does NOT
     (most renderers block local file URIs in image src for security
     and just show a broken-image icon).
   - **Below the image**, render a plain markdown text link to the
     HTML — AI Suite (and most desktop chat clients) DO follow
     `file://` URLs in regular `[text](url)` markdown links:
     ```markdown
     **[📄 Open the full interactive report →](file:///abs/path/to/<sessionId>_<analysisId>.html)**

     *Path (copy/paste if the link is blocked):*
     `/abs/path/to/<sessionId>_<analysisId>.html`
     ```

   Rules:
   - Always `Read` the PNG **before** writing the link, so the image
     anchors above the click-through and the user reads top-to-bottom.
   - Always use **absolute** paths — relative paths break.
   - Always include the plain text path inside a single-backtick code
     fence so the user can triple-click + copy if their environment
     (Slack, locked-down browsers) blocks `file://` link clicks.
   - **Never** use `![](file://...)` markdown image syntax. It will
     render as a broken-image placeholder.

5. **Multiple analyses on the same session.** Each sub-skill that
   runs gets its own HTML + PNG pair. Don't overwrite an earlier
   analysis's files — the filename includes `<analysisId>` precisely
   so they coexist.

6. **Failures are non-fatal.** If `render_html.py` or
   `screenshot_html.py` fails, fall back to dumping the analysis prose
   in chat (the old behavior) and surface the error in a one-line
   note ("⚠️ HTML preview failed: <reason>. Showing full report in
   chat instead."). Don't block the analysis output on a render error.

What the HTML renderer produces (deterministic, no LLM):
- Header with session metadata.
- 4 charts (Chart.js): Operations by type, Latency per op (avg+max),
  Timeline, Status breakdown.
- Operations table with status badges + stage durations.
- The full analysis body (markdown via marked.js, or pretty-printed JSON).
- Splunk Links Used section.

Output is a single ~20-30 KB HTML file (CDN deps for Chart.js +
marked.js). Self-contained — drop into Slack / email and it works.

#### User-typed `+html` / `share` / `export`

Since HTML is now produced by default, these phrases no longer trigger
a separate flow. Treat them as a hint to:
- re-surface the existing image + path if the analysis already ran,
- or proceed normally (the HTML will render in this Step 9 as part of
  the standard flow).

### Step 10 — File GUS work item (on request)

Triggers (any of):
- User included `+gus`, `+wi`, `+ticket`, `gus wi`, `file a gus`,
  `create gus`, or `file ticket` in their original request.
- User picked option `(c)` in the "What's next?" menu.
- User explicitly says "file this in GUS" / "make a WI for that".

This step **applies to every analysis sub-skill**, not just one.
Whichever analysis the user most recently ran becomes the source.
Skip when:
- The most recent sub-skill has `html_eligible: false` AND nothing
  GUS-meaningful was produced (none ship today; flag is reserved).
- No analysis has run yet — refuse and ask for one first.

### Behavior

1. **Confirm scope** before doing anything else. Render this block and
   stop:

   ```
   About to file a GUS work item:

     Source analysis: <id> (run at <hh:mm> on this session)
     Session: <sessionId>
     Stage / env / org: <stage> / <env> / <org>
     Candidate title: <draft from analysis findings>

   I need:
     • Team name (required, e.g. "CC-Chatty (Shopper & Buyer Agents)")
     • Theme (optional — prefixes the title, e.g. "perf", "search-quality")

   Reply with: team=<name> theme=<tag>   (or just confirm to use the candidate title)
   ```

2. **HTML report is already on disk.** Step 9 ran automatically right
   after the analysis, so `.agents/artifacts/<sessionId>_<analysisId>.html`
   should exist. If it's missing for any reason (Step 9 failure, etc.),
   re-run the renderer now silently.

3. **Build the WI fields:**

   - **Title**: `[<theme>] <one-line problem statement>` (≤ 80 chars,
     theme optional). No requestId / sessionId in the title.
   - **`Type__c`**:
     - `Bug` if the source analysis reports `status != Success` rows or
       any single operation > 4 s.
     - `User Story` otherwise (forward-looking improvement).
   - **`Details__c`** (HTML, ≤ 2 KB) — see structure below.
   - **`Status__c`**: `New`.
   - **`Story_Points__c`**: leave blank for Bug; default `2` for User
     Story unless `suggested-improvements` named an L (5) / M (3) / S
     (2) effort estimate.
   - **Scrum Team**: resolved by `sfcli:gus` from the user's chosen
     team name. If the user gave CC-Chatty, the user's MEMORY.md
     defaults apply. For any other team, state explicitly that
     team-specific defaults need fresh resolution.
   - Everything else (assignee, product tag, sprint, validation-rule
     fields like `Found_in_Build__c` / `Impact__c` / `Frequency__c`)
     is `sfcli:gus`'s responsibility — that skill knows the user's
     MEMORY.md template and resolves the current sprint at runtime.

   **`Details__c` structure** (always include all four blocks):

   ```html
   <p><strong>Problem:</strong> <one-sentence statement with one
   quantitative observation, e.g. "Three SCAPI calls in a 30-second
   session each took 3.6–4.0 s, accounting for ~99% of
   B2CProductSearchAction time."></p>

   <p><strong>Why it matters:</strong> <one-sentence user / cost / data
   impact></p>

   <p><strong>Evidence:</strong> session
   <code>&lt;botSessionId&gt;</code>, requestIds
   <code>&lt;a, b, c&gt;</code>, <env>, <date>.
   <a href="<splunk-link>">Raw Splunk</a>.
   Full report attached as file.</p>

   <p><strong>Analysis output (from <code>&lt;sub-skill-id&gt;</code>):</strong></p>
   <blockquote>
     <!-- Paste the analysis prose here, converted to HTML.
          Strip the chat-side <details> wrappers — Salesforce HTML
          fields don't render <details>. Use <h4> for what was a <h2>,
          and so on.
          Keep ≤ 1.5 KB after stripping. If the analysis is longer,
          truncate the prose with "[full report attached as HTML]"
          and rely on the file attachment for the rest. -->
   </blockquote>
   ```

4. **Run the `sfcli:gus` write workflow.** Hand off the field map.
   That skill performs its own preview + confirmation per its core
   rules — do not skip its preview, even if you already showed the
   user the scope confirmation in step 1. (User confirms twice — once
   on scope+team, once on the full record. Worth it; GUS writes are
   sticky.)

5. **Attach the HTML report.** After the WI is created, get the
   `ADM_Work__c` record Id from the `sfcli:gus` response and run:

   ```bash
   ~/.claude/skills/shopper-agent-obs-hub-analyze/scripts/attach_html_to_gus.sh \
     <wi-record-id> \
     .agents/artifacts/<sessionId>_<analysisId>.html \
     "<analysis-label> — <sessionId>"
   ```

   The script:
   - Creates a `ContentVersion` with the file body (base64).
   - Resolves its `ContentDocumentId`.
   - Creates a `ContentDocumentLink` to the work item.
   - Returns the file's Salesforce URL.

   Surface the file URL alongside the W-number in the final
   confirmation.

   If the attach script fails (auth, permissions, network), the WI is
   already created — that's fine. Tell the user the WI Id, the failure
   reason, and how to retry the attach manually.

6. **Render the success block:**

   ```
   ✅ Created W-XXXXXXXX

     Title:  <final title>
     Team:   <team>
     Type:   <Bug | User Story>  (Story Points: <n> | Bug priority auto-set)
     Source: <sub-skill-id>
     WI:     https://gus.lightning.force.com/lightning/r/ADM_Work__c/<id>/view
     Attached: <html-file-url>

   Anything else to file from this session?
   ```

### GUS schema gotchas

- **Title field on `ADM_Work__c` is `Subject__c`, NOT `Subject`.**
  GUS is a custom-object app; almost every field has the `__c`
  suffix. The standard-object name `Subject` (Case, Task) does not
  apply here and will fail with `INVALID_FIELD: No such column
  'Subject' on sobject of type ADM_Work__c`.
- **Lookup fields on `ADM_Work__c` are `<Thing>__c`** (Id-typed),
  not `<Thing>__r.Id`. Examples: `Scrum_Team__c`, `Sprint__c`,
  `Assignee__c`, `Product_Tag__c`, `QA_Engineer__c`,
  `Product_Owner__c`, `Found_in_Build__c`, `Impact__c`,
  `Frequency__c`, `Epic__c`. Pass the 15- or 18-char Id directly.
- **`Story_Points__c` is a number** (not a string). Pass `2`, not
  `"2"`.
- **Sprint resolution is per-team:** filter by `Scrum_Team__c =
  '<team-id>'` and `Start_Date__c <= TODAY <= End_Date__c`. Don't
  rely on a `Team__r.Name` join — the lookup is to
  `ADM_Scrum_Team__c` and the filter syntax depends on the env.
- **Always verify with the schema describe** if a write fails
  with `INVALID_FIELD` before retrying — the field may exist under
  a different name.

### Rules

- **Always preview** the scope block (step 1) **and** let
  `sfcli:gus` show its own preview (step 4). Two confirmations. GUS
  writes can't be undone cleanly.
- **One WI per analysis output.** Each Step-10 invocation creates
  exactly one GUS work item, regardless of how many findings the
  analysis produced. For `suggested-improvements`, that means filing
  the **whole backlog** as a single WI — title summarizes the
  highest-priority item, `Details__c` lists every IMP-NN row with its
  tier and one-line rationale, and the full HTML attachment carries
  the experiment cards. Reasoning: GUS WIs are sticky, the team
  triages them one at a time anyway, and filing 8 separate WIs
  fragments context and clutters the backlog. If the user later wants
  individual WIs per IMP, they can re-invoke Step 10 with `+gus`
  pointed at a specific IMP-NN.
- **Always include the Splunk link** in `Details__c`. A WI without
  the raw-data link is hard to triage.
- **Always attach the HTML.** It's the readable artifact teammates
  will actually open. The Details__c HTML is the searchable summary;
  the file is the deep dive.
- **Don't propagate CC-Chatty defaults to other teams.** If the user
  named a team that isn't CC-Chatty, state that the user's
  MEMORY.md GUS template applies only to CC-Chatty and the other
  team's defaults need fresh resolution by `sfcli:gus`.
- **GUS auth failure → stop.** Don't try workarounds; point at
  `sfcli:gus`'s `workspace-auth.md`.
- **HTML attach failure does not roll back the WI.** Report the
  W-number and the attach error so the user can retry.

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
