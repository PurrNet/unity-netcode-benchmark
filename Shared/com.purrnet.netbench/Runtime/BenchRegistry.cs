namespace PurrNet.NetBench
{
    /// <summary>
    /// Netcode-agnostic count of live benchmark objects per test, fed by each project's behaviour
    /// scripts from their netcode spawn/despawn callbacks. Clients use it to detect which test the
    /// server is running (no cross-netcode RPC needed); the server uses it as its object count.
    /// Test ids: 1 MoveY, 2 MoveAllAxis, 3 MoveWander, 4 SendRPC.
    /// </summary>
    public static class BenchRegistry
    {
        private const int MaxTests = 8;
        private static readonly int[] s_counts = new int[MaxTests];

        public static void Spawned(int test)
        {
            if ((uint)test < MaxTests)
                s_counts[test]++;
        }

        public static void Despawned(int test)
        {
            if ((uint)test < MaxTests && s_counts[test] > 0)
                s_counts[test]--;
        }

        public static int Count(int test) => (uint)test < MaxTests ? s_counts[test] : 0;

        /// <summary>Lowest test id with live objects, or 0 when nothing is spawned.</summary>
        public static int ActiveTest()
        {
            for (int i = 1; i < MaxTests; i++)
            {
                if (s_counts[i] > 0)
                    return i;
            }

            return 0;
        }
    }
}
