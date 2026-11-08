#!/bin/bash
set -e
N=32
: > out/parts.txt
for i in $(seq 0 $((N-1))); do printf "file 'part_%02d.mp4'\n" $i >> out/parts.txt; done
ffmpeg -v error -y -f concat -safe 0 -i out/parts.txt -c copy out/video_only.mp4
# master: full quality video + 320k AAC
ffmpeg -v error -y -i out/video_only.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -movflags +faststart -shortest out/Vijay_Mallya_master_1080p.mp4
# GitHub-friendly 1080p (<100 MB): two-pass x264 ~1.35 Mbps video + 128k audio
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 out/video_only.mp4)
ffmpeg -v error -y -i out/video_only.mp4 -c:v libx264 -preset slow -tune film -b:v 1350k -pass 1 -passlogfile out/x264 -an -f mp4 /dev/null
ffmpeg -v error -y -i out/video_only.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v libx264 -preset slow -tune film -b:v 1350k -pass 2 -passlogfile out/x264 \
  -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart -shortest out/Vijay_Mallya_1080p.mp4
ls -la out/*.mp4 | grep Vijay
