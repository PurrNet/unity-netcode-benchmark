_Last run 2026-09-03: PurrNet 1.23.0-beta.23 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="Server downstream on-wire at 100 connections; Server CPU at 100 connections. Best value per row highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 13.6 | 14.1 | 171 | **11.6** | 224 |
| MoveY | **490** | 1,248 | 2,428 | 3,110 | 2,863 |
| MoveAllAxis | **1,265** | 2,025 | 4,427 | 4,939 | 2,779 |
| MoveWander | **1,679** | 2,839 | 5,192 | 6,548 | 3,567 |
| SendRPC | 1,783 | **1,447** | 3,015 | 3,241 | 3,793 |
| Static | 13.8 | 14.1 | 171 | **11.6** | 410 |
| SpawnChurn | 804 | 646 | 795 | 944 | **371** |
| ClientInput | **92.5** | 93.8 | 280 | 115 | 216 |
| SyncVars | **2,660** | 3,645 | 4,975 | 4,156 | 3,386 |

**Server CPU at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 7.0 | **3.6** | 7.2 | 6.0 | 8.2 |
| MoveY | 24.5 | **7.4** | 10.9 | 66.3 | 14.3 |
| MoveAllAxis | 19.7 | **4.7** | 12.8 | 49.6 | 13.8 |
| MoveWander | 19.3 | **4.3** | 15.5 | 57.5 | 15.1 |
| SendRPC | 14.3 | **11.7** | 20.0 | 59.3 | 13.1 |
| Static | 6.5 | **4.0** | 8.8 | 7.3 | 8.5 |
| SpawnChurn | 21.7 | **9.0** | 14.5 | 9.7 | 17.5 |
| ClientInput | 8.1 | 5.7 | 10.7 | **5.3** | 24.4 |
| SyncVars | 12.2 | **9.3** | 17.1 | 46.4 | 12.9 |

</details>

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33806833133), [raw datapoints](docs/latest.json).
