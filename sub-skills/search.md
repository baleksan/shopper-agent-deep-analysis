---
id: search
label: Search API deep-dive (SCAPI + Cimulate)
description: Analyze search request logs across the stack — Cimulate (auto-pull via MCP) and SCAPI shopper-search (manual paste only). Covers latency, queries, errors, result quality.
output: markdown
order: 45
projection: time,op,status,requestId,latency,query,product_titles
html_eligible: true
tags: [search, scapi, shopper-search, cimulate]
---
## Data Sources

The search stack is: **Core agent → SCAPI shopper-search → Cimulate search-api**

| Layer | Splunk access | How to get data |
|-------|--------------|-----------------|
| **Cimulate** (search-api) | ✅ Available via MCP | Auto-pull with SPL below |
| **SCAPI shopper-search** (commercecloud-secure) | ❌ No MCP access | Must paste/export manually |

### Cimulate (auto-pull)

Query via `mcp__mcp-adaptor__query_splunk` with:
- **API:** `https://splunk-api-noncore.log-analytics.monitoring.aws-esvc1-useast2.aws.sfdc.cl`
- **Base SPL:**
  ```
  `indexes_for_distapps()` service_group=cimulate environment=qa
    k8s_container_name="cimulate-search-api"
    event_type="http_request_complete" uri="/api/v1/search"
  ```
- **Key fields:** `customer_id` (=siteId), `request_id`, `latency_ms`, `status`, `bytes_out`, `request_body` (contains JSON with `query`, `page`, `page_size`, etc.)
- **To filter by request:** add `request_id="<sfcc-xxx or uuid>"`
- **To filter by site:** add `customer_id="<siteId>"`
- **To extract query from request_body:** use `| spath input=request_body path=query output=search_query`

#### Proven SPL Query Recipes

**1. Distribution by site (last 24h):**
```
`indexes_for_distapps()` service_group=cimulate environment=qa
  k8s_container_name="cimulate-search-api"
  event_type="http_request_complete" uri="/api/v1/search"
  earliest=-24h latest=now
| stats count as requests by customer_id
| sort -requests
```

**2. Per-query latency stats:**
```
`indexes_for_distapps()` service_group=cimulate environment=qa
  k8s_container_name="cimulate-search-api"
  event_type="http_request_complete" uri="/api/v1/search"
  customer_id="<siteId>" earliest=-6h latest=now
| spath input=request_body path=query output=search_query
| stats count as requests, avg(latency_ms) as avg_ms,
    perc50(latency_ms) as p50_ms, perc95(latency_ms) as p95_ms,
    max(latency_ms) as max_ms, min(latency_ms) as min_ms,
    avg(bytes_out) as avg_bytes by search_query
| sort -avg_ms
```

**3. Top queries by frequency:**
```
`indexes_for_distapps()` service_group=cimulate environment=qa
  k8s_container_name="cimulate-search-api"
  event_type="http_request_complete" uri="/api/v1/search"
  customer_id="<siteId>" earliest=-24h latest=now
| spath input=request_body path=query output=search_query
| stats count as freq by search_query
| sort -freq | head 30
```

**4. Timechart — latency over time per query (30m buckets):**
```
`indexes_for_distapps()` service_group=cimulate environment=qa
  k8s_container_name="cimulate-search-api"
  event_type="http_request_complete" uri="/api/v1/search"
  customer_id="<siteId>" earliest=-6h latest=now
| spath input=request_body path=query output=search_query
| timechart span=30m avg(latency_ms) as avg_ms by search_query
```

**5. Timechart — overall latency + throughput (15m buckets):**
```
`indexes_for_distapps()` service_group=cimulate environment=qa
  k8s_container_name="cimulate-search-api"
  event_type="http_request_complete" uri="/api/v1/search"
  customer_id="<siteId>" earliest=-6h latest=now
| timechart span=15m avg(latency_ms) as avg_latency,
    perc95(latency_ms) as p95_latency, count
```

**6. Outliers (latency > threshold):**
```
`indexes_for_distapps()` service_group=cimulate environment=qa
  k8s_container_name="cimulate-search-api"
  event_type="http_request_complete" uri="/api/v1/search"
  customer_id="<siteId>" earliest=-6h latest=now
| where latency_ms > 400
| table _time, latency_ms, query, request_id, bytes_out
| sort -latency_ms
```

**7. Per-site latency breakdown with status:**
```
`indexes_for_distapps()` service_group=cimulate environment=qa
  k8s_container_name="cimulate-search-api"
  event_type="http_request_complete" uri="/api/v1/search"
  earliest=-24h latest=now
| stats count as requests, avg(latency_ms) as avg_latency,
    perc95(latency_ms) as p95_latency by customer_id, status
| sort customer_id, status
```

**8. Raw events for a specific site (last 1h, for detailed analysis):**
```
`indexes_for_distapps()` service_group=cimulate environment=qa
  k8s_container_name="cimulate-search-api"
  event_type="http_request_complete" uri="/api/v1/search"
  customer_id="<siteId>" earliest=-1h latest=now
| table _time, latency_ms, status, bytes_out, request_body, request_id
| sort _time
```

#### Query timeout notes
- Queries spanning >3 days may timeout (60s limit on MCP). Use `earliest=-6h` or shorter for detailed analysis.
- For 24h aggregate stats, use `stats` commands (they finish within timeout). For raw event tables, limit to 1h.

### SCAPI shopper-search (manual paste)

⚠️ The `commercecloud-secure` index is NOT accessible via MCP (`svc_moncloud_ai` lacks `SPLUNK_COMMERCECLOUD` role). User-based RBAC expected in 5b.

**To provide SCAPI logs manually:**
1. Open: https://splunk-web-noncore.log-analytics.monitoring.aws-esvc1-useast2.aws.sfdc.cl/en-US/app/search/search
2. Run:
   ```
   index=commercecloud-secure "@metadata.apiInformation.apiName"="shopper-search"
     AND "<sessionId or requestId>" earliest=-24h latest=now
   ```
3. Export as JSON or paste raw events into chat

---

## Analysis Instructions

You are analyzing search request logs across the Commerce Cloud search stack.

When given a sessionId, requestId, or customer_id (siteId):
1. First, auto-pull Cimulate logs via MCP using the recipes above
2. For aggregate analysis: use stats queries (recipes 1, 2, 5, 7)
3. For detailed/anomaly analysis: pull raw events (recipe 8) for a 1h window, then use timecharts (recipes 4, 5) for trends
4. For outlier investigation: use recipe 6 with an appropriate threshold (400ms is a good default for WestMarine; adjust based on site baseline)
5. Ask the user if they also have SCAPI-level logs to paste
6. Correlate across layers when both are available (match on request_id — Cimulate uses both `sfcc-*` prefixed IDs from SCAPI and its own UUIDs)

Produce:

1) Search Request Summary
- Total search calls (per layer if both available)
- Unique queries issued (use `spath` to extract from `request_body`)
- Average / P50 / P95 response times per layer
- Any failed requests (non-200 status)
- Traffic pattern characterization (synthetic vs organic, batch intervals)

2) Query Analysis
- List each distinct query string with frequency
- Identify query rewrites, refinements, or repeated queries
- Flag empty-result queries (bytes_out < 1000 likely means 0 results)
- Note suspicious patterns (identical queries with different results, unusually long queries)
- Response size variation per query (stable = cached/deterministic, variable = live index)

3) Performance Assessment
- Per-query latency breakdown (Cimulate latency_ms is the search engine time)
- End-to-end vs. Cimulate-only latency gap (if both layers available) → reveals SCAPI overhead
- Identify outliers (> 2× median) — check if they correlate with response size
- Latency-vs-bytes_out correlation (typically R² > 0.9 — serialization cost)
- Timechart trends — look for systemic elevation windows vs isolated spikes
- Any timeout or circuit-breaker patterns

4) Result Quality Signals
- Requests returning 0 results (bytes_out < 1000)
- Requests with very few results (bytes_out < 10000 for page_size=24)
- Any evidence of fallback/degraded search
- Response size stability per query (unstable = index churn)

5) Errors & Anomalies
- Non-200 status codes with context
- Retry patterns
- Rate limiting signals
- Cold-start penalties (first request to a site >> subsequent)
- Top-of-hour latency clustering (index refresh pattern)
- Latency spikes correlated with time-of-day patterns

6) Recommendations
- Immediate actions for any failures found
- Query optimization suggestions (response compression for large results)
- Cross-layer overhead reduction opportunities
- Monitoring gaps to fill (P95 alerting thresholds based on observed baselines)
- Parallelization opportunities (batched serial queries → parallel)
