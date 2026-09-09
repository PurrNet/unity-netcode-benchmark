_Last run 2026-09-09: PurrNet 1.23.0-beta.44 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

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
| PurrNet | Completed | **1.63 MB/s** | **6.0%** | **143 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 2.53 MB/s | 6.3% | 739 KB/s | 29 | 17.4 ms |
| Mirror | Completed | 4.10 MB/s | 12.7% | 3.09 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.86 MB/s | 78.6% | 1.3 KB/s | 0 | 51.3 ms |
| Fusion | Completed | 3.50 MB/s | 21.3% | 1.05 MB/s | 16 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **719 KB/s** | **5.6%** | **63.6 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 773 KB/s | 7.3% | 888 KB/s | 29 | 17.6 ms |
| Mirror | Completed | 1.63 MB/s | 11.9% | 3.60 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.91 MB/s | 38.2% | 48.4 KB/s | 1 | 44.8 ms |
| Fusion | Completed | 1.97 MB/s | 12.8% | 1005 KB/s | 5 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 737 KB/s | 9.4% | **485 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | **643 KB/s** | **7.9%** | 1.41 MB/s | 23 | 17.5 ms |
| Mirror | Completed | 854 KB/s | 9.5% | 4.50 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 2.16 MB/s | 11.1% | 1.04 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **651 KB/s** | 11.8% | 733 KB/s | 2 | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **11.9 KB/s** | **0.048 pts** | **60.0 KB/s** | 0.277 pts |
| FishNet | 16.6 KB/s | 0.053 pts | 81.9 KB/s | **0.255 pts** |
| Mirror | 28.0 KB/s | 0.104 pts | 124 KB/s | 0.407 pts |
| NGO | 33.7 KB/s | 0.545 pts | – | – |
| Fusion | 25.8 KB/s | 0.135 pts | 144 KB/s | 0.944 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/34383416617) · [raw datapoints](latest.json).
