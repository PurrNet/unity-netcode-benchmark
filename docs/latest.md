_Last run 2026-09-06: PurrNet 1.23.0-beta.35 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 10 s windows · sessions 100c @ 60 Hz._

_Note: NGO at 100c @ 60 Hz: resource limit exceeded (8 GiB memory)._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 60 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Who's ahead, 100 connections @ 60 Hz** (best per category; no averaging across categories)

| Category | Bandwidth | Server CPU | GC alloc |
|---|---:|---:|---:|
| State replication | PurrNet | FishNet | PurrNet |
| Messaging | FishNet | PurrNet | PurrNet |
| Spawn / despawn | FishNet | FishNet, Mirror | Fusion |

**State replication** (100 connections @ 60 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **5.28 MB/s** | 19.9% | **1.06 MB/s** | **3** | **16.7 ms** |
| FishNet | Completed | 7.53 MB/s | **15.9%** | 2.10 MB/s | 78 | 17.5 ms |
| Mirror | Completed | 11.30 MB/s | 30.2% | 6.21 MB/s | 48 | **16.7 ms** |
| NGO | Did not complete | – | – | – | 0 | 24.4 ms |
| Fusion | Completed | 10.41 MB/s | 66.2% | 3.70 MB/s | 47 | **16.7 ms** |

**Messaging** (100 connections @ 60 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 2.71 MB/s | **15.6%** | **2.09 MB/s** | **2** | **16.7 ms** |
| FishNet | Completed | **2.23 MB/s** | 18.1% | 2.40 MB/s | 91 | 17.6 ms |
| Mirror | Completed | 4.72 MB/s | 29.7% | 8.29 MB/s | 44 | **16.7 ms** |
| NGO | Did not complete | – | – | – | – | – |
| Fusion | Overloaded (1/2) | 5.92 MB/s | 71.3% | 1.56 MB/s | 2 | 1397.9 ms |

**Spawn / despawn** (100 connections @ 60 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 2.22 MB/s | 41.0% | 9.38 MB/s | 4 | **16.7 ms** |
| FishNet | Completed | **1.87 MB/s** | **19.6%** | 4.38 MB/s | 63 | 17.7 ms |
| Mirror | Completed | 2.13 MB/s | **19.5%** | 10.24 MB/s | 26 | **16.7 ms** |
| NGO | Did not complete | – | – | – | – | – |
| Fusion | Completed | 3.98 MB/s | 46.8% | **1.90 MB/s** | **1** | **16.7 ms** |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/34031707776) · [raw datapoints](latest.json).
