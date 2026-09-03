#!/usr/bin/env bash
# Prints a JSON object with the netcode library versions committed in this repo (for result headers).
set -euo pipefail
cd "$(dirname "$0")/../.."

purrnet=$(jq -r '.version // "?"' purrnet/Assets/PurrNet/package.json 2>/dev/null || echo "?")
fishnet=$(find fishnet/Assets/FishNet -maxdepth 2 -name package.json -exec jq -r '.version // empty' {} \; 2>/dev/null | head -n1)
mirror=$(tr -d '[:space:]' < mirror/Assets/Mirror/version.txt 2>/dev/null || echo "?")
ngo=$(jq -r '.dependencies["com.unity.netcode.gameobjects"] // "?"' ngo/Packages/manifest.json 2>/dev/null || echo "?")
fusion=$(sed -n 's/^build: *//p' fusion/Assets/Photon/Fusion/build_info.txt 2>/dev/null | head -n1)
unity=$(sed -n 's/^m_EditorVersion: *//p' purrnet/ProjectSettings/ProjectVersion.txt 2>/dev/null | head -n1)

jq -n \
  --arg purrnet "${purrnet:-?}" \
  --arg fishnet "${fishnet:-?}" \
  --arg mirror "${mirror:-?}" \
  --arg ngo "${ngo:-?}" \
  --arg fusion "${fusion:-?}" \
  --arg unity "${unity:-?}" \
  '{purrnet: $purrnet, fishnet: $fishnet, mirror: $mirror, ngo: $ngo, fusion: $fusion, unity: $unity}'
