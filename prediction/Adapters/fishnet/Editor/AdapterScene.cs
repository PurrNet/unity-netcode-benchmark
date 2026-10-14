using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Object;
using UnityEditor;
using UnityEngine;

namespace PredictionBench.Editor
{
    public static class AdapterScene
    {
        public static PredictionAdapter Create()
        {
            var managerPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/_Benchmark/Prefab/NetworkManager.prefab");
            if (!managerPrefab) throw new System.InvalidOperationException("FishNet manager prefab missing");
            var manager = ((GameObject)PrefabUtility.InstantiatePrefab(managerPrefab)).GetComponent<NetworkManager>();
            var pawn = new GameObject("Predicted state");
            var networkObject = pawn.AddComponent<NetworkObject>();
            pawn.AddComponent<FishNetPredictionPawn>();
            var properties = new SerializedObject(networkObject);
            properties.FindProperty("_enablePrediction").boolValue = true;
            properties.FindProperty("_enableStateForwarding").boolValue = true;
            properties.ApplyModifiedPropertiesWithoutUndo();
            var prefab = PrefabUtility.SaveAsPrefabAsset(pawn, "Assets/PredictionBench/Generated/Pawn.prefab");
            Object.DestroyImmediate(pawn);
            var prefabs = ScriptableObject.CreateInstance<SinglePrefabObjects>();
            prefabs.AddObject(prefab.GetComponent<NetworkObject>());
            AssetDatabase.CreateAsset(prefabs, "Assets/PredictionBench/Generated/Prefabs.asset");
            manager.SpawnablePrefabs = prefabs;
            var adapter = new GameObject("FishNet prediction adapter").AddComponent<FishNetPredictionAdapter>();
            adapter.manager = manager;
            adapter.prefab = prefab.GetComponent<FishNetPredictionPawn>();
            return adapter;
        }
    }
}
