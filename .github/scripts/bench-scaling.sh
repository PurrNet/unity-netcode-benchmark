#!/usr/bin/env bash
# Renders the cross-netcode scaling comparison from the datapoints emitted by bench-aggregate.sh
# (dp-<netcode>-<connections>.json). Output goes to the job summary and to <out_dir>/summary.md,
# with the merged datapoints in <out_dir>/scaling.json.
#
# Usage: bench-scaling.sh <datapoints_dir> <window_s> <objects> [versions_json] [out_dir]
set -euo pipefail

DP_DIR="${1:?datapoints dir}"
WINDOW="${2:-?}"
OBJECTS="${3:-?}"
VERSIONS="${4:-}"
OUT_DIR="${5:-results-out}"

SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/stdout}"
mkdir -p "$OUT_DIR"
MD="$OUT_DIR/summary.md"

shopt -s nullglob
FILES=("$DP_DIR"/dp-*.json)

if [ ${#FILES[@]} -eq 0 ]; then
  echo "## Netcode scaling benchmark" > "$MD"
  echo "" >> "$MD"
  echo "_No datapoints collected._" >> "$MD"
  cat "$MD" >> "$SUMMARY"
  exit 0
fi

VERSIONS_JSON="{}"
[ -n "$VERSIONS" ] && [ -f "$VERSIONS" ] && VERSIONS_JSON=$(cat "$VERSIONS")

jq -s '.' "${FILES[@]}" > "$OUT_DIR/scaling.json"

jq -r --argjson versions "$VERSIONS_JSON" --arg window "$WINDOW" --arg objects "$OBJECTS" '
  def r1: if . == null then "-" else "\((.*10|floor)/10)" end;
  def r2: if . == null then "-" else "\((.*100|floor)/100)" end;
  def kb: if . == null then "-" else "\((./1024*10|floor)/10)" end;
  def d1: (. // 0) | (.*10|floor)/10;
  def shortCpu: if . == null then "-" else (gsub("\\(R\\)|\\(TM\\)|CPU|Processor|@.*$"; "") | gsub("  +"; " ") | ltrimstr(" ") | rtrimstr(" ")) end;

  (["purrnet", "fishnet", "mirror", "ngo", "fusion"]) as $order
  | ["#2f6feb", "#e36209", "#6f42c1", "#1a7f37", "#cf222e"] as $palette
  | (map(.netcode) | unique) as $present
  | [ $order[] | select(. as $n | $present | index($n)) ] as $netcodes
  # Rows are keyed by the requested size (Fusion capped at 99 still sits in the 100 row); the
  # "clients connected" table shows the actual counts.
  | (map(.size // .connections) | unique | sort) as $conns
  # dp[netcode][size] = datapoint
  | (reduce .[] as $d ({}; .[$d.netcode][($d.size // $d.connections) | tostring] = $d)) as $dp
  | def cell($n; $c): $dp[$n][$c | tostring];
  # Generic table: rows = connection counts, columns = netcodes, cell = f(datapoint)
  def table(title; f):
      "#### \(title)\n\n| Connections | \($netcodes | join(" | ")) |\n|---|\($netcodes | map("---") | join("|"))|\n"
      + ( [ $conns[] as $c | "| \($c) | " + ( [ $netcodes[] as $n | (cell($n; $c)) as $d | if $d == null then "-" else ($d | f) end ] | join(" | ") ) + " |" ] | join("\n") )
      + "\n\n";
  def chart(title; ylabel; f):
      ( [ $netcodes[] as $n | [ $conns[] as $c | (cell($n; $c)) as $d | if $d == null then 0 else ($d | f | d1) end ] ] ) as $series
      | ( [ $series[][] ] | max // 0 ) as $m
      | "```mermaid\n%%{init: {\"themeVariables\": {\"xyChart\": {\"plotColorPalette\": \"\([ range(0; $netcodes|length) as $i | $palette[$i] ] | join(","))\"}}}}%%\nxychart-beta\n"
        + "    title \"\(title)\"\n"
        + "    x-axis [\($conns | map(tostring) | join(", "))]\n"
        + "    y-axis \"\(ylabel)\" 0 --> \((($m * 1.1) | floor) + 1)\n"
        + ( [ $series[] | "    line [\(map(tostring) | join(", "))]" ] | join("\n") )
        + "\n```\n"
        + "Series: " + ( [ range(0; $netcodes|length) as $i | "\($palette[$i]) \($netcodes[$i])" ] | join(" · ") ) + "\n\n";
  def idleCpu($d): ($d.server.Idle.cpuPercent // 0);

  "## Netcode scaling benchmark\n\n"
  + "Window: \($window)s per test · Objects per test: \($objects) · Connections: \($conns | map(tostring) | join(" / "))\n\n"
  + "| Netcode | Version |\n|---|---|\n"
  + ( [ $netcodes[] as $n | "| \($n) | \($versions[$n] // "?") |" ] | join("\n") )
  + "\n| unity | \($versions.unity // "?") |\n\n"
  + "Every netcode runs the same scenario: the server spawns N objects and replicates them to every client. MoveY / MoveAllAxis / MoveWander move them each tick; SendRPC fires one observers-RPC with one float per object per tick; Static spawns them and never touches them; SpawnChurn keeps N alive while despawning and spawning N/50 per tick; ClientInput spawns one hub object and every client sends one small server RPC (Vector3 + float) per tick; SyncVars changes one of four synced fields per object per tick. "
  + "Server numbers come from the single server process; client numbers are averages over the single-process measured clients. "
  + "On-wire bandwidth is read from the network interface (headers, ACKs and resends included). CPU is the whole process, all threads, as % of one core with the frame loop capped at 60 fps; the Idle row (connected, nothing spawned) is the per-netcode baseline and is subtracted in the \"CPU − idle\" tables. "
  + "Fusion is relay-based: server and clients talk to Photon Cloud (traffic measured on the public interface, RTT includes the relay hop); the server still sends one stream per client, so its downstream is comparable.\n\n"
  + "### Machines\n\n"
  + table("Server CPU model (numbers are only comparable within a row when these match)"; "\(.meta.cpuModel | shortCpu) x\(.meta.cpuCount)\(if .meta.devBuild then " (dev)" else "" end)")
  + table("Clients connected at start / expected · measured clients (rows are the requested size; a capped or partially connected run shows its real count here)"; "\(.meta.connectedAtStart)/\(.meta.expectedClients) · \(.meta.measuredClients)\(if .meta.serverError != null then " ⚠️ \(.meta.serverError)" else "" end)")
  + "### Idle baseline (connected, nothing spawned)\n\n"
  + table("Server CPU % · frame p95 ms"; "\(.server.Idle.cpuPercent | r1)% · \(.server.Idle.p95FrameMs | r2) ms")
  + ( [ ("MoveY", "MoveAllAxis", "MoveWander", "SendRPC", "Static", "SpawnChurn", "ClientInput", "SyncVars") as $t
        | "### \($t)\n\n"
        + table("\($t) — server downstream on-wire (KB/s, all clients)"; .server[$t].txBytesPerSec | kb)
        + table("\($t) — per-client downstream on-wire (KB/s, client-measured)"; .clients[$t].rxBytesPerSec | kb)
        + table("\($t) — server upstream on-wire (KB/s, all clients)"; .server[$t].rxBytesPerSec | kb)
        + table("\($t) — per-client upstream on-wire (KB/s, client-measured)"; .clients[$t].txBytesPerSec | kb)
        + ( if $t == "ClientInput" then table("ClientInput — server input RPCs received per second (expected ≈ 20 × connections)"; .server[$t].inputsPerSec | if . == null then "-" else floor end) else "" end )
        + table("\($t) — server CPU % minus idle (raw)"; . as $d | ($d.server[$t].cpuPercent) as $c | if $c == null then "-" else "\(($c - idleCpu($d)) | r1)% (\($c | r1)%)" end)
        + table("\($t) — server frame avg / p95 / p99 (ms)"; "\(.server[$t].avgFrameMs | r2) / \(.server[$t].p95FrameMs | r2) / \(.server[$t].p99FrameMs | r2)")
        + table("\($t) — server GC collections · peak RSS"; "\(.server[$t].gcCollections // "-") · \(((.server[$t].peakRssBytes // 0) / 1048576) | floor) MB")
        + table("\($t) — client RTT p50 / p95 (ms, netcode-reported)"; "\(.clients[$t].rttP50Ms | r2) / \(.clients[$t].rttP95Ms | r2)")
        + ( if ($conns | length) < 2 then "_Charts need ≥2 connection sizes._\n\n"
            else chart("\($t) — server downstream KB/s vs connections"; "KB/s"; (.server[$t].txBytesPerSec // 0) / 1024)
               + chart("\($t) — per-client downstream KB/s vs connections"; "KB/s"; (.clients[$t].rxBytesPerSec // 0) / 1024)
               + chart("\($t) — server CPU % minus idle vs connections"; "CPU %"; . as $d | (($d.server[$t].cpuPercent // 0) - idleCpu($d)))
               + chart("\($t) — client RTT p95 ms vs connections"; "ms"; .clients[$t].rttP95Ms // 0)
            end )
      ] | join("") )
' "$OUT_DIR/scaling.json" > "$MD" || {
  echo "_Failed to render datapoints._" > "$MD"
}

cat "$MD" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "Summary written to $MD"
