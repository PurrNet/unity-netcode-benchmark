using Mirror;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.MirrorBenchmark
{
    public class SineMoveYBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private SinMoveYWrapper _wrapper;

        public override void OnStartServer()
        {
            BenchRegistry.Spawned(1);
            if (isClient) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);
        }

        public override void OnStopServer() => BenchRegistry.Despawned(1);
        public override void OnStartClient() => BenchRegistry.Spawned(1);
        public override void OnStopClient() => BenchRegistry.Despawned(1);

        private void FixedUpdate()
        {
            if (isClient) return;

            _wrapper.NetworkUpdate(transform);
        }
    }
}
