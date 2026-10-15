import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('prediction-profile.py')
SPEC = importlib.util.spec_from_file_location('prediction_profile', SCRIPT)
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


class NativeProfileTests(unittest.TestCase):
    def test_stack_summary_exposes_thread_coverage_including_samples_without_stacks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'samples.txt'
            path.write_text('Unity Main Thre 123 1.000: 1001001 cpu-clock:\n'
                            '\t  1234 MainWork+0x1 (/GameAssembly.so)\n\n'
                            'ReceiveThread(1 124 1.100: 1001001 cpu-clock:\n'
                            '\t  5678 ReceiveWork+0x2 (/libc.so)\n\n'
                            'ReceiveThread(1 124 1.200: 1001001 cpu-clock:\n\n')
            summary = PROFILE.summarize(path)
            self.assertEqual(summary['samples'], 2)
            self.assertEqual(summary['sampleHeaders'], 3)
            threads = {row['tid']: row for row in summary['byThread']}
            self.assertEqual(threads[123], dict(tid=123, name='Unity Main Thre', samples=1, stackSamples=1))
            self.assertEqual(threads[124], dict(tid=124, name='ReceiveThread(1', samples=2, stackSamples=1))

    def test_capture_scope_selects_process_or_main_thread(self):
        for all_threads, selector in ((False, '-t'), (True, '-p')):
            command = PROFILE.recording_command(Path('perf'), 123, Path('out.data'), 25, all_threads)
            self.assertEqual(command[command.index(selector) + 1], '123')
            self.assertNotIn('-p' if selector == '-t' else '-t', command)
            self.assertEqual(command[-3:], ['--', 'sleep', '25'])

    def test_dry_run_records_actual_requested_scope(self):
        for flags, expected in (([], False), (['--all-threads'], True)):
            result = subprocess.run([sys.executable, str(SCRIPT), '--dry-run', '--player-run', '123',
                                     '--players', 'unused', *flags], check=True, capture_output=True, text=True)
            settings = json.loads(result.stdout)
            self.assertEqual(settings['allThreads'], expected)
            self.assertIn('all threads' if expected else 'main thread', settings['scope'])
            self.assertTrue(settings['diagnosticOnly'])

    def test_proc_thread_names_with_parentheses_and_exiting_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            thread = root / '123/task/456'
            thread.mkdir(parents=True)
            fields = ['S'] + ['0'] * 49
            fields[11], fields[12], fields[19] = '20', '10', '999'
            (thread / 'stat').write_text('456 (Net (UDP) Rx) ' + ' '.join(fields))
            (thread.parent / '457').mkdir()  # Exited before its stat could be read.
            self.assertEqual(PROFILE.thread_cpu(123, root),
                             {'456': {'name': 'Net (UDP) Rx', 'ticks': 30, 'startTicks': 999}})

    def test_cpu_deltas_handle_renames_new_threads_and_missing_final_counters(self):
        before = {'1': dict(name='main', ticks=10, startTicks=1),
                  '2': dict(name='old worker', ticks=30, startTicks=2),
                  '3': dict(name='exited', ticks=40, startTicks=3),
                  '4': dict(name='reused', ticks=50, startTicks=4)}
        after = {'1': dict(name='main', ticks=60, startTicks=1),
                 '2': dict(name='renamed worker', ticks=50, startTicks=2),
                 '4': dict(name='reused', ticks=10, startTicks=5),
                 '5': dict(name='new', ticks=5, startTicks=6)}
        result = PROFILE.thread_cpu_delta(before, after, 100)
        rows = {row['tid']: row for row in result['threads']}
        self.assertEqual(rows[1]['cpuSeconds'], .5)
        self.assertEqual(rows[2]['cpuSeconds'], .2)
        self.assertTrue(rows[2]['presentAtStart'])
        self.assertEqual(rows[4]['cpuSeconds'], .1)
        self.assertFalse(rows[4]['presentAtStart'])
        self.assertEqual(rows[5]['cpuSeconds'], .05)
        self.assertEqual(result['exitedThreadIds'], [3])


if __name__ == '__main__':
    unittest.main()
