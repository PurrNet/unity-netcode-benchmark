#!/usr/bin/env python3
"""Arrange both single-artifact and multi-artifact download layouts."""
import argparse
from pathlib import Path
import shutil


def arrange(source, output, solutions, purrdiction_source=None):
    names = [name.strip() for name in solutions.split(',')]
    if not names or len(set(names)) != len(names) or any(name not in ('purrdiction', 'purrdiction-owned', 'purrdiction-player-input', 'fishnet', 'fusion') for name in names):
        raise ValueError('Invalid prediction solutions')
    source, output = source.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(output)
    overrides = [name for name in names if name.startswith('purrdiction')] if purrdiction_source else []
    if purrdiction_source and not overrides:
        raise ValueError('PurrDiction source override requires a PurrDiction solution')
    players = []
    for root, selected in ((source, [name for name in names if name not in overrides]),
                           (Path(purrdiction_source).resolve() if purrdiction_source else None, overrides)):
        if not selected:
            continue
        if (root / 'PredictionBench').is_file():
            if len(selected) != 1:
                raise ValueError('A flat artifact download requires exactly one solution per source')
            players.append((selected[0], root))
        else:
            players.extend((name, root / ('prediction-player-' + name)) for name in selected)
    for _, player in players:
        if not (player / 'PredictionBench').is_file():
            raise FileNotFoundError(player / 'PredictionBench')
    for name, player in players:
        destination = output / name
        shutil.copytree(player, destination)
        executable = destination / 'PredictionBench'
        executable.chmod(executable.stat().st_mode | 0o111)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('downloaded-players'))
    parser.add_argument('--output', type=Path, default=Path('prediction-players'))
    parser.add_argument('--solutions', required=True)
    parser.add_argument('--purrdiction-source', type=Path,
                        help='Use this frozen artifact source for selected PurrDiction adapters only')
    args = parser.parse_args()
    arrange(args.source, args.output, args.solutions, args.purrdiction_source)
