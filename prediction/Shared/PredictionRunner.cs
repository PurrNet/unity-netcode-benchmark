using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Text;
using PurrNet.NetBench;
using UnityEngine;
using UnityEngine.Networking;

namespace PredictionBench
{
    [Serializable]
    public class PredictionReport
    {
        public int schemaVersion = 1;
        public string suite = "prediction", workload = "sequenced-state-v1";
        public string solution, predictionScope, replayDefinition, unityVersion, peer, role, diagnosticJson, provenanceJson;
        public bool success, restoresAvailable;
        public bool linuxMetricsAvailable, developmentBuild;
        public bool cpuMetricsAvailable;
        public string scriptingBackend;
        public string networkCounterScope = "host-wide loopback aggregate; not per-peer bandwidth; excludes Photon Cloud traffic";
        public string error;
        public string memoryDiagnosticJson;
        public bool memorySnapshotRequested, memorySnapshotSucceeded;
        public string memorySnapshotPath;
        public PredictionConfig config;
        public int actualTickRate, observedObjects, ownedObjects;
        public int requestedFrameCap = 60, actualFrameCap;
        public double rttMs;
        public long forwardCalls, replayCalls, appliedInputs, restoreCalls, restoreDistance;
        public long ownedForwardCalls, ownedReplayCalls;
        public LoadStats load;
        public PawnSnapshot[] finalState;
    }

    public class PredictionRunner : MonoBehaviour
    {
        public PredictionAdapter adapter;
        private PredictionConfig _config;
        private PredictionReport _report;
        private string _results;
        private bool _finished;
        private readonly LoadSampler _sampler = new LoadSampler();
        private string _error;

        private void Awake()
        {
            Application.targetFrameRate = 60;
            Application.runInBackground = true;
            QualitySettings.vSyncCount = 0;
            _results = Arg("-predictionResults", "prediction.json");
            _config = new PredictionConfig
            {
                role = Arg("-predictionRole", "server"), peer = Arg("-predictionPeer", "server"),
                coordinator = Arg("-predictionCoordinator", "http://127.0.0.1:17999"),
                serverHost = Arg("-serverHost", "127.0.0.1"), session = Arg("-session", "prediction-bench"),
                region = Arg("-region", "eu"), clients = int.Parse(Arg("-count", "1")),
                objects = int.Parse(Arg("-benchObjects", "32")), tickRate = int.Parse(Arg("-tickRate", "60")),
                port = int.Parse(Arg("-port", "17800")), seconds = float.Parse(Arg("-benchSeconds", "10"), System.Globalization.CultureInfo.InvariantCulture),
                warmupSeconds = float.Parse(Arg("-warmupSeconds", "3"), System.Globalization.CultureInfo.InvariantCulture)
            };
            _report = new PredictionReport { solution = adapter.Solution, predictionScope = adapter.PredictionScope,
                replayDefinition = adapter.ReplayDefinition, restoresAvailable = adapter.RestoresAvailable,
                unityVersion = Application.unityVersion, peer = _config.peer, role = _config.role, config = _config };
            _report.provenanceJson = Resources.Load<TextAsset>("PredictionProvenance").text;
            _report.linuxMetricsAvailable = File.Exists("/proc/self/stat");
            _report.developmentBuild = Debug.isDebugBuild;
#if ENABLE_IL2CPP
            _report.scriptingBackend = "IL2CPP";
#else
            _report.scriptingBackend = "Mono";
#endif
            Application.logMessageReceived += OnLog;
        }

        private void Start() => StartCoroutine(Run());

        private IEnumerator Run()
        {
            adapter.Initialize(_config);
            float deadline = Time.realtimeSinceStartup + 120;
            while (!adapter.Connected)
            {
                if (_error != null || Time.realtimeSinceStartup > deadline) { Finish(false, _error ?? "Connection timeout"); yield break; }
                yield return null;
            }
            if (adapter.Server) Debug.Log("[PredictionBench] Server listening");
            while (adapter.Server && adapter.ConnectedClients != _config.clients)
            {
                if (_error != null || Time.realtimeSinceStartup > deadline) { Finish(false, _error ?? "Client population timeout"); yield break; }
                yield return null;
            }
            if (adapter.Server) adapter.Spawn();
            while (adapter.Snapshot().Length != _config.objects)
            {
                if (_error != null || Time.realtimeSinceStartup > deadline) { Finish(false, _error ?? "Spawn timeout"); yield break; }
                yield return new WaitForSecondsRealtime(0.1f);
            }
            var observed = adapter.Snapshot();
            _report.observedObjects = observed.Length;
            _report.ownedObjects = observed.Count(p => p.owned);
            _report.actualTickRate = adapter.ActualTickRate;
            if (_report.actualTickRate != _config.tickRate || (!adapter.Server && _report.ownedObjects == 0))
            { Finish(false, "Wrong tick rate or no locally owned predicted objects"); yield break; }

            // Control traffic is outside the timed window. The coordinator releases every
            // peer only after all have received their full object population.
            using (var request = UnityWebRequest.Post(_config.coordinator + "/ready/" + _config.peer, "{}", "application/json"))
            {
                request.timeout = 120;
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success) { Finish(false, "Ready barrier: " + request.error); yield break; }
            }
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 0;
            PredictionWorkload.Running = true;
            yield return new WaitForSecondsRealtime(_config.warmupSeconds);
            GC.Collect();
            Application.targetFrameRate = 60;
            _report.actualFrameCap = Application.targetFrameRate;
            GC.WaitForPendingFinalizers();
            GC.Collect();
            _report.rttMs = adapter.RttMs;
            adapter.BeginDiagnostics();
            PredictionWorkload.Begin();
            _sampler.Begin(Arg("-iface", "lo"));
            double end = Time.realtimeSinceStartupAsDouble + _config.seconds;
            yield return null; // Exclude the frame that established the measurement window.
            while (Time.realtimeSinceStartupAsDouble < end && _error == null)
            {
                if (!adapter.Connected || Application.targetFrameRate != 60)
                { _error = "Connection or frame-cap changed during measurement"; break; }
                _sampler.SampleFrame();
                yield return null;
            }
            _report.load = _sampler.End();
            _report.cpuMetricsAvailable = _report.load.cpuPercent >= 0;
            PredictionWorkload.Sampling = false;
            _report.diagnosticJson = adapter.EndDiagnostics();
            _report.memoryDiagnosticJson = adapter.MemoryDiagnostics();
            _report.forwardCalls = PredictionWorkload.ForwardCalls;
            _report.replayCalls = PredictionWorkload.ReplayCalls;
            _report.ownedForwardCalls = PredictionWorkload.OwnedForwardCalls;
            _report.ownedReplayCalls = PredictionWorkload.OwnedReplayCalls;
            _report.appliedInputs = PredictionWorkload.AppliedInputs;
            _report.restoreCalls = PredictionWorkload.Corrections;
            _report.restoreDistance = PredictionWorkload.CorrectionDistance;
            PredictionWorkload.Running = false;
            // Every peer has stopped input generation before final snapshots are requested.
            // Final commands continue being supplied to the native input path while settling.
            using (var request = UnityWebRequest.Post(_config.coordinator + "/stopped/" + _config.peer, "{}", "application/json"))
            {
                request.timeout = 120;
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success) { Finish(false, "Stop barrier: " + request.error); yield break; }
            }
            yield return new WaitForSecondsRealtime(5);
            _report.finalState = adapter.Snapshot().OrderBy(p => p.index).ToArray();
            // Optional retained-heap diagnostic, after timing, input shutdown and final state capture.
            string snapshotPath = Arg("-predictionMemorySnapshot", "");
            if (!string.IsNullOrEmpty(snapshotPath))
            {
                _report.memorySnapshotRequested = true;
                _report.memorySnapshotPath = Path.GetFullPath(snapshotPath);
                bool completed = false;
                if (File.Exists(_report.memorySnapshotPath))
                    _error = "Refusing to replace memory snapshot: " + _report.memorySnapshotPath;
                else
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(_report.memorySnapshotPath));
                    GC.Collect();
                    GC.WaitForPendingFinalizers();
                    GC.Collect();
                    Unity.Profiling.Memory.MemoryProfiler.TakeSnapshot(_report.memorySnapshotPath,
                        (_, success) => { _report.memorySnapshotSucceeded = success; completed = true; },
                        Unity.Profiling.Memory.CaptureFlags.ManagedObjects | Unity.Profiling.Memory.CaptureFlags.NativeObjects);
                    double snapshotDeadline = Time.realtimeSinceStartupAsDouble + 30;
                    while (!completed && Time.realtimeSinceStartupAsDouble < snapshotDeadline) yield return null;
                    if (!completed || !_report.memorySnapshotSucceeded)
                        _error = "Memory snapshot capture failed or timed out";
                }
            }
            bool active = _report.forwardCalls + _report.replayCalls > 0 &&
                _report.finalState.Length == _config.objects && _report.finalState.All(p => p.state.appliedInputs > 0);
            Finish(active && _error == null, _error ?? (active ? null : "Inactive or incomplete predicted workload"), quit: false);
            // Hold native networking alive until every peer captured its final state.
            using (var request = UnityWebRequest.Post(_config.coordinator + "/done/" + _config.peer, "{}", "application/json"))
            {
                request.timeout = 120;
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success)
                { _report.success = false; _report.error = "Final barrier: " + request.error; WriteReport(); }
            }
            Application.Quit(_report.success ? 0 : 1);
        }

        private void OnLog(string message, string stack, LogType type)
        {
            if (type == LogType.Exception || type == LogType.Error || type == LogType.Assert)
                _error = message;
        }

        private void Finish(bool success, string error, bool quit = true)
        {
            _finished = true;
            _report.success = success;
            _report.error = error;
            WriteReport();
            if (quit) Application.Quit(success ? 0 : 1);
        }

        private void WriteReport()
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(_results)));
            File.WriteAllText(_results, JsonUtility.ToJson(_report, true), Encoding.UTF8);
        }

        private void OnDestroy()
        {
            Application.logMessageReceived -= OnLog;
            if (!_finished && _report != null) Finish(false, "Runner destroyed before completion", quit: false);
        }

        public static string Arg(string name, string fallback)
        {
            var args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, name);
            return index >= 0 && index + 1 < args.Length ? args[index + 1] : fallback;
        }
    }
}
