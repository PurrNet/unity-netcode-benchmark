#!/usr/bin/env python3
"""Alternate two existing prediction builds on the same measurement machine."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

SCRIPT = Path(__file__).with_name('prediction-bench.py')
SPEC = importlib.util.spec_from_file_location('prediction_bench', SCRIPT)
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)


def commands(args):
    if args.diagnostics not in ('auto', 'on', 'off'):
        raise ValueError('Invalid detailed diagnostics mode')
    solution = args.solution
    if solution not in ('purrdiction', 'purrdiction-owned', 'purrdiction-player-input'):
        raise ValueError('Revision comparisons require one PurrDiction adapter')
    BENCH.make_plan(solution, args.clients, args.ticks, args.objects,
                    args.repeats, args.seconds, args.warmup)
    builds = {'baseline': args.baseline, 'candidate': args.candidate}
    planned = []
    for repeat in range(args.repeats):
        order = ('baseline', 'candidate') if repeat % 2 == 0 else ('candidate', 'baseline')
        for variant in order:
            planned.append([sys.executable, str(SCRIPT), '--solutions', solution,
                '--players', str(builds[variant]), '--output', str(args.output / variant),
                '--clients', args.clients, '--ticks', args.ticks, '--objects', args.objects,
                '--repeats', '1', '--seconds', str(args.seconds), '--warmup', str(args.warmup),
                '--timeout', str(max(240, args.seconds + args.warmup + 120)),
                '--diagnostics', args.diagnostics])
    return planned


def run(args, execute=subprocess.run):
    planned = commands(args)
    if args.dry_run:
        print(json.dumps(planned, indent=2))
        return 0
    failed = False
    environment = dict(os.environ, PREDICTION_EXECUTION_DIRECTORY_MODE=(
        'shared-directory' if args.baseline.resolve() == args.candidate.resolve()
        else 'separate-directories'))
    for index, command in enumerate(planned, 1):
        print(f'Comparison run {index}/{len(planned)}: {command}', flush=True)
        failed |= execute(command, check=False, env=environment).returncode != 0
    return int(failed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--solution', choices=('purrdiction', 'purrdiction-owned', 'purrdiction-player-input'), default='purrdiction')
    parser.add_argument('--output', type=Path, default=Path('prediction-ab-results'))
    parser.add_argument('--clients', default='4')
    parser.add_argument('--ticks', default='60')
    parser.add_argument('--objects', default='128')
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--warmup', type=float, default=20)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--diagnostics', choices=('auto', 'on', 'off'), default='auto')
    sys.exit(run(parser.parse_args()))
