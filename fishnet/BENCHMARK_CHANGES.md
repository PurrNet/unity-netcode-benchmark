# FishNet project: changes made for the automated benchmark

Everything below is specific to the `fishnet/` project. The shared harness itself lives in
`Shared/com.purrnet.netbench` and is described in the root README.

## 1. Vendored FishNet change: Tugboat packet size (the only edit inside `Assets/FishNet`)

**File:** `Assets/FishNet/Runtime/Transporting/Transports/Tugboat/Tugboat.cs`

```diff
-        private const int MAXIMUM_UDP_MTU = 1350;
+        private const int MAXIMUM_UDP_MTU = 1200;
```

**Why.** The CI benchmark runs over a Tailscale overlay whose interface MTU is 1280 bytes.
LiteNetLib (which Tugboat embeds) opens its sockets with the don't-fragment flag set, so any UDP
datagram larger than the path MTU is rejected by the kernel with `EMSGSIZE`, and LiteNetLib treats
that error as "ignore". Tugboat passes the hard-coded `MAXIMUM_UDP_MTU` (1350) straight into
`NetManager.MtuOverride`, which also disables LiteNetLib's MTU discovery, so every packet that
LiteNetLib filled to 1350 bytes was silently dropped.

**Symptom in the first CI run (run 33739147252).** Idle, MoveY and MoveAllAxis worked (their
per-tick payload per client stayed under one packet), MoveWander and SendRPC sent almost nothing
(server downstream fell to ~1 KB/s while the server believed all 10 clients were still connected),
the SendRPC spawn batch never reached the clients because the reliable channel had stalled, and
the FishNet log contained no warning or error at all. The exact same Linux player worked with
10 clients on loopback under WSL, which isolated the problem to the network path.

**Why 1200.** It is the largest common value that is safe below 1280 with UDP/IP headers and
Tugboat's own framing, and it is what Mirror's KCP transport uses by default, so FishNet is not
put at a disadvantage relative to the other candidates. For reference, PurrNet uses the same
LiteNetLib but leaves MTU discovery on, so it settles at 1204 bytes on this path by itself; Unity
Transport (NGO) does not set don't-fragment and lets the IP layer fragment its 1400-byte packets.

**Maintenance.** There is no inspector setting for this in FishNet 4.7.3 (`_unreliableMTU` on
the Tugboat component is serialized but not used for the socket). Re-apply the one-line change
after every FishNet update, or the benchmark will silently regress for FishNet only. The compile
check and the SendRPC server downstream number are the quickest tell.

## 2. Embedded `com.stinkysteak.netcode-benchmarker-util` package

**Path:** `Packages/com.stinkysteak.netcode-benchmarker-util/`

The other four projects already embedded a modified copy of StinkySteak's benchmark utility
package that adds the fourth stress test slot (`_test_4`, SendRPC). The FishNet project still
pulled the upstream git version through its manifest, which has only three slots, so the SendRPC
prefab reference already present in `Benchmark.unity` was dangling and the adapter could not
compile against `_test_4`. The identical embedded copy from `purrnet/Packages` was copied in;
an embedded package takes precedence over the manifest entry, which was left untouched.

## 3. Manifest

`Packages/manifest.json` gained the shared harness:

```json
"com.purrnet.netbench": "file:../../Shared/com.purrnet.netbench"
```

`packages-lock.json` was updated by Unity accordingly.

## 4. `GUIGame` implements the harness adapter

**File:** `Assets/_Benchmark/Scripts/GUIGame.cs`

The manual (button) flow is unchanged. `GUIGame` additionally implements
`PurrNet.NetBench.IBenchAdapter`:

| Adapter member | FishNet call |
|---|---|
| `Configure` | On the `Tugboat` transport: `SetMaximumClients`, `SetClientAddress`, `SetPort`, `SetServerBindAddress("0.0.0.0", IPv4)` |
| `StartBenchServer` / `StartBenchClient` | `ServerManager.StartConnection()` / `ClientManager.StartConnection()` |
| `RestartBenchClient` | `ClientManager.StopConnection()` then `StartConnection()` |
| `IsServerListening` / `IsClientConnected` | `ServerManager.Started` / `ClientManager.Started` |
| `ConnectedClientCount` | `ServerManager.Clients.Count` |
| `ClientRttMs` | `TimeManager.RoundTripTime` |
| `TickRate` | `TimeManager.TickRate` |
| `SpawnTest` | `Instantiate` + `ServerManager.Spawn(go)`, instances kept in a list |
| `DespawnOldest` / `DespawnAll` | `ServerManager.Despawn(go)` on the oldest N / all tracked instances |
| `ShutdownBench` | `ServerManager.StopConnection(true)`, `ClientManager.StopConnection()` |

Profiler-marker prefixes used for the development-build CPU table: `FishNet`, `TimeManager`,
`ServerManager`, `ClientManager`, `TransportManager`, `Tugboat`, `NetworkObject`,
`NetworkBehaviour`.

## 5. Behaviour scripts

**Files:** `Assets/_Benchmark/Scripts/SinMoveYBehaviour.cs`, `SinRandomMoveBehaviour.cs`,
`WanderMoveBehaviour.cs`, `SendRPCBehaviour.cs`

- Each script reports itself to `BenchRegistry` in `OnStartNetwork` / `OnStopNetwork`
  (slots 1 to 4). Clients use these counts to detect which test the server is running; the
  server uses them as its object count.
- **Bug fix that was needed regardless of the benchmark:** the movement scripts subscribed to
  `TimeManager.OnTick` in `OnStartNetwork` and never unsubscribed. Once objects are despawned
  between tests the stale handlers would keep touching destroyed transforms every tick.
  `OnStopNetwork` now unsubscribes.
- `SinMoveYBehaviour` skips movement while `BenchRegistry.MovementEnabled` is false (Static and
  SpawnChurn tests reuse the MoveY prefab).
- `SendRPCBehaviour` drives three tests depending on `BenchRegistry.Mode`:
  - `Broadcast` (SendRPC): one `[ObserversRpc]` with one `float` per tick (the upstream benchmark
    sent an `int`; see below).
  - `ClientInput`: clients call `[ServerRpc(RequireOwnership = false)] ServerInput(Vector3, float)`
    at 20 Hz from `Update`; the server counts arrivals.
  - `SyncVars`: the server changes one of four `SyncVar<T>` fields (`float`, `float`, `float`,
    `Vector3`) per tick.
- **Why floats.** FishNet's writer varint-packs integers automatically (an `int` in
  [-10000, 10000] costs 2 to 3 bytes), while Mirror, NGO and Fusion write 4 bytes and PurrNet only
  packs when the field is declared `PackedInt`. The upstream PurrNet project had switched its RPC
  argument to `PackedInt` to match FishNet, but its SyncVars were still plain `int`. Floats are
  4 bytes on every netcode, so every project now sends floats and the RPC / SyncVar tests compare
  message framing and batching rather than integer encoding.

## 6. Runtime behaviour the harness overrides at run time (no file change)

- **Frame rate.** FishNet's `NetworkManager` applies its own frame-rate cap on start (500 fps by
  default; the benchmark's first CI run showed a constant 2 ms frame on every FishNet process).
  The harness re-applies its 60 fps cap at every measurement window so CPU % is comparable across
  netcodes. This is a runtime `Application.targetFrameRate` write only.
- **Headless auto-start.** FishNet's "start server on headless" only triggers under the
  dedicated-server define (`UNITY_SERVER`); the benchmark ships a regular Linux player, so client
  processes do not accidentally start a server. Nothing had to change for this, but it is the
  reason the player is not built with the Dedicated Server subtarget.

## 7. Not changed

- `Assets/DefaultPrefabObjects.asset` already lists all four benchmark prefabs.
- `Assets/_Benchmark/Prefab/*.prefab` and `Scenes/Benchmark.unity` are untouched; the NetworkTransform
  settings on the movement prefabs (client-authoritative flag, 1-tick interval, 0.001
  sensitivity) are the upstream benchmark's and identical across the three movement prefabs.
- Tick rate stays at the project's 20 Hz, matching the other four projects.
