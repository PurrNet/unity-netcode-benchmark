using System;
using System.Collections.Generic;
using kcp2k;
using Mirror;
using PurrNet.NetBench;
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
            RegisterPrefabs(new StressTestEssential[] { _test_1, _test_2, _test_3 });
        }

        private void RegisterPrefabs(StressTestEssential[] stressTestEssential)
        {
            for (int i = 0; i < stressTestEssential.Length; i++)
            {
                _networkManager.spawnPrefabs.Add(stressTestEssential[i].Prefab);
            }
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
                GameObject go = Instantiate(stressTest.Prefab);
                go.transform.position = Random.insideUnitSphere * 10;
                NetworkServer.Spawn(go);
            }
        }

        protected override void UpdateNetworkStats()
        {
            if (_networkManager == null) return;

            if (!_networkManager.isNetworkActive) return;

            if (_networkManager.mode == NetworkManagerMode.ServerOnly)
            {
                _textLatency.SetText("Latency: 0ms (Server)");
                return;
            }

            _textLatency.SetText("Latency: {0}ms", (float)NetworkTime.rtt * 1_000);
        }

        // ---- IBenchAdapter ----

        public string NetcodeName => "mirror";

        public int TickRate => _networkManager != null ? _networkManager.sendRate : 0;

        public string[] ProfilerMarkerPrefixes => new[]
        {
            "Mirror", "NetworkServer", "NetworkClient", "NetworkLoop", "NetworkIdentity", "NetworkBehaviour", "Kcp", "kcp"
        };

        public void Configure(BenchConnectOptions options)
        {
            _networkManager.networkAddress = options.host;
            _networkManager.maxConnections = options.maxClients;
            if (_networkManager.transport is KcpTransport kcp)
                kcp.Port = options.port;
        }

        public void StartBenchServer() => _networkManager.StartServer();

        public void StartBenchClient() => _networkManager.StartClient();

        public void RestartBenchClient()
        {
            _networkManager.StopClient();
            _networkManager.StartClient();
        }

        public bool IsServerListening => NetworkServer.active;

        public bool IsClientConnected => NetworkClient.isConnected && NetworkClient.ready;

        public int ConnectedClientCount => NetworkServer.connections.Count;

        public double ClientRttMs => NetworkTime.rtt * 1000.0;

        public int SpawnTest(int test, int count)
        {
            var prefab = GetTestPrefab(test);
            if (prefab == null) return 0;

            for (int i = 0; i < count; i++)
            {
                GameObject go = Instantiate(prefab);
                go.transform.position = Random.insideUnitSphere * 10;
                NetworkServer.Spawn(go);
                _spawned.Add(go);
            }

            return count;
        }

        public void DespawnAll()
        {
            for (int i = 0; i < _spawned.Count; i++)
            {
                if (_spawned[i] != null)
                    NetworkServer.Destroy(_spawned[i]);
            }

            _spawned.Clear();
        }

        public void ShutdownBench()
        {
            if (_networkManager == null) return;
            if (NetworkServer.active) _networkManager.StopServer();
            if (NetworkClient.active) _networkManager.StopClient();
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
