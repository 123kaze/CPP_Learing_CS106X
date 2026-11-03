#!/usr/bin/env bash
# Every method on every TCP-only trace, 4 processes at a time (one method per process).
cd "$(dirname "$0")/.."
export PY=../../.condaenv/bin/python
mkdir -p results/logs
job() {
  $PY -u src/tcp11.py method "$1" "$2" > "results/logs/$1_$2.log" 2>&1
  echo "done $1 $2 exit $?"
}
export -f job
for m in run5 run6 run10 grid10; do
  for d in caida_tcp_flow mawi2020_tcp_flow mawi2021_tcp_flow mawi2022_tcp_flow; do
    [ "$m $d" = "run5 caida_tcp_flow" ] && [ -f results/run5/results/rows_caida_tcp_flow_189.csv ] && continue
    echo "$m $d"
  done
done | xargs -P 4 -L 1 bash -c 'job "$0" "$1"'
