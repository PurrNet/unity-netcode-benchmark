using Fusion;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.FusionBenchmark
{
    public class SineMoveBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private SinRandomMoveWrapper _wrapper;

        public override void Spawned()
        {
            BenchRegistry.Spawned(2);
            if (!Object.HasStateAuthority) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);
        }

        public override void Despawned(NetworkRunner runner, bool hasState)
        {
            BenchRegistry.Despawned(2);
        }

        public override void FixedUpdateNetwork()
        {
            if (!Object.HasStateAuthority) return;

            if (!BenchRegistry.MovementEnabled) return;
            _wrapper.NetworkUpdate(transform, Runner.DeltaTime);
        }
    }
}
