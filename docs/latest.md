_Last run 2026-11-09: PurrNet 1.26.0-beta.7 · FishNet 4.7.3 · Unity 6000.5.4f1 · 2000 objects per test · 10 s windows · sessions 100c @ 30 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 30 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**State replication** (100 connections @ 30 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (2/3) | 42.10 MB/s | 81.0% | 32.93 MB/s | 14 | 41.0 ms |
| FishNet | Overloaded (2/3) | 50.98 MB/s | 104.1% | 177.48 MB/s | 369 | 671.6 ms |

**Messaging** (100 connections @ 30 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (1/2) | 20.57 MB/s | 77.6% | 3.94 MB/s | 1 | 53.3 ms |
| FishNet | Overloaded (1/2) | 19.88 MB/s | 64.7% | 95.61 MB/s | 50 | 205.8 ms |

**Spawn / despawn** (100 connections @ 30 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 34.48 MB/s | 139.8% | 3.36 MB/s | 1 | 16.9 ms |
| FishNet | Overloaded (1/1) | 16.59 MB/s | 97.9% | 162.62 MB/s | 124 | 37.0 ms |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42539824766) · [raw datapoints](latest.json).
