using FishNet.Object;
using PurrNet.NetBench;
using TMPro;
using UnityEngine;

public class SendRPCBehaviour : NetworkBehaviour
{
    [SerializeField] TMP_Text _text;

    public override void OnStartNetwork()
    {
        BenchRegistry.Spawned(4);
        if (!IsServer) return;

        TimeManager.OnTick += OnTick;
    }

    public override void OnStopNetwork()
    {
        BenchRegistry.Despawned(4);
        if (TimeManager != null)
            TimeManager.OnTick -= OnTick;
    }

    private void OnTick()
    {
        var v = Random.Range(-10000, 10000);
        SomeData(v);
        _text.SetText(v.ToString());
    }

    [ObserversRpc]
    private void SomeData(int data)
    {
        _text.SetText(data.ToString());
    }
}
