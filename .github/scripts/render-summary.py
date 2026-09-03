#!/usr/bin/env python3
"""Render the compact "Latest results" Markdown block that the workflow commits into README.md.

Usage: render-summary.py <scaling.json> [--versions versions.json] [--run-url URL] [--report-url URL]

Prints Markdown: a header line with run date / versions, then two tables at the largest connection
count (server downstream on-wire per test, server CPU minus idle per test) and pointers to the
full report. Everything else lives in the interactive report.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ORDER = ["purrnet", "fishnet", "mirror", "ngo", "fusion"]
NAMES = {"purrnet": "PurrNet", "fishnet": "FishNet", "mirror": "Mirror", "ngo": "NGO", "fusion": "Fusion"}
TESTS = ["MoveY", "MoveAllAxis", "MoveWander", "SendRPC", "Static", "SpawnChurn", "ClientInput", "SyncVars"]


def fmt_kb(v):
    if v is None:
        return "–"
    kb = v / 1024
    return f"{kb:,.0f}" if kb >= 100 else f"{kb:.1f}"


def fmt_pct(v):
    return "–" if v is None else f"{v:.1f}"


def table(title, unit, netcodes, sizes, by, cell, lower=True):
    out = [f"**{title}** ({unit}, lower is better)", "", "| Test | " + " | ".join(NAMES[n] for n in netcodes) + " |",
           "|---|" + "|".join("---:" for _ in netcodes) + "|"]
    size = sizes[-1]
    for t in TESTS:
        vals = []
        for n in netcodes:
            r = by.get((n, size))
            vals.append(cell(r, t) if r else None)
        present = [v for v in vals if v is not None]
        best = (min(present) if lower else max(present)) if len(present) > 1 else None
        cells = []
        for v in vals:
            s = fmt_kb(v) if unit == "KB/s" else fmt_pct(v)
            cells.append(f"**{s}**" if v is not None and v == best else s)
        out.append(f"| {t} | " + " | ".join(cells) + " |")
    out.append("")
    return out


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("scaling")
    ap.add_argument("--versions")
    ap.add_argument("--run-url", default="")
    ap.add_argument("--report-url", default="")
    args = ap.parse_args()

    runs = json.loads(Path(args.scaling).read_text(encoding="utf-8"))
    versions = json.loads(Path(args.versions).read_text(encoding="utf-8")) if args.versions and Path(args.versions).exists() else {}
    import re
    for r in runs:
        if not r.get("size"):
            m = re.fullmatch(r"c(\d+)", str(r.get("tag", "")))
            r["size"] = int(m.group(1)) if m else r.get("connections")
    netcodes = [n for n in ORDER if any(r["netcode"] == n for r in runs)]
    sizes = sorted({r["size"] for r in runs})
    by = {(r["netcode"], r["size"]): r for r in runs}
    if not sizes:
        print("_No datapoints._")
        return

    size = sizes[-1]
    any_run = next(iter(runs))
    any_test = next((t for t in any_run.get("server", {}).values() if isinstance(t, dict) and t.get("test", 0) > 0), None)
    objects = any_test["objects"] if any_test else "?"
    window = round(any_test["windowSeconds"]) if any_test else "?"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def idle(r):
        return (r.get("server", {}).get("Idle") or {}).get("cpuPercent", 0) or 0

    def srv_down(r, t):
        s = r.get("server", {}).get(t)
        return s["txBytesPerSec"] if s else None

    def cpu(r, t):
        s = r.get("server", {}).get(t)
        return (s["cpuPercent"] - idle(r)) if s else None

    lines = []
    ver = " · ".join(f"{NAMES[n]} {versions.get(n, '?')}" for n in netcodes)
    lines.append(f"_Last run {date}: {ver} · Unity {versions.get('unity', '?')} · {objects} objects per test · {window} s windows · "
                 f"connections {' / '.join(str(s) for s in sizes)}._")
    lines.append("")
    conn_notes = []
    for n in netcodes:
        r = by.get((n, size))
        if r and r["meta"].get("connectedAtStart") != r["meta"].get("expectedClients"):
            conn_notes.append(f"{NAMES[n]} ran with {r['meta'].get('connectedAtStart')}/{r['meta'].get('expectedClients')} clients")
        elif r and r.get("connections") != size:
            conn_notes.append(f"{NAMES[n]} ran with {r.get('connections')} clients")
    if conn_notes:
        lines.append("_Note: " + "; ".join(conn_notes) + "._")
        lines.append("")
    lines += table(f"Server downstream on-wire at {size} connections", "KB/s", netcodes, sizes, by, srv_down)
    lines += table(f"Server CPU minus idle at {size} connections", "% of one core", netcodes, sizes, by, cpu)
    links = []
    if args.report_url:
        links.append(f"[interactive report]({args.report_url})")
    if args.run_url:
        links.append(f"[workflow run]({args.run_url})")
    links.append("[raw datapoints](docs/latest.json)")
    lines.append("All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the " + ", ".join(links) + ".")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
