# Release prediction baseline

[Frozen run 38763353030](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/38763353030)
completed 32 valid cases on one hosted runner: four clients, 60 Hz, 128/512 total objects,
20 seconds warmup, 30 seconds sampling, and four fresh-process repeats per adapter/workload.
Adapter order rotated each repeat. All 160 peer reports converged in release IL2CPP with
detailed diagnostics off. PurrDiction used `a3489811` with PurrNet `fd4b1fbe`.

CPU is whole-process CPU across all threads, expressed as a percentage of one core. Each
client figure averages the four clients within a repeat, then takes the median across repeats.

| Adapter | 128 client CPU % | 128 server CPU % | 512 client CPU % | 512 server CPU % |
|---|---:|---:|---:|---:|
| PurrDiction FullPrediction | 4.11 | 5.27 | 11.43 | 15.07 |
| PurrDiction PredictedIfOwned | 4.03 | 4.87 | 11.56 | 14.93 |
| FishNet | 3.91 | 4.78 | 14.44 | 15.40 |
| Fusion Server mode | 4.52 | 4.63 | 6.17 | 5.41 |

The larger workload shows lower PurrDiction client CPU than FishNet, similar server figures,
and substantially lower Fusion CPU. Smaller differences need repeat comparisons: subsequent
identical-player controls have produced apparent server improvements of several percent.
These controls provide context; CPU scores here remain unadjusted.

The adapters provide different services. FullPrediction rolls back the world; PredictedIfOwned
predicts owned objects and runs verified ServerRelay ticks for remote objects. FishNet uses
owned/spectator prediction with state forwarding, while Fusion predicts input-authority objects
and replicates proxies. Fusion sends one 12-byte command per player/tick shared by owned pawns;
PurrDiction and FishNet supply commands per owned pawn. This sequenced-state workload uses the
same logical command generator, without independent per-pawn controls. Fusion uses Photon
Cloud; the other adapters use loopback. Every process shares the measurement runner.

[The retained data](2026-10-15-release-baseline.json) contains every peer's unrounded CPU
sample, measured wall time, FPS and work-call counts, plus aggregated CPU/frame metrics, source
provenance and runtime SHA-256 inventories. It is a compact extract of the CI report, whose
SHA-256 is recorded alongside the workflow URL. It does not retain every log or final state;
the workflow artifact contains those validation records during its retention period.

This historical player predates the work-counter harness. New revision A/B comparisons must
build both revisions with the same current harness. See the [suite methodology](../README.md).
