---
id: create-gus-wi
label: Create a GUS work item from this session's findings
description: Turn the most recent analysis (or session anomalies) into a GUS work item. Asks for team name, with optional theme. Delegates to sfcli:gus.
output: markdown
order: 80
tags: [action, gus]
html_eligible: false
---

You are creating a GUS work item from the analysis output(s) of this
session. **You do not author the WI body from scratch** — you draw on
what's already been produced (anomaly findings, latency hotspots,
quality gaps, suggested-improvements backlog). You delegate the actual
write to the `sfcli:gus` skill.

# Required inputs

Before doing anything, the parent skill must pass:

1. **Team name** (required) — e.g. *"CC-Chatty (Shopper & Buyer Agents)"*,
   *"Cimulate"*, *"SCAPI"*. Used as the Scrum Team. **Always ask the
   user for this** unless they named it in the request. Don't guess
   from the session.
2. **Theme** (optional) — a short tag the user wants on the WI to
   bundle related improvements (e.g. *"perf"*, *"search-quality"*,
   *"P0-instrumentation"*). If provided, prefix the WI title with
   `[<theme>] `.

# Source material (in priority order)

Use whichever exists in this session, in this order:

1. **`suggested-improvements` output** — if present, each `IMP-NN`
   item is already a candidate WI. Ask the user which one(s) to file.
2. **`anomaly` findings** — convert the highest-severity finding to a
   single WI.
3. **`latency` slowdowns** — convert the dominant bottleneck.
4. **`quality` recommendations** — convert the top "Immediate" item.
5. **No prior analysis** — refuse and ask the user to run an analysis
   first. WIs filed without grounding evidence are noise.

# Workflow

## Step 1 — Confirm scope

Render this confirmation block and **stop**:

```
About to create a GUS work item:

  Team: <team-name>
  Theme: <theme or "(none)">
  Source: <which sub-skill output is being converted>
  Candidate title: <draft title>

Reply 'yes' to proceed, or edit any field.
```

Do NOT skip this confirmation, even if the user said "just file it" —
GUS writes are sticky and need a preview.

## Step 2 — Resolve team-specific defaults

Once confirmed, run the `sfcli:gus` write workflow. That skill knows
how to:
- Resolve the current sprint for the chosen team at runtime.
- Apply the user's MEMORY.md GUS template (Type=User Story,
  Story_Points=2, etc. — see
  `~/.claude/projects/-Users-baleksandrovsky/memory/gus_wi_template.md`).
- Look up the team's required validation-rule fields
  (Found_in_Build, Impact, Frequency for CC-Chatty etc.).
- Honor the user's defaults (assignee, product tag, QA, PO).

If the user's team is not CC-Chatty, the team defaults from MEMORY.md
**do not apply** — `sfcli:gus` will need to resolve fresh team
defaults. State this explicitly to the user.

## Step 3 — Author the WI body

Build the WI fields. Title and Details are the only ones this skill
shapes; everything else comes from team defaults.

### Title format

```
<theme prefix> <one-line problem statement>
```

Examples:
- `[perf] SCAPI HybridCallSCAPI dominates Shopper Agent search turns at ~3.8s`
- `[search-quality] Top-10 product lists 50% duplicated for nto storefront`
- `Investigate B2CProductSearchAction double-logging — 2 rows per request`

Caps:
- ≤ 80 chars including the theme prefix.
- No requestId / sessionId in the title — those go in Details.
- No marketing language ("epic perf win"). State the problem.

### Details (HTML, short)

Two-paragraph HTML, modeled on the user's MEMORY.md template style:

```html
<p><strong>Problem:</strong> <one-sentence problem statement with the
quantitative observation (e.g. "Three independent SCAPI calls in a
30-second session each took 3.6–4.0 s, accounting for ~99% of
B2CProductSearchAction time.").</strong></p>

<p><strong>Why it matters:</strong> <one-sentence impact — user-facing
latency, cost, data-quality, etc.>. <strong>Evidence:</strong> session
<code>&lt;botSessionId&gt;</code>, requestIds <code>&lt;a, b, c&gt;</code>,
preprod, <date>. See <a href="<splunk-link>">raw Splunk</a>.</p>
```

Rules for the Details block:
- Always link the Splunk web URL from the source analysis's "Splunk
  Links Used" section. The reader will click it.
- Always cite at least one concrete number (latency, count, %).
- Always cite the session ID + requestIds inline so the WI is
  self-contained.
- If the source was `suggested-improvements`, also paste the
  experiment hypothesis as a third `<p>` — this is how the team
  decides whether to ship-then-test or design an experiment first.
- ≤ 400 chars total HTML (excluding tags). The template file warns
  about long Details.

### Other fields

Pass to `sfcli:gus`:
- `Scrum Team` — the user-supplied team name (resolve to its Salesforce
  ID via the GUS skill).
- `Type__c` — `User Story` if it's a forward-looking improvement.
  `Bug` if it's a confirmed regression with user-visible impact.
  Decide from the source: `anomaly`/`latency` outputs with status
  failures or > 4s latency = Bug; everything else = User Story.
- `Story_Points__c` — leave blank if Bug; default to 2 for User Story
  (override if effort estimate from `suggested-improvements` says
  L → 5, M → 3, S → 2).
- `Status__c` — `New`.
- Everything else — let the user's MEMORY.md template + the
  `sfcli:gus` write workflow fill in.

## Step 4 — Preview

Before the actual write, render the `sfcli:gus` write preview block
(it's already required by that skill's core rules). Wait for
confirmation.

## Step 5 — File and report

After `sfcli:gus` returns the W-number:

```
✅ Created W-XXXXXXXX

  Title: <final title>
  Team:  <team>
  Type:  <type>  (Story Points: <n> | Bug: priority auto-set)
  Link:  https://gus.lightning.force.com/lightning/r/ADM_Work__c/<id>/view
  Source: <which sub-skill output>

Anything else to file from this session?
```

# Rules

- **One WI per call.** Even if `suggested-improvements` produced 6
  items, file them one at a time. The user must explicitly pick.
- **Never bulk-file from `all-remaining`.** Refuse and explain.
- **Always preview before write** (per `sfcli:gus` core rules).
- **Always include the Splunk web URL in Details.** A WI without a
  link to raw evidence is hard to triage.
- **No HTML export for this sub-skill** (`html_eligible: false`).
  A GUS write is an action, not a report.
- **If GUS auth is broken**, stop and point the user at
  `sfcli:gus` workspace-auth troubleshooting; do not attempt
  workarounds.
- **If the user's chosen team is not in the user's MEMORY.md
  defaults**, say so. Don't silently apply CC-Chatty defaults to
  another team's WI.
