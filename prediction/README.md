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

For revision comparisons, dispatch **Prediction Benchmark** with `baseline_run` and
`candidate_run` set to two successful prediction run IDs. This optional mode downloads
their existing PurrDiction players and alternates baseline/candidate order on one runner.
Both revisions use identical sampling parameters and fresh processes. Separate reports retain
the original build provenance and runtime hashes. This helps distinguish code changes from
differences between hosted runners; the source artifacts expire after three days.

To repeat an adapter comparison without rebuilding, set `reuse_run` to an existing prediction
run ID that contains every selected player. Sources, Unity version and build settings come
from those frozen artifacts; `purrdiction_ref` and `profiling` do not rebuild them in this mode.
Runtime sampling and diagnostics inputs still apply. Within each workload, repeats rotate
adapter order to distribute early and late positions. Use a repeat count divisible by the
number of adapters for balanced positions.

When only PurrDiction changes, keep `reuse_run` for the frozen comparison players and set
`purrdiction_run` to the run containing the new PurrDiction players. Both PurrDiction policies
use the override; FishNet and Fusion keep their original binaries. The override must contain
every selected PurrDiction policy. Missing players fail before measurement, and raw results
retain each selected binary's source provenance and runtime hash.

Hosted builds may run while another revision is being measured. Standard hosted loopback
comparisons and revision A/B jobs use independent VMs. Fusion comparisons and custom runners
share the replication scaling runner lock and queue without replacing one another.

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
| PurrDiction owned (optional `purrdiction-owned`) | Same API and source revision; existing `PredictedIfOwned` policy | Owned objects predict and replay; remote objects run verified `ServerRelay` ticks |
| FishNet | `TickNetworkBehaviour`, `[Replicate]`, `[Reconcile]`; prediction and state forwarding enabled | Owned objects and spectators process forwarded state/input |
| Fusion 2 | `INetworkInput`, `OnInput`, `[Networked]` state, `FixedUpdateNetwork`; dedicated `GameMode.Server` | Native input-authority prediction; proxies receive networked state |

Fusion's Shared Mode is deliberately excluded. It has a different authority model and does not
exercise this server-authoritative rollback/resimulation path. FishNet's state forwarding is
explicitly enabled in the generated prefab. These scopes are reported alongside results; a
solution doing less speculative world work cannot be described as performing the same service
just because its CPU number is smaller.

Input distribution also follows each native API. Fusion collects one 12-byte command per
player per tick in `OnInput`; all of that player's input-authority pawns consume that stream.
PurrDiction and FishNet collect a command separately for each owned pawn. Pawns use the same
command generator, but input record counts are not normalized across adapters. This workload
does not compare independently controlled objects or establish equal input-processing work.

Include `purrdiction-owned` in the `solutions` input to measure that existing policy separately.
It has its own player artifact, solution name, policy provenance and report rows, so its results
cannot be pooled with `purrdiction`. The default matrix keeps the full-world case. The owned
variant is closer to Fusion's input-authority scope, but still executes verified remote simulation;
it does not make the adapters identical or measure interactions between predicted objects.

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

PurrDiction also exports `memoryDiagnosticJson` after the measured window. It counts the
benchmark pawns' predicted, verified, and input history slots, live entries, and backing-array
payload bytes. This excludes array/object headers, owned payloads, framework statics, and
native memory; it is not a whole-heap census. An unavailable census reports its error instead
of treating missing reflection metadata or an empty population as zero memory.
The optional `hierarchy` section separately counts hierarchy history arrays and the unique
piece/deletion lists retained by those histories, including their list capacities. List slots
are reported separately from array payload bytes and are not a whole-heap estimate.

For a retained-heap investigation, add `--memory-snapshots` to a local launcher command.
It captures server and client-1 `.snap` files after measurement, input shutdown, and final
state capture, with a full collection first. Players keep networking alive until those
captures finish. Open the files in Unity's Memory Profiler; timing and heap figures in the
report were recorded before capture. The launcher rejects missing captures and older
players that ignore the request. Ordinary runs do not request snapshots.

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

Detailed native pass telemetry defaults to on in development players and off in release
players when launched with `auto`. The workflow defaults to `off` for comparisons.
Use `--diagnostics on|off|auto` (or the workflow's `diagnostics` input) to override
it. The player records the effective mode; explicit requests fail validation if an older
player ignores them. Reports keep on, off, and unrecorded legacy modes in separate groups.
Gameplay counters and final-state validation remain active in every mode. Use diagnostics
off for cross-adapter CPU/memory comparisons, and on for investigating PurrDiction passes.

Counter initialization is outside the CPU/wall measurement window. Raw `load.setupWallSeconds`
records that setup duration separately. Builds made before this change include setup in
their sampled clocks, so compare revisions built with the same harness version.
Warmup, the sample deadline, CPU denominator, and sampled frame intervals use one monotonic
clock (`CLOCK_MONOTONIC` on Linux, Stopwatch on Windows). Raw `load.wallClock` identifies it;
`load.unityWallSeconds` and `load.stopwatchWallSeconds` separately record those elapsed times
to expose clock disagreement.
The first partial frame interval is excluded from frame distributions.

Each case also saves `host.json` before launching players and after they exit: available CPU
model names, reported MHz, Linux scheduler counters (including steal), VM boot ID and clock
source. The manifest includes an initial host snapshot. These optional diagnostics cover the
whole case, including startup and warmup; they do not represent the player timing window and
are never used to normalize scores. Missing host counters remain unavailable.

For native CPU investigation, dispatch the same workflow with `profile_run` set to an existing
player-build run, one `solutions` adapter, one client/tick/object count, `seconds=50`, and
`warmup_seconds=20`. It samples the server and first client's main threads after warmup.
Set `profile_all_threads=true` to sample every thread in each process instead. The capture
also reports per-thread CPU time over the sampling interval, identifies newly observed and
exited threads, and excludes exited threads from CPU deltas when their final counters are
unavailable. Per-thread sample counts are reported separately: compare their coverage with
CPU counters before interpreting aggregate stack percentages as CPU-time shares.
It checks matching ELF symbol build IDs and uploads `prediction-native-profile` with raw stacks,
workload validation, and a summary of Unity frame-wait samples. Missing frame-wait symbols
produce an unavailable percentage. These sampled runs carry a diagnostic marker and have
their own artifact; they do not produce a comparative performance report.

Primary references: [PurrDiction](https://purrnet.gitbook.io/docs/client-side-prediction),
[FishNet prediction](https://fish-networking.gitbook.io/docs/guides/features/prediction),
[Fusion client-server input](https://doc.photonengine.com/fusion/v2/manual/input/player-input),
and [Fusion Shared Mode input](https://doc.photonengine.com/fusion/v2/manual/input/shared-mode-input).
