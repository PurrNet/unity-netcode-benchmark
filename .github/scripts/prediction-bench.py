#!/usr/bin/env python3
"""Independent prediction case matrix, barriers and strict final-state validation."""
import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import itertools
import json
import math
import os
import platform
from pathlib import Path
import signal
import subprocess
import shutil
import sys
import threading
import time
import uuid

SOLUTIONS = ('purrdiction', 'purrdiction-owned', 'fishnet', 'fusion')
WORKLOAD = 'sequenced-state-v1'
WORK_COUNTER_NAMES = (
    'deltaFramesWrittenTotal', 'fullFramesSentTotal',
    'deltaSectionDeleteBitsTotal', 'deltaSectionHierarchyBitsTotal',
    'deltaSectionInputBitsTotal', 'deltaSectionStateBitsTotal',
    'deltaFrameBytesTotal', 'fullFrameBytesTotal',
    'inputSendsTotal', 'inputBytesSentTotal', 'inputTicksSentTotal',
    'framesReceivedTotal', 'fullFramesReceivedTotal',
    'leadJumpsTotal', 'leadPausesTotal', 'minLeadSnapsTotal', 'starvationJumpsTotal',
    'renderPhaseFrameAppliesTotal', 'tickPhaseFrameAppliesTotal',
)


def work_counter_delta(report):
    """Validate optional boundary snapshots; legacy/other adapters remain unavailable."""
    provenance = json.loads(report.get('provenanceJson') or '{}')
    if not isinstance(provenance, dict):
        raise ValueError('Invalid work counter provenance')
    expected = provenance.get('workCountersSchema')
    raw = report.get('workCountersJson')
    if expected is not None and (type(expected) is not int or expected != 1):
        raise ValueError('Unsupported work counter capability')
    if not raw:
        if expected is not None:
            raise ValueError('Missing promised work counters')
        return None
    window = json.loads(raw)
    if not isinstance(window, dict) or type(window.get('schemaVersion')) is not int or window['schemaVersion'] != 1:
        raise ValueError('Unsupported work counter window')
    for name in ('scope', 'sectionScope', 'byteScope'):
        if not isinstance(window.get(name), str) or not window[name]:
            raise ValueError('Missing work counter scope')
    for name in ('localTickStart', 'localTickEnd', 'maxAckLagTicksStart', 'maxAckLagTicksEnd'):
        value = window.get(name)
        if type(value) is not int or not 0 <= value <= 2**64 - 1:
            raise ValueError('Invalid work counter gauge')
    snapshots = [window.get(name) for name in ('start', 'end')]
    for snapshot in snapshots:
        if not isinstance(snapshot, dict) or set(snapshot) != set(WORK_COUNTER_NAMES):
            raise ValueError('Incomplete work counter snapshot')
        if any(type(value) is not int or not 0 <= value <= 2**64 - 1 for value in snapshot.values()):
            raise ValueError('Invalid work counter value')
    start, end = snapshots
    if any(end[name] < start[name] for name in WORK_COUNTER_NAMES):
        raise ValueError('Work counter reset during measurement')
    return {name: end[name] - start[name] for name in WORK_COUNTER_NAMES}


def host_snapshot(proc=Path('/proc'), sysfs=Path('/sys')):
    """Optional VM-wide context, collected outside player timing; never normalize scores."""
    def read(path):
        try:
            return path.read_text(errors='replace').strip()
        except OSError:
            return ''
    models, mhz = set(), []
    for line in read(proc / 'cpuinfo').splitlines():
        key, separator, value = line.partition(':')
        if not separator:
            continue
        key, value = key.strip().lower(), value.strip()
        if key in ('model name', 'hardware') and value:
            models.add(value)
        if key == 'cpu mhz':
            try:
                frequency = float(value)
                if math.isfinite(frequency) and frequency > 0:
                    mhz.append(frequency)
            except ValueError:
                pass
    ticks = None
    for line in read(proc / 'stat').splitlines():
        if line.startswith('cpu '):
            try:
                ticks = dict(zip(('user', 'nice', 'system', 'idle', 'iowait', 'irq',
                                  'softirq', 'steal', 'guest', 'guestNice'), map(int, line.split()[1:])))
            except ValueError:
                pass
            break
    try:
        tick_rate = os.sysconf('SC_CLK_TCK')
    except (AttributeError, OSError, ValueError):
        tick_rate = None
    return dict(capturedMonotonic=time.monotonic(), cpuModels=sorted(models), cpuMhz=mhz,
                schedulerCpuTicks=ticks, schedulerTicksPerSecond=tick_rate,
                bootId=read(proc / 'sys/kernel/random/boot_id') or None,
                clockSource=read(sysfs / 'devices/system/clocksource/clocksource0/current_clocksource') or None)


def csv_ints(text, minimum, maximum):
    values = [int(value.strip()) for value in text.split(',')]
    if not values or len(values) != len(set(values)) or any(not minimum <= x <= maximum for x in values):
        raise ValueError(f'Expected unique integers in [{minimum}, {maximum}]: {text!r}')
    return values


def make_plan(solutions, clients, ticks, objects, repeats, seconds, warmup):
    selected = [s.strip() for s in solutions.split(',')]
    if not selected or len(selected) != len(set(selected)) or any(s not in SOLUTIONS for s in selected):
        raise ValueError('Solutions must be unique entries from ' + ','.join(SOLUTIONS))
    counts, rates, populations = csv_ints(clients, 1, 16), csv_ints(ticks, 1, 240), csv_ints(objects, 1, 10000)
    if min(populations) < max(counts):
        raise ValueError('Each object count must give every client at least one owned object')
    if not 1 <= repeats <= 20 or not math.isfinite(seconds) or not 0.1 <= seconds <= 600 or not math.isfinite(warmup) or not 0 <= warmup <= 60:
        raise ValueError('Invalid measurement duration, warmup or repeat count')
    cases = []
    for n, t, o in itertools.product(counts, rates, populations):
        for r in range(1, repeats + 1):
            offset = (r - 1) % len(selected)
            for s in selected[offset:] + selected[:offset]:
                cases.append(dict(id=len(cases) + 1, solution=s, clients=n, tickRate=t,
                                  objects=o, repeat=r, seconds=seconds,
                                  warmupSeconds=warmup, workload=WORKLOAD))
    return cases


class Barrier:
    def __init__(self, peers, timeout):
        self.peers = set(peers)
        self.timeout = timeout
        self.condition = threading.Condition()
        self.arrivals = {phase: set() for phase in ('ready', 'stopped', 'done')}
        self.aborted = False

    def arrive(self, phase, peer):
        with self.condition:
            if phase not in self.arrivals or peer not in self.peers:
                raise ValueError('Unknown phase or peer')
            previous = {'stopped': 'ready', 'done': 'stopped'}.get(phase)
            if previous and self.arrivals[previous] != self.peers:
                raise ValueError('Barrier reached out of order')
            if peer in self.arrivals[phase]:
                raise ValueError('Duplicate barrier arrival')
            self.arrivals[phase].add(peer)
            self.condition.notify_all()
            completed = self.condition.wait_for(lambda: self.aborted or self.arrivals[phase] == self.peers, self.timeout)
            if not completed or self.aborted:
                raise TimeoutError('Barrier aborted or timed out')

    def abort(self):
        with self.condition:
            self.aborted = True
            self.condition.notify_all()


@contextmanager
def coordinator(peers, timeout):
    barrier = Barrier(peers, timeout)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                phase, peer = self.path.strip('/').split('/')
                barrier.arrive(phase, peer)
                status, payload = 200, b'{}'
            except (ValueError, TimeoutError) as error:
                status, payload = 400, str(error).encode()
            try:
                self.send_response(status)
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', barrier
    finally:
        barrier.abort()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def validate_case(case, reports):
    expected = {'server', *(f'client-{i}' for i in range(1, case['clients'] + 1))}
    if set(reports) != expected:
        raise ValueError('Missing or unexpected peer reports')
    snapshots = {}
    owners = []
    modes = [report.get('detailedDiagnostics') for report in reports.values()]
    if any(mode is not None and type(mode) is not bool for mode in modes) or len(set(modes)) != 1:
        raise ValueError('Mismatched detailed diagnostics modes')
    requested = case.get('diagnostics', 'auto')
    if requested not in ('auto', 'on', 'off'):
        raise ValueError('Invalid detailed diagnostics mode')
    if requested in ('on', 'off') and modes[0] is not (requested == 'on'):
        raise ValueError('Player did not honor the requested detailed diagnostics mode')
    for peer, report in reports.items():
        if not report.get('success') or report.get('schemaVersion') != 1 or report.get('suite') != 'prediction':
            raise ValueError(f'{peer}: failed or unsupported report: {report.get("error")}')
        if report.get('solution') != case['solution'] or report.get('workload') != WORKLOAD or report.get('peer') != peer:
            raise ValueError(f'{peer}: wrong solution, workload or peer')
        work_counter_delta(report)
        config = report.get('config', {})
        for key in ('clients', 'objects', 'tickRate', 'seconds', 'warmupSeconds'):
            if config.get(key) != case[key]:
                raise ValueError(f'{peer}: mismatched {key}')
        role = 'server' if peer == 'server' else 'client'
        if report.get('role') != role or report.get('actualTickRate') != case['tickRate']:
            raise ValueError(f'{peer}: wrong role or actual tick rate')
        if report.get('requestedFrameCap') != 60 or report.get('actualFrameCap') != 60:
            raise ValueError(f'{peer}: wrong measurement frame cap')
        if report.get('observedObjects') != case['objects'] or (role == 'client' and report.get('ownedObjects', 0) < 1):
            raise ValueError(f'{peer}: incomplete population or no owned objects')
        load = report.get('load', {})
        if not math.isfinite(load.get('wallSeconds', 0)) or load.get('wallSeconds', 0) < case['seconds'] * .8 or load.get('frameCount', 0) < 1:
            raise ValueError(f'{peer}: incomplete measurement window')
        if report.get('forwardCalls', 0) + report.get('replayCalls', 0) < 1:
            raise ValueError(f'{peer}: no native prediction callbacks')
        if role == 'server' and (type(report.get('appliedInputs')) is not int or report['appliedInputs'] < 1):
            raise ValueError(f'{peer}: no new input commands during sampling')
        if role == 'client' and report.get('ownedForwardCalls', 0) < 1:
            raise ValueError(f'{peer}: no owned forward prediction callbacks')
        entries = report.get('finalState', [])
        indexed = {p['index']: p['state'] for p in entries}
        if len(entries) != case['objects'] or set(indexed) != set(range(case['objects'])):
            raise ValueError(f'{peer}: duplicate or missing final objects')
        fields = {'x', 'z', 'lastSequence', 'appliedInputs', 'hash', 'a', 'b', 'c'}
        if any(set(s) != fields or any(type(value) is not int for value in s.values()) for s in indexed.values()):
            raise ValueError(f'{peer}: invalid final state schema')
        if any(s.get('appliedInputs', 0) < 1 or s.get('lastSequence', 0) < 1 for s in indexed.values()):
            raise ValueError(f'{peer}: inactive inputs')
        if role == 'client':
            owned = [p['index'] for p in entries if p.get('owned')]
            if len(owned) != report['ownedObjects']:
                raise ValueError(f'{peer}: owned-object count changed')
            owners.extend(owned)
        snapshots[peer] = indexed
    reference = snapshots['server']
    if sorted(owners) != list(range(case['objects'])):
        raise ValueError('Final ownership does not assign exactly one owner to every object')
    for peer, state in snapshots.items():
        if state != reference:
            raise ValueError(f'{peer}: final predicted state differs from authority')
    return True


def stop_process(process):
    if os.name == 'nt':
        if process.poll() is not None:
            return
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # An exited xvfb wrapper can still have descendants in its process group.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        finally:
            # Clean descendants even if the wrapper/parent already exited.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    process.wait(timeout=10)


def validate_memory_snapshots(reports, directory):
    for peer in ('server', 'client-1'):
        report = reports[peer]
        expected = directory / (peer + '.snap')
        if not report.get('memorySnapshotRequested') or not report.get('memorySnapshotSucceeded'):
            raise ValueError(f'{peer}: memory snapshot was not captured')
        if Path(report.get('memorySnapshotPath', '')).resolve() != expected.resolve() or not expected.is_file() or expected.stat().st_size == 0:
            raise ValueError(f'{peer}: missing or mismatched memory snapshot artifact')


def run_case(case, binary, directory, timeout, region, memory_snapshots=False):
    directory.mkdir()
    host_before = host_snapshot()
    deadline = time.monotonic() + timeout
    peers = ['server', *(f'client-{i}' for i in range(1, case['clients'] + 1))]
    commands, processes, streams = {}, {}, []
    session = 'csp-' + uuid.uuid4().hex
    try:
        with coordinator(peers, timeout) as (url, barrier):
            for peer in peers:
                commands[peer] = [str(binary), '-batchmode', '-nographics', '-predictionRole', 'server' if peer == 'server' else 'client',
                    '-predictionPeer', peer, '-predictionCoordinator', url,
                    '-count', str(case['clients']), '-benchObjects', str(case['objects']), '-tickRate', str(case['tickRate']),
                    '-benchSeconds', str(case['seconds']), '-warmupSeconds', str(case['warmupSeconds']),
                    '-serverHost', '127.0.0.1', '-port', '17800', '-session', session, '-region', region,
                    '-predictionResults', str(directory / (peer + '.json')), '-logFile', str(directory / (peer + '.log')),
                    '-job-worker-count', '2']
                if memory_snapshots and peer in ('server', 'client-1'):
                    commands[peer] += ['-predictionMemorySnapshot', str(directory / (peer + '.snap'))]
                if case.get('diagnostics', 'auto') != 'auto':
                    commands[peer] += ['-predictionDiagnostics', str(case['diagnostics'] == 'on').lower()]
                stream = (directory / (peer + '.stdout.log')).open('wb')
                streams.append(stream)
                command = commands[peer]
                if os.name != 'nt' and shutil.which('xvfb-run'):
                    command = ['xvfb-run', '-a', *command]
                processes[peer] = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                    start_new_session=os.name != 'nt', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                if peer == 'server':
                    # Photon rooms do not exist until the server has finished connecting.
                    # Starting clients concurrently can make a valid Fusion run fail to join.
                    listening_deadline = min(deadline, time.monotonic() + 120)
                    log = directory / 'server.log'
                    while not log.is_file() or '[PredictionBench] Server listening' not in log.read_text(encoding='utf-8', errors='replace'):
                        if processes[peer].poll() is not None or time.monotonic() > listening_deadline:
                            raise RuntimeError('Server did not become ready before clients started')
                        time.sleep(.1)
            (directory / 'commands.json').write_text(json.dumps(commands, indent=2))
            while any(p.poll() is None for p in processes.values()):
                failed = [name for name, p in processes.items() if p.poll() not in (None, 0)]
                if failed or time.monotonic() > deadline:
                    barrier.abort()
                    raise RuntimeError('Failed processes: ' + ','.join(failed) if failed else 'Case timeout')
                time.sleep(.2)
            reports = {peer: json.loads((directory / (peer + '.json')).read_text(encoding='utf-8-sig')) for peer in peers}
            validate_case(case, reports)
            if memory_snapshots:
                validate_memory_snapshots(reports, directory)
            return reports
    finally:
        for process in processes.values():
            stop_process(process)
        for stream in streams:
            stream.close()
        host_after = host_snapshot()
        (directory / 'host.json').write_text(json.dumps(dict(before=host_before, after=host_after,
            intervalSeconds=host_after['capturedMonotonic'] - host_before['capturedMonotonic'],
            scope='VM-wide whole-case context including startup, warmup and shutdown; not the player measurement window. Not used to normalize scores.'), indent=2))


def inventory(root):
    hashes = {}
    for path in sorted(root.rglob('*')):
        if path.is_file() and not any('ButDontShipItWithYourGame' in part or 'BurstDebugInformation_DoNotShip' in part for part in path.parts):
            with path.open('rb') as stream:
                hashes[path.relative_to(root).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solutions', default='purrdiction,fishnet,fusion')
    parser.add_argument('--clients', default='1,2,4')
    parser.add_argument('--ticks', default='20,60')
    parser.add_argument('--objects', default='32,128')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--warmup', type=float, default=3)
    parser.add_argument('--timeout', type=float, default=240)
    parser.add_argument('--players', type=Path, default=Path('prediction-players'))
    parser.add_argument('--output', type=Path, default=Path('prediction-results'))
    parser.add_argument('--region', default='eu')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--diagnostics', choices=('auto', 'on', 'off'), default='auto',
                        help='Detailed native pass telemetry: auto enables it only in development players')
    parser.add_argument('--memory-snapshots', action='store_true',
                        help='Capture server/client-1 retained heaps after sampling and final state capture')
    args = parser.parse_args()
    plan = make_plan(args.solutions, args.clients, args.ticks, args.objects, args.repeats, args.seconds, args.warmup)
    for case in plan:
        case['diagnostics'] = args.diagnostics
    if not math.isfinite(args.timeout) or args.timeout < args.seconds + args.warmup + 15:
        parser.error('--timeout must leave at least 15 seconds outside sampling and warmup')
    run = args.output.resolve() / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    manifest = {'schemaVersion': 1, 'suite': 'prediction', 'cases': plan, 'dryRun': args.dry_run,
        'execution': 'Sequential cases; one dedicated server plus N clients sharing one machine',
        'network': 'Direct loopback for PurrDiction/FishNet; Photon Cloud Server mode for Fusion; no artificial delay/loss',
        'comparison': 'Diagnostic baseline, not an overall ranking. Prediction scopes and transport routes differ.',
        'machine': {'platform': platform.platform(), 'processor': platform.processor(), 'logicalProcessors': os.cpu_count(),
                    'hostSnapshot': host_snapshot(),
                    'executionDirectoryMode': os.environ.get('PREDICTION_EXECUTION_DIRECTORY_MODE', 'adapter-default')},
        'workflowRun': os.environ.get('GITHUB_RUN_ID'), 'benchmarkCommit': os.environ.get('GITHUB_SHA'), 'region': args.region, 'players': {}}
    for solution in {case['solution'] for case in plan}:
        binary = args.players.resolve() / solution / ('PredictionBench.exe' if os.name == 'nt' else 'PredictionBench')
        if not args.dry_run and not binary.is_file():
            parser.error(f'Player missing: {binary}')
        manifest['players'][solution] = {'path': str(binary), 'runtimeSha256': inventory(binary.parent) if binary.is_file() else {}}
    (run / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(run, flush=True)
    if args.dry_run:
        return
    failures = []
    for case in plan:
        print(f'Case {case["id"]}/{len(plan)}: {case}', flush=True)
        try:
            run_case(case, Path(manifest['players'][case['solution']]['path']), run / f'case-{case["id"]:04d}', args.timeout, args.region, args.memory_snapshots)
        except Exception as error:
            failures.append({'id': case['id'], 'error': str(error)})
            print(f'Failed: {error}', flush=True)
    (run / 'failures.json').write_text(json.dumps(failures, indent=2))
    if failures:
        sys.exit(1)


if __name__ == '__main__':
    def terminate(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, terminate)
    main()
