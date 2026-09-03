using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace PurrNet.NetBench
{
    /// <summary>
    /// Headless benchmark orchestrator. Activates only when the player is started with -role; the
    /// scene's GUIGame (an <see cref="IBenchAdapter"/>) is then driven through the same scenario on
    /// every netcode:
    ///
    ///   server: listen -> wait for -count clients -> Idle window -> for each test: spawn objects,
    ///           warm up, measure, slack, despawn, cool down -> write -results JSON -> quit
    ///   client: connect (retrying) -> Idle window -> for each test seen via BenchRegistry:
    ///           warm up, measure (slightly shorter than the server window) -> wait for despawn
    ///           -> write -results JSON -> quit
    ///
    /// Tests (ids for -tests): 1 MoveY, 2 MoveAllAxis, 3 MoveWander, 4 SendRPC, 5 Static,
    /// 6 SpawnChurn, 7 ClientInput, 8 SyncVars. Tests 5-8 reuse the MoveY / SendRPC prefabs with
    /// movement disabled or a different BenchRegistry.Mode, so no extra assets are needed.
    ///
    /// Arguments:
    ///   -role server|client   -count N (server: expected clients)   -serverHost H  -port P
    ///   -session S -region R -photonAppId ID (relay netcodes)       -tests 1,2,3,4,5,6,7,8
    ///   -benchSeconds S (20)  -warmupSeconds S (3)  -idleSeconds S (5)  -benchObjects N (100)
    ///   -connectTimeout S (120)  -maxRunSeconds S (900)  -fps N (60)  -netIface NAME (auto)
    ///   -results PATH  -loadgen (client is load only, not a measured sample)
    /// </summary>
    public sealed class BenchRunner : MonoBehaviour
    {
        public static readonly string[] TestNames =
        {
            "Idle", "MoveY", "MoveAllAxis", "MoveWander", "SendRPC", "Static", "SpawnChurn", "ClientInput", "SyncVars"
        };

        private const int TestStatic = 5;
        private const int TestSpawnChurn = 6;
        private const int TestClientInput = 7;
        private const int TestSyncVars = 8;

        private const float SlackSeconds = 1.5f;
        private const float CooldownSeconds = 2f;
        private const float ClientRetrySeconds = 15f;
        private const float RttSampleInterval = 0.1f;
        private const float ChurnInterval = 0.05f;

        private static bool s_started;

        private IBenchAdapter _adapter;
        private RunResult _run;

        private bool _isServer;
        private bool _loadgen;
        private int _expectedClients;
        private int _objects;
        private int[] _tests;
        private float _benchSeconds;
        private float _warmupSeconds;
        private float _idleSeconds;
        private float _connectTimeout;
        private float _maxRunSeconds;
        private int _fps;
        private string _iface;
        private string _resultsPath;
        private BenchConnectOptions _opts;

        private float _startTime;
        private bool _finished;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Boot()
        {
            if (s_started || !CommandLine.TryGet("-role", out _))
                return;

            s_started = true;
            var go = new GameObject("NetBenchRunner");
            DontDestroyOnLoad(go);
            go.AddComponent<BenchRunner>();
        }

        private void Awake()
        {
            Application.runInBackground = true;
        }

        private void Start()
        {
            StartCoroutine(Run());
        }

        private void Update()
        {
            if (_finished || _run == null)
                return;

            if (Time.realtimeSinceStartup - _startTime > _maxRunSeconds)
            {
                Debug.LogError($"[NetBench] Exceeded -maxRunSeconds ({_maxRunSeconds}s); writing partial results.");
                _run.error = "timeout";
                Finish(2);
            }
        }

        private void LoadArgs()
        {
            var role = CommandLine.Get("-role", "server");
            _isServer = role.Equals("server", StringComparison.OrdinalIgnoreCase);
            _loadgen = CommandLine.Has("-loadgen");
            _expectedClients = CommandLine.GetInt("-count", 1);
            _objects = CommandLine.GetInt("-benchObjects", 100);
            _benchSeconds = CommandLine.GetFloat("-benchSeconds", 20f);
            _warmupSeconds = CommandLine.GetFloat("-warmupSeconds", 3f);
            _idleSeconds = CommandLine.GetFloat("-idleSeconds", 5f);
            _connectTimeout = CommandLine.GetFloat("-connectTimeout", 120f);
            _maxRunSeconds = CommandLine.GetFloat("-maxRunSeconds", 900f);
            _fps = CommandLine.GetInt("-fps", 60);
            _resultsPath = CommandLine.Get("-results");
            _iface = ResolveIface(CommandLine.Get("-netIface"));

            var tests = new List<int>();
            foreach (var part in CommandLine.Get("-tests", "1,2,3,4,5,6,7,8").Split(','))
            {
                if (int.TryParse(part.Trim(), out var t) && t > 0 && t < TestNames.Length)
                    tests.Add(t);
            }
            _tests = tests.ToArray();

            _opts = new BenchConnectOptions
            {
                host = CommandLine.Get("-serverHost", "127.0.0.1"),
                port = (ushort)CommandLine.GetInt("-port", 25565),
                maxClients = _expectedClients + 4,
                session = CommandLine.Get("-session", "netbench"),
                region = CommandLine.Get("-region", "us"),
                photonAppId = CommandLine.Get("-photonAppId", "")
            };
        }

        private static string ResolveIface(string requested)
        {
            var available = LoadSampler.ListIfaces();
            if (!string.IsNullOrEmpty(requested))
            {
                if (!available.Contains(requested))
                    Debug.LogWarning($"[NetBench] -netIface {requested} not found in /proc/net/dev (have: {string.Join(",", available)}); traffic counters will be 0.");
                return requested;
            }

            if (available.Contains("tailscale0"))
                return "tailscale0";

            foreach (var name in available)
            {
                if (name != "lo")
                    return name;
            }

            return "";
        }

        private static IBenchAdapter FindAdapter()
        {
            var behaviours = FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            for (int i = 0; i < behaviours.Length; i++)
            {
                if (behaviours[i] is IBenchAdapter adapter)
                    return adapter;
            }

            return null;
        }

        private static void ApplyMode(int test)
        {
            BenchRegistry.MovementEnabled = test != TestStatic && test != TestSpawnChurn;
            BenchRegistry.Mode = test == TestClientInput ? BenchMode.ClientInput
                : test == TestSyncVars ? BenchMode.SyncVars
                : BenchMode.Broadcast;
        }

        private static void ResetMode()
        {
            BenchRegistry.MovementEnabled = true;
            BenchRegistry.Mode = BenchMode.Broadcast;
        }

        private IEnumerator Run()
        {
            _startTime = Time.realtimeSinceStartup;
            LoadArgs();

            // Let the scene's GUIGame run Start()/Initialize() (it instantiates the NetworkManager).
            yield return null;
            yield return null;

            _adapter = FindAdapter();
            if (_adapter == null)
            {
                _run = new RunResult { error = "No IBenchAdapter (GUIGame) found in the scene" };
                Debug.LogError("[NetBench] " + _run.error);
                Finish(1);
                yield break;
            }

            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = _fps;

            _run = new RunResult
            {
                netcode = _adapter.NetcodeName,
                role = _isServer ? "server" : "client",
                measured = !_loadgen,
                loadgen = _loadgen,
                devBuild = Debug.isDebugBuild,
                unityVersion = Application.unityVersion,
                platform = Application.platform.ToString(),
                cpuModel = SystemInfo.processorType,
                cpuCount = SystemInfo.processorCount,
                targetFps = _fps,
                expectedClients = _expectedClients,
                benchObjects = _objects,
                benchSeconds = _benchSeconds,
                warmupSeconds = _warmupSeconds
            };

            Debug.Log($"[NetBench] netcode={_run.netcode} role={_run.role} loadgen={_loadgen} clients={_expectedClients} objects={_objects} " +
                      $"window={_benchSeconds}s warmup={_warmupSeconds}s tests={string.Join(",", _tests)} iface={_iface} fps={_fps} " +
                      $"host={_opts.host}:{_opts.port} session={_opts.session} region={_opts.region} cpu={_run.cpuModel} x{_run.cpuCount}");

            if (!Try(() => _adapter.Configure(_opts), "Configure"))
                yield break;

            if (_isServer)
                yield return ServerFlow();
            else
                yield return ClientFlow();
        }

        private IEnumerator ServerFlow()
        {
            if (!Try(() => _adapter.StartBenchServer(), "StartBenchServer"))
                yield break;

            float deadline = Time.realtimeSinceStartup + _connectTimeout;
            float nextLog = 0;
            int connected = 0;
            while (Time.realtimeSinceStartup < deadline)
            {
                connected = _adapter.ConnectedClientCount;
                if (connected >= _expectedClients)
                    break;

                if (Time.realtimeSinceStartup >= nextLog)
                {
                    Debug.Log($"[NetBench] Waiting for clients: {connected}/{_expectedClients} (listening={_adapter.IsServerListening})");
                    nextLog = Time.realtimeSinceStartup + 5f;
                }

                yield return new WaitForSecondsRealtime(0.5f);
            }

            connected = _adapter.ConnectedClientCount;
            _run.connectedAtStart = connected;
            if (connected == 0)
            {
                _run.error = "No clients connected before -connectTimeout";
                Debug.LogError("[NetBench] " + _run.error);
                Finish(1);
                yield break;
            }

            if (connected < _expectedClients)
                Debug.LogWarning($"[NetBench] Proceeding with {connected}/{_expectedClients} clients (connect timeout reached).");
            else
                Debug.Log($"[NetBench] All {connected} clients connected.");

            ReadTickRate();

            yield return Window(0, _idleSeconds);

            for (int i = 0; i < _tests.Length; i++)
            {
                int test = _tests[i];
                int slot = BenchRegistry.SlotOf(test);
                int count = test == TestClientInput ? 1 : _objects;
                int spawned = 0;

                ApplyMode(test);
                if (!Try(() => spawned = _adapter.SpawnTest(slot, count), $"SpawnTest({test})"))
                    yield break;

                Debug.Log($"[NetBench] Test {test} {TestNames[test]}: spawned {spawned} objects (mode={BenchRegistry.Mode}, movement={BenchRegistry.MovementEnabled}), warming up {_warmupSeconds}s");
                yield return new WaitForSecondsRealtime(_warmupSeconds);
                yield return Window(test, _benchSeconds);

                // Let late-starting client windows finish before the objects vanish.
                yield return new WaitForSecondsRealtime(SlackSeconds);
                Try(() => _adapter.DespawnAll(), "DespawnAll");
                ResetMode();
                yield return new WaitForSecondsRealtime(CooldownSeconds);
            }

            // Give clients a moment to observe the final despawn and flush their own results.
            yield return new WaitForSecondsRealtime(2f);
            Finish(0);
        }

        private IEnumerator ClientFlow()
        {
            if (!Try(() => _adapter.StartBenchClient(), "StartBenchClient"))
                yield break;

            float deadline = Time.realtimeSinceStartup + _connectTimeout;
            float nextRetry = Time.realtimeSinceStartup + ClientRetrySeconds;
            float nextLog = 0;
            while (!_adapter.IsClientConnected && Time.realtimeSinceStartup < deadline)
            {
                if (Time.realtimeSinceStartup >= nextRetry)
                {
                    Debug.Log("[NetBench] Not connected yet, restarting client connection attempt");
                    Try(() => _adapter.RestartBenchClient(), "RestartBenchClient");
                    nextRetry = Time.realtimeSinceStartup + ClientRetrySeconds;
                }

                if (Time.realtimeSinceStartup >= nextLog)
                {
                    Debug.Log("[NetBench] Connecting...");
                    nextLog = Time.realtimeSinceStartup + 5f;
                }

                yield return new WaitForSecondsRealtime(0.5f);
            }

            if (!_adapter.IsClientConnected)
            {
                _run.error = "Client never connected before -connectTimeout";
                Debug.LogError("[NetBench] " + _run.error);
                Finish(1);
                yield break;
            }

            Debug.Log("[NetBench] Connected.");
            _run.connectedAtStart = 1;
            ReadTickRate();

            if (BenchRegistry.ActiveSlot() == 0)
                yield return Window(0, _idleSeconds);

            var remaining = new List<int>(_tests);
            float clientWindow = Mathf.Max(1f, _benchSeconds - 1f);

            while (remaining.Count > 0)
            {
                if (!_adapter.IsClientConnected)
                {
                    Debug.LogWarning("[NetBench] Disconnected from server; ending run.");
                    _run.error = "disconnected";
                    break;
                }

                // The server runs tests in list order and despawns between them, so the first
                // remaining test that uses the active prefab slot is the one being run.
                int slot = BenchRegistry.ActiveSlot();
                int test = 0;
                if (slot != 0)
                {
                    for (int i = 0; i < remaining.Count; i++)
                    {
                        if (BenchRegistry.SlotOf(remaining[i]) == slot)
                        {
                            test = remaining[i];
                            break;
                        }
                    }
                }

                if (test == 0)
                {
                    yield return null;
                    continue;
                }

                ApplyMode(test);
                Debug.Log($"[NetBench] Test {test} {TestNames[test]} detected ({BenchRegistry.Count(slot)} objects, mode={BenchRegistry.Mode}), warming up {_warmupSeconds}s");
                yield return new WaitForSecondsRealtime(_warmupSeconds);
                yield return Window(test, clientWindow);
                remaining.Remove(test);

                while (BenchRegistry.Count(slot) > 0 && _adapter.IsClientConnected)
                    yield return new WaitForSecondsRealtime(0.1f);

                ResetMode();
            }

            Finish(_run.error == null ? 0 : 1);
        }

        private void ReadTickRate()
        {
            if (_run.tickRate > 0)
                return;

            // Adapters may not know the tick rate until the connection has settled; never let that abort a run.
            try
            {
                _run.tickRate = _adapter.TickRate;
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[NetBench] TickRate unavailable yet: {e.Message}");
            }
        }

        private void EnforceFrameCap()
        {
            // Several netcodes set their own cap when they start (Mirror: sendRate on headless servers,
            // FishNet: its TimeManager frame rate). Re-assert ours so CPU numbers stay comparable.
            QualitySettings.vSyncCount = 0;
            if (Application.targetFrameRate != _fps)
            {
                Debug.Log($"[NetBench] Frame cap was {Application.targetFrameRate}, re-applying {_fps}");
                Application.targetFrameRate = _fps;
            }
        }

        private IEnumerator Window(int test, float seconds)
        {
            var load = new LoadSampler();
            var markers = new MarkerSampler();
            var rtts = new List<double>();
            int slot = BenchRegistry.SlotOf(test);
            bool churn = _isServer && test == TestSpawnChurn;
            int churnCount = Mathf.Max(1, _objects / 50);

            EnforceFrameCap();
            ReadTickRate();
            load.Begin(_iface);
            markers.Begin(_adapter.ProfilerMarkerPrefixes);
            long inputs0 = BenchRegistry.ServerInputsReceived;

            double elapsed = 0;
            float nextRtt = 0;
            float churnAcc = 0;
            bool truncated = false;

            while (elapsed < seconds)
            {
                yield return null;
                float dt = Time.unscaledDeltaTime;
                elapsed += dt;

                load.SampleFrame();
                markers.Sample();

                if (!_isServer)
                {
                    nextRtt -= dt;
                    if (nextRtt <= 0)
                    {
                        double rtt = _adapter.ClientRttMs;
                        if (rtt > 0)
                            rtts.Add(rtt);
                        nextRtt = RttSampleInterval;
                    }
                }

                if (churn && BenchRegistry.Due(ref churnAcc, dt, ChurnInterval))
                {
                    _adapter.DespawnOldest(churnCount);
                    _adapter.SpawnTest(slot, churnCount);
                }

                if (test != 0 && BenchRegistry.Count(slot) == 0)
                {
                    truncated = true;
                    break;
                }

                if (test == 0 && BenchRegistry.ActiveSlot() != 0)
                {
                    truncated = true;
                    break;
                }
            }

            var stats = load.End();
            var cpuMarkers = markers.End();
            long inputs = BenchRegistry.ServerInputsReceived - inputs0;
            double wall = Math.Max(0.001, stats.wallSeconds);

            var result = new TestResult
            {
                test = test,
                name = TestNames[test],
                objects = BenchRegistry.Count(slot),
                windowSeconds = stats.wallSeconds,
                connections = _isServer ? _adapter.ConnectedClientCount : 1,
                truncated = truncated,
                cpuPercent = stats.cpuPercent,
                avgFrameMs = stats.avgFrameMs,
                minFrameMs = stats.minFrameMs,
                maxFrameMs = stats.maxFrameMs,
                p95FrameMs = stats.p95FrameMs,
                p99FrameMs = stats.p99FrameMs,
                avgFps = stats.avgFps,
                frameCount = stats.frameCount,
                gcCollections = stats.gcCollections,
                managedHeapBytes = stats.managedHeapBytes,
                peakRssBytes = stats.peakRssBytes,
                iface = _iface,
                inputsReceived = inputs,
                inputsPerSec = inputs / wall,
                cpuMarkers = cpuMarkers
            };

            if (stats.ifaceDelta.valid)
            {
                result.txBytes = stats.ifaceDelta.txBytes;
                result.rxBytes = stats.ifaceDelta.rxBytes;
                result.txBytesPerSec = stats.ifaceDelta.txBytes / wall;
                result.rxBytesPerSec = stats.ifaceDelta.rxBytes / wall;
                result.txPacketsPerSec = stats.ifaceDelta.txPackets / wall;
                result.rxPacketsPerSec = stats.ifaceDelta.rxPackets / wall;
            }

            if (rtts.Count > 0)
            {
                double sum = 0;
                for (int i = 0; i < rtts.Count; i++)
                    sum += rtts[i];
                rtts.Sort();
                result.rttSamples = rtts.Count;
                result.rttAvgMs = sum / rtts.Count;
                result.rttP50Ms = LoadSampler.Percentile(rtts, 0.50);
                result.rttP95Ms = LoadSampler.Percentile(rtts, 0.95);
                result.rttP99Ms = LoadSampler.Percentile(rtts, 0.99);
            }

            _run.tests.Add(result);

            Debug.Log($"[NetBench] {result.name}: objects={result.objects} conns={result.connections} window={result.windowSeconds:F1}s " +
                      $"cpu={result.cpuPercent:F1}% frame={result.avgFrameMs:F2}ms p95={result.p95FrameMs:F2}ms " +
                      $"tx={result.txBytesPerSec:F0}B/s rx={result.rxBytesPerSec:F0}B/s rttP50={result.rttP50Ms:F1}ms " +
                      $"inputs/s={result.inputsPerSec:F0} gc={result.gcCollections} rss={result.peakRssBytes / 1048576}MB truncated={truncated}");
        }

        private bool Try(Action action, string what)
        {
            try
            {
                action();
                return true;
            }
            catch (Exception e)
            {
                _run.error = $"{what} failed: {e.Message}";
                Debug.LogException(e);
                Finish(1);
                return false;
            }
        }

        private void WriteResults()
        {
            if (string.IsNullOrEmpty(_resultsPath) || _run == null)
                return;

            try
            {
                var dir = Path.GetDirectoryName(Path.GetFullPath(_resultsPath));
                if (!string.IsNullOrEmpty(dir))
                    Directory.CreateDirectory(dir);

                File.WriteAllText(_resultsPath, JsonUtility.ToJson(_run, true));
                Debug.Log($"[NetBench] Results written to {_resultsPath}");
            }
            catch (Exception e)
            {
                Debug.LogError($"[NetBench] Failed to write results: {e}");
            }
        }

        private void Finish(int exitCode)
        {
            if (_finished)
                return;

            _finished = true;
            ResetMode();
            WriteResults();

            try
            {
                _adapter?.ShutdownBench();
            }
            catch (Exception e)
            {
                Debug.LogException(e);
            }

            StartCoroutine(QuitSoon(exitCode));
        }

        private IEnumerator QuitSoon(int exitCode)
        {
            yield return new WaitForSecondsRealtime(1f);
            Debug.Log($"[NetBench] Exiting with code {exitCode}");
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit(exitCode);
#endif
        }
    }
}
