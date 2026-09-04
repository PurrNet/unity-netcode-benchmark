using PurrNet;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.MirrorBenchmark
{
    public class SineMoveYBehaviour : NetworkBehaviour, ITick
    {
        [SerializeField] private BehaviourConfig _config;
        private SinMoveYWrapper _wrapper;

        protected override void OnSpawned(bool asServer)
        {
            BenchRegistry.Spawned(1);
            if (!asServer) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);
        }

        protected override void OnDespawned(bool asServer)
        {
            BenchRegistry.Despawned(1);
        }

        public void OnTick(float delta)
        {
            if (isClient) return;
            if (!BenchRegistry.MovementEnabled) return;

            _wrapper.NetworkUpdate(transform, delta);
        }
    }
}
