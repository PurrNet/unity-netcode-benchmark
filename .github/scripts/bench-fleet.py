#!/usr/bin/env python3
"""Run a sequential benchmark suite on one prepared fleet; no orchestration polling in players."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.request import Request, urlopen

import bench_resources as resources

NETCODES = ('purrnet', 'fishnet', 'mirror', 'ngo', 'fusion')
# Cover the existing 15-minute process watchdog, its kill grace and delayed client startup.
# This is a coordination ceiling, not a shorter cutoff on a player's own measurement window.
CASE_EXIT_BUDGET = 900 + 10 + 180


def positive(value, name, minimum=1):
    if not re.fullmatch(r'\d+', str(value)) or int(value) < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return int(value)


def make_plan(env):
    netcodes = [n.strip() for n in env['NETCODES'].split(',')]
    if not netcodes or len(set(netcodes)) != len(netcodes) or any(n not in NETCODES for n in netcodes):
        raise ValueError('Select unique, known netcodes')
    # Preserve the requested order, with Fusion last as before.
    netcodes = [n for n in netcodes if n != 'fusion'] + (['fusion'] if 'fusion' in netcodes else [])
    measured = positive(env.get('MEASURED_CLIENTS', '10'), 'measured_clients', 0)
    procs = positive(env.get('LOADGEN_PROCS', '12'), 'loadgen_procs')
    cap = positive(env.get('FUSION_MAX_CLIENTS', '100'), 'fusion_max_clients')
    seconds = float(env.get('BENCH_SECONDS', '10'))
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('bench_seconds must be a positive, finite number')
    positive(env.get('BENCH_OBJECTS', '100'), 'bench_objects')
    if env.get('MAX_PARALLEL', '1') != '1':
        raise ValueError('max_parallel must be 1: the measurement fleet is sequential')
    if env.get('FUSION_AFTER', ''):
        raise ValueError('fusion_after is obsolete; put sequential sessions in sessions instead')
    sessions = []
    entries = env.get('SESSIONS', '').strip()
    for entry in (entries or f"{env.get('SIZE', '10')}@{env.get('TICK_RATE', '20')}").split(','):
        match = re.fullmatch(r'(\d+)(?:@(\d+))?', entry.strip())
        if not match:
            raise ValueError(f'Invalid session: {entry!r}')
        size = positive(match[1], 'connections')
        tick = positive(match[2] or '20', 'tick_rate', 0)
        tag = f'c{size}t{tick}' if entries else env.get('TAG', 'solo')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,30}', tag):
            raise ValueError(f'Invalid session tag: {tag!r}')
        if any(s['tag'] == tag for s in sessions):
            raise ValueError(f'Duplicate session: {tag}')
        sessions.append(dict(size=size, tick=tick, tag=tag))
    cases = []
    worker_map = {}
    for session in sessions:
        for netcode in netcodes:
            total = min(session['size'], cap if netcode == 'fusion' else 200)
            count = min(measured, total)
            workers = {f'client-{i}': 1 for i in range(1, count + 1)}
            rest = total - count
            for i in range(1, math.ceil(rest / procs) + 1):
                workers[f'loadgen-{i}'] = min(procs, rest - (i - 1) * procs)
            for worker in workers:
                role, index = worker.split('-')
                runner = env.get('LOADGEN_RUNNER') if role == 'loadgen' else None
                worker_map[worker] = dict(id=worker, role=role, index=int(index), runner=runner or env['RUNNER'])
            cases.append(dict(id=len(cases) + 1, netcode=netcode, total=total, workers=workers, **session))
    if len(worker_map) > 255:
        raise ValueError('Fleet exceeds the Actions matrix limit')
    return dict(netcodes=netcodes, sessions=sessions, cases=cases, workers=list(worker_map.values()),
                expected=len(cases), server_runner=env.get('SERVER_RUNNER') or env['RUNNER'])


class Coordinator:
    """Idempotent acknowledgements; a case cannot advance while any worker still owns a player."""
    def __init__(self, plan):
        self.plan = plan
        self.workers = {w['id'] for w in plan['workers']}
        self.ready = set()
        self.acks = {0: set()}
        self.finished = set()
        self.failed = set()
        self.missing_results = set()
        self.limited = set()
        self.current = 0
        self.aborted = ''
        self.condition = threading.Condition()

    def abort(self, reason):
        with self.condition:
            self.aborted = reason
            self.condition.notify_all()

    def wait_for(self, predicate, timeout, description):
        with self.condition:
            if not self.condition.wait_for(lambda: self.aborted or predicate(), timeout):
                self.abort(f'Timed out waiting for {description}')
            if self.aborted:
                raise RuntimeError(self.aborted)

    def publish(self, index):
        with self.condition:
            if self.aborted:
                raise RuntimeError(self.aborted)
            if index != self.current + 1 or (self.current and self.acks[self.current] != self.workers):
                raise RuntimeError('Cannot advance before every worker has acknowledged completion')
            if self.ready != self.workers:
                raise RuntimeError('Cannot start before the full fleet is ready')
            self.current = index
            self.acks[index] = set()
            self.condition.notify_all()

    def next(self, worker, completed, ok=True, has_results=False):
        with self.condition:
            if (worker not in self.workers or type(completed) is not int or
                    type(ok) is not bool or type(has_results) is not bool):
                raise ValueError('Invalid worker acknowledgement')
            if completed < 0 or completed > len(self.plan['cases']) or completed not in (self.current, self.current - 1):
                raise ValueError('Stale or future acknowledgement')
            if completed == 0:
                self.ready.add(worker)
            else:
                self.acks[completed].add(worker)
                if not ok:
                    self.failed.add((worker, completed))
                    if not has_results:
                        self.missing_results.add((worker, completed))
            self.condition.notify_all()
            # One open request, not repeated HTTP polling during a measurement window.
            self.condition.wait_for(lambda: self.aborted or self.current > completed)
            if self.aborted:
                return dict(kind='abort', reason=self.aborted)
            # A terminated server can make clients fail to connect or finish. Only accept those
            # failures when they left diagnostics; never excuse a launch failure/missing output.
            accepted = ok or (completed in self.limited and has_results)
            if self.current > len(self.plan['cases']):
                return dict(kind='done', accepted=accepted)
            return dict(kind='case', case=self.plan['cases'][self.current - 1], accepted=accepted)

    def finish(self, worker):
        with self.condition:
            if worker not in self.workers or self.current != len(self.plan['cases']) + 1:
                raise ValueError('Unexpected final acknowledgement')
            self.finished.add(worker)
            self.condition.notify_all()
        return dict(kind='released')


def control_server(state, bind, port):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def log_message(self, *_):
            pass

        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError('Invalid request length')
                data = json.loads(self.rfile.read(length))
                if self.path == '/next':
                    response = state.next(data['worker'], data['completed'], data.get('ok', True), data.get('has_results', False))
                elif self.path == '/finished':
                    response = state.finish(data['worker'])
                else:
                    raise ValueError('Unknown endpoint')
                payload = json.dumps(response).encode()
                self.send_response(200)
            except (ValueError, KeyError, TypeError) as error:
                payload = json.dumps(dict(error=str(error))).encode()
                self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass  # A retry of the same acknowledgement returns the same case.

    server = ThreadingHTTPServer((bind, port), Handler)
    # Joining handlers on shutdown ensures final acknowledgement responses have been flushed.
    server.daemon_threads = False
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def request(url, endpoint, data, retry_seconds=600):
    deadline = time.monotonic() + retry_seconds
    while True:
        try:
            req = Request(url + endpoint, json.dumps(data).encode(), {'Content-Type': 'application/json'})
            # A healthy request stays open through one entire case (15m process limit + barrier).
            with urlopen(req, timeout=1200) as response:
                return json.load(response)
        except URLError as error:
            if getattr(error, 'code', 0) == 400 or time.monotonic() >= deadline:
                raise
            time.sleep(2)


def event(message, **fields):
    print(json.dumps(dict(time=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), event=message, **fields)), flush=True)


def player_command(case, role, index, process, root, env):
    netcode, tag = case['netcode'], case['tag']
    name = 'server' if role == 'server' else f'client-{index}' if role == 'client' else f'loadgen-{index}-{process}'
    log = root / 'logs' / tag / netcode / f'{name}.log'
    result = root / 'results' / tag / netcode / f'{name}.json'
    # Prepare all directories before readiness is announced (also for workers sitting a case out).
    cmd = ['xvfb-run', f'--server-num={100 + process}', '--server-args=-screen 0 1024x768x24',
           f'--error-file={log.with_suffix(".xvfb.log")}']
    if role == 'server' and env.get('BENCH_CPUS'):
        cmd += ['taskset', '-c', env['BENCH_CPUS']]
    cmd += [str(root / 'players' / f'player-{netcode}' / 'NetBench'), '-batchmode', '-nographics',
            '-role', 'server' if role == 'server' else 'client',
            '-benchSeconds', env.get('BENCH_SECONDS', '10'), '-benchObjects', env.get('BENCH_OBJECTS', '100'),
            '-tickRate', str(case['tick']), '-connectTimeout', '180', '-maxRunSeconds', '780',
            '-results', str(result), '-logFile', str(log)]
    if role == 'server':
        cmd += ['-count', str(case['total'])]
    if role == 'loadgen':
        cmd += ['-loadgen']
    if netcode == 'fusion':
        route = subprocess.check_output(['ip', '-j', 'route', 'get', '1.1.1.1'], text=True)
        interface = json.loads(route)[0]['dev']
        cmd += ['-session', f"nb-{env['GITHUB_RUN_ID']}-{env.get('GITHUB_RUN_ATTEMPT', '1')}-{tag}",
                '-region', env.get('PHOTON_REGION', 'eu'), '-netIface', interface,
                '-photonAppId', env.get('PHOTON_APP_ID', '')]
    else:
        cmd += ['-serverHost', '0.0.0.0' if role == 'server' else env['SERVER_IP'],
                '-port', env.get('BENCH_PORT', '7777'), '-netIface', 'tailscale0']
    return cmd, log.with_suffix('.launcher.log'), result


def stop_process(process):
    if os.name == 'posix':
        try:
            # The whole private group includes xvfb-run, Xvfb and the player, even if the parent exited.
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    process.wait()


def run_players(commands, timeout=900, memory_bytes=0):
    processes, streams, codes = [], [], []
    groups = []
    timed_out = set()
    cancelled = threading.Event()
    watchdog_thread = None
    deadline = time.monotonic() + timeout

    def watchdog():
        if cancelled.wait(max(0, deadline - time.monotonic())):
            return
        for process in processes:
            if process.poll() is None:
                timed_out.add(process.pid)
                try:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGTERM)
                    else:
                        process.terminate()
                except ProcessLookupError:
                    pass
        if not cancelled.wait(10):
            for process in processes:
                if process.pid in timed_out:
                    stop_process(process)

    try:
        for cmd, log, _ in commands:
            stream = log.open('wb')
            streams.append(stream)
            if memory_bytes:
                group, cmd = resources.guarded_command(cmd, memory_bytes)
                groups.append(group)
            processes.append(subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT,
                                              start_new_session=os.name == 'posix'))
        # Popen.wait(timeout=...) polls waitpid on Linux. Use a sleeping watchdog plus a blocking
        # wait instead, so the orchestrator does not wake 20 times/s beside a measured player.
        watchdog_thread = threading.Thread(target=watchdog, daemon=True)
        watchdog_thread.start()
        for process in processes:
            code = process.wait()
            codes.append(124 if process.pid in timed_out else code)
        for index, (cmd, _, result) in enumerate(commands):
            stats = resources.counters(groups[index]) if memory_bytes else None
            record = resources.process_record(codes[index], timeout, memory_bytes, stats)
            if '-maxRunSeconds' in cmd:
                record['harnessMaxSeconds'] = float(cmd[cmd.index('-maxRunSeconds') + 1])
                try:
                    raw = json.loads(result.read_text(encoding='utf-8'))
                    if record['status'] == 'exited' and raw.get('error') == 'timeout':
                        record.update(status='resource-limit-exceeded', reason='time', limit=record['harnessMaxSeconds'])
                except (OSError, ValueError):
                    pass  # Missing/invalid results are handled separately, not inferred as a timeout.
            resources.write_record(result, record)
    finally:
        cancelled.set()
        if watchdog_thread:
            watchdog_thread.join()
        for process in processes:
            stop_process(process)
        try:
            for group in groups:
                resources.privileged('cleanup', group)
        finally:
            for stream in streams:
                stream.close()
    return codes


def prepare(plan, root):
    for netcode in plan['netcodes']:
        binary = root / 'players' / f'player-{netcode}' / 'NetBench'
        if not binary.is_file():
            raise ValueError(f'Missing player: {binary}')
        binary.chmod(binary.stat().st_mode | 0o111)
    for case in plan['cases']:
        for directory in ('results', 'logs'):
            (root / directory / case['tag'] / case['netcode']).mkdir(parents=True, exist_ok=True)
    # Keep build provenance with the long-lived raw results, not only the one-day player artifact.
    provenance = root / 'results' / 'build-provenance'
    provenance.mkdir(parents=True, exist_ok=True)
    for netcode in plan['netcodes']:
        source = root / 'players' / f'player-{netcode}' / 'build-provenance.json'
        shutil.copy2(source, provenance / f'{netcode}.json')


def run_server(plan, root, env, execute=None):
    if execute is None:
        execute = lambda commands: run_players(commands, memory_bytes=resources.SERVER_MEMORY_BYTES)
    state = Coordinator(plan)
    server = control_server(state, env['CONTROL_BIND'], int(env.get('PHASE_PORT', '8788')))
    failed = []
    try:
        event('waiting-for-fleet', workers=sorted(state.workers))
        state.wait_for(lambda: state.ready == state.workers, 600, 'all prepared runners')
        for case in plan['cases']:
            if case['netcode'] != 'fusion':
                # Never start a new transport while the old one still owns the benchmark port.
                deadline = time.monotonic() + 30
                while re.search(rf"[:.]{int(env.get('BENCH_PORT', '7777'))}\b",
                                subprocess.check_output(['ss', '-lun'], text=True)):
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Benchmark UDP port is still in use')
                    time.sleep(1)
            event('case-start', id=case['id'], tag=case['tag'], netcode=case['netcode'])
            exit_deadline = time.monotonic() + CASE_EXIT_BUDGET
            state.publish(case['id'])
            command = player_command(case, 'server', 0, 1, root, env)
            code = execute([command])[0]
            process_file = resources.record_path(command[2])
            outcome = json.loads(process_file.read_text()) if process_file.exists() else {}
            if outcome.get('status') == 'resource-limit-exceeded':
                with state.condition:
                    state.limited.add(case['id'])
            # Preserve partial results and the original harness's own failure diagnostics.
            # A contained resource failure is a benchmark outcome, not a broken fleet barrier.
            if (outcome.get('status') == 'host-oom' or
                    ((not command[2].is_file() or not command[2].stat().st_size) and
                     outcome.get('status') != 'resource-limit-exceeded')):
                failed.append(case['id'])
            event('server-exited', id=case['id'], exit_code=code, process=outcome)
            state.wait_for(lambda: state.acks[case['id']] == state.workers,
                           max(0, exit_deadline - time.monotonic()),
                           f"case {case['id']} process-exit acknowledgements")
            event('case-finished', id=case['id'])
        state.publish(len(plan['cases']) + 1)
        state.wait_for(lambda: state.finished == state.workers, 120, 'final acknowledgements')
        unexpected = {pair for pair in state.failed if pair[1] not in state.limited or pair in state.missing_results}
        event('fleet-finished', failed_servers=failed, failed_workers=sorted(unexpected),
              limited_cases=sorted(state.limited), client_failures=sorted(state.failed))
        return int(bool(failed or unexpected))
    except Exception as error:
        event('fleet-aborted', reason=str(error), case=state.current,
              missing_ready=sorted(state.workers - state.ready),
              missing_exits=sorted(state.workers - state.acks.get(state.current, set())))
        raise
    finally:
        state.abort('Coordinator stopped')
        server.shutdown()
        server.server_close()


def run_worker(plan, root, env, execute=run_players):
    worker = env['WORKER_ID']
    role, index = worker.split('-')
    url = f"http://{env['SERVER_IP']}:{env.get('PHASE_PORT', '8788')}"
    completed, ok, has_results = 0, True, True
    failed = False
    while True:
        message = request(url, '/next', dict(worker=worker, completed=completed, ok=ok, has_results=has_results))
        if message['kind'] == 'abort':
            released(env)
            raise RuntimeError(message['reason'])
        failed |= not message.get('accepted', ok)
        if message['kind'] == 'done':
            request(url, '/finished', dict(worker=worker), retry_seconds=120)
            released(env)
            return int(failed)
        case = message['case']
        count = case['workers'].get(worker, 0)
        event('worker-case', id=case['id'], worker=worker, processes=count)
        commands = [player_command(case, role, int(index), p, root, env) for p in range(1, count + 1)]
        try:
            codes = execute(commands)
        except (OSError, subprocess.SubprocessError) as error:
            # run_players has already cleaned up every child. Stay at the barrier instead of
            # exiting into an artifact upload while another runner is still measuring.
            event('worker-launch-failed', id=case['id'], worker=worker, error=str(error))
            codes = [1] * count
        has_results = all(c[2].is_file() and c[2].stat().st_size > 0 for c in commands)
        ok = all(code == 0 for code in codes) and has_results
        completed = case['id']
        event('worker-exited', id=completed, worker=worker, exit_codes=codes)


def released(env):
    if env.get('GITHUB_OUTPUT'):
        with open(env['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('released=true\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'prepare', 'server', 'worker'))
    args = parser.parse_args()
    env = os.environ
    if args.operation == 'plan':
        plan = make_plan(env)
        outputs = dict(plan=plan, netcode_matrix=plan['netcodes'], worker_matrix={'include': plan['workers']},
                       expected=plan['expected'], server_runner=plan['server_runner'])
        print(json.dumps(plan, indent=2))
        if env.get('GITHUB_OUTPUT'):
            with open(env['GITHUB_OUTPUT'], 'a') as stream:
                for key, value in outputs.items():
                    stream.write(f'{key}={json.dumps(value, separators=(",", ":")) if not isinstance(value, str) else value}\n')
        return 0
    plan = json.loads(env['PLAN'])
    root = Path.cwd()
    if args.operation == 'prepare':
        prepare(plan, root)
        if not env.get('WORKER_ID'):
            # Fail before joining the fleet if this runner cannot enforce the shared policy.
            log = root / 'logs' / 'resource-preflight.log'
            result = root / 'logs' / 'resource-preflight.json'
            if run_players([(['/bin/true'], log, result)], memory_bytes=resources.SERVER_MEMORY_BYTES) != [0]:
                raise RuntimeError('Server resource-guard preflight failed')
        return 0
    def interrupted(*_):
        raise KeyboardInterrupt('Runner cancelled')
    signal.signal(signal.SIGTERM, interrupted)
    return run_server(plan, root, env) if args.operation == 'server' else run_worker(plan, root, env)


if __name__ == '__main__':
    raise SystemExit(main())
