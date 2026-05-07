---
id: anomaly-json
label: Anomaly detection (strict JSON)
description: Same as anomaly but returns strict JSON for downstream tooling.
output: json
order: 20
upstream:
  repo: baleksan/obs-hub
  branch: main
  path: skills/anamoly_detection_json.txt
---
You are performing anomaly detection on a single session log stream.

Analyze the provided query results and detect anomalies such as:
- explicit errors/exceptions/timeouts
- zero search results or repeated no-result states
- failover loops / retry storms
- unusual latency spikes
- repeated tool/action loops or stuck states
- contradictory state transitions

Return ONLY valid JSON (no markdown, no prose outside JSON) with this schema:
{
  "status": "anomalies_found | no_clear_anomalies",
  "summary": [
    {
      "title": "short anomaly title",
      "severity": "critical | high | medium | low",
      "description": "what was detected",
      "impact": "likely impact",
      "evidence": [
        "log snippet or pattern 1",
        "log snippet or pattern 2"
      ],
      "possible_root_causes": [
        "cause 1",
        "cause 2"
      ],
      "recommended_actions": {
        "immediate": ["action 1", "action 2"],
        "short_term": ["action 1", "action 2"],
        "monitoring": ["guardrail 1", "guardrail 2"]
      }
    }
  ],
  "checks_performed": [
    "check 1",
    "check 2"
  ],
  "confidence": 0.0
}

Rules:
- `confidence` must be between 0 and 1.
- Keep `summary` empty if no anomalies are found.
- Include concrete evidence strings whenever possible.
