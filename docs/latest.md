_Last run 2026-09-03: PurrNet 1.23.0-beta.23 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="Server downstream on-wire at 100 connections; Server CPU minus idle at 100 connections. Best value per row highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| MoveY | **490** | 1,249 | 2,437 | 3,098 | 2,866 |
| MoveAllAxis | **1,281** | 2,024 | 4,422 | 5,025 | 2,786 |
| MoveWander | **1,671** | 2,839 | 5,194 | 6,534 | 3,720 |
| SendRPC | 1,782 | **1,450** | 3,015 | 3,285 | 3,832 |
| Static | 13.8 | 14.2 | 171 | **11.6** | 380 |
| SpawnChurn | 803 | 645 | 853 | 944 | **404** |
| ClientInput | **92.3** | 93.7 | 280 | 114 | 218 |
| SyncVars | **2,640** | 3,642 | 4,997 | 4,251 | 3,401 |

**Server CPU minus idle at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| MoveY | 6.2 | **3.8** | 5.7 | 52.7 | 9.6 |
| MoveAllAxis | 5.1 | **3.4** | 6.3 | 46.7 | 11.5 |
| MoveWander | 6.3 | **5.2** | 7.1 | 53.8 | 21.1 |
| SendRPC | **6.2** | 9.9 | 15.2 | 48.4 | 14.4 |
| Static | 0.8 | 1.2 | 1.0 | **-2.2** | 4.4 |
| SpawnChurn | 20.4 | 7.1 | 6.7 | **0.6** | 13.7 |
| ClientInput | 4.4 | 3.1 | 3.1 | **-2.6** | 20.7 |
| SyncVars | **7.4** | 7.6 | 11.4 | 43.0 | 14.0 |

</details>

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33801754829), [raw datapoints](docs/latest.json).
