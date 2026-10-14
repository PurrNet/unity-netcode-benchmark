#!/usr/bin/env python3
"""Generate isolated prediction projects; existing replication projects stay untouched."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOLUTIONS = ('purrdiction', 'fishnet', 'fusion')


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def prepare(solution, output, prediction_source=None):
    if solution not in SOLUTIONS:
        raise ValueError(f'Unknown prediction solution: {solution}')
    if output.exists():
        raise ValueError(f'Refusing to overwrite generated project: {output}')
    if solution == 'purrdiction' and (prediction_source is None or not (prediction_source / 'Assets/PurrDiction/package.json').is_file()):
        raise ValueError('PurrDiction requires --prediction-source pointing to a source checkout')
    base = ROOT / ('purrnet' if solution == 'purrdiction' else solution)
    for name in ('Assets', 'Packages', 'ProjectSettings'):
        def ignore(path, names):
            if Path(path) == base / 'Assets/_Benchmark':
                return [entry for entry in names if entry not in ('Prefab', 'Prefab.meta', 'Prefabs', 'Prefabs.meta')]
            if Path(path) in (base / 'Assets/_Benchmark/Prefab', base / 'Assets/_Benchmark/Prefabs'):
                return [entry for entry in names if entry not in ('NetworkManager.prefab', 'NetworkManager.prefab.meta')]
            return []
        shutil.copytree(base / name, output / name, ignore=ignore)
    manifest_path = output / 'Packages/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    manifest['dependencies'].pop('com.purrnet.netbench', None)
    locked = json.loads((base / 'Packages/packages-lock.json').read_text())['dependencies']
    for key, value in manifest['dependencies'].items():
        if value.startswith('file:'):
            source = (base / 'Packages' / value[5:]).resolve()
            relative = os.path.relpath(source, output / 'Packages').replace('\\', '/')
            manifest['dependencies'][key] = 'file:' + relative
        elif locked.get(key, {}).get('source') == 'git':
            manifest['dependencies'][key] = value.split('#')[0] + '#' + locked[key]['hash']
    provenance = {'suite': 'prediction', 'solution': solution, 'benchmarkCommit': git(ROOT, 'rev-parse', 'HEAD'),
                  'benchmarkDirty': bool(git(ROOT, 'status', '--porcelain')), 'sourceUnity': (base / 'ProjectSettings/ProjectVersion.txt').read_text().splitlines()[0]}
    if solution == 'purrdiction':
        package = prediction_source / 'Assets/PurrDiction'
        destination = output / 'Assets/PurrDiction'
        destination.mkdir()
        for name in ('Runtime', 'Codegen', 'Editor'):
            shutil.copytree(package / name, destination / name)
            shutil.copy2(package / (name + '.meta'), destination / (name + '.meta'))
        source_manifest = json.loads((prediction_source / 'Packages/manifest.json').read_text())
        # Build PurrDiction against its declared PurrNet revision rather than silently using dev.
        manifest['dependencies']['dev.purrnet.purrnet'] = source_manifest['dependencies']['dev.purrnet.purrnet']
        source_lock_path = prediction_source / 'Packages/packages-lock.json'
        if source_lock_path.is_file():
            source_lock = json.loads(source_lock_path.read_text())['dependencies'].get('dev.purrnet.purrnet', {})
            if source_lock.get('source') == 'git' and source_lock.get('version') == manifest['dependencies']['dev.purrnet.purrnet']:
                manifest['dependencies']['dev.purrnet.purrnet'] = source_lock['version'].split('#')[0] + '#' + source_lock['hash']
        provenance.update(predictionCommit=git(prediction_source, 'rev-parse', 'HEAD'),
                          predictionDirty=bool(git(prediction_source, 'status', '--porcelain')),
                          predictionVersion=json.loads((package / 'package.json').read_text())['version'],
                          purrnetDependency=manifest['dependencies']['dev.purrnet.purrnet'])
    else:
        provenance['vendoredSourceCommit'] = provenance['benchmarkCommit']
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    # This generated manifest can differ from the source; let Unity resolve it afresh.
    (output / 'Packages/packages-lock.json').unlink(missing_ok=True)
    target = output / 'Assets/PredictionBench'
    shutil.copytree(ROOT / 'prediction/Shared', target)
    shutil.copytree(ROOT / 'prediction/Adapters' / solution, target / 'Adapter')
    # Reuse the established load counter implementation, without activating BenchRunner.
    shutil.copy2(ROOT / 'Shared/com.purrnet.netbench/Runtime/LoadSampler.cs', target / 'LoadSampler.cs')
    sampler = target / 'LoadSampler.cs'
    sampler.write_text(sampler.read_text().replace('    public struct ', '    [Serializable]\n    public struct '), encoding='utf-8')
    resources = target / 'Resources'
    resources.mkdir()
    provenance['adapterSha256'] = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(target.rglob('*.cs'))}
    (resources / 'PredictionProvenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    (output / 'prediction-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return provenance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('solution', choices=SOLUTIONS)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prediction-source', type=Path)
    args = parser.parse_args()
    prepare(args.solution, args.output.resolve(), args.prediction_source)
    print(f'Prepared {args.solution} at {args.output}')
