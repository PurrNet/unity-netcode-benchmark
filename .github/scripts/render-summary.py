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


SERIES = {
    "light": {"purrnet": "#eb6834", "fishnet": "#2a78d6", "mirror": "#1baf7a", "ngo": "#eda100", "fusion": "#e87ba4"},
    "dark": {"purrnet": "#d95926", "fishnet": "#3987e5", "mirror": "#199e70", "ngo": "#c98500", "fusion": "#d55181"},
}
THEME = {
    "light": {"ink": "#1f2328", "muted": "#656d76", "grid": "#d0d7de", "best_fill": "#dafbe1", "best_ink": "#1a7f37"},
    "dark": {"ink": "#e6edf3", "muted": "#8d96a0", "grid": "#30363d", "best_fill": "#12351d", "best_ink": "#3fb950"},
}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_tables(blocks, netcodes, theme):
    """blocks: list of (title, unit, rows) where rows = [(test, [(text, is_best), ...])]. One SVG, tables stacked."""
    t = THEME[theme]
    col0, colw, rowh, headh, titleh, gap, pad = 118, 92, 27, 30, 26, 22, 8
    width = pad * 2 + col0 + colw * len(netcodes)
    height = pad * 2 + sum(titleh + headh + rowh * len(rows) for _, _, rows in blocks) + gap * (len(blocks) - 1)
    font = 'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Benchmark summary tables">',
           f'<style>text{{{font.replace("font-family=", "font-family:").strip(chr(34))};font-size:13px;font-variant-numeric:tabular-nums}}</style>']
    y = pad
    for title, unit, rows in blocks:
        out.append(f'<text x="{pad}" y="{y + 17}" font-weight="600" fill="{t["ink"]}">{esc(title)}</text>')
        out.append(f'<text x="{width - pad}" y="{y + 17}" text-anchor="end" fill="{t["muted"]}" font-size="12">{esc(unit)}, lower is better</text>')
        y += titleh
        out.append(f'<text x="{pad}" y="{y + 19}" fill="{t["muted"]}" font-size="11" letter-spacing="0.5">TEST</text>')
        for i, n in enumerate(netcodes):
            x = pad + col0 + colw * (i + 1) - 6
            out.append(f'<text x="{x}" y="{y + 19}" text-anchor="end" font-weight="600" fill="{SERIES[theme][n]}">{esc(NAMES[n])}</text>')
        y += headh
        out.append(f'<line x1="{pad}" y1="{y}" x2="{width - pad}" y2="{y}" stroke="{t["grid"]}" stroke-width="1"/>')
        for test, cells in rows:
            out.append(f'<text x="{pad}" y="{y + 18}" fill="{t["ink"]}">{esc(test)}</text>')
            for i, (text, best) in enumerate(cells):
                x0 = pad + col0 + colw * i
                if best:
                    out.append(f'<rect x="{x0 + 8}" y="{y + 3}" width="{colw - 12}" height="{rowh - 6}" rx="5" fill="{t["best_fill"]}"/>')
                out.append(f'<text x="{x0 + colw - 6}" y="{y + 18}" text-anchor="end" fill="{t["best_ink"] if best else t["ink"]}" font-weight="{600 if best else 400}">{esc(text)}</text>')
            y += rowh
            out.append(f'<line x1="{pad}" y1="{y}" x2="{width - pad}" y2="{y}" stroke="{t["grid"]}" stroke-width="0.5"/>')
        y += gap
    out.append("</svg>")
    return "\n".join(out)


def rows_for(unit, netcodes, sizes, by, cell, lower=True):
    size = sizes[-1]
    rows = []
    for t in TESTS:
        vals = [cell(by.get((n, size)), t) if by.get((n, size)) else None for n in netcodes]
        present = [v for v in vals if v is not None]
        best = (min(present) if lower else max(present)) if len(present) > 1 else None
        rows.append((t, [((fmt_kb(v) if unit == "KB/s" else fmt_pct(v)) if v is not None else "–", v is not None and v == best) for v in vals]))
    return rows


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
    ap.add_argument("--svg-out", default="", help="directory to write latest-light.svg / latest-dark.svg into (referenced from the Markdown as <dir>/latest-*.svg)")
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
    t1 = f"Server downstream on-wire at {size} connections"
    t2 = f"Server CPU minus idle at {size} connections"
    if args.svg_out:
        blocks = [(t1, "KB/s", rows_for("KB/s", netcodes, sizes, by, srv_down)),
                  (t2, "% of one core", rows_for("%", netcodes, sizes, by, cpu))]
        out_dir = Path(args.svg_out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for theme in ("light", "dark"):
            (out_dir / f"latest-{theme}.svg").write_text(svg_tables(blocks, netcodes, theme), encoding="utf-8")
        rel = args.svg_out.rstrip("/\\").replace("\\", "/")
        lines.append("<picture>")
        lines.append(f'  <source media="(prefers-color-scheme: dark)" srcset="{rel}/latest-dark.svg">')
        lines.append(f'  <img alt="{esc(t1)}; {esc(t2)}. Best value per row highlighted in green." src="{rel}/latest-light.svg">')
        lines.append("</picture>")
        lines.append("")
        lines.append("<details><summary>Same tables as text</summary>")
        lines.append("")
        lines += table(t1, "KB/s", netcodes, sizes, by, srv_down)
        lines += table(t2, "% of one core", netcodes, sizes, by, cpu)
        lines.append("</details>")
        lines.append("")
    else:
        lines += table(t1, "KB/s", netcodes, sizes, by, srv_down)
        lines += table(t2, "% of one core", netcodes, sizes, by, cpu)
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
