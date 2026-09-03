using PurrNet;
using PurrNet.NetBench;
using PurrNet.Packing;
using TMPro;
using UnityEngine;

// Drives three benchmark tests depending on BenchRegistry.Mode:
//   Broadcast   (SendRPC)     server -> all clients, one observers RPC with one int per tick
//   ClientInput (ClientInput) every client -> server, one small RPC per tick
//   SyncVars    (SyncVars)    server changes one of four synced fields per tick
public class SendRPCBehaviour : NetworkBehaviour
{
    [SerializeField] TMP_Text _text;

    private SyncVar<int> _syncA = new SyncVar<int>(0);
    private SyncVar<int> _syncB = new SyncVar<int>(0);
    private SyncVar<float> _syncC = new SyncVar<float>(0f);
    private SyncVar<Vector3> _syncD = new SyncVar<Vector3>(Vector3.zero);

    private int _seq;
    private float _inputAcc;

    protected override void OnSpawned(bool asServer)
    {
        BenchRegistry.Spawned(4);
        _seq = Random.Range(0, 4);
    }

    protected override void OnDespawned(bool asServer)
    {
        BenchRegistry.Despawned(4);
    }

    private void FixedUpdate()
    {
        if (isClient) return;
        OnTick();
    }

    private void Update()
    {
        if (isServer || !isClient) return;
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
            case 0: _syncA.value = Random.Range(-10000, 10000); break;
            case 1: _syncB.value = Random.Range(0, 100); break;
            case 2: _syncC.value = Random.value; break;
            default: _syncD.value = Random.insideUnitSphere * 100f; break;
        }
    }

    // Fishnet packs their ints automatically, we don't agree with this move
    // so to match the behaviour we are doing the same manually
    [ObserversRpc]
    private void SomeData(PackedInt data)
    {
        _text.SetText(data.ToString());
    }

    [ServerRpc(requireOwnership: false)]
    private void ServerInput(Vector3 direction, int tick)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
