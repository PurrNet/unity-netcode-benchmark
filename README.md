# Unity netcode benchmark

Five Unity 6 projects (one per netcode) running the same four stress scenarios, plus GitHub
Actions workflows that build every project, run the scenarios headless at 10 / 25 / 50 / 100
connections on real machines, and render a cross-netcode comparison (bandwidth, CPU, frame
times, RTT) into the workflow summary.

| Project | Netcode |
|---|---|
| `purrnet/` | PurrNet |
| `fishnet/` | FishNet |
| `mirror/` | Mirror (KCP transport) |
| `ngo/` | Netcode for GameObjects (Unity Transport) |
| `fusion/` | Photon Fusion 2 (dedicated server mode via Photon Cloud) |

All projects use Unity `6000.5.4f1`, a 20 Hz network tick and the same scenes/prefabs (from
[StinkySteak's netcode benchmark](https://github.com/StinkySteak/unity-netcode-benchmark)).
Library versions are read from the repo by `.github/scripts/versions.sh`.

## Scenarios

The server spawns `N` objects and replicates them to every client:

| Test | What the server does per object, every tick |
|---|---|
| MoveY | Moves the object on a sine wave along Y (NetworkTransform / networked position) |
| MoveAllAxis | Moves it on a sine wave along a random 3D direction |
| MoveWander | Wander steering: position **and** rotation change |
| SendRPC | Sends one observers RPC carrying one `int` |
| Static | Nothing. Objects are spawned and never touched (baseline cost of idle networked objects, per-object keepalives) |
| SpawnChurn | Despawns the N/50 oldest objects and spawns N/50 new ones every tick, keeping N alive (spawn payload, allocation / GC pressure) |
| ClientInput | One hub object; every **client** sends one small server RPC (`Vector3` + `int`) per tick. Measures server ingest scaling with client count |
| SyncVars | Changes one of four synced fields (`int`, `int`, `float`, `Vector3`) per object per tick, via each netcode's variable sync (SyncVar / NetworkVariable / [Networked]) |

The last four reuse the MoveY and SendRPC prefabs with movement disabled or a different
`BenchRegistry.Mode`, so no extra assets are involved. An **Idle** window (connected, nothing
spawned) is measured first and used as the per-netcode CPU baseline. The `-tests` argument
(default `1,2,3,4,5,6,7,8`) selects which run.

## Automated runs

Everything lives in `.github/workflows/`:

| Workflow | Purpose |
|---|---|
| `scaling.yml` (**Netcode Scaling Benchmark**) | The one to dispatch. Builds the selected netcodes in parallel, then runs each netcode at each connection count one run at a time, then renders the comparison tables and charts. |
| `benchmark.yml` | One netcode at one connection count (reusable; also dispatchable on its own). |
| `build.yml` | Builds one project as a StandaloneLinux64 IL2CPP player (reusable). |

How a run works (same design as PurrNet's own benchmark CI):

1. One **server** runner and `N` **client** runners join a Tailscale tailnet and wait for each
   other. Single-process "measured" client runners report clean numbers; for 100 connections,
   4 extra "loadgen" runners host 12 client processes each and only add connection load.
2. Every process is the same player started with `-role server|client`. The shared
   `Shared/com.purrnet.netbench` package (referenced by every project's manifest) drives the
   scenario: wait for all clients → Idle window → for each test spawn `N` objects, warm up 3 s,
   measure `bench_seconds`, despawn, cool down → write a JSON result → quit. Clients detect the
   active test through the spawned objects themselves, so no cross-netcode RPC is needed.
3. `bench-aggregate.sh` renders each run and emits a datapoint; `bench-scaling.sh` merges all
   datapoints into per-test tables (rows = connections, columns = netcodes) and Mermaid charts.
   Raw JSON (every process) and the rendered Markdown are uploaded as the `benchmark-results`
   artifact.

Dispatch inputs: `netcodes` (default all five), `sizes` (default `10,25,50,100`),
`bench_seconds` (20), `bench_objects` (100), `profiling` (development builds add a
CPU-by-profiler-marker table), `runner` (`runs-on` label, see below) and `region`
(Photon Cloud region for Fusion).

### What is measured

| Metric | Source | Notes |
|---|---|---|
| Downstream / upstream on-wire bytes | `/proc/net/dev` counters of the benchmark interface (`tailscale0`, or `eth0` for Fusion) read in-process at window start/end | Includes UDP/IP headers, ACKs, resends. Server side = all clients; client side = one client. |
| CPU % | Process CPU time (all threads) / wall time, from `/proc/self/stat` | % of one core. Frame loop capped at 60 fps on every netcode so an idle spin loop does not read as load. Idle baseline is subtracted in the comparison tables. |
| Frame time avg / p95 / p99 | `Time.unscaledDeltaTime` per frame | Main-thread tick budget adherence. |
| GC collections, managed heap, peak RSS | `GC.CollectionCount`, `GC.GetTotalMemory`, `/proc/self/status` | |
| RTT p50 / p95 / p99 | Each netcode's own RTT estimate, sampled 10×/s on measured clients | Fusion's includes the relay hop. |
| CPU by profiler marker | `UnityEngine.Profiling.Recorder` on netcode-prefixed samplers | Development builds only (`profiling: true`). |

Caveats worth keeping in mind when reading results:

- **Fusion is relay-based.** Its dedicated server and its clients all talk to Photon Cloud
  instead of to each other, so its RTT includes the relay hop and its traffic is measured on the
  public interface (`eth0`) rather than the tailnet. The server still sends one stream per
  client through the relay, so server-side downstream is comparable with the others. Its Photon
  plan is capped at 100 CCU and the server counts as one, so the 100-connection point runs with
  99 clients.
- **Machines.** Jobs default to Blacksmith's `blacksmith-4vcpu-ubuntu-2404` pool (fixed hardware
  generation, so CPU numbers are comparable across runs). Set `runner: ubuntu-latest` to fall
  back to GitHub-hosted runners, whose CPU model varies; the summary prints the server CPU model
  per datapoint either way.
- Release builds are the default; development builds (`profiling`) enable the marker table but
  add profiler overhead.
- **Frame cap.** Every process is capped at 60 fps and the cap is re-applied at each measurement
  window, because Mirror (headless server: `sendRate`) and FishNet (`TimeManager` frame rate,
  500 by default) otherwise override it and CPU % would not be comparable.
- **FishNet packet size.** The tailnet interface has a 1280-byte MTU and LiteNetLib sends with the
  don't-fragment flag. Tugboat hard-codes a 1350-byte maximum packet (no inspector setting), so
  every full packet was silently dropped in CI; the vendored constant in
  `fishnet/Assets/FishNet/Runtime/Transporting/Transports/Tugboat/Tugboat.cs` is lowered to 1200
  (the same value Mirror's KCP uses). PurrNet's LiteNetLib discovers the path MTU and settles at
  1204 on its own; Unity Transport fragments at the IP layer. All FishNet-project changes are
  listed in [fishnet/BENCHMARK_CHANGES.md](fishnet/BENCHMARK_CHANGES.md).

### Running a build locally

Any project can be driven the same way after a StandaloneLinux64 build (the harness reads
`/proc`, so bandwidth/CPU counters only work on Linux; frame stats work everywhere):

```bash
./NetBench -batchmode -nographics -role server -count 2 -port 7777 -benchObjects 100 -benchSeconds 10 -results server.json
./NetBench -batchmode -nographics -role client -serverHost 127.0.0.1 -port 7777 -benchObjects 100 -benchSeconds 10 -results client.json
```

Fusion uses `-session <name> -region us` instead of `-serverHost/-port`.

## Historical manual results (500 objects, editor, bandwidth only)

<img width="1120" height="600" alt="image" src="https://github.com/user-attachments/assets/5149537d-b4ad-4662-b903-ba6ac5406ec5" />

```
FishNetworking.4.6.18R:

MoveY (500 objects) Average 63k bytes/s
MoveAllAxis (500 objects) Average 104k bytes/s
MoveWander (500 objects) Average 142k bytes/s
SendRPC (500 rpcs with 1 int) Average 55k bytes/s

Mirror 96.0.1:

MoveY (500 objects) Average 131k bytes/s
MoveAllAxis (500 objects) Average 229k bytes/s
MoveWander (500 objects) Average 262k bytes/s
SendRPC (500 rpcs with 1 int) Average 139k bytes/s

Netcode for GameObjects 2.7.0:

MoveY (500 objects) Average 144k bytes/s
MoveAllAxis (500 objects) Average 231k bytes/s
MoveWander (500 objects) Average 307k bytes/s
SendRPC (500 rpcs with 1 int) Average 133k bytes/s

photon-fusion-2.0.9-stable-1566:

MoveY (500 objects) Average 88k bytes/s
MoveAllAxis (500 objects) Average 79k bytes/s
MoveWander (500 objects) Average 85k bytes/s
SendRPC (100 rpcs with 1 int - 500 crashes the editor) Average 25k bytes/s

PurrNet v1.18.0-beta.21:

MoveY (500 objects) Average 35k bytes/s
MoveAllAxis (500 objects) Average 87k bytes/s
MoveWander (500 objects) Average 109k bytes/s
SendRPC (500 rpcs with 1 int) Average 48k bytes/s
```
