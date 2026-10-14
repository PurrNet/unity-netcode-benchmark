using System;
using System.Collections.Generic;
using System.Linq;
using Fusion;
using Fusion.Photon.Realtime;
using Fusion.Sockets;
using UnityEngine;

namespace PredictionBench
{
    public struct FusionDriveInput : INetworkInput
    {
        public int sequence, x, z;
        public DriveInput ToCommon() => new DriveInput { sequence = sequence, x = x, z = z };
        public static FusionDriveInput From(DriveInput input) => new FusionDriveInput { sequence = input.sequence, x = input.x, z = input.z };
    }
    public struct FusionDriveState : INetworkStruct
    {
        public int x, z, lastSequence, appliedInputs, hash, a, b, c;
        public DriveState ToCommon() => new DriveState { x = x, z = z, lastSequence = lastSequence,
            appliedInputs = appliedInputs, hash = hash, a = a, b = b, c = c };
        public static FusionDriveState From(DriveState state) => new FusionDriveState { x = state.x, z = state.z,
            lastSequence = state.lastSequence, appliedInputs = state.appliedInputs,
            hash = state.hash, a = state.a, b = state.b, c = state.c };
    }
    public class FusionPredictionPawn : NetworkBehaviour
    {
        [Networked] public int Index { get; set; }
        [Networked] public FusionDriveState State { get; set; }
        public override void FixedUpdateNetwork()
        {
            var state = State.ToCommon();
            var input = GetInput(out FusionDriveInput value) ? value.ToCommon() : default;
            PredictionWorkload.Simulate(input, ref state, Runner.IsResimulation, Object.HasInputAuthority);
            State = FusionDriveState.From(state);
        }
    }
}
