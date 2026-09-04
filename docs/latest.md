_Last run 2026-09-04: PurrNet 1.23.0-beta.26 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**At a glance, 100 connections @ 20 Hz** (× best netcode, geometric mean over the load tests; lower is better)

| Netcode | Bandwidth | Server CPU | Collections | Frame p99 | Wins |
|---|---:|---:|---:|---:|---:|
| PurrNet | **1.07×** | 1.20× | **5** | **16.7 ms** | **8 / 12** |
| FishNet | 1.29× | **1.11×** | 82 | 17.5 ms | 5 / 12 |
| Mirror | 2.39× | 1.86× | 52 | **16.7 ms** | 0 / 12 |
| NGO | 2.56× | 5.37× | 12 | 46.5 ms | 1 / 12 |
| Fusion | 2.08× | 2.60× | 24 | **16.7 ms** | 0 / 12 |

**How it scales** (cost multiplier; linear = 10.0× for 10 → 100 conn, linear = 3.00× for 20 → 60 Hz)

| Netcode | Bandwidth 10 → 100 conn | Server CPU 10 → 100 conn | Bandwidth 20 → 60 Hz | Server CPU 20 → 60 Hz |
|---|---:|---:|---:|---:|
| PurrNet | 9.92× | 3.55× | 1.42× | 1.48× |
| FishNet | 10.0× | **3.47×** | 1.92× | 1.82× |
| Mirror | 10.3× | 4.86× | 1.26× | 1.52× |
| NGO | **6.90×** | 8.14× | **0.33×** | **0.65×** |
| Fusion | 10.0× | **3.43×** | 3.07× | 3.64× |

</details>

Bandwidth is server downstream on-wire, CPU is the whole server process and GC alloc is managed bytes allocated per second; each is shown as a multiple of the best netcode in each of the 6 load tests, averaged (geometric mean), so 1.00× is best everywhere. Collections is the count over those tests, each starting on a freshly collected heap. Wins counts tests won on bandwidth, CPU or allocation.
Every metric per test (bandwidth, CPU, frame times, RTT, GC, memory) and every session are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33889595415), [raw datapoints](latest.json).
