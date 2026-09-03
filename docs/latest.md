_Last run 2026-09-03: PurrNet 1.23.0-beta.20 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 50 / 100._

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| MoveY | **490** | 1,251 | 2,434 | 3,140 | 2,878 |
| MoveAllAxis | **1,283** | 2,024 | 4,413 | 4,856 | 2,775 |
| MoveWander | **1,686** | 2,841 | 5,177 | 6,511 | 3,519 |
| SendRPC | 1,484 | **1,090** | 2,773 | 2,875 | 3,773 |
| Static | 13.8 | 14.1 | 170 | **11.6** | 398 |
| SpawnChurn | 742 | 645 | 851 | 798 | **343** |
| ClientInput | **89.8** | 93.9 | 283 | 111 | 214 |
| SyncVars | 5,388 | 3,415 | 4,757 | 4,121 | **2,801** |

**Server CPU minus idle at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| MoveY | 17.5 | **2.9** | 5.0 | 43.5 | 7.7 |
| MoveAllAxis | 15.2 | **2.3** | 6.2 | 57.4 | 10.0 |
| MoveWander | 16.8 | **3.8** | 6.5 | 47.3 | 9.1 |
| SendRPC | **6.1** | 6.9 | 11.4 | 45.3 | 6.1 |
| Static | **-0.8** | 0.9 | 1.1 | -0.2 | 0.8 |
| SpawnChurn | 11.2 | 6.5 | 5.3 | **2.7** | 9.2 |
| ClientInput | 1.0 | 3.3 | 1.9 | **0.2** | 14.9 |
| SyncVars | 6.6 | **4.8** | 7.8 | 51.5 | 6.4 |

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33774317390), [raw datapoints](docs/latest.json).
