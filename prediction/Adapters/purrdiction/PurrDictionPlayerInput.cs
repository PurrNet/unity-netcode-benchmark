#if PURRDICTION_PLAYER_INPUT
using System;
using PurrNet;
using PurrNet.Prediction;

namespace PredictionBench
{
    // One input identity per player, owned by that player. Its current input is the command
    // every pawn of that player simulates with for the tick being run.
    public class PurrDictionPlayerInput : PredictedIdentity<PurrDictionPlayerInput.Input, PurrDictionPlayerInput.State>
    {
        public struct Input : IPredictedData { public DriveInput value; public void Dispose() { } }
        public struct State : IPredictedData<State> { public int unused; public void Dispose() { } }

        // Indexed by player id, like a per-player input table; every pawn reads it each tick.
        private static PurrDictionPlayerInput[] s_byOwner = new PurrDictionPlayerInput[16];
        private int _sequence;

        public static Input For(PlayerID? owner)
        {
            if (!owner.HasValue)
                return default;
            ulong id = owner.Value.id.value;
            var input = id < (ulong)s_byOwner.Length ? s_byOwner[id] : null;
            return input is null ? default : input.currentInput;
        }

        protected override void OnOwnerAssigned(PlayerID? player)
        {
            base.OnOwnerAssigned(player);
            if (!player.HasValue)
                return;
            Unregister();
            ulong id = player.Value.id.value;
            if (id >= (ulong)s_byOwner.Length)
                Array.Resize(ref s_byOwner, (int)Math.Max(id + 1, (ulong)s_byOwner.Length * 2));
            s_byOwner[id] = this;
        }

        protected override void OnDestroy()
        {
            base.OnDestroy();
            Unregister();
        }

        private void Unregister()
        {
            for (int i = 0; i < s_byOwner.Length; i++)
                if (ReferenceEquals(s_byOwner[i], this))
                    s_byOwner[i] = null;
        }

        protected override void GetFinalInput(ref Input input) => input.value = PredictionWorkload.Next(ref _sequence);

        protected override void Simulate(Input input, ref State state, float delta) { }
    }
}
#endif
