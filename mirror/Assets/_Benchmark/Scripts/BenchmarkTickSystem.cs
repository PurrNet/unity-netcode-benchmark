using System;
using Mirror;
using PurrNet.NetBench;
using UnityEngine;

namespace StinkySteak.MirrorBenchmark
{
    /// <summary>Server workload clock for Mirror, which exposes a send rate but no simulation tick event.
    /// Runs before Mirror's late network send and leaves Unity's physics timestep unchanged.</summary>
    public sealed class BenchmarkTickSystem : MonoBehaviour
    {
        public static event Action<float> Tick;
        private double _accumulator;

        private void Update()
        {
            if (!NetworkServer.active)
            {
                _accumulator = 0;
                return;
            }

            double interval = 1.0 / NetworkManager.singleton.sendRate;
            int ticks = BenchRegistry.AdvanceTicks(ref _accumulator, Time.unscaledDeltaTime, interval);
            for (int i = 0; i < ticks; i++)
                Tick?.Invoke((float)interval);
        }

        private void OnDestroy() => Tick = null;
    }
}
