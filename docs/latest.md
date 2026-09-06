_Last run 2026-09-05: PurrNet 1.23.0-beta.30 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

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
| PurrNet | Completed | **1.81 MB/s** | 7.6% | **568 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 2.53 MB/s | **6.4%** | 760 KB/s | 30 | 17.4 ms |
| Mirror | Completed | 4.13 MB/s | 12.9% | 3.11 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 4.98 MB/s | 74.7% | 1.3 KB/s | 0 | 47.3 ms |
| Fusion | Completed | 3.48 MB/s | 21.1% | 1021 KB/s | 17 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 935 KB/s | **5.9%** | **734 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | **773 KB/s** | 7.3% | 909 KB/s | 30 | 17.6 ms |
| Mirror | Completed | 1.63 MB/s | 11.8% | 3.52 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.73 MB/s | 38.2% | 48.5 KB/s | 1 | 41.1 ms |
| Fusion | Completed | 1.97 MB/s | 12.7% | 972 KB/s | 3 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 773 KB/s | 13.7% | 3.17 MB/s | 3 | **16.7 ms** |
| FishNet | Completed | **643 KB/s** | **7.8%** | 1.52 MB/s | 22 | 17.5 ms |
| Mirror | Completed | 852 KB/s | 9.4% | 4.49 MB/s | 12 | **16.7 ms** |
| NGO | Completed | 2.13 MB/s | 11.1% | 1.03 MB/s | 11 | **16.7 ms** |
| Fusion | Completed | **638 KB/s** | 11.7% | **386 KB/s** | **2** | **16.7 ms** |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **13.7 KB/s** | 0.064 pts | **66.3 KB/s** | 0.354 pts |
| FishNet | 16.6 KB/s | **0.054 pts** | 81.8 KB/s | **0.256 pts** |
| Mirror | 28.2 KB/s | 0.105 pts | 124 KB/s | 0.408 pts |
| NGO | 33.7 KB/s | 0.523 pts | – | – |
| Fusion | 25.6 KB/s | 0.133 pts | 147 KB/s | 0.897 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33959665448) · [raw datapoints](latest.json).
