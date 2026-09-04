using System;
using UnityEngine;

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

        /// <summary>Whether the server should generate RPCs / state changes. Paused while final delivery settles.</summary>
        public static bool WorkloadEnabled = true;

        /// <summary>Shared cadence for frame-driven input and churn, set from the actual network tick rate.</summary>
        public static int TickRate = 20;
        public static double TickInterval => 1.0 / TickRate;

        // Whole-test counters include warmup and the delivery grace period. They add no network traffic.
        public static long RpcsSent;
        public static long RpcsReceived;
        public static long SyncMutations;
        public static int FinalStateObjects;
        private static ulong s_finalStateHash;
        public static string FinalStateHash => s_finalStateHash.ToString("x16");

        /// <summary>Server-side count of client input RPCs received (incremented by the SendRPC scripts).</summary>
        public static long ServerInputsReceived;

        public static void Spawned(int slot)
        {
            // Reset on the first RPC-prefab spawn, before any RPC can arrive on the client.
            // Resetting when the harness detects the test would discard early deliveries.
            if (slot == 4 && s_counts[slot] == 0)
            {
                RpcsSent = RpcsReceived = SyncMutations = 0;
                FinalStateObjects = 0;
                s_finalStateHash = 0;
            }
            if ((uint)slot < MaxSlots)
                s_counts[slot]++;
        }

        /// <summary>Capture each object's final SyncVar state before the netcode resets it on despawn.
        /// The sum is independent of spawn/despawn order. This checks exact convergence, not a spatial tolerance.</summary>
        public static void RecordFinalState(float a, float b, float c, Vector3 d)
        {
            if (Mode != BenchMode.SyncVars) return;
            ulong hash = 14695981039346656037UL;
            hash = HashFloat(hash, a);
            hash = HashFloat(hash, b);
            hash = HashFloat(hash, c);
            hash = HashFloat(hash, d.x);
            hash = HashFloat(hash, d.y);
            hash = HashFloat(hash, d.z);
            unchecked { s_finalStateHash += hash; }
            FinalStateObjects++;
        }

        private static ulong HashFloat(ulong hash, float value)
        {
            // Treat +0 and -0 as the same value.
            uint bits = value == 0f ? 0u : unchecked((uint)BitConverter.SingleToInt32Bits(value));
            return unchecked((hash ^ bits) * 1099511628211UL);
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

        /// <summary>Number of workload ticks due this frame. Preserve the remainder and catch up after slow
        /// frames, so a frame cap or hitch cannot silently reduce offered input / churn load.</summary>
        public static int AdvanceTicks(ref double accumulator, double deltaTime, double interval)
        {
            accumulator += deltaTime;
            int ticks = (int)Math.Floor((accumulator + interval * 1e-7) / interval);
            accumulator = Math.Max(0, accumulator - ticks * interval);
            return ticks;
        }
    }

    /// <summary>Client-visible state sampled at the same Unity phase in every project. No wire data,
    /// network-clock assumptions or per-sample allocations. Silence is not server-to-client latency.</summary>
    public static class SyncObservation
    {
        public static bool Measuring { get; private set; }
        public static long Changes { get; private set; }
        public static long Samples { get; private set; }
        public static double SilenceSumMs { get; private set; }
        public static double SilenceMaxMs { get; private set; }

        public static void Begin()
        {
            Changes = Samples = 0;
            SilenceSumMs = SilenceMaxMs = 0;
            Measuring = true;
        }

        public static void End() => Measuring = false;

        internal static void Record(bool changed, double silenceSeconds)
        {
            if (!Measuring) return;
            if (changed) Changes++;
            Samples++;
            double ms = Math.Max(0, silenceSeconds) * 1000;
            SilenceSumMs += ms;
            SilenceMaxMs = Math.Max(SilenceMaxMs, ms);
        }
    }

    /// <summary>One per object, reset on spawn. Warmup observations seed the last-change times;
    /// the first observation establishes a baseline and is never counted as a delivered change.</summary>
    public struct SyncStateObserver
    {
        private bool _initialized;
        private float _a, _b, _c;
        private Vector3 _d;
        private double _aChanged, _bChanged, _cChanged, _dChanged;

        public void Observe(float a, float b, float c, Vector3 d, double now)
        {
            if (!_initialized)
            {
                _initialized = true;
                _a = a; _b = b; _c = c; _d = d;
                _aChanged = _bChanged = _cChanged = _dChanged = now;
                return;
            }

            Sample(a != _a, now, ref _aChanged);
            Sample(b != _b, now, ref _bChanged);
            Sample(c != _c, now, ref _cChanged);
            // A Vector3 is one synced field, not three changes. Use exact components, not Unity's
            // approximate Vector3 equality, so every stack is observed with the same precision.
            Sample(d.x != _d.x || d.y != _d.y || d.z != _d.z, now, ref _dChanged);
            _a = a; _b = b; _c = c; _d = d;
        }

        private static void Sample(bool changed, double now, ref double lastChanged)
        {
            if (changed) lastChanged = now;
            SyncObservation.Record(changed, now - lastChanged);
        }
    }
}
