_Last run 2026-09-09: PurrNet 1.23.0-beta.42 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

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
| PurrNet | Completed | **1.70 MB/s** | **6.0%** | **49.9 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 2.53 MB/s | 6.4% | 762 KB/s | 29 | 17.4 ms |
| Mirror | Completed | 4.11 MB/s | 12.7% | 3.05 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.86 MB/s | 74.8% | 1.3 KB/s | 0 | 47.2 ms |
| Fusion | Completed | 3.50 MB/s | 21.3% | 1.02 MB/s | 17 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **719 KB/s** | **5.6%** | **63.2 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 769 KB/s | 7.3% | 880 KB/s | 30 | 17.5 ms |
| Mirror | Completed | 1.63 MB/s | 11.8% | 3.56 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.74 MB/s | 38.3% | 48.4 KB/s | 1 | 40.9 ms |
| Fusion | Completed | 1.98 MB/s | 13.5% | 1.29 MB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 739 KB/s | 9.3% | **504 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | **643 KB/s** | **7.9%** | 1.50 MB/s | 22 | 17.6 ms |
| Mirror | Completed | 859 KB/s | 9.4% | 4.51 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 1.84 MB/s | 8.6% | 1.04 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **639 KB/s** | 11.8% | 584 KB/s | **1** | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **12.3 KB/s** | **0.048 pts** | **59.6 KB/s** | 0.272 pts |
| FishNet | 16.6 KB/s | 0.054 pts | 81.8 KB/s | **0.251 pts** |
| Mirror | 28.1 KB/s | 0.104 pts | 124 KB/s | 0.418 pts |
| NGO | 32.5 KB/s | 0.520 pts | – | – |
| Fusion | 25.7 KB/s | 0.138 pts | 131 KB/s | 1.21 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/34364138644) · [raw datapoints](latest.json).
