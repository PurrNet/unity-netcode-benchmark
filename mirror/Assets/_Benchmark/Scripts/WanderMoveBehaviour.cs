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
        }

        public override void OnStopServer() => BenchRegistry.Despawned(3);
        public override void OnStartClient() => BenchRegistry.Spawned(3);
        public override void OnStopClient() => BenchRegistry.Despawned(3);

        private void FixedUpdate()
        {
            if (isClient) return;

            _wrapper.NetworkUpdate(transform);
        }
    }
}
