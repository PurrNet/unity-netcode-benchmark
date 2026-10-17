#if PURRDICTION_PLAYER_INPUT
using System.Collections.Generic;
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

        private static readonly Dictionary<PlayerID, PurrDictionPlayerInput> s_byOwner = new Dictionary<PlayerID, PurrDictionPlayerInput>();
        private int _sequence;

        public static Input For(PlayerID? owner)
            => owner.HasValue && s_byOwner.TryGetValue(owner.Value, out var input) && input ? input.currentInput : default;

        protected override void OnOwnerAssigned(PlayerID? player)
        {
            base.OnOwnerAssigned(player);
            if (player.HasValue)
                s_byOwner[player.Value] = this;
        }

        protected override void OnDestroy()
        {
            base.OnDestroy();
            if (owner.HasValue && s_byOwner.TryGetValue(owner.Value, out var input) && input == this)
                s_byOwner.Remove(owner.Value);
        }

        protected override void GetFinalInput(ref Input input) => input.value = PredictionWorkload.Next(ref _sequence);

        protected override void Simulate(Input input, ref State state, float delta) { }
    }
}
#endif
