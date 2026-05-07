---
description: Run a predefined obs-hub analysis (anomaly, latency, quality, summary, etc.) on a Shopper Agent session's Splunk logs. Add `+html` to also export a shareable HTML report.
argument-hint: <sessionId> [stage] [analysis] [+html]
---

Use the **shopper-agent-obs-hub-analyze** skill to handle this request.

User input: $ARGUMENTS

Routing logic (apply in order):

1. **Empty input** → Show short help:
   - `/shopper-agent-obs-hub-analyze <sessionId>` — pull `core` stage, show analysis menu
   - `/shopper-agent-obs-hub-analyze <sessionId> <stage>` — pull `<stage>`, show menu
   - `/shopper-agent-obs-hub-analyze <sessionId> <stage> <analysis>` — pull and run directly
   - Stages: `core` (default), `scrt2`, `e2e`, `ux`
   - Analyses: discovered from `sub-skills/*.md` (run with no analysis arg to see the live menu), or `all`
   Then stop.

2. **First token matches a UUID** (`[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`) → that's the `sessionId`.
   - Second token (if present and one of `core | scrt2 | e2e | ux`) → `stage`.
   - Third token (if present): match it against the `id` field of any
     `sub-skills/*.md` (case-insensitive). If it matches → `analysis`.
     `all` is also valid. If it doesn't match anything, treat it as
     natural-language and let the SKILL.md handle resolution.
   - Any token equal to `+html`, `html`, `+report`, or `+share` → set
     the **HTML export flag**. After Step 6 (rendering the analysis in
     chat) and Step 7-8 (links + what's-next), automatically run
     Step 9 (HTML export) without waiting for the user to pick (c).

3. **Input doesn't start with a UUID** → pass the whole string to the skill as a natural-language request and let the SKILL.md triggers handle it.

Follow all the rules in `SKILL.md`. The three **mandatory** behaviors:

1. **Menu on entry.** When the user did not name an analysis (or `all`),
   render the numbered analysis menu from SKILL.md Step 3 — including
   one-line descriptions — and wait for their pick. Do not silently
   default.
2. **Splunk Links Used (every time).** End every report with the
   `## 🔗 Splunk Links Used` section listing each query you ran as a
   clickable web URL with time range and row-count note. Skipped queries
   get a placeholder bullet.
3. **What's next? (every time).** After the Splunk-links section, render
   the Step 8 follow-up menu offering `(a)` continue with another
   sub-skill on the same data, `(b)` start a new analysis on a
   different session, or `(c)` export the most recent analysis as a
   shareable HTML report. Mark already-run sub-skills `(✓ already run)`.

Plus the standard rules:
- Verify the sister skill `shopper-agent-splunk-query` and the `query_splunk` MCP tool are available before doing anything else.
- Load prompt files verbatim from `prompts/`. Never paraphrase them.
- Use `raw` output from the sister skill so the LLM sees real log lines.
- For `_json` analyses, validate the response is parseable JSON; retry once if not.
- Render the standard report header (sessionId, stage, env/org, time range, analysis, row count) before the analysis output.
- Cache pulled rows under `.agents/artifacts/<sessionId>_raw.json` so option (a) of the "what's next" menu can reuse them without re-querying Splunk.
