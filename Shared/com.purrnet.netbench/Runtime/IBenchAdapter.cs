namespace PurrNet.NetBench
{
    public struct BenchConnectOptions
    {
        /// <summary>Server address for direct-connect netcodes (ignored by relay-based ones).</summary>
        public string host;
        public ushort port;
        /// <summary>Upper bound on simultaneous clients the server should accept.</summary>
        public int maxClients;
        /// <summary>Session/room name for relay-based netcodes (Fusion).</summary>
        public string session;
        /// <summary>Fixed cloud region for relay-based netcodes.</summary>
        public string region;
        /// <summary>Optional app id override for relay-based netcodes (empty = project default).</summary>
        public string photonAppId;
    }

    /// <summary>
    /// Implemented by each netcode project's GUIGame so <see cref="BenchRunner"/> can drive the
    /// same scenario across netcodes. Members must tolerate "not started yet" states.
    /// </summary>
    public interface IBenchAdapter
    {
        string NetcodeName { get; }
        /// <summary>Network tick rate in Hz, or 0 if unknown until started.</summary>
        int TickRate { get; }
        /// <summary>Profiler sampler name prefixes to attribute CPU time to (Development builds only).</summary>
        string[] ProfilerMarkerPrefixes { get; }

        void Configure(BenchConnectOptions options);

        void StartBenchServer();
        void StartBenchClient();
        /// <summary>Called periodically while a client has not connected yet; should tear down and retry.</summary>
        void RestartBenchClient();

        bool IsServerListening { get; }
        bool IsClientConnected { get; }
        /// <summary>Server-side connected client count.</summary>
        int ConnectedClientCount { get; }
        /// <summary>Client-side round-trip time estimate in milliseconds (0 if unknown).</summary>
        double ClientRttMs { get; }

        /// <summary>Server: spawn <paramref name="count"/> instances of the given test's prefab. Returns spawned count.</summary>
        int SpawnTest(int test, int count);
        /// <summary>Server: despawn everything spawned by <see cref="SpawnTest"/>.</summary>
        void DespawnAll();

        void ShutdownBench();
    }
}
