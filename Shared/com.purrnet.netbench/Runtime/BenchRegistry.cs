namespace PurrNet.NetBench
{
    /// <summary>What the SendRPC-prefab behaviours do while spawned.</summary>
    public enum BenchMode
    {
        /// <summary>Server fires one observers RPC per object per tick (test SendRPC; also the manual/button default).</summary>
        Broadcast = 0,
        /// <summary>Clients each send one small server RPC per tick; the server only receives (test ClientInput).</summary>
        ClientInput = 1,
        /// <summary>Server changes one synced field per object per tick (test SyncVars).</summary>
        SyncVars = 2
    }

    /// <summary>
    /// Netcode-agnostic shared state between <see cref="BenchRunner"/> and each project's behaviour
    /// scripts. Live object counts per prefab slot are fed from the netcode spawn/despawn callbacks;
    /// clients use them to detect which test the server is running (no cross-netcode RPC needed),
    /// the server uses them as its object count.
    ///
    /// Prefab slots: 1 MoveY, 2 MoveAllAxis, 3 MoveWander, 4 SendRPC. Tests map onto slots via
    /// <see cref="SlotOf"/>: Static and SpawnChurn reuse slot 1 with movement disabled, ClientInput
    /// and SyncVars reuse slot 4 with a different <see cref="Mode"/>.
    /// </summary>
    public static class BenchRegistry
    {
        private const int MaxSlots = 8;
        private static readonly int[] s_counts = new int[MaxSlots];

        /// <summary>Behaviour of the SendRPC-prefab scripts. Defaults keep the manual (button) behaviour.</summary>
        public static BenchMode Mode = BenchMode.Broadcast;

        /// <summary>False during Static / SpawnChurn so the movement scripts leave their transforms alone.</summary>
        public static bool MovementEnabled = true;

        /// <summary>Client -> server messages per second per client in <see cref="BenchMode.ClientInput"/>.</summary>
        public const float ClientInputHz = 20f;

        /// <summary>Server-side count of client input RPCs received (incremented by the SendRPC scripts).</summary>
        public static long ServerInputsReceived;

        public static void Spawned(int slot)
        {
            if ((uint)slot < MaxSlots)
                s_counts[slot]++;
        }

        public static void Despawned(int slot)
        {
            if ((uint)slot < MaxSlots && s_counts[slot] > 0)
                s_counts[slot]--;
        }

        public static int Count(int slot) => (uint)slot < MaxSlots ? s_counts[slot] : 0;

        /// <summary>Lowest prefab slot with live objects, or 0 when nothing is spawned.</summary>
        public static int ActiveSlot()
        {
            for (int i = 1; i < MaxSlots; i++)
            {
                if (s_counts[i] > 0)
                    return i;
            }

            return 0;
        }

        /// <summary>Prefab slot used by a test id (see <see cref="BenchRunner.TestNames"/>).</summary>
        public static int SlotOf(int test)
        {
            switch (test)
            {
                case 1: case 5: case 6: return 1;
                case 2: return 2;
                case 3: return 3;
                case 4: case 7: case 8: return 4;
                default: return 0;
            }
        }

        /// <summary>Fixed-rate helper for Update-driven loops: returns true once per <paramref name="interval"/>.</summary>
        public static bool Due(ref float accumulator, float deltaTime, float interval)
        {
            accumulator += deltaTime;
            if (accumulator < interval)
                return false;

            accumulator -= interval;
            if (accumulator > interval)
                accumulator = 0f;
            return true;
        }
    }
}
