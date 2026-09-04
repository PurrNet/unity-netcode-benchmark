# Unity netcode benchmark

The same five stress scenarios built for PurrNet, FishNet, Mirror, Netcode for GameObjects and
Photon Fusion 2, run headless by GitHub Actions at 10 and 100 connections and at 20 and 60 Hz
on a dedicated server, with bandwidth, CPU, frame time and RTT compared side by side.

## Latest results

<!-- BENCH:START -->
_Last run 2026-09-04: PurrNet 1.23.0-beta.26 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="Server downstream on-wire at 100 connections; Server CPU at 100 connections. Best value per row highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 13.9 | 14.7 | 204 | 14.3 | **0.0** |
| MoveY | 493 | 1,252 | 2,435 | 3,186 | **0.0** |
| MoveAllAxis | 1,318 | 2,024 | 4,418 | 4,881 | **0.0** |
| MoveWander | 1,889 | 2,840 | 5,186 | 6,676 | **0.0** |
| SendRPC | 1,782 | 1,447 | 3,044 | 3,772 | **0.0** |
| Static | 13.8 | 14.2 | 173 | 14.1 | **0.0** |
| SpawnChurn | 782 | 645 | 861 | 1,830 | **0.0** |
| ClientInput | 91.4 | 92.6 | 282 | 117 | **0.0** |
| SyncVars | 2,501 | 3,500 | 4,862 | 4,293 | **0.0** |

**Server CPU at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | **1.2** | 2.0 | 5.2 | 1.8 | 8.2 |
| MoveY | 10.2 | **6.2** | 10.2 | 73.2 | 23.0 |
| MoveAllAxis | 12.6 | **4.3** | 11.6 | 73.3 | 23.0 |
| MoveWander | 13.7 | **5.1** | 12.7 | 74.0 | 24.5 |
| SendRPC | **8.2** | 9.4 | 16.3 | 73.1 | 16.5 |
| Static | **1.4** | 1.6 | 5.4 | 1.9 | 9.6 |
| SpawnChurn | 14.2 | **7.8** | 9.5 | 10.2 | 11.8 |
| ClientInput | **3.6** | 5.2 | 7.3 | 3.9 | 10.1 |
| SyncVars | **6.9** | 7.4 | 14.1 | 78.6 | 16.0 |

</details>

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33872472252), [raw datapoints](docs/latest.json).
<!-- BENCH:END -->

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
| GC, heap, peak RSS | `GC.CollectionCount`, `GC.GetTotalMemory`, `/proc/self/status` |
| RTT p50 / p95 | each netcode's own estimate, sampled on measured clients |

Server figures come from the one server process; client figures are averages over the
single-process measured clients (the remaining connections run as load generators).

## Running it

Dispatch **Netcode Scaling Benchmark** (`.github/workflows/scaling.yml`). Defaults run all five
netcodes in three sessions, `10@20,100@20,100@60` (connections@tickHz), with 10-second windows
(Idle and Static use 5, since they only check the floor).
Inside a session the five netcodes run back to back on the same server machine and the same
client machines; sessions run one after another on the dedicated server, about 40 minutes each.
Useful inputs: `netcodes`, `sessions`, `bench_seconds`, `bench_objects`, `profiling`
(development builds add a CPU-by-profiler-marker table), `fusion_max_clients`. `server_runner`,
`runner` and `loadgen_runner` pick the machines; the defaults below are the published setup.

Quick reference run while iterating on one netcode: `netcodes: purrnet`, `sessions: 10,100`,
`bench_seconds: 5` (about 8 minutes).

Each run renders the job summary, uploads raw per-process JSON as the `benchmark-results`
artifact, and commits `docs/index.html` (interactive report), `docs/latest.json` and the
"Latest results" block above. Serve `docs/` with GitHub Pages to get a permanent report URL.

How to read the results: the block above and the top of the report show one row per netcode.
Bandwidth and CPU are a multiple of the best netcode in each load test, averaged over the seven
load tests (geometric mean), so 1.00× means best everywhere and 2× means twice the best on
average; Idle and Static are left out of the averages because they sit at the noise floor.
"How it scales" gives the cost multiplier from 10 to 100 connections and from 20 to 60 Hz, next
to what a linear sender would score (10× and 3×), so below that line a netcode amortises. The
per-test bar charts and the session table underneath carry every metric.

How a session works: one server runner and the client runners meet over a Tailscale tailnet and
stay up for the whole session. The server announces which netcode is next on a small HTTP endpoint,
every runner launches that netcode's player, and every process is the same harness driven by
`Shared/com.purrnet.netbench` (`-role server|client`), which waits for all clients, runs the Idle
window and the seven tests, writes JSON and quits. Clients detect the active test from the spawned
objects themselves, so no cross-netcode signalling is needed inside a netcode. Locally:

```bash
./NetBench -batchmode -nographics -role server -count 2 -port 7777 -benchObjects 100 -benchSeconds 10 -tickRate 20 -results server.json
./NetBench -batchmode -nographics -role client -serverHost 127.0.0.1 -port 7777 -benchObjects 100 -benchSeconds 10 -tickRate 20 -results client.json
```

Fusion uses `-session <name> -region eu` instead of `-serverHost/-port`. Bandwidth and CPU
counters need Linux; frame stats work everywhere.

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
  RTT column reads as US clients to an EU server for every netcode alike; the Idle row shows that
  floor. Bandwidth, packets, GC and frame times do not depend on the machine. Every runner is a
  tailnet device (100 on Tailscale's Personal plan), which bounds `max_parallel` if you raise it
  with a different `server_runner`.
- **Frame cap.** Mirror (headless server) and FishNet override the frame rate on start; the
  harness re-applies 60 fps at every measurement window.
- **FishNet packet size.** Tugboat hard-codes 1350-byte packets and LiteNetLib sets don't-fragment;
  over the 1280-byte tailnet that silently drops every full packet, so the vendored constant is
  lowered to 1200 (Mirror's KCP default). All FishNet-side changes are listed in
  [fishnet/BENCHMARK_CHANGES.md](fishnet/BENCHMARK_CHANGES.md).
- Release builds by default; `profiling` builds add profiler overhead.
