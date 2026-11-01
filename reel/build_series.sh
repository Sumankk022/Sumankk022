#!/usr/bin/env bash
# Builds episodes 2-6 (or the ones named as arguments), e.g. ./build_series.sh ep4_rainyday
set -euo pipefail
cd "$(dirname "$0")"
EPS=("$@")
[ ${#EPS[@]} -eq 0 ] && EPS=(ep2_sandcastle ep3_pancake ep4_rainyday ep5_legday ep6_snowman)
for ep in "${EPS[@]}"; do
  TMP=$(mktemp -d)
  python3 "$ep.py" video "$TMP" "${WORKERS:-4}"
  python3 "$ep.py" audio "$TMP/audio.wav"
  ffmpeg -y -loglevel error -f concat -safe 0 -i "$TMP/parts.txt" -i "$TMP/audio.wav" \
    -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$ep.mp4"
  rm -rf "$TMP"
  echo "wrote $(pwd)/$ep.mp4"
done
