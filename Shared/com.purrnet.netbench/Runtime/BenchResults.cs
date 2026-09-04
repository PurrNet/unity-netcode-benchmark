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
        /// <summary>Managed bytes allocated during the window (all threads); -1 when the profiler counter is unavailable.</summary>
        public long gcAllocBytes;
        public double gcAllocBytesPerSec;
        /// <summary>True when gcAllocBytes is heap growth between frames (release players) rather than the profiler counter.</summary>
        public bool gcAllocEstimated;
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

        // Server: client input RPCs received during the window (ClientInput test).
        public long inputsReceived;
        public double inputsPerSec;

        // Rate counters cover the measurement window; totals cover spawn through final despawn.
        public double rpcsSentPerSec;
        public double rpcsReceivedPerSec;
        public double syncMutationsPerSec;
        // Client-visible SyncVars sampled once per LateUpdate; Vector3 counts as one field.
        // Silence is time since the last locally observed change, NOT time since server mutation.
        public bool syncObservationAvailable;
        public long syncObservedChanges;
        public double syncObservedChangesPerSec;
        public long syncFieldSamples;
        public double syncSilenceAvgMs;
        public double syncSilenceMaxMs;
        public long rpcsSent;
        public long rpcsReceived;
        public long syncMutations;
        public bool deliveryComplete;
        public int finalStateObjects;
        public string finalStateHash;

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
        /// <summary>Tick rate asked for on the command line (0 = project default); tickRate is what the netcode reported.</summary>
        public int requestedTickRate;
        public int targetFps;
        public int expectedClients;
        public int connectedAtStart;
        public int benchObjects;
        public double benchSeconds;
        public double warmupSeconds;
        public string error;
        /// <summary>False while the run is in progress; the file is rewritten after every test so a crash keeps what finished.</summary>
        public bool completed;
        public List<TestResult> tests = new List<TestResult>();
    }
}
