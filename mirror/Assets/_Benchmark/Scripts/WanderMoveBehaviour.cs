using Mirror;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.MirrorBenchmark
{
    public class WanderMoveBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private WanderMoveWrapper _wrapper;

        public override void OnStartServer()
        {
            BenchRegistry.Spawned(3);
            if (isClient) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);
            BenchmarkTickSystem.Tick += OnTick;
        }

        public override void OnStopServer()
        {
            BenchmarkTickSystem.Tick -= OnTick;
            BenchRegistry.Despawned(3);
        }
        public override void OnStartClient() => BenchRegistry.Spawned(3);
        public override void OnStopClient() => BenchRegistry.Despawned(3);

        private void OnTick(float delta)
        {
            if (isClient) return;

            if (!BenchRegistry.MovementEnabled) return;
            _wrapper.NetworkUpdate(transform, delta);
        }
    }
}
