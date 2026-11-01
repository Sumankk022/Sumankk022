#!/usr/bin/env bash
# Builds the_last_coffee.mp4 (1080x1920, 30fps, 30s) from scratch.
set -euo pipefail
cd "$(dirname "$0")"
TMP=$(mktemp -d)
python3 render.py "$TMP" "${WORKERS:-4}"
python3 audio.py "$TMP/audio.wav"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$TMP/parts.txt" -i "$TMP/audio.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart \
  the_last_coffee.mp4
rm -rf "$TMP"
echo "wrote $(pwd)/the_last_coffee.mp4"
