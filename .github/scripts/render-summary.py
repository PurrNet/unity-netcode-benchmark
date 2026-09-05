#!/usr/bin/env python3
"""Render the compact "Latest results" Markdown block (docs/latest.md, also the job summary).

Usage: render-summary.py <scaling.json> [--versions versions.json] [--run-url URL] [--report-url URL] [--svg-out DIR]

Prints Markdown: a header line with run date / versions, then category and scaling tables,
rendered as an SVG (light + dark) and as text in a <details>:

  * Category measurements at the reference session (largest connection count, lowest tick rate):
    bandwidth, CPU and allocation averages, GC collections and worst frame p99. No combined ranking.
  * How it scales: added bandwidth and CPU cost per connection or Hz.

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
CATEGORIES = [
    ("State replication", ["MoveY", "MoveWander", "SyncVars"]),
    ("Messaging", ["SendRPC", "ClientInput"]),
    ("Spawn / despawn", ["SpawnChurn"]),
]

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


def run_failure(r):
    if not r:
        return "no datapoint"
    if (r.get("meta") or {}).get("serverError"):
        return r["meta"]["serverError"]
    return category_failure(r, SCORE_TESTS)


def category_failure(r, tests):
    if not r:
        return "no datapoint"
    meta = r.get("meta") or {}
    if (meta.get("process") or {}).get("status") == "host-oom":
        return "host memory exhausted"
    def complete(t):
        w = r.get("server", {}).get(t)
        return bool(w and not w.get("truncated") and not (
            t in ("SendRPC", "SyncVars") and (w.get("deliveryComplete") is False or
            (meta.get("serverError") and w.get("deliveryComplete") is not True))))
    have = sum(complete(t) for t in tests)
    return f"incomplete ({have}/{len(tests)} tests)" if have < len(tests) else None


def metric(r, mid, t, tests=None):
    s = r.get("server", {}).get(t) if r else None
    if not s or (run_failure(r) if tests is None else category_failure(r, tests)):
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


def fmt_kbs(v):
    """v in bytes/s."""
    if v is None:
        return "–"
    kb = v / 1024
    return f"{kb / 1024:.2f} MB/s" if kb >= 1024 else f"{kb:.0f} KB/s" if kb >= 100 else f"{kb:.1f} KB/s"


def fmt_pct(v):
    return "–" if v is None else f"{v:.1f}%"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def overloaded(r, t):
    """Finished, but the server could not hold the 60 fps budget: p99 past twice the budget or a sixth of frames dropped."""
    w = (r or {}).get("server", {}).get(t)
    if not w:
        return False
    fps = w.get("avgFps") or 0
    return (w.get("p99FrameMs") or 0) > 33.3 or 0 < fps < 54


def scorecard(netcodes, by, sc, tests=None):
    """Rows of measurements and completion status, without a combined score."""
    selected = SCORE_TESTS if tests is None else tests
    rows = {}
    for n in netcodes:
        r = by.get((n, sc))
        have = [t for t in selected if r and r.get("server", {}).get(t)]
        def average(mid):
            vals = [metric(r, mid, t, tests) for t in selected]
            return mean(vals) if all(v is not None for v in vals) else None
        rows[n] = {
            "bw": average("srvDown"),
            "cpu": average("cpu"),
            "alloc": average("alloc"),
            "gc": sum(r["server"][t].get("gcCollections", 0) for t in have) if have else None,
            "p99": max(r["server"][t].get("p99FrameMs", 0) for t in have) if have else None,
            "error": run_failure(r) if tests is None else category_failure(r, tests),
            "overloaded": sum(overloaded(r, t) for t in selected),
        }
    return rows


def marginal(by, n, frm, to, mid, units):
    """(cost at the larger session - cost at the smaller) / units added, averaged over the load tests.
    Both sessions must have a complete suite."""
    if run_failure(by.get((n, frm))) or run_failure(by.get((n, to))):
        return None
    deltas = []
    for t in SCORE_TESTS:
        a = metric(by[(n, frm)], mid, t) if (n, frm) in by else None
        b = metric(by[(n, to)], mid, t) if (n, to) in by else None
        if a is not None and b is not None:
            deltas.append((b - a) / units)
    return sum(deltas) / len(deltas) if len(deltas) == len(SCORE_TESTS) else None


def fmt_cost(v, unit):
    if v is None:
        return "–"
    a = abs(v)
    return (f"{v:.0f}" if a >= 100 else f"{v:.1f}" if a >= 10 else f"{v:.2f}" if a >= 1 else f"{v:.3f}") + f" {unit}"


def scaling_axes(scenarios):
    """(from, to, column label, units added, note)"""
    sizes = sorted({s for s, _ in scenarios})
    ticks = sorted({t for _, t in scenarios})
    axes = []
    by_size = sorted(s for s in scenarios if s[1] == ticks[0])
    if len(by_size) > 1:
        axes.append((by_size[0], by_size[-1], "per conn", by_size[-1][0] - by_size[0][0], f"{by_size[0][0]} → {by_size[-1][0]} connections at {ticks[0]} Hz"))
    by_tick = sorted((s for s in scenarios if s[0] == sizes[-1]), key=lambda s: s[1])
    if len(by_tick) > 1:
        axes.append((by_tick[0], by_tick[-1], "per Hz", by_tick[-1][1] - by_tick[0][1], f"{by_tick[0][1]} → {by_tick[-1][1]} Hz at {sizes[-1]} connections"))
    return axes


def mark_best(cells, lower=True, rel=0.02, abs_tol=None):
    """cells: list of (value, text). Returns list of (text, is_best); values within the tolerance of
    the best share the mark, and nothing is marked when every value ties."""
    present = [v for v, _ in cells if v is not None]
    if len(present) < 2:
        return [(text, False) for _, text in cells]
    best = min(present) if lower else max(present)
    eps = abs_tol if abs_tol is not None else abs(best) * rel
    best_text = next(text for v, text in cells if v == best)
    flags = [v is not None and (abs(v - best) <= eps or text == best_text) for v, text in cells]
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
        first = "CATEGORY" if rows and all(color is None for _, color, _ in rows) else "NETCODE"
        out.append(f'<text x="{pad}" y="{y + 21}" fill="{t["muted"]}" font-size="11" letter-spacing="0.5">{first}</text>')
        for i, c in enumerate(cols):
            x = pad + col0 + colw * (i + 1) - 6
            lines = c.split("\n")
            for j, line in enumerate(lines):
                yy = y + 21 - (len(lines) - 1 - j) * 12
                out.append(f'<text x="{x}" y="{yy}" text-anchor="end" fill="{t["muted"]}" font-size="11" letter-spacing="0.5">{esc(line.upper())}</text>')
        y += headh
        out.append(f'<line x1="{pad}" y1="{y}" x2="{width - pad}" y2="{y}" stroke="{t["grid"]}" stroke-width="1"/>')
        for label, color, cells in rows:
            if color:
                out.append(f'<rect x="{pad}" y="{y + 9}" width="9" height="9" rx="2" fill="{color}"/>')
            out.append(f'<text x="{pad + (15 if color else 0)}" y="{y + 18}" fill="{t["ink"]}" font-weight="600">{esc(label)}</text>')
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
    first = "Category" if rows and all(color is None for _, color, _ in rows) else "Netcode"
    out = [f"**{title}** ({note})", "", f"| {first} | " + " | ".join(c.replace("\n", " ") for c in cols) + " |",
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
        for n in netcodes:
            error = (by.get((n, sc), {}).get("meta") or {}).get("serverError")
            if error:
                notes.append(f"{NAMES[n]} at {sc[0]}c @ {sc[1]} Hz: {error}")
        models = {NAMES[n]: by[(n, sc)]["meta"].get("cpuModel") for n in netcodes if (n, sc) in by and by[(n, sc)]["meta"].get("cpuModel")}
        if len(set(models.values())) > 1:
            notes.append(f"at {sc[0]}c @ {sc[1]} Hz the servers ran on different CPU models (" + "; ".join(f"{n}: {m}" for n, m in models.items()) + "), so CPU is not comparable there")
    if notes:
        lines.append("_Note: " + "; ".join(notes) + "._")
        lines.append("")

    # One scorecard per category; no overall pass/fail scorecard.
    blocks = []
    t1 = f"At a glance, {ref[0]} connections @ {ref[1]} Hz"
    # Who's ahead: the best netcode per category and column, among those that completed it without
    # overloading; ties within 2% share the cell. Nothing is averaged across categories.
    strip_cols = [("Bandwidth", "bw", fmt_kbs), ("Server CPU", "cpu", fmt_pct), ("GC alloc", "alloc", fmt_kbs)]
    strip_rows = []
    for category, tests in CATEGORIES:
        rows = scorecard(netcodes, by, ref, tests)
        cells = []
        for _, key, formatter in strip_cols:
            eligible = [n for n in netcodes if not rows[n]["error"] and not rows[n]["overloaded"] and rows[n][key] is not None]
            if not eligible:
                cells.append(("–", False))
                continue
            marked = mark_best([(None if rows[n]["error"] or rows[n]["overloaded"] else rows[n][key],
                                 "–" if rows[n][key] is None else formatter(rows[n][key])) for n in netcodes])
            names = [NAMES[n] for n, (_, best) in zip(netcodes, marked) if best]
            cells.append((", ".join(names) if names else "tie", False))
        strip_rows.append((category, None, cells))
    if any(text not in ("–", "tie") for _, _, cells in strip_rows for text, _ in cells):
        blocks.append((f"Who's ahead, {ref[0]} connections @ {ref[1]} Hz", "best per category; no averaging across categories",
                       [title for title, _, _ in strip_cols], strip_rows))
    for category, tests in CATEGORIES:
        rows = scorecard(netcodes, by, ref, tests)
        specs = [
            ("Bandwidth", "bw", fmt_kbs, {}),
            ("Server CPU", "cpu", fmt_pct, {}),
            ("GC alloc", "alloc", fmt_kbs, {}),
            ("Collections", "gc", str, dict(abs_tol=0)),
            ("Frame p99", "p99", lambda v: f"{v:.1f} ms", dict(abs_tol=0.2)),
        ]
        columns = []
        for title, key, formatter, options in specs:
            if not any(rows[n][key] is not None for n in netcodes):
                continue
            cells = mark_best([(None if rows[n]["error"] or rows[n]["overloaded"] else rows[n][key],
                                "–" if rows[n][key] is None else formatter(rows[n][key]))
                               for n in netcodes], **options)
            columns.append((title, cells))
        def status(n):
            if rows[n]["error"]:
                return "Did not complete"
            if rows[n]["overloaded"]:
                return f"Overloaded ({rows[n]['overloaded']}/{len(tests)})"
            return "Completed"
        table_rows = [(NAMES[n], colors[n], [(status(n), False)] + [cells[i] for _, cells in columns])
                      for i, n in enumerate(netcodes)]
        blocks.append((category, f"{ref[0]} connections @ {ref[1]} Hz · " + ", ".join(tests),
                       ["Status"] + [title for title, _ in columns], table_rows))

    # Scaling still requires the complete, identical six-test suite in both sessions.
    axes = scaling_axes(scenarios)
    if axes:
        cols2 = [f"{g}\n{label}" for _, _, label, _, _ in axes for g in ("Bandwidth", "Server CPU")]
        cells2 = []
        for frm, to, _, units, _ in axes:
            for mid, unit in (("srvDown", "KB/s"), ("cpu", "pts")):
                vals = [marginal(by, n, frm, to, mid, units) for n in netcodes]
                if mid == "srvDown":
                    vals = [v / 1024 if v is not None else None for v in vals]
                cells2.append(mark_best([(v, fmt_cost(v, unit)) for v in vals], rel=0.05))
        rows2 = [(NAMES[n], colors[n], [c[i] for c in cells2]) for i, n in enumerate(netcodes)]
        note2 = "marginal server cost; " + "; ".join(note for _, _, _, _, note in axes)
        blocks.append(("What one more costs", note2, cols2, rows2))

    if args.svg_out:
        out_dir = Path(args.svg_out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for theme in ("light", "dark"):
            themed = [(t, s, c, [(l, SERIES[theme][n] if color else None, cells) for (l, color, cells), n in zip(r, netcodes + [None] * len(r))]) for (t, s, c, r) in blocks]
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
    lines.append("Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.")
    links = []
    if args.report_url:
        links.append(f"[interactive report]({args.report_url})")
    if args.run_url:
        links.append(f"[workflow run]({args.run_url})")
    links.append("[raw datapoints](latest.json)")
    lines.append("Full results: " + " · ".join(links) + ".")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
