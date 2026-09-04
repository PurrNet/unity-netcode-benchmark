using System;
using StinkySteak.NetcodeBenchmark;
using UnityEditor;
using UnityEngine;

namespace PurrNet.NetBench.Editor
{
    // Run with Unity -batchmode -nographics -projectPath <project>
    // -executeMethod PurrNet.NetBench.Editor.BenchRegressionChecks.Run -logFile <path>.
    public static class BenchRegressionChecks
    {
        public static void Run()
        {
            try
            {
                CheckCadence();
                CheckMovement();
                CheckFinalState();
                Debug.Log("[BenchRegressionChecks] PASS: cadence, hitch catch-up, movement timestep, final-state checks.");
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                EditorApplication.Exit(1);
            }
        }

        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }

        private static void CheckCadence()
        {
            foreach (int hz in new[] { 20, 60 })
            {
                foreach (int fps in new[] { 30, 60, 144 })
                {
                    double accumulator = 0;
                    int ticks = 0;
                    for (int frame = 0; frame < fps * 10; frame++)
                        ticks += BenchRegistry.AdvanceTicks(ref accumulator, 1.0 / fps, 1.0 / hz);
                    Require(ticks == hz * 10, $"{hz} Hz workload produced {ticks} ticks at {fps} fps.");
                }

                double remainder = 0;
                int caughtUp = BenchRegistry.AdvanceTicks(ref remainder, 0.25, 1.0 / hz);
                Require(caughtUp == hz / 4, $"{hz} Hz workload dropped ticks during a hitch.");
            }
            double carry = 0;
            Require(BenchRegistry.AdvanceTicks(ref carry, 0.049, 0.05) == 0, "Tick fired early.");
            Require(BenchRegistry.AdvanceTicks(ref carry, 0.001, 0.05) == 1, "Fractional tick was lost.");
        }

        private static void CheckMovement()
        {
            var a = new GameObject("TickCheckA");
            var b = new GameObject("TickCheckB");
            var randomState = UnityEngine.Random.state;
            try
            {
                // Equal simulated time must reach the same sine position at 20 and 60 Hz.
                var y20 = SinMoveYWrapper.CreateDefault();
                var y60 = SinMoveYWrapper.CreateDefault();
                UnityEngine.Random.InitState(17);
                y20.NetworkStart(a.transform);
                UnityEngine.Random.InitState(17);
                y60.NetworkStart(b.transform);
                for (int i = 0; i < 20; i++) y20.NetworkUpdate(a.transform, 1f / 20);
                for (int i = 0; i < 60; i++) y60.NetworkUpdate(b.transform, 1f / 60);
                Require(Vector3.Distance(a.transform.position, b.transform.position) < 0.0001f,
                    "Sine motion depends on the Unity frame clock instead of simulated time.");

                // With the same steering step, tripling the supplied dt must triple displacement.
                var wander = WanderMoveWrapper.CreateDefault();
                UnityEngine.Random.InitState(21);
                wander.NetworkStart(a.transform);
                var copy = wander;
                b.transform.position = a.transform.position;
                var start = a.transform.position;
                var stepRandom = UnityEngine.Random.state;
                wander.NetworkUpdate(a.transform, 0.05f);
                UnityEngine.Random.state = stepRandom;
                copy.NetworkUpdate(b.transform, 1f / 60);
                var large = a.transform.position - start;
                var small = b.transform.position - start;
                Require(large.sqrMagnitude > 0 && Vector3.Distance(large, small * 3) < 0.0001f,
                    "Wander displacement does not use the supplied simulation timestep.");
            }
            finally
            {
                UnityEngine.Random.state = randomState;
                UnityEngine.Object.DestroyImmediate(a);
                UnityEngine.Object.DestroyImmediate(b);
            }
        }

        private static void CheckFinalState()
        {
            BenchRegistry.Mode = BenchMode.SyncVars;
            BenchRegistry.Spawned(4);
            BenchRegistry.RecordFinalState(1, 2, 3, Vector3.one);
            BenchRegistry.RecordFinalState(4, 5, 6, Vector3.zero);
            string ordered = BenchRegistry.FinalStateHash;
            Require(BenchRegistry.FinalStateObjects == 2, "Final-state object count is wrong.");
            BenchRegistry.Despawned(4);

            BenchRegistry.Spawned(4);
            Require(BenchRegistry.FinalStateObjects == 0, "A new test retained the previous state.");
            BenchRegistry.RecordFinalState(4, 5, 6, Vector3.zero);
            BenchRegistry.RecordFinalState(1, 2, 3, Vector3.one);
            Require(BenchRegistry.FinalStateHash == ordered, "Despawn order changes the state fingerprint.");
            BenchRegistry.Despawned(4);

            BenchRegistry.Spawned(4);
            BenchRegistry.RecordFinalState(4, 5, 7, Vector3.zero);
            BenchRegistry.RecordFinalState(1, 2, 3, Vector3.one);
            Require(BenchRegistry.FinalStateHash != ordered, "A changed field was not detected.");
            BenchRegistry.Despawned(4);
            BenchRegistry.Mode = BenchMode.Broadcast;
        }
    }
}
