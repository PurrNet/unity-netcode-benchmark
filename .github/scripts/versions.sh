#!/usr/bin/env bash
# Prints a JSON object with the netcode library versions committed in this repo (for result headers).
set -euo pipefail
cd "$(dirname "$0")/../.."

# PurrNet is either vendored under Assets (package.json) or pulled from git via the manifest. CI pins
# the git dependency to one commit (pin-purrnet.py); PURRNET_COMMIT names it when this checkout is not
# pinned. The version is that commit's package.json, and the commit is reported next to it, since the
# dev branch moves past its last release tag.
purrnet=$(jq -r '.version // empty' purrnet/Assets/PurrNet/package.json 2>/dev/null || true)
purrnet_commit="${PURRNET_COMMIT:-}"
if [ -z "$purrnet" ]; then
  rev=$(jq -r '.dependencies["dev.purrnet.purrnet"] // empty' purrnet/Packages/manifest.json 2>/dev/null | sed -n 's/.*#//p')
  if [ -z "$purrnet_commit" ]; then
    if [[ "$rev" =~ ^[0-9a-f]{40}$ ]]; then
      purrnet_commit=$rev
    else
      purrnet_commit=$(jq -r '.dependencies["dev.purrnet.purrnet"].hash // empty' purrnet/Packages/packages-lock.json 2>/dev/null || true)
    fi
  fi
  if [ -n "$purrnet_commit" ]; then
    purrnet=$(curl -fsSL --max-time 20 "https://raw.githubusercontent.com/PurrNet/PurrNet/$purrnet_commit/Assets/PurrNet/package.json" 2>/dev/null \
      | jq -r '.version // empty' 2>/dev/null || true)
  fi
  # Offline: a release tag in the manifest (#v1.2.3) still names the version.
  [ -n "$purrnet" ] || purrnet=$(sed -n 's/^v\{0,1\}\([0-9].*\)/\1/p' <<< "$rev")
fi
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
  --arg purrnet_commit "${purrnet_commit:-}" \
  '{purrnet: $purrnet, fishnet: $fishnet, mirror: $mirror, ngo: $ngo, fusion: $fusion, unity: $unity}
   + (if $purrnet_commit != "" then {purrnet_commit: $purrnet_commit} else {} end)'
