#!/usr/bin/env python3
"""Fast orchestration/packaging regressions; fake players, never comparative CPU measurements."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


fleet = module('fleet', SCRIPTS / 'bench-fleet.py')
package = module('package', SCRIPTS / 'package-player.py')


def environment(**overrides):
    return dict(NETCODES='purrnet,fishnet,mirror,ngo,fusion', SESSIONS='10@20,100@20,100@60',
                RUNNER='ubuntu-latest', **overrides)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class Plans(unittest.TestCase):
    def test_defaults_match_original_workloads(self):
        plan = fleet.make_plan(environment())
        self.assertEqual(plan['expected'], 15)
        self.assertEqual(len(plan['workers']), 18)
        self.assertEqual([c['tick'] for c in plan['cases']], [20] * 10 + [60] * 5)
        for case in plan['cases']:
            self.assertEqual(sum(case['workers'].values()), case['total'])
            self.assertEqual(case['total'], 10 if case['id'] <= 5 else 100)
            self.assertEqual(case['workers'].get('loadgen-8'), None if case['id'] <= 5 else 6)

    def test_caps_order_and_runner_labels(self):
        env = environment(FUSION_MAX_CLIENTS='16', LOADGEN_RUNNER='loadgen-box', SERVER_RUNNER='server-box')
        env.update(NETCODES='fusion,mirror', SESSIONS='100@60,1@0')
        plan = fleet.make_plan(env)
        self.assertEqual(plan['netcodes'], ['mirror', 'fusion'])
        self.assertEqual([c['total'] for c in plan['cases']], [100, 16, 1, 1])
        self.assertEqual(plan['server_runner'], 'server-box')
        self.assertEqual(plan['cases'][1]['workers']['loadgen-1'], 6)
        self.assertEqual(plan['workers'][-1]['runner'], 'loadgen-box')
        self.assertEqual(plan['cases'][-1]['workers'], {'client-1': 1})

    def test_standalone_and_fractional_window(self):
        env = environment(SIZE='2', TICK_RATE='60', TAG='local', BENCH_SECONDS='2.5')
        env.update(SESSIONS='', NETCODES='fusion')
        plan = fleet.make_plan(env)
        self.assertEqual(plan['sessions'], [dict(size=2, tick=60, tag='local')])
        self.assertEqual(plan['expected'], 1)

    def test_invalid_inputs_fail_before_building(self):
        for key, value in [('SESSIONS', '0@20'), ('SESSIONS', '10@'), ('SESSIONS', '10@20,10'),
                           ('SESSIONS', '1@20;echo hi'), ('NETCODES', 'mirror,mirror'),
                           ('NETCODES', 'unknown'), ('LOADGEN_PROCS', '0'), ('MAX_PARALLEL', '2'),
                           ('BENCH_SECONDS', 'nan'), ('BENCH_SECONDS', '-1')]:
            with self.subTest(key=key, value=value):
                env = environment()
                env[key] = value
                with self.assertRaises(ValueError):
                    fleet.make_plan(env)


class Packages(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix' and os.geteuid() != 0,
                         'requires POSIX permissions and an unprivileged process')
    def test_default_destination_works_when_build_directory_is_not_writable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / 'build'
            source = build / 'StandaloneLinux64'
            for name in ('NetBench', 'GameAssembly.so', 'UnityPlayer.so', 'NetBench_Data/globalgamemanagers',
                         'NetBench_BackUpThisFolder_ButDontShipItWithYourGame/player.debug'):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
            (source / 'NetBench').chmod(0o755)
            original = package.inventory(source)
            # Reproduce the runner's inability to create a sibling under Docker's build directory.
            build.chmod(0o555)
            try:
                with self.assertRaises(PermissionError):
                    (build / 'player-package/runtime').mkdir(parents=True)
                command = [sys.executable, str(SCRIPTS / 'package-player.py')]
                result = subprocess.run(command + ['package', '--key', 'exact-key', '--revision', 'source-sha'],
                                        cwd=root, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = subprocess.run(command + ['verify', '--key', 'exact-key'],
                                        cwd=root, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                output = root / 'player-package'
                self.assertTrue((output / 'runtime/NetBench').is_file())
                self.assertEqual((output / 'runtime/NetBench').stat().st_mode, (source / 'NetBench').stat().st_mode)
                self.assertTrue((output / 'diagnostics/NetBench_BackUpThisFolder_ButDontShipItWithYourGame/player.debug').is_file())
                self.assertEqual(package.inventory(source), original)
                self.assertEqual(build.stat().st_mode & 0o777, 0o555)
                self.assertFalse((build / 'player-package').exists())
            finally:
                build.chmod(0o755)

    def test_runtime_unchanged_diagnostics_separate_and_cache_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'build'
            for name in ('NetBench', 'GameAssembly.so', 'UnityPlayer.so', 'NetBench_Data/globalgamemanagers',
                         'NetBench_Data/Plugins/plugin.so',
                         'NetBench_BackUpThisFolder_ButDontShipItWithYourGame/player.debug',
                         'NetBench_BackUpThisFolder_ButDontShipItWithYourGame/il2cppOutput/source.cpp'):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
            (source / 'NetBench').chmod(0o755)
            output = root / 'package'
            package.package(source, output, 'exact-key', 'source-sha')
            self.assertFalse((output / 'runtime/NetBench_BackUpThisFolder_ButDontShipItWithYourGame').exists())
            self.assertEqual((output / 'runtime/NetBench').read_bytes(), (source / 'NetBench').read_bytes())
            self.assertEqual((output / 'runtime/NetBench').stat().st_mode, (source / 'NetBench').stat().st_mode)
            self.assertTrue((output / 'diagnostics/NetBench_BackUpThisFolder_ButDontShipItWithYourGame/player.debug').exists())
            package.verify(output, 'exact-key')
            with self.assertRaises(ValueError):
                package.verify(output, 'different-inputs')
            with self.assertRaises(ValueError):
                package.package(source, output, 'exact-key', 'sha')
            (output / 'runtime/NetBench').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                package.verify(output, 'exact-key')


class Protocol(unittest.TestCase):
    def plan(self):
        env = environment()
        env.update(NETCODES='mirror', SESSIONS='1@20,2@60', MEASURED_CLIENTS='1', LOADGEN_PROCS='1')
        return fleet.make_plan(env)

    def test_no_advance_until_all_exit_idempotent_retry_and_final_release(self):
        plan = self.plan()
        state = fleet.Coordinator(plan)
        with ThreadPoolExecutor(max_workers=5) as pool:
            try:
                first = [pool.submit(state.next, w['id'], 0) for w in plan['workers']]
                state.wait_for(lambda: state.ready == state.workers, 2, 'readiness')
                state.publish(1)
                self.assertTrue(all(f.result(2)['case']['id'] == 1 for f in first))
                self.assertEqual(state.next('client-1', 0)['case']['id'], 1)  # Lost response retry.
                client = pool.submit(state.next, 'client-1', 1)
                state.wait_for(lambda: 'client-1' in state.acks[1], 2, 'client exit')
                with self.assertRaises(RuntimeError):
                    state.publish(2)
                self.assertFalse(client.done())
                loadgen = pool.submit(state.next, 'loadgen-1', 1)
                state.wait_for(lambda: state.acks[1] == state.workers, 2, 'all exits')
                state.publish(2)
                self.assertEqual(client.result(2)['case']['id'], 2)
                self.assertEqual(loadgen.result(2)['case']['id'], 2)
                last = [pool.submit(state.next, w['id'], 2, w['id'] != 'client-1') for w in plan['workers']]
                state.wait_for(lambda: state.acks[2] == state.workers, 2, 'last exits')
                state.publish(3)
                self.assertTrue(all(f.result(2)['kind'] == 'done' for f in last))
                self.assertEqual(state.failed, {('client-1', 2)})
                for worker in state.workers:
                    self.assertEqual(state.finish(worker)['kind'], 'released')
                self.assertEqual(state.finished, state.workers)
            finally:
                state.abort('test complete')

    def test_missing_runner_times_out_and_cannot_start_partial_fleet(self):
        state = fleet.Coordinator(self.plan())
        with ThreadPoolExecutor() as pool:
            response = pool.submit(state.next, 'client-1', 0)
            with self.assertRaises(RuntimeError):
                state.wait_for(lambda: state.ready == state.workers, 0.02, 'missing loadgen')
            self.assertEqual(response.result(1)['kind'], 'abort')
            with self.assertRaises(RuntimeError):
                state.publish(1)

    def test_reject_foreign_stale_or_future_ack(self):
        state = fleet.Coordinator(self.plan())
        for worker, completed in [('stranger', 0), ('client-1', 1), ('client-1', -1), ('client-1', True)]:
            with self.subTest(worker=worker, completed=completed), self.assertRaises(ValueError):
                state.next(worker, completed)
        with self.assertRaises(ValueError):
            state.finish('client-1')

    def test_http_long_poll_and_shutdown(self):
        state = fleet.Coordinator(self.plan())
        server = fleet.control_server(state, '127.0.0.1', 0)
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            with ThreadPoolExecutor() as pool:
                requests = [pool.submit(fleet.request, url, '/next', dict(worker=w, completed=0)) for w in state.workers]
                state.wait_for(lambda: state.ready == state.workers, 2, 'HTTP readiness')
                self.assertTrue(all(not r.done() for r in requests))
                state.abort('test abort')
                self.assertTrue(all(r.result(2)['kind'] == 'abort' for r in requests))
        finally:
            state.abort('cleanup')
            server.shutdown()
            server.server_close()


class Processes(unittest.TestCase):
    def test_player_arguments_preserve_workload_and_isolate_outputs(self):
        env = environment(BENCH_SECONDS='10', BENCH_OBJECTS='100', BENCH_CPUS='2-3',
                          SERVER_IP='100.1.2.3', GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='2',
                          PHOTON_REGION='eu', PHOTON_APP_ID='test-app')
        plan = fleet.make_plan(env)
        root = Path.cwd()
        for role in ('server', 'client', 'loadgen'):
            with self.subTest(role=role):
                cmd, log, result = fleet.player_command(plan['cases'][10], role, 2, 3, root, env)
                for flag, value in [('-benchSeconds', '10'), ('-benchObjects', '100'), ('-tickRate', '60'),
                                    ('-connectTimeout', '180'), ('-maxRunSeconds', '780'), ('-netIface', 'tailscale0')]:
                    self.assertEqual(cmd[cmd.index(flag) + 1], value)
                self.assertEqual('-loadgen' in cmd, role == 'loadgen')
                self.assertEqual('taskset' in cmd, role == 'server')
                self.assertEqual(result.parent, root / 'results/c100t60/purrnet')
                self.assertEqual(log.parent, root / 'logs/c100t60/purrnet')
                self.assertIn('--server-num=103', cmd)
        with patch.object(fleet.subprocess, 'check_output', return_value='[{"dev":"eth0"}]'):
            cmd, _, _ = fleet.player_command(plan['cases'][-1], 'client', 1, 1, root, env)
            self.assertEqual(cmd[cmd.index('-session') + 1], 'nb-123-2-c100t60')
            self.assertEqual(cmd[cmd.index('-netIface') + 1], 'eth0')
            self.assertEqual(cmd[cmd.index('-region') + 1], 'eu')

    def test_prepare_keeps_provenance_and_creates_every_session_directory(self):
        plan = fleet.make_plan(environment())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for netcode in plan['netcodes']:
                runtime = root / 'players' / f'player-{netcode}'
                runtime.mkdir(parents=True)
                (runtime / 'NetBench').write_bytes(b'fixture')
                (runtime / 'build-provenance.json').write_text('{"sourceRevision":"test"}')
            fleet.prepare(plan, root)
            for case in plan['cases']:
                self.assertTrue((root / 'results' / case['tag'] / case['netcode']).is_dir())
                self.assertTrue((root / 'logs' / case['tag'] / case['netcode']).is_dir())
            for netcode in plan['netcodes']:
                self.assertEqual(json.loads((root / 'results/build-provenance' / f'{netcode}.json').read_text()),
                                 dict(sourceRevision='test'))

    def test_process_failure_and_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = [([sys.executable, '-c', 'import sys; sys.exit(7)'], root / 'failure.log', root / 'result')]
            self.assertEqual(fleet.run_players(commands), [7])
            commands = [([sys.executable, '-c', 'import time; time.sleep(60)'], root / 'timeout.log', root / 'result')]
            self.assertEqual(fleet.run_players(commands, timeout=0.05), [124])

    @unittest.skipUnless(os.name == 'posix', 'Linux process-group cleanup')
    def test_orphan_child_is_killed_before_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pidfile = root / 'child.pid'
            source = ('import subprocess,sys,pathlib; '
                      'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); '
                      'pathlib.Path(sys.argv[1]).write_text(str(p.pid))')
            command = ([sys.executable, '-c', source, str(pidfile)], root / 'out.log', root / 'result')
            self.assertEqual(fleet.run_players([command]), [0])
            pid = int(pidfile.read_text())
            # An unreaped zombie may briefly remain in /proc; it cannot execute or affect a measurement.
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                stat = Path(f'/proc/{pid}/stat')
                if not stat.exists() or stat.read_text().split()[2] == 'Z':
                    break
                time.sleep(0.01)
            else:
                self.fail('Child is still running after acknowledgement would have been sent')

    def test_whole_suite_real_processes_and_http_no_case_overlap(self):
        env = environment()
        env.update(NETCODES='mirror,fishnet', SESSIONS='1@20,4@60,2@20', MEASURED_CLIENTS='1', LOADGEN_PROCS='2',
                   CONTROL_BIND='127.0.0.1', SERVER_IP='127.0.0.1', PHASE_PORT=str(free_port()))
        plan = fleet.make_plan(env)
        active, observed, lock = {}, [], threading.Lock()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for case in plan['cases']:
                for folder in ('logs', 'results'):
                    (root / folder / case['tag'] / case['netcode']).mkdir(parents=True, exist_ok=True)

            def command(case, role, index, process, root, env):
                name = f'{role}-{index}-{process}'
                result = root / 'results' / case['tag'] / case['netcode'] / f'{name}.json'
                log = root / 'logs' / case['tag'] / case['netcode'] / f'{name}.log'
                script = ('import os,sys,time,pathlib,json; time.sleep(float(sys.argv[2])); '
                          'pathlib.Path(sys.argv[1]).write_text(json.dumps({"pid":os.getpid()}))')
                cmd = [sys.executable, '-c', script, str(result), '0.01' if role == 'server' else '0.04', str(case['id'])]
                return cmd, log, result

            def execute(commands):
                if not commands:
                    return []
                case_id = int(commands[0][0][-1])
                with lock:
                    self.assertTrue(all(c == case_id for c in active))
                    active[case_id] = active.get(case_id, 0) + 1
                    observed.append(case_id)
                try:
                    return fleet.run_players(commands)
                finally:
                    with lock:
                        active[case_id] -= 1
                        if not active[case_id]:
                            del active[case_id]

            with patch.object(fleet, 'player_command', command), patch.object(fleet.subprocess, 'check_output', return_value=''):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    server = pool.submit(fleet.run_server, plan, root, env, execute)
                    workers = [pool.submit(fleet.run_worker, plan, root, dict(env, WORKER_ID=w['id']), execute)
                               for w in plan['workers']]
                    self.assertEqual(server.result(20), 0)
                    self.assertTrue(all(w.result(2) == 0 for w in workers))
            self.assertEqual(sorted(set(observed)), list(range(1, 7)))
            results = list((root / 'results').rglob('*.json'))
            self.assertEqual(len(results), sum(1 + c['total'] for c in plan['cases']))
            self.assertEqual(len({json.loads(r.read_text())['pid'] for r in results}), len(results))


if __name__ == '__main__':
    unittest.main(verbosity=2)
