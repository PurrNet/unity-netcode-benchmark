using FishNet.Object;
using FishNet.Object.Synchronizing;
using PurrNet.NetBench;
using TMPro;
using UnityEngine;

// Drives three benchmark tests depending on BenchRegistry.Mode:
//   Broadcast   (SendRPC)     server -> all clients, one observers RPC with one float per tick
//   ClientInput (ClientInput) every client -> server, one small RPC per tick
//   SyncVars    (SyncVars)    server changes one of four synced fields per tick
// Payloads are floats on purpose: some netcodes varint-pack integers by default and others do not,
// floats are 4 bytes everywhere, so the tests compare framing and batching rather than int encoding.
public class SendRPCBehaviour : NetworkBehaviour
{
    [SerializeField] TMP_Text _text;

    private readonly SyncVar<float> _syncA = new SyncVar<float>();
    private readonly SyncVar<float> _syncB = new SyncVar<float>();
    private readonly SyncVar<float> _syncC = new SyncVar<float>();
    private readonly SyncVar<Vector3> _syncD = new SyncVar<Vector3>();

    private int _seq;
    private double _inputAcc;

    public override void OnStartNetwork()
    {
        BenchRegistry.Spawned(4);
        _seq = Random.Range(0, 4);
        if (!IsServer) return;

        TimeManager.OnTick += OnTick;
    }

    public override void OnStopNetwork()
    {
        BenchRegistry.RecordFinalState(_syncA.Value, _syncB.Value, _syncC.Value, _syncD.Value);
        BenchRegistry.Despawned(4);
        if (TimeManager != null)
            TimeManager.OnTick -= OnTick;
    }

    private void Update()
    {
        if (IsServerInitialized || !IsClientInitialized) return;
        if (BenchRegistry.Mode != BenchMode.ClientInput) return;

        for (int ticks = BenchRegistry.AdvanceTicks(ref _inputAcc, Time.unscaledDeltaTime, BenchRegistry.TickInterval); ticks > 0; ticks--)
            ServerInput(Random.insideUnitSphere, Time.time);
    }

    private void OnTick()
    {
        if (!BenchRegistry.WorkloadEnabled) return;
        switch (BenchRegistry.Mode)
        {
            case BenchMode.Broadcast:
                BenchRegistry.RpcsSent++;
                var v = Random.Range(-10000f, 10000f);
                SomeData(v);
                _text.SetText(v.ToString());
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
            case 0: _syncA.Value = Random.Range(-10000f, 10000f); break;
            case 1: _syncB.Value = Random.Range(0f, 100f); break;
            case 2: _syncC.Value = Random.value; break;
            default: _syncD.Value = Random.insideUnitSphere * 100f; break;
        }
    }

    [ObserversRpc]
    private void SomeData(float data)
    {
        if (!IsServerInitialized) BenchRegistry.RpcsReceived++;
        _text.SetText(data.ToString());
    }

    [ServerRpc(RequireOwnership = false)]
    private void ServerInput(Vector3 direction, float clientTime)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
