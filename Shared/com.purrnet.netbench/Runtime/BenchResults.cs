using System;
using System.Collections.Generic;

namespace PurrNet.NetBench
{
    [Serializable]
    public class CpuMarker
    {
        public string name;
        public double totalMs;
        public double perFrameMs;
        public long calls;
    }

    [Serializable]
    public class TestResult
    {
        public int test;
        public string name;
        public int objects;
        public double windowSeconds;
        public int connections;
        public bool truncated;

        // Process-wide CPU (all threads) over the window, percent of one core.
        public double cpuPercent;
        public double avgFrameMs;
        public double minFrameMs;
        public double maxFrameMs;
        public double p95FrameMs;
        public double p99FrameMs;
        public double avgFps;
        public int frameCount;
        public int gcCollections;
        public long managedHeapBytes;
        public long peakRssBytes;

        // On-wire traffic on the selected network interface (UDP/IP headers, ACKs, everything included).
        // Server: tx = downstream to all clients, rx = upstream from all clients.
        // Client: rx = this client's downstream, tx = its upstream.
        public string iface;
        public long txBytes;
        public long rxBytes;
        public double txBytesPerSec;
        public double rxBytesPerSec;
        public double txPacketsPerSec;
        public double rxPacketsPerSec;

        public int rttSamples;
        public double rttAvgMs;
        public double rttP50Ms;
        public double rttP95Ms;
        public double rttP99Ms;

        public List<CpuMarker> cpuMarkers = new List<CpuMarker>();
    }

    [Serializable]
    public class RunResult
    {
        public string netcode;
        public string role;
        public bool measured;
        public bool loadgen;
        public bool devBuild;
        public string unityVersion;
        public string platform;
        public string cpuModel;
        public int cpuCount;
        public int tickRate;
        public int targetFps;
        public int expectedClients;
        public int connectedAtStart;
        public int benchObjects;
        public double benchSeconds;
        public double warmupSeconds;
        public string error;
        public List<TestResult> tests = new List<TestResult>();
    }
}
