using Fusion;
using PurrNet.NetBench;
using TMPro;
using UnityEngine;

// Drives three benchmark tests depending on BenchRegistry.Mode:
//   Broadcast   (SendRPC)     server -> all clients, one observers RPC with one float per tick
//   ClientInput (ClientInput) every client -> server, one small RPC per tick
//   SyncVars    (SyncVars)    server changes one of four networked properties per tick
// Payloads are floats on purpose: some netcodes varint-pack integers by default and others do not,
// floats are 4 bytes everywhere, so the tests compare framing and batching rather than int encoding.
public class SendRPCBehabiour : NetworkBehaviour
{
    [Networked] public Vector3 SpawnPos { get; set; }
    [Networked] public Quaternion SpawnRot { get; set; }

    [Networked] public float SyncA { get; set; }
    [Networked] public float SyncB { get; set; }
    [Networked] public float SyncC { get; set; }
    [Networked] public Vector3 SyncD { get; set; }

    [SerializeField] TMP_Text _text;

    private int _seq;
    private double _inputAcc;
    private SyncStateObserver _syncObserver;

    public override void Spawned()
    {
        BenchRegistry.Spawned(4);
        _syncObserver = default;
        _seq = Random.Range(0, 4);

        // apply on clients
        if (!Runner.IsServer)
        {
            transform.SetPositionAndRotation(SpawnPos, SpawnRot);
        }
        else
        {
            SpawnPos = transform.position;
            SpawnRot = transform.rotation;
        }
    }

    public override void Despawned(NetworkRunner runner, bool hasState)
    {
        if (hasState) BenchRegistry.RecordFinalState(SyncA, SyncB, SyncC, SyncD);
        BenchRegistry.Despawned(4);
    }

    // Identical client observation phase across all five netcodes; no extra network fields.
    private void LateUpdate()
    {
        if (Runner == null || !Runner.IsRunning || Runner.IsServer || !Object || !Object.IsValid) return;
        if (BenchRegistry.Mode != BenchMode.SyncVars) return;
        _syncObserver.Observe(SyncA, SyncB, SyncC, SyncD, Time.unscaledTimeAsDouble);
    }

    private void Update()
    {
        if (Runner == null || !Runner.IsRunning || Runner.IsServer || !Object || !Object.IsValid) return;
        if (BenchRegistry.Mode != BenchMode.ClientInput) return;

        for (int ticks = BenchRegistry.AdvanceTicks(ref _inputAcc, Time.unscaledDeltaTime, BenchRegistry.TickInterval); ticks > 0; ticks--)
            ServerInputRpc(Random.insideUnitSphere, Time.time);
    }

    public override void FixedUpdateNetwork()
    {
        if (!Object.HasStateAuthority || !BenchRegistry.WorkloadEnabled) return;

        switch (BenchRegistry.Mode)
        {
            case BenchMode.Broadcast:
                BenchRegistry.RpcsSent++;
                var v = Random.Range(-10000f, 10000f);
                SomeDataClientRpc(v);
                break;
            case BenchMode.SyncVars:
                MutateSyncVar();
                break;
        }
    }

    private void MutateSyncVar()
    {
        BenchRegistry.SyncMutations++;
        switch (_seq++ & 3)
        {
            case 0: SyncA = Random.Range(-10000f, 10000f); break;
            case 1: SyncB = Random.Range(0f, 100f); break;
            case 2: SyncC = Random.value; break;
            default: SyncD = Random.insideUnitSphere * 100f; break;
        }
    }

    [Rpc(sources: RpcSources.StateAuthority, targets: RpcTargets.All)]
    private void SomeDataClientRpc(float data)
    {
        if (!Runner.IsServer) BenchRegistry.RpcsReceived++;
        _text.SetText(data.ToString());
    }

    [Rpc(sources: RpcSources.All, targets: RpcTargets.StateAuthority)]
    private void ServerInputRpc(Vector3 direction, float clientTime)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
