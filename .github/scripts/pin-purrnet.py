#!/usr/bin/env python3
"""Resolve a PurrNet git ref to a commit and, with --write, pin the purrnet project to it.

Usage: pin-purrnet.py [--write] <ref>

<ref> is a branch (dev), a tag (v1.24.0-beta.19) or a full commit hash. Prints the commit and, on
GitHub Actions, writes `sha=<commit>` to $GITHUB_OUTPUT.

--write points purrnet/Packages/manifest.json at that exact commit and drops PurrNet's entry from
packages-lock.json, so Unity resolves the pinned commit and the player cache key (which hashes
Packages/) changes exactly when PurrNet does. A branch name in the manifest would not do: Unity
keeps using the commit in the lock file, and the cache would serve the old player.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/PurrNet/PurrNet.git"
PACKAGE = "dev.purrnet.purrnet"
URL = REPO + "?path=/Assets/PurrNet#{rev}"
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "purrnet" / "Packages" / "manifest.json"
LOCK = ROOT / "purrnet" / "Packages" / "packages-lock.json"


def resolve(ref):
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        return ref
    out = subprocess.run(["git", "ls-remote", REPO, ref], check=True, capture_output=True, text=True).stdout
    refs = dict(reversed(line.split("\t", 1)) for line in out.splitlines() if "\t" in line)
    # An annotated tag's commit is its peeled entry (^{}); a branch or lightweight tag has none.
    for name in (f"refs/tags/{ref}^{{}}", f"refs/tags/{ref}", f"refs/heads/{ref}"):
        if name in refs:
            return refs[name]
    sys.exit(f"pin-purrnet: {ref!r} is not a branch, tag or commit of {REPO}")


def write(sha):
    # Replace only the URL, keeping the manifest's formatting and line endings.
    text = MANIFEST.read_text(encoding="utf-8")
    pattern = re.compile(r'("' + re.escape(PACKAGE) + r'"\s*:\s*")[^"]*(")')
    if not pattern.search(text):
        sys.exit(f"pin-purrnet: {PACKAGE} is not in {MANIFEST}")
    MANIFEST.write_text(pattern.sub(lambda m: m.group(1) + URL.format(rev=sha) + m.group(2), text, count=1),
                        encoding="utf-8", newline="")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    if lock.get("dependencies", {}).pop(PACKAGE, None) is not None:
        LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ref")
    ap.add_argument("--write", action="store_true", help="pin purrnet/Packages to the resolved commit")
    args = ap.parse_args()
    sha = resolve(args.ref.strip())
    if args.write:
        write(sha)
    print(sha)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"sha={sha}\n")


if __name__ == "__main__":
    main()
