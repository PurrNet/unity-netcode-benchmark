using System;
using System.Collections.Generic;
using System.Linq;
using Fusion;
using Fusion.Photon.Realtime;
using Fusion.Sockets;
using UnityEngine;

namespace PredictionBench
{
    public class FusionPredictionAdapter : PredictionAdapter, INetworkRunnerCallbacks
    {
        public FusionPredictionPawn prefab;
        private NetworkRunner _runner;
        private int _sequence;
        public override string Solution => "fusion";
        public override string PredictionScope => "native Server mode input authority; proxies receive networked state";
        public override string ReplayDefinition => "NetworkRunner.IsResimulation";
        public override bool Connected => _runner && _runner.IsRunning && (Server || _runner.LocalPlayer.IsRealPlayer);
        public override int ConnectedClients => _runner ? _runner.ActivePlayers.Count() : 0;
        public override int ActualTickRate => (int)_runner.TickRate;
        public override double RttMs => Server ? 0 : _runner.GetPlayerRtt(_runner.LocalPlayer) * 1000;
        protected override async void Connect()
        {
            _runner = new GameObject("Fusion runner").AddComponent<NetworkRunner>();
            _runner.ProvideInput = !Server;
            _runner.AddCallbacks(this);
            var selection = NetworkProjectConfig.Global.Simulation.TickRateSelection;
            selection.Client = Config.tickRate;
            selection.ClientSendInterval = selection.ServerTickInterval = selection.ServerSendInterval = 1;
            NetworkProjectConfig.Global.Simulation.TickRateSelection = selection;
            var settings = new FusionAppSettings();
            PhotonAppSettings.Global.AppSettings.CopyTo(settings);
            settings.FixedRegion = Config.region;
            var result = await _runner.StartGame(new StartGameArgs {
                GameMode = Server ? GameMode.Server : GameMode.Client, SessionName = Config.session,
                PlayerCount = Config.clients + 1, CustomPhotonAppSettings = settings,
                Scene = SceneRef.FromIndex(0), SceneManager = _runner.gameObject.AddComponent<NetworkSceneManagerDefault>() });
            if (!result.Ok) Debug.LogError("Fusion start failed: " + result.ShutdownReason);
        }
        public override void Spawn()
        {
            var players = _runner.ActivePlayers.OrderBy(p => p.RawEncoded).ToArray();
            for (int i = 0; i < Config.objects; i++)
            {
                int index = i;
                _runner.Spawn(prefab.GetComponent<NetworkObject>(), inputAuthority: players[i % players.Length],
                    onBeforeSpawned: (runner, obj) => obj.GetComponent<FusionPredictionPawn>().Index = index);
            }
        }
        public override PawnSnapshot[] Snapshot() => FindObjectsByType<FusionPredictionPawn>(FindObjectsSortMode.None)
            .Where(p => p.Object && p.Object.IsValid).Select(p => new PawnSnapshot {
                index = p.Index, owned = p.Object.HasInputAuthority, state = p.State.ToCommon() }).ToArray();
        public void OnInput(NetworkRunner runner, NetworkInput input) => input.Set(FusionDriveInput.From(PredictionWorkload.Next(ref _sequence)));
        public void OnInputMissing(NetworkRunner runner, PlayerRef player, NetworkInput input) { }
        public void OnPlayerJoined(NetworkRunner runner, PlayerRef player) { }
        public void OnPlayerLeft(NetworkRunner runner, PlayerRef player) { }
        public void OnConnectedToServer(NetworkRunner runner) { }
        public void OnDisconnectedFromServer(NetworkRunner runner, NetDisconnectReason reason) => Debug.LogError("Fusion disconnected: " + reason);
        public void OnConnectRequest(NetworkRunner runner, NetworkRunnerCallbackArgs.ConnectRequest request, byte[] token) { }
        public void OnConnectFailed(NetworkRunner runner, NetAddress address, NetConnectFailedReason reason) => Debug.LogError("Fusion connection failed: " + reason);
        public void OnShutdown(NetworkRunner runner, ShutdownReason reason) { }
        public void OnSessionListUpdated(NetworkRunner runner, List<SessionInfo> sessions) { }
        public void OnCustomAuthenticationResponse(NetworkRunner runner, Dictionary<string, object> data) { }
        public void OnHostMigration(NetworkRunner runner, HostMigrationToken token) { }
        public void OnReliableDataReceived(NetworkRunner runner, PlayerRef player, ReliableKey key, ReadOnlySpan<byte> data) { }
        public void OnReliableDataProgress(NetworkRunner runner, PlayerRef player, ReliableKey key, float progress) { }
        public void OnSceneLoadDone(NetworkRunner runner) { }
        public void OnSceneLoadStart(NetworkRunner runner) { }
        public void OnObjectEnterAOI(NetworkRunner runner, NetworkObject obj, PlayerRef player) { }
        public void OnObjectExitAOI(NetworkRunner runner, NetworkObject obj, PlayerRef player) { }
    }
}
