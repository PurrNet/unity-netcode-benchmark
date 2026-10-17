using System;
using System.Collections.Generic;
using System.Reflection;
using PurrNet.Prediction;
using UnityEngine;

namespace PredictionBench
{
    [Serializable]
    public sealed class HierarchyMemoryStats
    {
        public HistoryMemoryStats predicted = new HistoryMemoryStats();
        public HistoryMemoryStats verified = new HistoryMemoryStats();
        public int uniquePieceLists, uniqueDeleteLists;
        public long pieceSlots, deleteSlots;
    }

    [Serializable]
    public sealed class HistoryMemoryStats
    {
        public int histories, entries;
        public long slots, arrayPayloadBytes;
    }

    [Serializable]
    public sealed class PurrDictionMemorySnapshot
    {
        public string scope = "Pawn history backing-array payload bytes and hierarchy history/list capacities. Excludes object/array headers, other owned payloads, framework statics, and native memory. Captured after timing.";
        public bool available = true;
        public string error;
        public int activePawns, templates;
        public HistoryMemoryStats predicted = new HistoryMemoryStats();
        public HistoryMemoryStats verified = new HistoryMemoryStats();
        public HistoryMemoryStats inputs = new HistoryMemoryStats();
        public HierarchyMemoryStats hierarchy;
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
#if !PURRDICTION_PLAYER_INPUT
                    Add(pawn, "_inputHistory", result.inputs);
#endif
                }
#if PURRDICTION_PLAYER_INPUT
                foreach (var input in UnityEngine.Object.FindObjectsByType<PurrDictionPlayerInput>(FindObjectsSortMode.None))
                    if (input.predictionManager == world)
                        Add(input, "_inputHistory", result.inputs);
#endif
                if (result.activePawns == 0)
                    throw new InvalidOperationException("No benchmark pawns belong to the prediction world.");
                if (world.hierarchy)
                {
                    result.hierarchy = new HierarchyMemoryStats();
                    var pieces = new HashSet<List<InstanceDetails>>();
                    var deletes = new HashSet<List<PredictedObjectID>>();
                    CountTopology(Add(world.hierarchy, "_stateHistory", result.hierarchy.predicted), pieces, deletes);
                    CountTopology(Add(world.hierarchy, "_verifiedHistory", result.hierarchy.verified), pieces, deletes);
                    result.hierarchy.uniquePieceLists = pieces.Count;
                    result.hierarchy.uniqueDeleteLists = deletes.Count;
                    foreach (var list in pieces) result.hierarchy.pieceSlots += list.Capacity;
                    foreach (var list in deletes) result.hierarchy.deleteSlots += list.Capacity;
                }
            }
            catch (Exception error)
            {
                result.available = false;
                result.error = error.Message;
            }
            return result;
        }

        private static object Add(object pawn, string name, HistoryMemoryStats totals)
        {
            FieldInfo field = null;
            for (var type = pawn.GetType(); type != null && field == null; type = type.BaseType)
                field = type.GetField(name, Fields);
            if (field == null)
                throw new InvalidOperationException("History field unavailable: " + name);
            var history = field.GetValue(pawn);
            if (history == null)
                return null;
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
            return history;
        }

        private static void CountTopology(object history, HashSet<List<InstanceDetails>> pieces,
            HashSet<List<PredictedObjectID>> deletes)
        {
            if (history == null) return;
            var type = history.GetType();
            var item = type.GetProperty("Item");
            var state = type.GetGenericArguments()[0].GetField("state");
            if (item == null || state == null)
                throw new InvalidOperationException("Topology history metadata unavailable.");
            int count = (int)type.GetProperty("Count").GetValue(history);
            var index = new object[1];
            for (int i = 0; i < count; i++)
            {
                index[0] = i;
                var topology = (PredictedHierarchyState)state.GetValue(item.GetValue(history, index));
                if (!topology.spawnedPrefabs.isDisposed) pieces.Add(topology.spawnedPrefabs.list);
                if (!topology.toDelete.isDisposed) deletes.Add(topology.toDelete.list);
            }
        }
    }
}
