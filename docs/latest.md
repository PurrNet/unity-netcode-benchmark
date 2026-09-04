_Last run 2026-09-04: PurrNet ? · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="Server downstream on-wire at 100 connections; Server CPU at 100 connections. Best value per row highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 14.1 | 14.2 | 169 | **12.3** | 1,314 |
| MoveY | **485** | 1,253 | 2,464 | 2,934 | 2,805 |
| MoveAllAxis | **1,282** | 2,025 | 4,418 | 4,585 | 2,774 |
| MoveWander | **1,704** | 2,839 | 5,187 | 6,199 | 3,679 |
| SendRPC | 1,782 | **1,446** | 3,014 | 3,034 | 3,831 |
| Static | 13.8 | 14.2 | 171 | **11.6** | 405 |
| SpawnChurn | 743 | 645 | 851 | 944 | **388** |
| ClientInput | **91.2** | 93.2 | 277 | 115 | 217 |
| SyncVars | **2,496** | 3,475 | 4,774 | 3,885 | 3,223 |

**Server CPU at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 2.0 | **1.4** | 5.6 | 1.4 | 6.6 |
| MoveY | 9.9 | **3.8** | 5.7 | 31.7 | 12.2 |
| MoveAllAxis | 11.1 | **3.4** | 5.4 | 32.4 | 13.0 |
| MoveWander | 11.2 | **2.7** | 5.7 | 33.5 | 13.7 |
| SendRPC | 7.1 | **5.4** | 7.3 | 32.2 | 12.9 |
| Static | 1.7 | 1.4 | 3.8 | **1.1** | 8.1 |
| SpawnChurn | 11.0 | 4.4 | 5.3 | **3.7** | 9.8 |
| ClientInput | 2.4 | 2.8 | 5.1 | **1.8** | 9.4 |
| SyncVars | **3.9** | 4.3 | 6.9 | 35.8 | 13.4 |

</details>

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33863558632), [raw datapoints](docs/latest.json).
