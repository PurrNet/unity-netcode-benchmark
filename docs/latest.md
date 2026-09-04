_Last run 2026-09-04: PurrNet 1.23.0-beta.26 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**At a glance, 100 connections @ 20 Hz** (averages over the load tests; lower is better)

| Netcode | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 | Wins |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | **1.34 MB/s** | 8.0% | 1.07 MB/s | **6** | **16.7 ms** | **10 / 18** |
| FishNet | 1.62 MB/s | **6.8%** | **866 KB/s** | 79 | 17.5 ms | 5 / 18 |
| Mirror | 2.73 MB/s | 11.7% | 3.47 MB/s | 53 | **16.7 ms** | 0 / 18 |
| NGO (stalled 4/6) | – | – | – | 11 | 51.1 ms | 1 / 18 |
| Fusion | 2.51 MB/s | 17.0% | **877 KB/s** | 21 | **16.7 ms** | 3 / 18 |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **13.7 KB/s** | 0.064 pts | **66.2 KB/s** | 0.347 pts |
| FishNet | 16.6 KB/s | **0.053 pts** | 81.8 KB/s | **0.257 pts** |
| Mirror | 28.0 KB/s | 0.102 pts | 125 KB/s | 0.415 pts |
| NGO | – | – | – | – |
| Fusion | 25.7 KB/s | 0.136 pts | – | – |

</details>

Averages over the 6 load tests: bandwidth is server downstream on-wire to all clients, CPU is the whole server process as a share of one core, GC alloc is managed bytes allocated per second. Collections is the count over those tests, each starting on a freshly collected heap. Wins counts tests won on bandwidth, CPU or allocation. A test is a stall when the server's frame p99 passed twice the 60 fps budget, it dropped more than a sixth of its frames, it lost clients, or its memory ran to four times its Idle footprint: it wins nothing and is left out of the averages.
Comparison metrics per test (bandwidth, CPU, frame times, GC, memory) and every session are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33913885604), [raw datapoints](latest.json).
