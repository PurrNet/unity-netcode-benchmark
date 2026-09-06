_Last run 2026-09-06: PurrNet dev · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

_Note: NGO at 100c @ 60 Hz: resource limit exceeded (8 GiB memory)._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Who's ahead, 100 connections @ 20 Hz** (best per category; no averaging across categories)

| Category | Bandwidth | Server CPU | GC alloc |
|---|---:|---:|---:|
| State replication | PurrNet | FishNet | PurrNet |
| Messaging | FishNet | PurrNet | PurrNet |
| Spawn / despawn | Fusion | FishNet | Fusion |

**State replication** (100 connections @ 20 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **1.79 MB/s** | 8.9% | **498 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 2.47 MB/s | **7.6%** | 1013 KB/s | 31 | 17.4 ms |
| Mirror | Completed | 4.14 MB/s | 15.3% | 2.79 MB/s | 24 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.87 MB/s | 86.5% | 43.4 KB/s | 0 | 53.4 ms |
| Fusion | Completed | 3.50 MB/s | 22.8% | 989 KB/s | 16 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 935 KB/s | **7.9%** | **691 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | **773 KB/s** | 9.4% | 1.48 MB/s | 31 | 17.6 ms |
| Mirror | Completed | 1.65 MB/s | 15.1% | 3.29 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.79 MB/s | 43.2% | 85.6 KB/s | 2 | 46.9 ms |
| Fusion | Completed | 1.97 MB/s | 15.0% | 818 KB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 754 KB/s | 15.2% | 3.03 MB/s | **2** | **16.7 ms** |
| FishNet | Completed | 633 KB/s | **9.5%** | 2.44 MB/s | 24 | 17.6 ms |
| Mirror | Completed | 790 KB/s | 11.1% | 3.87 MB/s | 11 | **16.7 ms** |
| NGO | Completed | 2.14 MB/s | 13.9% | 1.01 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **605 KB/s** | 13.0% | **636 KB/s** | **2** | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **13.6 KB/s** | 0.068 pts | **66.0 KB/s** | 0.382 pts |
| FishNet | 16.3 KB/s | **0.057 pts** | 80.4 KB/s | **0.287 pts** |
| Mirror | 28.2 KB/s | 0.117 pts | 124 KB/s | 0.463 pts |
| NGO | 33.3 KB/s | 0.589 pts | – | – |
| Fusion | 25.7 KB/s | 0.139 pts | 137 KB/s | 1.25 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/34024137258) · [raw datapoints](latest.json).
