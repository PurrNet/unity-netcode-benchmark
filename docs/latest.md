_Last run 2026-09-03: PurrNet 1.23.0-beta.23 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="Server downstream on-wire at 100 connections; Server CPU at 100 connections. Best value per row highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 13.9 | 14.4 | 187 | **12.1** | 245 |
| MoveY | **490** | 1,249 | 2,437 | 3,098 | 2,866 |
| MoveAllAxis | **1,281** | 2,024 | 4,422 | 5,025 | 2,786 |
| MoveWander | **1,671** | 2,839 | 5,194 | 6,534 | 3,720 |
| SendRPC | 1,782 | **1,450** | 3,015 | 3,285 | 3,832 |
| Static | 13.8 | 14.2 | 171 | **11.6** | 380 |
| SpawnChurn | 803 | 645 | 853 | 944 | **404** |
| ClientInput | **92.3** | 93.7 | 280 | 114 | 218 |
| SyncVars | **2,640** | 3,642 | 4,997 | 4,251 | 3,401 |

**Server CPU at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | **3.4** | 5.2 | 11.0 | 8.6 | 10.4 |
| MoveY | 9.6 | **9.0** | 16.7 | 61.3 | 19.9 |
| MoveAllAxis | **8.5** | 8.6 | 17.3 | 55.3 | 21.9 |
| MoveWander | **9.7** | 10.4 | 18.1 | 62.4 | 31.5 |
| SendRPC | **9.6** | 15.1 | 26.2 | 57.0 | 24.8 |
| Static | **4.2** | 6.4 | 12.0 | 6.4 | 14.7 |
| SpawnChurn | 23.8 | 12.3 | 17.7 | **9.1** | 24.1 |
| ClientInput | 7.8 | 8.3 | 14.1 | **6.0** | 31.1 |
| SyncVars | **10.8** | 12.8 | 22.4 | 51.6 | 24.4 |

</details>

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33801754829), [raw datapoints](docs/latest.json).
