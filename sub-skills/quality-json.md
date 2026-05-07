---
id: quality-json
label: Search quality (strict JSON)
description: Same as quality but returns strict JSON.
output: json
order: 50
upstream:
  repo: baleksan/obs-hub
  branch: main
  path: skills/quality_assesment_json.txt
---
You are performing search quality assessment for a single session log stream.

Evaluate:
1) query-to-results accuracy
2) follow-up suggestion quality
3) ranking quality using NDCG

Use ESCI-style graded relevance for result quality judgments:
- E = Exact
- S = Substitute
- C = Complement
- I = Irrelevant

Return ONLY valid JSON (no markdown, no prose outside JSON) using this schema:
{
  "assessment_meta": {
    "scope": "single_session | multi_session | unknown",
    "assumptions": [
      "assumption 1",
      "assumption 2"
    ],
    "data_gaps": [
      "missing field 1",
      "missing field 2"
    ],
    "confidence": 0.0
  },
  "executive_summary": [
    "key finding 1",
    "key finding 2"
  ],
  "query_result_assessments": [
    {
      "query_text": "string",
      "session_id": "string or unknown",
      "result_set_id": "string or derived label",
      "esci_distribution": {
        "E": 0,
        "S": 0,
        "C": 0,
        "I": 0
      },
      "top_result_labels": [
        {
          "rank": 1,
          "result_ref": "id/title/snippet",
          "esci_label": "E | S | C | I",
          "graded_relevance": 0,
          "reason": "short justification"
        }
      ],
      "query_accuracy_score": 0.0,
      "evidence": [
        "evidence snippet 1",
        "evidence snippet 2"
      ]
    }
  ],
  "followup_suggestion_assessments": [
    {
      "query_text": "string",
      "suggestions": [
        "suggestion 1",
        "suggestion 2"
      ],
      "quality_dimensions": {
        "relevance": 0.0,
        "diversity": 0.0,
        "specificity": 0.0,
        "actionability": 0.0
      },
      "suggestion_quality_score": 0.0,
      "issues": [
        "off-topic",
        "too broad"
      ],
      "evidence": [
        "evidence snippet"
      ]
    }
  ],
  "ranking_metrics": [
    {
      "query_text": "string",
      "result_set_id": "string or derived label",
      "k_values": [5, 10],
      "ndcg_at_5": 0.0,
      "ndcg_at_10": 0.0,
      "ideal_ranking_basis": "how ideal ranking was derived",
      "notes": "assumptions or estimation method"
    }
  ],
  "outliers": {
    "high_performers": [
      {
        "query_text": "string",
        "result_set_id": "string",
        "overall_score": 0.0,
        "why_high": "reason"
      }
    ],
    "low_performers": [
      {
        "query_text": "string",
        "result_set_id": "string",
        "overall_score": 0.0,
        "why_low": "reason",
        "likely_root_causes": [
          "cause 1",
          "cause 2"
        ]
      }
    ]
  },
  "aggregate_scores": {
    "query_results_accuracy_score": 0.0,
    "followup_suggestion_quality_score": 0.0,
    "overall_search_quality_score": 0.0
  },
  "recommendations": {
    "immediate": [
      "action 1",
      "action 2"
    ],
    "short_term": [
      "action 1",
      "action 2"
    ],
    "monitoring": [
      "metric/threshold 1",
      "metric/threshold 2"
    ]
  }
}

Rules:
- All score fields are numeric in range 0-100 except `confidence` (0-1).
- If exact NDCG cannot be computed, provide a defensible estimate and explain in `notes`.
- `graded_relevance` should be 0-3 where possible (e.g. E=3, S=2, C=1, I=0).
- Provide at least one item in `outliers.high_performers` and one in `outliers.low_performers` when data permits.
- Keep JSON valid and parseable.
