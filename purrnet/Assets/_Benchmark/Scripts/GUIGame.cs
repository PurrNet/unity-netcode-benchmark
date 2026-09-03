using System.Collections.Generic;
using PurrNet;
using PurrNet.NetBench;
using PurrNet.Transports;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;
using Random = UnityEngine.Random;

namespace StinkySteak.MirrorBenchmark
{
    public class GUIGame : BaseGUIGame, IBenchAdapter
    {
        [SerializeField] private NetworkManager _networkManagerPrefab;
        private NetworkManager _networkManager;

        private readonly List<GameObject> _spawned = new List<GameObject>();

        protected override void Initialize()
        {
            base.Initialize();
            _networkManager = Instantiate(_networkManagerPrefab);
        }

        protected override void StartClient()
        {
            _networkManager.StartClient();
        }

        protected override void StartServer()
        {
            _networkManager.StartServer();
        }

        protected override void StressTest(StressTestEssential stressTest)
        {
            for (int i = 0; i < stressTest.SpawnCount; i++)
            {
                Instantiate(stressTest.Prefab,
                    Random.insideUnitSphere * 10,
                    Quaternion.identity);
            }
        }

        protected override void UpdateNetworkStats()
        {
            if (_networkManager == null || _networkManager.tickModule == null) return;

            _textLatency.SetText("Latency: {0}ms", (float)_networkManager.tickModule.rtt * 1_000);
        }

        // ---- IBenchAdapter ----

        public string NetcodeName => "purrnet";

        public int TickRate => _networkManager != null && _networkManager.tickModule != null ? _networkManager.tickModule.tickRate : 0;

        public string[] ProfilerMarkerPrefixes => new[]
        {
            "NetworkManager.", "NetworkTransform.", "NetworkIdentity.", "RPCModule.", "RPCBatch", "DeltaModule.", "PurrNet"
        };

        public void Configure(BenchConnectOptions options)
        {
            if (_networkManager.transport is UDPTransport udp)
            {
                udp.address = options.host;
                udp.serverPort = options.port;
                udp.maxConnections = options.maxClients;
            }
        }

        public void StartBenchServer() => _networkManager.StartServer();

        public void StartBenchClient() => _networkManager.StartClient();

        public void RestartBenchClient()
        {
            _networkManager.StopClient();
            _networkManager.StartClient();
        }

        public bool IsServerListening => _networkManager != null && _networkManager.serverState == ConnectionState.Connected;

        public bool IsClientConnected => _networkManager != null && _networkManager.clientState == ConnectionState.Connected;

        public int ConnectedClientCount => _networkManager != null ? _networkManager.playerCount : 0;

        public double ClientRttMs => _networkManager != null && _networkManager.tickModule != null ? _networkManager.tickModule.rtt * 1000.0 : 0;

        public int SpawnTest(int test, int count)
        {
            var prefab = GetTestPrefab(test);
            if (prefab == null) return 0;

            for (int i = 0; i < count; i++)
                _spawned.Add(Instantiate(prefab, Random.insideUnitSphere * 10, Quaternion.identity));

            return count;
        }

        public void DespawnOldest(int count)
        {
            int n = Mathf.Min(count, _spawned.Count);
            for (int i = 0; i < n; i++)
            {
                if (_spawned[i] != null)
                    Destroy(_spawned[i]);
            }

            _spawned.RemoveRange(0, n);
        }

        public void DespawnAll()
        {
            for (int i = 0; i < _spawned.Count; i++)
            {
                if (_spawned[i] != null)
                    Destroy(_spawned[i]);
            }

            _spawned.Clear();
        }

        public void ShutdownBench()
        {
            if (_networkManager == null) return;
            if (_networkManager.isServer) _networkManager.StopServer();
            if (_networkManager.isClient) _networkManager.StopClient();
        }

        private GameObject GetTestPrefab(int test)
        {
            switch (test)
            {
                case 1: return _test_1.Prefab;
                case 2: return _test_2.Prefab;
                case 3: return _test_3.Prefab;
                case 4: return _test_4.Prefab;
                default: return null;
            }
        }
    }
}
