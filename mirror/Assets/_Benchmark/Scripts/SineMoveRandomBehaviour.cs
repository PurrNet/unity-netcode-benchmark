using Mirror;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.MirrorBenchmark
{
    public class SineMoveRandomBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private SinRandomMoveWrapper _wrapper;

        public override void OnStartServer()
        {
            BenchRegistry.Spawned(2);
            if (isClient) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);
        }

        public override void OnStopServer() => BenchRegistry.Despawned(2);
        public override void OnStartClient() => BenchRegistry.Spawned(2);
        public override void OnStopClient() => BenchRegistry.Despawned(2);

        private void FixedUpdate()
        {
            if (isClient) return;

            _wrapper.NetworkUpdate(transform);
        }
    }
}
