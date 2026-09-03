using Mirror;
using PurrNet.NetBench;
using TMPro;
using UnityEngine;

public class SendRPCBehaviour : NetworkBehaviour
{
    [SerializeField] TMP_Text _text;

    public override void OnStartServer() => BenchRegistry.Spawned(4);
    public override void OnStopServer() => BenchRegistry.Despawned(4);
    public override void OnStartClient() => BenchRegistry.Spawned(4);
    public override void OnStopClient() => BenchRegistry.Despawned(4);

    private void FixedUpdate()
    {
        if (isClient) return;
        OnTick();
    }

    private void OnTick()
    {
        var v = Random.Range(-10000, 10000);
        SomeData(v);
        _text.SetText(v.ToString());
    }

    [ClientRpc]
    private void SomeData(int data)
    {
        _text.SetText(data.ToString());
    }
}
