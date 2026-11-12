using System.Collections.Generic;
using PurrNet;
using PurrNet.Modules;
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
        private readonly List<NetworkIdentity> _identities = new List<NetworkIdentity>();
        private NetworkVisibilityRuleSet _visibilityRules;

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
            if (options.tickRate > 0)
                _networkManager.tickRate = options.tickRate;
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

            // Instantiate spawns and picks the observers right away, so the rule set goes on in the
            // pre-spawn callback rather than after the call.
            bool restrict = BenchRegistry.VisibleOneIn > 1;
            if (restrict)
                HierarchyV2.onPreSpawn += RestrictVisibility;

            try
            {
                for (int i = 0; i < count; i++)
                    _spawned.Add(Instantiate(prefab, Random.insideUnitSphere * 10, Quaternion.identity));
            }
            finally
            {
                if (restrict)
                    HierarchyV2.onPreSpawn -= RestrictVisibility;
            }

            return count;
        }

        public bool SupportsVisibility => true;

        public void RerollVisibility(int index)
        {
            if ((uint)index >= (uint)_spawned.Count || !_spawned[index]) return;
            var identity = _spawned[index].GetComponent<NetworkIdentity>();
            BenchRegistry.RerollVisibility((long)identity.objectId);
            identity.EvaluateVisibility();
        }

        // Every identity of the object gets the rule set: they are evaluated one by one.
        private void RestrictVisibility(GameObject go, bool isSceneObject)
        {
            if (!_visibilityRules)
            {
                _visibilityRules = ScriptableObject.CreateInstance<NetworkVisibilityRuleSet>();
                _visibilityRules.Setup(_networkManager);
                _visibilityRules.AddRule(_networkManager, new BenchVisibilityRule());
            }

            go.GetComponentsInChildren(true, _identities);
            for (int i = 0; i < _identities.Count; i++)
                _identities[i].SetVisibilityRules(_visibilityRules);
            _identities.Clear();
        }

        private sealed class BenchVisibilityRule : INetworkVisibilityRule
        {
            public int complexity => 0;

            public bool CanSee(PlayerID player, NetworkIdentity target)
            {
                return BenchRegistry.IsVisibleTo((long)target.GetRootIdentity().objectId, (long)player.id.value);
            }
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
