_Last run 2026-11-09: PurrNet 1.26.0-beta.7 · FishNet 4.7.3 · Unity 6000.5.4f1 · 2000 objects per test · 10 s windows · sessions 100c @ 30 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 30 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**State replication** (100 connections @ 30 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (2/3) | 41.22 MB/s | 86.9% | 34.07 MB/s | 11 | 124.9 ms |
| FishNet | Overloaded (2/3) | 50.86 MB/s | 103.6% | 184.59 MB/s | 368 | 663.6 ms |

**Messaging** (100 connections @ 30 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (1/2) | 21.16 MB/s | 79.9% | 4.65 MB/s | 0 | 51.4 ms |
| FishNet | Overloaded (1/2) | 19.93 MB/s | 64.9% | 143.36 MB/s | 51 | 232.4 ms |

**Spawn / despawn** (100 connections @ 30 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 33.62 MB/s | 135.5% | 3.38 MB/s | 0 | 16.7 ms |
| FishNet | Overloaded (1/1) | 16.62 MB/s | 100.4% | 162.47 MB/s | 126 | 38.6 ms |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42542056128) · [raw datapoints](latest.json).
