#!/usr/bin/env python3
"""Prediction matrix, lifecycle barriers and report integrity regressions."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import signal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


bench = module('prediction_bench', 'prediction-bench.py')
reporter = module('prediction_report', 'prediction-report.py')
prepare = module('prediction_prepare', 'prediction-prepare.py')
arranger = module('prediction_arrange', 'prediction-arrange.py')


class ArtifactLayoutTests(unittest.TestCase):
    def test_single_artifact_flat_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'downloaded'
            source.mkdir()
            (source / 'PredictionBench').write_bytes(b'player')
            (source / 'PredictionBench_Data').mkdir()
            (source / 'PredictionBench_Data/data').write_bytes(b'data')
            arranger.arrange(source, root / 'players', 'purrdiction')
            self.assertEqual((root / 'players/purrdiction/PredictionBench').read_bytes(), b'player')
            self.assertEqual((root / 'players/purrdiction/PredictionBench_Data/data').read_bytes(), b'data')

    def test_multi_artifact_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'downloaded'
            for name in ('purrdiction', 'fishnet'):
                player = source / ('prediction-player-' + name)
                player.mkdir(parents=True)
                (player / 'PredictionBench').write_text(name)
            arranger.arrange(source, root / 'players', 'purrdiction,fishnet')
            for name in ('purrdiction', 'fishnet'):
                self.assertEqual((root / 'players' / name / 'PredictionBench').read_text(), name)

    def test_ambiguous_flat_layout_and_missing_players_fail_before_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'downloaded'
            source.mkdir()
            with self.assertRaises(FileNotFoundError):
                arranger.arrange(source, root / 'players', 'purrdiction')
            (source / 'PredictionBench').write_bytes(b'player')
            with self.assertRaises(ValueError):
                arranger.arrange(source, root / 'players', 'purrdiction,fishnet')
            self.assertFalse((root / 'players').exists())


def fixture():
    case = bench.make_plan('fishnet', '1', '60', '2', 1, 2, 1)[0]
    reports = {}
    for peer, role in [('server', 'server'), ('client-1', 'client')]:
        reports[peer] = {'success': True, 'schemaVersion': 1, 'suite': 'prediction',
            'solution': 'fishnet', 'workload': bench.WORKLOAD, 'peer': peer, 'role': role,
            'predictionScope': 'state forwarding', 'replayDefinition': 'native replay',
            'provenanceJson': '{}', 'linuxMetricsAvailable': True, 'scriptingBackend': 'IL2CPP', 'developmentBuild': True,
            'config': {key: case[key] for key in ('clients', 'objects', 'tickRate', 'seconds', 'warmupSeconds')},
            'actualTickRate': 60, 'observedObjects': 2, 'ownedObjects': 2 if role == 'client' else 0,
            'requestedFrameCap': 60, 'actualFrameCap': 60,
            'forwardCalls': 120, 'replayCalls': 60, 'ownedForwardCalls': 120 if role == 'client' else 0,
            'load': {'wallSeconds': 2, 'frameCount': 120, 'cpuPercent': 10, 'p95FrameMs': 17,
                'p99FrameMs': 18, 'managedHeapBytes': 1048576, 'peakRssBytes': 2097152,
                'gcAllocBytes': 100, 'gcAllocEstimated': False},
            'finalState': [{'index': i, 'owned': role == 'client', 'state': dict(x=3, z=-2,
                lastSequence=100, appliedInputs=100, hash=123, a=1, b=2, c=3)} for i in range(2)]}
    return case, reports


class Matrix(unittest.TestCase):
    def test_independent_dimensions_and_fixed_population(self):
        cases = bench.make_plan('purrdiction,fishnet,fusion', '1,2,4', '20,60', '32,128', 3, 10, 3)
        self.assertEqual(len(cases), 108)
        self.assertEqual({case['objects'] for case in cases}, {32, 128})
        self.assertTrue(all(case['workload'] == 'sequenced-state-v1' for case in cases))

    def test_rejects_replication_netcode_names(self):
        with self.assertRaises(ValueError): bench.make_plan('purrnet', '1', '60', '32', 1, 10, 3)

    def test_rejects_invalid_matrix(self):
        for options in [('fishnet,fishnet', '1', '60', '32', 1, 10, 3),
                        ('fishnet', '1,1', '60', '32', 1, 10, 3),
                        ('fishnet', '4', '60', '2', 1, 10, 3),
                        ('fishnet', '1', '0', '32', 1, 10, 3),
                        ('fishnet', '1', '60', '32', 1, float('nan'), 3)]:
            with self.subTest(options=options), self.assertRaises(ValueError): bench.make_plan(*options)


class Barriers(unittest.TestCase):
    def test_all_peers_required_and_phase_order(self):
        barrier = bench.Barrier(['server', 'client-1'], 2)
        with ThreadPoolExecutor() as pool:
            first = pool.submit(barrier.arrive, 'ready', 'server')
            with barrier.condition:
                barrier.condition.wait_for(lambda: 'server' in barrier.arrivals['ready'], 1)
            self.assertFalse(first.done())
            barrier.arrive('ready', 'client-1')
            first.result(timeout=1)
        with self.assertRaises(ValueError): barrier.arrive('done', 'server')
        with self.assertRaises(ValueError): barrier.arrive('ready', 'server')

    def test_aborted_barrier_unblocks_waiters(self):
        barrier = bench.Barrier(['server', 'client-1'], 10)
        with ThreadPoolExecutor() as pool:
            waiter = pool.submit(barrier.arrive, 'ready', 'server')
            barrier.abort()
            with self.assertRaises(TimeoutError): waiter.result(timeout=1)

    def test_unknown_peer_cannot_release_barrier(self):
        barrier = bench.Barrier(['server'], .1)
        with self.assertRaises(ValueError): barrier.arrive('ready', 'client-1')


class Validation(unittest.TestCase):
    def test_complete_authoritative_convergence(self):
        self.assertTrue(bench.validate_case(*fixture()))

    def test_missing_peer_rejected(self):
        case, reports = fixture()
        reports.pop('client-1')
        with self.assertRaises(ValueError): bench.validate_case(case, reports)

    def test_different_final_state_rejected(self):
        case, reports = fixture()
        reports['client-1']['finalState'][0]['state']['hash'] += 1
        with self.assertRaisesRegex(ValueError, 'differs from authority'): bench.validate_case(case, reports)

    def test_duplicate_final_object_rejected(self):
        case, reports = fixture()
        reports['client-1']['finalState'][1]['index'] = 0
        with self.assertRaisesRegex(ValueError, 'duplicate or missing'): bench.validate_case(case, reports)

    def test_replication_without_owned_prediction_rejected(self):
        case, reports = fixture()
        reports['client-1']['ownedForwardCalls'] = 0
        with self.assertRaisesRegex(ValueError, 'owned forward'): bench.validate_case(case, reports)

    def test_wrong_tick_rate_and_incomplete_window_rejected(self):
        for field, value in [('actualTickRate', 20), ('actualFrameCap', 500), ('success', False)]:
            case, reports = fixture()
            reports['client-1'][field] = value
            with self.assertRaises(ValueError): bench.validate_case(case, reports)
        case, reports = fixture()
        reports['client-1']['load']['wallSeconds'] = .1
        with self.assertRaisesRegex(ValueError, 'window'): bench.validate_case(case, reports)

    def test_missing_ownership_and_inactive_inputs_rejected(self):
        case, reports = fixture()
        reports['client-1']['finalState'][1]['owned'] = False
        reports['client-1']['ownedObjects'] = 1
        with self.assertRaisesRegex(ValueError, 'exactly one owner'): bench.validate_case(case, reports)
        case, reports = fixture()
        for data in reports.values(): data['finalState'][0]['state']['appliedInputs'] = 0
        with self.assertRaisesRegex(ValueError, 'inactive'): bench.validate_case(case, reports)


class Reports(unittest.TestCase):
    def make_run(self, root, failed=False, linux=True):
        case, reports = fixture()
        run = root / 'run'
        run.mkdir()
        (run / 'manifest.json').write_text(json.dumps({'schemaVersion': 1, 'suite': 'prediction', 'machine': {'cpu': 'test'}, 'cases': [case]}))
        (run / 'failures.json').write_text(json.dumps([{'id': 1, 'error': 'exit failure'}] if failed else []))
        folder = run / 'case-0001'
        folder.mkdir()
        for peer, data in reports.items():
            data['linuxMetricsAvailable'] = linux
            (folder / (peer + '.json')).write_text(json.dumps(data))

    def test_failed_execution_is_not_scored_even_with_valid_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_run(root, failed=True)
            data = reporter.render(root, root / 'report')
            self.assertFalse(data['complete'])
            self.assertEqual(data['groups'], [])

    def test_windows_missing_cpu_is_not_reported_as_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_run(root, linux=False)
            data = reporter.render(root, root / 'report')
            self.assertTrue(data['complete'])
            self.assertTrue(all(row['cpuPercent'] is None for row in data['groups']))
            self.assertIn('unavailable', (root / 'report/latest.md').read_text())

    def test_windows_cpu_clock_is_scored_while_rss_stays_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_run(root, linux=False)
            for path in (root / 'run/case-0001').glob('*.json'):
                peer = json.loads(path.read_text())
                peer['cpuMetricsAvailable'] = True
                path.write_text(json.dumps(peer))
            data = reporter.render(root, root / 'report')
            self.assertTrue(data['complete'])
            self.assertTrue(all(row['cpuPercent'] == 10 for row in data['groups']))
            self.assertTrue(all(row['peakRssBytes'] is None for row in data['groups']))

    def test_different_source_hashes_are_not_pooled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_run(root)
            source = root / 'run'
            target = root / 'second'
            import shutil
            shutil.copytree(source, target)
            for peer in ('server', 'client-1'):
                path = target / 'case-0001' / (peer + '.json')
                data = json.loads(path.read_text())
                data['provenanceJson'] = '{"revision":"different"}'
                path.write_text(json.dumps(data))
            result = reporter.render(root, root / 'report')
            self.assertEqual(len(result['groups']), 4)

    def test_runtime_file_changes_are_not_pooled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_run(root)
            import shutil
            shutil.copytree(root / 'run', root / 'second')
            for name, fingerprint in [('run', 'before'), ('second', 'after')]:
                path = root / name / 'manifest.json'
                data = json.loads(path.read_text())
                data['players'] = {'fishnet': {'runtimeSha256': {'GameAssembly.so': fingerprint}}}
                path.write_text(json.dumps(data))
            result = reporter.render(root, root / 'report')
            self.assertEqual(len(result['groups']), 4)


class Preparation(unittest.TestCase):
    def test_isolated_project_preserves_manager_guid_and_pins_git_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = {
                'fishnet/Assets/_Benchmark/Prefab/NetworkManager.prefab': 'manager',
                'fishnet/Assets/_Benchmark/Prefab/NetworkManager.prefab.meta': 'guid: existing-guid',
                'fishnet/Assets/_Benchmark/Prefab/OldWorkload.prefab': 'old workload',
                'fishnet/Assets/_Benchmark/Scripts/OldWorkload.cs': 'old code',
                'fishnet/Packages/manifest.json': json.dumps({'dependencies': {'com.purrnet.netbench': 'file:../../Shared', 'com.timer': 'https://example.com/timer.git'}}),
                'fishnet/Packages/packages-lock.json': json.dumps({'dependencies': {'com.timer': {'source': 'git', 'hash': 'a' * 40}}}),
                'fishnet/ProjectSettings/ProjectVersion.txt': 'm_EditorVersion: test',
                'prediction/Shared/Runner.cs': 'shared harness',
                'prediction/Adapters/fishnet/Adapter.cs': 'native adapter',
                'Shared/com.purrnet.netbench/Runtime/LoadSampler.cs': '    public struct LoadStats {}'
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            output = root / 'generated'
            with patch.object(prepare, 'ROOT', root), patch.object(prepare, 'git', side_effect=lambda root, *args: '' if args[0] == 'status' else 'b' * 40):
                prepare.prepare('fishnet', output)
                with self.assertRaisesRegex(ValueError, 'overwrite'): prepare.prepare('fishnet', output)
            self.assertEqual((output / 'Assets/_Benchmark/Prefab/NetworkManager.prefab.meta').read_text(), 'guid: existing-guid')
            self.assertFalse((output / 'Assets/_Benchmark/Scripts').exists())
            self.assertFalse((output / 'Assets/_Benchmark/Prefab/OldWorkload.prefab').exists())
            dependencies = json.loads((output / 'Packages/manifest.json').read_text())['dependencies']
            self.assertEqual(dependencies['com.timer'], 'https://example.com/timer.git#' + 'a' * 40)
            self.assertNotIn('com.purrnet.netbench', dependencies)
            self.assertEqual((root / 'fishnet/Packages/manifest.json').read_text(), files['fishnet/Packages/manifest.json'])

    def test_exited_linux_wrapper_still_cleans_descendants(self):
        process = Mock(pid=12345)
        process.poll.return_value = 0
        with patch.object(bench.os, 'name', 'posix'), patch.object(bench.os, 'killpg', create=True) as kill, patch.object(bench.signal, 'SIGKILL', 9, create=True):
            bench.stop_process(process)
        self.assertEqual([call.args for call in kill.call_args_list], [(12345, signal.SIGTERM), (12345, 9)])


if __name__ == '__main__':
    unittest.main()
