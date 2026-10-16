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

## Matched original/current release comparison (2026-10-16)

The original PurrDiction `1.4.1-beta.2` revision (`29d0ced3`, PurrNet `52ce233c`)
and the accepted performance revision (`a3489811`, PurrNet `fd4b1fbe`) were rebuilt with
the same benchmark C# sources at benchmark commit `1cd3eb6`. This measures the combined
PurrDiction and PurrNet changes, including their declared dependencies.

Each population uses six alternating fresh-process pairs on one hosted VM: four clients,
60 Hz, 20 seconds warmup and 60 seconds sampling. The 128- and 512-object comparisons
use separate VMs. Players use release IL2CPP with detailed diagnostics off; convergence
and input-activity validation remain enabled. CPU is the unadjusted percentage of one
core across all process threads. Client peers are averaged within each run before pairing.
The paired median percentage uses six pair ratios, rather than the ratio of the two medians.

The [retention audit](../../.github/scripts/prediction-start-current.py) validates all peer
reports, source/dependency revisions, identical benchmark source hashes, fixed runtime
files per revision, one VM boot per population and the alternating execution order. It
retains unrounded peer samples, work counters, source provenance, runtime inventories,
host metadata and report hashes. Full final states and logs remain in the CI artifacts
for their retention period. These results describe this workload and host cohort;
they do not establish a universal performance ranking or isolate individual changes.

| Objects | Role | Original CPU % | Current CPU % | Paired median CPU change |
|---|---|---:|---:|---:|
| 128 | Client | 4.74 | 2.91 | -38.1% |
| 128 | Server | 6.41 | 3.68 | -43.0% |
| 512 | Client | 18.44 | 9.60 | -45.3% |
| 512 | Server | 24.51 | 13.13 | -41.9% |

The current revision used less CPU in all six pairs for each role and population.
All 120 peer reports passed validation. Measured server simulation rates stayed between
59.99 and 60.03 Hz, and sampled server input-application rates remained comparable;
these samples did not exhibit the previously reproduced stalled-input failure. Client
replay counts varied and were neither equalized nor used to normalize CPU.

Retained data and successful workflow runs:

- [128 objects](2026-10-16-start-current-128.json), [comparison run 38869092008](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/38869092008).
- [512 objects](2026-10-16-start-current-512.json), [comparison run 38869099801](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/38869099801).
- Release builds: [original 38866770742](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/38866770742), [current 38866794558](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/38866794558).

To reproduce an extract after downloading `prediction-revision-comparison-results`:

```sh
python .github/scripts/prediction-start-current.py <download>/prediction-ab-results <output.json>
```

This loopback comparison does not resolve the separate high-latency server-backlog/input-stall
issue. That failure remains an open investigation.
