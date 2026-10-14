using System.Linq;
using PurrNet;
using PurrNet.Prediction;
using PurrNet.Transports;
using UnityEngine;

namespace PredictionBench
{
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
}
