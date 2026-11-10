_Last run 2026-11-10: PurrNet 1.26.0-beta.13 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 30 Hz × 2000 objects / 100c @ 60 Hz._

_Note: NGO at 100c @ 30 Hz × 2000 objects: resource limit exceeded (8 GiB memory); NGO at 100c @ 60 Hz: resource limit exceeded (8 GiB memory)._

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
| Spawn / despawn | FishNet, Fusion | FishNet | PurrNet |

**State replication** (100 connections @ 20 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **1.49 MB/s** | **4.8%** | **28.9 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 2.53 MB/s | 6.4% | 771 KB/s | 29 | 17.4 ms |
| Mirror | Completed | 4.12 MB/s | 12.6% | 3.04 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.88 MB/s | 74.9% | 0.7 KB/s | 0 | 46.8 ms |
| Fusion | Completed | 3.50 MB/s | 21.8% | 1.01 MB/s | 17 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **747 KB/s** | **6.6%** | **125 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 769 KB/s | 7.5% | 848 KB/s | 29 | 17.6 ms |
| Mirror | Completed | 1.64 MB/s | 11.9% | 3.53 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.74 MB/s | 38.5% | 47.3 KB/s | 1 | 40.2 ms |
| Fusion | Completed | 1.98 MB/s | 13.0% | 931 KB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 701 KB/s | 7.9% | **67.6 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | **640 KB/s** | **7.8%** | 1.44 MB/s | 22 | 17.6 ms |
| Mirror | Completed | 860 KB/s | 9.5% | 4.41 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 2.14 MB/s | 11.1% | 1.04 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **639 KB/s** | 11.7% | 483 KB/s | 2 | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **11.3 KB/s** | **0.044 pts** | **57.4 KB/s** | **0.202 pts** |
| FishNet | 16.6 KB/s | 0.055 pts | 82.0 KB/s | 0.251 pts |
| Mirror | 28.2 KB/s | 0.104 pts | 124 KB/s | 0.406 pts |
| NGO | 33.2 KB/s | 0.526 pts | – | – |
| Fusion | 25.7 KB/s | 0.137 pts | 139 KB/s | 0.945 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42799932985) · [raw datapoints](latest.json).
