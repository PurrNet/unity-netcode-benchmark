_Last run 2026-09-04: PurrNet 1.23.0-beta.26 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="Server downstream on-wire at 100 connections; Server CPU at 100 connections. Best value per row highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 13.9 | 14.7 | 204 | 14.3 | **0.0** |
| MoveY | 493 | 1,252 | 2,435 | 3,186 | **0.0** |
| MoveAllAxis | 1,318 | 2,024 | 4,418 | 4,881 | **0.0** |
| MoveWander | 1,889 | 2,840 | 5,186 | 6,676 | **0.0** |
| SendRPC | 1,782 | 1,447 | 3,044 | 3,772 | **0.0** |
| Static | 13.8 | 14.2 | 173 | 14.1 | **0.0** |
| SpawnChurn | 782 | 645 | 861 | 1,830 | **0.0** |
| ClientInput | 91.4 | 92.6 | 282 | 117 | **0.0** |
| SyncVars | 2,501 | 3,500 | 4,862 | 4,293 | **0.0** |

**Server CPU at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | **1.2** | 2.0 | 5.2 | 1.8 | 8.2 |
| MoveY | 10.2 | **6.2** | 10.2 | 73.2 | 23.0 |
| MoveAllAxis | 12.6 | **4.3** | 11.6 | 73.3 | 23.0 |
| MoveWander | 13.7 | **5.1** | 12.7 | 74.0 | 24.5 |
| SendRPC | **8.2** | 9.4 | 16.3 | 73.1 | 16.5 |
| Static | **1.4** | 1.6 | 5.4 | 1.9 | 9.6 |
| SpawnChurn | 14.2 | **7.8** | 9.5 | 10.2 | 11.8 |
| ClientInput | **3.6** | 5.2 | 7.3 | 3.9 | 10.1 |
| SyncVars | **6.9** | 7.4 | 14.1 | 78.6 | 16.0 |

</details>

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33872472252), [raw datapoints](docs/latest.json).
