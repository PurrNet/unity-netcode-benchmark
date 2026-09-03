using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace StinkySteak.NetcodeBenchmark
{
    public class BaseGUIGame : MonoBehaviour
    {
        [SerializeField] private Button _buttonStartServer;
        [SerializeField] private Button _buttonStartClient;

        [Space]
        [SerializeField] protected TMP_Text _textLatency;
        [SerializeField] private float _updateLatencyTextInterval = 1f;
        private SimulationTimer.SimulationTimer _timerUpdateLatencyText;

        [Header("Stress Test 1: Move Y")]
        [SerializeField] protected StressTestEssential _test_1;

        [Header("Stress Test 2: Move All Axis")]
        [SerializeField] protected StressTestEssential _test_2;

        [Header("Stress Test 3: Move Wander")]
        [SerializeField] protected StressTestEssential _test_3;

        [Header("Stress Test 4: Send RPCs")]
        [SerializeField] protected StressTestEssential _test_4;

        [System.Serializable]
        public struct StressTestEssential
        {
            public Button ButtonExecute;
            public int SpawnCount;
            public GameObject Prefab;
        }

        private void Start()
        {
            Initialize();
        }

        protected virtual void Initialize()
        {
            _test_1.ButtonExecute.onClick.AddListener(StressTest_1);
            _test_2.ButtonExecute.onClick.AddListener(StressTest_2);
            _test_3.ButtonExecute.onClick.AddListener(StressTest_3);
            _test_4.ButtonExecute.onClick.AddListener(StressTest_4);

            _buttonStartServer.onClick.AddListener(StartServer);
            _buttonStartClient.onClick.AddListener(StartClient);
        }

        protected virtual void StartClient() { }
        protected virtual void StartServer() { }
        private void StressTest_1() => StressTest(_test_1);
        private void StressTest_2() => StressTest(_test_2);
        private void StressTest_3() => StressTest(_test_3);
        private void StressTest_4() => StressTest(_test_4);
        protected virtual void StressTest(StressTestEssential stressTest) { }


        private void LateUpdate()
        {
            if (!_timerUpdateLatencyText.IsExpiredOrNotRunning()) return;

            UpdateNetworkStats();
            _timerUpdateLatencyText = SimulationTimer.SimulationTimer.CreateFromSeconds(_updateLatencyTextInterval);
        }

        protected virtual void UpdateNetworkStats() { }
    }
}
