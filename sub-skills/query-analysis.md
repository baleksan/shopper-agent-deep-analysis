---
id: query-analysis
label: Inspect user query for anomalies
description: Lightweight check of the user's query for anomalies (markdown table).
output: markdown
order: 70
projection: time,op,status,query
upstream:
  repo: baleksan/obs-hub
  branch: main
  path: skills/query_analysis.txt
---
You job is to analyze the input query and detect any anamolies. report in a table