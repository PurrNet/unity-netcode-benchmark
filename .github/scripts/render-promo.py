#!/usr/bin/env python3
"""Render promotional PNG/SVG charts from the same data and rules as the report.

Requires Matplotlib and Pillow. Example, from the repository root:
  python .github/scripts/render-promo.py
The default dated output directory is derived from docs/latest.md.
"""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from matplotlib.lines import Line2D
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
LOGO = ROOT / "docs/promo/assets/purrnet-logo-orange.png"
spec = importlib.util.spec_from_file_location("summary", Path(__file__).with_name("render-summary.py"))
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)

BG = "#111417"
INK = "#f5f2ea"
MUTED = "#adb4bb"
GRID = "#343d45"
ORANGE = "#ff854c"
OTHER = "#8b9298"
W, H = 1920, 1080


def setup_fonts():
    # Use the OS font when available; Matplotlib's bundled font is the fallback.
    for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            font_manager.fontManager.addfont(str(path))
    family = "Segoe UI" if Path("C:/Windows/Fonts/segoeui.ttf").exists() else "DejaVu Sans"
    plt.rcParams.update({"font.family": family, "font.size": 14, "text.color": INK,
                         "axes.labelcolor": MUTED, "xtick.color": MUTED,
                         "svg.fonttype": "path", "svg.hashsalt": "purrnet-promo"})


def text(fig, x, y, s, size=16, color=INK, weight="normal", **kwargs):
    return fig.text(x / W, 1 - y / H, s, fontsize=size, color=color,
                    weight=weight, va="top", **kwargs)


def line(fig, x1, y1, x2, y2, color=GRID):
    fig.add_artist(Line2D([x1 / W, x2 / W], [1 - y1 / H, 1 - y2 / H],
                          transform=fig.transFigure, color=color, linewidth=0.8))


def draw_card(card, metadata, out):
    fig = plt.figure(figsize=(16, 9), dpi=120, facecolor=BG)
    with Image.open(LOGO) as source:
        logo = source.convert("RGBA")
    logo_height = 66
    logo_width = logo_height * logo.width / logo.height
    logo_ax = fig.add_axes([104 / W, 1 - 111 / H, logo_width / W, logo_height / H])
    logo_ax.imshow(logo, interpolation="lanczos")
    logo_ax.set_axis_off()
    text(fig, 185, 62, "PurrNet", 21, color=INK, weight="bold")
    text(fig, 373, 72, "Unity netcode benchmark", 13, color=MUTED)
    text(fig, 1816, 72, metadata["date"], 13, color=MUTED, ha="right")
    line(fig, 104, 120, 1816, 120)
    text(fig, 102, 162, card["chart_title"], 35, weight="bold")
    text(fig, 104, 240, card["takeaway"], 18, color=ORANGE)
    text(fig, 104, 293, card["kicker"], 13, color=MUTED)
    text(fig, 104, 359, card["chart_subtitle"], 13, color=MUTED)

    plot_left, plot_width = 560, 1106
    ax = fig.add_axes([plot_left / W, 1 - 804 / H, plot_width / W, 384 / H], facecolor=BG)
    rows = sorted(card["rows"], key=lambda row: row["value"])
    ax.set_xlim(0, card["axis_max"])
    ax.set_ylim(-0.5, len(rows) - 0.5)
    ax.invert_yaxis()
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(card["tick_step"]))
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:g}"))
    ax.xaxis.grid(True, color=GRID, linewidth=0.7)
    ax.tick_params(axis="x", length=0, labelsize=12, pad=12)
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i, row in enumerate(rows):
        color = ORANGE if row["netcode"] == "purrnet" else OTHER
        ax.barh(i, row["value"], height=0.44, color=color, zorder=3,
                alpha=0.40 if row["overloaded"] else 1,
                hatch="///" if row["overloaded"] else None,
                edgecolor=color if row["overloaded"] else "none", linewidth=0)
        label = (summary.NAMES[row["netcode"]] + " " + metadata["netcode_versions"][row["netcode"]]
                 + ("*" if row["overloaded"] else ""))
        ax.text((104 - plot_left) / plot_width * card["axis_max"], i, label, ha="left", va="center",
                color=color if row["netcode"] == "purrnet" else INK,
                fontsize=16, weight="bold" if row["netcode"] == "purrnet" else "normal")
        ax.text(row["value"] + 0.014 * card["axis_max"], i, card["value_format"].format(row["value"]),
                va="center", fontsize=16, color=color if row["netcode"] == "purrnet" else INK,
                weight="bold" if row["netcode"] == "purrnet" else "normal", clip_on=False,
                bbox={"facecolor": BG, "edgecolor": "none", "pad": 2})
    text(fig, 104, 861, card["chart_note"], 12, color=MUTED)
    text(fig, 104, 900, card["figure_method"], 12, color=MUTED)
    line(fig, 104, 950, 1816, 950)
    text(fig, 104, 975, "Dedicated Ryzen 5 3600 server, Unity " + metadata["unity_version"] + ", 60 fps cap", 12, color=MUTED)
    fig.savefig(out / f'{card["slug"]}.png', dpi=120, facecolor=BG,
                metadata={"Title": card["alt"], "Description": card["method"] + " " + card["caveat"]})
    fig.savefig(out / f'{card["slug"]}.svg', facecolor=BG,
                metadata={"Title": card["alt"], "Description": card["method"] + " " + card["caveat"], "Date": metadata["date"]})
    plt.close(fig)


def build_cards(data):
    by = {(r["netcode"], (r["connections"], r["tick"])): r for r in data}
    ref = (100, 20)
    def category_rows(tests, metric, divisor=1):
        scores = summary.scorecard(summary.ORDER, by, ref, tests)
        rows = []
        for n in summary.ORDER:
            row = scores[n]
            if row["error"] or row[metric] is None:
                raise ValueError(f"{n}: {tests}: cannot chart missing/incomplete metric")
            rows.append({"netcode": n, "value": row[metric] / divisor,
                         "overloaded": row["overloaded"], "tests": tests})
        return rows
    state = category_rows(["MoveY", "MoveWander", "SyncVars"], "bw", 1024**2)
    messaging = category_rows(["SendRPC", "ClientInput"], "cpu")
    general_gc = category_rows(summary.SCORE_TESTS, "alloc", 1024)
    for n in summary.ORDER:
        for test in summary.SCORE_TESTS:
            if by[n, ref]["server"][test].get("gcAllocEstimated") is not True:
                raise ValueError("Update the allocation chart's method note for this dataset")
    scaling = []
    for n in summary.ORDER:
        value = summary.marginal(by, n, (10, 20), ref, "srvDown", 90)
        if value is None:
            raise ValueError(f"{n}: scaling requires two complete suites")
        scaling.append({"netcode": n, "value": value / 1024,
                        "overloaded": sum(summary.overloaded(by[n, sc], t)
                                          for sc in ((10, 20), ref) for t in summary.SCORE_TESTS),
                        "tests": summary.SCORE_TESTS})
    cards = [
        dict(slug="01-state-bandwidth", kicker="NetworkTransform + SyncVars, 100 connections, 20 Hz",
             takeaway="PurrNet used {reduction}% less downstream bandwidth than FishNet across the state replication tests.",
             figure_method="Mean of three transform and synced-variable workloads. 100 objects, 10 s windows. On-wire server downstream.",
             figure_caveat="Single run; variability not measured. Fusion used Photon relay; replication behavior differs between netcodes.",
             chart_title="State replication bandwidth", chart_subtitle="Server downstream, MiB/s, lower is better",
             rows=state, baseline="fishnet", axis_max=5.2, tick_step=1, value_format="{:.2f}",
             chart_note="* NGO completed all 3 tests with server overload.",
             method="Arithmetic mean: MoveY, MoveWander, SyncVars. 100 objects · 10 s per test · on-wire server downstream · 1 MiB = 1,048,576 bytes.",
             caveat="One benchmark run; no repeat variability measured. Native replication behavior differs. Fusion uses Photon relay. Full methodology at the link below."),
        dict(slug="02-messaging-cpu", kicker="RPCs: server broadcasts + client inputs, 100 connections, 20 Hz",
             takeaway="PurrNet used {reduction}% less server CPU than Mirror and {fishnet_reduction}% less than FishNet in the messaging tests.",
             figure_method="Mean of two RPC workloads: server broadcasts + client inputs. 10 s windows. Whole-process CPU, no idle subtraction.",
             figure_caveat="Benchmark + OS only. Observed CPU variation around ±1% (operator measurements). Fusion used Photon relay.",
             chart_title="Messaging server CPU", chart_subtitle="Whole-process CPU, % of one core, lower is better",
             rows=messaging, baseline="mirror", axis_max=40, tick_step=10, value_format="{:.1f}%",
             chart_note="* NGO completed both workloads; server-broadcast RPCs were overloaded.",
             method="Arithmetic mean: SendRPC and ClientInput. 100 connections · 20 Hz · 10 s per test · CPU includes all process threads, with no idle subtraction.",
             caveat="The benchmark operator reports CPU variation of around ±1% on a server running only the benchmark and OS. This is a separate operator observation, not a per-netcode error bound calculated from this snapshot. Same Ryzen 5 3600 server; 60 fps cap. Fusion uses Photon relay."),
        dict(slug="03-general-gc", kicker="NetworkTransform + SyncVars + RPCs + spawn/despawn, 100 connections, 20 Hz",
             takeaway="PurrNet’s estimated GC allocation rate was {reduction}% lower than FishNet’s across the active workloads.",
             figure_method="Mean allocation rate across six active workloads, 10 s windows. Idle connections and static objects excluded.",
             figure_caveat="Estimated from positive managed-heap growth between frames. Single run; variability not measured.",
             chart_title="GC allocation across workloads", chart_subtitle="Estimated server GC allocation, KiB/s, lower is better",
             rows=general_gc, baseline="fishnet", axis_max=4000, tick_step=1000, value_format="{:,.0f}",
             chart_note="* NGO completed all six workloads; " + str(next(row["overloaded"] for row in general_gc if row["netcode"] == "ngo")) + " were overloaded.",
             method="Arithmetic mean of server gcAllocBytesPerSec across MoveY, MoveWander, SyncVars, SendRPC, ClientInput and SpawnChurn at 100 connections and 20 Hz. 10 s windows; Idle and Static excluded. 1 KiB = 1,024 bytes.",
             caveat="Allocation is estimated from positive managed-heap growth between frames, not a precise allocation count. NGO includes overloaded workloads and is not eligible for a best-value claim. One run; no repeat variability measured."),
        dict(slug="04-connection-scaling", kicker="NetworkTransform + SyncVars + RPCs + spawn/despawn, 10 → 100 connections, 20 Hz",
             takeaway="PurrNet used {reduction}% less additional downstream bandwidth per connection than FishNet, from 10 to 100 connections.",
             figure_method="Average added bandwidth: (downstream at 100 connections − at 10) / 90 across six active workloads. 10 s windows.",
             figure_caveat="Observed cost over this interval, not a projection. Single run; variability not measured. Fusion used Photon relay.",
             chart_title="Bandwidth per added connection", chart_subtitle="Added server downstream, KiB/s per connection, lower is better",
             rows=scaling, baseline="fishnet", axis_max=36, tick_step=10, value_format="{:.1f}",
             chart_note="* NGO completed both suites; the 100-connection suite includes overload.",
             method="Mean across six load tests of (server downstream at 100 connections − at 10) / 90, at 20 Hz. 1 KiB = 1,024 bytes.",
             caveat="Observed marginal cost over this interval; not a per-player total or a projection. One run; no repeat variability measured. Fusion uses Photon relay."),
    ]
    for i, card in enumerate(cards, 1):
        values = {r["netcode"]: r["value"] for r in card["rows"]}
        if any(not 0 <= v <= card["axis_max"] for v in values.values()):
            raise ValueError("Update the chart axis: a value would be clipped")
        if next(r for r in card["rows"] if r["netcode"] == "purrnet")["overloaded"]:
            raise ValueError("PurrNet is overloaded; revisit the promotional claims")
        if next(r for r in card["rows"] if r["netcode"] == card["baseline"])["overloaded"]:
            raise ValueError("The named comparison is overloaded; revisit the promotional claim")
        reduction = (1 - values["purrnet"] / values[card["baseline"]]) * 100
        if reduction <= 0:
            raise ValueError("Headline no longer describes an advantage")
        card.update(number=i, reduction_percent=reduction, reduction_percent_rounded=round(reduction))
        card["takeaway"] = card["takeaway"].format(reduction=round(reduction),
                              fishnet_reduction=round((1 - values["purrnet"] / values["fishnet"]) * 100))
        card["alt"] = card["chart_title"] + ". " + card["takeaway"] + " " + card["kicker"] + "."
    return cards


def write_readme(metadata, cards, out):
    lines = ["# PurrNet promotional benchmark charts", "",
             f'Four 1920 × 1080 PNG images and matching scalable SVGs, based on the **{metadata["date"]}** published run.', "",
             f'[{metadata["versions"]}]({metadata["run_url"]})', "",
             "These are selected resource comparisons, not an overall netcode ranking. All five netcodes are shown on linear scales starting at zero. Overloaded rows remain visible and are marked. Percent reductions use unrounded raw values, rounded to the nearest whole percent.", ""]
    original = out.with_name(out.name + "-original")
    if original.is_dir():
        lines += [f'[First design pass, kept for comparison](../{original.name}/README.md)', ""]
    for card in cards:
        lines += [f'## {card["chart_title"]}', "", card["alt"], "",
                  f'![{card["alt"]}]({card["slug"]}.png)', "",
                  f'[PNG]({card["slug"]}.png) · [SVG]({card["slug"]}.svg)', "",
                  card["method"], "", card["caveat"], ""]
    lines += ["## Provenance and calculation", "",
              f'- [Source workflow run]({metadata["run_url"]})',
              '- [Full methodology and live report](https://purrnet.github.io/unity-netcode-benchmark/)',
              f'- [Raw source at the pulled revision](https://github.com/PurrNet/unity-netcode-benchmark/blob/{metadata["source_revision"]}/docs/latest.json)',
              f'- Source JSON SHA-256: `{metadata["source_sha256"]}`',
              '- [Exact plotted values and claims](chart-data.json)',
              '- [Supplied PurrNet logo](../assets/purrnet-logo-orange.png), embedded in every PNG and SVG header.',
              '- Reduction formula: `100 × (1 − PurrNet / named competitor)`.',
              '- Category values use the existing report’s arithmetic means and completion/overload rules.',
              '- Scaling averages six per-test deltas: MoveY, MoveWander, SyncVars, SendRPC, ClientInput, SpawnChurn.',
              '- General GC averages allocation rates across the same six active workloads at 100 connections and 20 Hz; Idle and Static are excluded.',
              '- State, messaging, general GC and scaling NGO rows include overload. This can make resource use lower than equivalent unsaturated service; they are not eligible for best-value claims.',
              '- Allocation is a positive heap-growth estimate, not the profiler allocation counter or process memory usage.',
              '- Individual versions, transport differences, replication behavior, and benchmark overrides are documented in the full methodology.', "",
              "## Regenerate", "", "Install `matplotlib` and `pillow`, then run from the repository root:", "", "```sh",
              "python .github/scripts/render-promo.py", "```", "",
              "This reads `docs/latest.json` and the run metadata in `docs/latest.md`, and writes a dated folder under `docs/promo/`. To reproduce an older run, pass its matching `--data` and `--summary` files, plus `--source-revision` and `--output`. The renderer stops when required data are missing or the highlighted result is overloaded.", ""]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "docs/latest.json")
    parser.add_argument("--summary", type=Path, default=ROOT / "docs/latest.md")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default=None)
    args = parser.parse_args()
    raw = args.data.read_bytes()
    md = args.summary.read_text(encoding="utf-8")
    date = re.search(r"Last run (\d{4}-\d{2}-\d{2})", md).group(1)
    run_url = re.search(r"https://github.com/[^)]+/actions/runs/\d+", md).group(0)
    versions = md.split(": ", 1)[1].split(" · Unity", 1)[0]
    version_parts = versions.split(" · ")
    netcode_versions = {
        netcode: next(part[len(name) + 1:] for part in version_parts if part.startswith(name + " "))
        for netcode, name in summary.NAMES.items()
    }
    unity_version = re.search(r" · Unity ([^ ·]+)", md).group(1)
    if args.source_revision is None:
        import subprocess
        args.source_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    metadata = dict(date=date, run_url=run_url, run_id=run_url.rsplit("/", 1)[1],
                    versions=versions, netcode_versions=netcode_versions, unity_version=unity_version, source_revision=args.source_revision,
                    source_sha256=hashlib.sha256(raw).hexdigest(),
                    source_data="docs/latest.json", size=[W, H],
                    note="One published run. CPU stability observation supplied separately by the benchmark operator. Selected categories, no overall ranking.")
    cards = build_cards(json.loads(raw))
    out = args.output or ROOT / "docs/promo" / date
    out.mkdir(parents=True, exist_ok=True)
    setup_fonts()
    for card in cards:
        draw_card(card, metadata, out)
        print(f'{card["slug"]}: {card["reduction_percent"]:.9f}% reduction vs {card["baseline"]}')
    (out / "chart-data.json").write_text(json.dumps(dict(metadata=metadata, charts=cards), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(metadata, cards, out)
    print(f"Wrote {len(cards)} PNGs + SVGs to {out}")


if __name__ == "__main__":
    main()
