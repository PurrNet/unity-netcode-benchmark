#!/usr/bin/env python3
"""Render prediction diagnostics separately from the replication scorecard."""
import argparse
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import statistics

SPEC = importlib.util.spec_from_file_location('prediction_bench', Path(__file__).with_name('prediction-bench.py'))
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)


def render(source, output):
    output.mkdir(parents=True, exist_ok=True)
    groups, failures, raw = {}, [], []
    manifests = list(source.rglob('manifest.json'))
    if not manifests:
        raise ValueError('No prediction run manifests found')
    for path in manifests:
        manifest = json.loads(path.read_text())
        if manifest.get('suite') != 'prediction' or manifest.get('schemaVersion') != 1:
            raise ValueError(f'Unsupported manifest: {path}')
        for case in manifest['cases']:
            folder = path.parent / f'case-{case["id"]:04d}'
            try:
                reports = {peer: json.loads((folder / f'{peer}.json').read_text(encoding='utf-8-sig'))
                           for peer in ['server', *(f'client-{i}' for i in range(1, case['clients'] + 1))]}
                BENCH.validate_case(case, reports)
                # A process failure after writing JSON still invalidates a case.
                execution_failures = json.loads((path.parent / 'failures.json').read_text())
                if any(item['id'] == case['id'] for item in execution_failures):
                    raise ValueError('Player orchestration failed after report creation')
            except (OSError, ValueError, KeyError) as error:
                failures.append({'case': case, 'error': str(error)})
                continue
            raw.append({'case': case, 'reports': reports, 'manifest': manifest})
            for role in ('server', 'client'):
                peers = [report for report in reports.values() if report['role'] == role]
                # Never silently pool different binaries, build modes, or hardware.
                build_inputs = [peers[0].get('provenanceJson'), manifest.get('players', {}).get(case['solution'], {}).get('runtimeSha256'),
                                peers[0].get('detailedDiagnostics')]
                build = hashlib.sha256(json.dumps(build_inputs, sort_keys=True).encode()).hexdigest()[:12]
                environment = json.dumps([manifest['machine'], peers[0].get('unityVersion'), peers[0].get('scriptingBackend'), peers[0].get('developmentBuild')], sort_keys=True)
                hardware = hashlib.sha256(environment.encode()).hexdigest()[:12]
                key = (case['solution'], case['clients'], case['tickRate'], case['objects'], role, build, hardware)
                item = groups.setdefault(key, {'samples': [], 'predictionScope': peers[0]['predictionScope'],
                                              'replayDefinition': peers[0]['replayDefinition'],
                                              'detailedDiagnostics': peers[0].get('detailedDiagnostics'),
                                              'workSamples': []})
                # One datapoint per repeat; clients on the same case are averaged before
                # taking the median across independent runs.
                sample = {}
                for metric in ('cpuPercent', 'p95FrameMs', 'p99FrameMs', 'managedHeapBytes', 'peakRssBytes'):
                    values = [peer['load'][metric] for peer in peers]
                    if metric == 'cpuPercent':
                        available = all(peer.get('cpuMetricsAvailable', peer.get('linuxMetricsAvailable')) for peer in peers)
                    elif metric == 'peakRssBytes':
                        available = all(peer.get('linuxMetricsAvailable') for peer in peers)
                    else:
                        available = True
                    sample[metric] = statistics.mean(values) if available and all(v >= 0 for v in values) else None
                sample['callbacksPerSecond'] = statistics.mean(
                    (peer['forwardCalls'] + peer['replayCalls']) / peer['load']['wallSeconds'] for peer in peers)
                sample['replayCallbacksPerSecond'] = statistics.mean(peer['replayCalls'] / peer['load']['wallSeconds'] for peer in peers)
                sample['gcBytesPerSecond'] = statistics.mean(peer['load']['gcAllocBytes'] / peer['load']['wallSeconds'] for peer in peers)
                sample['gcEstimated'] = any(peer['load']['gcAllocEstimated'] for peer in peers)
                item['samples'].append(sample)
                counters = [BENCH.work_counter_delta(peer) for peer in peers]
                item['workSamples'].append({name: statistics.mean(
                    count[name] / peer['load']['wallSeconds'] for count, peer in zip(counters, peers))
                    for name in BENCH.WORK_COUNTER_NAMES} if all(count is not None for count in counters) else None)
    aggregates = []
    for key, group in sorted(groups.items()):
        row = dict(zip(('solution', 'clients', 'tickRate', 'objects', 'role', 'buildFingerprint', 'environmentFingerprint'), key))
        row.update(predictionScope=group['predictionScope'], replayDefinition=group['replayDefinition'],
                   detailedDiagnostics=group['detailedDiagnostics'], repeats=len(group['samples']))
        for metric in group['samples'][0]:
            values = [sample[metric] for sample in group['samples']]
            row[metric] = any(values) if metric == 'gcEstimated' else statistics.median(values) if all(v is not None for v in values) else None
        row['workCountersPerSecond'] = {name: statistics.median(sample[name] for sample in group['workSamples'])
                                       for name in BENCH.WORK_COUNTER_NAMES} if all(
                                           sample is not None for sample in group['workSamples']) else None
        aggregates.append(row)
    data = {'schemaVersion': 1, 'suite': 'prediction', 'complete': not failures and bool(raw),
            'groups': aggregates, 'failures': failures, 'raw': raw}
    (output / 'latest.json').write_text(json.dumps(data, indent=2) + '\n')
    lines = ['# Prediction benchmark', '',
        'Separate from the replication benchmark. Workload: **sequenced-state-v1**, a 12-byte input and 32-byte integer state; no physics or graphics.', '',
        'Cases run sequentially. Server and clients share one machine; this is a diagnostic baseline, not a ranking. Fusion uses Photon Cloud; PurrDiction/FishNet use loopback. No artificial latency or loss is applied.', '',
        'Client figures average peers within a run, then take the median across repeats. CPU is whole-process, all threads, as a percentage of one core. Frame time includes the 60 fps cap. RSS is the process-lifetime high-water mark. Estimated GC allocation is marked with `~`.', '',
        '**Native replay counts have different definitions and prediction scopes.** They explain work within an adapter; they are not interchangeable amounts of service.', '',
        'Input distribution is native: Fusion collects one 12-byte command per player per tick, shared by that player\'s pawns; PurrDiction/FishNet collect commands per owned pawn. Input record counts are not normalized. This workload does not compare independently controlled objects.', '',
        'Detailed telemetry is optional: development players enable it by default; release players disable it. On, off and unrecorded legacy modes are never pooled.', '',
        f'Validated cases: {len(raw)} / {len(raw) + len(failures)}.', '',
        '| Solution | Clients | Hz | Objects | Role | Details | Repeats | CPU % | Frame p95 ms | Heap MiB | Peak RSS MiB | GC bytes/s | Calls/s | Native replay calls/s |',
        '|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    def number(value, divisor=1):
        return 'unavailable' if value is None or value < 0 else f'{value / divisor:.2f}'
    for row in aggregates:
        details = 'legacy' if row['detailedDiagnostics'] is None else 'on' if row['detailedDiagnostics'] else 'off'
        lines.append('| ' + ' | '.join([row['solution'], str(row['clients']), str(row['tickRate']), str(row['objects']), row['role'], details, str(row['repeats']),
            number(row['cpuPercent']), number(row['p95FrameMs']), number(row['managedHeapBytes'], 1048576), number(row['peakRssBytes'], 1048576),
            ('~' if row['gcEstimated'] else '') + number(row['gcBytesPerSecond']), number(row['callbacksPerSecond']), number(row['replayCallbacksPerSecond'])]) + ' |')
    lines += ['', '## Adapter semantics', '']
    for solution in sorted({row['solution'] for row in aggregates}):
        row = next(row for row in aggregates if row['solution'] == solution)
        lines.append(f'- **{solution}**: {row["predictionScope"]}. Replay classification: {row["replayDefinition"]}.')
    work_rows = [row for row in aggregates if row['workCountersPerSecond'] is not None]
    if work_rows:
        lines += ['', '## PurrDiction work counters', '',
                  'Existing per-world counters are read outside CPU timing, including release runs with detailed diagnostics off. Client peers are averaged before repeat medians. These describe work; CPU scores are not normalized.', '',
                  'Prepared delta frames/section bits include bodies replaced before sending. State/input sections exclude full frames and trailing event sections. Frame body bytes are before RPC compression, headers and fragmentation; they are not wire bandwidth. Start/end snapshots and lead-adjustment counters remain in raw JSON.', '',
                  '| Policy | Objects | Role | Prepared deltas/s | Prepared state kbit/s | Prepared input kbit/s | Frame body KiB/s | Received frames/s | Input sends/s |',
                  '|---|---:|---|---:|---:|---:|---:|---:|---:|']
        for row in work_rows:
            work = row['workCountersPerSecond']
            lines.append('| ' + ' | '.join([row['solution'], str(row['objects']), row['role'],
                number(work['deltaFramesWrittenTotal']), number(work['deltaSectionStateBitsTotal'], 1000),
                number(work['deltaSectionInputBitsTotal'], 1000),
                number(work['deltaFrameBytesTotal'] + work['fullFrameBytesTotal'], 1024),
                number(work['framesReceivedTotal']), number(work['inputSendsTotal'])]) + ' |')
    if failures:
        lines += ['', '## Incomplete cases', '']
        lines += [f'- {item["case"]["solution"]}, case {item["case"]["id"]}: {item["error"]}' for item in failures]
    lines += ['', 'Raw JSON contains per-peer counters, exact final state, native PurrDiction pass telemetry and build/source provenance. Validation happens after timing and requires every final state to equal server authority. This does not measure visual correction quality, input-to-display latency, physics interactions, or history growth under long latency.', '']
    (output / 'latest.md').write_text('\n'.join(lines))
    # Standalone artifact: no external dependencies, script tags or injected report HTML.
    table = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(row.get(key, "")))}</td>' for key in
        ('solution', 'clients', 'tickRate', 'objects', 'role', 'repeats', 'cpuPercent', 'p95FrameMs', 'callbacksPerSecond', 'replayCallbacksPerSecond')) + '</tr>' for row in aggregates)
    report = '<!doctype html><meta charset="utf-8"><title>Prediction benchmark</title><style>body{font:16px system-ui;margin:32px;line-height:1.5}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccc}pre{white-space:pre-wrap}</style>'
    report += '<h1>Prediction benchmark</h1><p>Diagnostic baseline; shared hardware and native prediction scopes differ. <a href="latest.json">Raw data</a></p>'
    report += '<table><tr>' + ''.join(f'<th>{label}</th>' for label in ('Solution', 'Clients', 'Hz', 'Objects', 'Role', 'Repeats', 'CPU %', 'Frame p95 ms', 'Calls/s', 'Native replay calls/s')) + '</tr>' + table + '</table>'
    report += '<pre>' + html.escape('\n'.join(lines)) + '</pre>'
    (output / 'index.html').write_text(report)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = render(args.source, args.output)
    print(f'{len(result["groups"])} result groups; {len(result["failures"])} incomplete cases')
