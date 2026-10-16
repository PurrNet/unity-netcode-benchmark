using System;
using PurrNet.Prediction;
using UnityEngine;

namespace PredictionBench
{
    // Snapshot existing counters only at the measurement boundaries. No per-tick hook,
    // detailed telemetry collector, reflection or additional hot-loop counter is installed.
    public sealed class PurrDictionWorkCounters
    {
        [Serializable]
        public struct Snapshot
        {
            public ulong deltaFramesWrittenTotal, fullFramesSentTotal;
            public ulong deltaSectionDeleteBitsTotal, deltaSectionHierarchyBitsTotal;
            public ulong deltaSectionInputBitsTotal, deltaSectionStateBitsTotal;
            public ulong deltaFrameBytesTotal, fullFrameBytesTotal;
            public ulong inputSendsTotal, inputBytesSentTotal, inputTicksSentTotal;
            public ulong framesReceivedTotal, fullFramesReceivedTotal;
            public ulong leadJumpsTotal, leadPausesTotal, minLeadSnapsTotal, starvationJumpsTotal;
            public ulong renderPhaseFrameAppliesTotal, tickPhaseFrameAppliesTotal;

            public static Snapshot Capture(PredictionManager world) => new Snapshot
            {
                deltaFramesWrittenTotal = world.deltaFramesWrittenTotal,
                fullFramesSentTotal = world.fullFramesSentTotal,
                deltaSectionDeleteBitsTotal = world.deltaSectionDeleteBitsTotal,
                deltaSectionHierarchyBitsTotal = world.deltaSectionHierarchyBitsTotal,
                deltaSectionInputBitsTotal = world.deltaSectionInputBitsTotal,
                deltaSectionStateBitsTotal = world.deltaSectionStateBitsTotal,
                deltaFrameBytesTotal = world.deltaFrameBytesTotal,
                fullFrameBytesTotal = world.fullFrameBytesTotal,
                inputSendsTotal = world.inputSendsTotal,
                inputBytesSentTotal = world.inputBytesSentTotal,
                inputTicksSentTotal = world.inputTicksSentTotal,
                framesReceivedTotal = world.framesReceivedTotal,
                fullFramesReceivedTotal = world.fullFramesReceivedTotal,
                leadJumpsTotal = world.leadJumpsTotal,
                leadPausesTotal = world.leadPausesTotal,
                minLeadSnapsTotal = world.minLeadSnapsTotal,
                starvationJumpsTotal = world.starvationJumpsTotal,
                renderPhaseFrameAppliesTotal = world.renderPhaseFrameAppliesTotal,
                tickPhaseFrameAppliesTotal = world.tickPhaseFrameAppliesTotal
            };
        }

        [Serializable]
        public sealed class Window
        {
            public int schemaVersion = 1;
            public string scope = "Existing per-world counters read immediately before and after CPU timing; CPU scores are unchanged.";
            public string sectionScope = "Prepared ordinary-frame sections include bodies replaced before sending; exclude full frames and trailing event sections.";
            public string byteScope = "Frame bodies and input payloads before RPC compression, headers and fragmentation; not wire bandwidth.";
            public Snapshot start, end;
            public ulong localTickStart, localTickEnd, maxAckLagTicksStart, maxAckLagTicksEnd;
        }

        // Allocate before warmup/measurement, alongside the adapter.
        private readonly Window _window = new Window();

        public void Begin(PredictionManager world)
        {
            _window.start = Snapshot.Capture(world);
            _window.localTickStart = world.localTick;
            _window.maxAckLagTicksStart = world.lastMaxAckLagTicks;
        }

        public string End(PredictionManager world)
        {
            _window.end = Snapshot.Capture(world);
            _window.localTickEnd = world.localTick;
            _window.maxAckLagTicksEnd = world.lastMaxAckLagTicks;
            return JsonUtility.ToJson(_window);
        }
    }
}
