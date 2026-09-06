_Last run 2026-09-06: PurrNet 1.23.0-beta.38 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

_Note: NGO at 100c @ 60 Hz: resource limit exceeded (8 GiB memory)._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Who's ahead, 100 connections @ 20 Hz** (best per category; no averaging across categories)

| Category | Bandwidth | Server CPU | GC alloc |
|---|---:|---:|---:|
| State replication | PurrNet | PurrNet | PurrNet |
| Messaging | PurrNet | PurrNet | PurrNet |
| Spawn / despawn | FishNet, Fusion | FishNet | Fusion |

**State replication** (100 connections @ 20 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **1.71 MB/s** | **5.9%** | **51.5 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 2.52 MB/s | 6.3% | 765 KB/s | 29 | 17.4 ms |
| Mirror | Completed | 4.13 MB/s | 12.8% | 3.15 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.99 MB/s | 75.0% | 1.5 KB/s | 0 | 47.5 ms |
| Fusion | Completed | 3.49 MB/s | 21.2% | 1.01 MB/s | 16 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **719 KB/s** | **5.6%** | **66.2 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 770 KB/s | 7.3% | 886 KB/s | 29 | 17.5 ms |
| Mirror | Completed | 1.63 MB/s | 11.8% | 3.64 MB/s | 18 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.76 MB/s | 38.2% | 48.5 KB/s | 1 | 41.1 ms |
| Fusion | Completed | 1.98 MB/s | 13.0% | 781 KB/s | 3 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 738 KB/s | 9.5% | 699 KB/s | **2** | **16.7 ms** |
| FishNet | Completed | **640 KB/s** | **7.8%** | 1.50 MB/s | 22 | 17.5 ms |
| Mirror | Completed | 855 KB/s | 9.5% | 4.59 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 2.14 MB/s | 11.2% | 1.04 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **646 KB/s** | 11.8% | **584 KB/s** | **2** | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **12.4 KB/s** | **0.047 pts** | **58.6 KB/s** | 0.281 pts |
| FishNet | 16.5 KB/s | 0.052 pts | 82.0 KB/s | **0.254 pts** |
| Mirror | 28.2 KB/s | 0.104 pts | 123 KB/s | 0.403 pts |
| NGO | 33.9 KB/s | 0.525 pts | – | – |
| Fusion | 25.6 KB/s | 0.134 pts | 152 KB/s | 1.20 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/34054617470) · [raw datapoints](latest.json).
