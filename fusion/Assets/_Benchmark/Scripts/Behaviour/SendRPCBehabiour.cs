using Fusion;
using PurrNet.NetBench;
using TMPro;
using UnityEngine;

public class SendRPCBehabiour : NetworkBehaviour
{
    [Networked] public Vector3 SpawnPos { get; set; }
    [Networked] public Quaternion SpawnRot { get; set; }

    [SerializeField] TMP_Text _text;

    public override void Spawned()
    {
        BenchRegistry.Spawned(4);

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

    public override void FixedUpdateNetwork()
    {
        if (!Object.HasStateAuthority) return;

        var v = Random.Range(-10000, 10000);
        SomeDataClientRpc(v);
    }

    [Rpc(sources: RpcSources.StateAuthority, targets: RpcTargets.All)]
    private void SomeDataClientRpc(int data)
    {
        _text.SetText(data.ToString());
    }
}
