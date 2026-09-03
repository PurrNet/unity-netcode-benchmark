using FishNet.Object;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.FishnetBenchmark
{
    public class SinMoveYBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private SinMoveYWrapper _wrapper;

        public override void OnStartNetwork()
        {
            BenchRegistry.Spawned(1);
            if (!IsServer) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);

            TimeManager.OnTick += OnTick;
        }

        public override void OnStopNetwork()
        {
            BenchRegistry.Despawned(1);
            if (TimeManager != null)
                TimeManager.OnTick -= OnTick;
        }

        private void OnTick()
        {
            _wrapper.NetworkUpdate(transform);
        }
    }
}
