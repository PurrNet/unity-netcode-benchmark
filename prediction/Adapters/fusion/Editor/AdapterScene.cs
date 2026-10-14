using Fusion;
using UnityEditor;
using UnityEngine;

namespace PredictionBench.Editor
{
    public static class AdapterScene
    {
        public static PredictionAdapter Create()
        {
            var pawn = new GameObject("Predicted state");
            pawn.AddComponent<NetworkObject>();
            pawn.AddComponent<FusionPredictionPawn>();
            new NetworkObjectBaker().Bake(pawn);
            var prefab = PrefabUtility.SaveAsPrefabAsset(pawn, "Assets/PredictionBench/Generated/Pawn.prefab");
            Object.DestroyImmediate(pawn);
            AssetDatabase.ImportAsset("Assets/PredictionBench/Generated/Pawn.prefab", ImportAssetOptions.ForceSynchronousImport);
            // Fusion's prefab importer registers this asset in the project's prefab table.
            var adapter = new GameObject("Fusion prediction adapter").AddComponent<FusionPredictionAdapter>();
            adapter.prefab = prefab.GetComponent<FusionPredictionPawn>();
            return adapter;
        }
    }
}
