using System;
using System.Linq;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Object;
using FishNet.Object.Prediction;
using FishNet.Object.Synchronizing;
using FishNet.Transporting;
using FishNet.Transporting.Tugboat;
using FishNet.Utility.Template;
using UnityEngine;

namespace PredictionBench
{
    public class FishNetPredictionAdapter : PredictionAdapter
    {
        public NetworkManager manager;
        public FishNetPredictionPawn prefab;
        public override string Solution => "fishnet";
        public override string PredictionScope => "owned and spectator objects; state forwarding enabled";
        public override string ReplayDefinition => "ReplicateState.ContainsReplayed";
        public override bool RestoresAvailable => true;
        public override bool Connected => Server ? manager.ServerManager.Started : manager.ClientManager.Started;
        public override int ConnectedClients => manager.ServerManager.Clients.Values.Count(p => p.LoadedStartScenes(true));
        public override int ActualTickRate => manager.TimeManager.TickRate;
        public override double RttMs => manager.TimeManager.RoundTripTime;
        protected override void Connect()
        {
            manager.TimeManager.SetTickRate((ushort)Config.tickRate);
            manager.ServerManager.SetFrameRate(60);
            manager.ClientManager.SetFrameRate(60);
            var transport = (Tugboat)manager.TransportManager.Transport;
            transport.SetMaximumClients(Config.clients);
            transport.SetClientAddress(Config.serverHost);
            transport.SetServerBindAddress("0.0.0.0", IPAddressType.IPv4);
            transport.SetPort((ushort)Config.port);
            if (Server) manager.ServerManager.StartConnection(); else manager.ClientManager.StartConnection();
        }
        public override void Spawn()
        {
            var players = manager.ServerManager.Clients.OrderBy(p => p.Key).Select(p => p.Value).ToArray();
            for (int i = 0; i < Config.objects; i++)
            {
                var pawn = Instantiate(prefab);
                pawn.SetIndex(i);
                manager.ServerManager.Spawn(pawn.gameObject, players[i % players.Length]);
            }
        }
        public override PawnSnapshot[] Snapshot() => FindObjectsByType<FishNetPredictionPawn>(FindObjectsSortMode.None)
            .Where(p => p.IsSpawned).Select(p => new PawnSnapshot { index = p.Index, owned = p.IsOwner, state = p.State }).ToArray();
    }
}
