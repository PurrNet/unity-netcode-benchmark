using PurrNet;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.MirrorBenchmark
{
    public class SineMoveRandomBehaviour : NetworkBehaviour, ITick
    {
        [SerializeField] private BehaviourConfig _config;
        private SinRandomMoveWrapper _wrapper;

        protected override void OnSpawned(bool asServer)
        {
            BenchRegistry.Spawned(2);
            if (!asServer) return;
            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);
        }

        protected override void OnDespawned(bool asServer)
        {
            BenchRegistry.Despawned(2);
        }

        public void OnTick(float delta)
        {
            if (isClient) return;
            _wrapper.NetworkUpdate(transform);
        }
    }
}
