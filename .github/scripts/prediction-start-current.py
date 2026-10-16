#!/usr/bin/env python3
"""Validate and retain the 2026-10-16 original/current release prediction comparison."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from statistics import mean, median

SPEC = importlib.util.spec_from_file_location(
    'prediction_bench', Path(__file__).with_name('prediction-bench.py'))
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)
SOURCES = {
    'baseline': '29d0ced375d84433681eeb39a8554f494794627a',
    'candidate': 'a3489811e3d938e88e0c345a50cad9234eb161ec',
}
SDKS = {
    'baseline': '52ce233cccfc6c9f6c98bfaf5bee57c58566b2cf',
    'candidate': 'fd4b1fbed03c30b764312cc30be546736db9f4c6',
}
PEERS = ('server', 'client-1', 'client-2', 'client-3', 'client-4')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def summarize(root):
    groups, boots, harnesses, peer_samples, cases = {}, set(), set(), [], set()
    run_metadata = []
    fingerprints = {}
    for variant in SOURCES:
        groups[variant] = []
        fingerprints[variant] = set()
        paths = sorted((root / variant).glob('20*'))
        assert len(paths) == 6, f'{variant}: expected six fresh-process runs'
        for path in paths:
            manifest = read(path / 'manifest.json')
            assert len(manifest['cases']) == 1 and read(path / 'failures.json') == []
            case = manifest['cases'][0]
            assert case['solution'] == 'purrdiction' and case['clients'] == 4
            assert case['tickRate'] == 60 and case['objects'] in (128, 512)
            assert case['seconds'] == 60 and case['warmupSeconds'] == 20
            settings = {key: case[key] for key in
                        ('clients', 'objects', 'tickRate', 'seconds', 'warmupSeconds')}
            cases.add(json.dumps(settings, sort_keys=True))
            machine = manifest['machine']
            assert machine['executionDirectoryMode'] == 'separate-directories'
            assert not machine.get('diagnosticCapture')
            boots.add(machine['hostSnapshot']['bootId'])
            inventory = manifest['players']['purrdiction']['runtimeSha256']
            assert inventory
            fingerprints[variant].add(digest(inventory))
            run_metadata.append(dict(variant=variant, run=path.name,
                manifestSha256=hashlib.sha256((path / 'manifest.json').read_bytes()).hexdigest(),
                machine=machine, runtimeSha256=inventory))
            reports = {peer: read(path / 'case-0001' / (peer + '.json')) for peer in PEERS}
            BENCH.validate_case(case, reports)
            rows = {}
            for peer, report in reports.items():
                assert report['developmentBuild'] is False
                assert report['detailedDiagnostics'] is False
                assert report['scriptingBackend'] == 'IL2CPP'
                provenance = json.loads(report['provenanceJson'])
                assert provenance['predictionCommit'] == SOURCES[variant]
                assert provenance['purrnetDependency'].endswith('#' + SDKS[variant])
                assert provenance['workCountersSchema'] == 1
                harnesses.add(digest(provenance['adapterSha256']))
                counters = BENCH.work_counter_delta(report)
                assert counters is not None
                wall = report['load']['wallSeconds']
                rows[peer] = dict(cpu=report['load']['cpuPercent'], fps=report['load']['avgFps'],
                                  forward=report['forwardCalls'] / wall,
                                  replay=report['replayCalls'] / wall,
                                  appliedInputs=report['appliedInputs'] / wall)
                rows[peer].update({name: count / wall for name, count in counters.items()})
                peer_samples.append(dict(variant=variant, run=path.name, peer=peer,
                    reportSha256=hashlib.sha256((path / 'case-0001' / (peer + '.json')).read_bytes()).hexdigest(),
                    cpuPercent=report['load']['cpuPercent'], wallSeconds=wall,
                    fps=report['load']['avgFps'], forwardCalls=report['forwardCalls'],
                    replayCalls=report['replayCalls'], appliedInputs=report['appliedInputs'],
                    provenance=provenance, workCounters=json.loads(report['workCountersJson'])))
            groups[variant].append({role: {name: mean(rows[peer][name] for peer in peers)
                for name in rows['server']} for role, peers in
                (('server', ('server',)), ('client', PEERS[1:]))})
        assert len(fingerprints[variant]) == 1, f'{variant}: runtime files changed between runs'
    assert len(boots) == 1 and None not in boots, 'Runs did not share one VM boot'
    assert len(harnesses) == 1, 'Benchmark C# source hashes differ'
    assert len(cases) == 1, 'Workload settings differ'
    execution_order = [row['variant'] for row in sorted(run_metadata, key=lambda row: row['run'])]
    assert execution_order == ['baseline', 'candidate', 'candidate', 'baseline'] * 3, \
        'Revision execution order does not match six alternating pairs'
    case = json.loads(next(iter(cases)))
    roles = {}
    for role in ('server', 'client'):
        roles[role] = {}
        for metric in groups['baseline'][0][role]:
            before = [run[role][metric] for run in groups['baseline']]
            after = [run[role][metric] for run in groups['candidate']]
            paired = [100 * (c / b - 1) if b else None for b, c in zip(before, after)]
            roles[role][metric] = dict(baselineMedian=median(before), candidateMedian=median(after),
                pairedMedianPercent=median(paired) if all(p is not None for p in paired) else None,
                baselinePerPair=before, candidatePerPair=after, pairedPercent=paired,
                lowerPairs=sum(c < b for b, c in zip(before, after)))
    return dict(schemaVersion=1, pairs=6, peersChecked=len(peer_samples), sources=SOURCES, sdks=SDKS,
        case=case, roles=roles, peerSamples=peer_samples, runMetadata=run_metadata,
        executionOrder=execution_order,
        runtimeFingerprints={variant: next(iter(values)) for variant, values in fingerprints.items()},
        serverEffectiveTickHz={variant: [run['server']['forward'] / case['objects']
            for run in runs] for variant, runs in groups.items()},
        notes=[
            'All peers passed release IL2CPP, diagnostics-off, final convergence and sampled-input checks.',
            'Identical benchmark C# sources, one VM boot per population, fixed runtime files per revision.',
            'FullPrediction world rollback; four clients at 60 Hz, no physics or graphics, loopback.',
            'Each revision uses its declared PurrNet dependency; this measures their combined changes.',
            'CPU is unadjusted whole-process percentage of one core. Clients are averaged before pairing.',
            'Six alternating pairs per population; one host cohort per population, with run-to-run variation.',
            'Paired median change uses six pair ratios, not the ratio of the two medians.',
            'Compact extract; full final states and logs remain in the CI artifacts for their retention period.',
        ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, help='Downloaded prediction-ab-results directory')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = summarize(args.root)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({role: result['roles'][role]['cpu'] for role in result['roles']}, indent=2))
