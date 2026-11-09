_Last run 2026-11-09: PurrNet 1.26.0-beta.7 · FishNet 4.7.3 · Unity 6000.5.4f1 · 2000 objects per test · 10 s windows · sessions 50c @ 30 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 50 connections @ 30 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Who's ahead, 50 connections @ 30 Hz** (best per category; no averaging across categories)

| Category | Bandwidth | Server CPU | GC alloc |
|---|---:|---:|---:|
| State replication | PurrNet | PurrNet | PurrNet |
| Messaging | – | – | – |
| Spawn / despawn | FishNet | PurrNet | PurrNet |

**State replication** (50 connections @ 30 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | **20.37 MB/s** | **38.6%** | **10.04 MB/s** | **4** | **19.7 ms** |
| FishNet | Completed | 27.08 MB/s | 56.6% | 109.45 MB/s | 209 | 33.1 ms |

**Messaging** (50 connections @ 30 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (1/2) | 6.16 MB/s | 58.6% | 6.83 MB/s | 1 | 47.0 ms |
| FishNet | Overloaded (1/2) | 10.51 MB/s | 58.4% | 24.35 MB/s | 27 | 73.2 ms |

**Spawn / despawn** (50 connections @ 30 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 9.60 MB/s | **51.0%** | **1.43 MB/s** | **0** | **16.7 ms** |
| FishNet | Completed | **8.28 MB/s** | 64.9% | 109.69 MB/s | 127 | 24.0 ms |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42596080351) · [raw datapoints](latest.json).
