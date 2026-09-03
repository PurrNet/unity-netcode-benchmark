# Unity netcode benchmark

The same five stress scenarios built for PurrNet, FishNet, Mirror, Netcode for GameObjects and
Photon Fusion 2, run headless by GitHub Actions at 10 / 50 / 100 connections on identical
hardware, with bandwidth, CPU, frame time and RTT compared side by side.

## Latest results

<!-- BENCH:START -->
_Last run 2026-09-03: PurrNet 1.23.0-beta.20 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 25 / 50 / 100._

_Note: Fusion ran with 99 clients._

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| MoveY | **491** | 1,249 | 2,438 | 2,960 | 2,874 |
| MoveAllAxis | **1,237** | 2,023 | 4,422 | 4,671 | 2,774 |
| MoveWander | **1,724** | 2,840 | 5,189 | 6,258 | 3,840 |
| SendRPC | 1,485 | **1,090** | 2,767 | 2,662 | 3,779 |
| Static | 13.8 | 14.2 | 170 | **11.6** | 723 |
| SpawnChurn | 742 | 645 | 852 | 944 | **533** |
| ClientInput | **89.7** | 93.9 | 279 | 114 | 229 |
| SyncVars | 5,351 | 3,411 | 4,748 | 3,899 | **3,024** |

**Server CPU minus idle at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| MoveY | 10.9 | 3.3 | **3.2** | 34.7 | 8.9 |
| MoveAllAxis | 10.0 | **1.5** | 3.4 | 38.3 | 12.6 |
| MoveWander | 14.7 | **1.6** | 5.6 | 35.9 | 9.5 |
| SendRPC | 5.4 | **5.1** | 6.2 | 29.8 | 7.3 |
| Static | 1.2 | **-1.9** | 1.4 | -0.7 | 2.8 |
| SpawnChurn | 10.9 | **1.6** | 4.0 | 2.3 | 3.0 |
| ClientInput | 2.6 | 0.8 | 3.3 | **-0.0** | 11.4 |
| SyncVars | 6.6 | **3.2** | 7.4 | 35.1 | 8.0 |

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33753327418), [raw datapoints](docs/latest.json).
<!-- BENCH:END -->

## What runs

| Project | Netcode | Transport |
|---|---|---|
| `purrnet/` | PurrNet | UDP (LiteNetLib) |
| `fishnet/` | FishNet | Tugboat (LiteNetLib) |
| `mirror/` | Mirror | KCP |
| `ngo/` | Netcode for GameObjects | Unity Transport |
| `fusion/` | Photon Fusion 2 | Photon Cloud relay, dedicated server mode |

All projects use Unity `6000.5.4f1`, a 20 Hz tick, a 60 fps frame cap and the same scenes and
prefabs (from [StinkySteak's benchmark](https://github.com/StinkySteak/unity-netcode-benchmark)).
The server spawns `N` objects (100 by default) and replicates them to every client:

| Test | Per object, every tick |
|---|---|
| MoveY | sine movement on Y |
| MoveAllAxis | sine movement on a random 3D axis |
| MoveWander | wander steering, position and rotation |
| SendRPC | one observers RPC carrying one `int` |
| Static | nothing; objects are spawned and never touched |
| SpawnChurn | N/50 objects despawned and respawned per tick, N kept alive |
| ClientInput | one hub object; every **client** sends one server RPC (`Vector3` + `int`) per tick |
| SyncVars | one of four synced fields (`int`, `int`, `float`, `Vector3`) changed per tick |

An **Idle** window (connected, nothing spawned) is measured first as each netcode's CPU baseline.

## Measured

| Metric | How |
|---|---|
| Downstream / upstream on-wire | interface byte counters (`/proc/net/dev`) read in-process; headers, ACKs and resends included |
| CPU % | process CPU time, all threads, as % of one core; Idle subtracted in the comparison |
| Frame avg / p95 / p99 | main-thread frame time; 16.7 ms means on budget at 60 fps |
| GC, heap, peak RSS | `GC.CollectionCount`, `GC.GetTotalMemory`, `/proc/self/status` |
| RTT p50 / p95 | each netcode's own estimate, sampled on measured clients |

Server figures come from the one server process; client figures are averages over the
single-process measured clients (the remaining connections run as load generators).

## Running it

Dispatch **Netcode Scaling Benchmark** (`.github/workflows/scaling.yml`). Defaults run all five
netcodes at 10 / 50 / 100 connections with 20-second windows, netcodes side by side, one size at a
time, in about 25 to 30 minutes. Useful inputs: `netcodes`, `sizes`, `bench_seconds`,
`bench_objects`, `profiling` (development builds add a CPU-by-profiler-marker table),
`max_parallel`, `fusion_max_clients`.

Quick reference run while iterating on one netcode: `netcodes: purrnet`, `sizes: 10,100`,
`bench_seconds: 10` (about 12 minutes).

Each run renders the job summary, uploads raw per-process JSON as the `benchmark-results`
artifact, and commits `docs/index.html` (interactive report), `docs/latest.json` and the
"Latest results" block above. Serve `docs/` with GitHub Pages to get a permanent report URL.

How a run works: one server runner and the client runners meet over a Tailscale tailnet; every
process is the same player driven by `Shared/com.purrnet.netbench` (`-role server|client`),
which waits for all clients, runs the Idle window and the eight tests, writes JSON and quits.
Clients detect the active test from the spawned objects themselves, so no cross-netcode signalling
is needed. Locally:

```bash
./NetBench -batchmode -nographics -role server -count 2 -port 7777 -benchObjects 100 -benchSeconds 10 -results server.json
./NetBench -batchmode -nographics -role client -serverHost 127.0.0.1 -port 7777 -benchObjects 100 -benchSeconds 10 -results client.json
```

Fusion uses `-session <name> -region us` instead of `-serverHost/-port`. Bandwidth and CPU
counters need Linux; frame stats work everywhere.

## Caveats

- **Fusion is relay-based.** Server and clients talk to Photon Cloud, so its RTT includes the
  relay hop and its traffic is measured on the public interface. The server still sends one stream
  per client, so its downstream is comparable. `fusion_max_clients` caps its client count to the
  Photon CCU plan.
- **Hardware.** Jobs run on Blacksmith's `blacksmith-4vcpu-ubuntu-2404` pool so CPU numbers are
  comparable between runs; the report lists the server CPU model per datapoint. Every runner is a
  tailnet device (100 on Tailscale's Personal plan), which bounds `max_parallel`.
- **Frame cap.** Mirror (headless server) and FishNet override the frame rate on start; the
  harness re-applies 60 fps at every measurement window.
- **FishNet packet size.** Tugboat hard-codes 1350-byte packets and LiteNetLib sets don't-fragment;
  over the 1280-byte tailnet that silently drops every full packet, so the vendored constant is
  lowered to 1200 (Mirror's KCP default). All FishNet-side changes are listed in
  [fishnet/BENCHMARK_CHANGES.md](fishnet/BENCHMARK_CHANGES.md).
- Release builds by default; `profiling` builds add profiler overhead.
