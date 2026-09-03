using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace PurrNet.NetBench.Editor
{
    // game-ci custom build entry point: `buildMethod: PurrNet.NetBench.Editor.CIBuild.BuildLinuxPlayer`.
    // Builds the StandaloneLinux64 IL2CPP player for whichever project it runs in. Flags are read from
    // the Unity command line (game-ci customParameters); env vars do not reach the build container.
    //   -devBuild       Development build (live profiler samplers -> CPU-by-marker breakdown)
    //   -buildOutput P  Output path (absolute, or relative to the project root)
    public static class CIBuild
    {
        public static void BuildLinuxPlayer()
        {
            bool dev = Array.IndexOf(Environment.GetCommandLineArgs(), "-devBuild") >= 0;

            // Output precedence: explicit -buildOutput, then game-ci's -customBuildPath (absolute,
            // <workspace>/<buildsPath>/<target>/<buildName>, which is what the workflow uploads),
            // then a project-relative default for local use.
            string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string output = GetCommandLineValue("-buildOutput")
                            ?? GetCommandLineValue("-customBuildPath")
                            ?? Path.Combine("build", "StandaloneLinux64", "NetBench");
            if (!Path.IsPathRooted(output))
                output = Path.GetFullPath(Path.Combine(projectRoot, output));

            var scenes = EditorBuildSettings.scenes
                .Where(s => s.enabled)
                .Select(s => s.path)
                .ToArray();

            if (scenes.Length == 0)
            {
                // Some projects never added their scene to Build Settings; fall back to the benchmark scene.
                scenes = AssetDatabase.FindAssets("t:Scene", new[] { "Assets/_Benchmark" })
                    .Select(AssetDatabase.GUIDToAssetPath)
                    .OrderBy(p => p)
                    .Take(1)
                    .ToArray();
            }

            if (scenes.Length == 0)
            {
                Debug.LogError("[CIBuild] No scene to build.");
                EditorApplication.Exit(1);
                return;
            }

            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.IL2CPP);
            PlayerSettings.runInBackground = true;

            var options = new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = output,
                target = BuildTarget.StandaloneLinux64,
                options = dev ? BuildOptions.Development : BuildOptions.None
            };

            Debug.Log($"[CIBuild] Building StandaloneLinux64 IL2CPP (development={dev}) scenes=[{string.Join(", ", scenes)}] -> {output}");
            var report = BuildPipeline.BuildPlayer(options);
            var summary = report.summary;
            Debug.Log($"[CIBuild] Result={summary.result} size={summary.totalSize} errors={summary.totalErrors}");

            EditorApplication.Exit(summary.result == BuildResult.Succeeded ? 0 : 1);
        }

        private static string GetCommandLineValue(string key)
        {
            var args = Environment.GetCommandLineArgs();
            for (var i = 0; i < args.Length - 1; i++)
            {
                if (args[i] == key)
                    return args[i + 1];
            }

            return null;
        }
    }
}
