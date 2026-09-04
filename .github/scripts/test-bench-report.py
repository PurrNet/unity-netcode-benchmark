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
               finalStateObjects=10, finalStateHash='abcd000012345678')
    return row


class DeliveryReportChecks(unittest.TestCase):
    def test_delivery_cases(self):
        for case in ('match', 'mismatch', 'client_incomplete', 'server_incomplete', 'legacy', 'missing_client'):
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
                if case in ('client_incomplete', 'server_incomplete'):
                    for row in (client if case == 'client_incomplete' else server)['tests']:
                        row['deliveryComplete'] = False
                if case == 'legacy':
                    for row in server['tests'] + client['tests']:
                        for key in ('deliveryComplete', 'rpcsSent', 'rpcsReceived', 'rpcsReceivedPerSec',
                                    'finalStateObjects', 'finalStateHash'):
                            row.pop(key)
                (results / 'server.json').write_text(json.dumps(server), encoding='utf-8')
                if case != 'missing_client':
                    (results / 'client-0.json').write_text(json.dumps(client), encoding='utf-8')
                env = dict(os.environ, GITHUB_STEP_SUMMARY=(root / 'summary.md').as_posix())
                subprocess.run([BASH, (SCRIPTS / 'bench-aggregate.sh').as_posix(), results.as_posix(),
                                'mirror', '1', 'c1t20', '2', '10', root.as_posix()],
                               check=True, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
                dp = root / 'dp-mirror-c1t20.json'
                data = json.loads(dp.read_text(encoding='utf-8'))
                checked = int(case in ('match', 'mismatch'))
                matched = int(case == 'match')
                if case != 'missing_client':
                    self.assertEqual(data['clients']['SendRPC']['rpcDeliveryChecked'], checked)
                    self.assertEqual(data['clients']['SendRPC']['rpcDeliveryMatched'], matched)
                    self.assertEqual(data['clients']['SyncVars']['syncStateChecked'], checked)
                    self.assertEqual(data['clients']['SyncVars']['syncStateMatched'], matched)
                    if case == 'legacy':
                        self.assertIsNone(data['clients']['SendRPC']['rpcsReceivedPerSec'])
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
                    self.assertIn(f'RPC delivery on {matched}/1 checked clients', output)
                    self.assertIn(f'SyncVar state matched on {matched}/1 checked clients', output)
                else:
                    self.assertNotIn('checked clients', output)
                self.assertEqual('validation is incomplete' in output,
                                 case in ('client_incomplete', 'server_incomplete', 'missing_client'))


if __name__ == '__main__':
    unittest.main()
