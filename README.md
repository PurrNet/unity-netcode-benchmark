# Unity netcode benchmark

The same five stress scenarios built for PurrNet, FishNet, Mirror, Netcode for GameObjects and
Photon Fusion 2, run headless by GitHub Actions at 10 / 50 / 100 connections on identical
hardware, with bandwidth, CPU, frame time and RTT compared side by side.

## Latest results

<!-- BENCH:START -->
_Last run 2026-09-04: PurrNet ? · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="Server downstream on-wire at 100 connections; Server CPU at 100 connections. Best value per row highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 14.1 | 14.2 | 169 | **12.3** | 1,314 |
| MoveY | **485** | 1,253 | 2,464 | 2,934 | 2,805 |
| MoveAllAxis | **1,282** | 2,025 | 4,418 | 4,585 | 2,774 |
| MoveWander | **1,704** | 2,839 | 5,187 | 6,199 | 3,679 |
| SendRPC | 1,782 | **1,446** | 3,014 | 3,034 | 3,831 |
| Static | 13.8 | 14.2 | 171 | **11.6** | 405 |
| SpawnChurn | 743 | 645 | 851 | 944 | **388** |
| ClientInput | **91.2** | 93.2 | 277 | 115 | 217 |
| SyncVars | **2,496** | 3,475 | 4,774 | 3,885 | 3,223 |

**Server CPU at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 2.0 | **1.4** | 5.6 | 1.4 | 6.6 |
| MoveY | 9.9 | **3.8** | 5.7 | 31.7 | 12.2 |
| MoveAllAxis | 11.1 | **3.4** | 5.4 | 32.4 | 13.0 |
| MoveWander | 11.2 | **2.7** | 5.7 | 33.5 | 13.7 |
| SendRPC | 7.1 | **5.4** | 7.3 | 32.2 | 12.9 |
| Static | 1.7 | 1.4 | 3.8 | **1.1** | 8.1 |
| SpawnChurn | 11.0 | 4.4 | 5.3 | **3.7** | 9.8 |
| ClientInput | 2.4 | 2.8 | 5.1 | **1.8** | 9.4 |
| SyncVars | **3.9** | 4.3 | 6.9 | 35.8 | 13.4 |

</details>

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33863558632), [raw datapoints](docs/latest.json).
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
netcodes at 10 / 50 / 100 connections with 20-second windows. Each connection count is one
session: the five netcodes run back to back on the same server machine and the same client
machines, sessions run side by side, about 40 minutes in total. Useful inputs: `netcodes`, `sizes`, `bench_seconds`,
`bench_objects`, `profiling` (development builds add a CPU-by-profiler-marker table),
`max_parallel`, `fusion_max_clients`.

Quick reference run while iterating on one netcode: `netcodes: purrnet`, `sizes: 10,100`,
`bench_seconds: 10` (about 12 minutes).

Each run renders the job summary, uploads raw per-process JSON as the `benchmark-results`
artifact, and commits `docs/index.html` (interactive report), `docs/latest.json` and the
"Latest results" block above. Serve `docs/` with GitHub Pages to get a permanent report URL.

How a session works: one server runner and the client runners meet over a Tailscale tailnet and
stay up for the whole session. The server announces which netcode is next on a small HTTP endpoint,
every runner launches that netcode's player, and every process is the same harness driven by
`Shared/com.purrnet.netbench` (`-role server|client`), which waits for all clients, runs the Idle
window and the eight tests, writes JSON and quits. Clients detect the active test from the spawned
objects themselves, so no cross-netcode signalling is needed inside a netcode. Locally:

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
- **Hardware.** Jobs run on Blacksmith's `blacksmith-4vcpu-ubuntu-2404` pool, which is a mix of
  CPU models whose speed also varies over time. That is why all netcodes of one connection count
  share one server machine: CPU is comparable across netcodes within a connection count, not
  between connection counts and not between runs. Bandwidth, packets, GC and frame times do not
  depend on the machine. Every runner is a tailnet device (100 on Tailscale's Personal plan), which
  bounds `max_parallel`.
- **Frame cap.** Mirror (headless server) and FishNet override the frame rate on start; the
  harness re-applies 60 fps at every measurement window.
- **FishNet packet size.** Tugboat hard-codes 1350-byte packets and LiteNetLib sets don't-fragment;
  over the 1280-byte tailnet that silently drops every full packet, so the vendored constant is
  lowered to 1200 (Mirror's KCP default). All FishNet-side changes are listed in
  [fishnet/BENCHMARK_CHANGES.md](fishnet/BENCHMARK_CHANGES.md).
- Release builds by default; `profiling` builds add profiler overhead.
