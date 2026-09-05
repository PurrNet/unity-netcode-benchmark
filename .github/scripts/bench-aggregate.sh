#!/usr/bin/env bash
# Renders one benchmark run (one netcode, one session) to the job summary and emits a compact
# datapoint (dp-<netcode>-<tag>.json) for bench-scaling.sh.
#
# Inputs are the per-process JSON files written by BenchRunner (Shared/com.purrnet.netbench):
#   <results_dir>/server.json          server process
#   <results_dir>/client-<idx>.json    measured (single-process) clients
#
# Usage: bench-aggregate.sh <results_dir> <netcode> <total_connections> <tag> <window_s> <objects> <out_dir>
set -euo pipefail

RESULTS_DIR="${1:?results dir}"
NETCODE="${2:?netcode}"
TOTAL="${3:?total connections}"
TAG="${4:-solo}"
WINDOW="${5:-?}"
OBJECTS="${6:-?}"
OUT_DIR="${7:-scaling}"

SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/stdout}"
mkdir -p "$OUT_DIR"

# Artifacts may nest their files (an artifact with several paths keeps its directory structure),
# so locate the result files recursively rather than assuming a flat layout.
SERVER_FILE=$(find "$RESULTS_DIR" -type f -name server.json | head -n1)
[ -z "$SERVER_FILE" ] && SERVER_FILE="$RESULTS_DIR/server.json"
mapfile -t CLIENT_FILES < <(find "$RESULTS_DIR" -type f -name 'client-*.json' | sort)
PROCESS_FILE=$(find "$RESULTS_DIR" -type f -name process-server.json | head -n1)
SERVER_VALID=false
if [ -s "$SERVER_FILE" ] && jq -e 'type == "object" and (.tests | type == "array")' "$SERVER_FILE" >/dev/null 2>&1; then
  SERVER_VALID=true
fi

JQ_LIB='
def hbR:
  if . == null then "-"
  elif . < 1024 then "\(.|floor) B/s"
  elif . < 1048576 then "\((.*10/1024|floor)/10) KB/s"
  else "\((.*100/1048576|floor)/100) MB/s" end;
def r1: if . == null then "-" else "\((.*10|floor)/10)" end;
def r2: if . == null then "-" else "\((.*100|floor)/100)" end;
def mb: if . == null then "-" else "\((./1048576)|floor) MB" end;
def avg(f): if length == 0 then null else (map(f) | add) / length end;
def byName: map({key: .name, value: .}) | from_entries;
'

{
  echo "## ${NETCODE} — ${TOTAL} connections (tag: ${TAG})"
  echo ""
} >> "$SUMMARY"

if [ "$SERVER_VALID" = true ]; then
  jq -r "$JQ_LIB"'
    . as $run
    | ($run.tests | byName) as $t
    | "Window: '"$WINDOW"'s · Objects: '"$OBJECTS"' · Measured clients: '"${#CLIENT_FILES[@]}"' · Server CPU: \($run.cpuModel) x\($run.cpuCount) · Tick: \($run.tickRate) Hz · \(if $run.devBuild then "Development" else "Release" end) build · Connected at start: \($run.connectedAtStart)/\($run.expectedClients)"
      + (if ($run.error // "") != "" then "\n\n> ⚠️ Server reported: `\($run.error)`" else "" end)
      + "\n\n### Server\n\n"
      + "| Test | Objects | Conns | Down on-wire | Per-conn down | Up on-wire | Pkts out/s | Inputs in/s | CPU | Avg frame | p95 | p99 | GC | Alloc | Heap | Peak RSS |\n"
      + "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
      + ( [ $run.tests[]
            | (if .connections > 0 then .txBytesPerSec / .connections else null end) as $perConn
            | "| \(.name)\(if .truncated then " ⚠️" else "" end) | \(.objects) | \(.connections) | \(.txBytesPerSec|hbR) | \($perConn|hbR) | \(.rxBytesPerSec|hbR) | \(.txPacketsPerSec|floor) | \(if (.inputsPerSec // 0) > 0 then (.inputsPerSec|floor) else "-" end) | \(.cpuPercent|r1)% | \(.avgFrameMs|r2) ms | \(.p95FrameMs|r2) ms | \(.p99FrameMs|r2) ms | \(.gcCollections) | \(if (.gcAllocBytesPerSec // -1) >= 0 then (.gcAllocBytesPerSec|hbR) else "-" end) | \(.managedHeapBytes|mb) | \(.peakRssBytes|mb) |"
          ] | join("\n") )
      + "\n\nOn-wire = bytes on the `\($run.tests[0].iface // "?")` interface (UDP/IP headers, ACKs and resends included). CPU = whole process, all threads, % of one core; frame loop capped at \($run.targetFps) fps.\n"
      # CPU-by-marker table (Development builds only): top markers by peak per-frame µs, one column per test.
      + ( ([ $run.tests[] | .cpuMarkers[]?.name ] | unique) as $names
          | if ($names | length) == 0 then "" else
            ($names
              | map(. as $n | {name: $n, peak: ([ $run.tests[] | (.cpuMarkers // [])[] | select(.name == $n) | .perFrameMs ] | max // 0)})
              | sort_by(-.peak) | .[0:15] | map(.name)) as $top
            | "\n#### Server CPU µs/frame by profiler marker (Development build)\n\n"
            + "| Marker | \([ $run.tests[].name ] | join(" | ")) |\n|---|\([ $run.tests[] | "---" ] | join("|"))|\n"
            + ( [ $top[] | . as $mk
                  | "| \($mk) | " + ( [ $run.tests[] | ((.cpuMarkers // []) | map(select(.name == $mk)) | first) as $e | if $e == null then "-" else "\($e.perFrameMs * 1000 | floor)" end ] | join(" | ") ) + " |"
                ] | join("\n") )
            + "\n"
            end )
  ' "$SERVER_FILE" >> "$SUMMARY"
  echo "" >> "$SUMMARY"
else
  echo "_No server result file._" >> "$SUMMARY"
  echo "" >> "$SUMMARY"
fi

if [ ${#CLIENT_FILES[@]} -gt 0 ]; then
  jq -rs "$JQ_LIB"'
    [ .[] | select(.measured == true) ] as $runs
    | ($runs | length) as $n
    | ([ $runs[].tests[].name ] | unique) as $names
    | "### Measured clients (avg of \($n))\n\n"
      + "| Test | Down per client | Up per client | Truncated |\n|---|---|---|---|\n"
      + ( [ ("Idle", "MoveY", "MoveWander", "SendRPC", "Static", "SpawnChurn", "ClientInput", "SyncVars", "MoveAllAxis") as $name
            | [ $runs[].tests[] | select(.name == $name) ] as $rows
            | select(($rows | length) > 0)
            | "| \($name) | \($rows | avg(.rxBytesPerSec) | hbR) | \($rows | avg(.txBytesPerSec) | hbR) | \([ $rows[] | select(.truncated) ] | length)/\($rows | length) |"
          ] | join("\n") )
      + "\n"
      + ( [ $runs[] | select((.error // "") != "") | .error ] | if length == 0 then "" else "\n> ⚠️ \(length) client(s) reported errors: \(unique | join("; "))\n" end )
  ' "${CLIENT_FILES[@]}" >> "$SUMMARY"
  echo "" >> "$SUMMARY"
fi

# A server result whose expected client count is not this session's total was not produced by this
# session (a self-hosted runner can leave an earlier session's files in the workspace); no datapoint.
if [ "$SERVER_VALID" = true ]; then
  EXPECTED=$(jq -r '.expectedClients // 0' "$SERVER_FILE")
  if [ "$EXPECTED" != "$TOTAL" ]; then
    echo "::error::$NETCODE ($TAG): server result expects $EXPECTED clients but this session runs $TOTAL; not writing a datapoint"
    exit 0
  fi
fi

# Datapoint for the cross-netcode scaling table. Inputs go through files (--slurpfile), not
# arguments: with 25+ clients the concatenated JSON exceeds the exec argument limit.
TMP_DIR=$(mktemp -d)
if [ "$SERVER_VALID" = true ]; then
  cp "$SERVER_FILE" "$TMP_DIR/server.json"
else
  echo "null" > "$TMP_DIR/server.json"
fi
if [ -n "$PROCESS_FILE" ]; then
  cp "$PROCESS_FILE" "$TMP_DIR/process.json"
else
  echo '{}' > "$TMP_DIR/process.json"
fi
if [ ${#CLIENT_FILES[@]} -gt 0 ]; then
  jq -s '[ .[] | select(.measured == true) ]' "${CLIENT_FILES[@]}" > "$TMP_DIR/clients.json"
else
  echo "[]" > "$TMP_DIR/clients.json"
fi

jq -n \
  --arg netcode "$NETCODE" --argjson connections "$TOTAL" --arg tag "$TAG" \
  --slurpfile serverFile "$TMP_DIR/server.json" --slurpfile clientsFile "$TMP_DIR/clients.json" \
  --slurpfile processFile "$TMP_DIR/process.json" \
  "$JQ_LIB"'
  $serverFile[0] as $server | $clientsFile[0] as $clients | $processFile[0] as $process
  | ($server.tests // [] | byName) as $st
  | {
      netcode: $netcode,
      connections: $connections,
      # Requested size and tick from the tag (c100t60 -> 100 connections at 60 Hz) so capped runs
      # (e.g. Fusion at 99) land in the same row as the other netcodes; fall back to the actual values.
      size: (([$tag | capture("^c(?<n>[0-9]+)") | .n] | first // ($connections | tostring)) | tonumber),
      tick: (([$tag | capture("t(?<t>[0-9]+)$") | .t] | first // ($server.tickRate | tostring)) | tonumber),
      tag: $tag,
      meta: {
        cpuModel: $server.cpuModel, cpuCount: $server.cpuCount, devBuild: $server.devBuild,
        tickRate: $server.tickRate, requestedTickRate: ($server.requestedTickRate // 0), unityVersion: $server.unityVersion,
        connectedAtStart: $server.connectedAtStart, expectedClients: ($server.expectedClients // $connections),
        process: $process,
        serverError: (if $process.status == "resource-limit-exceeded" then
                        "resource limit exceeded (" + (if $process.reason == "memory" then "\($process.limit / 1073741824) GiB memory"
                                                      else "\($process.limit)s time" end) + ")"
                      elif $process.status == "host-oom" then "host memory exhausted (infrastructure failure)"
                      elif $server.error == "timeout" then "resource limit exceeded (" +
                        (if $process.harnessMaxSeconds then "\($process.harnessMaxSeconds)s harness time" else "harness time" end) + ")"
                      elif $server == null then "did not complete: no valid server result"
                      elif ($server.error // "") != "" then $server.error
                      elif ($process.exitCode // 0) != 0 then "server exited with code \($process.exitCode)"
                      elif $server.completed == false then "did not complete: the server died after \($server.tests | length) tests"
                      else null end),
        measuredClients: ($clients | length)
      },
      server: $st,
      clients: ( [ $clients[].tests[].name ] | unique
                 | map(. as $name
                       | [ $clients[].tests[] | select(.name == $name) ] as $rows
                       | {key: $name, value: {
                           n: ($rows | length),
                           rxBytesPerSec: ($rows | avg(.rxBytesPerSec)),
                           txBytesPerSec: ($rows | avg(.txBytesPerSec)),
                           rttAvgMs: ($rows | avg(.rttAvgMs)),
                           rttP50Ms: ($rows | avg(.rttP50Ms)),
                           rttP95Ms: ($rows | avg(.rttP95Ms)),
                           rttP99Ms: ($rows | avg(.rttP99Ms)),
                           rpcsReceivedPerSec: ($rows | map(select(has("rpcsReceivedPerSec"))) | avg(.rpcsReceivedPerSec)),
                           syncObservationClients: ($rows | map(select(.syncObservationAvailable == true)) | length),
                           syncObservedChangesPerSec: ($rows | map(select(.syncObservationAvailable == true)) | avg(.syncObservedChangesPerSec)),
                           syncSilenceAvgMs: ($rows | map(select(.syncObservationAvailable == true)) | avg(.syncSilenceAvgMs)),
                           syncSilenceMaxMs: ($rows | map(select(.syncObservationAvailable == true)) | map(.syncSilenceMaxMs) | max),
                           rpcDeliveryChecked: ([ $rows[] | select($name == "SendRPC" and $st[$name].deliveryComplete == true and .deliveryComplete == true) ] | length),
                           rpcDeliveryMatched: ([ $rows[] | select($name == "SendRPC" and $st[$name].deliveryComplete == true and .deliveryComplete == true and .rpcsReceived == $st[$name].rpcsSent) ] | length),
                           syncStateChecked: ([ $rows[] | select($name == "SyncVars" and $st[$name].deliveryComplete == true and .deliveryComplete == true) ] | length),
                           syncStateMatched: ([ $rows[] | select($name == "SyncVars" and $st[$name].deliveryComplete == true and .deliveryComplete == true and .finalStateObjects == $st[$name].finalStateObjects and .finalStateObjects > 0 and .finalStateHash == $st[$name].finalStateHash) ] | length),
                           truncated: ([ $rows[] | select(.truncated) ] | length)
                         }})
                 | from_entries )
    }
' > "$OUT_DIR/dp-${NETCODE}-${TAG}.json"

echo "Datapoint written to $OUT_DIR/dp-${NETCODE}-${TAG}.json"
