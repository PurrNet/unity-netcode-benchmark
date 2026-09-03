using Fusion;
using PurrNet.NetBench;
using TMPro;
using UnityEngine;

// Drives three benchmark tests depending on BenchRegistry.Mode:
//   Broadcast   (SendRPC)     server -> all clients, one observers RPC with one int per tick
//   ClientInput (ClientInput) every client -> server, one small RPC per tick
//   SyncVars    (SyncVars)    server changes one of four networked properties per tick
public class SendRPCBehabiour : NetworkBehaviour
{
    [Networked] public Vector3 SpawnPos { get; set; }
    [Networked] public Quaternion SpawnRot { get; set; }

    [Networked] public int SyncA { get; set; }
    [Networked] public int SyncB { get; set; }
    [Networked] public float SyncC { get; set; }
    [Networked] public Vector3 SyncD { get; set; }

    [SerializeField] TMP_Text _text;

    private int _seq;
    private float _inputAcc;

    public override void Spawned()
    {
        BenchRegistry.Spawned(4);
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
        BenchRegistry.Despawned(4);
    }

    private void Update()
    {
        if (Runner == null || !Runner.IsRunning || Runner.IsServer || !Object || !Object.IsValid) return;
        if (BenchRegistry.Mode != BenchMode.ClientInput) return;

        if (BenchRegistry.Due(ref _inputAcc, Time.deltaTime, 1f / BenchRegistry.ClientInputHz))
            ServerInputRpc(Random.insideUnitSphere, ++_seq);
    }

    public override void FixedUpdateNetwork()
    {
        if (!Object.HasStateAuthority) return;

        switch (BenchRegistry.Mode)
        {
            case BenchMode.Broadcast:
                var v = Random.Range(-10000, 10000);
                SomeDataClientRpc(v);
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
            case 0: SyncA = Random.Range(-10000, 10000); break;
            case 1: SyncB = Random.Range(0, 100); break;
            case 2: SyncC = Random.value; break;
            default: SyncD = Random.insideUnitSphere * 100f; break;
        }
    }

    [Rpc(sources: RpcSources.StateAuthority, targets: RpcTargets.All)]
    private void SomeDataClientRpc(int data)
    {
        _text.SetText(data.ToString());
    }

    [Rpc(sources: RpcSources.All, targets: RpcTargets.StateAuthority)]
    private void ServerInputRpc(Vector3 direction, int tick)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
