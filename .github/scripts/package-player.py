#!/usr/bin/env python3
"""Package identical player bytes separately from Unity's non-runtime build diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def inventory(root):
    hashes = {}
    for path in sorted(root.rglob('*')):
        if path.is_file() and path != root / 'build-provenance.json':
            with path.open('rb') as stream:
                hashes[path.relative_to(root).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return hashes


def package(source, destination, key, revision):
    if destination.exists():
        raise ValueError(f'Refusing to overwrite package: {destination}')
    runtime = destination / 'runtime'
    diagnostics = destination / 'diagnostics'
    runtime.mkdir(parents=True)
    diagnostics.mkdir()
    for item in source.iterdir():
        target = diagnostics if item.name == 'NetBench_BackUpThisFolder_ButDontShipItWithYourGame' else runtime
        if item.is_dir():
            shutil.copytree(item, target / item.name)
        else:
            shutil.copy2(item, target / item.name)
    provenance = {'cacheKey': key, 'sourceRevision': revision,
                  'runtimeSha256': inventory(runtime), 'diagnosticsSha256': inventory(diagnostics)}
    (runtime / 'build-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    verify(destination, key)


def verify(destination, key):
    runtime = destination / 'runtime'
    provenance = json.loads((runtime / 'build-provenance.json').read_text())
    if provenance['cacheKey'] != key:
        raise ValueError('Player cache key does not match the requested build inputs')
    for name in ('NetBench', 'GameAssembly.so', 'UnityPlayer.so', 'NetBench_Data/globalgamemanagers'):
        if not (runtime / name).is_file() or not (runtime / name).stat().st_size:
            raise ValueError(f'Missing runtime file: {name}')
    if inventory(runtime) != provenance['runtimeSha256']:
        raise ValueError('Runtime payload failed SHA-256 verification')
    if inventory(destination / 'diagnostics') != provenance['diagnosticsSha256']:
        raise ValueError('Build diagnostics failed SHA-256 verification')
    for folder in ('runtime', 'diagnostics'):
        size = sum(p.stat().st_size for p in (destination / folder).rglob('*') if p.is_file())
        print(f'{folder}: {size:,} bytes', flush=True)
    print(f"Verified player built from {provenance['sourceRevision']}", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('package', 'verify'))
    parser.add_argument('--source', type=Path, default=Path('build/StandaloneLinux64'))
    parser.add_argument('--destination', type=Path, default=Path('build/player-package'))
    parser.add_argument('--key', required=True)
    parser.add_argument('--revision', default='')
    args = parser.parse_args()
    if args.operation == 'package':
        package(args.source, args.destination, args.key, args.revision)
    else:
        verify(args.destination, args.key)
