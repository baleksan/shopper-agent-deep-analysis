#!/usr/bin/env python3
"""
project_rows.py — emit a slimmed, sub-skill-specific view of cached
Splunk rows, suitable for feeding to the analysis LLM.

Input:  a JSON file produced by the parent skill, of the shape
          [{"_time": "...", "_raw": "<backtick log line>"}, ...]
Output: a text file with one human-readable line per row, containing
        only the fields requested via --include.

Why: the cached _raw lines are 30-50 KB each because they include the
full SCAPI ProductSearchResponse (10 hits × image groups, prices,
URLs). Most analyses don't need that. Projecting down to relevant
fields cuts the LLM's input by 5-10x with no accuracy loss when the
projection is chosen correctly.

The projection is declarative: each sub-skill's frontmatter declares
which `include` tags it wants. This script doesn't decide what each
sub-skill needs — it just executes the projection.

Available include tags (always-on tags `time`, `op`, `status`,
`requestId` are emitted regardless):

  latency       top_latency_ms + stages dict + phase.search.durationMs
                + phase.queryUnderstanding.durationMs
  query         userQuery
  product_titles  list of (productName, master-product-prefix) for each hit
  product_full  full hit payload incl. images/prices (use sparingly)
  followup_meta suggestionCount, classificationType, llmGenerationTimeMs,
                CONTEXT_KEY_FALLBACK_USED, shoppingContextAvailable,
                productCount
  scapi_meta    searchCmdtCacheHit, queryFacets, scapiSearch_*
                productPageUrlsLoaded, phase.search.productCount
  cache         just searchCmdtCacheHit
  site          siteId, botSessionId
  errors_context last 200 chars of _raw when status is not Success

Usage:
  project_rows.py \\
    --rows-file <input.json> \\
    --include time,op,status,latency,query \\
    --out <output.txt>
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

OP_RE = re.compile(
    r'`(?P<service>ECOMShopperAgent|LLMGateway|EcomConcierge|Storefront|Concierge|GuidedShoppingAgent)`'
    r'(?P<operation>[^`]*)`(?P<latency>\d+)'
)
STATUS_RE = re.compile(r'`(?P<status>Success|Failure|Error|N/A)```')
JSON_BLOB_RE = re.compile(r'```(\{.+?\})```', re.DOTALL)
REQ_RE = re.compile(r'^b2usg`[^`]*`([^`]*)`')


def parse_row(r: dict) -> dict:
    """Extract a flat dict of useful fields from a raw row."""
    out = dict(r)
    raw = r.get("_raw", "") or ""
    out["_raw_excerpt_200"] = raw[-200:] if len(raw) > 200 else raw

    m = REQ_RE.match(raw)
    if m:
        out["requestId"] = m.group(1)

    m = OP_RE.search(raw)
    if m:
        out["service"] = m.group("service")
        out["operation"] = m.group("operation")
        try:
            out["top_latency_ms"] = int(m.group("latency"))
        except ValueError:
            pass

    m = STATUS_RE.search(raw)
    if m:
        out["status"] = m.group("status")

    blob = {}
    m = JSON_BLOB_RE.search(raw)
    if m:
        try:
            blob = json.loads(m.group(1))
        except json.JSONDecodeError:
            blob = {}
    out["_blob"] = blob
    return out


def render_titles(blob: dict, max_titles: int = 10) -> str:
    """Compact representation of the top-N product hits: name + master prefix."""
    psr = blob.get("ProductSearchResponse")
    if not psr:
        return ""
    m = re.match(r'\[Status:\s*\d+\.\s*Response:\s*(\{.*\})\]?\s*$', psr, re.DOTALL)
    if not m:
        return ""
    try:
        sr = json.loads(m.group(1))
    except json.JSONDecodeError:
        return ""
    hits = sr.get("hits", [])[:max_titles]
    items = []
    for i, h in enumerate(hits, 1):
        name = (h.get("productName") or "?").strip()
        pid = h.get("productId") or ""
        family = pid[:7] if pid else ""
        items.append(f"#{i} {name!r} (family={family})")
    total = sr.get("total")
    suffix = f" (catalog total={total})" if total else ""
    return f"[{', '.join(items)}]{suffix}"


def render_row_line(parsed: dict, include: set[str]) -> str:
    """Build a one-line human-readable view for the row, per include set."""
    blob = parsed.get("_blob", {}) or {}
    parts = [parsed.get("_time", "")]
    parts.append(parsed.get("operation") or "?")
    parts.append(parsed.get("status") or "?")
    if "requestId" in include:
        parts.append(f"req={(parsed.get('requestId') or '')[:24]}")

    if "latency" in include:
        lat = parsed.get("top_latency_ms")
        stages = blob.get("operationStagesWithExecutionTime") or {}
        ph_s = blob.get("phase.search.durationMs")
        ph_qu = blob.get("phase.queryUnderstanding.durationMs")
        bits = []
        if lat is not None:
            bits.append(f"top={lat}ms")
        if stages:
            bits.append("stages={" + ", ".join(f"{k}={v}" for k, v in stages.items()) + "}")
        if ph_s is not None:
            bits.append(f"phase.search.ms={ph_s}")
        if ph_qu is not None:
            bits.append(f"phase.qu.ms={ph_qu}")
        if bits:
            parts.append(" | ".join(bits))

    if "query" in include:
        q = blob.get("userQuery")
        if q:
            parts.append(f'q="{q}"')

    if "product_titles" in include:
        titles = render_titles(blob)
        if titles:
            parts.append(f"hits={titles}")

    if "product_full" in include:
        # When the user really wants raw — fall back to a truncated _raw.
        psr = blob.get("ProductSearchResponse")
        if psr:
            parts.append(f"productSearchResponse={psr[:1500]}{'...[truncated]' if len(psr) > 1500 else ''}")

    if "followup_meta" in include:
        keys = [
            "suggestionCount", "classificationType", "llmGenerationTimeMs",
            "CONTEXT_KEY_FALLBACK_USED", "shoppingContextAvailable", "productCount",
        ]
        sub = {k: blob[k] for k in keys if k in blob}
        if sub:
            parts.append("followup=" + json.dumps(sub, separators=(",", "=")))

    if "scapi_meta" in include:
        keys = [
            "searchCmdtCacheHit", "queryFacets", "phase.search.productCount",
            "scapiSearch_productPageUrlsLoaded", "scapiSearch_productDetailsRequested",
            "scapiSearch_productDetailsReturned", "searchProviderUsed",
        ]
        sub = {k: blob[k] for k in keys if k in blob}
        if sub:
            parts.append("scapi=" + json.dumps(sub, separators=(",", "=")))

    if "cache" in include:
        chr_ = blob.get("searchCmdtCacheHit")
        if chr_ is not None:
            parts.append(f"cache_hit={chr_}")

    if "site" in include:
        site = blob.get("siteId")
        bsid = blob.get("botSessionId")
        bits = []
        if site:
            bits.append(f"siteId={site}")
        if bsid:
            bits.append(f"botSessionId={bsid[:13]}...")
        if bits:
            parts.append(" ".join(bits))

    if "errors_context" in include:
        status = (parsed.get("status") or "").lower()
        if status not in ("success", "1", "n/a"):
            parts.append(f"raw_tail={parsed.get('_raw_excerpt_200', '')!r}")

    return " | ".join(p for p in parts if p)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--rows-file", required=True)
    p.add_argument("--include", required=True,
                   help="Comma-separated include tags. The always-on tags are "
                        "time/op/status (and requestId is added automatically when 'latency' is included).")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    include = set(t.strip() for t in args.include.split(",") if t.strip())
    if "latency" in include:
        include.add("requestId")

    rows = json.loads(Path(args.rows_file).read_text(encoding="utf-8"))
    parsed = [parse_row(r) for r in rows]
    lines = [render_row_line(p, include) for p in parsed]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(lines) + "\n"
    out_path.write_text(body, encoding="utf-8")

    in_size = Path(args.rows_file).stat().st_size
    out_size = out_path.stat().st_size
    pct = round(100 * out_size / in_size, 1) if in_size else 0
    print(f"✅ Projected {len(rows)} rows: {in_size:,} → {out_size:,} bytes ({pct}% of original)")
    print(f"   Include tags: {sorted(include)}")
    print(f"   Output: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
