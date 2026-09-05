#!/usr/bin/env python3
"""Kernel memory guard for Linux benchmark servers; no sampling during measurement.

Only attach/cleanup need root. The launcher retains the runner's user, environment and CPU
affinity. Each private cgroup contains one server and its xvfb wrapper, not the orchestrator.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

SERVER_MEMORY_BYTES = 8 * 1024 ** 3
CGROUP_ROOT = Path('/sys/fs/cgroup')
SCRIPT = Path(__file__).resolve()


def group_path(name):
    if not re.fullmatch(r'netbench-[0-9a-f]{32}', name):
        raise ValueError('Not a private benchmark cgroup name')
    path = CGROUP_ROOT / name
    if path.is_symlink():
        raise ValueError('Benchmark cgroup must not be a symlink')
    return path


def privileged(*args):
    command = [sys.executable, str(SCRIPT), *map(str, args)]
    return subprocess.run(command if os.geteuid() == 0 else ['sudo', '-n', *command], check=True)


def attach(name, memory_bytes, pid):
    """Set limits before the unprivileged launcher execs the player (and forks Xvfb)."""
    if memory_bytes <= 0 or pid <= 1:
        raise ValueError('Invalid memory limit or launcher PID')
    if 'memory' not in (CGROUP_ROOT / 'cgroup.subtree_control').read_text().split():
        raise RuntimeError('cgroup v2 memory controller must be enabled; refusing an unguarded run')
    path = group_path(name)
    path.mkdir()  # Never reuse counters or another run's group.
    try:
        for key, value in [('memory.max', memory_bytes), ('memory.swap.max', 0), ('memory.oom.group', 1)]:
            (path / key).write_text(str(value))
        if not (path / 'cgroup.kill').exists():
            raise RuntimeError('cgroup.kill is required for complete server cleanup')
        (path / 'cgroup.procs').write_text(str(pid))
    except BaseException:
        path.rmdir()
        raise


def cleanup(name):
    path = group_path(name)
    if not path.exists():
        return
    # This exact, private group also catches a child that detached from the process group.
    (path / 'cgroup.kill').write_text('1')
    deadline = time.monotonic() + 10
    while 'populated 1' in (path / 'cgroup.events').read_text():
        if time.monotonic() >= deadline:
            raise RuntimeError(f'Server processes remain in {name}; cannot advance the fleet')
        time.sleep(0.05)  # Teardown only, after this server's measurement has ended.
    path.rmdir()


def counters(name):
    path = group_path(name)
    events = dict((key, int(value)) for key, value in
                  (line.split() for line in (path / 'memory.events').read_text().splitlines()))
    peak = path / 'memory.peak'
    return dict(memoryEvents=events, cgroupPeakBytes=int(peak.read_text()) if peak.exists() else None)


def guarded_command(command, memory_bytes):
    name = 'netbench-' + uuid.uuid4().hex
    return name, [sys.executable, str(SCRIPT), 'exec', name, str(memory_bytes), *command]


def process_record(code, timeout, memory_bytes=0, stats=None):
    record = dict(exitCode=code, status='exited', watchdogSeconds=timeout)
    if memory_bytes:
        record.update(memoryLimitBytes=memory_bytes, swapLimitBytes=0, **(stats or {}))
    events = record.get('memoryEvents', {})
    # oom_kill alone can also mean host-wide OOM; do not blame the case's cap without evidence.
    if events.get('max', 0) > 0 or events.get('oom', 0) > 0:
        record.update(status='resource-limit-exceeded', reason='memory', limit=memory_bytes)
    elif events.get('oom_kill', 0) > 0:
        record.update(status='host-oom', reason='host memory exhaustion')
    elif code == 124:
        record.update(status='resource-limit-exceeded', reason='time', limit=timeout)
    return record


def record_path(result):
    # Does not match client-*.json or server.json in the result aggregator.
    return result.with_name('process-' + result.name)


def write_record(result, record):
    record_path(result).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('attach', 'cleanup', 'exec'))
    parser.add_argument('name')
    parser.add_argument('rest', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    group_path(args.name)
    if args.operation == 'attach':
        attach(args.name, int(args.rest[0]), int(args.rest[1]))
    elif args.operation == 'cleanup':
        cleanup(args.name)
    else:
        memory_bytes, *command = args.rest
        privileged('attach', args.name, memory_bytes, os.getpid())
        os.execvp(command[0], command)


if __name__ == '__main__':
    main()
