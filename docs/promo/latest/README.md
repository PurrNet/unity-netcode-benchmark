# PurrNet promotional benchmark charts

0 charts, with 1920 × 1080 PNG and matching SVG exports, from **2026-11-09**.

[PurrNet 1.26.0-beta.7 · FishNet 4.7.3](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42642262967)

These are selected resource comparisons, not an overall netcode ranking. Each chart includes all five netcodes on a linear scale starting at zero. Asterisks and hatching mark overload. Relative percentages use unrounded values and round to the nearest whole percent.

## Charts unavailable for this run

- 01-state-bandwidth: PurrNet at 100 connections / 20 Hz: no datapoint
- 02-messaging-cpu: PurrNet at 100 connections / 20 Hz: no datapoint
- 03-general-gc: PurrNet at 100 connections / 20 Hz: no datapoint
- 04-connection-scaling: PurrNet at 10 connections / 20 Hz: no datapoint

Unavailable charts are omitted from this bundle; images from earlier runs are not retained here.

## Source and calculation

- [Workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42642262967)
- [Exact raw data used for these images](source-data.json)
- [Run metadata and original summary](source-summary.md)
- [Plotted values, claims and skipped charts](chart-data.json)
- Raw data SHA-256: `4e9d59379373f0d2a405b0c3204c451feab6e110fec708856ad5ee45969b3894`
- Renderer checkout revision: `7c564e4f04a339e45c36363527fe05119410bffb`. This identifies the code checkout, not the data snapshot.
- Lower/higher comparisons use `100 × (PurrNet / named competitor − 1)`. Zero baselines and overloaded comparators receive neutral text.
- Bandwidth and CPU categories use arithmetic means. General GC uses the six active workloads. Scaling averages their per-test `(100 connections − 10 connections) / 90` bandwidth deltas.
- Idle and Static are excluded. Missing or incomplete workloads are not treated as zero.
- GC labels distinguish heap-growth estimates from profiler counters. A mixture of those methods makes the GC chart unavailable.
- Source, units and full workload names are retained in the bundled data; the images use short workload descriptions.

## Regenerate

Install the pinned dependencies with `python -m pip install -r .github/scripts/requirements-promo.txt`, then run from the repository root:

```sh
python .github/scripts/render-promo.py --ci --output docs/promo/latest
```

Use `--chart 03-general-gc` to select one chart. To reproduce this particular bundle, supply its `source-data.json` with `--data` and `source-summary.md` with `--summary`. A render replaces the generated chart bundle in its output directory, including removing skipped or unselected images.

`--ci` skips unsupported comparisons with reasons in this README and `chart-data.json`; unexpected errors still fail the job. Without `--ci`, an unavailable comparison raises an error.
