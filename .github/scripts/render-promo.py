#!/usr/bin/env python3
"""Render promotional PNG/SVG charts from the same data and rules as the report.

Requires Matplotlib and Pillow. Example, from the repository root:
  python .github/scripts/render-promo.py
Render only the GC chart with --chart 03-general-gc.
The default dated output directory is derived from docs/latest.md.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import tempfile
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
CHART_SLUGS = ("01-state-bandwidth", "02-messaging-cpu", "03-general-gc", "04-connection-scaling")


def setup_fonts(family=None):
    # Use the OS font when available; Matplotlib's bundled font is the fallback.
    for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            font_manager.fontManager.addfont(str(path))
    family = family or ("Segoe UI" if Path("C:/Windows/Fonts/segoeui.ttf").exists() else "DejaVu Sans")
    plt.rcParams.update({"font.family": family, "font.size": 14, "text.color": INK,
                         "axes.labelcolor": MUTED, "xtick.color": MUTED,
                         "svg.fonttype": "path", "svg.hashsalt": "purrnet-promo"})


def text(fig, x, y, s, size=16, color=INK, weight="normal", **kwargs):
    item = fig.text(x / W, 1 - y / H, s, fontsize=size, color=color,
                    weight=weight, va="top", **kwargs)
    # CI uses Matplotlib's bundled font, which is wider than Segoe UI.
    if kwargs.get("ha") != "right":
        width = item.get_window_extent(fig.canvas.get_renderer()).width
        available = 1816 - x
        if width > available:
            item.set_fontsize(size * available / width)
    return item


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
        label_item = ax.text((104 - plot_left) / plot_width * card["axis_max"], i, label, ha="left", va="center",
                color=color if row["netcode"] == "purrnet" else INK,
                fontsize=16, weight="bold" if row["netcode"] == "purrnet" else "normal")
        label_width = label_item.get_window_extent(fig.canvas.get_renderer()).width
        if label_width > plot_left - 128:
            label_item.set_fontsize(16 * (plot_left - 128) / label_width)
        ax.text(row["value"] + 0.014 * card["axis_max"], i, card["value_format"].format(row["value"]),
                va="center", fontsize=16, color=color if row["netcode"] == "purrnet" else INK,
                weight="bold" if row["netcode"] == "purrnet" else "normal", clip_on=False,
                bbox={"facecolor": BG, "edgecolor": "none", "pad": 2})
    text(fig, 104, 861, card["chart_note"], 12, color=MUTED)
    text(fig, 104, 900, card["figure_method"], 12, color=MUTED)
    line(fig, 104, 950, 1816, 950)
    text(fig, 104, 975, card["footer"], 12, color=MUTED)
    fig.savefig(out / f'{card["slug"]}.png', dpi=120, facecolor=BG,
                metadata={"Title": card["alt"], "Description": card["method"] + " " + card["caveat"]})
    fig.savefig(out / f'{card["slug"]}.svg', facecolor=BG,
                metadata={"Title": card["alt"], "Description": card["method"] + " " + card["caveat"], "Date": metadata["date"]})
    plt.close(fig)


class ChartUnavailable(ValueError):
    """The run cannot support this comparison; CI records why and skips it."""


def number(value, label, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ChartUnavailable(f"{label}: missing or non-finite measurement")
    if value < 0 or (positive and value == 0):
        raise ChartUnavailable(f"{label}: invalid negative or zero measurement")
    return value


def run_index(data):
    if not isinstance(data, list):
        raise ValueError("Expected a list of benchmark datapoints")
    by = {}
    for run in data:
        key = (run["netcode"], (run.get("size", run.get("connections")), run.get("tick")))
        if key in by:
            raise ValueError(f"Duplicate benchmark datapoint: {key}")
        by[key] = run
    return by


def required_runs(by, sessions, tests, field, *, full_suite=False):
    runs = []
    for session in sessions:
        for netcode in summary.ORDER:
            label = f"{summary.NAMES[netcode]} at {session[0]} connections / {session[1]} Hz"
            run = by.get((netcode, session))
            failure = summary.run_failure(run) if full_suite else summary.category_failure(run, tests)
            if failure:
                raise ChartUnavailable(f"{label}: {failure}")
            meta = run.get("meta") or {}
            if any(v != session[0] for v in (run.get("connections"), meta.get("connectedAtStart"), meta.get("expectedClients"))):
                raise ChartUnavailable(f"{label}: actual connection count does not match the session")
            if meta.get("tickRate") != session[1]:
                raise ChartUnavailable(f"{label}: actual tick rate does not match the session")
            for test in tests:
                window = run["server"][test]
                if window.get("connections") != session[0]:
                    raise ChartUnavailable(f"{label}: connections changed during {test}")
                number(window.get(field), f"{label} / {test} / {field}")
                number(window.get("windowSeconds"), f"{label} / {test} / duration", positive=True)
                number(window.get("p99FrameMs"), f"{label} / {test} / frame p99")
                number(window.get("avgFps"), f"{label} / {test} / FPS", positive=True)
                number(window.get("objects"), f"{label} / {test} / objects", positive=True)
            runs.append(run)
    return runs


def conditions(runs, tests, *, cpu=False):
    build_modes = [r["meta"].get("devBuild") for r in runs]
    modes = set(build_modes)
    if any(type(mode) is not bool for mode in build_modes) or len(modes) != 1:
        raise ChartUnavailable("Build mode is missing or differs between netcodes")
    unity = {r["meta"].get("unityVersion") for r in runs}
    if len(unity) != 1 or not next(iter(unity)):
        raise ChartUnavailable("Unity version is missing or differs between netcodes")
    cpus = {r["meta"].get("cpuModel") for r in runs}
    if cpu and (len(cpus) != 1 or not next(iter(cpus))):
        raise ChartUnavailable("Server CPU model is missing or differs between netcodes")
    # Churn can be sampled between despawn and respawn. Its instantaneous object
    # count is not the configured object target. Client input uses a single hub.
    objects = {r["server"][t]["objects"] for r in runs for t in tests if t not in ("SpawnChurn", "ClientInput")}
    if len(objects) != 1:
        raise ChartUnavailable("Replicated object count differs between the compared workloads")
    for r in runs:
        if "ClientInput" in tests and r["server"]["ClientInput"]["objects"] != 1:
            raise ChartUnavailable("Client-input workload does not use the expected single hub")
    durations = [r["server"][t]["windowSeconds"] for r in runs for t in tests]
    lo, hi = round(min(durations), 1), round(max(durations), 1)
    window_text = f"{lo:g} s windows" if lo == hi else f"{lo:g}–{hi:g} s windows"
    model = next(iter(cpus)) if len(cpus) == 1 else "Multiple server CPUs"
    model = re.sub(r"\s+\d+-Core Processor$", "", model or "Server CPU unknown")
    footer = f"{model}, Unity {next(iter(unity))}, {'development' if next(iter(modes)) else 'release'} build"
    fps = {r["meta"].get("targetFps") for r in runs}
    # The report's overload thresholds assume 60 fps. Older aggregates omitted
    # this field; explicit settings must match that assumption across the run.
    if fps != {None}:
        if len(fps) != 1:
            raise ChartUnavailable("Frame cap is missing or differs between netcodes")
        cap = number(next(iter(fps)), "Frame cap", positive=True)
        if cap != 60:
            raise ChartUnavailable("Overload comparisons require the benchmark's 60 fps frame cap")
        footer += f", {cap:g} fps cap"
    return dict(objects=next(iter(objects)), windows=window_text, footer=footer)


def axis_range(values, minimum, step):
    largest = max(values)
    if largest <= minimum:
        return minimum, step
    rough = largest / 4
    scale = 10 ** math.floor(math.log10(rough))
    step = next(x for x in (1, 2, 2.5, 5, 10) if x * scale >= rough) * scale
    return math.ceil(largest * 1.1 / step) * step, step


def comparison(value, baseline, name):
    if baseline == 0:
        return f"the same as {name}" if value == 0 else None
    change = (value / baseline - 1) * 100
    rounded = round(abs(change))
    if rounded == 0:
        return f"approximately the same as {name}"
    return f"{rounded}% {'lower' if change < 0 else 'higher'} than {name}"


def build_cards(data, selected=None, *, ci=False, skipped=None):
    by = run_index(data)
    skipped = skipped if skipped is not None else {}
    configs = {
        "01-state-bandwidth": dict(tests=["MoveY", "MoveWander", "SyncVars"], field="txBytesPerSec",
            divisor=1024**2, title="State replication bandwidth", noun="downstream bandwidth",
            units="Server downstream, MiB/s", scope="across the state replication workloads",
            baseline="fishnet", axis=5.2, step=1, value_format="{:.2f}",
            workload="NetworkTransform + SyncVars"),
        "02-messaging-cpu": dict(tests=["SendRPC", "ClientInput"], field="cpuPercent",
            divisor=1, title="Messaging server CPU", noun="server CPU usage",
            units="Whole-process CPU, % of one core", scope="in the messaging workloads",
            baseline="mirror", axis=40, step=10, value_format="{:.1f}%",
            workload="RPCs: server broadcasts + client inputs"),
        "03-general-gc": dict(tests=summary.SCORE_TESTS, field="gcAllocBytesPerSec",
            divisor=1024, title="GC allocation across workloads", noun="GC allocation rate",
            units="Server GC allocation, KiB/s", scope="across the active workloads",
            baseline="fishnet", axis=4000, step=1000, value_format="{:,.0f}",
            workload="NetworkTransform + SyncVars + RPCs + spawn/despawn"),
        "04-connection-scaling": dict(tests=summary.SCORE_TESTS, field="txBytesPerSec",
            divisor=1024, title="Bandwidth per added connection", noun="additional downstream bandwidth per connection",
            units="Added server downstream, KiB/s per connection", scope="from 10 to 100 connections",
            baseline="fishnet", axis=36, step=10, value_format="{:.1f}",
            workload="NetworkTransform + SyncVars + RPCs + spawn/despawn"),
    }
    if selected is not None and selected not in configs:
        raise ValueError(f"Unknown chart: {selected}")
    cards = []
    for index, (slug, config) in enumerate(configs.items(), 1):
        if selected and selected != slug:
            continue
        try:
            scaling = slug == "04-connection-scaling"
            sessions = [(10, 20), (100, 20)] if scaling else [(100, 20)]
            tests = config["tests"]
            runs = required_runs(by, sessions, tests, config["field"], full_suite=scaling)
            context = conditions(runs, tests, cpu=slug == "02-messaging-cpu")
            allocation_estimated = None
            if slug == "03-general-gc":
                modes = [r["server"][t].get("gcAllocEstimated") for r in runs for t in tests]
                if any(type(mode) is not bool for mode in modes) or len(set(modes)) != 1:
                    raise ChartUnavailable("GC allocation methods are missing or mixed between heap estimates and profiler counters")
                allocation_estimated = modes[0]
            rows = []
            for netcode in summary.ORDER:
                cases = [r for r in runs if r["netcode"] == netcode]
                if scaling:
                    # Same arithmetic mean as the report, without inspecting unrelated metrics.
                    value = summary.mean([(cases[1]["server"][t][config["field"]] - cases[0]["server"][t][config["field"]]) / 90
                                          for t in tests]) / config["divisor"]
                else:
                    value = summary.mean([cases[0]["server"][t][config["field"]] for t in tests]) / config["divisor"]
                number(value, f"{summary.NAMES[netcode]} / {slug}")
                rows.append(dict(netcode=netcode, value=value,
                    overloaded=sum(summary.overloaded(r, t) for r in cases for t in tests), tests=list(tests)))
            indexed = {row["netcode"]: row for row in rows}
            purr, baseline = indexed["purrnet"], indexed[config["baseline"]]
            claim_allowed = not purr["overloaded"] and not baseline["overloaded"]
            reduction = (1 - purr["value"] / baseline["value"]) * 100 if baseline["value"] > 0 and claim_allowed else None
            phrase = comparison(purr["value"], baseline["value"], summary.NAMES[config["baseline"]]) if claim_allowed else None
            noun = ("estimated " if allocation_estimated else "") + config["noun"]
            if phrase:
                if slug == "02-messaging-cpu" and not indexed["fishnet"]["overloaded"]:
                    secondary = comparison(purr["value"], indexed["fishnet"]["value"], "FishNet")
                    if secondary:
                        phrase += " and " + secondary
                takeaway = f"PurrNet’s {noun} was {phrase} {config['scope']}."
            else:
                takeaway = f"Measured {noun} {config['scope']}."
            total_tests = len(tests) * len(sessions)
            overloaded = [f"{summary.NAMES[row['netcode']]}: {row['overloaded']}/{total_tests} workloads overloaded"
                          for row in rows if row["overloaded"]]
            chart_note = "* " + "; ".join(overloaded) + "." if overloaded else ""
            axis_max, tick_step = axis_range([row["value"] for row in rows], config["axis"], config["step"])
            if slug == "01-state-bandwidth":
                figure_method = f"Mean of three transform and synced-variable workloads. {context['objects']:g} objects, {context['windows']}."
            elif slug == "02-messaging-cpu":
                figure_method = f"Mean of two RPC workloads: broadcasts on {context['objects']:g} objects + client inputs. {context['windows']}. No idle subtraction."
            elif slug == "03-general-gc":
                figure_method = f"Mean allocation rate across six active workloads, {context['windows']}. Idle connections and static objects excluded."
            else:
                figure_method = f"Mean of six active workload deltas: (downstream at 100 connections − at 10) / 90. {context['windows']}."
            session_label = "10 → 100 connections, 20 Hz" if scaling else "100 connections, 20 Hz"
            units = config["units"]
            if allocation_estimated:
                units = "Estimated " + units.lower()
            method = ("Mean of per-test (100-connection − 10-connection) server downstream / 90."
                      if scaling else f"Arithmetic mean of server {config['field']}.")
            method += f" Tests: {', '.join(tests)}. Sessions: {session_label}. {context['windows']}. "
            method += "No idle subtraction. Binary byte units (1 KiB = 1,024 bytes)."
            caveat = "One published run. Overloaded rows describe saturated servers and are not used for comparative claims."
            if slug == "03-general-gc":
                caveat += (" Allocation is estimated from frame-to-frame managed-heap growth, using a running average when collection shrinks the heap."
                           if allocation_estimated else " Allocation is measured by the profiler allocation counter.")
            card = dict(slug=slug, number=index, chart_title=config["title"], takeaway=takeaway,
                kicker=config["workload"] + ", " + session_label, chart_subtitle=units + ", lower is better",
                rows=rows, baseline=config["baseline"], axis_max=axis_max, tick_step=tick_step,
                value_format=config["value_format"], chart_note=chart_note, figure_method=figure_method,
                method=method, caveat=caveat, footer=context["footer"],
                allocation_estimated=allocation_estimated, reduction_percent=reduction,
                reduction_percent_rounded=round(reduction) if reduction is not None else None)
            card["alt"] = card["chart_title"] + ". " + takeaway + " " + card["kicker"] + "."
            cards.append(card)
        except ChartUnavailable as error:
            if not ci:
                raise
            skipped[slug] = str(error)
    return cards


def parse_metadata(raw, markdown, revision):
    header = re.search(r"_Last run (\d{4}-\d{2}-\d{2}): (.+?) · Unity ([^ ·]+)", markdown)
    run = re.search(r"https://github.com/[^)\s]+/actions/runs/\d+", markdown)
    if not header or not run:
        raise ValueError("Summary must contain a run date, versions, Unity version and workflow URL")
    date, versions, unity = header.groups()
    version_parts = versions.split(" · ")
    netcode_versions = {netcode: next((part[len(name) + 1:] for part in version_parts if part.startswith(name + " ")), "version unknown")
                        for netcode, name in summary.NAMES.items()}
    return dict(date=date, run_url=run.group(), run_id=run.group().rsplit("/", 1)[1],
        versions=versions, netcode_versions=netcode_versions, unity_version=unity,
        source_revision=revision, source_sha256=hashlib.sha256(raw).hexdigest(),
        source_data="source-data.json", source_summary="source-summary.md", size=[W, H],
        note="One published run. Selected resource comparisons, no overall ranking.")


def write_readme(metadata, cards, out, skipped=None):
    skipped = skipped or {}
    lines = ["# PurrNet promotional benchmark charts", "",
        f'{len(cards)} {"chart" if len(cards) == 1 else "charts"}, with 1920 × 1080 PNG and matching SVG exports, from **{metadata["date"]}**.', "",
        f'[{metadata["versions"]}]({metadata["run_url"]})', "",
        "These are selected resource comparisons, not an overall netcode ranking. Each chart includes all five netcodes on a linear scale starting at zero. Asterisks and hatching mark overload. Relative percentages use unrounded values and round to the nearest whole percent.", ""]
    if skipped:
        lines += ["## Charts unavailable for this run", ""]
        lines += [f"- {slug}: {reason}" for slug, reason in skipped.items()]
        lines += ["", "Unavailable charts are omitted from this bundle; images from earlier runs are not retained here.", ""]
    for card in cards:
        lines += [f'## {card["chart_title"]}', "", card["alt"], "",
            f'![{card["alt"]}]({card["slug"]}.png)', "",
            f'[PNG]({card["slug"]}.png) / [SVG]({card["slug"]}.svg)', "",
            card["method"], "", card["caveat"], ""]
    lines += ["## Source and calculation", "",
        f'- [Workflow run]({metadata["run_url"]})',
        '- [Exact raw data used for these images](source-data.json)',
        '- [Run metadata and original summary](source-summary.md)',
        '- [Plotted values, claims and skipped charts](chart-data.json)',
        f'- Raw data SHA-256: \x60{metadata["source_sha256"]}\x60',
        f'- Renderer checkout revision: \x60{metadata["source_revision"]}\x60. This identifies the code checkout, not the data snapshot.',
        '- Lower/higher comparisons use \x60100 × (PurrNet / named competitor − 1)\x60. Zero baselines and overloaded comparators receive neutral text.',
        '- Bandwidth and CPU categories use arithmetic means. General GC uses the six active workloads. Scaling averages their per-test \x60(100 connections − 10 connections) / 90\x60 bandwidth deltas.',
        '- Idle and Static are excluded. Missing or incomplete workloads are not treated as zero.',
        '- GC labels distinguish heap-growth estimates from profiler counters. A mixture of those methods makes the GC chart unavailable.',
        '- Source, units and full workload names are retained in the bundled data; the images use short workload descriptions.', "",
        "## Regenerate", "",
        "Install the pinned dependencies with \x60python -m pip install -r .github/scripts/requirements-promo.txt\x60, then run from the repository root:", "", "\x60\x60\x60sh",
        "python .github/scripts/render-promo.py --ci --output docs/promo/latest",
        "\x60\x60\x60", "",
        "Use \x60--chart 03-general-gc\x60 to select one chart. To reproduce this particular bundle, supply its \x60source-data.json\x60 with \x60--data\x60 and \x60source-summary.md\x60 with \x60--summary\x60. A render replaces the generated chart bundle in its output directory, including removing skipped or unselected images.", "",
        "\x60--ci\x60 skips unsupported comparisons with reasons in this README and \x60chart-data.json\x60; unexpected errors still fail the job. Without \x60--ci\x60, an unavailable comparison raises an error.", ""]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_bundle(cards, metadata, skipped, raw, markdown, output):
    """Render completely before changing managed output files; never touch archives/assets."""
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    managed = {slug + suffix for slug in CHART_SLUGS for suffix in (".png", ".svg")}
    managed.update(("README.md", "chart-data.json", "source-data.json", "source-summary.md"))
    with tempfile.TemporaryDirectory(prefix=".promo-", dir=output.parent) as temporary:
        staging = Path(temporary).resolve()
        if staging.parent != output.parent:
            raise ValueError("Temporary render directory is outside the intended output parent")
        for card in cards:
            draw_card(card, metadata, staging)
        (staging / "chart-data.json").write_text(json.dumps(dict(metadata=metadata, charts=cards, skipped=skipped),
            indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        (staging / "source-data.json").write_bytes(raw)
        (staging / "source-summary.md").write_text(markdown, encoding="utf-8")
        write_readme(metadata, cards, staging, skipped)
        output.mkdir(parents=True, exist_ok=True)
        staged = {path.name for path in staging.iterdir()}
        for name in sorted(managed - staged):
            (output / name).unlink(missing_ok=True)
        for name in sorted(staged):
            os.replace(staging / name, output / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "docs/latest.json")
    parser.add_argument("--summary", type=Path, default=ROOT / "docs/latest.md")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default=None, help="Code checkout revision, not the data revision.")
    parser.add_argument("--chart", choices=CHART_SLUGS, help="Render just one chart (default: all four).")
    parser.add_argument("--ci", action="store_true", help="Skip unsupported comparisons with recorded reasons.")
    parser.add_argument("--font-family", help="Override the font; CI defaults to Matplotlib's bundled DejaVu Sans.")
    args = parser.parse_args()
    raw = args.data.read_bytes()
    markdown = args.summary.read_text(encoding="utf-8")
    if args.source_revision is None:
        import subprocess
        args.source_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    metadata = parse_metadata(raw, markdown, args.source_revision)
    skipped = {}
    cards = build_cards(json.loads(raw), args.chart, ci=args.ci, skipped=skipped)
    output = args.output or ROOT / "docs/promo" / metadata["date"]
    setup_fonts(args.font_family)
    write_bundle(cards, metadata, skipped, raw, markdown, output)
    for card in cards:
        print(f'{card["slug"]}: {card["takeaway"]}')
    for slug, reason in skipped.items():
        print(f"Skipped {slug}: {reason}")
    print(f"Wrote {len(cards)} PNG/SVG pairs to {output}")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary_file:
            summary_file.write(f"\n### Promotional charts\n\nGenerated {len(cards)} PNG/SVG pairs; {len(skipped)} unavailable. Included in the benchmark-results artifact.\n")
            for slug, reason in skipped.items():
                summary_file.write(f"\n- {slug}: {reason}\n")


if __name__ == "__main__":
    main()
