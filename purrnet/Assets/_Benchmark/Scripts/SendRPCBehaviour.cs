using PurrNet;
using PurrNet.NetBench;
using PurrNet.Packing;
using TMPro;
using UnityEngine;

public class SendRPCBehaviour : NetworkBehaviour
{
    [SerializeField] TMP_Text _text;

    protected override void OnSpawned(bool asServer)
    {
        BenchRegistry.Spawned(4);
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

    private void OnTick()
    {
        var v = Random.Range(-10000, 10000);
        SomeData(v);
        _text.SetText(v.ToString());
    }

    // Fishnet packs their ints automatically, we don't agree with this move
    // so to match the behaviour we are doing the same manually
    [ObserversRpc]
    private void SomeData(PackedInt data)
    {
        _text.SetText(data.ToString());
    }
}
