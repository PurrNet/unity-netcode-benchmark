using System;
using System.Linq;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Object;
using FishNet.Object.Prediction;
using FishNet.Object.Synchronizing;
using FishNet.Transporting;
using FishNet.Transporting.Tugboat;
using FishNet.Utility.Template;
using UnityEngine;

namespace PredictionBench
{
    public class FishNetPredictionPawn : TickNetworkBehaviour
    {
        public struct InputData : IReplicateData
        {
            public DriveInput input;
            private uint _tick;
            public void Dispose() { }
            public uint GetTick() => _tick;
            public void SetTick(uint tick) => _tick = tick;
        }
        public struct StateData : IReconcileData
        {
            public DriveState state;
            private uint _tick;
            public void Dispose() { }
            public uint GetTick() => _tick;
            public void SetTick(uint tick) => _tick = tick;
        }
        private readonly SyncVar<int> _index = new SyncVar<int>();
        private DriveState _state;
        private int _sequence;
        public int Index => _index.Value;
        public DriveState State => _state;
        public void SetIndex(int index) => _index.Value = index;
        protected override void TimeManager_OnTick()
        {
            var input = IsOwner ? PredictionWorkload.Next(ref _sequence) : default;
            RunInput(new InputData { input = input });
        }
        protected override void TimeManager_OnPostTick() => CreateReconcile();
        public override void CreateReconcile() => Restore(new StateData { state = _state });
        [Replicate]
        private void RunInput(InputData input, ReplicateState state = ReplicateState.Invalid, Channel channel = Channel.Unreliable)
            => PredictionWorkload.Simulate(input.input, ref _state, state.ContainsReplayed(), IsOwner);
        [Reconcile]
        private void Restore(StateData state, Channel channel = Channel.Unreliable)
        {
            PredictionWorkload.Correction(_state, state.state);
            _state = state.state;
        }
    }
}
