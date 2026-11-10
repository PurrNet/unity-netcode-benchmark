_Last run 2026-11-10: PurrNet 1.26.0-beta.9 · FishNet 4.7.3 · Unity 6000.5.4f1 · 2000 objects per test · 10 s windows · sessions 50c @ 30 Hz / 100c @ 30 Hz._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 30 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**State replication** (100 connections @ 30 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (2/3) | 4.95 MB/s | 71.5% | 32.10 MB/s | 9 | 3127.0 ms |
| FishNet | Overloaded (2/3) | 50.70 MB/s | 103.8% | 188.28 MB/s | 370 | 663.3 ms |

**Messaging** (100 connections @ 30 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (1/2) | 0.0 KB/s | 47.1% | 1.38 MB/s | 0 | 30.8 ms |
| FishNet | Overloaded (1/2) | 19.95 MB/s | 64.5% | 132.87 MB/s | 48 | 231.4 ms |

**Spawn / despawn** (100 connections @ 30 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 0.0 KB/s | 19.8% | 82.0 KB/s | 0 | 16.7 ms |
| FishNet | Overloaded (1/1) | 16.61 MB/s | 97.8% | 162.99 MB/s | 128 | 36.9 ms |

**What one more costs** (marginal server cost; 50 → 100 connections at 30 Hz)

| Netcode | Bandwidth per conn | Server CPU per conn |
|---|---:|---:|
| PurrNet | **-44.5 KB/s** | **-0.025 pts** |
| FishNet | 340 KB/s | 0.622 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42783271952) · [raw datapoints](latest.json).
