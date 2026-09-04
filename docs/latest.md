_Last run 2026-09-04: PurrNet 1.23.0-beta.26 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**At a glance, 100 connections @ 20 Hz** (averages over the load tests; lower is better)

| Netcode | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 | Wins |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | **1.27 MB/s** | 8.0% | 978 KB/s | **4** | **16.7 ms** | **11 / 18** |
| FishNet | 1.56 MB/s | **6.9%** | **783 KB/s** | 80 | 17.5 ms | 7 / 18 |
| Mirror | 2.67 MB/s | 11.9% | 3.41 MB/s | 53 | **16.7 ms** | 0 / 18 |
| NGO (stalled 4/6) | – | – | – | 11 | 51.2 ms | 2 / 18 |
| Fusion | 2.47 MB/s | 16.8% | 953 KB/s | 25 | **16.7 ms** | 1 / 18 |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **13.0 KB/s** | 0.064 pts | 23.3 KB/s | **0.116 pts** |
| FishNet | 16.0 KB/s | **0.053 pts** | 56.2 KB/s | 0.171 pts |
| Mirror | 27.4 KB/s | 0.104 pts | **16.6 KB/s** | 0.153 pts |
| NGO | – | – | – | – |
| Fusion | 25.3 KB/s | 0.134 pts | 146 KB/s | 0.969 pts |

</details>

Averages over the 6 load tests: bandwidth is server downstream on-wire to all clients, CPU is the whole server process as a share of one core, GC alloc is managed bytes allocated per second. Collections is the count over those tests, each starting on a freshly collected heap. Wins counts tests won on bandwidth, CPU or allocation. A test is a stall when the server's frame p99 passed twice the 60 fps budget, it dropped more than a sixth of its frames, it lost clients, or its memory ran to four times its Idle footprint: it wins nothing and is left out of the averages.
Every metric per test (bandwidth, CPU, frame times, RTT, GC, memory) and every session are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33908349862), [raw datapoints](latest.json).
