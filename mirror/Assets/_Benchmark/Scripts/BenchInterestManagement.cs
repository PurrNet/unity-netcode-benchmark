using System.Collections.Generic;
using Mirror;
using PurrNet.NetBench;

namespace StinkySteak.MirrorBenchmark
{
    /// <summary>Visibility test: each object is observed by the clients BenchRegistry.IsVisibleTo picks.</summary>
    public class BenchInterestManagement : InterestManagement
    {
        public override bool OnCheckObserver(NetworkIdentity identity, NetworkConnectionToClient newObserver)
        {
            return BenchRegistry.IsVisibleTo(identity.netId, newObserver.connectionId);
        }

        public override void OnRebuildObservers(NetworkIdentity identity, HashSet<NetworkConnectionToClient> newObservers)
        {
            foreach (NetworkConnectionToClient conn in NetworkServer.connections.Values)
            {
                if (conn.isReady && BenchRegistry.IsVisibleTo(identity.netId, conn.connectionId))
                    newObservers.Add(conn);
            }
        }
    }
}