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
        /// <summary>Network tick rate to run at in Hz, or 0 to keep the project's configured rate.</summary>
        public int tickRate;
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

        /// <summary>Whether <see cref="SpawnTest"/> can hide objects per client (test Visibility). A netcode
        /// that cannot do it without changing how every other test replicates sits that test out.</summary>
        bool SupportsVisibility { get; }

        /// <summary>Server: spawn <paramref name="count"/> instances of the prefab in the given slot (1..4). Returns spawned count.
        /// While <see cref="BenchRegistry.VisibleOneIn"/> is above 1, each object is only replicated to the
        /// clients <see cref="BenchRegistry.IsVisibleTo"/> allows, through the netcode's own interest system.</summary>
        int SpawnTest(int slot, int count);
        /// <summary>Server (VisibilityChurn): give the <paramref name="index"/>-th object spawned by
        /// <see cref="SpawnTest"/> a new audience: <see cref="BenchRegistry.RerollVisibility"/> with the
        /// object's key, then the netcode's own re-evaluation of that one object for every client.</summary>
        void RerollVisibility(int index);
        /// <summary>Server: despawn the <paramref name="count"/> oldest objects spawned by <see cref="SpawnTest"/> (SpawnChurn).</summary>
        void DespawnOldest(int count);
        /// <summary>Server: despawn everything spawned by <see cref="SpawnTest"/>.</summary>
        void DespawnAll();

        void ShutdownBench();
    }
}
