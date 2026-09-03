using System.Collections.Generic;
using FishNet.Managing;
using FishNet.Transporting;
using FishNet.Transporting.Tugboat;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.FishnetBenchmark
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

        protected override void StressTest(StressTestEssential stressTest)
        {
            for (int i = 0; i < stressTest.SpawnCount; i++)
            {
                GameObject go = Instantiate(stressTest.Prefab);
                go.transform.position = Random.insideUnitSphere * 10;
                _networkManager.ServerManager.Spawn(go);
            }
        }

        protected override void StartClient()
        {
            _networkManager.ClientManager.StartConnection("127.0.0.1", 25565);
        }
        protected override void StartServer()
        {
            _networkManager.ServerManager.StartConnection(25565);
        }

        protected override void UpdateNetworkStats()
        {
            if (_networkManager == null) return;

            if (_networkManager.IsOffline) return;

            _textLatency.SetText("Latency: {0}ms", _networkManager.TimeManager.RoundTripTime);
        }

        // ---- IBenchAdapter ----

        public string NetcodeName => "fishnet";

        public int TickRate => _networkManager != null ? _networkManager.TimeManager.TickRate : 0;

        public string[] ProfilerMarkerPrefixes => new[]
        {
            "FishNet", "TimeManager", "ServerManager", "ClientManager", "TransportManager", "Tugboat", "NetworkObject", "NetworkBehaviour"
        };

        public void Configure(BenchConnectOptions options)
        {
            if (_networkManager.TransportManager.Transport is Tugboat tugboat)
            {
                tugboat.SetMaximumClients(options.maxClients);
                tugboat.SetClientAddress(options.host);
                tugboat.SetPort(options.port);
                tugboat.SetServerBindAddress("0.0.0.0", IPAddressType.IPv4);
            }
        }

        public void StartBenchServer() => _networkManager.ServerManager.StartConnection();

        public void StartBenchClient() => _networkManager.ClientManager.StartConnection();

        public void RestartBenchClient()
        {
            _networkManager.ClientManager.StopConnection();
            _networkManager.ClientManager.StartConnection();
        }

        public bool IsServerListening => _networkManager != null && _networkManager.ServerManager.Started;

        public bool IsClientConnected => _networkManager != null && _networkManager.ClientManager.Started;

        public int ConnectedClientCount => _networkManager != null ? _networkManager.ServerManager.Clients.Count : 0;

        public double ClientRttMs => _networkManager != null ? _networkManager.TimeManager.RoundTripTime : 0;

        public int SpawnTest(int test, int count)
        {
            var prefab = GetTestPrefab(test);
            if (prefab == null) return 0;

            for (int i = 0; i < count; i++)
            {
                GameObject go = Instantiate(prefab);
                go.transform.position = Random.insideUnitSphere * 10;
                _networkManager.ServerManager.Spawn(go);
                _spawned.Add(go);
            }

            return count;
        }

        public void DespawnAll()
        {
            for (int i = 0; i < _spawned.Count; i++)
            {
                if (_spawned[i] != null)
                    _networkManager.ServerManager.Despawn(_spawned[i]);
            }

            _spawned.Clear();
        }

        public void ShutdownBench()
        {
            if (_networkManager == null) return;
            _networkManager.ServerManager.StopConnection(true);
            _networkManager.ClientManager.StopConnection();
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
