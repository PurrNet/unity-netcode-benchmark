using FishNet.Connection;
using FishNet.Observing;
using PurrNet.NetBench;

namespace StinkySteak.FishnetBenchmark
{
    /// <summary>Visibility test: each object is observed by the clients BenchRegistry.IsVisibleTo picks.</summary>
    public class BenchVisibilityCondition : ObserverCondition
    {
        public override bool ConditionMet(NetworkConnection connection, bool currentlyAdded, out bool notProcessed)
        {
            notProcessed = false;
            return BenchRegistry.IsVisibleTo(NetworkObject.ObjectId, connection.ClientId);
        }

        public override ObserverConditionType GetConditionType() => ObserverConditionType.Normal;
    }
}