using PurrNet.NetBench;
using TMPro;
using Unity.Netcode;
using UnityEngine;

// Drives three benchmark tests depending on BenchRegistry.Mode:
//   Broadcast   (SendRPC)     server -> all clients, one observers RPC with one float per tick
//   ClientInput (ClientInput) every client -> server, one small RPC per tick
//   SyncVars    (SyncVars)    server changes one of four synced fields per tick
// Payloads are floats on purpose: some netcodes varint-pack integers by default and others do not,
// floats are 4 bytes everywhere, so the tests compare framing and batching rather than int encoding.
public class SendRPCsBehaviour : NetworkBehaviour
{
    [SerializeField] TMP_Text _text;

    private readonly NetworkVariable<float> _syncA = new NetworkVariable<float>();
    private readonly NetworkVariable<float> _syncB = new NetworkVariable<float>();
    private readonly NetworkVariable<float> _syncC = new NetworkVariable<float>();
    private readonly NetworkVariable<Vector3> _syncD = new NetworkVariable<Vector3>();

    private int _seq;
    private float _inputAcc;

    public override void OnNetworkSpawn()
    {
        BenchRegistry.Spawned(4);
        _seq = Random.Range(0, 4);
        if (!IsServer) return;

        NetworkManager.NetworkTickSystem.Tick += OnTick;
    }

    public override void OnNetworkDespawn()
    {
        BenchRegistry.Despawned(4);
        if (IsServer && NetworkManager != null && NetworkManager.NetworkTickSystem != null)
            NetworkManager.NetworkTickSystem.Tick -= OnTick;
    }

    private void Update()
    {
        if (!IsSpawned || IsServer || !IsClient) return;
        if (BenchRegistry.Mode != BenchMode.ClientInput) return;

        if (BenchRegistry.Due(ref _inputAcc, Time.deltaTime, 1f / BenchRegistry.ClientInputHz))
            ServerInputServerRpc(Random.insideUnitSphere, Time.time);
    }

    private void OnTick()
    {
        switch (BenchRegistry.Mode)
        {
            case BenchMode.Broadcast:
                var v = Random.Range(-10000f, 10000f);
                SomeDataClientRpc(v);
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
            case 0: _syncA.Value = Random.Range(-10000f, 10000f); break;
            case 1: _syncB.Value = Random.Range(0f, 100f); break;
            case 2: _syncC.Value = Random.value; break;
            default: _syncD.Value = Random.insideUnitSphere * 100f; break;
        }
    }

    [ClientRpc]
    private void SomeDataClientRpc(float data)
    {
        _text.SetText(data.ToString());
    }

    [ServerRpc(RequireOwnership = false)]
    private void ServerInputServerRpc(Vector3 direction, float clientTime)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
