#!/usr/bin/env python3
"""Sample frozen prediction players; diagnostic captures are not comparison results."""
import argparse
from collections import Counter
from contextlib import contextmanager, ExitStack
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time


def recording_command(perf, pid, destination, duration, all_threads=False):
    return [str(perf), 'record', '-B', '-e', 'cpu-clock', '-F', '999',
            '--call-graph', 'dwarf,16384', '-p' if all_threads else '-t', str(pid),
            '-o', str(destination), '--', 'sleep', str(duration)]


def thread_cpu(pid, proc=Path('/proc')):
    result = {}
    for task in (proc / str(pid) / 'task').iterdir():
        if not task.name.isdigit():
            continue
        try:
            stat = (task / 'stat').read_text()
        except (FileNotFoundError, ProcessLookupError):
            continue  # A worker can exit between directory enumeration and reading.
        close = stat.rindex(')')
        fields = stat[close + 2:].split()
        result[task.name] = dict(name=stat[stat.index('(') + 1:close],
                                 ticks=int(fields[11]) + int(fields[12]), startTicks=int(fields[19]))
    return result


def thread_cpu_delta(before, after, ticks_per_second):
    rows = []
    for tid, current in after.items():
        previous = before.get(tid)
        if previous and previous['startTicks'] != current['startTicks']:
            previous = None
        ticks = current['ticks'] - (previous['ticks'] if previous else 0)
        if ticks < 0:
            continue
        rows.append(dict(tid=int(tid), name=current['name'], cpuSeconds=ticks / ticks_per_second,
                         presentAtStart=previous is not None))
    return dict(threads=sorted(rows, key=lambda row: row['cpuSeconds'], reverse=True),
                exitedThreadIds=sorted(int(tid) for tid in before.keys() - after.keys()),
                note='Per-thread CPU counters; exited threads have no final counter and are not summed.')


def summarize(path):
    total = waiting = managed = unresolved = 0
    leaves, inclusive = Counter(), Counter()
    thread_samples, thread_stacks, thread_names = Counter(), Counter(), {}
    for block in path.read_text(errors='replace').split('\n\n'):
        lines = block.splitlines()
        header = re.match(r'^(.*?)\s+(\d+)\s+[\d.]+:\s+\d+\s+cpu-clock:', lines[0]) if lines else None
        frames = [line for line in block.splitlines() if line.startswith('\t')]
        if header:
            tid = int(header[2])
            thread_names[tid] = header[1].strip()
            thread_samples[tid] += 1
            thread_stacks[tid] += bool(frames)
        if not frames:
            continue
        total += 1
        symbols = [re.sub(r'_m[0-9A-Fa-f]{32,40}', '', line.split()[1].split('+')[0]) for line in frames]
        waiting += any('TimeManager::EndSyncFrame(' in name for name in symbols)
        managed += any('/GameAssembly.so)' in line for line in frames)
        unresolved += symbols[0] == '[unknown]'
        leaves[symbols[0]] += 1
        inclusive.update(set(symbols))
    if not total:
        raise RuntimeError(f'No sampled stacks: {path}')
    return dict(samples=total, frameWaitSamples=waiting, managedStackSamples=managed,
                unresolvedLeafSamples=unresolved, frameWaitPercent=100 * waiting / total,
                sampleHeaders=sum(thread_samples.values()),
                byThread=[dict(tid=tid, name=thread_names[tid], samples=count, stackSamples=thread_stacks[tid])
                          for tid, count in thread_samples.most_common()],
                samplingNote='Stack counts describe sampled events, not exact CPU-time shares. Compare per-thread samples with threadCpu counters; coverage can differ between threads.',
                leaf=leaves.most_common(25), inclusive=inclusive.most_common(35))


def install_symbols(perf, player):
    backup = player / 'PredictionBench_BackUpThisFolder_ButDontShipItWithYourGame'
    installed = []
    for binary, debug in (('UnityPlayer.so', 'UnityPlayer_s.debug'),
                          ('GameAssembly.so', 'GameAssembly.debug'), ('PredictionBench', 'PredictionBench_s.debug')):
        original, symbols = player / binary, backup / debug
        if not original.is_file() or not symbols.is_file():
            continue
        def build_id(path):
            notes = subprocess.check_output(['readelf', '-n', str(path)], text=True, stderr=subprocess.PIPE)
            match = re.search(r'Build ID: ([a-f0-9]+)', notes)
            if not match:
                raise RuntimeError(f'ELF build ID missing: {path}')
            return match.group(1)
        identifier = build_id(original)
        if build_id(symbols) != identifier:
            raise RuntimeError(f'Symbol build ID mismatch: {binary}')
        destination = Path('/usr/lib/debug/.build-id') / identifier[:2] / (identifier[2:] + '.debug')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            destination.unlink()
        elif destination.exists():
            raise RuntimeError(f'Refusing to replace existing symbol file: {destination}')
        destination.symlink_to(symbols)
        # The original ELF supplies unwind mappings; the debug sidecar supplies symbols.
        subprocess.run([str(perf), 'buildid-cache', '--update', str(original)], check=True)
        installed.append(dict(binary=binary, buildId=identifier))
    return installed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solution', default='purrdiction')
    parser.add_argument('--players', type=Path, required=True)
    parser.add_argument('--perf', type=Path)
    parser.add_argument('--output', type=Path, default=Path('prediction-native-profile'))
    parser.add_argument('--clients', type=int, default=4)
    parser.add_argument('--ticks', type=int, default=60)
    parser.add_argument('--objects', type=int, default=128)
    parser.add_argument('--seconds', type=float, default=50)
    parser.add_argument('--warmup', type=float, default=20)
    parser.add_argument('--region', default='eu')
    parser.add_argument('--player-run', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--all-threads', action='store_true', help='Sample all threads of each selected process')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('prediction_bench', Path(__file__).with_name('prediction-bench.py'))
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    bench.make_plan(args.solution, str(args.clients), str(args.ticks), str(args.objects), 1, args.seconds, args.warmup)
    if args.solution not in bench.SOLUTIONS or not args.player_run.isdigit() or args.seconds < 10:
        parser.error('Select one adapter, a numeric artifact run ID and at least ten measurement seconds')
    duration = min(25, args.seconds - 5)
    settings = dict(diagnosticOnly=True, playerRun=args.player_run, solution=args.solution,
                    clients=args.clients, tickRate=args.ticks, objects=args.objects,
                    warmupSeconds=args.warmup, measurementSeconds=args.seconds,
                    captureSeconds=duration, captureOffsetAfterReadySeconds=args.warmup + 2,
                    peers=['server', 'client-1'], allThreads=args.all_threads,
                    scope='999 Hz cpu-clock samples of ' +
                          ('all threads in each selected process' if args.all_threads else 'each selected main thread'))
    if args.dry_run:
        print(json.dumps(settings, indent=2))
        return
    if sys.platform != 'linux' or os.geteuid() != 0 or not args.perf or not args.perf.is_file():
        parser.error('Use Linux root with an explicit perf executable')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'settings.json').write_text(json.dumps(settings, indent=2))
    original_launch, original_coordinator = bench.subprocess.Popen, bench.coordinator
    groups, samplers, errors, captures = {}, [], [], {}
    stop = threading.Event()

    def launch(command, *positional, **keywords):
        process = original_launch(command, *positional, **keywords)
        if '-predictionPeer' in command:
            groups[command[command.index('-predictionPeer') + 1]] = process.pid
        return process

    def sample(barrier):
        processes = []
        try:
            with barrier.condition:
                ready = barrier.condition.wait_for(lambda: barrier.aborted or
                    barrier.arrivals['ready'] == barrier.peers, 120)
                if not ready or barrier.aborted:
                    raise RuntimeError('Players did not reach the ready barrier')
            if stop.wait(args.warmup + 2):
                raise RuntimeError('Workload ended before sampling')
            with ExitStack() as streams:
                for peer in settings['peers']:
                    candidates = []
                    for entry in Path('/proc').iterdir():
                        if not entry.name.isdigit():
                            continue
                        try:
                            command = (entry / 'cmdline').read_bytes().decode(errors='replace').split('\0')
                            if command[0].endswith('/PredictionBench') and '-predictionPeer' in command and \
                                    command[command.index('-predictionPeer') + 1] == peer and \
                                    os.getpgid(int(entry.name)) == groups[peer]:
                                candidates.append(int(entry.name))
                        except (OSError, IndexError):
                            continue
                    if len(candidates) != 1:
                        raise RuntimeError(f'Expected one owned player PID for {peer}, got {candidates}')
                    captures[peer] = dict(pid=candidates[0], startedMonotonic=time.monotonic(),
                                          threadCpuBefore=thread_cpu(candidates[0]))
                    log = streams.enter_context((output / f'{peer}.perf.log').open('w'))
                    process = original_launch(recording_command(args.perf, candidates[0],
                        output / f'{peer}.perf.data', duration, args.all_threads),
                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    processes.append(process)
                deadline = time.monotonic() + duration + 20
                while any(process.poll() is None for process in processes) and not stop.is_set() and time.monotonic() < deadline:
                    stop.wait(.1)
                if any(process.poll() != 0 for process in processes):
                    raise RuntimeError('Native sampling failed, ended early or exceeded its deadline')
                for capture in captures.values():
                    capture['threadCpu'] = thread_cpu_delta(capture.pop('threadCpuBefore'),
                        thread_cpu(capture['pid']), os.sysconf('SC_CLK_TCK'))
                    capture['counterIntervalSeconds'] = time.monotonic() - capture['startedMonotonic']
        except Exception as error:
            errors.append(str(error))
        finally:
            for process in processes:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGINT)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)

    @contextmanager
    def coordinator(peers, timeout):
        with original_coordinator(peers, timeout) as (url, barrier):
            thread = threading.Thread(target=sample, args=(barrier,))
            samplers.append(thread)
            thread.start()
            yield url, barrier

    bench.subprocess.Popen, bench.coordinator = launch, coordinator
    sys.argv = ['profile', '--solutions', args.solution, '--clients', str(args.clients), '--ticks', str(args.ticks),
        '--objects', str(args.objects), '--seconds', str(args.seconds), '--warmup', str(args.warmup),
        '--repeats', '1', '--diagnostics', 'off', '--region', args.region,
        '--players', str(args.players.resolve()), '--output', str(output / 'validation')]
    try:
        bench.main()
    finally:
        stop.set()
        for thread in samplers:
            thread.join(timeout=15)
            if thread.is_alive():
                errors.append('Native sampler did not stop')
        bench.subprocess.Popen, bench.coordinator = original_launch, original_coordinator
        for path in output.rglob('manifest.json'):
            manifest = json.loads(path.read_text())
            manifest['machine']['diagnosticCapture'] = settings
            path.write_text(json.dumps(manifest, indent=2))
        (output / 'capture.json').write_text(json.dumps(dict(peers=captures, errors=errors), indent=2))
    if errors or set(captures) != set(settings['peers']):
        raise RuntimeError(f'Native capture did not complete: {errors}')
    installed = install_symbols(args.perf, args.players.resolve() / args.solution)
    wait_symbols = any(item['binary'] == 'UnityPlayer.so' for item in installed)
    summary = dict(settings=settings, installedSymbols=installed, frameWaitSymbolsAvailable=wait_symbols, peers={})
    for peer in settings['peers']:
        stacks = output / f'{peer}.stacks.txt'
        with stacks.open('w') as stream:
            subprocess.run([str(args.perf), 'script', '--no-inline', '-f', '-i', str(output / f'{peer}.perf.data')],
                           stdout=stream, check=True, env=dict(os.environ, DEBUGINFOD_URLS=''))
        summary['peers'][peer] = summarize(stacks)
        summary['peers'][peer]['threadCpu'] = captures[peer]['threadCpu']
        if not wait_symbols:
            summary['peers'][peer]['frameWaitPercent'] = None
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(dict(diagnosticOnly=True, frameWaitSymbolsAvailable=wait_symbols,
        peers={peer: {key: values[key] for key in ('samples', 'frameWaitPercent',
            'managedStackSamples', 'unresolvedLeafSamples')} for peer, values in summary['peers'].items()}), indent=2))


if __name__ == '__main__':
    main()
