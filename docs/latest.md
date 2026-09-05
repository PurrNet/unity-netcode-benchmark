_Last run 2026-09-04: PurrNet 1.23.0-beta.27 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**At a glance, 100 connections @ 20 Hz** (averages over the load tests; lower is better)

| Netcode | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 | Wins |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | **1.33 MB/s** | 8.0% | 1.04 MB/s | **5** | **16.7 ms** | **10 / 18** |
| FishNet | 1.62 MB/s | **6.9%** | **906 KB/s** | 77 | 17.6 ms | 5 / 18 |
| Mirror | 2.74 MB/s | 11.8% | 3.56 MB/s | 53 | **16.7 ms** | 0 / 18 |
| NGO (stalled 4/6) | – | – | – | 11 | 47.6 ms | 1 / 18 |
| Fusion | 2.51 MB/s | 16.9% | **898 KB/s** | 22 | **16.7 ms** | 3 / 18 |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **13.6 KB/s** | 0.064 pts | **65.8 KB/s** | 0.348 pts |
| FishNet | 16.6 KB/s | **0.053 pts** | 81.8 KB/s | **0.257 pts** |
| Mirror | 28.1 KB/s | 0.103 pts | 125 KB/s | 0.413 pts |
| NGO | – | – | – | – |
| Fusion | 25.7 KB/s | 0.135 pts | – | – |

</details>

Across 6 load tests: bandwidth, CPU and allocation are averages; collections are totals; frame p99 is the maximum. Wins count lowest bandwidth, CPU or allocation; ties share wins. Incomplete or stalled runs have no averages.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33924304494) · [raw datapoints](latest.json).
