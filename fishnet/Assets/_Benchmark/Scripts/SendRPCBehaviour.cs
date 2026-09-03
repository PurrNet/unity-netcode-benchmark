using FishNet.Object;
using FishNet.Object.Synchronizing;
using PurrNet.NetBench;
using TMPro;
using UnityEngine;

// Drives three benchmark tests depending on BenchRegistry.Mode:
//   Broadcast   (SendRPC)     server -> all clients, one observers RPC with one int per tick
//   ClientInput (ClientInput) every client -> server, one small RPC per tick
//   SyncVars    (SyncVars)    server changes one of four synced fields per tick
public class SendRPCBehaviour : NetworkBehaviour
{
    [SerializeField] TMP_Text _text;

    private readonly SyncVar<int> _syncA = new SyncVar<int>();
    private readonly SyncVar<int> _syncB = new SyncVar<int>();
    private readonly SyncVar<float> _syncC = new SyncVar<float>();
    private readonly SyncVar<Vector3> _syncD = new SyncVar<Vector3>();

    private int _seq;
    private float _inputAcc;

    public override void OnStartNetwork()
    {
        BenchRegistry.Spawned(4);
        _seq = Random.Range(0, 4);
        if (!IsServer) return;

        TimeManager.OnTick += OnTick;
    }

    public override void OnStopNetwork()
    {
        BenchRegistry.Despawned(4);
        if (TimeManager != null)
            TimeManager.OnTick -= OnTick;
    }

    private void Update()
    {
        if (IsServerInitialized || !IsClientInitialized) return;
        if (BenchRegistry.Mode != BenchMode.ClientInput) return;

        if (BenchRegistry.Due(ref _inputAcc, Time.deltaTime, 1f / BenchRegistry.ClientInputHz))
            ServerInput(Random.insideUnitSphere, ++_seq);
    }

    private void OnTick()
    {
        switch (BenchRegistry.Mode)
        {
            case BenchMode.Broadcast:
                var v = Random.Range(-10000, 10000);
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
        switch (_seq++ & 3)
        {
            case 0: _syncA.Value = Random.Range(-10000, 10000); break;
            case 1: _syncB.Value = Random.Range(0, 100); break;
            case 2: _syncC.Value = Random.value; break;
            default: _syncD.Value = Random.insideUnitSphere * 100f; break;
        }
    }

    [ObserversRpc]
    private void SomeData(int data)
    {
        _text.SetText(data.ToString());
    }

    [ServerRpc(RequireOwnership = false)]
    private void ServerInput(Vector3 direction, int tick)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
