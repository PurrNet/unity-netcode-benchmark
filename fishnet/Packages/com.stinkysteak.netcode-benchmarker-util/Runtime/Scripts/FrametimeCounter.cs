using UnityEngine;

namespace StinkySteak.NetcodeBenchmark
{
    public class FrametimeCounter : MonoBehaviour
    {
        private int _size = 5000;
        private float[] _frametimes;
        private int _indexer;

        private void Start()
        {
            _frametimes = new float[_size];
        }

        private void Update()
        {
            if (_indexer >= _size)
                _indexer = 0;

            _frametimes[_indexer] = Time.deltaTime;
            _indexer++;
        }
        public float GetAvgFrameTime()
        {
            float totalFrameTime = 0;

            foreach (var frametime in _frametimes)
            {
                totalFrameTime += frametime;
            }

            float secondsToMs = 1_000;
            float avgFrameTime = totalFrameTime / _size * secondsToMs;

            return avgFrameTime;
        }

        [ContextMenu("Print FrameTime")]
        private void PrintFrameTime()
        {
            print($"avgFrameTime: {GetAvgFrameTime()}ms");
        }
    }
}