#!/usr/bin/env bash
# Every round-6 main-table setting with the fingerprint cache, 4 jobs at a time (~2.5 GB each).
cd "$(dirname "$0")/.."
export PY=../../.condaenv/bin/python
mkdir -p results/logs
job() {
  $PY -u src/run10.py --dataset "$1" ${2:+--budgets "$2"} > "results/logs/$1${2:+-$2}.log" 2>&1
  echo "done $1 $2 exit $?"
}
export -f job
printf '%s\n' "caida 128,256" "caida 1024,2048" "shalla 256,1024" "shalla 2048,4096" "cod" "url" \
  "caida_flow" "mawi2020_flow" "mawi2021_flow" "mawi2022_flow" |
  xargs -P 4 -L 1 bash -c 'job "$0" "$1"'
