using Fusion;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.FusionBenchmark
{
    public class SineMoveYBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private SinMoveYWrapper _wrapper;

        public override void Spawned()
        {
            BenchRegistry.Spawned(1);
            if (!Object.HasStateAuthority) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);
        }

        public override void Despawned(NetworkRunner runner, bool hasState)
        {
            BenchRegistry.Despawned(1);
        }

        public override void FixedUpdateNetwork()
        {
            if (!Object.HasStateAuthority) return;
            if (!BenchRegistry.MovementEnabled) return;

            _wrapper.NetworkUpdate(transform);
        }
    }
}
