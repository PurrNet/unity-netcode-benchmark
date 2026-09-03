using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Fusion;
using Fusion.Photon.Realtime;
using PurrNet.NetBench;
using StinkySteak.NetcodeBenchmark;
using UnityEngine;

namespace StinkySteak.FusionBenchmark
{
    public class GUIGame : BaseGUIGame, IBenchAdapter
    {
        // Static so a scene reload (if the scene manager ever does one) cannot orphan the live runner.
        private static NetworkRunner s_runner;

        private NetworkRunner _runner;
        private BenchConnectOptions _opts;
        private bool _starting;
        private readonly List<NetworkObject> _spawned = new List<NetworkObject>();

        protected override void Initialize()
        {
            base.Initialize();
            if (s_runner == null)
                s_runner = new GameObject("Runner").AddComponent<NetworkRunner>();
            _runner = s_runner;
        }

        protected override void StartClient()
        {
            print($"[GUIGame]: Starting client...");

            _runner.StartGame(new StartGameArgs()
            {
                GameMode = GameMode.Client,
                SceneManager = _runner.gameObject.AddComponent<NetworkSceneManagerDefault>(),
                Scene = SceneRef.FromIndex(0),
                SessionName = "my-session",
            });
        }

        protected override void StartServer()
        {
            print($"[GUIGame]: Starting server...");

            _runner.StartGame(new StartGameArgs()
            {
                GameMode = GameMode.Server,
                SceneManager = _runner.gameObject.AddComponent<NetworkSceneManagerDefault>(),
                Scene = SceneRef.FromIndex(0),
                SessionName = "my-session",
                AuthValues = new Photon.Realtime.AuthenticationValues { UserId = SystemInfo.deviceUniqueIdentifier + Path.GetDirectoryName(Directory.GetCurrentDirectory()) }
            });
        }
        protected override void StressTest(StressTestEssential stressTest)
        {
            for (int i = 0; i < stressTest.SpawnCount; i++)
            {
                _runner.Spawn(stressTest.Prefab, Random.insideUnitSphere * 10, Quaternion.identity, _runner.LocalPlayer);
            }
        }

        protected override void UpdateNetworkStats()
        {
            if (_runner == null) return;

            if (!_runner.IsRunning) return;

            if (_runner.IsServer)
            {
                _textLatency.SetText("Latency: 0ms (Server)");
                return;
            }

            float latency = (float)_runner.GetPlayerRtt(_runner.LocalPlayer) * 1000;

            _textLatency.SetText($"Latency: {latency}ms ({_runner.CurrentConnectionType})");
        }

        // ---- IBenchAdapter ----

        public string NetcodeName => "fusion";

        public int TickRate => _runner != null && _runner.IsRunning ? (int)_runner.TickRate : 0;

        public string[] ProfilerMarkerPrefixes => new[] { "Fusion", "NetworkRunner", "Simulation", "NetworkObject", "NetworkBehaviour" };

        public void Configure(BenchConnectOptions options)
        {
            _opts = options;
        }

        public void StartBenchServer() => _ = StartBench(GameMode.Server);

        public void StartBenchClient() => _ = StartBench(GameMode.Client);

        public void RestartBenchClient()
        {
            if (_starting)
                return;

            // A runner that failed/shut down cannot be restarted; make a fresh one.
            if (_runner != null)
                Destroy(_runner.gameObject);
            s_runner = new GameObject("Runner").AddComponent<NetworkRunner>();
            _runner = s_runner;
            _ = StartBench(GameMode.Client);
        }

        private async Task StartBench(GameMode mode)
        {
            _starting = true;
            try
            {
                var settings = new FusionAppSettings();
                PhotonAppSettings.Global.AppSettings.CopyTo(settings);
                if (!string.IsNullOrEmpty(_opts.region))
                    settings.FixedRegion = _opts.region;
                if (!string.IsNullOrEmpty(_opts.photonAppId))
                    settings.AppIdFusion = _opts.photonAppId;

                var args = new StartGameArgs
                {
                    GameMode = mode,
                    SceneManager = _runner.gameObject.AddComponent<NetworkSceneManagerDefault>(),
                    Scene = SceneRef.FromIndex(0),
                    SessionName = _opts.session,
                    PlayerCount = _opts.maxClients,
                    CustomPhotonAppSettings = settings
                };

                if (mode == GameMode.Server)
                    args.AuthValues = new Photon.Realtime.AuthenticationValues { UserId = SystemInfo.deviceUniqueIdentifier + Path.GetDirectoryName(Directory.GetCurrentDirectory()) };

                Debug.Log($"[GUIGame] StartGame {mode} session={_opts.session} region={settings.FixedRegion} players={_opts.maxClients}");
                var result = await _runner.StartGame(args);
                if (!result.Ok)
                    Debug.LogWarning($"[GUIGame] StartGame {mode} failed: {result.ShutdownReason} {result.ErrorMessage}");
            }
            finally
            {
                _starting = false;
            }
        }

        public bool IsServerListening => _runner != null && _runner.IsRunning && _runner.IsServer;

        public bool IsClientConnected => _runner != null && _runner.IsRunning && _runner.IsConnectedToServer;

        public int ConnectedClientCount => _runner != null && _runner.IsRunning ? _runner.ActivePlayers.Count() : 0;

        public double ClientRttMs => _runner != null && _runner.IsRunning ? _runner.GetPlayerRtt(_runner.LocalPlayer) * 1000.0 : 0;

        public int SpawnTest(int test, int count)
        {
            var prefab = GetTestPrefab(test);
            if (prefab == null) return 0;

            for (int i = 0; i < count; i++)
                _spawned.Add(_runner.Spawn(prefab, Random.insideUnitSphere * 10, Quaternion.identity, PlayerRef.None));

            return count;
        }

        public void DespawnAll()
        {
            for (int i = 0; i < _spawned.Count; i++)
            {
                if (_spawned[i] != null)
                    _runner.Despawn(_spawned[i]);
            }

            _spawned.Clear();
        }

        public void ShutdownBench()
        {
            if (_runner != null && _runner.IsRunning)
                _runner.Shutdown();
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
