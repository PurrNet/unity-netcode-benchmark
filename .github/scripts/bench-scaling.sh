#!/usr/bin/env bash
# Merges the datapoints emitted by bench-aggregate.sh (dp-<netcode>-<tag>.json) into
# <out_dir>/scaling.json and writes a short coverage table to the job summary. The readable
# tables come from render-summary.py and the full picture from render-report.py; both read
# scaling.json.
#
# Usage: bench-scaling.sh <datapoints_dir> [out_dir]
set -euo pipefail

DP_DIR="${1:?datapoints dir}"
OUT_DIR="${2:-results-out}"

SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/stdout}"
mkdir -p "$OUT_DIR"

shopt -s nullglob
FILES=("$DP_DIR"/dp-*.json)

if [ ${#FILES[@]} -eq 0 ]; then
  echo "[]" > "$OUT_DIR/scaling.json"
  printf '## Netcode scaling benchmark\n\n_No datapoints collected._\n' >> "$SUMMARY"
  exit 0
fi

jq -s '.' "${FILES[@]}" > "$OUT_DIR/scaling.json"

# Coverage: one row per session, one column per netcode, cell = clients connected at start.
jq -r '
  (["purrnet", "fishnet", "mirror", "ngo", "fusion"]) as $order
  | (map(.netcode) | unique) as $present
  | [ $order[] | select(. as $n | $present | index($n)) ] as $netcodes
  | (map({size: .size, tick: .tick}) | unique | sort_by(.size, .tick)) as $sessions
  | (reduce .[] as $d ({}; .[$d.netcode + "@" + ($d.size|tostring) + "@" + ($d.tick|tostring)] = $d)) as $dp
  | "### Datapoints\n\n| Session | " + ($netcodes | join(" | ")) + " |\n|---|" + ($netcodes | map("---") | join("|")) + "|\n"
    + ( [ $sessions[] as $s
          | "| \($s.size) connections @ \($s.tick) Hz | "
            + ( [ $netcodes[] as $n | $dp[$n + "@" + ($s.size|tostring) + "@" + ($s.tick|tostring)] as $d
                  | if $d == null then "missing"
                    else "\($d.meta.connectedAtStart)/\($d.meta.expectedClients)"
                      + (if $d.meta.tickRate != $s.tick then " ⚠️ \($d.meta.tickRate) Hz" else "" end)
                      + (if $d.meta.serverError != null then " ⚠️ \($d.meta.serverError)" else "" end)
                    end ] | join(" | ") )
            + " |" ] | join("\n") )
    + "\n\nCells are clients connected at start / expected.\n"
' "$OUT_DIR/scaling.json" >> "$SUMMARY"

echo "Merged ${#FILES[@]} datapoints into $OUT_DIR/scaling.json"
