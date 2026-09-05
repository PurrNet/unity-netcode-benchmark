# Unity netcode benchmark

The same five stress scenarios built for PurrNet, FishNet, Mirror, Netcode for GameObjects and
Photon Fusion 2, run headless by GitHub Actions at 10 and 100 connections and at 20 and 60 Hz
on a dedicated server, with bandwidth, CPU, frame time and memory compared side by side.

## Results

Live report: **https://purrnet.github.io/unity-netcode-benchmark/** (scorecard, scaling table, comparison
metrics per test and session). Raw datapoints of the latest run are in `docs/latest.json`.
Detailed workload/delivery diagnostics stay in the raw data. Run notes show only problems, not successful checks or routine measurements.
RTT measurements remain in the raw data only; they are not used for comparisons.

## What runs

| Project | Netcode | Transport |
|---|---|---|
| `purrnet/` | PurrNet | UDP (LiteNetLib) |
| `fishnet/` | FishNet | Tugboat (LiteNetLib) |
| `mirror/` | Mirror | KCP |
| `ngo/` | Netcode for GameObjects | Unity Transport |
| `fusion/` | Photon Fusion 2 | Photon Cloud relay, dedicated server mode |

All projects use Unity `6000.5.4f1`, the same tick rate (set per session with `-tickRate`), a
60 fps frame cap and the same scenes and prefabs (from [StinkySteak's benchmark](https://github.com/StinkySteak/unity-netcode-benchmark)).
The server spawns `N` objects (100 by default) and replicates them to every client:

| Test | Per object, every tick |
|---|---|
| MoveY | sine movement on Y |
| MoveWander | wander steering, position and rotation |
| SendRPC | one observers RPC carrying one `float` |
| Static | nothing; objects are spawned and never touched |
| SpawnChurn | N/50 objects despawned and respawned per tick, N kept alive |
| ClientInput | one hub object; every **client** sends one server RPC (`Vector3` + `float`) per tick |
| SyncVars | one of four synced fields (`float`, `float`, `float`, `Vector3`) changed per tick |

An **Idle** window (connected, nothing spawned) is measured first and reported as its own row: what holding the connections costs before anything is replicated. Nothing is subtracted from the other tests.
Payloads are floats rather than ints on purpose: FishNet varint-packs integers by default and the
others do not, whereas a float is 4 bytes on every netcode, so the RPC and SyncVar tests compare
framing and batching instead of integer encoding.

## Measured

| Metric | How |
|---|---|
| Downstream / upstream on-wire | interface byte counters (`/proc/net/dev`) read in-process; headers, ACKs and resends included |
| CPU % | process CPU time, all threads, as % of one core; whole process, nothing subtracted |
| Frame avg / p95 / p99 | main-thread frame time; 16.7 ms means on budget at 60 fps |
| GC alloc, collections, heap, peak RSS | the `GC Allocated In Frame` profiler counter summed over the window (all threads), `GC.CollectionCount`, `GC.GetTotalMemory`, `/proc/self/status`; every test starts on a freshly collected heap |

Server figures come from the one server process; client figures are averages over the
single-process measured clients (the remaining connections run as load generators).

## Running it

Dispatch **Netcode Scaling Benchmark** (`.github/workflows/scaling.yml`). Defaults run all five
netcodes in three sessions, `10@20,100@20,100@60` (connections@tickHz), with 10-second windows
(Idle and Static use 5, since they only check the floor).
The entire suite uses one prepared server/client fleet, sized for the largest session. Sessions
and netcodes run one after another; every case starts fresh player processes on those same machines.
Smaller sessions leave the extra loadgen runners idle. `max_parallel` must remain `1`.
Useful inputs: `netcodes`, `sessions`, `bench_seconds`, `bench_objects`, `profiling`
(development builds add a CPU-by-profiler-marker table), `fusion_max_clients`. `server_runner`,
`runner` and `loadgen_runner` pick the machines; the defaults below are the published setup.

Quick reference run while iterating on one netcode: select that `netcodes` entry, `sessions: 10,100`,
`bench_seconds: 5`. Use the full suite and normal windows for published comparisons.

Each run renders the job summary, uploads raw per-process JSON as the `benchmark-results`
artifact. When all planned datapoints exist and the workflow succeeds, it commits `docs/`
(interactive report, `latest.json`, `latest.md`). A failed fleet or missing completion acknowledgement
does not replace the published report. GitHub Pages serves `docs/` as the live report.

How to read the results: the report opens with one row per netcode.
Bandwidth and CPU are a multiple of the best netcode in each load test, averaged over the seven
load tests (geometric mean), so 1.00× means best everywhere and 2× means twice the best on
average; Idle and Static are left out of the averages because they sit at the noise floor.
"How it scales" gives the cost multiplier from 10 to 100 connections and from 20 to 60 Hz, next
to what a linear sender would score (10× and 3×), so below that line a netcode amortises. The
per-test bar charts and the session table underneath carry the comparison metrics.

How the suite works: one server runner and the client runners meet over a Tailscale tailnet and
stay up for all sessions. The server announces each case on a small HTTP endpoint,
every runner launches that netcode's player, and every process is the same harness driven by
`Shared/com.purrnet.netbench` (`-role server|client`), which waits for all clients, runs the Idle
window and the seven tests, writes JSON and quits. Clients detect the active test from the spawned
objects themselves, so no cross-netcode signalling is needed inside a netcode. Every runner must
finish preparation before the first case starts. Between cases, the coordinator waits for every
worker to acknowledge that its player processes have exited (including loadgens); it does not
shorten any measurement window to advance. Workers use a held HTTP request, not periodic phase
polling while players run. Results and logs upload after the suite, not between sessions. Locally:

```bash
./NetBench -batchmode -nographics -role server -count 2 -port 7777 -benchObjects 100 -benchSeconds 10 -tickRate 20 -results server.json
./NetBench -batchmode -nographics -role client -serverHost 127.0.0.1 -port 7777 -benchObjects 100 -benchSeconds 10 -tickRate 20 -results client.json
```

Fusion uses `-session <name> -region eu` instead of `-serverHost/-port`. Bandwidth and CPU
counters need Linux; frame stats work everywhere.

### CI overhead and build reuse

Each `player-<netcode>` artifact contains only runtime files plus `build-provenance.json`.
Unity's `NetBench_BackUpThisFolder_ButDontShipItWithYourGame` folder (generated source, symbols
and other build diagnostics) is retained separately as `build-diagnostics-<netcode>`, not downloaded
by the measurement fleet. Packaging does not change player bytes, build flags or networking settings.

Finished players are cached with an exact key covering the selected project's Assets, Packages
and ProjectSettings (including Unity version), the shared harness, build workflow, packaging script,
Linux IL2CPP target and release/development mode. There is no fallback key for finished binaries.
Cache hits verify the recorded SHA-256 inventory and retain the original source revision in the
provenance file. Cache misses build normally using the existing incremental Library cache.

These changes target overhead observed in [run 33908349862](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33908349862):
repeated player downloads, a slow artifact download holding up the fleet, and fixed final sleeps.
The latter are replaced by bounded completion acknowledgements. Workload timing, warmup,
delivery grace, cooldowns, connection budgets and overload behaviour are unchanged. Actual time
savings still need to be measured on a new CI run; they are not inferred from local correctness tests.

Local orchestration checks: `python .github/scripts/test-bench-fleet.py` (fake players, no CPU
comparison); the Linux run additionally checks cleanup of orphaned child processes.

## Changes from the defaults

The intent is to preserve each netcode's networking defaults while giving it the same requested
workload. That requires both compatibility fixes and some benchmark-side scheduling. The changes
below are explicit so the reader can judge the tradeoffs; equivalent offered work does not mean
forcing identical batching, compression, precision or delivery behaviour.

| Netcode | What | Default | Here | Why it was needed |
|---|---|---|---|---|
| FishNet | Send interval on the four benchmark SyncVars | 0.1 seconds per field | `UpdateSendRate(0f)` after initialization: changed state is eligible every network tick | This scenario requests tick-driven state replication. At 60 Hz each of the four fields changes 15 times/s; the default interval can coalesce those changes into roughly 10 sends/s per field. Removing the extra interval avoids comparing that lower update frequency as if it were equivalent service. Reliability, permissions and global SyncType defaults are unchanged. |
| FishNet | Tugboat's packet size constant `MAXIMUM_UDP_MTU` (a source edit in the vendored transport; there is no inspector field for it) | 1350 | 1200 | LiteNetLib sets don't-fragment and Tugboat hands it a fixed 1350-byte MTU, so on the 1280-byte tailnet every full packet was silently dropped and MoveWander and SendRPC sent almost nothing. 1200 is Mirror's KCP default. Details in [fishnet/BENCHMARK_CHANGES.md](fishnet/BENCHMARK_CHANGES.md). |
| NGO | Unity Transport → `Max Packet Queue Size` (inspector field on the NetworkManager prefab) | 128 | 4096 | At 128 the server overflows the queue from 50 connections up, drops packets and logs one error per connection per tick; at 100 connections and 60 Hz the logging alone saturates a core. Unity recommends raising it for large player counts. |
| NGO | NetworkTransform → `Use Unreliable Deltas` (inspector field on the three movement prefabs) | off | on | Delivers transform deltas unreliably, which is what the other four do for transforms out of the box (Mirror's default NetworkTransform is the unreliable one, FishNet and PurrNet send transform deltas unreliably, Fusion's snapshots are unreliable). With the reliable default the server queues without bound behind Unity Transport's reliable window at 60 Hz and dies. |
| Mirror | Benchmark workload scheduling (application code, not a Mirror source change) | The vendored Mirror provides a network send rate and frame-loop hooks, but no fixed-rate gameplay tick callback | A small custom tick loop for movement, RPC generation and SyncVar mutations, at the session's `-tickRate` | Interval-driven application work must be scheduled by the application. The loop honours the requested workload timing without changing Unity's physics timestep. |

Mirror's custom [benchmark tick system](mirror/Assets/_Benchmark/Scripts/BenchmarkTickSystem.cs)
accumulates elapsed time in Unity's `Update` and catches up missed ticks after a slow frame.
It passes the tick duration to movement code and leaves `Time.fixedDeltaTime` unchanged, avoiding
extra physics steps just to schedule network workloads. A Mirror application that wants to send
something at an interval likewise has to arrange that timing itself, for example with Unity
callbacks or a timer. This helper's CPU cost is included in Mirror's results. It is not a new
networking tick implementation: Mirror still decides when and how to batch and transmit updates,
and several workload ticks can occur within one Unity frame.

The other projects use their native tick callbacks (including PurrNet's `ITick`). All movement
uses the supplied tick duration, rather than Unity's render-frame delta. Client-input generation
and spawn churn use the session tick rate with elapsed-time catch-up, rather than a hard-coded
20 Hz. These are benchmark workload changes, not changes to replication defaults.

The harness also records generated/received RPC counts and final SyncVar state fingerprints.
After measurement the server pauses mutations for a 1.5-second delivery grace period; clients
stay connected until despawn, including after their last measurement window. Whole-test RPC
delivery and exact final-state matches are reported separately from window rates. These are
diagnostic checks, not a guarantee of equal movement fidelity or update freshness; a state
mismatch needs investigation before changing a netcode's precision or delivery defaults.

All five projects also sample their client-visible SyncVar state in `LateUpdate`, including
warmup, with counts collected only during the measurement window. The report shows observed
field changes per second and average/maximum **field silence** (time since a field last changed
locally). A `Vector3` counts as one field. The initial state is a baseline, not a received change.
These allocation-free per-sample checks add no wire data, and their client CPU cost is included.
They expose coalescing or stalled updates using the same observation rule for every netcode,
including PurrNet. They are frame-sampled diagnostics, not packet counts, per-mutation delivery
guarantees or server-to-client state age: updates within one frame may coalesce, and a steady
delayed stream can have the same change rate and silence as a prompt one. No absolute freshness
claim or new pass/fail scoring threshold is inferred from them.

Beyond the exceptions above, networking settings remain unchanged. RPCs are reliable in every
netcode, and NGO's NetworkVariables are reliable by design. Native coalescing, thresholds and
send intervals are retained except for the documented FishNet SyncVar override.

## Caveats

- **Fusion is relay-based.** Server and clients talk to Photon Cloud, so its RTT includes the
  relay hop and its traffic is measured on the public interface. The server still sends one stream
  per client, so its downstream is comparable. `fusion_max_clients` caps its client count to the
  Photon CCU plan.
- **Hardware.** The server runs on a dedicated Hetzner AX41 (Ryzen 5 3600, Helsinki) registered
  as the self-hosted `bench-server` runner: SMT and turbo off, performance governor, interrupts
  and the runner agent pinned to two cores and the server player to the other four
  (`infra/bench-server-setup.sh`). Server CPU is therefore comparable across netcodes, connection
  counts and runs. The box takes one session at a time, which is why `max_parallel` defaults
  to 1. Clients and load generators run on GitHub-hosted `ubuntu-latest` runners in the US, so the
  raw RTT readings include that route and are not used for comparisons.
  Bandwidth, packets, GC and frame times do not depend on the machine. Every runner is a
  tailnet device (100 on Tailscale's Personal plan), which bounds `max_parallel` if you raise it
  with a different `server_runner`.
- **Frame cap.** Mirror (headless server) and FishNet override the frame rate on start; the
  harness re-applies 60 fps at every measurement window.
- **Categories, not an overall verdict.** At a glance separates state replication (MoveY,
  MoveWander, SyncVars), messaging (server broadcast and client-to-server RPCs), and lifecycle
  (SpawnChurn). Idle and Static remain unscored baselines. A stall removes that category's averages;
  missing or truncated tests remove its averages and wins. Completed categories remain usable after
  a later failure, with the run error still shown. Scaling still requires the full suite in both sessions.
- **Resource limits.** Every netcode keeps the same tests, including NGO at 100 connections / 60 Hz
  and reliable RPCs. Each server case has an 8 GiB cgroup memory ceiling with no swap, the existing
  780-second harness timeout and a 900-second external watchdog (10-second termination grace).
  The memory ceiling includes the server and its Xvfb wrapper, including charged file cache and
  kernel memory; it is not an RSS threshold. Limits are enforced outside Unity, with no memory
  polling during measurement. A runner without cgroup v2 memory controls fails preparation.
  Limit hits show as **resource limit exceeded** and retain completed measurement windows. Incomplete
  categories receive no averages, wins or best-value highlights; completed categories are kept.
  Missing later tests stay missing, not zero. A contained
  limit hit does not prevent publication; a host OOM or broken fleet barrier does.
  These guards apply to new fleet runs; older results are not retroactively capped.
- **Peak RSS is cumulative.** It is the process-lifetime high-water mark as of each test, not that
  test's own peak. A large earlier allocation does not mark a later, healthy window as stalled.
- Release builds by default; `profiling` builds add profiler overhead.
