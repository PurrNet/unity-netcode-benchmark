using FishNet.Object;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.FishnetBenchmark
{
    public class WanderMoveBehaviour : NetworkBehaviour
    {
        [SerializeField] private BehaviourConfig _config;
        private WanderMoveWrapper _wrapper;

        public override void OnStartNetwork()
        {
            BenchRegistry.Spawned(3);
            if (!IsServer) return;

            _config.ApplyConfig(ref _wrapper);
            _wrapper.NetworkStart(transform);

            TimeManager.OnTick += OnTick;
        }

        public override void OnStopNetwork()
        {
            BenchRegistry.Despawned(3);
            if (TimeManager != null)
                TimeManager.OnTick -= OnTick;
        }

        private void OnTick()
        {
            if (!BenchRegistry.MovementEnabled) return;
            _wrapper.NetworkUpdate(transform, (float)TimeManager.TickDelta);
        }
    }
}
