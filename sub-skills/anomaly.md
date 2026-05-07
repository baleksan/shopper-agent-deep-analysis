---
id: anomaly
label: Anomaly detection (errors, retry loops, latency spikes, stuck states)
description: Find errors, retry loops, latency spikes, stuck states. Markdown report.
output: markdown
order: 10
upstream:
  repo: baleksan/obs-hub
  branch: main
  path: skills/anamoly_detection.txt
---
You are performing anomaly detection on a single session log stream.

Analyze the provided query results and identify anomalies such as:
- explicit errors/exceptions/timeouts
- zero search results or repeated no-result states
- failover loops or repeated retry/fallback cycles
- unusual latency spikes or repeated slow operations
- repeated tool/action invocation patterns that indicate stuck behavior
- contradictory state transitions in the same session

Return your output in this structure:

1) Anomaly Summary
- 3-8 bullet points of the most important anomalies found.

2) Evidence
- For each anomaly, include concrete log snippets or message patterns that support it.

3) Likely Impact
- Explain probable user/system impact for each anomaly.

4) Most Likely Root Causes
- Prioritized list of likely causes.

5) Recommended Next Actions
- Immediate actions (now)
- Short-term fixes (this sprint)
- Monitoring/guardrails to prevent recurrence

If no anomalies are found, explicitly say "No clear anomalies detected" and explain what checks were performed.
