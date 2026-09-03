using PurrNet.NetBench;
using TMPro;
using Unity.Netcode;
using UnityEngine;

public class SendRPCsBehaviour : NetworkBehaviour
{
    [SerializeField] TMP_Text _text;

    public override void OnNetworkSpawn()
    {
        BenchRegistry.Spawned(4);
        if (!IsServer) return;

        NetworkManager.NetworkTickSystem.Tick += OnTick;
    }

    public override void OnNetworkDespawn()
    {
        BenchRegistry.Despawned(4);
        if (IsServer && NetworkManager != null && NetworkManager.NetworkTickSystem != null)
            NetworkManager.NetworkTickSystem.Tick -= OnTick;
    }

    private void OnTick()
    {
        var v = Random.Range(-10000, 10000);
        SomeDataClientRpc(v);
        _text.SetText(v.ToString());
    }

    [ClientRpc]
    private void SomeDataClientRpc(int data)
    {
        _text.SetText(data.ToString());
    }
}
