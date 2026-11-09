_Last run 2026-11-09: PurrNet 1.26.0-beta.7 · FishNet 4.7.3 · Unity 6000.5.4f1 · 2000 objects per test · 10 s windows · sessions 50c @ 30 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 50 connections @ 30 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Who's ahead, 50 connections @ 30 Hz** (best per category; no averaging across categories)

| Category | Bandwidth | Server CPU | GC alloc |
|---|---:|---:|---:|
| State replication | tie | tie | tie |
| Messaging | – | – | – |
| Spawn / despawn | FishNet | FishNet | PurrNet |

**State replication** (50 connections @ 30 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 22.29 MB/s | 37.5% | 3.58 MB/s | 2 | 17.6 ms |
| FishNet | Overloaded (1/3) | 25.85 MB/s | 56.2% | 110.42 MB/s | 206 | 35.7 ms |

**Messaging** (50 connections @ 30 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (1/2) | 18.40 MB/s | 68.7% | 5.31 MB/s | 1 | 46.0 ms |
| FishNet | Overloaded (1/2) | 9.52 MB/s | 57.8% | 25.30 MB/s | 26 | 70.9 ms |

**Spawn / despawn** (50 connections @ 30 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 15.28 MB/s | 70.7% | **1.83 MB/s** | **0** | **16.7 ms** |
| FishNet | Completed | **8.31 MB/s** | **65.1%** | 106.40 MB/s | 124 | 25.2 ms |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42649270961) · [raw datapoints](latest.json).
