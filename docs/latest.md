_Last run 2026-09-05: PurrNet 1.23.0-beta.29 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

_Note: NGO at 100c @ 60 Hz: resource limit exceeded (8 GiB memory)._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**State replication** (100 connections @ 20 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **1.79 MB/s** | 7.5% | **471 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 2.52 MB/s | **6.2%** | 726 KB/s | 29 | 17.4 ms |
| Mirror | Completed | 4.12 MB/s | 12.7% | 3.08 MB/s | 22 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.83 MB/s | 75.2% | 1.3 KB/s | 0 | 47.5 ms |
| Fusion | Completed | 3.50 MB/s | 21.3% | 1.01 MB/s | 18 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 935 KB/s | **6.0%** | **729 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | **770 KB/s** | 7.3% | 884 KB/s | 31 | 17.6 ms |
| Mirror | Completed | 1.63 MB/s | 11.9% | 3.56 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.67 MB/s | 38.3% | 48.4 KB/s | 1 | 41.1 ms |
| Fusion | Completed | 1.98 MB/s | 12.8% | 946 KB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 775 KB/s | 13.9% | 3.21 MB/s | **2** | **16.7 ms** |
| FishNet | Completed | **640 KB/s** | **7.8%** | 1.48 MB/s | 24 | 17.5 ms |
| Mirror | Completed | 858 KB/s | 9.5% | 4.55 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 2.14 MB/s | 11.2% | 1.03 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **637 KB/s** | 11.8% | **580 KB/s** | **2** | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **13.6 KB/s** | 0.064 pts | **66.1 KB/s** | 0.352 pts |
| FishNet | 16.5 KB/s | **0.053 pts** | 82.0 KB/s | **0.258 pts** |
| Mirror | 28.2 KB/s | 0.104 pts | 124 KB/s | 0.415 pts |
| NGO | 32.7 KB/s | 0.527 pts | – | – |
| Fusion | 25.7 KB/s | 0.135 pts | 147 KB/s | 1.27 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33955131784) · [raw datapoints](latest.json).
