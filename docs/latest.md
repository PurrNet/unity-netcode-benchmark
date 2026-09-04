_Last run 2026-09-04: PurrNet 1.23.0-beta.26 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · sessions 10c @ 20 Hz / 100c @ 60 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 60 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**At a glance, 100 connections @ 60 Hz** (× best netcode, geometric mean over the load tests; lower is better)

| Netcode | Server CPU | Collections | Frame p99 | Wins |
|---|---:|---:|---:|---:|
| PurrNet | **1.96×** | **5** | **16.7 ms** | 3 / 12 |
| FishNet | 2.27× | 317 | 17.6 ms | 1 / 12 |
| Mirror | 3.14× | 171 | **16.7 ms** | 0 / 12 |
| NGO | 2.93× | 132 | 11309.8 ms | 2 / 12 |
| Fusion | 11.9× | 102 | 1000.4 ms | **6 / 12** |

</details>

Bandwidth is server downstream on-wire, CPU is the whole server process and GC alloc is managed bytes allocated per second; each is shown as a multiple of the best netcode in each of the 6 load tests, averaged (geometric mean), so 1.00× is best everywhere. Collections is the count over those tests, each starting on a freshly collected heap. Wins counts tests won on bandwidth, CPU or allocation.
Every metric per test (bandwidth, CPU, frame times, RTT, GC, memory) and every session are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33882268438), [raw datapoints](latest.json).
