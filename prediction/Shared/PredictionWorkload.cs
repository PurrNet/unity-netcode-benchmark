using System;

namespace PredictionBench
{
    // Identical game logic and logical payload on every adapter; no Unity physics or allocations.
    [Serializable]
    public struct DriveInput
    {
        public int sequence, x, z;
    }

    [Serializable]
    public struct DriveState
    {
        public int x, z, lastSequence, appliedInputs;
        public int hash, a, b, c;
    }

    public static class PredictionWorkload
    {
        public static bool Running;
        public static bool Sampling;
        public static long ForwardCalls, ReplayCalls, AppliedInputs, Corrections;
        public static long OwnedForwardCalls, OwnedReplayCalls;
        public static long CorrectionDistance;

        public static DriveInput Next(ref int sequence)
        {
            if (Running) sequence++;
            if (sequence == 0) return default;
            return new DriveInput { sequence = sequence,
                x = (sequence / 12 & 1) == 0 ? 1 : -1,
                z = (sequence / 19 & 1) == 0 ? 1 : -1 };
        }

        public static void Simulate(DriveInput input, ref DriveState state, bool replay, bool owned)
        {
            if (Sampling)
            {
                if (replay) ReplayCalls++; else ForwardCalls++;
                if (owned) { if (replay) OwnedReplayCalls++; else OwnedForwardCalls++; }
            }
            // This workload consumes sequenced commands once. Repeated/absent inputs do not
            // advance its state, allowing exact final convergence after input generation stops.
            if (input.sequence <= state.lastSequence) return;
            unchecked
            {
                state.x += input.x;
                state.z += input.z;
                state.lastSequence = input.sequence;
                state.appliedInputs++;
                state.hash = state.hash * 31 + input.sequence;
                state.a = state.a * 17 + input.x;
                state.b = state.b * 23 + input.z;
                state.c = state.c * 13 + input.x * input.z;
            }
            if (Sampling) AppliedInputs++;
        }

        public static void Correction(DriveState before, DriveState after)
        {
            // A restore can rewind time without representing a misprediction. These are
            // restore deltas, deliberately not advertised as visible correction error.
            if (!Sampling) return;
            Corrections++;
            CorrectionDistance += Math.Abs((long)before.x - after.x) + Math.Abs((long)before.z - after.z);
        }

        public static void Begin()
        {
            ForwardCalls = ReplayCalls = AppliedInputs = Corrections = CorrectionDistance = 0;
            OwnedForwardCalls = OwnedReplayCalls = 0;
            Sampling = true;
        }
    }
}
