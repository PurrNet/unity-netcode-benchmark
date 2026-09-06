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
| PurrNet | Completed | **1.80 MB/s** | 7.4% | **468 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 2.52 MB/s | **6.3%** | 746 KB/s | 29 | 17.4 ms |
| Mirror | Completed | 4.12 MB/s | 12.8% | 3.08 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.80 MB/s | 75.4% | 1.3 KB/s | 0 | 47.6 ms |
| Fusion | Completed | 3.48 MB/s | 21.2% | 1.03 MB/s | 18 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 935 KB/s | **5.9%** | **709 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | **773 KB/s** | 7.2% | 872 KB/s | 30 | 17.6 ms |
| Mirror | Completed | 1.63 MB/s | 11.9% | 3.61 MB/s | 18 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.65 MB/s | 38.2% | 48.5 KB/s | 1 | 41.3 ms |
| Fusion | Completed | 1.97 MB/s | 12.7% | 950 KB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 756 KB/s | 13.4% | 3.19 MB/s | **2** | **16.7 ms** |
| FishNet | Completed | 643 KB/s | **7.8%** | 1.46 MB/s | 22 | 17.6 ms |
| Mirror | Completed | 859 KB/s | 9.5% | 4.52 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 2.12 MB/s | 11.2% | 1.04 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **625 KB/s** | 11.7% | **410 KB/s** | **2** | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **13.6 KB/s** | 0.063 pts | **65.7 KB/s** | 0.348 pts |
| FishNet | 16.6 KB/s | **0.052 pts** | 82.0 KB/s | **0.260 pts** |
| Mirror | 28.1 KB/s | 0.105 pts | 122 KB/s | 0.401 pts |
| NGO | 32.4 KB/s | 0.527 pts | – | – |
| Fusion | 25.6 KB/s | 0.134 pts | 139 KB/s | 0.968 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/34020614052) · [raw datapoints](latest.json).
