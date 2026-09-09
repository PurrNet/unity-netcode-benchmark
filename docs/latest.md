_Last run 2026-09-09: PurrNet 1.23.0-beta.45 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

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
| Spawn / despawn | FishNet, Fusion | FishNet | PurrNet, Fusion |

**State replication** (100 connections @ 20 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **1.67 MB/s** | **6.0%** | **125 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 2.53 MB/s | 6.4% | 762 KB/s | 28 | 17.4 ms |
| Mirror | Completed | 4.12 MB/s | 12.6% | 3.04 MB/s | 24 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.87 MB/s | 75.4% | 1.5 KB/s | 0 | 47.7 ms |
| Fusion | Completed | 3.50 MB/s | 21.1% | 1009 KB/s | 18 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **719 KB/s** | **5.7%** | **62.2 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 770 KB/s | 7.3% | 911 KB/s | 31 | 17.5 ms |
| Mirror | Completed | 1.64 MB/s | 11.9% | 3.63 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.65 MB/s | 38.3% | 48.7 KB/s | 1 | 41.2 ms |
| Fusion | Completed | 1.98 MB/s | 12.8% | 941 KB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 739 KB/s | 9.3% | **491 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | **643 KB/s** | **7.8%** | 1.50 MB/s | 23 | 17.5 ms |
| Mirror | Completed | 791 KB/s | 8.5% | 4.33 MB/s | 11 | **16.7 ms** |
| NGO | Completed | 1.86 MB/s | 8.6% | 1.04 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **631 KB/s** | 11.7% | **482 KB/s** | 2 | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **12.1 KB/s** | **0.048 pts** | **59.7 KB/s** | 0.277 pts |
| FishNet | 16.6 KB/s | 0.053 pts | 82.0 KB/s | **0.254 pts** |
| Mirror | 28.1 KB/s | 0.103 pts | 123 KB/s | 0.411 pts |
| NGO | 32.3 KB/s | 0.523 pts | – | – |
| Fusion | 25.7 KB/s | 0.133 pts | 137 KB/s | 0.936 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/34398328852) · [raw datapoints](latest.json).
