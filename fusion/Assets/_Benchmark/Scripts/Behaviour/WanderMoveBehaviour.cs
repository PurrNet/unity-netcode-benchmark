using Fusion;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.FusionBenchmark
{
    public class WanderMoveBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private WanderMoveWrapper _wrapper;

        public override void Spawned()
        {
            BenchRegistry.Spawned(3);
            if (!Object.HasStateAuthority) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);
        }

        public override void Despawned(NetworkRunner runner, bool hasState)
        {
            BenchRegistry.Despawned(3);
        }

        public override void FixedUpdateNetwork()
        {
            if (!Object.HasStateAuthority) return;

            _wrapper.NetworkUpdate(transform);
        }
    }
}
