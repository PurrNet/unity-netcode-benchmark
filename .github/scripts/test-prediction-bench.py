#!/usr/bin/env python3
"""Prediction matrix, lifecycle barriers and report integrity regressions."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import signal
from pathlib import Path
import tempfile
from types import SimpleNamespace
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
ab = module('prediction_ab', 'prediction-ab.py')


class HostSnapshotTests(unittest.TestCase):
    def test_linux_snapshot_preserves_models_frequency_and_raw_scheduler_counters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc, sysfs = root / 'proc', root / 'sys'
            files = {
                proc / 'cpuinfo': 'processor: 0\nmodel name: Example CPU\ncpu MHz: 3000\n\n'
                                  'processor: 1\nmodel name: Example CPU\ncpu MHz: 2900.5\n',
                proc / 'stat': 'cpu 1 2 3 4 5 6 7 8 9 10\ncpu0 1 2 3\n',
                proc / 'sys/kernel/random/boot_id': 'example-boot\n',
                sysfs / 'devices/system/clocksource/clocksource0/current_clocksource': 'tsc\n',
            }
            for path, value in files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value)
            snapshot = bench.host_snapshot(proc, sysfs)
            self.assertEqual(snapshot['cpuModels'], ['Example CPU'])
            self.assertEqual(snapshot['cpuMhz'], [3000, 2900.5])
            self.assertEqual(snapshot['schedulerCpuTicks']['steal'], 8)
            self.assertEqual(snapshot['schedulerCpuTicks']['guestNice'], 10)
            self.assertEqual(snapshot['bootId'], 'example-boot')
            self.assertEqual(snapshot['clockSource'], 'tsc')

    def test_unavailable_host_files_do_not_prevent_a_benchmark(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = bench.host_snapshot(Path(directory) / 'proc', Path(directory) / 'sys')
            self.assertEqual(snapshot['cpuModels'], [])
            self.assertEqual(snapshot['cpuMhz'], [])
            self.assertIsNone(snapshot['schedulerCpuTicks'])
            self.assertIsNone(snapshot['clockSource'])
            self.assertIsNone(snapshot['bootId'])

    def test_malformed_optional_counters_stay_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'cpuinfo').write_text('cpu MHz: unavailable\ncpu MHz: nan\ncpu MHz: -1\n')
            (root / 'stat').write_text('cpu invalid\n')
            snapshot = bench.host_snapshot(root, root)
            self.assertEqual(snapshot['cpuMhz'], [])
            self.assertIsNone(snapshot['schedulerCpuTicks'])


class RevisionComparisonTests(unittest.TestCase):
    def args(self, **overrides):
        values = dict(baseline=Path('baseline'), candidate=Path('candidate'), output=Path('results'),
                      solution='purrdiction', clients='4', ticks='60', objects='128', repeats=3, seconds=20, warmup=20, dry_run=False, diagnostics='auto')
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_order_alternates_and_sampling_is_identical(self):
        commands = ab.commands(self.args())
        self.assertEqual([c[c.index('--players') + 1] for c in commands],
                         ['baseline', 'candidate', 'candidate', 'baseline', 'baseline', 'candidate'])
        for command in commands:
            self.assertEqual(command[command.index('--repeats') + 1], '1')
            self.assertEqual(command[command.index('--seconds') + 1], '20')
            self.assertEqual(command[command.index('--warmup') + 1], '20')

    def test_failure_is_reported_and_remaining_revisions_are_measured(self):
        execute = Mock(side_effect=[SimpleNamespace(returncode=1), SimpleNamespace(returncode=0)])
        self.assertEqual(ab.run(self.args(repeats=1), execute), 1)
        self.assertEqual(execute.call_count, 2)

    def test_owned_policy_is_identical_for_both_revisions(self):
        commands = ab.commands(self.args(solution='purrdiction-owned'))
        self.assertEqual([c[c.index('--solutions') + 1] for c in commands],
                         ['purrdiction-owned'] * 6)
        self.assertEqual([c[c.index('--players') + 1] for c in commands],
                         ['baseline', 'candidate', 'candidate', 'baseline', 'baseline', 'candidate'])

    def test_mixed_or_unrelated_adapters_never_start_a_player(self):
        for solution in ('purrdiction,purrdiction-owned', 'fishnet', 'fusion', ''):
            execute = Mock()
            with self.assertRaises(ValueError):
                ab.run(self.args(solution=solution), execute)
            execute.assert_not_called()

    def test_diagnostics_mode_applies_to_both_revisions(self):
        for mode in ('on', 'off', 'auto'):
            for command in ab.commands(self.args(diagnostics=mode)):
                self.assertEqual(command[command.index('--diagnostics') + 1], mode)

    def test_invalid_matrix_never_starts_a_player(self):
        execute = Mock()
        with self.assertRaises(ValueError):
            ab.run(self.args(repeats=0), execute)
        execute.assert_not_called()

    def test_invalid_diagnostics_never_starts_a_player(self):
        execute = Mock()
        with self.assertRaises(ValueError):
            ab.run(self.args(diagnostics='invalid'), execute)
        execute.assert_not_called()


class ArtifactLayoutTests(unittest.TestCase):
    def test_purrdiction_overrides_keep_other_frozen_players_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, override = root / 'original', root / 'candidate'
            names = ('purrdiction', 'purrdiction-owned', 'fishnet', 'fusion')
            for name in names:
                player = source / ('prediction-player-' + name)
                player.mkdir(parents=True)
                (player / 'PredictionBench').write_text('old-' + name)
                (player / 'stale-only.txt').write_text('old')
            for name in names[:2]:
                player = override / ('prediction-player-' + name)
                player.mkdir(parents=True)
                (player / 'PredictionBench').write_text('new-' + name)
                (player / 'prediction-provenance.json').write_text('candidate-' + name)
            arranger.arrange(source, root / 'players', ','.join(names), override)
            for name in names:
                player = root / 'players' / name
                self.assertEqual((player / 'PredictionBench').read_text(),
                                 ('new-' if name in names[:2] else 'old-') + name)
                self.assertEqual((player / 'stale-only.txt').exists(), name not in names[:2])
                if name in names[:2]:
                    self.assertEqual((player / 'prediction-provenance.json').read_text(), 'candidate-' + name)

    def test_flat_sources_are_unambiguous_with_one_adapter_each(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, override = root / 'original', root / 'candidate'
            source.mkdir(); override.mkdir()
            (source / 'PredictionBench').write_text('fishnet')
            (override / 'PredictionBench').write_text('purrdiction')
            arranger.arrange(source, root / 'players', 'purrdiction,fishnet', override)
            for name in ('purrdiction', 'fishnet'):
                self.assertEqual((root / 'players' / name / 'PredictionBench').read_text(), name)

    def test_missing_override_never_falls_back_to_original_purrdiction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, override = root / 'original', root / 'candidate'
            player = source / 'prediction-player-purrdiction'
            player.mkdir(parents=True)
            (player / 'PredictionBench').write_text('old')
            with self.assertRaises(FileNotFoundError):
                arranger.arrange(source, root / 'players', 'purrdiction', override)
            self.assertFalse((root / 'players').exists())

    def test_unused_override_fails_before_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                arranger.arrange(root / 'original', root / 'players', 'fishnet', root / 'candidate')
            self.assertFalse((root / 'players').exists())

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
            for name in ('purrdiction', 'purrdiction-owned', 'fishnet'):
                player = source / ('prediction-player-' + name)
                player.mkdir(parents=True)
                (player / 'PredictionBench').write_text(name)
            arranger.arrange(source, root / 'players', 'purrdiction,purrdiction-owned,fishnet')
            for name in ('purrdiction', 'purrdiction-owned', 'fishnet'):
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
    def test_repeats_rotate_adapter_positions_and_preserve_every_case(self):
        solutions = ['purrdiction', 'purrdiction-owned', 'fishnet', 'fusion']
        cases = bench.make_plan(','.join(solutions), '2,4', '20,60', '32,128', 4, 20, 20)
        self.assertEqual([case['id'] for case in cases], list(range(1, 129)))
        keys = {(c['solution'], c['clients'], c['tickRate'], c['objects'], c['repeat']) for c in cases}
        self.assertEqual(len(keys), 128)
        for start in range(0, len(cases), 16):
            block = cases[start:start + 16]
            for position in range(4):
                self.assertEqual({block[r * 4 + position]['solution'] for r in range(4)}, set(solutions))
            for r in range(4):
                repeat = block[r * 4:r * 4 + 4]
                self.assertEqual([c['solution'] for c in repeat], solutions[r:] + solutions[:r])
                self.assertTrue(all(c['repeat'] == r + 1 for c in repeat))

    def test_owned_and_full_world_variants_are_separate_cases(self):
        cases = bench.make_plan('purrdiction,purrdiction-owned', '4', '60', '128', 1, 20, 20)
        self.assertEqual([case['solution'] for case in cases], ['purrdiction', 'purrdiction-owned'])

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


class SnapshotValidation(unittest.TestCase):
    def test_old_players_cannot_silently_ignore_snapshot_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'not captured'):
                bench.validate_memory_snapshots({'server': {}, 'client-1': {}}, Path(temp))

    def test_both_nonempty_artifacts_and_matching_paths_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reports = {peer: {'memorySnapshotRequested': True, 'memorySnapshotSucceeded': True,
                'memorySnapshotPath': str(root / (peer + '.snap'))} for peer in ('server', 'client-1')}
            for peer in reports: (root / (peer + '.snap')).write_bytes(b'example artifact')
            bench.validate_memory_snapshots(reports, root)
            (root / 'client-1.snap').write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'artifact'):
                bench.validate_memory_snapshots(reports, root)
            (root / 'client-1.snap').write_bytes(b'example artifact')
            reports['client-1']['memorySnapshotPath'] = str(root / 'unrelated.snap')
            with self.assertRaisesRegex(ValueError, 'artifact'):
                bench.validate_memory_snapshots(reports, root)


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
    def test_explicit_diagnostics_modes_must_be_honored_by_every_peer(self):
        for mode in ('on', 'off'):
            case, reports = fixture()
            case['diagnostics'] = mode
            with self.assertRaisesRegex(ValueError, 'honor'):
                bench.validate_case(case, reports)
            for peer in reports.values():
                peer['detailedDiagnostics'] = mode == 'on'
            self.assertTrue(bench.validate_case(case, reports))
            reports['client-1']['detailedDiagnostics'] = mode != 'on'
            with self.assertRaisesRegex(ValueError, 'Mismatched'):
                bench.validate_case(case, reports)

    def test_diagnostics_flags_require_real_booleans(self):
        for value in ('false', 0, 1):
            case, reports = fixture()
            reports['client-1']['detailedDiagnostics'] = value
            with self.assertRaisesRegex(ValueError, 'Mismatched'):
                bench.validate_case(case, reports)

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
    def test_diagnostics_modes_and_legacy_reports_are_never_pooled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, mode in enumerate((True, False, None)):
                parent = root / str(index)
                parent.mkdir()
                self.make_run(parent)
                if mode is not None:
                    for path in (parent / 'run/case-0001').glob('*.json'):
                        peer = json.loads(path.read_text())
                        peer['detailedDiagnostics'] = mode
                        path.write_text(json.dumps(peer))
            data = reporter.render(root, root / 'report')
            self.assertTrue(data['complete'])
            self.assertEqual(len(data['groups']), 6)
            self.assertEqual({row['detailedDiagnostics'] for row in data['groups']}, {True, False, None})
            self.assertTrue(all(row['repeats'] == 1 for row in data['groups']))

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

    def test_owned_and_full_world_results_are_never_pooled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for solution in ('purrdiction', 'purrdiction-owned'):
                variant = root / solution
                variant.mkdir()
                self.make_run(variant)
                path = variant / 'run/manifest.json'
                manifest = json.loads(path.read_text())
                manifest['cases'][0]['solution'] = solution
                path.write_text(json.dumps(manifest))
                for path in (variant / 'run/case-0001').glob('*.json'):
                    peer = json.loads(path.read_text())
                    peer['solution'] = solution
                    peer['predictionScope'] = solution
                    path.write_text(json.dumps(peer))
            data = reporter.render(root, root / 'report')
            self.assertTrue(data['complete'])
            self.assertEqual(len(data['groups']), 4)
            self.assertEqual({row['solution'] for row in data['groups']}, {'purrdiction', 'purrdiction-owned'})
            self.assertTrue(all(row['repeats'] == 1 for row in data['groups']))

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
    def test_owned_variant_reuses_pinned_source_but_has_distinct_policy_and_adapter_hash(self):
        adapter_source = (prepare.ROOT / 'prediction/Adapters/purrdiction/PurrDictionPredictionAdapter.cs').read_text()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = {
                'purrnet/Assets/_Benchmark/Prefabs/NetworkManager.prefab': 'manager',
                'purrnet/Packages/manifest.json': '{"dependencies": {}}',
                'purrnet/Packages/packages-lock.json': '{"dependencies": {}}',
                'purrnet/ProjectSettings/ProjectVersion.txt': 'm_EditorVersion: test',
                'source/Assets/PurrDiction/package.json': '{"version": "test"}',
                'source/Packages/manifest.json': '{"dependencies": {"dev.purrnet.purrnet": "https://example.com/purrnet.git#pinned"}}',
                'prediction/Shared/Runner.cs': 'shared harness',
                'prediction/Adapters/purrdiction/PurrDictionPredictionAdapter.cs': adapter_source,
                'Shared/com.purrnet.netbench/Runtime/LoadSampler.cs': '    public struct LoadStats {}',
            }
            for directory in ('Runtime', 'Codegen', 'Editor'):
                files[f'source/Assets/PurrDiction/{directory}/Code.cs'] = 'package code'
                files[f'source/Assets/PurrDiction/{directory}.meta'] = 'guid: package'
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            with patch.object(prepare, 'ROOT', root), patch.object(prepare, 'git', side_effect=lambda root, *args: '' if args[0] == 'status' else 'b' * 40):
                full = prepare.prepare('purrdiction', root / 'full', root / 'source')
                owned = prepare.prepare('purrdiction-owned', root / 'owned', root / 'source')
            self.assertEqual(full['predictionCommit'], owned['predictionCommit'])
            self.assertEqual(full['purrnetDependency'], owned['purrnetDependency'])
            self.assertEqual(full['predictionPolicy'], 'FullPrediction')
            self.assertEqual(owned['predictionPolicy'], 'PredictedIfOwned')
            adapter_path = 'Adapter/PurrDictionPredictionAdapter.cs'
            self.assertNotEqual(full['adapterSha256'][adapter_path], owned['adapterSha256'][adapter_path])
            self.assertTrue((root / 'owned/Assets/PredictionBench' / adapter_path).read_text().startswith('#define PURRDICTION_OWNED_ONLY\n'))
            self.assertFalse((root / 'full/Assets/PredictionBench' / adapter_path).read_text().startswith('#define'))

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
