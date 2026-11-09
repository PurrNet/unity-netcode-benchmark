_Last run 2026-11-09: PurrNet 1.26.0-beta.7 · FishNet 4.7.3 · Unity 6000.5.4f1 · 2000 objects per test · 10 s windows · sessions 100c @ 30 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 30 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**State replication** (100 connections @ 30 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (3/3) | 38.53 MB/s | 69.1% | 37.75 MB/s | 10 | 125.5 ms |
| FishNet | Overloaded (2/3) | 51.58 MB/s | 109.6% | 215.69 MB/s | 367 | 936.9 ms |

**Messaging** (100 connections @ 30 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (1/2) | 10.60 MB/s | 53.2% | 12.53 MB/s | 1 | 205.2 ms |
| FishNet | Overloaded (1/2) | 19.33 MB/s | 65.5% | 51.93 MB/s | 48 | 566.3 ms |

**Spawn / despawn** (100 connections @ 30 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (1/1) | 22.03 MB/s | 99.4% | 16.03 MB/s | 1 | 241.1 ms |
| FishNet | Overloaded (1/1) | 16.63 MB/s | 113.4% | 160.71 MB/s | 127 | 43.3 ms |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42536150942) · [raw datapoints](latest.json).
