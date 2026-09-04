_Last run 2026-09-03: PurrNet 1.23.0-beta.24 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

_Note: Fusion ran with 1/100 clients._

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/latest-dark.svg">
  <img alt="Server downstream on-wire at 100 connections; Server CPU at 100 connections. Best value per row highlighted in green." src="docs/latest-light.svg">
</picture>

<details><summary>Same tables as text</summary>

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 13.6 | 14.3 | 169 | **11.6** | 50.4 |
| MoveY | 492 | 1,253 | 2,443 | 3,024 | **68.1** |
| MoveAllAxis | 1,295 | 2,020 | 4,423 | 4,952 | **67.2** |
| MoveWander | 1,694 | 2,840 | 5,182 | 6,619 | **77.7** |
| SendRPC | 1,782 | 1,446 | 3,013 | 3,412 | **80.1** |
| Static | 13.8 | 14.1 | 171 | **11.6** | 42.0 |
| SpawnChurn | 745 | 644 | 852 | 944 | **43.7** |
| ClientInput | 91.0 | 93.8 | 279 | 115 | **42.0** |
| SyncVars | 2,612 | 3,661 | 4,983 | 4,281 | **67.1** |

**Server CPU at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| Idle | 3.0 | **3.0** | 6.4 | 3.4 | 3.4 |
| MoveY | 11.4 | 7.0 | 10.5 | 42.6 | **1.5** |
| MoveAllAxis | 16.5 | 5.1 | 9.4 | 55.4 | **2.4** |
| MoveWander | 14.1 | 6.3 | 10.0 | 55.7 | **1.7** |
| SendRPC | 5.4 | 9.3 | 17.7 | 56.6 | **2.6** |
| Static | 1.7 | 5.0 | 8.5 | 5.0 | **1.3** |
| SpawnChurn | 10.0 | 12.0 | 11.0 | 9.7 | **3.5** |
| ClientInput | 3.6 | 9.0 | 7.9 | 5.9 | **2.5** |
| SyncVars | 7.7 | 8.4 | 13.2 | 62.3 | **2.3** |

</details>

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33815693476), [raw datapoints](docs/latest.json).
