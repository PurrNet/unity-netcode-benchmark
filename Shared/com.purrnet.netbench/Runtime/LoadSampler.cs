using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Unity.Profiling;
using UnityEngine;

namespace PurrNet.NetBench
{
    public struct IfaceCounters
    {
        public long rxBytes;
        public long rxPackets;
        public long txBytes;
        public long txPackets;
        public bool valid;
    }

    public struct LoadStats
    {
        public double cpuPercent;
        public double avgFrameMs;
        public double minFrameMs;
        public double maxFrameMs;
        public double p95FrameMs;
        public double p99FrameMs;
        public double avgFps;
        public int frameCount;
        public int gcCollections;
        /// <summary>Managed bytes allocated during the window on every thread, or -1 when the counter is unavailable.</summary>
        public long gcAllocBytes;
        public long managedHeapBytes;
        public long peakRssBytes;
        public double wallSeconds;
        public IfaceCounters ifaceDelta;
    }

    /// <summary>
    /// Process CPU time (all threads, from /proc/self/stat), main-thread frame times, GC pressure,
    /// peak RSS and on-wire interface counters (/proc/net/dev) over a measurement window. Linux only
    /// for CPU/RSS/iface; frame stats work everywhere.
    /// </summary>
    public class LoadSampler
    {
        private double _startCpuSeconds;
        private double _startWallSeconds;
        private int _startGcCollections;
        private ProfilerRecorder _gcAlloc;
        private long _gcAllocBytes;
        private IfaceCounters _startIface;
        private string _iface;
        private readonly List<float> _frameMs = new List<float>();

        public void Begin(string iface)
        {
            _iface = iface;
            _startCpuSeconds = ReadProcessCpuSeconds();
            _startWallSeconds = NowSeconds();
            _startGcCollections = GC.CollectionCount(0);
            // Bytes handed out by the managed allocator per frame; collection counts only say when the
            // collector ran, this says how much garbage was made, however the collections happen to fall.
            _gcAllocBytes = 0;
            _gcAlloc = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Allocated In Frame");
            _startIface = ReadIface(iface);
            _frameMs.Clear();
        }

        public void SampleFrame()
        {
            _frameMs.Add(Time.unscaledDeltaTime * 1000f);
            if (_gcAlloc.Valid)
                _gcAllocBytes += _gcAlloc.LastValue;
        }

        public LoadStats End()
        {
            double cpu = ReadProcessCpuSeconds() - _startCpuSeconds;
            double wall = NowSeconds() - _startWallSeconds;
            var endIface = ReadIface(_iface);
            _gcAlloc.Dispose();

            var stats = new LoadStats
            {
                cpuPercent = wall > 0 ? cpu / wall * 100.0 : 0,
                peakRssBytes = ReadPeakResidentBytes(),
                frameCount = _frameMs.Count,
                gcCollections = GC.CollectionCount(0) - _startGcCollections,
                gcAllocBytes = _gcAlloc.Valid ? _gcAllocBytes : -1,
                managedHeapBytes = GC.GetTotalMemory(false),
                wallSeconds = wall,
                ifaceDelta = new IfaceCounters
                {
                    valid = _startIface.valid && endIface.valid,
                    rxBytes = endIface.rxBytes - _startIface.rxBytes,
                    rxPackets = endIface.rxPackets - _startIface.rxPackets,
                    txBytes = endIface.txBytes - _startIface.txBytes,
                    txPackets = endIface.txPackets - _startIface.txPackets
                }
            };

            if (_frameMs.Count > 0)
            {
                double sum = 0;
                for (int i = 0; i < _frameMs.Count; i++)
                    sum += _frameMs[i];

                var sorted = new List<float>(_frameMs);
                sorted.Sort();

                stats.avgFrameMs = sum / _frameMs.Count;
                stats.minFrameMs = sorted[0];
                stats.maxFrameMs = sorted[sorted.Count - 1];
                stats.p95FrameMs = Percentile(sorted, 0.95);
                stats.p99FrameMs = Percentile(sorted, 0.99);
                stats.avgFps = stats.avgFrameMs > 0 ? 1000.0 / stats.avgFrameMs : 0;
            }

            return stats;
        }

        public static double Percentile(List<float> sorted, double p)
        {
            if (sorted.Count == 0)
                return 0;
            if (sorted.Count == 1)
                return sorted[0];

            double rank = p * (sorted.Count - 1);
            int lo = (int)Math.Floor(rank);
            int hi = (int)Math.Ceiling(rank);
            if (lo == hi)
                return sorted[lo];

            return sorted[lo] + (sorted[hi] - sorted[lo]) * (rank - lo);
        }

        public static double Percentile(List<double> sorted, double p)
        {
            if (sorted.Count == 0)
                return 0;
            if (sorted.Count == 1)
                return sorted[0];

            double rank = p * (sorted.Count - 1);
            int lo = (int)Math.Floor(rank);
            int hi = (int)Math.Ceiling(rank);
            if (lo == hi)
                return sorted[lo];

            return sorted[lo] + (sorted[hi] - sorted[lo]) * (rank - lo);
        }

        private static double NowSeconds() => DateTime.UtcNow.Ticks / (double)TimeSpan.TicksPerSecond;

        private static double ReadProcessCpuSeconds()
        {
            try
            {
                var stat = File.ReadAllText("/proc/self/stat");
                int close = stat.LastIndexOf(')');
                var rest = stat.Substring(close + 2).Split(' ');
                double utime = double.Parse(rest[11], CultureInfo.InvariantCulture);
                double stime = double.Parse(rest[12], CultureInfo.InvariantCulture);
                return (utime + stime) / 100.0;
            }
            catch
            {
                return 0;
            }
        }

        private static long ReadPeakResidentBytes()
        {
            try
            {
                foreach (var line in File.ReadAllLines("/proc/self/status"))
                {
                    if (!line.StartsWith("VmHWM:"))
                        continue;
                    var parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                    return long.Parse(parts[1], CultureInfo.InvariantCulture) * 1024L;
                }
            }
            catch
            {
                // ignored
            }

            return 0;
        }

        /// <summary>Reads cumulative counters for one interface from /proc/net/dev.</summary>
        public static IfaceCounters ReadIface(string iface)
        {
            var result = new IfaceCounters();
            if (string.IsNullOrEmpty(iface))
                return result;

            try
            {
                foreach (var raw in File.ReadAllLines("/proc/net/dev"))
                {
                    int colon = raw.IndexOf(':');
                    if (colon < 0)
                        continue;
                    if (raw.Substring(0, colon).Trim() != iface)
                        continue;

                    var f = raw.Substring(colon + 1).Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                    if (f.Length < 10)
                        return result;

                    result.rxBytes = long.Parse(f[0], CultureInfo.InvariantCulture);
                    result.rxPackets = long.Parse(f[1], CultureInfo.InvariantCulture);
                    result.txBytes = long.Parse(f[8], CultureInfo.InvariantCulture);
                    result.txPackets = long.Parse(f[9], CultureInfo.InvariantCulture);
                    result.valid = true;
                    return result;
                }
            }
            catch
            {
                // ignored
            }

            return result;
        }

        /// <summary>Lists interface names from /proc/net/dev (empty on non-Linux).</summary>
        public static List<string> ListIfaces()
        {
            var list = new List<string>();
            try
            {
                foreach (var raw in File.ReadAllLines("/proc/net/dev"))
                {
                    int colon = raw.IndexOf(':');
                    if (colon > 0)
                        list.Add(raw.Substring(0, colon).Trim());
                }
            }
            catch
            {
                // ignored
            }

            return list;
        }
    }
}
