#!/usr/bin/env python3
"""
render_html.py — render a self-contained shareable HTML report.

Reads:
  - the analysis output (markdown or JSON, from --analysis-file)
  - the Splunk rows used (raw _time + _raw, from --rows-file)
  - session metadata (from --meta-file)

Emits a single HTML file that:
  - Renders the analysis prose / JSON nicely (marked.js for md, pretty-printed JSON for json)
  - Computes deterministic charts from the raw rows (Chart.js)
  - Lists the Splunk links used
  - Is fully self-contained — drop into Slack / email and it works

Usage:
  render_html.py \\
    --session-id <id> \\
    --stage <stage> \\
    --environment <env> \\
    --org <org> \\
    --earliest <e> \\
    --latest <l> \\
    --analysis-id <id> \\
    --analysis-label <human label> \\
    --analysis-output markdown|json \\
    --analysis-file <path>      # body produced by the LLM
    --rows-file <path>          # JSON array of {_time, _raw} (and optional parsed fields)
    --meta-file <path>          # JSON: { splunk_links: [...], summary: {...}, ...}
    --out <path.html>

The rows-file format is the same the parent skill caches under
.agents/artifacts/<session>_raw.json. Optional richer fields used for
charts when present:
  operation, status, top_latency_ms, stages (dict),
  scapi_total_ms, userQuery, siteId, requestId, service.

Stage-keyed durations (e.g. HybridCallSCAPI, ValidateRequest) are
extracted automatically from `_raw` when not pre-parsed.
"""

from __future__ import annotations
import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

PALETTE = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#f87171",
           "#f472b6", "#60a5fa", "#fb923c", "#a3e635", "#22d3ee"]

OP_RE = re.compile(
    r'`(?P<service>ECOMShopperAgent|LLMGateway|EcomConcierge|Storefront|Concierge|GuidedShoppingAgent)`'
    r'(?P<operation>[^`]*)`(?P<latency>\d+)'
)
STATUS_RE = re.compile(r'`(?P<status>Success|Failure|Error|N/A)```')
JSON_BLOB_RE = re.compile(r'```(\{[^`]*\})```')


def parse_row(r: dict) -> dict:
    """Best-effort extract operation/status/latency/stages/userQuery from a row."""
    out = dict(r)  # carry through any pre-parsed fields
    raw = r.get("_raw", "") or ""

    # Operation + service + latency.
    if "operation" not in out:
        m = OP_RE.search(raw)
        if m:
            out["service"] = m.group("service")
            out["operation"] = m.group("operation")
            try:
                out["top_latency_ms"] = int(m.group("latency"))
            except ValueError:
                pass

    # Status.
    if "status" not in out:
        m = STATUS_RE.search(raw)
        if m:
            out["status"] = m.group("status")

    # JSON blob → stages, userQuery, siteId, etc.
    if "stages" not in out or "userQuery" not in out:
        m = JSON_BLOB_RE.search(raw)
        if m:
            try:
                blob = json.loads(m.group(1))
                out.setdefault("stages", blob.get("operationStagesWithExecutionTime", {}) or {})
                out.setdefault("userQuery", blob.get("userQuery"))
                out.setdefault("siteId", blob.get("siteId"))
                out.setdefault("scapi_total_ms", blob.get("scapiSearch_totalTimeMs"))
                out.setdefault("requestId", blob.get("requestId"))
            except json.JSONDecodeError:
                pass

    return out


def parse_iso(t: str) -> float:
    """ISO8601 (with Z or offset) → epoch seconds."""
    if not t:
        return 0.0
    s = t.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(s).timestamp()
    except ValueError:
        return 0.0


def compute_chart_data(rows: list[dict]) -> dict:
    parsed = [parse_row(r) for r in rows]

    # Operations by type (count).
    op_counts: dict[str, int] = {}
    for p in parsed:
        op = p.get("operation") or "(unknown)"
        op_counts[op] = op_counts.get(op, 0) + 1
    ops_by_type = {
        "labels": list(op_counts.keys()),
        "values": list(op_counts.values()),
    }

    # Latency by op (avg + max).
    op_lat: dict[str, list[int]] = {}
    for p in parsed:
        op = p.get("operation")
        lat = p.get("top_latency_ms")
        if not op or lat is None:
            continue
        op_lat.setdefault(op, []).append(int(lat))
    latency_by_op = {
        "labels": list(op_lat.keys()),
        "avg": [round(sum(v) / len(v), 1) for v in op_lat.values()],
        "max": [max(v) for v in op_lat.values()],
    }

    # Status breakdown.
    status_counts: dict[str, int] = {}
    for p in parsed:
        s = p.get("status") or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
    status = {
        "labels": list(status_counts.keys()),
        "values": list(status_counts.values()),
    }

    # Timeline: each row plotted at (seconds_since_start, op_name).
    times = [parse_iso(p.get("_time", "")) for p in parsed]
    valid_times = [t for t in times if t > 0]
    t0 = min(valid_times) if valid_times else 0
    op_index_for_y: dict[str, int] = {}
    y_labels: list[str] = []
    for p in parsed:
        op = p.get("operation") or "(unknown)"
        if op not in op_index_for_y:
            op_index_for_y[op] = len(y_labels)
            y_labels.append(op)
    points = []
    for p, t in zip(parsed, times):
        if t == 0:
            continue
        op = p.get("operation") or "(unknown)"
        points.append({
            "t": round(t - t0, 3),
            "row": op,
            "label": op,
            "duration_ms": p.get("top_latency_ms"),
            "color_idx": op_index_for_y[op],
        })
    timeline = {"points": points, "y_labels": y_labels}

    # Aggregate session stats.
    durations = [p.get("top_latency_ms") for p in parsed if p.get("top_latency_ms") is not None]
    failures = sum(1 for p in parsed if p.get("status") and p["status"].lower() not in ("success", "1", "n/a"))
    user_queries = sorted({p["userQuery"] for p in parsed if p.get("userQuery")})
    request_ids = sorted({p.get("requestId") for p in parsed if p.get("requestId")})
    span_seconds = (max(valid_times) - min(valid_times)) if len(valid_times) >= 2 else 0
    site_ids = sorted({p["siteId"] for p in parsed if p.get("siteId")})

    summary = {
        "total_rows": len(parsed),
        "unique_operations": len(op_counts),
        "unique_turns": len(request_ids),
        "duration_seconds": round(span_seconds, 2),
        "failures": failures,
        "max_latency_ms": max(durations) if durations else 0,
        "user_queries": user_queries,
        "site_ids": site_ids,
    }

    return {
        "ops_by_type": ops_by_type,
        "latency_by_op": latency_by_op,
        "status": status,
        "timeline": timeline,
        "_summary": summary,
        "_parsed_rows": parsed,
    }


def render_stat_card(num, label, color="accent") -> str:
    color_class = {"good": "good", "warn": "warn", "bad": "bad"}.get(color, "")
    return (f'<div class="card stat">'
            f'<div class="lbl">{html.escape(str(label))}</div>'
            f'<div class="num" style="color: var(--{color_class or "accent"});">{html.escape(str(num))}</div>'
            f'</div>')


def render_badges(meta: dict, summary: dict) -> str:
    badges = []
    if meta.get("environment"):
        badges.append(f'<span class="badge">env: {html.escape(meta["environment"])}</span>')
    if meta.get("org"):
        badges.append(f'<span class="badge">org: {html.escape(meta["org"])}</span>')
    if meta.get("stage"):
        badges.append(f'<span class="badge">stage: {html.escape(meta["stage"])}</span>')
    if summary.get("failures", 0) == 0 and summary.get("total_rows", 0) > 0:
        badges.append('<span class="badge good">✓ no failures</span>')
    elif summary.get("failures", 0) > 0:
        badges.append(f'<span class="badge bad">✗ {summary["failures"]} failures</span>')
    if summary.get("duration_seconds", 0):
        badges.append(f'<span class="badge">⏱ {summary["duration_seconds"]:.2f}s</span>')
    return "\n".join(badges)


def render_stats_cards(summary: dict) -> str:
    cards = []
    cards.append(render_stat_card(summary.get("total_rows", 0), "Splunk rows"))
    cards.append(render_stat_card(summary.get("unique_turns", 0), "Distinct turns"))
    cards.append(render_stat_card(summary.get("unique_operations", 0), "Unique ops"))
    cards.append(render_stat_card(f"{summary.get('duration_seconds', 0):.2f}s", "Wall clock"))
    cards.append(render_stat_card(
        summary.get("failures", 0),
        "Failures",
        color="good" if summary.get("failures", 0) == 0 else "bad"))
    cards.append(render_stat_card(f"{summary.get('max_latency_ms', 0)} ms", "Max latency"))
    return "\n".join(cards)


def render_operations_table(parsed_rows: list[dict]) -> str:
    if not parsed_rows:
        return ""
    rows_html = []
    for p in parsed_rows:
        t_iso = (p.get("_time") or "").replace("T", " ").split("+")[0]
        op = html.escape(p.get("operation") or "")
        status = p.get("status") or ""
        status_class = ""
        if status.lower() in ("success", "1"):
            status_class = "good"
        elif status.lower() in ("failure", "error"):
            status_class = "bad"
        elif status.lower() in ("n/a",):
            status_class = ""
        else:
            status_class = "warn"
        lat = p.get("top_latency_ms")
        stages = p.get("stages") or {}
        stages_str = ", ".join(f"{k}={v}" for k, v in stages.items()) if stages else ""
        req = p.get("requestId") or ""
        rows_html.append(
            f"<tr>"
            f"<td>{html.escape(t_iso)}</td>"
            f"<td>{op}</td>"
            f"<td><span class='badge {status_class}'>{html.escape(status)}</span></td>"
            f"<td class='num'>{lat if lat is not None else ''}</td>"
            f"<td class='id'>{html.escape(req)}</td>"
            f"<td class='id' style='font-size:0.75rem;'>{html.escape(stages_str)}</td>"
            f"</tr>"
        )
    return f"""
<section class="card" style="margin-bottom: 20px;">
  <details class="section" open>
    <summary>📋 Operations table</summary>
    <div style="overflow-x:auto;">
    <table>
      <thead>
        <tr>
          <th>Time (UTC)</th>
          <th>Operation</th>
          <th>Status</th>
          <th class="num">Top latency (ms)</th>
          <th>Request ID</th>
          <th>Stage breakdown</th>
        </tr>
      </thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    </div>
  </details>
</section>
"""


def render_splunk_links(links: list[dict]) -> str:
    if not links:
        return '<li class="note">(none recorded)</li>'
    items = []
    for l in links:
        lbl = html.escape(l.get("label", "Link"))
        url = html.escape(l.get("url", ""), quote=True)
        note = html.escape(l.get("note", ""))
        items.append(
            f"<li><span class='lbl'>{lbl}</span>"
            f"{f'<a href={chr(34)}{url}{chr(34)} target=_blank>{url}</a>' if url else ''}"
            f"{f'<span class={chr(34)}note{chr(34)}>{note}</span>' if note else ''}"
            f"</li>"
        )
    return "\n".join(items)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session-id", required=True)
    p.add_argument("--stage", default="core")
    p.add_argument("--environment", default="")
    p.add_argument("--org", default="")
    p.add_argument("--earliest", default="")
    p.add_argument("--latest", default="")
    p.add_argument("--analysis-id", required=True)
    p.add_argument("--analysis-label", default="")
    p.add_argument("--analysis-output", choices=["markdown", "json"], default="markdown")
    p.add_argument("--analysis-file", required=True, help="Path to LLM output (.md or .json)")
    p.add_argument("--rows-file", required=True, help="JSON array of {_time, _raw, ...}")
    p.add_argument("--meta-file", default="", help="JSON metadata (splunk_links, etc.)")
    p.add_argument("--out", required=True, help="Output HTML path")
    p.add_argument("--template", default="", help="Override template path")
    p.add_argument("--open", dest="open_browser", action="store_true", default=True,
                   help="Open the rendered HTML in the default browser (default: on)")
    p.add_argument("--no-open", dest="open_browser", action="store_false",
                   help="Skip opening the browser")
    args = p.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    template_path = Path(args.template) if args.template else skill_dir / "templates" / "report.html.tmpl"
    if not template_path.exists():
        print(f"error: template not found: {template_path}", file=sys.stderr)
        return 1

    analysis_text = Path(args.analysis_file).read_text(encoding="utf-8")
    rows = json.loads(Path(args.rows_file).read_text(encoding="utf-8"))
    meta = {}
    if args.meta_file:
        meta = json.loads(Path(args.meta_file).read_text(encoding="utf-8"))

    chart_data = compute_chart_data(rows)
    summary = chart_data.pop("_summary")
    parsed_rows = chart_data.pop("_parsed_rows")

    meta_for_badges = {
        "environment": args.environment,
        "org": args.org,
        "stage": args.stage,
    }

    title = f"🔬 Obs-Hub Analysis — {args.analysis_id}"
    subtitle = (
        f"Session <code style='font-family:ui-monospace,Menlo,monospace;'>{html.escape(args.session_id)}</code> · "
        f"{html.escape(args.earliest)} → {html.escape(args.latest)}"
    )

    splunk_links = meta.get("splunk_links", [])

    template = template_path.read_text(encoding="utf-8")

    replacements = {
        "__TITLE__": html.escape(title),
        "__SUBTITLE__": subtitle,
        "__BADGES__": render_badges(meta_for_badges, summary),
        "__STATS_CARDS__": render_stats_cards(summary),
        "__OPERATIONS_TABLE__": render_operations_table(parsed_rows),
        "__ANALYSIS_LABEL__": html.escape(args.analysis_label or args.analysis_id),
        "__SPLUNK_LINKS__": render_splunk_links(splunk_links),
        "__GENERATED_AT__": dt.datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip(),
        "__ANALYSIS_RAW_JSON__": json.dumps(analysis_text),
        "__ANALYSIS_OUTPUT_TYPE_JSON__": json.dumps(args.analysis_output),
        "__CHART_DATA_JSON__": json.dumps(chart_data),
    }

    out = template
    for k, v in replacements.items():
        out = out.replace(k, v)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")

    file_url = f"file://{out_path.resolve()}"
    print(f"✅ HTML report written: {out_path}")
    print(f"   Size: {out_path.stat().st_size:,} bytes")
    print(f"   Open: {file_url}")

    if args.open_browser:
        # Try to open in the user's default browser. macOS `open` is the
        # most reliable on this platform; fall back to webbrowser.open
        # cross-platform. Either way, never block on browser launch — and
        # never fail the script if the launch fails (the file is what
        # matters).
        opened = False
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", file_url], check=False, timeout=3)
                opened = True
            elif sys.platform.startswith("linux"):
                subprocess.run(["xdg-open", file_url], check=False, timeout=3)
                opened = True
            elif os.name == "nt":
                os.startfile(str(out_path.resolve()))  # type: ignore[attr-defined]
                opened = True
            else:
                opened = webbrowser.open(file_url, new=2)
        except Exception as e:
            print(f"   (browser auto-open failed: {e})")
        if opened:
            print(f"   🌐 Opened in browser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
