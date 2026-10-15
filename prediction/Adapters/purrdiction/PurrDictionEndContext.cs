using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using PurrNet;
using PurrNet.Prediction;
using UnityEngine;

namespace PredictionBench
{
    // Diagnostic-only snapshots at the end of timing and after the ordinary final-state
    // snapshot. No per-tick hooks; clock values are local gauges, not CPU corrections.
    internal static class PurrDictionEndContext
    {
        private const BindingFlags Fields = BindingFlags.Instance | BindingFlags.NonPublic;
        private static readonly string[] Names = {
            "_verifiedServerTick", "_ackedServerTick", "_latestFrameServerTick", "_inputAckTick",
            "_pauseAdvanceTicks", "_leadAdjustGateTick", "_inputStarved", "_frameInputMargin",
            "_frameInputMarginTick", "_hasFrameInputMargin", "_frameInputSlackMs",
            "_frameInputSlackServerTick", "_frameInputSlackInputTick", "_hasFrameInputSlack",
            "_serverSendsInputSlack", "_lowMarginStreak", "_slackEmaMs", "_slackDevEmaMs",
            "_slackFloorEstimateMs", "_hasSlackEma", "_cachedInputFirstTick",
            "_cachedInputTickCount", "_cachedInputFragmented", "_lastInputSendTime"
        };

        [Serializable] private sealed class Gauge
        {
            public string name, type, value;
            public bool available;
        }

        [Serializable] private sealed class QueueContext
        {
            public ulong playerId, highestReceivedTick, rawHighestReceivedTick, ackedServerTick, lastConsumedTick;
            public bool bot, hasQueuedTicks, hasPendingInputSlack;
            public int queuedTicks;
            public ulong oldestQueuedTick, newestQueuedTick;
            public double pendingInputSlackMs;
        }

        [Serializable] private sealed class PawnInput
        {
            public int index, generatedSequence, appliedSequence;
        }

        [Serializable] private sealed class Snapshot
        {
            public int schemaVersion = 1;
            public string scope = "Read-only local clocks, input queues and owned generated/applied sequences outside CPU timing; diagnostic build only.";
            public string error;
            public bool server, inputQueuesAvailable;
            public ulong localTick;
            public double monotonicTime, unityTime;
            public Gauge[] gauges;
            public QueueContext[] inputQueues;
            public PawnInput[] ownedInputs;
        }

        internal static string Capture(PredictionManager world)
        {
            var snapshot = new Snapshot();
            try
            {
                snapshot.server = world.isServer;
                snapshot.localTick = world.localTick;
                snapshot.monotonicTime = PurrNet.NetBench.LoadSampler.MonotonicSeconds();
                snapshot.unityTime = Time.unscaledTimeAsDouble;
                var type = typeof(PredictionManager);
                var gauges = new List<Gauge>(Names.Length);
                foreach (var name in Names)
                {
                    var field = type.GetField(name, Fields);
                    gauges.Add(new Gauge { name = name, available = field != null,
                        type = field?.FieldType.FullName,
                        value = field == null ? null : Convert.ToString(field.GetValue(world), CultureInfo.InvariantCulture) });
                }
                snapshot.gauges = gauges.ToArray();
                var queues = type.GetField("_clientTicks", Fields)?.GetValue(world)
                    as Dictionary<PlayerID, PredictionManager.InputQueue>;
                snapshot.inputQueuesAvailable = queues != null;
                var queueContexts = new List<QueueContext>();
                if (queues != null)
                    foreach (var entry in queues)
                    {
                        var queue = entry.Value;
                        var context = new QueueContext { playerId = entry.Key.id.value, bot = entry.Key.isBot,
                            highestReceivedTick = queue.highestReceivedTick, rawHighestReceivedTick = queue.rawHighestReceivedTick,
                            ackedServerTick = queue.ackedServerTick, lastConsumedTick = queue.lastConsumedTick,
                            queuedTicks = queue.Count, hasQueuedTicks = queue.Count > 0,
                            pendingInputSlackMs = queue.pendingInputSlackMs, hasPendingInputSlack = queue.hasPendingInputSlack };
                        foreach (var tick in queue.byTick.Keys)
                        {
                            if (context.oldestQueuedTick == 0 || tick < context.oldestQueuedTick) context.oldestQueuedTick = tick;
                            if (tick > context.newestQueuedTick) context.newestQueuedTick = tick;
                        }
                        queueContexts.Add(context);
                    }
                snapshot.inputQueues = queueContexts.ToArray();
                var inputs = new List<PawnInput>();
                foreach (var pawn in UnityEngine.Object.FindObjectsByType<PurrDictionPredictionPawn>(FindObjectsSortMode.None))
                    if (pawn.predictionManager == world && pawn.gameObject.activeInHierarchy && pawn.IsOwner())
                        inputs.Add(new PawnInput { index = pawn.Index, generatedSequence = pawn.GeneratedInputSequence,
                            appliedSequence = pawn.currentState.value.lastSequence });
                snapshot.ownedInputs = inputs.ToArray();
            }
            catch (Exception error) { snapshot.error = error.GetType().Name + ": " + error.Message; }
            return JsonUtility.ToJson(snapshot);
        }
    }
}
