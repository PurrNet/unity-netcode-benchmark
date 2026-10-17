using System.Linq;
using PurrNet;
using PurrNet.Prediction;
using PurrNet.Transports;
using UnityEngine;

namespace PredictionBench
{
#if PURRDICTION_PLAYER_INPUT
    // Pawns read their owner's single input identity, as Fusion pawns read their input authority's
    // per-player input, instead of each pawn collecting its own command.
    public class PurrDictionPredictionPawn : PredictedIdentity<PurrDictionPredictionPawn.State>
    {
        public int Index;
        public struct State : IPredictedData<State> { public DriveState value; public void Dispose() { } }
        protected override void Simulate(ref State state, float delta)
            => PredictionWorkload.Simulate(PurrDictionPlayerInput.For(owner).value, ref state.value,
                predictionManager.isReplaying, IsOwner());
    }
#else
    public class PurrDictionPredictionPawn : PredictedIdentity<PurrDictionPredictionPawn.Input, PurrDictionPredictionPawn.State>
    {
        public int Index;
        private int _sequence;
        public struct Input : IPredictedData { public DriveInput value; public void Dispose() { } }
        public struct State : IPredictedData<State> { public DriveState value; public void Dispose() { } }
        protected override void GetFinalInput(ref Input input) => input.value = PredictionWorkload.Next(ref _sequence);
        protected override void Simulate(Input input, ref State state, float delta)
            => PredictionWorkload.Simulate(input.value, ref state.value, predictionManager.isReplaying, IsOwner());
    }
#endif
}
