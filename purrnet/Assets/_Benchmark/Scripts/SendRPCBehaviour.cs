using PurrNet;
using PurrNet.NetBench;
using TMPro;
using UnityEngine;

// Drives three benchmark tests depending on BenchRegistry.Mode:
//   Broadcast   (SendRPC)     server -> all clients, one observers RPC with one float per tick
//   ClientInput (ClientInput) every client -> server, one small RPC per tick
//   SyncVars    (SyncVars)    server changes one of four synced fields per tick
// Payloads are floats on purpose: some netcodes varint-pack integers by default and others do not,
// floats are 4 bytes everywhere, so the tests compare framing and batching rather than int encoding.
public class SendRPCBehaviour : NetworkBehaviour, ITick
{
    [SerializeField] TMP_Text _text;

    private SyncVar<float> _syncA = new SyncVar<float>(0f);
    private SyncVar<float> _syncB = new SyncVar<float>(0f);
    private SyncVar<float> _syncC = new SyncVar<float>(0f);
    private SyncVar<Vector3> _syncD = new SyncVar<Vector3>(Vector3.zero);

    private int _seq;
    private double _inputAcc;

    protected override void OnSpawned(bool asServer)
    {
        BenchRegistry.Spawned(4);
        _seq = Random.Range(0, 4);
    }

    protected override void OnDespawned(bool asServer)
    {
        BenchRegistry.RecordFinalState(_syncA.value, _syncB.value, _syncC.value, _syncD.value);
        BenchRegistry.Despawned(4);
    }

    private void Update()
    {
        if (isServer || !isClient) return;
        if (BenchRegistry.Mode != BenchMode.ClientInput) return;

        for (int ticks = BenchRegistry.AdvanceTicks(ref _inputAcc, Time.unscaledDeltaTime, BenchRegistry.TickInterval); ticks > 0; ticks--)
            ServerInput(Random.insideUnitSphere, Time.time);
    }

    public void OnTick(float delta)
    {
        if (!isServer || !BenchRegistry.WorkloadEnabled) return;
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
            case 0: _syncA.value = Random.Range(-10000f, 10000f); break;
            case 1: _syncB.value = Random.Range(0f, 100f); break;
            case 2: _syncC.value = Random.value; break;
            default: _syncD.value = Random.insideUnitSphere * 100f; break;
        }
    }

    [ObserversRpc]
    private void SomeData(float data)
    {
        if (!isServer) BenchRegistry.RpcsReceived++;
        _text.SetText(data.ToString());
    }

    [ServerRpc(requireOwnership: false)]
    private void ServerInput(Vector3 direction, float clientTime)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
