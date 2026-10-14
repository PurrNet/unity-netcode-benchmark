using System;
using System.Reflection;
using PurrNet.Prediction;
using UnityEngine;

namespace PredictionBench
{
    [Serializable]
    public sealed class HistoryMemoryStats
    {
        public int histories, entries;
        public long slots, arrayPayloadBytes;
    }

    [Serializable]
    public sealed class PurrDictionMemorySnapshot
    {
        public string scope = "Benchmark pawn history backing-array payloads only; excludes array/object headers, owned payloads, framework statics, and native memory. Captured after timing.";
        public bool available = true;
        public string error;
        public int activePawns, templates;
        public HistoryMemoryStats predicted = new HistoryMemoryStats();
        public HistoryMemoryStats verified = new HistoryMemoryStats();
        public HistoryMemoryStats inputs = new HistoryMemoryStats();
    }

    public static class PurrDictionMemoryDiagnostics
    {
        private const BindingFlags Fields = BindingFlags.Instance | BindingFlags.NonPublic;

        // Reflection is deliberately outside the measured window and never edits storage.
        public static PurrDictionMemorySnapshot Capture(PredictionManager world)
        {
            var result = new PurrDictionMemorySnapshot();
            try
            {
                foreach (var pawn in UnityEngine.Object.FindObjectsByType<PurrDictionPredictionPawn>(
                             FindObjectsInactive.Include, FindObjectsSortMode.None))
                {
                    if (pawn.predictionManager != world)
                    {
                        if (!pawn.predictionManager && !pawn.gameObject.activeInHierarchy)
                            result.templates++;
                        continue;
                    }
                    result.activePawns++;
                    Add(pawn, "_stateHistory", result.predicted);
                    Add(pawn, "_verifiedHistory", result.verified);
                    Add(pawn, "_inputHistory", result.inputs);
                }
                if (result.activePawns == 0)
                    throw new InvalidOperationException("No benchmark pawns belong to the prediction world.");
            }
            catch (Exception error)
            {
                result.available = false;
                result.error = error.Message;
            }
            return result;
        }

        private static void Add(object pawn, string name, HistoryMemoryStats totals)
        {
            FieldInfo field = null;
            for (var type = pawn.GetType(); type != null && field == null; type = type.BaseType)
                field = type.GetField(name, Fields);
            if (field == null)
                throw new InvalidOperationException("History field unavailable: " + name);
            var history = field.GetValue(pawn);
            if (history == null)
                return;
            var historyType = history.GetType();
            var payload = historyType.GetProperty("BackingStoragePayloadBytes", Fields);
            var values = historyType.GetField("m_values", Fields);
            var count = historyType.GetProperty("Count");
            if (payload == null || values == null || count == null)
                throw new InvalidOperationException("History layout unavailable: " + historyType.FullName);
            totals.histories++;
            totals.entries += (int)count.GetValue(history);
            totals.slots += ((Array)values.GetValue(history)).LongLength;
            totals.arrayPayloadBytes += (long)payload.GetValue(history);
        }
    }
}
