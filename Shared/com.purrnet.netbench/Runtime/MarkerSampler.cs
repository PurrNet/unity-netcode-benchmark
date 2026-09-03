using System.Collections.Generic;
using UnityEngine.Profiling;

namespace PurrNet.NetBench
{
    /// <summary>
    /// Reads profiler samplers matching the adapter's name prefixes (plus the whole-frame PlayerLoop
    /// sampler as a reference) via UnityEngine.Profiling.Recorder. Samplers only exist in a
    /// Development build; on a release build this no-ops and the CPU breakdown is omitted.
    /// </summary>
    public class MarkerSampler
    {
        private static readonly string[] AlwaysInclude = { "PlayerLoop" };

        private readonly List<string> _names = new List<string>();
        private readonly List<Recorder> _recorders = new List<Recorder>();
        private readonly List<long> _ns = new List<long>();
        private readonly List<long> _calls = new List<long>();
        private int _frames;
        private bool _available;

        public void Begin(string[] prefixes)
        {
            _names.Clear();
            _recorders.Clear();
            _ns.Clear();
            _calls.Clear();
            _frames = 0;

            // Release builds have no profiler; enabling it there only logs a warning per window.
            if (!UnityEngine.Debug.isDebugBuild)
            {
                _available = false;
                return;
            }

            Profiler.enabled = true;

            var all = new List<string>();
            Sampler.GetNames(all);

            for (int i = 0; i < all.Count; i++)
            {
                var n = all[i];
                if (!Matches(n, prefixes))
                    continue;

                var rec = Recorder.Get(n);
                if (rec == null || !rec.isValid)
                    continue;

                rec.enabled = true;
                _names.Add(n);
                _recorders.Add(rec);
                _ns.Add(0);
                _calls.Add(0);
            }

            _available = _recorders.Count > 0;
        }

        public void Sample()
        {
            if (!_available)
                return;

            _frames++;
            for (int i = 0; i < _recorders.Count; i++)
            {
                var rec = _recorders[i];
                _ns[i] += rec.elapsedNanoseconds;
                _calls[i] += rec.sampleBlockCount;
            }
        }

        public List<CpuMarker> End()
        {
            var list = new List<CpuMarker>();
            if (!_available)
                return list;

            for (int i = 0; i < _recorders.Count; i++)
                _recorders[i].enabled = false;

            int frames = _frames > 0 ? _frames : 1;
            for (int i = 0; i < _names.Count; i++)
            {
                if (_ns[i] <= 0 && _calls[i] == 0)
                    continue;

                double totalMs = _ns[i] / 1_000_000.0;
                list.Add(new CpuMarker
                {
                    name = _names[i],
                    totalMs = totalMs,
                    perFrameMs = totalMs / frames,
                    calls = _calls[i]
                });
            }

            list.Sort((a, b) => b.totalMs.CompareTo(a.totalMs));
            return list;
        }

        private static bool Matches(string name, string[] prefixes)
        {
            for (int i = 0; i < AlwaysInclude.Length; i++)
                if (name == AlwaysInclude[i])
                    return true;

            if (prefixes == null)
                return false;

            for (int i = 0; i < prefixes.Length; i++)
                if (name.StartsWith(prefixes[i]))
                    return true;

            return false;
        }
    }
}
