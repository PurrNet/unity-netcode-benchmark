_Last run 2026-10-20: PurrNet 1.25.0-beta.7 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 10c @ 20 Hz / 100c @ 20 Hz / 100c @ 60 Hz._

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
| PurrNet | Completed | **1.66 MB/s** | **5.5%** | **587 KB/s** | **4** | **16.7 ms** |
| FishNet | Completed | 2.53 MB/s | 6.5% | 755 KB/s | 30 | 17.4 ms |
| Mirror | Completed | 4.12 MB/s | 12.6% | 3.04 MB/s | 23 | **16.7 ms** |
| NGO | Overloaded (3/3) | 5.01 MB/s | 75.2% | 0.5 KB/s | 0 | 46.9 ms |
| Fusion | Completed | 3.51 MB/s | 21.6% | 1.04 MB/s | 17 | **16.7 ms** |

**Messaging** (100 connections @ 20 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **719 KB/s** | **5.5%** | **66.9 KB/s** | **1** | **16.7 ms** |
| FishNet | Completed | 773 KB/s | 7.5% | 869 KB/s | 30 | 17.6 ms |
| Mirror | Completed | 1.64 MB/s | 12.0% | 3.53 MB/s | 19 | **16.7 ms** |
| NGO | Overloaded (1/2) | 1.77 MB/s | 38.5% | 47.3 KB/s | 1 | 40.2 ms |
| Fusion | Completed | 1.97 MB/s | 18.5% | 1.13 MB/s | 4 | **16.7 ms** |

**Spawn / despawn** (100 connections @ 20 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 742 KB/s | 9.0% | **442 KB/s** | **1** | 16.7 ms |
| FishNet | Completed | **643 KB/s** | **8.0%** | 1.47 MB/s | 22 | 16.7 ms |
| Mirror | Completed | 860 KB/s | 9.4% | 4.42 MB/s | 12 | 16.7 ms |
| NGO | Completed | 2.10 MB/s | 11.0% | 1.03 MB/s | 11 | 16.7 ms |
| Fusion | Completed | **637 KB/s** | 11.8% | 950 KB/s | 3 | 16.7 ms |

**What one more costs** (marginal server cost; 10 → 100 connections at 20 Hz; 20 → 60 Hz at 100 connections)

| Netcode | Bandwidth per conn | Server CPU per conn | Bandwidth per Hz | Server CPU per Hz |
|---|---:|---:|---:|---:|
| PurrNet | **12.1 KB/s** | **0.045 pts** | **56.9 KB/s** | **0.259 pts** |
| FishNet | 16.6 KB/s | 0.056 pts | 82.0 KB/s | **0.251 pts** |
| Mirror | 28.2 KB/s | 0.104 pts | 123 KB/s | 0.404 pts |
| NGO | 34.0 KB/s | 0.529 pts | – | – |
| Fusion | 25.7 KB/s | 0.157 pts | 116 KB/s | 1.28 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/39431451208) · [raw datapoints](latest.json).
