_Last run 2026-10-05: PurrNet 1.24.0-beta.30 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

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
| Spawn / despawn | FishNet, Fusion | FishNet | PurrNet |

**State replication** (100 connections @ 20 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **1.61 MB/s** | **5.7%** | **48.7 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 2.52 MB/s | 6.2% | 727 KB/s | 28 | 17.4 ms |
| Mirror | Completed | 4.10 MB/s | 12.8% | 3.11 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.89 MB/s | 79.5% | 1.3 KB/s | 0 | 51.6 ms |
| Fusion | Completed | 3.50 MB/s | 21.3% | 1.02 MB/s | 17 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **743 KB/s** | **5.9%** | **70.0 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 770 KB/s | 7.2% | 855 KB/s | 29 | 17.5 ms |
| Mirror | Completed | 1.64 MB/s | 12.0% | 3.66 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.74 MB/s | 39.4% | 48.4 KB/s | 1 | 45.4 ms |
| Fusion | Completed | 1.97 MB/s | 12.8% | 952 KB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 747 KB/s | 9.3% | **496 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | **640 KB/s** | **7.8%** | 1.51 MB/s | 23 | 17.6 ms |
| Mirror | Completed | 859 KB/s | 9.6% | 4.59 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 2.04 MB/s | 10.6% | 1.03 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **633 KB/s** | 11.7% | 694 KB/s | 2 | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **11.9 KB/s** | **0.047 pts** | **58.8 KB/s** | 0.277 pts |
| FishNet | 16.6 KB/s | 0.052 pts | 81.9 KB/s | **0.258 pts** |
| Mirror | 28.1 KB/s | 0.105 pts | 124 KB/s | 0.410 pts |
| NGO | 33.0 KB/s | 0.552 pts | – | – |
| Fusion | 25.7 KB/s | 0.134 pts | 138 KB/s | 0.911 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/37328339458) · [raw datapoints](latest.json).
