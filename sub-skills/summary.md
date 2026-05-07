---
id: summary
label: Summary (single session OR time interval)
description: Plain-English summary with sub-headings. Works for one session, OR aggregated over a time window (e.g. all sessions for a customer over a day).
output: markdown
order: 5
tags: [synthesis, narrative]
---

You are summarizing Shopper Agent activity for a non-technical audience.

There are **two modes**, decided by what the parent skill passed in:

- **Single-session mode** — the input is one session's rows (16-200 rows
  for a single conversation). The narrative covers what *that user*
  experienced.
- **Interval mode** — the input is many sessions aggregated over a time
  window (e.g. "all `nto` sessions for 2026-05-05" or "SharkNinja last
  6 hours"). The narrative covers what the *cohort* experienced.

Detect which mode you're in by checking whether the rows span ≤ 1
distinct `botSessionId` (single-session) or many (interval).

# Output structure

Render this exact set of H2 sections, in this order. Skip a section
cleanly if there's nothing meaningful to say — do not pad.

## TL;DR

**One paragraph, 2-4 sentences.** Plain language, no jargon, no
metric names. The kind of summary you could read aloud to a PM.

For single-session: what did the user ask, what happened, did it
work, was it slow.

For interval: how many sessions, what the typical experience looked
like, biggest standout (good or bad).

## What happened

3-6 bullets walking through the meaningful events in chronological
order (single-session) or representative slice (interval). Use
plain English, not log line excerpts.

For interval mode, prefer "across the window..." framing:
- "Across the window, 142 sessions ran. The median session had 3
  search turns and lasted 38 seconds."
- "82% of sessions completed cleanly. The remaining 18% were split
  between abandons (user disconnected) and SCAPI errors."

## What worked well

3-5 bullets on positive signals. State the evidence concisely.
Examples:
- "All token fetches succeeded on the first attempt."
- "Search responses returned in under 4 seconds."
- "No retry storms, no auth failures."

If nothing genuinely worked well, write *"Nothing notable on the
positive side"* and explain.

## What was rough

3-5 bullets on negative signals. Same evidence-first style.
Examples:
- "The query 'men's DWR pants' returned no products that explicitly
  mention DWR — the user got generic men's pants instead."
- "A single SCAPI call dominates each search turn at ~3.8s; that's
  ~99% of the response time."

If nothing was rough, write *"The session(s) ran cleanly"* — don't
manufacture issues.

## Notable specifics

A short table of concrete data points the reader will want to cite or
look up later. Include only the rows that are present in the data —
omit empty rows entirely.

| Field | Value |
|---|---|
| Session(s) | `<botSessionId>` *(single)* OR `<count> sessions across <range>` *(interval)* |
| User queries | `<verbatim list of distinct queries>` |
| Sites / orgs | `<deduped list>` |
| Total / median wall-clock | `<duration>` |
| Failure count | `<n>` |
| Top operation by latency | `<op name> @ <ms>` |

## Who should read this

A one-line audience hint:
- *"PM / customer success — clean handoff doc."*
- *"On-call — investigate within 24h."*
- *"Engineering — schedule a perf deep-dive."*

# Rules

- **Plain English first.** Engineers will read this; PMs and CS will
  also read this. No `phase.queryUnderstanding.durationMs` jargon
  unless it appears in the "Notable specifics" table.
- **Mode visible up-front.** Open the TL;DR with "Single session..."
  or "Across N sessions..." so the reader knows immediately.
- **Quote user queries verbatim** when there are ≤ 5 distinct ones.
  For interval mode with many queries, give the top 3 by frequency
  + a count of the long tail.
- **No recommendations here.** This is a "what happened" report, not a
  "what should we do" report. The `suggested-improvements` sub-skill
  handles that. If the reader asks "so what?" you can point them
  there.
- **Soft cap**: ≤ 350 words of prose total. The "Notable specifics"
  table doesn't count toward the cap.
- **No errors / no findings is a valid output.** A clean session
  produces a 4-line TL;DR, a single bullet under "What worked
  well", and the table. Don't artificially inflate.
