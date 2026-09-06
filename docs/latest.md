_Last run 2026-09-06: PurrNet 1.23.0-beta.36 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

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
| Spawn / despawn | FishNet, Fusion | FishNet | Fusion |

**State replication** (100 connections @ 20 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **1.83 MB/s** | 7.2% | **158 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | 2.53 MB/s | **6.3%** | 719 KB/s | 30 | 17.4 ms |
| Mirror | Completed | 4.11 MB/s | 12.7% | 3.10 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.89 MB/s | 75.0% | 1.3 KB/s | 0 | 47.4 ms |
| Fusion | Completed | 3.49 MB/s | 21.2% | 1.01 MB/s | 16 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 935 KB/s | **5.7%** | **70.4 KB/s** | **0** | **16.7 ms** |
| FishNet | Completed | **770 KB/s** | 7.3% | 859 KB/s | 30 | 17.5 ms |
| Mirror | Completed | 1.64 MB/s | 12.0% | 3.62 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.67 MB/s | 38.2% | 48.5 KB/s | 1 | 41.1 ms |
| Fusion | Completed | 1.98 MB/s | 12.8% | 958 KB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 756 KB/s | 10.5% | 2.73 MB/s | **2** | **16.7 ms** |
| FishNet | Completed | **643 KB/s** | **7.9%** | 1.43 MB/s | 22 | 17.6 ms |
| Mirror | Completed | 857 KB/s | 9.6% | 4.52 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 1.85 MB/s | 8.5% | 1.04 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **632 KB/s** | 11.7% | **619 KB/s** | **2** | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **13.8 KB/s** | 0.057 pts | **65.6 KB/s** | 0.318 pts |
| FishNet | 16.6 KB/s | **0.054 pts** | 81.7 KB/s | **0.254 pts** |
| Mirror | 28.1 KB/s | 0.105 pts | 123 KB/s | 0.404 pts |
| NGO | 32.4 KB/s | 0.520 pts | – | – |
| Fusion | 25.6 KB/s | 0.134 pts | 143 KB/s | 1.19 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/34039781071) · [raw datapoints](latest.json).
