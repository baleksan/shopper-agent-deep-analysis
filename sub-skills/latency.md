---
id: latency
label: Per-step latency + slowdown analysis
description: Per-step duration table, slowdowns, missing/skipped steps, root causes.
output: markdown
order: 30
projection: time,op,status,requestId,latency,cache
upstream:
  repo: baleksan/obs-hub
  branch: main
  path: skills/measure_latency.txt
---
You are measuring per-step latency and execution completeness for a single session log stream.

Analyze the provided query results and determine:
- each meaningful step/phase that occurred in chronological order
- duration or latency hints for each step when timestamps are available
- perceived slowdowns (including long gaps between expected transitions)
- anomalies such as retries, stalls, repeated loops, timeout patterns, and contradictory timing
- steps that were expected but were not executed

Return your output in this structure:

1) Step Duration Table
- For each detected step, include:
  - step name
  - start signal
  - end signal
  - observed duration (or "unknown")
  - status: success | failure | partial | unknown

2) Slowdowns and Anomalies
- List any perceived slowdowns or latency anomalies.
- Include concrete evidence for each finding.

3) Missing or Skipped Steps
- Identify steps that appear to be expected but not executed.
- Explain why they are considered missing.

4) Probable Root Causes
- Prioritize likely causes for slowdowns/anomalies/missing steps.

5) Recommended Actions
- Immediate actions (now)
- Short-term fixes (this sprint)
- Monitoring and alert rules (to catch recurrence)

If duration cannot be computed exactly, estimate relative slowness from log ordering and timing clues, and clearly mark uncertainty.
