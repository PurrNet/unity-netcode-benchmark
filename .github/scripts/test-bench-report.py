#!/usr/bin/env python3
"""Regression checks for delivery aggregation and report notes (requires bash, jq and Node)."""
import copy
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
    def test_fleet_artifact_layout_uses_each_session_and_only_measured_clients(self):
        # Execute the actual workflow's aggregation shell, not a second implementation of it.
        lines = (SCRIPTS.parent / 'workflows/benchmark.yml').read_text(encoding='utf-8').splitlines()
        start = lines.index('      - name: Render per-session datapoints') + 2
        script = []
        for line in lines[start:]:
            if line and not line.startswith('          '):
                break
            script.append(line[10:])
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
            subprocess.run([BASH, '-euo', 'pipefail', '-c', '\n'.join(script)], cwd=root, env=env,
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
                checked = 2 if case == 'mixed_clients' else int(case not in ('client_incomplete', 'server_incomplete', 'legacy', 'missing_client'))
                matched = checked if case != 'mismatch' else 0
                if case != 'missing_client':
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
                if checked:
                    self.assertIn(f'RPC delivery on {matched}/{checked} checked clients', output)
                    self.assertIn(f'SyncVar state matched on {matched}/{checked} checked clients', output)
                else:
                    self.assertNotIn('checked clients', output)
                self.assertEqual('validation is incomplete' in output,
                                 case in ('client_incomplete', 'server_incomplete', 'missing_client'))
                self.assertEqual('observation is missing or incomplete' in output,
                                 case in ('missing_client', 'no_observation', 'mixed_clients'))
                if case == 'coalesced':
                    self.assertIn('client-visible SyncVar changes 120.0/s', output)
                    self.assertIn('nominal 200/s', output)
                    self.assertIn('field silence 350.0 ms', output)


if __name__ == '__main__':
    unittest.main()
