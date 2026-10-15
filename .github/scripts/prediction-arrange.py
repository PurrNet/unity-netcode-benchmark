#!/usr/bin/env python3
"""Arrange both single-artifact and multi-artifact download layouts."""
import argparse
from pathlib import Path
import shutil


def arrange(source, output, solutions):
    names = [name.strip() for name in solutions.split(',')]
    if not names or len(set(names)) != len(names) or any(name not in ('purrdiction', 'purrdiction-owned', 'fishnet', 'fusion') for name in names):
        raise ValueError('Invalid prediction solutions')
    source, output = source.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if (source / 'PredictionBench').is_file():
        if len(names) != 1:
            raise ValueError('A flat artifact download requires exactly one solution')
        players = [(names[0], source)]
    else:
        players = [(name, source / ('prediction-player-' + name)) for name in names]
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
    args = parser.parse_args()
    arrange(args.source, args.output, args.solutions)
