_Last run 2026-11-10: PurrNet 1.26.0-beta.11 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 2000 objects per test · 10 s windows · sessions 50c @ 30 Hz / 100c @ 30 Hz._

_Note: NGO at 50c @ 30 Hz: resource limit exceeded (8 GiB memory); NGO at 100c @ 30 Hz: resource limit exceeded (8 GiB memory)._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="latest-dark.svg">
  <img alt="At a glance, 100 connections @ 30 Hz; how it scales. Best value per column highlighted in green." src="latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Who's ahead, 100 connections @ 30 Hz** (best per category; no averaging across categories)

| Category | Bandwidth | Server CPU | GC alloc |
|---|---:|---:|---:|
| State replication | tie | tie | tie |
| Messaging | – | – | – |
| Spawn / despawn | Mirror | Mirror | PurrNet |

**State replication** (100 connections @ 30 Hz · MoveY, MoveWander, SyncVars)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 46.26 MB/s | 69.6% | 16.30 MB/s | 10 | 23.9 ms |
| FishNet | Overloaded (2/3) | 50.97 MB/s | 103.4% | 189.31 MB/s | 371 | 635.3 ms |
| Mirror | Overloaded (2/3) | 31.99 MB/s | 67.3% | 6.50 MB/s | 13 | 96.1 ms |
| NGO | Did not complete | – | – | – | 1 | 450.4 ms |
| Fusion | Overloaded (1/3) | 2.91 MB/s | 23.0% | 633 KB/s | 1 | 86.5 ms |

**Messaging** (100 connections @ 30 Hz · SendRPC, ClientInput)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Overloaded (1/2) | 44.63 MB/s | 96.4% | 8.00 MB/s | 2 | 63.4 ms |
| FishNet | Overloaded (1/2) | 20.05 MB/s | 64.3% | 148.64 MB/s | 49 | 226.6 ms |
| Mirror | Overloaded (1/2) | 8.34 MB/s | 49.8% | 49.38 MB/s | 20 | 15331.1 ms |
| NGO | Did not complete | – | – | – | – | – |
| Fusion | Overloaded (1/2) | 3.0 KB/s | 49.1% | 1.37 MB/s | 3 | 34.5 ms |

**Spawn / despawn** (100 connections @ 30 Hz · SpawnChurn)

| Netcode | Status | Bandwidth | Server CPU | GC alloc | Collections | Frame p99 |
|---|---:|---:|---:|---:|---:|---:|
| PurrNet | Completed | 30.55 MB/s | 129.3% | **1.10 MB/s** | **0** | 18.3 ms |
| FishNet | Overloaded (1/1) | 16.60 MB/s | 98.1% | 166.46 MB/s | 121 | 37.7 ms |
| Mirror | Completed | **0.0 KB/s** | **17.9%** | 86.64 MB/s | 15 | 19.9 ms |
| NGO | Did not complete | – | – | – | – | – |
| Fusion | Completed | 2.0 KB/s | 23.3% | 1.64 MB/s | 5 | **16.7 ms** |

**What one more costs** (marginal server cost; 50 → 100 connections at 30 Hz)

| Netcode | Bandwidth per conn | Server CPU per conn |
|---|---:|---:|
| PurrNet | 479 KB/s | 0.733 pts |
| FishNet | 349 KB/s | 0.620 pts |
| Mirror | **0.008 KB/s** | **0.027 pts** |
| NGO | – | – |
| Fusion | 13.4 KB/s | 0.082 pts |

</details>

Categories are reported separately, with no combined ranking. Bandwidth, CPU and allocation: averages; collections: total; frame p99: maximum. Categories that did not complete have no averages. Completed means the test finished. Overloaded means it finished but the server could not hold the 60 fps budget in that many tests (frame p99 past 33 ms or a sixth of frames dropped); its numbers are shown but never marked best, since they describe a saturated server. Idle and Static remain baselines; scaling requires the full suite.
Full results: [interactive report](https://purrnet.github.io/unity-netcode-benchmark/) · [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/42787654442) · [raw datapoints](latest.json).
