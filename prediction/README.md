# Prediction benchmark

This is a separate suite from the repository's replication benchmarks. Dispatch **Prediction
Benchmark** (`.github/workflows/prediction.yml`). It builds isolated players for **PurrDiction,
FishNet prediction, and Photon Fusion 2 Server mode**, runs cases sequentially, and uploads
`prediction-benchmark-results` with raw peer JSON, logs, launch commands, a Markdown summary,
and a standalone HTML report. It does not replace `docs/latest.*`, the replication scorecard,
promotional charts, or the existing benchmark-history upload.

The first suite answers how much input/state prediction costs, how that changes with object
population and client count, and how much native replay work is performed. It is a diagnostic
baseline. It does not yet establish an overall winner or cover all prediction architectures.

## Workload and adapters

`sequenced-state-v1` supplies a changing, 12-byte logical input (`sequence`, `x`, `z`) through
each solution's native client-input path. Eight integers form a 32-byte logical state: position,
last sequence, applied command count, and four accumulators. Simulation consumes each newer
command once; absent/repeated commands leave state unchanged. Histories, native framing,
compression and redundant input transmission are left to the solution. Logical payload size
does not imply identical wire bytes.

There are no rigidbodies, rendering, per-tick queries, or gameplay allocations. This isolates
prediction/state machinery from expensive physics. It is a command-accumulation microbenchmark,
not a character controller; physics and continuously integrated movement need their own workloads.
Every client owns at least one object. Objects are distributed round-robin over connected clients.
Object populations are fixed independently of connection count.

| Adapter | Native path | Prediction scope |
|---|---|---|
| PurrDiction | `PredictedIdentity<INPUT, STATE>`, `GetFinalInput`, `Simulate`; `FullPrediction` | Every object participates in world prediction/replay |
| FishNet | `TickNetworkBehaviour`, `[Replicate]`, `[Reconcile]`; prediction and state forwarding enabled | Owned objects and spectators process forwarded state/input |
| Fusion 2 | `INetworkInput`, `OnInput`, `[Networked]` state, `FixedUpdateNetwork`; dedicated `GameMode.Server` | Native input-authority prediction; proxies receive networked state |

Fusion's Shared Mode is deliberately excluded. It has a different authority model and does not
exercise this server-authoritative rollback/resimulation path. FishNet's state forwarding is
explicitly enabled in the generated prefab. These scopes are reported alongside results; a
solution doing less speculative world work cannot be described as performing the same service
just because its CPU number is smaller.

Replay counters also have native meanings: PurrDiction `isReplaying` includes verified, gap,
and speculative passes; FishNet uses `ContainsReplayed`; Fusion uses `IsResimulation`.
PurrDiction additionally exports its existing pass telemetry, replay depth, batch sizes, and
timings. Restore deltas from FishNet are **not visual correction errors**: restoring an older
tick changes state even when prediction was correct. Unsupported metrics stay unavailable.

## Measurement and validation

Each case uses fresh dedicated-server and client processes. The launcher waits for the server
to listen before starting clients, including waiting for Fusion's cloud room to exist. All
peers must receive the complete object population before an HTTP readiness barrier releases
warmup. Control traffic is outside timing; there is no coordinator polling during measurement.

Every process collects its own wall-clock window after warmup (three seconds by default) and a full GC.
The workflow's `warmup_seconds` input can use 20 seconds to measure filled histories separately
from startup growth; compare all adapters with the same warmup and sampling duration.
The suite reuses the established load sampler for whole-process CPU (Linux process clock or
Windows `GetProcessTimes`, summing all threads), frame distributions,
managed heap, allocations/GC and Linux RSS. Harness and diagnostic overhead is included.
Development mode and scripting backend are recorded. The frame cap is 60 fps, so frame time
includes pacing; use process CPU and native work counters to investigate cost. Exact allocation
counters depend on Unity availability; the sampler marks heap-growth estimates explicitly.
Peak RSS and interface counters remain unavailable in Windows runs. Older Windows reports
without a CPU availability flag keep CPU marked unavailable.
FishNet's native server/client frame-rate settings are set to 60, and the common harness
reasserts the cap before warmup and timing. Changing that cap or losing the native connection
during measurement fails the case.

After sampling, clients stop creating new commands but keep supplying their final command to
the native input path. A second barrier ensures every peer has stopped, followed by five seconds
of settlement. Every object's exact final state must equal server authority, indices must be
unique and complete, ownership must cover every object exactly once, all inputs must be active,
and every client must have exercised owned forward prediction during timing. Networking stays
alive until all peers have captured their snapshots. Failed processes, missing reports, incomplete
windows, wrong tick rates, and failed state convergence exclude the case from result tables.

Client metrics average peers within each run, then use the median across fresh-process repeats.
Different source hashes, hardware metadata, build modes or scripting backends are not pooled.
Raw data retains each peer and repeat, including source provenance and native diagnostics.

## Current environment limits

The initial workflow runs the server and clients on **one runner**. Cases are sequential, but
processes within a case share hardware. This is useful for diagnosing a change under matched
conditions; client contention can influence results. Use the same fixed runner for comparisons.
The workflow shares the replication suite's concurrency lock to prevent concurrent measurements
on a dedicated runner.

PurrDiction and FishNet use loopback; Fusion uses Photon Cloud in the requested region, with the
existing project's Photon app settings and CCU limits. There is no artificial delay, jitter or
loss in this first suite. Route differences influence replay volume, so do not turn these CPU
numbers into an unconditional ranking. Raw interface counters are host-wide loopback totals,
not per-process on-wire bandwidth, and do not include Fusion's cloud traffic.
The raw PurrDiction `rttMs` field is currently an unavailable zero placeholder; it is not an
RTT measurement and is not used in the comparison report.

Next useful extensions are isolated server/measured-client runners, comparable delay/jitter/loss
profiles, input latency and presentation-error instrumentation, colliding rigidbody workloads,
large/history-owning states, spawn churn and outage recovery. PurrDiction's existing full physics
benchmark is a separate diagnostic source; it must not be scored against this math-only workload.

## Local runs

Generate projects without modifying the replication projects. PurrDiction needs a source checkout;
its runtime, editor and codegen are copied with existing Unity GUIDs and its declared PurrNet
dependency. FishNet and Fusion use the vendored implementations. Git package dependencies are
pinned to the existing lockfile commits; generated projects never follow an unrelated mutable
dependency while resolving packages. All generated folders are ignored by git.

```powershell
python .github/scripts/prediction-prepare.py purrdiction --output prediction-projects/purrdiction --prediction-source C:/path/to/PurrDiction
python .github/scripts/prediction-prepare.py fishnet --output prediction-projects/fishnet
python .github/scripts/prediction-prepare.py fusion --output prediction-projects/fusion
```

Build each generated project with Unity in batch mode, using
`-executeMethod PredictionBench.Editor.PredictionBenchBuild.BuildWindows` and
`-buildOutput <repo>/prediction-players/<solution>/PredictionBench.exe` (`-devBuild` enables
development mode). Linux uses `BuildLinux` and an extensionless `PredictionBench` player with
IL2CPP. The generated scene and prediction prefab are authored by the editor build method.
Project generation refuses to overwrite an existing generated project.

```powershell
python .github/scripts/prediction-bench.py --dry-run
python .github/scripts/prediction-bench.py --solutions purrdiction,fishnet,fusion --clients 1,2 --ticks 20,60 --objects 32 --seconds 10 --repeats 3
python .github/scripts/prediction-report.py prediction-results prediction-report
python .github/scripts/test-prediction-bench.py
```

For a quick functional smoke run use one client, eight objects, one repeat and a two-second
window. That verifies integration and convergence, not comparative performance. Each invocation
gets a unique results folder and preserves earlier runs. The default workflow runs 108 cases.

Primary references: [PurrDiction](https://purrnet.gitbook.io/docs/client-side-prediction),
[FishNet prediction](https://fish-networking.gitbook.io/docs/guides/features/prediction),
[Fusion client-server input](https://doc.photonengine.com/fusion/v2/manual/input/player-input),
and [Fusion Shared Mode input](https://doc.photonengine.com/fusion/v2/manual/input/shared-mode-input).
