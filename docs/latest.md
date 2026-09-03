_Last run 2026-09-03: PurrNet 1.23.0-beta.20 · FishNet 4.7.3 · Mirror 96.0.1 · NGO 2.13.2 · Fusion 2.1.2 Stable 2279 · Unity 6000.5.4f1 · 100 objects per test · 20 s windows · connections 10 / 25 / 50 / 100._

_Note: Fusion ran with 99 clients._

**Server downstream on-wire at 100 connections** (KB/s, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| MoveY | **491** | 1,249 | 2,438 | 2,960 | 2,874 |
| MoveAllAxis | **1,237** | 2,023 | 4,422 | 4,671 | 2,774 |
| MoveWander | **1,724** | 2,840 | 5,189 | 6,258 | 3,840 |
| SendRPC | 1,485 | **1,090** | 2,767 | 2,662 | 3,779 |
| Static | 13.8 | 14.2 | 170 | **11.6** | 723 |
| SpawnChurn | 742 | 645 | 852 | 944 | **533** |
| ClientInput | **89.7** | 93.9 | 279 | 114 | 229 |
| SyncVars | 5,351 | 3,411 | 4,748 | 3,899 | **3,024** |

**Server CPU minus idle at 100 connections** (% of one core, lower is better)

| Test | PurrNet | FishNet | Mirror | NGO | Fusion |
|---|---:|---:|---:|---:|---:|
| MoveY | 10.9 | 3.3 | **3.2** | 34.7 | 8.9 |
| MoveAllAxis | 10.0 | **1.5** | 3.4 | 38.3 | 12.6 |
| MoveWander | 14.7 | **1.6** | 5.6 | 35.9 | 9.5 |
| SendRPC | 5.4 | **5.1** | 6.2 | 29.8 | 7.3 |
| Static | 1.2 | **-1.9** | 1.4 | -0.7 | 2.8 |
| SpawnChurn | 10.9 | **1.6** | 4.0 | 2.3 | 3.0 |
| ClientInput | 2.6 | 0.8 | 3.3 | **-0.0** | 11.4 |
| SyncVars | 6.6 | **3.2** | 7.4 | 35.1 | 8.0 |

All metrics (per-client bandwidth, frame times, RTT, GC, memory, every connection count) are in the [interactive report](https://purrnet.github.io/unity-netcode-benchmark/), [workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/33753327418), [raw datapoints](docs/latest.json).
