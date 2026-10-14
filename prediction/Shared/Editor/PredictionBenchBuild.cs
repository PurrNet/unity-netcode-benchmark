using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace PredictionBench.Editor
{
    public static class PredictionBenchBuild
    {
        public static void BuildLinux() => Build(BuildTarget.StandaloneLinux64, ScriptingImplementation.IL2CPP);
        public static void BuildWindows() => Build(BuildTarget.StandaloneWindows64, ScriptingImplementation.Mono2x);
        private static void Build(BuildTarget target, ScriptingImplementation backend)
        {
            try
            {
                Directory.CreateDirectory("Assets/PredictionBench/Generated");
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                var adapter = AdapterScene.Create();
                new GameObject("Prediction benchmark").AddComponent<PredictionRunner>().adapter = adapter;
                const string scene = "Assets/PredictionBench/Generated/Prediction.unity";
                EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), scene);
                PlayerSettings.runInBackground = true;
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, backend);
                string output = PredictionRunner.Arg("-customBuildPath",
                    PredictionRunner.Arg("-buildOutput", target == BuildTarget.StandaloneWindows64 ? "build/PredictionBench.exe" : "build/PredictionBench"));
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));
                bool development = Array.IndexOf(Environment.GetCommandLineArgs(), "-devBuild") >= 0;
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { scene },
                    locationPathName = output, target = target,
                    options = development ? BuildOptions.Development : BuildOptions.None });
                EditorApplication.Exit(report.summary.result == BuildResult.Succeeded ? 0 : 1);
            }
            catch (Exception error) { Debug.LogException(error); EditorApplication.Exit(1); }
        }
    }
}
