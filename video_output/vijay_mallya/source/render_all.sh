#!/bin/bash
# usage: render_all.sh N_PARTS PARALLEL [part ids...]
N=$1; P=$2; shift 2
ids="$@"; [ -z "$ids" ] && ids=$(seq 0 $((N-1)))
printf "%s\n" $ids | xargs -P $P -I{} sh -c "python3 engine.py --part {} $N > out/log_{}.txt 2>&1 && echo done {}"
