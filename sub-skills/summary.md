---
id: summary
label: Chronological timeline + summary (JSON)
description: Chronological timeline + key turning points + final summary (JSON).
output: json
order: 60
upstream:
  repo: baleksan/obs-hub
  branch: main
  path: skills/summarization_json.txt
---
You are summarizing a single session log into a clear timeline.

Analyze the provided query results and produce a concise sequence of events.

Return ONLY valid JSON (no markdown, no prose outside JSON) using this schema:
{
  "session_overview": {
    "session_id": "string or unknown",
    "status": "completed | failed | partial | unknown",
    "start_signal": "first meaningful event",
    "end_signal": "last meaningful event"
  },
  "event_sequence": [
    {
      "step": 1,
      "phase": "short phase label",
      "timestamp_hint": "timestamp string if available, otherwise null",
      "event": "what happened",
      "details": "important context",
      "outcome": "success | failure | unknown"
    }
  ],
  "key_turning_points": [
    "point 1",
    "point 2"
  ],
  "errors_or_anomalies": [
    {
      "type": "error | timeout | retry_loop | zero_results | other",
      "evidence": "short evidence text",
      "impact": "impact summary"
    }
  ],
  "final_summary": "2-4 sentence plain-language summary",
  "confidence": 0.0
}

Rules:
- Keep `event_sequence` in chronological order.
- Use `step` values starting at 1 and increment by 1.
- Include only meaningful events; avoid noise.
- If no errors are present, return an empty `errors_or_anomalies` array.
- `confidence` must be between 0 and 1.
