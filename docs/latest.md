_Last run 2026-09-04: PurrNet 1.23.0-beta.26 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**At a glance, 100 connections @ 20 Hz** (× best netcode, geometric mean over the load tests; lower is better)

| Netcode | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 | Wins |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | – | 1.12× | – | **6** | 16.67 ms | 5 / 18 |
| FishNet | – | **1.06×** | – | 75 | 16.67 ms | **6 / 18** |
| Mirror | – | 1.27× | – | 59 | 16.67 ms | 3 / 18 |
| NGO | – | 2.21× | – | 18 | 16.67 ms | 2 / 18 |
| Fusion | – | 2.54× | – | 8 | **16.67 ms** | **6 / 18** |

**How it scales** (cost multiplier; linear = 10.0× for 10 → 100 conn, linear = 3.00× for 20 → 60 Hz)

| Netcode | Bandwidth 10 → 100 conn | Server CPU 10 → 100 conn | Bandwidth 20 → 60 Hz | Server CPU 20 → 60 Hz |
|---|---:|---:|---:|---:|
| PurrNet | **1.00×** | **1.00×** | 14.1× | 5.25× |
| FishNet | **1.00×** | **1.00×** | 19.2× | 6.45× |
| Mirror | **1.00×** | **1.00×** | 12.9× | 7.48× |
| NGO | **1.00×** | **1.00×** | **0.93×** | **4.00×** |
| Fusion | – | **1.00×** | – | 14.2× |

</details>

Bandwidth is server downstream on-wire, CPU is the whole server process and GC alloc is managed bytes allocated per second; each is shown as a multiple of the best netcode in each of the 6 load tests, averaged (geometric mean), so 1.00× is best everywhere. Collections is the count over those tests, each starting on a freshly collected heap. Wins counts tests won on bandwidth, CPU or allocation.
Every metric per test (bandwidth, CPU, frame times, RTT, GC, memory) and every session are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33882268438), [raw datapoints](docs/latest.json).
