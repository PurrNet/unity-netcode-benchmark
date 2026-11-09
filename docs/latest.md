_Last run 2026-11-09: PurrNet 1.26.0-beta.10 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

_Note: NGO at 100c @ 60 Hz: resource limit exceeded (8 GiB memory)._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 20 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Who's ahead, 100 connections @ 20 Hz** (best per category; no averaging across categories)

| Category | Bandwidth | Server CPU | GC alloc |
|---|---:|---:|---:|
| State replication | PurrNet | PurrNet | FishNet |
| Messaging | PurrNet | PurrNet, FishNet | FishNet |
| Spawn / despawn | Fusion | FishNet | Fusion |

**State replication** (100 connections @ 20 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **1.51 MB/s** | **5.1%** | 1.13 MB/s | **5** | **16.7 ms** |
| FishNet | Completed | 2.53 MB/s | 6.2% | **678 KB/s** | 28 | 17.4 ms |
| Mirror | Completed | 4.12 MB/s | 12.8% | 3.17 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.87 MB/s | 78.3% | 0.5 KB/s | 0 | 51.0 ms |
| Fusion | Completed | 3.51 MB/s | 21.8% | 1017 KB/s | 17 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **747 KB/s** | **7.2%** | 1.02 MB/s | **3** | **16.7 ms** |
| FishNet | Completed | 770 KB/s | **7.2%** | **816 KB/s** | 28 | 17.6 ms |
| Mirror | Completed | 1.62 MB/s | 11.9% | 3.61 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.86 MB/s | 38.3% | 47.6 KB/s | 1 | 44.6 ms |
| Fusion | Completed | 1.97 MB/s | 13.0% | 913 KB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 684 KB/s | 8.5% | 990 KB/s | **1** | **16.7 ms** |
| FishNet | Completed | 643 KB/s | **7.8%** | 1.34 MB/s | 23 | 17.5 ms |
| Mirror | Completed | 790 KB/s | 8.5% | 4.21 MB/s | 11 | **16.7 ms** |
| NGO | Completed | 2.12 MB/s | 11.1% | 1.04 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **618 KB/s** | 11.6% | **546 KB/s** | 2 | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **11.4 KB/s** | **0.048 pts** | **58.0 KB/s** | **0.214 pts** |
| FishNet | 16.6 KB/s | 0.053 pts | 81.8 KB/s | 0.252 pts |
| Mirror | 28.0 KB/s | 0.103 pts | 123 KB/s | 0.407 pts |
| NGO | 33.6 KB/s | 0.545 pts | – | – |
| Fusion | 25.7 KB/s | 0.137 pts | 139 KB/s | 0.925 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42700271048) · [raw datapoints](latest.json).
