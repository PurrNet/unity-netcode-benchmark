using System.Linq;
using PurrNet;
using PurrNet.Prediction;
using PurrNet.Transports;
using UnityEngine;

namespace PredictionBench
{
    public class PurrDictionPredictionAdapter : PredictionAdapter
    {
        public NetworkManager manager;
        public PredictionManager world;
        private readonly PurrDictionWorkCounters _workCounters = new PurrDictionWorkCounters();
        private GameObject[] _prefabs;
#if PURRDICTION_PLAYER_INPUT
        private GameObject _inputPrefab;
        private const PredictionPolicy PawnPolicy = PredictionPolicy.PredictedIfOwned;
        public override string Solution => "purrdiction-player-input";
        public override string PredictionScope => "PredictedIfOwned; one input identity per player, read by that player's pawns";
#elif PURRDICTION_OWNED_ONLY
        private const PredictionPolicy PawnPolicy = PredictionPolicy.PredictedIfOwned;
        public override string Solution => "purrdiction-owned";
        public override string PredictionScope => "PredictedIfOwned: owned objects predict and replay; remote objects run verified ServerRelay ticks";
#else
        private const PredictionPolicy PawnPolicy = PredictionPolicy.FullPrediction;
        public override string Solution => "purrdiction";
        public override string PredictionScope => "FullPrediction for every object; world rollback";
#endif
        public override string ReplayDefinition => "PredictionManager.isReplaying (verified + gap + speculative); diagnosticJson separates passes";
        public override bool Connected => (Server ? manager.isServer : manager.isClient) && world.isSpawned;
        public override int ConnectedClients => manager.playerCount;
        public override int ActualTickRate => world.tickRate;
        public override double RttMs => 0; // Use native diagnostics; no invented RTT conversion.
        protected override void Connect()
        {
            manager.tickRate = Config.tickRate;
            manager.mtuExceededBehaviour = MTUExceededBehaviour.Fragment;
            var transport = (UDPTransport)manager.transport;
            transport.address = Config.serverHost;
            transport.serverPort = (ushort)Config.port;
            transport.maxConnections = Config.clients;
            var prefabs = ScriptableObject.CreateInstance<PredictedPrefabs>();
            prefabs.autoGenerate = false;
            prefabs.searchAllIfNoFolder = false;
            _prefabs = new GameObject[Config.objects];
            for (int i = 0; i < _prefabs.Length; i++)
            {
                var pawn = new GameObject("State template " + i);
                pawn.SetActive(false);
                var component = pawn.AddComponent<PurrDictionPredictionPawn>();
                component.Index = i;
                component.SetPredictionPolicyOverride(PawnPolicy);
                _prefabs[i] = pawn;
                prefabs.prefabs.Add(new PredictedPrefab { prefab = pawn, pooled = false });
            }
#if PURRDICTION_PLAYER_INPUT
            _inputPrefab = new GameObject("Player input template");
            _inputPrefab.SetActive(false);
            _inputPrefab.AddComponent<PurrDictionPlayerInput>().SetPredictionPolicyOverride(PawnPolicy);
            prefabs.prefabs.Add(new PredictedPrefab { prefab = _inputPrefab, pooled = false });
#endif
            world.predictedPrefabs = prefabs;
            if (Server) manager.StartServer(); else manager.StartClient();
        }
        public override void Spawn()
        {
            var players = manager.players.OrderBy(p => p.id.value).ToArray();
#if PURRDICTION_PLAYER_INPUT
            foreach (var player in players)
                world.hierarchy.Create(_inputPrefab, Vector3.zero, Quaternion.identity, player);
#endif
            for (int i = 0; i < Config.objects; i++)
                world.hierarchy.Create(_prefabs[i], Vector3.zero, Quaternion.identity, players[i % players.Length]);
        }
        public override PawnSnapshot[] Snapshot() => FindObjectsByType<PurrDictionPredictionPawn>(FindObjectsSortMode.None)
            .Where(p => p.predictionManager && p.gameObject.activeInHierarchy)
            .Select(p => new PawnSnapshot { index = p.Index, owned = p.IsOwner(), state = p.currentState.value }).ToArray();
        public override void BeginDiagnostics()
        {
            if (Config.detailedDiagnostics) PredictionPerformanceTelemetry.Begin(world);
        }
        public override string EndDiagnostics() => Config.detailedDiagnostics
            ? JsonUtility.ToJson(PredictionPerformanceTelemetry.End()) : "{}";
        public override void BeginWorkCounters() => _workCounters.Begin(world);
        public override string EndWorkCounters() => _workCounters.End(world);
        public override string MemoryDiagnostics() => JsonUtility.ToJson(PurrDictionMemoryDiagnostics.Capture(world));
    }
}
