using Mirror;
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

    [SyncVar] private float _syncA;
    [SyncVar] private float _syncB;
    [SyncVar] private float _syncC;
    [SyncVar] private Vector3 _syncD;

    private int _seq;
    private float _inputAcc;

    public override void OnStartServer()
    {
        BenchRegistry.Spawned(4);
        _seq = Random.Range(0, 4);
    }

    public override void OnStopServer() => BenchRegistry.Despawned(4);
    public override void OnStartClient() => BenchRegistry.Spawned(4);
    public override void OnStopClient() => BenchRegistry.Despawned(4);

    private void FixedUpdate()
    {
        if (isClient) return;
        OnTick();
    }

    private void Update()
    {
        if (!isClientOnly) return;
        if (BenchRegistry.Mode != BenchMode.ClientInput) return;

        if (BenchRegistry.Due(ref _inputAcc, Time.deltaTime, 1f / BenchRegistry.ClientInputHz))
            CmdServerInput(Random.insideUnitSphere, Time.time);
    }

    private void OnTick()
    {
        switch (BenchRegistry.Mode)
        {
            case BenchMode.Broadcast:
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
        switch (_seq++ & 3)
        {
            case 0: _syncA = Random.Range(-10000f, 10000f); break;
            case 1: _syncB = Random.Range(0f, 100f); break;
            case 2: _syncC = Random.value; break;
            default: _syncD = Random.insideUnitSphere * 100f; break;
        }
    }

    [ClientRpc]
    private void SomeData(float data)
    {
        _text.SetText(data.ToString());
    }

    [Command(requiresAuthority = false)]
    private void CmdServerInput(Vector3 direction, float clientTime)
    {
        BenchRegistry.ServerInputsReceived++;
    }
}
