#!/usr/bin/env python3
"""Regression checks for delivery aggregation and report notes (requires bash, jq and Node)."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
GIT_BASH = Path('C:/Program Files/Git/bin/bash.exe')
BASH = str(GIT_BASH) if os.name == 'nt' and GIT_BASH.exists() else shutil.which('bash')


def workflow_script(workflow, step):
    lines = (SCRIPTS.parent / 'workflows' / workflow).read_text(encoding='utf-8').splitlines()
    start = lines.index('      - name: ' + step)
    start = lines.index('        run: |', start) + 1
    script = []
    for line in lines[start:]:
        if line and not line.startswith('          '):
            break
        script.append(line[10:])
    return '\n'.join(script)


def sample(name):
    row = dict.fromkeys(('txBytesPerSec', 'rxBytesPerSec', 'txPacketsPerSec', 'inputsPerSec',
                         'cpuPercent', 'avgFrameMs', 'p95FrameMs', 'p99FrameMs', 'gcCollections',
                         'managedHeapBytes', 'peakRssBytes', 'rttAvgMs', 'rttP50Ms', 'rttP95Ms',
                         'rttP99Ms', 'rttSamples'), 0)
    row.update(name=name, objects=10, connections=1, truncated=False, deliveryComplete=True,
               rpcsSent=600, rpcsReceived=600, rpcsReceivedPerSec=200,
               syncObservationAvailable=name == 'SyncVars', syncObservedChangesPerSec=200,
               syncSilenceAvgMs=85, syncSilenceMaxMs=205,
               finalStateObjects=10, finalStateHash='abcd000012345678')
    return row


class DeliveryReportChecks(unittest.TestCase):
    def test_resource_outcomes_survive_aggregation_without_inventing_windows(self):
        script = workflow_script('benchmark.yml', 'Render per-session datapoints')
        for case in ('partial', 'missing', 'invalid', 'time', 'harness_time', 'crash', 'host_oom'):
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix='bench-resource-report-') as tmp:
                root = Path(tmp)
                scripts = root / '.github/scripts'
                scripts.mkdir(parents=True)
                shutil.copy2(SCRIPTS / 'bench-aggregate.sh', scripts / 'bench-aggregate.sh')
                results = root / 'all/results/c100t60/ngo'
                results.mkdir(parents=True)
                server = dict(expectedClients=100, connectedAtStart=100, completed=False, tickRate=60,
                              targetFps=60, tests=[sample('Idle')])
                process = dict(exitCode=-9, status='resource-limit-exceeded', reason='memory',
                               limit=8 * 1024 ** 3, memoryLimitBytes=8 * 1024 ** 3,
                               memoryEvents=dict(oom=1), cgroupPeakBytes=8 * 1024 ** 3,
                               watchdogSeconds=900, harnessMaxSeconds=780)
                if case == 'time':
                    process.update(exitCode=124, reason='time', limit=900)
                if case in ('harness_time', 'crash'):
                    process.update(exitCode=0, status='exited', memoryEvents={})
                if case == 'harness_time':
                    server.update(error='timeout', completed=True)
                if case == 'host_oom':
                    process.update(status='host-oom')
                if case != 'missing':
                    (results / 'server.json').write_text('{' if case == 'invalid' else json.dumps(server), encoding='utf-8')
                (results / 'process-server.json').write_text(json.dumps(process), encoding='utf-8')
                env = dict(os.environ, PLAN=json.dumps(dict(cases=[dict(netcode='ngo', tag='c100t60', total=100)])),
                           BENCH_SECONDS='10', BENCH_OBJECTS='100', GITHUB_STEP_SUMMARY=(root / 'summary.md').as_posix())
                output = subprocess.run([BASH, '-euo', 'pipefail', '-c', script], cwd=root, env=env,
                                        capture_output=True, text=True, encoding='utf-8', timeout=30)
                self.assertEqual(output.returncode, 0, output.stdout + output.stderr)
                data = json.loads((root / 'scaling/dp-ngo-c100t60.json').read_text())
                self.assertEqual(data['meta']['process'], process)
                self.assertEqual(data['meta']['expectedClients'], 100)
                self.assertEqual(data['server'], {} if case in ('missing', 'invalid') else {'Idle': server['tests'][0]})
                error = data['meta']['serverError']
                self.assertIn({'time': '900s time', 'harness_time': '780s harness time',
                               'crash': 'did not complete', 'host_oom': 'infrastructure failure'}.get(case, '8 GiB memory'), error)

    def test_scoring_distinguishes_inherited_rss_stalls_and_incomplete_runs_for_every_netcode(self):
        spec = importlib.util.spec_from_file_location('summary', SCRIPTS / 'render-summary.py')
        summary = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(summary)
        fixture = dict(size=100, tick=60, connections=100, clients={}, meta=dict(expectedClients=100),
                       server={t: dict(sample(t), connections=100, avgFps=60, p99FrameMs=16.7,
                                       gcAllocBytesPerSec=1024, peakRssBytes=52 * 1024 ** 3)
                               for t in ['Idle'] + summary.SCORE_TESTS})
        fixture['server']['Idle']['peakRssBytes'] = 200 * 1024 ** 2
        runs = [dict(copy.deepcopy(fixture), netcode=n) for n in summary.ORDER]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = root / 'source.json', root / 'report.html'
            source.write_text(json.dumps(runs), encoding='utf-8')
            subprocess.run([sys.executable, str(SCRIPTS / 'render-report.py'), str(source), str(output)], check=True, capture_output=True)
            js = re.search(r'<script>\s*(.*?)</script>', output.read_text(encoding='utf-8'), re.S).group(1)
            context = "const assert = require('node:assert/strict'); const elements = {}; const document = {getElementById: id => elements[id] ||= {}};\n"
            checks = r'''
const sc = scenarios[0];
assert.deepEqual(CATEGORIES.map(c => c.tests), [['MoveY', 'MoveWander', 'SyncVars'], ['SendRPC', 'ClientInput'], ['SpawnChurn']]);
for (const n of netcodes) {
  const r = run(n, sc);
  // Every category is isolated, for every netcode, with and without a process-level error.
  for (const failedCategory of CATEGORIES) {
    const t = failedCategory.tests[0], saved = r.server[t];
    delete r.server[t];
    for (const processError of [null, 'resource limit exceeded (8 GiB memory)']) {
      r.meta.serverError = processError;
      for (const c of CATEGORIES) {
        state.category = c.id;
        buildScorecard();
        assert.equal(!!categoryFailure(n, sc, c.tests), c === failedCategory);
        assert.equal(score(sc, c.tests).wins.cpu[n], c === failedCategory ? 0 : c.tests.length);
        assert.ok(elements['score-hint'].textContent.startsWith(c.hint));
        assert.ok(!elements.scorecard.innerHTML.includes('Peak RSS'));
      }
    }
    delete r.meta.serverError;
    r.server[t] = saved;
  }
  state.category = 'state';
  assert.equal(stalledAnywhere(n, sc), false); // 52 GiB inherited VmHWM isn't a local stall.
  r.server.SendRPC.p99FrameMs = 9000;
  assert.equal(stalled(n, sc, 'SendRPC'), true);
  assert.equal(stalled(n, sc, 'ClientInput'), false);
  r.server.SendRPC.p99FrameMs = 16.7;
  r.meta.serverError = 'resource limit exceeded (8 GiB memory)';
  buildScorecard();
  assert.ok(!elements.scorecard.innerHTML.includes(r.meta.serverError));
  buildNotes();
  assert.ok(elements.warnings.innerHTML.includes(r.meta.serverError));
  assert.equal(score(sc).wins.cpu[n], 0);
  assert.equal(marginal(n, sc, sc, 'cpu', 1), null);
  assert.equal(stalledAnywhere(n, sc), false); // Failure is not "stalled 6/6".
  delete r.meta.serverError;
  const saved = r.server.SyncVars;
  delete r.server.SyncVars;
  assert.ok(runFailure(n, sc).startsWith('incomplete'));
  assert.equal(score(sc).wins.cpu[n], 0);
  r.server.SyncVars = saved;
  r.server.SyncVars.truncated = true;
  assert.ok(runFailure(n, sc));
  r.server.SyncVars.truncated = false;
}
'''
            result = subprocess.run(['node'], input=context + js[:js.index('\nbuildHeader();')] + checks,
                                    text=True, capture_output=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
        for r in runs:
            n = r['netcode']
            by = {(n, (100, 60)): r}
            for _, failed_tests in summary.CATEGORIES:
                for process_error in (None, 'resource limit exceeded (8 GiB memory)'):
                    item = copy.deepcopy(r)
                    del item['server'][failed_tests[0]]
                    item['meta']['serverError'] = process_error
                    for _, tests in summary.CATEGORIES:
                        row = summary.scorecard([n], {(n, (100, 60)): item}, (100, 60), tests)[n]
                        self.assertEqual(row['cpu'] is None, tests == failed_tests)
                        self.assertEqual(row['wins'], 0 if tests == failed_tests else len(tests) * 3)
                        self.assertEqual(bool(row['error']), tests == failed_tests)
            self.assertFalse(summary.stalled_anywhere(r))
            r['server']['SendRPC']['p99FrameMs'] = 9000
            self.assertTrue(summary.stalled(r, 'SendRPC'))
            self.assertFalse(summary.stalled(r, 'ClientInput'))
            r['server']['SendRPC']['p99FrameMs'] = 16.7
            for failure in ('resource', 'missing', 'truncated'):
                item = copy.deepcopy(r)
                if failure == 'resource':
                    item['meta']['serverError'] = 'resource limit exceeded (8 GiB memory)'
                elif failure == 'missing':
                    del item['server']['SyncVars']
                else:
                    item['server']['SyncVars']['truncated'] = True
                rows = summary.scorecard([n], {(n, (100, 60)): item}, (100, 60))
                self.assertIsNone(rows[n]['bw'])
                self.assertIsNone(rows[n]['cpu'])
                self.assertEqual(rows[n]['wins'], 0)
                self.assertEqual(rows[n]['stalls'], 0)

    def test_chart_selector_excludes_single_test_diagnostics_and_rtt(self):
        tests = ('Idle', 'MoveY', 'MoveWander', 'SyncVars', 'SendRPC', 'ClientInput', 'Static', 'SpawnChurn')
        server = {t: dict(sample(t), gcAllocBytesPerSec=1024, rpcsSentPerSec=200,
                          syncMutationsPerSec=200, inputsPerSec=20) for t in tests}
        clients = {t: dict(n=1, rxBytesPerSec=1024, txBytesPerSec=512,
                           rttP50Ms=10 if t == 'Idle' else 12, rpcsReceivedPerSec=200,
                           syncObservationClients=1, syncObservedChangesPerSec=200,
                           syncSilenceAvgMs=85, syncSilenceMaxMs=205,
                           rpcDeliveryChecked=1, rpcDeliveryMatched=1,
                           syncStateChecked=1, syncStateMatched=1) for t in tests}
        data = dict(netcode='mirror', size=1, tick=20, connections=1, server=server, clients=clients,
                    meta=dict(expectedClients=1, connectedAtStart=1, measuredClients=1, tickRate=20))
        with tempfile.TemporaryDirectory(prefix='bench-chart-metrics-') as tmp:
            root = Path(tmp)
            source = root / 'results.json'
            source.write_text(json.dumps(data), encoding='utf-8')
            rendered = root / 'report.html'
            subprocess.run([sys.executable, str(SCRIPTS / 'render-report.py'), str(source), str(rendered)],
                           check=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
            # Check future rendered reports and the current checked-in report, without rewriting its data.
            for path in (rendered, SCRIPTS.parent.parent / 'docs/index.html'):
                with self.subTest(report=path.name):
                    page = path.read_text(encoding='utf-8')
                    js = re.search(r'<script>\s*(.*?)</script>', page, re.S).group(1)
                    subprocess.run(['node', '--check'], input=js, text=True, encoding='utf-8',
                                   check=True, capture_output=True, timeout=30)
                    context = '''
const assert = require('node:assert/strict');
const elements = {};
const document = {
  querySelectorAll: () => [],
  getElementById: id => elements[id] ||= {addEventListener() {}}
};
'''
                    checks = r'''
const expected = ['srvDown', 'cpu', 'cliDown', 'srvUp', 'cliUp', 'p99', 'pkts', 'alloc', 'gc', 'rss'];
assert.deepEqual(METRICS.map(m => m.id), expected);
assert.deepEqual(AVAILABLE.map(m => m.id), expected);
buildControls();
assert.deepEqual([...elements.metrics.innerHTML.matchAll(/data-id="([^"]+)"/g)].map(m => m[1]), expected);
assert.equal(state.metric, 'srvDown');
// Removing chart options must not discard the diagnostics or hide delivery problems.
assert.ok(DATA.runs.some(r => r.server.SendRPC?.rpcsSentPerSec > 0));
assert.ok(DATA.runs.some(r => r.server.SyncVars?.syncMutationsPerSec > 0));
assert.ok(DATA.runs.some(r => r.clients.SyncVars?.syncSilenceAvgMs > 0));
assert.ok(DATA.runs.some(r => r.clients.Idle?.rttP50Ms > 0));
buildNotes();
assert.ok(!elements.warnings.innerHTML.includes('complete reliable RPC delivery'));
assert.ok(!elements.warnings.innerHTML.includes('field silence'));
assert.ok(!elements.warnings.innerHTML.includes('state matched'));
if (DATA.runs.length === 1) assert.equal(elements.warnings.hidden, true);
buildScorecard();
assert.ok(elements['score-hint'].textContent.split(/\s+/).length <= 35);
assert.ok(elements['score-hint'].textContent.includes('Incomplete or stalled categories have no averages'));
assert.ok(METRICS.every(m => m.hint.split(/\s+/).length <= 15));
'''
                    subprocess.run(['node'], input=context + js[:js.index('\nbuildHeader();')] + checks,
                                   text=True, encoding='utf-8', check=True, capture_output=True, timeout=30)

    def test_no_artifacts_produces_empty_results_without_publishing_a_report(self):
        merge = workflow_script('scaling.yml', 'Merge datapoints')
        render = workflow_script('scaling.yml', 'Render interactive report')
        for expected, status in ((15, 'skipped'), (0, 'failure'), (0, 'success')):
            with self.subTest(expected=expected, status=status), tempfile.TemporaryDirectory(prefix='bench-empty-report-') as tmp:
                root = Path(tmp)
                scripts = root / '.github/scripts'
                scripts.mkdir(parents=True)
                for name in ('bench-scaling.sh', 'versions.sh'):
                    shutil.copy2(SCRIPTS / name, scripts / name)
                # Minimal project metadata for the real versions.sh; no downloaded artifact directory.
                for name, content in {
                    'purrnet/Assets/PurrNet/package.json': '{"version":"test"}',
                    'fishnet/Assets/FishNet/package.json': '{"version":"test"}',
                    'mirror/Assets/Mirror/version.txt': 'test',
                    'ngo/Packages/manifest.json': '{"dependencies":{"com.unity.netcode.gameobjects":"test"}}',
                    'fusion/Assets/Photon/Fusion/build_info.txt': 'build: test',
                    'purrnet/ProjectSettings/ProjectVersion.txt': 'm_EditorVersion: test',
                }.items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding='utf-8')
                env = dict(os.environ, BENCH_RESULT=status, GITHUB_OUTPUT=(root / 'outputs').as_posix(),
                           GITHUB_STEP_SUMMARY=(root / 'summary.md').as_posix())
                self.assertFalse((root / 'all').exists())
                result = subprocess.run([BASH, '-euo', 'pipefail', '-c', merge], cwd=root, env=env,
                                        capture_output=True, text=True, encoding='utf-8', timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads((root / 'results-out/scaling.json').read_text()), [])
                self.assertTrue((root / 'all/versions.json').is_file())
                replacements = {
                    'github.server_url': 'https://github.com',
                    'github.repository': 'example/benchmark',
                    'github.run_id': '123',
                    'github.repository_owner': 'example',
                    'github.event.repository.name': 'benchmark',
                    "needs.prep.outputs.expected || '0'": str(expected),
                }
                script = render
                for expression, value in replacements.items():
                    script = script.replace('${{ ' + expression + ' }}', value)
                self.assertNotIn('${{', script)
                result = subprocess.run([BASH, '-euo', 'pipefail', '-c', script], cwd=root, env=env,
                                        capture_output=True, text=True, encoding='utf-8', timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('No datapoints; skipping report', result.stdout)
                outputs = (root / 'outputs').read_text().splitlines()
                self.assertIn('count=0', outputs)
                self.assertIn('complete=false', outputs)
                self.assertFalse((root / 'results-out/report.html').exists())
                self.assertIn('No datapoints collected', (root / 'summary.md').read_text())

    def test_fleet_artifact_layout_uses_each_session_and_only_measured_clients(self):
        # Execute the actual workflow's aggregation shell, not a second implementation of it.
        script = workflow_script('benchmark.yml', 'Render per-session datapoints')
        self.assertTrue(script)
        with tempfile.TemporaryDirectory(prefix='bench-fleet-report-') as tmp:
            root = Path(tmp)
            scripts = root / '.github/scripts'
            scripts.mkdir(parents=True)
            shutil.copy2(SCRIPTS / 'bench-aggregate.sh', scripts / 'bench-aggregate.sh')
            cases = []
            for tick in (20, 60):
                tag = f'c1t{tick}'
                cases.append(dict(netcode='mirror', tag=tag, total=1))
                results = root / 'all/results' / tag / 'mirror'
                results.mkdir(parents=True)
                server = dict(expectedClients=1, connectedAtStart=1, completed=True, tickRate=tick,
                              targetFps=60, tests=[sample('SyncVars')])
                client = copy.deepcopy(server)
                client['measured'] = True
                client['tests'][0]['syncObservedChangesPerSec'] = tick * 10
                (results / 'server.json').write_text(json.dumps(server), encoding='utf-8')
                (results / 'client-1.json').write_text(json.dumps(client), encoding='utf-8')
                # Even if a diagnostic file were accidentally present, it must not enter the average.
                client['measured'] = False
                client['tests'][0]['syncObservedChangesPerSec'] = 99999
                (results / 'loadgen-1-1.json').write_text(json.dumps(client), encoding='utf-8')
            env = dict(os.environ, PLAN=json.dumps(dict(cases=cases)), BENCH_SECONDS='10', BENCH_OBJECTS='100',
                       GITHUB_STEP_SUMMARY=(root / 'summary.md').as_posix())
            subprocess.run([BASH, '-euo', 'pipefail', '-c', script], cwd=root, env=env,
                           check=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(len(list((root / 'scaling').glob('dp-*.json'))), 2)
            for tick in (20, 60):
                data = json.loads((root / f'scaling/dp-mirror-c1t{tick}.json').read_text(encoding='utf-8'))
                self.assertEqual(data['tick'], tick)
                self.assertEqual(data['meta']['measuredClients'], 1)
                self.assertEqual(data['clients']['SyncVars']['syncObservedChangesPerSec'], tick * 10)

    def test_delivery_cases(self):
        for case in ('match', 'mismatch', 'client_incomplete', 'server_incomplete', 'legacy', 'missing_client', 'coalesced', 'no_observation', 'mixed_clients'):
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix='bench-report-') as tmp:
                root = Path(tmp)
                results = root / 'results'
                results.mkdir()
                server = dict(expectedClients=1, connectedAtStart=1, completed=True, tickRate=20,
                              targetFps=60, tests=[sample('SendRPC'), sample('SyncVars')])
                client = copy.deepcopy(server)
                client['measured'] = True
                if case == 'mismatch':
                    client['tests'][0]['rpcsReceived'] -= 1
                    client['tests'][1]['finalStateHash'] = 'different'
                if case == 'coalesced':
                    client['tests'][1]['syncObservedChangesPerSec'] = 120
                    client['tests'][1]['syncSilenceMaxMs'] = 350
                if case == 'no_observation':
                    client['tests'][1]['syncObservationAvailable'] = False
                if case in ('client_incomplete', 'server_incomplete'):
                    for row in (client if case == 'client_incomplete' else server)['tests']:
                        row['deliveryComplete'] = False
                if case == 'legacy':
                    for row in server['tests'] + client['tests']:
                        for key in ('deliveryComplete', 'rpcsSent', 'rpcsReceived', 'rpcsReceivedPerSec',
                                    'finalStateObjects', 'finalStateHash', 'syncObservationAvailable',
                                    'syncObservedChangesPerSec', 'syncSilenceAvgMs', 'syncSilenceMaxMs'):
                            row.pop(key)
                (results / 'server.json').write_text(json.dumps(server), encoding='utf-8')
                if case != 'missing_client':
                    (results / 'client-0.json').write_text(json.dumps(client), encoding='utf-8')
                if case == 'mixed_clients':
                    missing_observation = copy.deepcopy(client)
                    missing_observation['tests'][1]['syncObservationAvailable'] = False
                    # Defaults from an unobserved client must not pull down the valid-client averages.
                    missing_observation['tests'][1]['syncObservedChangesPerSec'] = 0
                    missing_observation['tests'][1]['syncSilenceAvgMs'] = 0
                    missing_observation['tests'][1]['syncSilenceMaxMs'] = 0
                    (results / 'client-1.json').write_text(json.dumps(missing_observation), encoding='utf-8')
                env = dict(os.environ, GITHUB_STEP_SUMMARY=(root / 'summary.md').as_posix())
                subprocess.run([BASH, (SCRIPTS / 'bench-aggregate.sh').as_posix(), results.as_posix(),
                                'mirror', '1', 'c1t20', '2', '10', root.as_posix()],
                               check=True, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
                dp = root / 'dp-mirror-c1t20.json'
                data = json.loads(dp.read_text(encoding='utf-8'))
                summary = (root / 'summary.md').read_text(encoding='utf-8')
                self.assertNotIn('RTT', summary)
                self.assertNotIn('| Samples |', summary)
                checked = 2 if case == 'mixed_clients' else int(case not in ('client_incomplete', 'server_incomplete', 'legacy', 'missing_client'))
                matched = checked if case != 'mismatch' else 0
                if case != 'missing_client':
                    self.assertIn('| Test | Down per client | Up per client | Truncated |', summary)
                    self.assertIn('rttP50Ms', data['clients']['SendRPC'])
                    self.assertEqual(data['clients']['SendRPC']['rpcDeliveryChecked'], checked)
                    self.assertEqual(data['clients']['SendRPC']['rpcDeliveryMatched'], matched)
                    self.assertEqual(data['clients']['SyncVars']['syncStateChecked'], checked)
                    self.assertEqual(data['clients']['SyncVars']['syncStateMatched'], matched)
                    if case == 'legacy':
                        self.assertIsNone(data['clients']['SendRPC']['rpcsReceivedPerSec'])
                    observed = case not in ('legacy', 'no_observation')
                    sync = data['clients']['SyncVars']
                    self.assertEqual(sync['syncObservationClients'], int(observed))
                    self.assertEqual(sync['syncObservedChangesPerSec'], (120 if case == 'coalesced' else 200) if observed else None)
                    self.assertEqual(sync['syncSilenceAvgMs'], 85 if observed else None)
                    self.assertEqual(sync['syncSilenceMaxMs'], (350 if case == 'coalesced' else 205) if observed else None)
                html = root / 'report.html'
                subprocess.run([sys.executable, str(SCRIPTS / 'render-report.py'), str(dp), str(html)],
                               check=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
                page = html.read_text(encoding='utf-8')
                js = re.search(r'<script>\s*(.*?)</script>', page, re.S).group(1)
                subprocess.run(['node', '--check'], input=js, text=True, encoding='utf-8', check=True, capture_output=True, timeout=30)
                # Execute the actual notes function with a minimal DOM, not a copy of its logic.
                notes = js[js.index('function buildNotes()'):js.index('\nbuildHeader();')]
                context = 'const fixture = ' + json.dumps(data) + ';\n' + '''
const netcodes = ['mirror'], scenarios = [{size: 1, tick: 20}];
const NAMES = {mirror: 'Mirror'}, TESTS = ['SendRPC', 'SyncVars'];
const run = () => fixture, scLabel = () => '1 at 20 Hz';
const el = {}, document = {getElementById: () => el};
'''
                output = subprocess.run(['node'], input=context + notes + '\nbuildNotes(); console.log(el.innerHTML);',
                                        text=True, encoding='utf-8', check=True, capture_output=True, timeout=30).stdout
                if case == 'mismatch':
                    self.assertIn(f'incomplete RPC delivery on {checked - matched}/{checked} checked clients', output)
                    self.assertIn(f'final-state mismatch on {checked - matched}/{checked} checked clients', output)
                else:
                    self.assertNotIn('checked clients', output)
                self.assertEqual('delivery checks incomplete' in output,
                                 case in ('client_incomplete', 'server_incomplete', 'missing_client'))
                self.assertEqual('observations missing or incomplete' in output,
                                 case in ('missing_client', 'no_observation', 'mixed_clients'))
                self.assertNotIn('field silence', output)
                self.assertNotIn('client-visible SyncVar changes', output)
                self.assertNotIn('state matched', output)
                if case in ('match', 'coalesced', 'legacy'):
                    self.assertEqual(output.strip(), '')


if __name__ == '__main__':
    unittest.main()
