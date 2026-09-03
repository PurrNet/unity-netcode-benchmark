using System.Collections;
using System.Collections.Generic;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using Unity.Netcode;
using Unity.Netcode.Transports.UTP;
using UnityEngine;

namespace StinkySteak.NGOBenchmark
{
    public class GUIGame : BaseGUIGame, IBenchAdapter
    {
        [SerializeField] private NetworkManager _networkManagerPrefab;
        private NetworkManager _networkManager;

        private readonly List<NetworkObject> _spawned = new List<NetworkObject>();

        protected override void Initialize()
        {
            base.Initialize();

            _networkManager = Instantiate(_networkManagerPrefab);

            RegisterPrefabs(new StressTestEssential[] { _test_1, _test_2, _test_3 });
        }

        private void RegisterPrefabs(StressTestEssential[] stressTest)
        {
            for (int i = 0; i < stressTest.Length; i++)
            {
                _networkManager.AddNetworkPrefab(stressTest[i].Prefab);
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
                go.GetComponent<NetworkObject>().Spawn();
            }
        }

        protected override void UpdateNetworkStats()
        {
            if (_networkManager == null) return;

            if (!_networkManager.IsListening) return;

            if (_networkManager.IsServer)
            {
                _textLatency.SetText("Latency: 0ms (Server)");
                return;
            }

            ulong rtt = _networkManager.NetworkConfig.NetworkTransport.GetCurrentRtt(0);

            _textLatency.SetText("Latency: {0}ms", rtt);
        }

        // ---- IBenchAdapter ----

        public string NetcodeName => "ngo";

        public int TickRate => _networkManager != null ? (int)_networkManager.NetworkConfig.TickRate : 0;

        public string[] ProfilerMarkerPrefixes => new[]
        {
            "Netcode", "NetworkManager", "NetworkUpdateLoop", "NetworkBehaviourUpdater", "UnityTransport", "NetworkObject", "NGO"
        };

        public void Configure(BenchConnectOptions options)
        {
            if (_networkManager.NetworkConfig.NetworkTransport is UnityTransport utp)
                utp.SetConnectionData(options.host, options.port, "0.0.0.0");
        }

        public void StartBenchServer() => _networkManager.StartServer();

        public void StartBenchClient() => _networkManager.StartClient();

        public void RestartBenchClient()
        {
            StartCoroutine(RestartClientRoutine());
        }

        private IEnumerator RestartClientRoutine()
        {
            if (_networkManager.IsListening)
            {
                _networkManager.Shutdown();
                // Shutdown completes on the next NetworkManager update.
                yield return null;
                yield return null;
            }

            _networkManager.StartClient();
        }

        public bool IsServerListening => _networkManager != null && _networkManager.IsServer && _networkManager.IsListening;

        public bool IsClientConnected => _networkManager != null && _networkManager.IsConnectedClient;

        public int ConnectedClientCount => _networkManager != null && _networkManager.IsServer ? _networkManager.ConnectedClientsIds.Count : 0;

        public double ClientRttMs => _networkManager != null && _networkManager.IsConnectedClient
            ? _networkManager.NetworkConfig.NetworkTransport.GetCurrentRtt(NetworkManager.ServerClientId)
            : 0;

        public int SpawnTest(int test, int count)
        {
            var prefab = GetTestPrefab(test);
            if (prefab == null) return 0;

            for (int i = 0; i < count; i++)
            {
                GameObject go = Instantiate(prefab);
                go.transform.position = Random.insideUnitSphere * 10;
                var no = go.GetComponent<NetworkObject>();
                no.Spawn();
                _spawned.Add(no);
            }

            return count;
        }

        public void DespawnOldest(int count)
        {
            int n = Mathf.Min(count, _spawned.Count);
            for (int i = 0; i < n; i++)
            {
                if (_spawned[i] != null && _spawned[i].IsSpawned)
                    _spawned[i].Despawn(true);
            }

            _spawned.RemoveRange(0, n);
        }

        public void DespawnAll()
        {
            for (int i = 0; i < _spawned.Count; i++)
            {
                if (_spawned[i] != null && _spawned[i].IsSpawned)
                    _spawned[i].Despawn(true);
            }

            _spawned.Clear();
        }

        public void ShutdownBench()
        {
            if (_networkManager != null && _networkManager.IsListening)
                _networkManager.Shutdown();
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
