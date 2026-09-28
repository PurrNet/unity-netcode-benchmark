#!/usr/bin/env python3
"""Send benchmark results to purrnet.dev, where /admin/benchmarks keeps every run's history.

  upload-results.py send --data results-out/scaling.json --versions all/versions.json --complete true \\
      [--run-id ID] [--run-url URL] [--commit SHA] [--purrnet-commit SHA] [--config-json JSON] [--ran-at ISO]
  upload-results.py backfill [--dry-run] [--limit N]

`send` uploads one run (the scaling workflow calls it after rendering). `backfill` resends every
published run from this repository's history: each "bench: latest results from run N" commit's
docs/latest.json, with the versions from its latest.md and PurrNet's commit from its lock file.
A run is keyed by its workflow run id, so sending one twice replaces it rather than adding it.

Environment: PURRNET_BENCH_TOKEN (required; the site's BENCHMARK_INGEST_TOKEN) and optionally
PURRNET_BENCH_URL (default https://purrnet.dev/api/internal/benchmarks). Standard library only.
"""
import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_URL = "https://purrnet.dev/api/internal/benchmarks"
REPO_URL = "https://github.com/PurrNet/unity-netcode-benchmark"
ROOT = Path(__file__).resolve().parents[2]
NAMES = {"PurrNet": "purrnet", "FishNet": "fishnet", "Mirror": "mirror", "NGO": "ngo", "Fusion": "fusion", "Unity": "unity"}
RETRY_DELAYS = (5, 20, 60)


def post(payload, url, token):
    """POST gzip JSON; retries network errors, 429 and 5xx. Returns the response body."""
    body = gzip.compress(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    for attempt, delay in enumerate((0,) + RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
            "User-Agent": "unity-netcode-benchmark-uploader",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return json.loads(res.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:500]
            if err.code == 429 or err.code >= 500:
                print(f"upload attempt {attempt + 1}: HTTP {err.code} {detail}", file=sys.stderr)
                continue
            raise SystemExit(f"upload refused: HTTP {err.code} {detail}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            print(f"upload attempt {attempt + 1}: {err}", file=sys.stderr)
    raise SystemExit("upload failed after retries")


def target():
    token = os.environ.get("PURRNET_BENCH_TOKEN", "").strip()
    if not token:
        raise SystemExit("PURRNET_BENCH_TOKEN is not set")
    return os.environ.get("PURRNET_BENCH_URL", "").strip() or DEFAULT_URL, token


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout


def git_file(rev, path):
    try:
        return git("show", f"{rev}:{path}")
    except subprocess.CalledProcessError:
        return None


def derived_config(datapoints):
    """What the suite was, read back from the datapoints (for runs sent without their inputs)."""
    sessions = sorted({(d.get("size") or d.get("connections"), d.get("tick") or (d.get("meta") or {}).get("tickRate"))
                       for d in datapoints}, key=lambda s: (s[0] or 0, s[1] or 0))
    meta = next((d.get("meta") or {} for d in datapoints if d.get("meta")), {})
    return {
        "sessions": ",".join(f"{c}@{t}" for c, t in sessions),
        "netcodes": ",".join(sorted({d.get("netcode", "?") for d in datapoints})),
        "bench_objects": meta.get("benchObjects"),
        "bench_seconds": meta.get("benchSeconds"),
        "profiling": meta.get("devBuild"),
        "cpu": meta.get("cpuModel"),
    }


def cmd_send(args):
    url, token = target()
    datapoints = json.loads(Path(args.data).read_text(encoding="utf-8"))
    versions = json.loads(Path(args.versions).read_text(encoding="utf-8")) if args.versions and Path(args.versions).exists() else {}
    purrnet_commit = args.purrnet_commit or versions.pop("purrnet_commit", None)
    versions.pop("purrnet_commit", None)
    config = derived_config(datapoints)
    if args.config_json:
        config.update({k: v for k, v in json.loads(args.config_json).items() if v not in (None, "")})
    payload = {
        "run_id": args.run_id or None,
        "run_url": args.run_url or None,
        "commit": args.commit or None,
        "purrnet_commit": purrnet_commit,
        "ran_at": args.ran_at or datetime.now(timezone.utc).isoformat(),
        "complete": args.complete == "true",
        "versions": versions,
        "config": config,
        "datapoints": datapoints,
    }
    if not payload["run_id"]:
        payload["source_key"] = args.source_key or f"local:{int(time.time())}"
    res = post(payload, url, token)
    print(f"uploaded {len(datapoints)} datapoints: {json.dumps(res)}")


def purrnet_version(commit, cache={}):
    """PurrNet's package.json version at a commit, or None offline."""
    if commit not in cache:
        url = f"https://raw.githubusercontent.com/PurrNet/PurrNet/{commit}/Assets/PurrNet/package.json"
        try:
            with urllib.request.urlopen(url, timeout=20) as res:
                cache[commit] = json.loads(res.read().decode("utf-8")).get("version")
        except (urllib.error.URLError, TimeoutError, ValueError):
            cache[commit] = None
    return cache[commit]


def parse_versions(md):
    """The versions in latest.md's header line: '_Last run DATE: PurrNet 1.2 · FishNet 4.7 · ... · Unity 6000 · ...'."""
    first = (md or "").splitlines()[0] if md else ""
    m = re.match(r"_Last run [^:]+: (.*)", first)
    if not m:
        return {}
    out = {}
    for part in m.group(1).split(" · "):
        name, _, version = part.partition(" ")
        if name in NAMES and version:
            out[NAMES[name]] = version.rstrip("._")
    return out


def cmd_backfill(args):
    url, token = target() if not args.dry_run else (None, None)
    log = git("log", "--format=%H%x09%P%x09%cI%x09%s", "--", "docs/latest.json")
    commits = []
    for line in log.splitlines():
        sha, parents, when, subject = line.split("\t", 3)
        m = re.match(r"bench: latest results from run (\d+)", subject)
        if m:
            commits.append((sha, parents.split(" ")[0], when, int(m.group(1))))
    commits.reverse()  # oldest first, so a partial backfill still leaves a contiguous history
    if args.limit:
        commits = commits[-args.limit:]
    print(f"{len(commits)} published runs in history")
    for sha, parent, when, run_id in commits:
        data = git_file(sha, "docs/latest.json")
        if not data:
            print(f"  {sha[:7]} run {run_id}: no latest.json, skipped")
            continue
        datapoints = json.loads(data)
        versions = parse_versions(git_file(sha, "docs/latest.md"))
        lock = git_file(sha, "purrnet/Packages/packages-lock.json")
        purrnet_commit = None
        if lock:
            purrnet_commit = (json.loads(lock).get("dependencies", {}).get("dev.purrnet.purrnet") or {}).get("hash")
        # Runs made while the manifest said #dev (or before latest.md named versions) only know the commit.
        if purrnet_commit and not re.match(r"\d", versions.get("purrnet", "")):
            versions["purrnet"] = purrnet_version(purrnet_commit) or versions.get("purrnet", "?")
        payload = {
            "run_id": run_id,
            "run_url": f"{REPO_URL}/actions/runs/{run_id}",
            "commit": parent or None,
            "purrnet_commit": purrnet_commit,
            "ran_at": when,
            "complete": True,  # only complete runs were ever committed to docs/
            "versions": versions,
            "config": {**derived_config(datapoints), "backfilled_from": sha},
            "datapoints": datapoints,
        }
        label = f"  {when[:16]} run {run_id}: {len(datapoints)} datapoints, PurrNet {versions.get('purrnet', '?')}"
        if args.dry_run:
            print(label + " (dry run)")
            continue
        res = post(payload, url, token)
        stale = f", {res['skipped']} stale skipped" if res.get("skipped") else ""
        print(label + (" (replaced" if res.get("replaced") else " (new") + stale + ")")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send", help="upload one run")
    s.add_argument("--data", required=True, help="scaling.json")
    s.add_argument("--versions", help="versions.json from versions.sh")
    s.add_argument("--complete", required=True, choices=["true", "false"])
    s.add_argument("--run-id")
    s.add_argument("--run-url")
    s.add_argument("--commit")
    s.add_argument("--purrnet-commit")
    s.add_argument("--config-json", help="the workflow inputs, as JSON")
    s.add_argument("--ran-at")
    s.add_argument("--source-key", help="key for a run without a workflow run id (default local:<time>)")
    b = sub.add_parser("backfill", help="resend every published run from git history")
    b.add_argument("--dry-run", action="store_true")
    b.add_argument("--limit", type=int, default=0, help="only the newest N runs")
    args = ap.parse_args()
    {"send": cmd_send, "backfill": cmd_backfill}[args.cmd](args)


if __name__ == "__main__":
    main()
