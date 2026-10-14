using PurrNet;
using PurrNet.Prediction;
using UnityEditor;
using UnityEngine;

namespace PredictionBench.Editor
{
    public static class AdapterScene
    {
        public static PredictionAdapter Create()
        {
            var managerPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/_Benchmark/Prefabs/NetworkManager.prefab");
            if (!managerPrefab) throw new System.InvalidOperationException("PurrNet manager prefab missing");
            var manager = ((GameObject)PrefabUtility.InstantiatePrefab(managerPrefab)).GetComponent<NetworkManager>();
            var networkSettings = new SerializedObject(manager);
            networkSettings.FindProperty("_networkPrefabs").objectReferenceValue = null;
            networkSettings.ApplyModifiedPropertiesWithoutUndo();
            var world = new GameObject("Prediction world").AddComponent<PredictionManager>();
            var serialized = new SerializedObject(world);
            serialized.FindProperty("_physicsProvider").intValue = 0;
            serialized.ApplyModifiedPropertiesWithoutUndo();
            var adapter = new GameObject("PurrDiction prediction adapter").AddComponent<PurrDictionPredictionAdapter>();
            adapter.manager = manager;
            adapter.world = world;
            return adapter;
        }
    }
}
