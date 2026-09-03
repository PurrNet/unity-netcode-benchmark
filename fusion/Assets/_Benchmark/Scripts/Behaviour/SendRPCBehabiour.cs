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
            ServerInputRpc(Random.insideUnitSphere, Time.time);
    }

    public override void FixedUpdateNetwork()
    {
        if (!Object.HasStateAuthority) return;

        switch (BenchRegistry.Mode)
        {
            case BenchMode.Broadcast:
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
        _text.SetText(data.ToString());
    }

    [Rpc(sources: RpcSources.All, targets: RpcTargets.StateAuthority)]
    private void ServerInputRpc(Vector3 direction, float clientTime)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
