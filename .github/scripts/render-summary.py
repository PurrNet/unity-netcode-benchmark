#!/usr/bin/env python3
"""Render the compact "Latest results" Markdown block (docs/latest.md, also the job summary).

Usage: render-summary.py <scaling.json> [--versions versions.json] [--run-url URL] [--report-url URL] [--svg-out DIR]

Prints Markdown: a header line with run date / versions, then the same two tables the report opens
with, rendered as an SVG (light + dark) and as text in a <details>:

  * Scorecard at the reference session (largest connection count, lowest tick rate): per netcode,
    bandwidth and server CPU as the geometric mean over the load tests of "value / best value in that
    test" (1.00x = best everywhere), GC collections, worst frame p99 and a win count.
  * How it scales: the cost multiplier from the smallest to the largest connection count and from
    the lowest to the highest tick rate, per netcode, for bandwidth and CPU.

Everything else lives in the interactive report.
"""
import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

ORDER = ["purrnet", "fishnet", "mirror", "ngo", "fusion"]
NAMES = {"purrnet": "PurrNet", "fishnet": "FishNet", "mirror": "Mirror", "ngo": "NGO", "fusion": "Fusion"}
# Tests that carry real load; Idle and Static sit at the noise floor.
SCORE_TESTS = ["MoveY", "MoveWander", "SyncVars", "SendRPC", "ClientInput", "SpawnChurn"]
GOALS = [("srvDown", 0.0), ("cpu", 0.5), ("alloc", 0.0)]

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


def metric(r, mid, t):
    s = r.get("server", {}).get(t)
    if not s:
        return None
    alloc = s.get("gcAllocBytesPerSec")
    return {"srvDown": s.get("txBytesPerSec"), "cpu": s.get("cpuPercent"), "gc": s.get("gcCollections"),
            "alloc": alloc if alloc is not None and alloc >= 0 else None}[mid]


def geomean(xs):
    xs = [x for x in xs if x is not None and x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None


def fmt_x(v):
    if v is None:
        return "–"
    return (f"{v:.0f}" if v >= 100 else f"{v:.1f}" if v >= 10 else f"{v:.2f}") + "×"


def goals_in_use(netcodes, by, sc):
    return [(g, tol) for g, tol in GOALS if any((n, sc) in by and metric(by[(n, sc)], g, t) is not None for n in netcodes for t in SCORE_TESTS)]


def scorecard(netcodes, by, sc):
    """rows: netcode -> dict(bw, cpu, alloc, gc, p99, wins)."""
    rel = {g: {n: [] for n in netcodes} for g, _ in GOALS}
    wins = {n: 0 for n in netcodes}
    for t in SCORE_TESTS:
        for g, tol in goals_in_use(netcodes, by, sc):
            vals = [(n, metric(by[(n, sc)], g, t)) for n in netcodes if (n, sc) in by]
            vals = [(n, v) for n, v in vals if v is not None]
            if not vals:
                continue
            best = min(v for _, v in vals)
            for n, v in vals:
                if v - best <= tol:
                    wins[n] += 1
                if best > 0:
                    rel[g][n].append(v / best)
    rows = {}
    for n in netcodes:
        r = by.get((n, sc))
        have = [t for t in SCORE_TESTS if r and r.get("server", {}).get(t)]
        rows[n] = {
            "bw": geomean(rel["srvDown"][n]),
            "cpu": geomean(rel["cpu"][n]),
            "alloc": geomean(rel["alloc"][n]),
            "gc": sum(r["server"][t].get("gcCollections", 0) for t in have) if have else None,
            "p99": max(r["server"][t].get("p99FrameMs", 0) for t in have) if have else None,
            "wins": wins[n] if r else None,
        }
    return rows


def multiplier(by, n, frm, to, mid):
    ratios = []
    for t in SCORE_TESTS:
        a = metric(by[(n, frm)], mid, t) if (n, frm) in by else None
        b = metric(by[(n, to)], mid, t) if (n, to) in by else None
        if a and b is not None and a > 0:
            ratios.append(b / a)
    return geomean(ratios)


def scaling_axes(scenarios):
    sizes = sorted({s for s, _ in scenarios})
    ticks = sorted({t for _, t in scenarios})
    axes = []
    by_size = sorted(s for s in scenarios if s[1] == ticks[0])
    if len(by_size) > 1:
        axes.append((by_size[0], by_size[-1], f"{by_size[0][0]} → {by_size[-1][0]} conn"))
    by_tick = sorted((s for s in scenarios if s[0] == sizes[-1]), key=lambda s: s[1])
    if len(by_tick) > 1:
        axes.append((by_tick[0], by_tick[-1], f"{by_tick[0][1]} → {by_tick[-1][1]} Hz"))
    return axes


def mark_best(cells, lower=True, rel=0.02, abs_tol=None):
    """cells: list of (value, text). Returns list of (text, is_best); values within the tolerance of
    the best share the mark, and nothing is marked when every value ties."""
    present = [v for v, _ in cells if v is not None]
    if len(present) < 2:
        return [(text, False) for _, text in cells]
    best = min(present) if lower else max(present)
    eps = abs_tol if abs_tol is not None else abs(best) * rel
    flags = [v is not None and abs(v - best) <= eps for v, _ in cells]
    if sum(flags) == len(present):
        flags = [False] * len(cells)
    return [(text, f) for (_, text), f in zip(cells, flags)]


def svg_tables(blocks, theme):
    """blocks: list of (title, subtitle, columns, rows) with rows = [(label, color, [(text, is_best), ...])]."""
    t = THEME[theme]
    col0, colw, rowh, headh, titleh, gap, pad = 96, 124, 27, 34, 26, 22, 8
    ncols = max(len(cols) for _, _, cols, _ in blocks)
    width = pad * 2 + col0 + colw * ncols
    height = pad * 2 + sum(titleh + headh + rowh * len(rows) for _, _, _, rows in blocks) + gap * (len(blocks) - 1)
    font = "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Benchmark summary tables">',
           f'<style>text{{font-family:{font};font-size:13px;font-variant-numeric:tabular-nums}}</style>']
    y = pad
    for title, subtitle, cols, rows in blocks:
        out.append(f'<text x="{pad}" y="{y + 17}" font-weight="600" fill="{t["ink"]}">{esc(title)}</text>')
        out.append(f'<text x="{width - pad}" y="{y + 17}" text-anchor="end" fill="{t["muted"]}" font-size="12">{esc(subtitle)}</text>')
        y += titleh
        out.append(f'<text x="{pad}" y="{y + 21}" fill="{t["muted"]}" font-size="11" letter-spacing="0.5">NETCODE</text>')
        for i, c in enumerate(cols):
            x = pad + col0 + colw * (i + 1) - 6
            lines = c.split("\n")
            for j, line in enumerate(lines):
                yy = y + 21 - (len(lines) - 1 - j) * 12
                out.append(f'<text x="{x}" y="{yy}" text-anchor="end" fill="{t["muted"]}" font-size="11" letter-spacing="0.5">{esc(line.upper())}</text>')
        y += headh
        out.append(f'<line x1="{pad}" y1="{y}" x2="{width - pad}" y2="{y}" stroke="{t["grid"]}" stroke-width="1"/>')
        for label, color, cells in rows:
            out.append(f'<rect x="{pad}" y="{y + 9}" width="9" height="9" rx="2" fill="{color}"/>')
            out.append(f'<text x="{pad + 15}" y="{y + 18}" fill="{t["ink"]}" font-weight="600">{esc(label)}</text>')
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


def md_table(title, note, cols, rows):
    out = [f"**{title}** ({note})", "", "| Netcode | " + " | ".join(c.replace("\n", " ") for c in cols) + " |",
           "|---|" + "|".join("---:" for _ in cols) + "|"]
    for label, _, cells in rows:
        out.append(f"| {label} | " + " | ".join(f"**{s}**" if best else s for s, best in cells) + " |")
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
    for r in runs:
        m = re.fullmatch(r"c(\d+)(?:t(\d+))?", str(r.get("tag", "")))
        if not r.get("size"):
            r["size"] = int(m.group(1)) if m else r.get("connections")
        if not r.get("tick"):
            r["tick"] = int(m.group(2)) if m and m.group(2) else (r.get("meta", {}).get("tickRate") or 0)
    netcodes = [n for n in ORDER if any(r["netcode"] == n for r in runs)]
    scenarios = sorted({(r["size"], r["tick"]) for r in runs})
    by = {(r["netcode"], (r["size"], r["tick"])): r for r in runs}
    if not scenarios:
        print("_No datapoints._")
        return

    sizes = sorted({s for s, _ in scenarios})
    ref = min((s for s in scenarios if s[0] == sizes[-1]), key=lambda s: s[1])
    any_run = next(iter(runs))
    any_test = next((t for t in any_run.get("server", {}).values() if isinstance(t, dict) and t.get("test", 0) > 0), None)
    objects = any_test["objects"] if any_test else "?"
    window = round(any_test["windowSeconds"]) if any_test else "?"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    colors = SERIES["light"]

    lines = []
    ver = " · ".join(f"{NAMES[n]} {versions.get(n, '?')}" for n in netcodes)
    lines.append(f"_Last run {date}: {ver} · Unity {versions.get('unity', '?')} · {objects} objects per test · {window} s windows · "
                 f"sessions {' / '.join(f'{s}c @ {t} Hz' for s, t in scenarios)}._")
    lines.append("")
    notes = []
    for n in netcodes:
        r = by.get((n, ref))
        if not r:
            notes.append(f"{NAMES[n]} has no datapoint at the reference session")
        elif r["meta"].get("connectedAtStart") != r["meta"].get("expectedClients"):
            notes.append(f"{NAMES[n]} ran with {r['meta'].get('connectedAtStart')}/{r['meta'].get('expectedClients')} clients")
        elif r.get("connections") != ref[0]:
            notes.append(f"{NAMES[n]} ran with {r.get('connections')} clients")
    for sc in scenarios:
        models = {NAMES[n]: by[(n, sc)]["meta"].get("cpuModel") for n in netcodes if (n, sc) in by and by[(n, sc)]["meta"].get("cpuModel")}
        if len(set(models.values())) > 1:
            notes.append(f"at {sc[0]}c @ {sc[1]} Hz the servers ran on different CPU models (" + "; ".join(f"{n}: {m}" for n, m in models.items()) + "), so CPU is not comparable there")
    if notes:
        lines.append("_Note: " + "; ".join(notes) + "._")
        lines.append("")

    # Block 1: scorecard at the reference session.
    rows = scorecard(netcodes, by, ref)
    t1 = f"At a glance, {ref[0]} connections @ {ref[1]} Hz"
    bw = mark_best([(rows[n]["bw"], fmt_x(rows[n]["bw"])) for n in netcodes])
    cpu = mark_best([(rows[n]["cpu"], fmt_x(rows[n]["cpu"])) for n in netcodes])
    alloc = mark_best([(rows[n]["alloc"], fmt_x(rows[n]["alloc"])) for n in netcodes])
    gc = mark_best([(rows[n]["gc"], "–" if rows[n]["gc"] is None else str(rows[n]["gc"])) for n in netcodes], abs_tol=0)
    p99 = mark_best([(rows[n]["p99"], "–" if rows[n]["p99"] is None else f"{rows[n]['p99']:.1f} ms") for n in netcodes], abs_tol=0.2)
    n_goals = len(goals_in_use(netcodes, by, ref))
    wins = mark_best([(rows[n]["wins"], "–" if rows[n]["wins"] is None else f"{rows[n]['wins']} / {len(SCORE_TESTS) * n_goals}") for n in netcodes], lower=False, abs_tol=0)
    # Columns the dataset does not have (older runs lack allocation) are left out rather than shown as dashes.
    columns = [("Bandwidth", "bw", bw), ("Server CPU", "cpu", cpu), ("GC alloc", "alloc", alloc), ("Collections", "gc", gc), ("Frame p99", "p99", p99), ("Wins", "wins", wins)]
    columns = [c for c in columns if any(rows[n][c[1]] is not None for n in netcodes)]
    cols1 = [c[0] for c in columns]
    rows1 = [(NAMES[n], colors[n], [c[2][i] for c in columns]) for i, n in enumerate(netcodes)]
    note1 = "× best netcode, geometric mean over the load tests; lower is better"

    # Block 2: how it scales.
    axes = scaling_axes(scenarios)
    blocks = [(t1, note1, cols1, rows1)]
    if axes:
        cols2 = [f"{g}\n{label}" for _, _, label in axes for g in ("Bandwidth", "Server CPU")]
        cells2 = []
        for frm, to, _ in axes:
            for mid in ("srvDown", "cpu"):
                cells2.append(mark_best([(multiplier(by, n, frm, to, mid), fmt_x(multiplier(by, n, frm, to, mid))) for n in netcodes]))
        rows2 = [(NAMES[n], colors[n], [c[i] for c in cells2]) for i, n in enumerate(netcodes)]
        linear = ", ".join(f"linear = {fmt_x((to[0] / frm[0]) * (to[1] / frm[1]))} for {label}" for frm, to, label in axes)
        note2 = f"cost multiplier; {linear}"
        blocks.append(("How it scales", note2, cols2, rows2))

    if args.svg_out:
        out_dir = Path(args.svg_out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for theme in ("light", "dark"):
            themed = [(t, s, c, [(l, SERIES[theme][n], cells) for (l, _, cells), n in zip(r, netcodes)]) for (t, s, c, r) in blocks]
            (out_dir / f"latest-{theme}.svg").write_text(svg_tables(themed, theme), encoding="utf-8")
        rel = args.svg_out.rstrip("/\\").replace("\\", "/")
        lines.append("<picture>")
        lines.append(f'  <source media="(prefers-color-scheme: dark)" srcset="{rel}/latest-dark.svg">')
        lines.append(f'  <img alt="{esc(t1)}; how it scales. Best value per column highlighted in green." src="{rel}/latest-light.svg">')
        lines.append("</picture>")
        lines.append("")
        lines.append("<details><summary>Same tables as text</summary>")
        lines.append("")
        for title, note, cols, rows_ in blocks:
            lines += md_table(title, note, cols, rows_)
        lines.append("</details>")
        lines.append("")
    else:
        for title, note, cols, rows_ in blocks:
            lines += md_table(title, note, cols, rows_)
    lines.append(f"Bandwidth is server downstream on-wire, CPU is the whole server process and GC alloc is managed bytes allocated per second; each is shown as a multiple of the best netcode in each of the {len(SCORE_TESTS)} load tests, averaged (geometric mean), so 1.00× is best everywhere. Collections is the count over those tests, each starting on a freshly collected heap. Wins counts tests won on bandwidth, CPU or allocation.")
    links = []
    if args.report_url:
        links.append(f"[interactive report]({args.report_url})")
    if args.run_url:
        links.append(f"[workflow run]({args.run_url})")
    links.append("[raw datapoints](latest.json)")
    lines.append("Every metric per test (bandwidth, CPU, frame times, RTT, GC, memory) and every session are in the " + ", ".join(links) + ".")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
