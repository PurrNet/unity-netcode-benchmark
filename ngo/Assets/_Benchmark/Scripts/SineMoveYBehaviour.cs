using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using Unity.Netcode;
using UnityEngine;

namespace StinkySteak.NGOBenchmark
{
    public class SineMoveYBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private SinMoveYWrapper _wrapper;

        public override void OnNetworkSpawn()
        {
            BenchRegistry.Spawned(1);
            if (!IsServer) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);

            NetworkManager.NetworkTickSystem.Tick += OnTick;
        }

        public override void OnNetworkDespawn()
        {
            BenchRegistry.Despawned(1);
            if (IsServer && NetworkManager != null && NetworkManager.NetworkTickSystem != null)
                NetworkManager.NetworkTickSystem.Tick -= OnTick;
        }

        private void OnTick()
        {
            if (!IsServer) return;
            if (!BenchRegistry.MovementEnabled) return;

            _wrapper.NetworkUpdate(transform, 1f / NetworkManager.NetworkConfig.TickRate);
        }
    }
}
